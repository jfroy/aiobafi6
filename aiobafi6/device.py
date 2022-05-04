"""aiobafi6 device.

Provides functionality to query and control BAF i6 protocol devices.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import time
import typing as t
from enum import IntEnum

from google.protobuf import json_format
from google.protobuf.message import Message

from . import wireutils
from .discovery import Service
from .proto import aiobafi6_pb2
from .protoprop import (
    ClosedIntervalValidator,
    ProtoProp,
    from_proto_humidity,
    from_proto_temperature,
    to_proto_temperature,
)

__all__ = ("OffOnAuto", "Device")

_LOGGER = logging.getLogger(__name__)
_DELAY_BETWEEN_CONNECT_ATTEMPTS = 5
_MAX_SPEED = 7


class OffOnAuto(IntEnum):
    """Tri-state mode enum that matches the protocol buffer."""

    OFF = 0
    ON = 1
    AUTO = 3


class Device:
    """A connected BAF i6 protocol device.

    The design the of class is relatively simple. Since the protocol is based on
    protofbuf, the majority of a device's state can be stored in a `Properties` message.
    The query loop simply updates this message using `MergeFrom`, with unknown fields
    removed (as they are otherwise treated as repeated fields and would lead to unbound
    memory growth). Synthetic properties expose the protobuf to clients.

    A device must be initialized with a `Service`, either obtained using the `discovery`
    module or manually created. The only required fields are at least an address and a
    port.

    A `Device` object is initially inert. A client must called its `run` method to
    create an `asyncio.Task` that will maintain a connection to the device and service
    properties queries, pushes, and commits.

    To disable periodic properties queries, set `query_interval_seconds` to 0.
    """

    def __init__(
        self,
        service: Service,
        query_interval_seconds: int = 60,
    ):
        if len(service.ip_addresses) == 0 or service.port == 0:
            raise ValueError(
                f"Invalid service: must have at least one address and a port: {service}"
            )

        self.query_interval_seconds = query_interval_seconds
        self.service = service

        # Permanent Properties protobuf into which query results are merged.
        self._properties = aiobafi6_pb2.Properties()

        # Device update callbacks.
        self._callbacks: list[t.Callable[[Device], None]] = []
        self._coro_callbacks: list[t.Coroutine] = []
        self._dispatch_coro_callback_tasks: t.Set[asyncio.Task] = set()

        # Run task and connection. See `run`.
        self._run_task: t.Optional[asyncio.Task] = None
        self._connection: t.Optional[
            tuple[asyncio.StreamReader, asyncio.StreamWriter]
        ] = None

        # Events that track if the device is connected and has received a "full" query
        # result set. See `async_wait_available`.
        self._is_connected_event = asyncio.Event()
        self._first_query_done_event = asyncio.Event()

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

    def _maybe_prop(self, field: str) -> t.Optional[t.Any]:
        return maybe_proto_field(t.cast(Message, self._properties), field)

    @property
    def properties_dict(self) -> dict[str, t.Any]:
        """Return a dict created by merging the device's service and properties."""
        d = {
            "dns_sd_uuid": self.service.uuid,
            "service_name": self.service.service_name,
            "name": self.service.device_name,
            "model": self.service.model,
            "api_version": self.service.api_version,
            "ip_addresses": self.service.ip_addresses,
            "port": self.service.port,
        }
        d.update(
            json_format.MessageToDict(
                t.cast(Message, self._properties), preserving_proto_field_name=True
            )
        )
        return d

    @property
    def properties_proto(self) -> aiobafi6_pb2.Properties:
        p = aiobafi6_pb2.Properties()
        p.CopyFrom(self._properties)
        return p

    def add_callback(self, callback: t.Callable[[Device], None]) -> None:
        """Add a device update callback.

        The callback must be a `Callable` with a `Device` argument.
        """
        is_coroutine = inspect.iscoroutinefunction(callback)
        if is_coroutine:
            if callback not in self._coro_callbacks:
                self._coro_callbacks.append(callback)  # type: ignore
            _LOGGER.debug(f"{self.name}: Added coroutine callback.")
            return
        if callback not in self._callbacks:
            self._callbacks.append(callback)
        _LOGGER.debug(f"{self.name}: Added function callback.")

    def remove_callback(self, callback) -> None:
        """Remove a device update callback."""
        if callback in self._coro_callbacks:
            self._coro_callbacks.remove(callback)
            _LOGGER.debug(f"{self.name}: Removed coroutine callback.")
            return
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            _LOGGER.debug(f"{self.name}: Removed function callback.")
            return

    def _dispatch_callbacks(self) -> None:
        """Dispatch registered device update callbacks.

        An async task is created for coroutine callbacks. Function callbacks are
        executed synchronously. For function callbacks, each invocation is done inside
        a try-except block to swallow any error."""
        for callback in self._callbacks:
            try:
                callback(self)
            except Exception:
                _LOGGER.exception("Exception raised during callback.")
        for coro in self._coro_callbacks:
            t = asyncio.create_task(coro(self))  # type: ignore
            self._dispatch_coro_callback_tasks.add(t)
            t.add_done_callback(lambda t: self._dispatch_coro_callback_tasks.remove(t))
        _LOGGER.debug(
            f"{self.name}: Dispatched {len(self._callbacks) + len(self._coro_callbacks)} client callbacks."
        )

    def _commit_property(self, p: aiobafi6_pb2.Properties) -> None:
        """Commit a property to the device.

        This does not update the properties reflected by the `Device` object. That will
        happen once the device confirms the change by doing a properties push.

        Is it unknown if the firmware generally supports writing more than one property
        in one transaction.
        """
        if self._connection is None:
            _LOGGER.warning(
                f"{self.name}: Dropping property commit because device is not connected: {p}"
            )
            return
        root = aiobafi6_pb2.Root()
        root.root2.commit.properties.CopyFrom(p)
        _LOGGER.debug(f"{self.name}: Sending commit:\n{root}")
        self._connection[1].write(wireutils.serialize(root))

    async def _async_run_loop(self) -> None:
        """Run a loop that maintains a connection and monitors other loops.

        This function loops until `run_task` is cancelled. Every loop consists of the
        following steps:

            - Connect to the device. If that fails, start over.
            - Spawn `_async_read_loop` as a task.
            - Spawn `_async_query_loop` as a task.
            - Await the above 2 tasks, returning on the first exception.

        Every time through the loop, the loop tasks are canceled and the connection
        reset. This ensures that if a connection or loop probem happens, everything gets
        torn down and re-started.
        """
        _LOGGER.debug(f"{self.name}: Starting run loop.")
        next_connect_ts = time.monotonic() - _DELAY_BETWEEN_CONNECT_ATTEMPTS
        read_task: t.Optional[asyncio.Task] = None
        query_task: t.Optional[asyncio.Task] = None
        try:
            while True:
                try:
                    # Connect to the device, potentially after a delay to avoid banging
                    # on an unresponsive of invalid address.
                    delay = next_connect_ts - time.monotonic()
                    if delay > 0:
                        await asyncio.sleep(delay)
                    next_connect_ts = time.monotonic() + _DELAY_BETWEEN_CONNECT_ATTEMPTS
                    _LOGGER.debug(
                        f"{self.name}: Connecting to {self.service.ip_addresses[0]}:{self.service.port}."
                    )
                    assert self._connection is None
                    self._connection = await asyncio.wait_for(
                        asyncio.open_connection(
                            self.service.ip_addresses[0], self.service.port
                        ),
                        timeout=_DELAY_BETWEEN_CONNECT_ATTEMPTS,
                    )
                    _LOGGER.debug(f"{self.name}: Connected.")
                    self._is_connected_event.set()

                    # Spawn a reader and query task for the connection.
                    assert read_task is None
                    read_task = asyncio.create_task(self._async_read_loop())
                    assert query_task is None
                    query_task = asyncio.create_task(self._async_query_loop())

                    # Wait until both tasks are done, indicating the connection closed.
                    await asyncio.wait(
                        (read_task, query_task), return_when=asyncio.FIRST_EXCEPTION
                    )
                except asyncio.TimeoutError:
                    _LOGGER.debug(f"{self.name}: Timeout in the run loop.")
                except OSError as err:
                    _LOGGER.debug(f"{self.name}: OS error in the run loop: {err}")
                finally:
                    _LOGGER.debug(
                        f"{self.name}: Resetting run loop tasks and connection."
                    )
                    if read_task is not None:
                        read_task.cancel()
                        read_task = None
                    if query_task is not None:
                        query_task.cancel()
                        query_task = None
                    if self._connection is not None:
                        self._connection[1].close()
                        await self._connection[1].wait_closed()
                        self._connection = None
                        # Dispatch callbacks so clients become aware the device is no
                        # longer connected.
                        self._is_connected_event.clear()
                        self._dispatch_callbacks()
        except asyncio.CancelledError:
            _LOGGER.debug(f"{self.name}: Run loop was cancelled.")
        except Exception:
            _LOGGER.exception(f"{self.name}: Unknown error in the run loop.")
            raise
        finally:
            _LOGGER.debug(f"{self.name}: Exiting run loop.")
            self._run_task = None

    async def _async_read_loop(self) -> None:
        """Run a loop that reads messages from the connection."""
        _LOGGER.debug(f"{self.name}: Starting read loop.")
        dispatch_task: t.Optional[asyncio.Task] = None
        try:
            while True:
                if self._connection is None:
                    break
                # The wire format frames messages with 0xc0, so the first `readuntil`
                # will return just that byte and the next will return the message with
                # the terminating byte.
                #
                # The socket setup by asyncio takes a really long time to detect broken
                # connections on Linux. So explicitly use `wait_for` with twice the
                # query interval as the read timeout.
                raw_buf = await asyncio.wait_for(
                    self._connection[0].readuntil(b"\xc0"),
                    self.query_interval_seconds * 2
                    if self.query_interval_seconds > 0
                    else None,
                )
                if len(raw_buf) == 1:
                    continue
                buf = wireutils.remove_emulation_prevention(raw_buf[:-1])
                root = aiobafi6_pb2.Root()
                root.ParseFromString(buf)
                # Discard unknown fields because `MergeFrom` treats them as repeated.
                root.DiscardUnknownFields()  # type: ignore
                for p in root.root2.query_result.properties:
                    self._properties.MergeFrom(p)
                # A query can yield one or more result messages, so wait for the reader
                # to idle to avoid a callback storm.

                async def dispatch_after(delay: float) -> None:
                    await asyncio.sleep(delay)
                    # Allow futures waiting on `async_wait_available` to fire before
                    # dispatching callbacks.
                    if not self._first_query_done_event.is_set():
                        self._first_query_done_event.set()
                        await asyncio.sleep(0)
                    self._dispatch_callbacks()

                if dispatch_task is not None:
                    dispatch_task.cancel()
                dispatch_task = asyncio.create_task(dispatch_after(0.2))
        except asyncio.CancelledError:
            _LOGGER.debug(f"{self.name}: Read loop was cancelled.")
        except asyncio.TimeoutError:
            _LOGGER.debug(f"{self.name}: Timeout in the read loop.")
            raise
        except OSError as err:
            _LOGGER.debug(f"{self.name}: OS error in the read loop: {err}")
            raise
        except Exception:
            _LOGGER.exception(f"{self.name}: Unknown error in the read loop.")
            raise
        finally:
            _LOGGER.debug(f"{self.name}: Exiting read loop.")

    async def _async_query_loop(self) -> None:
        """Run a loop that sends a ALL properties query periodically."""
        _LOGGER.debug(f"{self.name}: Starting query loop.")
        one_query_sent = False
        try:
            while True:
                if self._connection is None:
                    break
                if self.query_interval_seconds <= 0 and one_query_sent:
                    await asyncio.sleep(1)
                    continue
                root = aiobafi6_pb2.Root()
                root.root2.query.property_query = aiobafi6_pb2.ALL
                _LOGGER.debug(f"{self.name}: Sending query:\n{root}")
                self._connection[1].write(wireutils.serialize(root))
                one_query_sent = True
                await self._connection[1].drain()
                await asyncio.sleep(self.query_interval_seconds)
        except asyncio.CancelledError:
            _LOGGER.debug(f"{self.name}: Query loop was cancelled.")
        except asyncio.TimeoutError:
            _LOGGER.debug(f"{self.name}: Timeout in the query loop.")
            raise
        except OSError as err:
            _LOGGER.debug(f"{self.name}: OS error in the query loop: {err}")
            raise
        except Exception:
            _LOGGER.exception(f"{self.name}: Unknown error in the query loop.")
            raise
        finally:
            _LOGGER.debug(f"{self.name}: Exiting query loop.")

    def run(self) -> asyncio.Task:
        """Run the device.

        Creates an asyncio task (if needed) that maintains a connection to the device
        and services property pushes, periodic property queries, and property commits.
        The task is stored in the `run_task` property and is returned to the caller.
        """
        if self._run_task is not None:
            return self._run_task
        self._run_task = asyncio.create_task(self._async_run_loop())
        return self._run_task

    @property
    def run_task(self) -> t.Optional[asyncio.Task]:
        return self._run_task

    @property
    def available(self) -> bool:
        """Return True when device is connected and an property query has finished."""
        return (
            self._is_connected_event.is_set() and self._first_query_done_event.is_set()
        )

    async def async_wait_available(self) -> None:
        """t.Coroutine that waits for the device to be available."""
        await self._is_connected_event.wait()
        await self._first_query_done_event.wait()

    # General

    @property
    def name(self) -> str:
        if len(self._properties.name) > 0:
            return self._properties.name
        if len(self._properties.mac_address) > 0:
            return self._properties.mac_address
        if self.service.device_name is not None and len(self.service.device_name) > 0:
            return self.service.device_name
        return self.service.ip_addresses[0]

    @property
    def model(self) -> t.Optional[str]:
        if len(self._properties.model) > 0:
            return self._properties.model
        return self.service.model

    firmware_version = ProtoProp[t.Optional[str]]()
    mac_address = ProtoProp[t.Optional[str]]()

    # API

    @property
    def dns_sd_uuid(self) -> t.Optional[str]:
        if len(self._properties.dns_sd_uuid) > 0:
            return self._properties.dns_sd_uuid
        return self.service.uuid

    @property
    def has_fan(self) -> bool:
        # TODO(!xxx): Support light-only devices.
        return True

    @property
    def has_light(self) -> t.Optional[bool]:
        return maybe_proto_field(self._properties.capabilities, "has_light")

    # Fan

    fan_mode = ProtoProp[OffOnAuto](writable=True)
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

    # Light

    light_mode = ProtoProp[OffOnAuto](writable=True)
    light_brightness_percent = ProtoProp[int](writable=True)
    light_brightness_level = ProtoProp[int](writable=True)
    light_color_temperature = ProtoProp[int](writable=True)

    light_dim_to_warm_enable = ProtoProp[bool](writable=True)

    light_auto_motion_timeout = ProtoProp[int](writable=True)

    light_return_to_auto_enable = ProtoProp[bool](writable=True)
    light_return_to_auto_timeout = ProtoProp[int](writable=True)

    light_warmest_color_temperature = ProtoProp[int]()
    light_coolest_color_temperature = ProtoProp[int]()

    # Sensors

    temperature = ProtoProp[float](
        to_proto=to_proto_temperature,
        from_proto=from_proto_temperature,
    )
    humidity = ProtoProp[int](from_proto=from_proto_humidity)

    # Connectivity

    @property
    def ip_address(self) -> str:
        if len(self._properties.ip_address) > 0:
            return self._properties.ip_address
        return self.service.ip_addresses[0]

    @property
    def wifi_ssid(self) -> t.Optional[str]:
        return maybe_proto_field(self._properties.wifi, "ssid")

    # More

    led_indicators_enable = ProtoProp[bool](writable=True)
    fan_beep_enable = ProtoProp[bool](writable=True)
    legacy_ir_remote_enable = ProtoProp[bool](writable=True)


def maybe_proto_field(message: Message, field: str) -> t.Optional[t.Any]:
    """Returns the value of `field` in `message` or `None` if not set."""
    return getattr(message, field) if message.HasField(field) else None
