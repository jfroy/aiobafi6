"""aiobafi6 device.

Provides functionality to query and control BAF i6 protocol devices.
"""
from __future__ import annotations

import asyncio
import copy
import inspect
import logging
import time
import typing as t

from google.protobuf import json_format
from google.protobuf.message import Message

from . import wireutils
from .const import DELAY_BETWEEN_CONNECTS_SECONDS, OCCUPANCY_MIN_API_VERSION
from .discovery import Service
from .exceptions import DeviceUUIDMismatchError
from .proto import aiobafi6_pb2
from .protoprop import (
    ClosedIntervalValidator,
    OffOnAuto,
    ProtoProp,
    from_proto_humidity,
    from_proto_temperature,
    maybe_proto_field,
    to_proto_temperature,
)

__all__ = (
    "VOLATILE_PROPERTIES",
    "Device",
)

VOLATILE_PROPERTIES = (
    "current_rpm",
    "local_datetime",
    "stats",
    "utc_datetime",
)

_LOGGER = logging.getLogger(__name__)
_MAX_SPEED = 7
_RECV_BUFFER_LIMIT = 4096  # No message is ever expected to be > 4K
_PROPS_REQUIRED_FOR_AVAILABLE = (
    "name",
    "model",
    "firmware_version",
    "mac_address",
    "dns_sd_uuid",
    "capabilities",
    "ip_address",
)


def _clear_volatile_props(props: aiobafi6_pb2.Properties):
    """Clear volatile properties from `props`."""
    for field in VOLATILE_PROPERTIES:
        props.ClearField(field)


class Device:
    """A BAF i6 protocol device.

    The design the of class is relatively simple. Since the protocol is based on
    protofbuf, the majority of a device's state can be stored in a `Properties` message.
    The query loop simply updates this message using `MergeFrom`, with unknown fields
    removed (as they are otherwise treated as repeated fields and would lead to unbound
    memory growth). Synthetic properties expose the protobuf to clients.

    A device must be initialized with a `Service`, either obtained using the `discovery`
    module or manually created. The only required fields are `ip_addresses` and `port`.

    A `Device` object is initially inert. A client must call its `async_run` method to
    connect the device, process state changes and handle device updates. A
    `asyncio.Future` is returned to monitor and stop the device.

    A device has an `available` property which is true when the device is connected and
    has received basic properties from the firmware. The `async_wait_available` coroutine
    can be used to wait for a device to become available (which may never happen).

    If the `uuid` field of the `Service` used to initialize a device is set, the library
    will validate it against the device's `dns_sd_uuid` property after connecting to the
    device and receiving basic properties. If the UUIDs do not match, the device is
    stopped and a `DeviceUUIDMismatchError` exception is set on the run future and raised
    in `async_wait_available` coroutines.

    To disable periodic properties queries, set `query_interval_seconds` to 0.

    Clients can register callbacks to be notified when one or more device properties
    have changed. Callbacks are suppressed when no actual changes are observed (i.e.
    the device is in a steady state). Callbacks are also be suppressed when only
    so-called volatile properties have changed, such as fan RPM, device uptime or the
    device's internal clock. This can be disabled by setting `ignore_volatile_props` to
    False. These properties are still queried and available to read from the device.
    """

    def __init__(
        self,
        service: Service,
        query_interval_seconds: int = 60,
        ignore_volatile_props: bool = True,
        delay_between_connects_seconds: int = DELAY_BETWEEN_CONNECTS_SECONDS,
    ):
        if len(service.ip_addresses) == 0 or service.port == 0:
            raise ValueError(
                f"Invalid service: must have at least one address and a port: {service}"
            )

        self._service = copy.deepcopy(service)
        self._query_interval_seconds = query_interval_seconds
        self._ignore_volatile_props = ignore_volatile_props

        # Permanent Properties protobuf into which query results are merged.
        self._properties = aiobafi6_pb2.Properties()  # pylint: disable=no-member

        # Device update callbacks.
        self._callbacks: list[t.Callable[[Device], None]] = []
        self._coro_callbacks: list[t.Coroutine] = []
        self._dispatch_coro_callback_tasks: t.Set[asyncio.Task] = set()

        # Connection and periodic queries.
        self._loop = asyncio.get_running_loop()
        if self._loop is None:
            raise RuntimeError("no running loop")
        self._run_fut: t.Optional[asyncio.Future] = None
        self._next_connect_ts: float = time.monotonic()
        self._connect_timer: t.Optional[asyncio.TimerHandle] = None
        self._connect_task: t.Optional[asyncio.Task] = None
        self._delay_between_connects_seconds = delay_between_connects_seconds
        self._transport: t.Optional[asyncio.Transport] = None
        self._protocol: t.Optional[Protocol] = None
        self._query_timer: t.Optional[asyncio.TimerHandle] = None

        # Availability.
        self._available_fut: asyncio.Future = self._loop.create_future()

    def __eq__(self, other: t.Any) -> bool:
        if isinstance(other, Device):
            return self.dns_sd_uuid == t.cast(Device, other).dns_sd_uuid
        if isinstance(other, str):
            return other == self.name
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.dns_sd_uuid)

    def __str__(self) -> str:
        string = f"Name: {self.name}"
        string += f", Model: {self.model}"
        string += f", DNS SD UUID: {self.dns_sd_uuid}"
        string += f", IP: {self.ip_address}"
        string += f", MAC: {self.mac_address}"
        if self.firmware_version is not None:
            string += f", Firmware: {self.firmware_version}"
        if self.has_light is not None:
            string += f", Has Light: {self.has_light}"
        return string

    @property
    def service(self) -> Service:  # pylint: disable=missing-function-docstring
        return copy.deepcopy(self._service)

    @property
    def properties_dict(self) -> dict[str, t.Any]:
        """Return a dict created by merging the device's service and properties."""
        propsd = {
            "dns_sd_uuid": self._service.uuid,
            "service_name": self._service.service_name,
            "name": self._service.device_name,
            "model": self._service.model,
            "api_version": self._service.api_version,
            "ip_addresses": self._service.ip_addresses,
            "port": self._service.port,
        }
        propsd.update(
            json_format.MessageToDict(
                t.cast(Message, self._properties), preserving_proto_field_name=True
            )
        )
        return propsd

    @property
    def properties_proto(  # pylint: disable=missing-function-docstring
        self,
    ) -> aiobafi6_pb2.Properties:
        props = aiobafi6_pb2.Properties()  # pylint: disable=no-member
        props.CopyFrom(self._properties)
        return props

    # Client callbacks

    def add_callback(self, callback: t.Callable[[Device], None]) -> None:
        """Add a device update callback.

        The callback must be a `Callable` with a `Device` argument.
        """
        is_coroutine = inspect.iscoroutinefunction(callback)
        if is_coroutine:
            if callback not in self._coro_callbacks:
                self._coro_callbacks.append(callback)  # type: ignore
            _LOGGER.debug("%s: Added coroutine callback.", self.name)
            return
        if callback not in self._callbacks:
            self._callbacks.append(callback)
        _LOGGER.debug("%s: Added function callback.", self.name)

    def remove_callback(self, callback) -> None:
        """Remove a device update callback."""
        if callback in self._coro_callbacks:
            self._coro_callbacks.remove(callback)
            _LOGGER.debug("%s: Removed coroutine callback.", self.name)
            return
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            _LOGGER.debug("%s: Removed function callback.", self.name)
            return

    def _dispatch_callbacks(self) -> None:
        """Dispatch registered device update callbacks.

        An async task is created for coroutine callbacks. Function callbacks are
        executed synchronously inside a try-except block to swallow any error."""
        for callback in self._callbacks:
            try:
                callback(self)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Exception raised during callback.")
        for coro in self._coro_callbacks:
            task = asyncio.create_task(coro(self))  # type: ignore
            self._dispatch_coro_callback_tasks.add(task)
            task.add_done_callback(self._dispatch_coro_callback_tasks.remove)
        _LOGGER.debug(
            "%s: Dispatched %s client callbacks.",
            self.name,
            len(self._callbacks) + len(self._coro_callbacks),
        )

    # protoprop support

    def _maybe_property(self, field: str) -> t.Optional[t.Any]:
        return maybe_proto_field(t.cast(Message, self._properties), field)

    def _commit_property(self, prop: aiobafi6_pb2.Properties) -> None:
        """Commit a property to the device.

        This does not update the properties reflected by the `Device` object. That will
        happen once the device confirms the change by doing a properties push.

        Is it unknown if the firmware generally supports writing more than one property
        in one transaction.
        """
        if self._transport is None:
            _LOGGER.warning(
                "%s: Dropping property commit because device is not connected: %s",
                self.name,
                prop,
            )
            return
        root = aiobafi6_pb2.Root()  # pylint: disable=no-member
        root.root2.commit.properties.CopyFrom(prop)
        _LOGGER.debug("%s: Sending commit:\n%s", self.name, root)
        self._transport.write(wireutils.serialize(root))

    # Connection and query machinery

    def _sched_connect_or_reset(self):
        """Schedule a `_connect` invocation or reset the device to be run again.

        This function is the entrypoint of the internal run state machine. It is called
        when there is no connection (`_start`), when a connection could not be
        established (error or timeout) or the connection has been closed, or when the
        device is stopped (`_stop`)."""
        assert self._connect_timer is None
        assert self._connect_task is None
        assert self._query_timer is None
        assert self._transport is None
        assert self._protocol is None
        assert self._run_fut
        # If the run future is done, then reset it to None and return.
        # `_sched_connect_or_reset` is the entrypoint of the internal run state machine
        # and therefore this is the right place to make the device runnable again (by
        # clearing the run future).
        if self._run_fut.done():
            _LOGGER.debug("%s: Resetting device for new run.", self.name)
            self._run_fut = None
            return
        _LOGGER.debug("%s: Scheduling next connect invocation.", self.name)
        self._connect_timer = self._loop.call_at(
            self._next_connect_ts,
            self._connect,
        )

    def _connect(self) -> None:
        self._connect_timer = None
        self._next_connect_ts = time.monotonic() + self._delay_between_connects_seconds
        _LOGGER.debug(
            "%s: Connecting to %s:%s.",
            self.name,
            self._service.ip_addresses[0],
            self._service.port,
        )
        connect_task = asyncio.create_task(
            self._loop.create_connection(
                lambda: Protocol(self),
                self._service.ip_addresses[0],
                self._service.port,
            )
        )
        connect_task.add_done_callback(self._finish_connect)
        self._loop.call_later(self._delay_between_connects_seconds, connect_task.cancel)
        self._connect_task = connect_task

    def _finish_connect(self, task: asyncio.Task) -> None:
        assert self._connect_task is task
        self._connect_task = None
        try:
            transport, protocol = task.result()
            _LOGGER.debug(
                "%s: Connected to %s.", self.name, transport.get_extra_info("peername")
            )
            self._transport = transport
            self._protocol = protocol
            self._loop.call_soon(self._query)
        except (OSError, asyncio.CancelledError) as err:
            _LOGGER.debug("%s: Connection failed: %s", self.name, err)
            self._sched_connect_or_reset()

    def _handle_connection_lost(self, exc: t.Optional[Exception]) -> None:
        _LOGGER.debug("%s: Connection lost: %s", self.name, exc)
        if self._query_timer is not None:
            self._query_timer.cancel()
            self._query_timer = None
        self._transport = None
        self._protocol = None
        self._sched_connect_or_reset()

    def _process_message(self, data: bytes) -> None:
        root = aiobafi6_pb2.Root()  # pylint: disable=no-member
        root.ParseFromString(data)
        _LOGGER.debug("%s: Received message: %s", self.name, root)
        # Discard unknown fields because `MergeFrom` treats them as repeated.
        root.DiscardUnknownFields()  # type: ignore
        previous = self.properties_proto
        for prop in root.root2.query_result.properties:
            self._properties.MergeFrom(prop)
        if not self.available:
            self._maybe_set_available()
        current = self.properties_proto
        if self._ignore_volatile_props:
            _clear_volatile_props(previous)
            _clear_volatile_props(current)
        if self.available and current != previous:
            self._dispatch_callbacks()

    def _maybe_set_available(self):
        """Set the device as available if all required properties are set."""
        for pname in _PROPS_REQUIRED_FOR_AVAILABLE:
            if not self._properties.HasField(pname):
                return
        if self._service.uuid is not None and self._service.uuid != self.dns_sd_uuid:
            _LOGGER.error(
                "%s: Device UUID (%s) does not match service UUID (%s): stopping.",
                self.name,
                self.dns_sd_uuid,
                self._service.uuid,
            )
            assert self._run_fut
            if not self._run_fut.done():
                self._run_fut.set_exception(DeviceUUIDMismatchError)
            return
        _LOGGER.debug("%s: Setting device as available.", self.name)
        self._available_fut.set_result(True)

    def _query(self) -> None:
        self._query_timer = None
        # The first `_query` of a connection is scheduled with `call_soon` and can't
        # be cancelled, so it's possible (though unlikely) for `_transport` to be None.
        # If that's the case, just bail out.
        if self._transport is None:
            return
        root = aiobafi6_pb2.Root()  # pylint: disable=no-member
        root.root2.query.property_query = aiobafi6_pb2.ALL  # pylint: disable=no-member
        _LOGGER.debug("%s: Sending query:\n%s", self.name, root)
        self._transport.write(wireutils.serialize(root))
        if self._query_interval_seconds > 0:
            self._query_timer = self._loop.call_later(
                self._query_interval_seconds, self._query
            )

    def async_run(self) -> asyncio.Future:
        """Run the device asynchronously.

        A running `Device` schedules functions on the run loop to maintain a connection
        to the device, sends periodic property queries, and services query commits.

        Returns a future that will resolve when the device stops. Cancelling this future
        will stop the device.
        """
        if self._run_fut is None:
            self._start()
        assert self._run_fut is not None
        return self._run_fut

    def _start(self):
        """Start the device.

        This function schedules the device to connect on the next run loop iteration.
        From there on, the device will continue scheduling functions to maintain the
        connection, send periodic property queries, and service query commits.
        """
        assert self._run_fut is None
        _LOGGER.debug("%s: Starting.", self.name)
        self._run_fut = self._loop.create_future()

        def stop_on_done(_: asyncio.Future):
            self._stop()

        self._run_fut.add_done_callback(stop_on_done)
        self._sched_connect_or_reset()

    def _stop(self) -> None:
        """Stop the device.

        This function ultimately causes `_sched_connect_or_reset` to be called by
        cancelling the appropriate in-flight task.

        This function also creates a new available future, thus marking the device as
        unavailable. If the run future became done because of an exception or because
        it was cancelled, that is propagated to the prior available future. Otherwise,
        the prior available future is never signalled."""
        _LOGGER.debug("%s: Stopping.", self.name)
        # Propagate run exception or cancellation to the available future, then reset it
        # to set the device as unavailable.
        assert self._run_fut
        if self._run_fut.cancelled():
            self._available_fut.cancel()
        else:
            run_exc = self._run_fut.exception()
            if run_exc is not None:
                self._available_fut.set_exception(run_exc)
        self._available_fut = self._loop.create_future()
        # Dispatch client callbacks, since some clients may observe the `available`
        # property through a callback.
        self._dispatch_callbacks()
        # If there is an active connection, close it.
        if self._transport is not None:
            self._transport.close()
        # Otherwise, if the device is opening a connection, cancel that.
        elif self._connect_task is not None:
            self._connect_task.cancel()
        # Otherwise, if `_connect` is scheduled, cancel that and call
        # `_sched_connect_or_reset` directly because nothing else will.
        elif self._connect_timer is not None:
            self._connect_timer.cancel()
            self._connect_timer = None
            self._sched_connect_or_reset()

    # Availability

    @property
    def available(self) -> bool:
        """Return True when device is running and has values for critical properties."""
        available_fut = self._available_fut
        return available_fut.done() and not available_fut.exception()

    async def async_wait_available(self) -> None:
        """Asynchronously wait for the device to be available."""
        await self._available_fut

    # General

    @property
    def name(self) -> str:  # pylint: disable=missing-function-docstring
        if len(self._properties.name) > 0:
            return self._properties.name
        if (
            self._service.service_name is not None
            and len(self._service.service_name) > 0
        ):
            return self._service.service_name
        if len(self._properties.mac_address) > 0:
            return self._properties.mac_address
        return self._service.ip_addresses[0]

    @property
    def model(self) -> t.Optional[str]:  # pylint: disable=missing-function-docstring
        if len(self._properties.model) > 0:
            return self._properties.model
        return self._service.model

    firmware_version = ProtoProp[t.Optional[str]]()
    mac_address = ProtoProp[t.Optional[str]]()

    # API

    @property
    def dns_sd_uuid(  # pylint: disable=missing-function-docstring
        self,
    ) -> t.Optional[str]:
        if len(self._properties.dns_sd_uuid) > 0:
            return self._properties.dns_sd_uuid
        return self._service.uuid

    @property
    def api_version(  # pylint: disable=missing-function-docstring
        self,
    ) -> t.Optional[str]:
        if len(self._properties.api_version) > 0:
            return self._properties.api_version
        return self._service.api_version

    @property
    def has_fan(self) -> bool:  # pylint: disable=missing-function-docstring
        # TODO(#1): Support light-only devices.
        return True

    @property
    def has_light(  # pylint: disable=missing-function-docstring
        self,
    ) -> t.Optional[bool]:
        return maybe_proto_field(self._properties.capabilities, "has_light")

    @property
    def has_auto_comfort(self) -> bool:  # pylint: disable=missing-function-docstring
        # https://github.com/home-assistant/core/issues/72934
        hc1 = maybe_proto_field(self._properties.capabilities, "has_comfort1") or False
        hc3 = maybe_proto_field(self._properties.capabilities, "has_comfort3") or False
        return hc1 and hc3

    @property
    def has_occupancy(self) -> bool:  # pylint: disable=missing-function-docstring
        try:
            api_version = int(self.api_version or 0)
        except ValueError:
            api_version = 0
        # There is probably a capability flag for this but it is unknown. Speculatively,
        # a device that supports auto comfort is assumed to supports occupancy.
        return api_version >= OCCUPANCY_MIN_API_VERSION and self.has_auto_comfort

    # Fan

    # pylint: disable=unnecessary-lambda
    fan_mode = ProtoProp[OffOnAuto](writable=True, from_proto=lambda v: OffOnAuto(v))
    reverse_enable = ProtoProp[bool](writable=True)
    speed_percent = ProtoProp[int]()
    speed = ProtoProp[int](
        writable=True, to_proto=ClosedIntervalValidator[int](0, _MAX_SPEED)
    )

    whoosh_enable = ProtoProp[bool](writable=True)
    eco_enable = ProtoProp[bool](writable=True)

    auto_comfort_enable = ProtoProp[bool](writable=True)
    comfort_ideal_temperature = ProtoProp[float](
        writable=True,
        to_proto=to_proto_temperature,
        from_proto=from_proto_temperature,
    )
    comfort_heat_assist_enable = ProtoProp[bool](writable=True)
    comfort_heat_assist_speed = ProtoProp[int](writable=True)
    comfort_heat_assist_reverse_enable = ProtoProp[bool](writable=True)
    comfort_min_speed = ProtoProp[int](
        writable=True, to_proto=ClosedIntervalValidator[int](0, _MAX_SPEED)
    )
    comfort_max_speed = ProtoProp[int](
        writable=True, to_proto=ClosedIntervalValidator[int](0, _MAX_SPEED)
    )

    motion_sense_enable = ProtoProp[bool](writable=True)
    motion_sense_timeout = ProtoProp[int](writable=True)

    return_to_auto_enable = ProtoProp[bool](writable=True)
    return_to_auto_timeout = ProtoProp[int](writable=True)

    target_rpm = ProtoProp[int]()
    current_rpm = ProtoProp[int]()

    fan_occupancy_detected = ProtoProp[bool](min_api_version=OCCUPANCY_MIN_API_VERSION)

    # Light

    # pylint: disable=unnecessary-lambda
    light_mode = ProtoProp[OffOnAuto](writable=True, from_proto=lambda v: OffOnAuto(v))
    light_brightness_percent = ProtoProp[int](writable=True)
    light_brightness_level = ProtoProp[int](writable=True)
    light_color_temperature = ProtoProp[int](writable=True)

    light_dim_to_warm_enable = ProtoProp[bool](writable=True)

    light_auto_motion_timeout = ProtoProp[int](writable=True)

    light_return_to_auto_enable = ProtoProp[bool](writable=True)
    light_return_to_auto_timeout = ProtoProp[int](writable=True)

    light_warmest_color_temperature = ProtoProp[int]()
    light_coolest_color_temperature = ProtoProp[int]()

    light_occupancy_detected = ProtoProp[bool](
        min_api_version=OCCUPANCY_MIN_API_VERSION
    )

    # Sensors

    temperature = ProtoProp[float](
        to_proto=to_proto_temperature,
        from_proto=from_proto_temperature,
    )
    humidity = ProtoProp[int](from_proto=from_proto_humidity)

    # Connectivity

    @property
    def ip_address(self) -> str:  # pylint: disable=missing-function-docstring
        if len(self._properties.ip_address) > 0:
            return self._properties.ip_address
        return self._service.ip_addresses[0]

    @property
    def wifi_ssid(  # pylint: disable=missing-function-docstring
        self,
    ) -> t.Optional[str]:
        return maybe_proto_field(self._properties.wifi, "ssid")

    # More

    led_indicators_enable = ProtoProp[bool](writable=True)
    fan_beep_enable = ProtoProp[bool](writable=True)
    legacy_ir_remote_enable = ProtoProp[bool](writable=True)


class Protocol(asyncio.Protocol):
    """AsyncIO Protocol for BAF i6."""

    __slots__ = ("_device", "_transport", "_buffer")

    def __init__(self, device: Device):
        self._device = device
        self._transport: t.Optional[asyncio.Transport] = None
        self._buffer = bytearray()

    def connection_made(self, transport: asyncio.Transport) -> None:
        self._transport = transport

    def connection_lost(self, exc: t.Optional[Exception]) -> None:
        self._device._handle_connection_lost(exc)  # pylint: disable=protected-access
        self._transport = None

    def data_received(self, data: bytes) -> None:
        assert self._transport is not None
        if len(self._buffer) + len(data) > _RECV_BUFFER_LIMIT:
            raise RuntimeError("Exceeded buffering limit.")
        self._buffer.extend(data)
        while len(self._buffer) > 1:
            if self._buffer[0] != 0xC0:
                _LOGGER.error("Receive buffer does not start with sync byte.")
                self._transport.abort()
                break
            end = self._buffer.find(0xC0, 1)
            if end == -1:
                break
            if end == 1:
                _LOGGER.error("Empty message found in receive buffer.")
                self._transport.abort()
                break
            self._device._process_message(  # pylint: disable=protected-access
                wireutils.remove_emulation_prevention(self._buffer[1:end])
            )
            self._buffer = self._buffer[end + 1 :]
