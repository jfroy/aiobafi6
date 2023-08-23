"""aiobafi6"""

from .const import MIN_API_VERSION
from .device import Device
from .discovery import PORT, ZEROCONF_SERVICE_TYPE, Service, ServiceBrowser
from .exceptions import DeviceUUIDMismatchError
from .protoprop import OffOnAuto

__all__ = (
    "MIN_API_VERSION",
    "PORT",
    "ZEROCONF_SERVICE_TYPE",
    "Device",
    "DeviceUUIDMismatchError",
    "OffOnAuto",
    "Service",
    "ServiceBrowser",
)
