"""Exceptions."""
from __future__ import annotations


class Error(Exception):
    """Base class for aiobafi6 errors."""


class DeviceUUIDMismatchError(Error):
    """Raised if init service UUID does not match the device UUID."""
