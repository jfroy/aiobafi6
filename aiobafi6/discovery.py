"""aiobafi6 discovery.

Provides functionality to discover BAF i6 API services.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Sequence, Set, Tuple

from zeroconf import ServiceStateChange, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo

__all__ = ("PORT", "ZEROCONF_SERVICE_TYPE", "Service", "ServiceBrowser")

_LOGGER = logging.getLogger(__name__)

"""Default service API port number. Only use to manually create a `Service` object."""
PORT = 31415

"""Zeroconf service type for BAF API DNS service discovery."""
ZEROCONF_SERVICE_TYPE = "_api._tcp.local."


@dataclass
class Service:
    """Represents a BAF i6 API service.

    A service is uniquely identified by a device UUID and provides a device name, model
    name, and API endpoints (address:port).

    A Device object can be created using a Service object.
    """

    ip_addresses: Tuple[str]
    port: int
    uuid: Optional[str] = None
    service_name: Optional[str] = None
    device_name: Optional[str] = None
    model: Optional[str] = None
    api_version: Optional[str] = None

    def __init__(
        self,
        ip_addresses: Sequence[str],
        port: int,
        uuid: Optional[str] = None,
        service_name: Optional[str] = None,
        device_name: Optional[str] = None,
        model: Optional[str] = None,
        api_version: Optional[str] = None,
    ):
        self.ip_addresses = tuple(ip for ip in ip_addresses)
        self.port = port
        self.uuid = uuid
        self.service_name = service_name
        self.device_name = device_name
        self.model = model
        self.api_version = api_version


class ServiceBrowser:
    """Discovers BAF i6 API services.

    This class manages a `AsyncServiceBrowser` bound to a provided `Zeroconf` object
    to discover BAF i6 API services. The browser will call `callback` with a tuple of
    `Service` objects whenever the browser detects a change in service availability.
    """

    def __init__(self, zc: Zeroconf, callback: Callable):
        self._callback = callback

        # Map device UUID to Service object. When a device is renamed, the service
        # record with the old name won't be removed until a TTL expires, so the
        # service/device name is not a good key.
        self._service_map: Dict[str, Service] = {}

        # Set of outstanding tasks spawned from the service browser.
        self._tasks: Set[asyncio.Task] = set()

        self._asb = AsyncServiceBrowser(
            zc, ["_api._tcp.local."], handlers=[self._on_state_change]
        )

    def _dispatch_callback(self) -> None:
        services = tuple(s for s in self._service_map.values())
        if inspect.iscoroutinefunction(self._callback):
            t = asyncio.create_task(self._callback(services))
            self._tasks.add(t)
            t.add_done_callback(lambda t: self._tasks.remove(t))
        else:
            self._callback(services)

    async def _async_resolve_service(
        self, zeroconf: Zeroconf, service_type: str, service_name: str
    ) -> None:
        info = AsyncServiceInfo(service_type, service_name)
        if not await info.async_request(zeroconf, 3000):
            _LOGGER.info(f"Failed to resolve service {service_name}.")
            return
        if info.properties is None:
            _LOGGER.info(f"Service {service_name} has no properties.")
            return
        if len(info.addresses) == 0:
            _LOGGER.info(f"Service {service_name} has no addresses.")
            return
        if info.port is None:
            _LOGGER.info(f"Service {service_name} has no port.")
            return
        try:
            api_version = info.properties[b"api version"].decode("utf-8")
            api_version_int = int(api_version)
            model = info.properties[b"model"].decode("utf-8")
            uuid = info.properties[b"uuid"].decode("utf-8")
            device_name = info.properties[b"name"].decode("utf-8")
        except (ValueError, KeyError) as err:
            _LOGGER.info(
                f"Failed to parse service properties for {service_name}: {err}\n{info.properties}"
            )
            return
        if api_version_int < 4:
            _LOGGER.info(
                f"Ignoring service {service_name} because api_version is < 4: {api_version}"
            )
            return
        _LOGGER.info(
            f"Resolved service {service_name}: device_name=`{device_name}`, model=`{model}`, uuid={uuid}, api_version={api_version}, ip_addresses={info.parsed_scoped_addresses()}, port={info.port}"
        )
        service = Service(
            info.parsed_scoped_addresses(),
            info.port,
            uuid,
            service_name,
            device_name,
            model,
            api_version,
        )
        self._service_map[uuid] = service
        self._dispatch_callback()

    def _on_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        _LOGGER.info(f"Service {name} state changed: {state_change}")
        if state_change == ServiceStateChange.Removed:
            for k in tuple(self._service_map.keys()):
                if self._service_map[k].service_name == name:
                    del self._service_map[k]
            self._dispatch_callback()
        else:
            t = asyncio.create_task(
                self._async_resolve_service(zeroconf, service_type, name)
            )
            self._tasks.add(t)
            t.add_done_callback(lambda t: self._tasks.remove(t))
