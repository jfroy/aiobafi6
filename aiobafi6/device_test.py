"""Tests for device."""

import pytest

from .device import Device
from .discovery import PORT, Service


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
