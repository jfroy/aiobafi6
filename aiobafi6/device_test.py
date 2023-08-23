# pylint: disable=protected-access, missing-class-docstring, missing-function-docstring, invalid-name

"""Tests for device."""

from __future__ import annotations

import asyncio
import typing as t

import pytest

from .device import Device
from .discovery import PORT, Service
from .exceptions import DeviceUUIDMismatchError
from .proto import aiobafi6_pb2


@pytest.mark.asyncio
async def test_device_init_copies_service():
    s = Service(("127.0.0.1",), PORT)
    d = Device(s)
    assert s == d._service
    s.ip_addresses = ("127.0.0.2",)
    assert d._service.ip_addresses == ("127.0.0.1",)


@pytest.mark.asyncio
async def test_service_property_copies():
    d = Device(Service(("127.0.0.1",), PORT))
    s = d.service
    assert s == d._service
    s.ip_addresses = ("127.0.0.2",)
    assert d._service.ip_addresses == ("127.0.0.1",)


@pytest.mark.asyncio
async def test_service_property_read_only():
    d = Device(Service(("127.0.0.1",), PORT))
    with pytest.raises(AttributeError):
        d.service = Service(("127.0.0.2",), PORT)  # type: ignore


@pytest.mark.asyncio
async def test_has_auto_comfort():
    d = Device(Service(("127.0.0.1",), PORT))
    assert not d.has_auto_comfort

    d._properties.capabilities.has_comfort1 = False
    assert not d.has_auto_comfort

    d._properties.capabilities.ClearField("has_comfort1")
    d._properties.capabilities.has_comfort3 = False
    assert not d.has_auto_comfort

    d._properties.capabilities.has_comfort1 = False
    d._properties.capabilities.has_comfort3 = False
    assert not d.has_auto_comfort

    d._properties.capabilities.ClearField("has_comfort3")
    d._properties.capabilities.has_comfort1 = True
    assert not d.has_auto_comfort

    d._properties.capabilities.ClearField("has_comfort1")
    d._properties.capabilities.has_comfort3 = True
    assert not d.has_auto_comfort

    d._properties.capabilities.has_comfort1 = True
    d._properties.capabilities.has_comfort3 = True
    assert d.has_auto_comfort


@pytest.mark.asyncio
async def test_no_redundant_callback():
    d = Device(Service(("127.0.0.1",), PORT))
    d._available_fut.set_result(True)
    called = False

    def callback(_: Device):
        nonlocal called
        called = True

    d.add_callback(callback)
    root = aiobafi6_pb2.Root()  # pylint: disable=no-member
    prop = root.root2.query_result.properties.add()
    prop.speed = 1
    buf = root.SerializeToString()
    d._process_message(buf)
    assert d._properties.speed == 1
    assert called
    called = False
    d._process_message(buf)
    assert not called


@pytest.mark.asyncio
async def test_ignore_volatile_props():
    d = Device(Service(("127.0.0.1",), PORT), ignore_volatile_props=True)
    d._available_fut.set_result(True)
    called = False

    def callback(_: Device):
        nonlocal called
        called = True

    d.add_callback(callback)
    root = aiobafi6_pb2.Root()  # pylint: disable=no-member
    prop = root.root2.query_result.properties.add()
    prop.current_rpm = 42
    buf = root.SerializeToString()
    d._process_message(buf)
    assert d._properties.current_rpm == 42
    assert not called


@pytest.mark.asyncio
async def test_no_ignore_volatile_props():
    d = Device(Service(("127.0.0.1",), PORT), ignore_volatile_props=False)
    d._available_fut.set_result(True)
    called = False

    def callback(_: Device):
        nonlocal called
        called = True

    d.add_callback(callback)
    root = aiobafi6_pb2.Root()  # pylint: disable=no-member
    prop = root.root2.query_result.properties.add()
    prop.current_rpm = 42
    buf = root.SerializeToString()
    d._process_message(buf)
    assert d._properties.current_rpm == 42
    assert called


@pytest.mark.asyncio
async def test_cancel_between_connect_attempt():
    d = Device(
        Service(("127.0.0.1",), PORT),
        ignore_volatile_props=False,
        delay_between_connects_seconds=1,
    )
    except_context: t.Optional[dict[str, t.Any]] = None

    def exception_handler(_: t.Any, context: dict[str, t.Any]) -> None:
        nonlocal except_context
        except_context = context

    def cancel_fut(fut: asyncio.Future):
        fut.cancel()

    run_fut = d.async_run()
    loop = run_fut.get_loop()
    loop.set_exception_handler(exception_handler)
    loop.call_later(1.5, cancel_fut, run_fut)
    with pytest.raises(asyncio.CancelledError):
        await run_fut
    assert except_context is None
    run_fut = d.async_run()
    loop.call_later(1.5, cancel_fut, run_fut)
    with pytest.raises(asyncio.CancelledError):
        await d.async_wait_available()


@pytest.mark.asyncio
async def test_uuid_mismatch():
    d = Device(
        Service(("127.0.0.1",), PORT, uuid="A"),
        ignore_volatile_props=False,
        delay_between_connects_seconds=1,
    )
    run_fut = d.async_run()
    avail_fut = d.async_wait_available()
    root = aiobafi6_pb2.Root()  # pylint: disable=no-member
    prop = root.root2.query_result.properties.add()
    prop.name = "name"
    prop.model = "model"
    prop.firmware_version = "firmware_version"
    prop.mac_address = "mac_address"
    prop.dns_sd_uuid = "B"
    prop.capabilities.SetInParent()
    prop.ip_address = "ip_address"
    buf = root.SerializeToString()
    d._process_message(buf)
    with pytest.raises(DeviceUUIDMismatchError):
        await run_fut
    with pytest.raises(DeviceUUIDMismatchError):
        await avail_fut
