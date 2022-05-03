"""aiobafi6 discovery.

Provides functionality to discover BAF i6 API services.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from collections import namedtuple

from zeroconf import ServiceStateChange, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo

_LOGGER = logging.getLogger(__name__)


"""Represents a BAF i6 API service.

A service is uniquely identified by a device UUID and provides a device name, model
name, and API endpoints (address:port).

A Device object can be created using a Service object.
"""
Service = namedtuple(
    "Service", "uuid, service_name, device_name, model, api_version, addrs, port"
)


def make_service_browser(zc: Zeroconf, callback) -> AsyncServiceBrowser:
    """Discovers BAF i6 API services.

    This function creates a `AsyncServiceBrowser` using the provided `Zeroconf` object
    to discover BAF i6 API services. The browser will call `callback` with a tuple of
    `Service` objects whenever the browser detects a change in service availability.

    Returns a `AsyncServiceBrowser` that should be kept alive for as long as service
    discovery should run.
    """
    # Map device UUID to Service tuple. When a device is renamed, the service record
    # with the old name won't be removed until a TTL expires, so the service/device name
    # is not a good key.
    service_map = {}

    def dispatch_callback() -> None:
        services = tuple(s for s in service_map.values())
        if inspect.iscoroutinefunction(callback):
            asyncio.create_task(callback(services))
        else:
            callback(services)

    async def async_resolve_service(
        zeroconf: Zeroconf, service_type: str, service_name: str
    ) -> None:
        info = AsyncServiceInfo(service_type, service_name)
        if not await info.async_request(zeroconf, 3000):
            _LOGGER.info(f"Failed to resolve service {service_name}.")
            return
        if info.properties is None:
            _LOGGER.info(f"Service {service_name} has no properties.")
            return
        try:
            api_version = int(info.properties[b"api version"].decode("utf-8"))
            model = info.properties[b"model"].decode("utf-8")
            uuid = info.properties[b"uuid"].decode("utf-8")
            device_name = info.properties[b"name"].decode("utf-8")
        except (ValueError, KeyError) as err:
            _LOGGER.info(
                f"Failed to parse service properties for {service_name}: {err}\n{info.properties}"
            )
            return
        if api_version < 4:
            _LOGGER.info(
                f"Ignoring service {service_name} because api_version is < 4: {api_version}"
            )
            return
        _LOGGER.info(
            f"Resolved service {service_name}: device_name=`{device_name}`, model=`{model}`, uuid={uuid}, api_version={api_version}, addrs={info.parsed_scoped_addresses()}, port={info.port}"
        )
        service = Service(
            uuid,
            service_name,
            device_name,
            model,
            api_version,
            tuple(addr for addr in info.parsed_scoped_addresses()),
            info.port,
        )
        service_map[uuid] = service
        dispatch_callback()

    def on_state_change(
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        _LOGGER.info(f"Service {name} state changed: {state_change}")
        if state_change == ServiceStateChange.Removed:
            for k in tuple(service_map.keys()):
                if service_map[k].service_name == name:
                    del service_map[k]
            dispatch_callback()
        else:
            _ = asyncio.create_task(async_resolve_service(zeroconf, service_type, name))

    return AsyncServiceBrowser(zc, ["_api._tcp.local."], handlers=[on_state_change])
