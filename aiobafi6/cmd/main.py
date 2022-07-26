"""Command line tool for aiobaf6."""
from __future__ import annotations

import argparse
import asyncio
import difflib
import ipaddress
import logging.config
import typing as t

from google.protobuf import text_format
from zeroconf import IPVersion
from zeroconf.asyncio import AsyncZeroconf

from aiobafi6 import wireutils
from aiobafi6.device import Device
from aiobafi6.discovery import PORT, Service, ServiceBrowser
from aiobafi6.proto import aiobafi6_pb2

ARGS = argparse.ArgumentParser(
    description="Command line tool for aiobaf6.\n\nThe tool supports a direct connection mode that is more powerful for debugging."  # pylint: disable=line-too-long
)
ARGS.add_argument(
    "-s",
    "--discover",
    action="store_true",
    dest="discover",
    help="discover devices",
)
ARGS.add_argument(
    "-i",
    "--ip",
    action="store",
    dest="ip_addr",
    help="device address",
)
ARGS.add_argument(
    "-d",
    "--dump",
    action="store_true",
    dest="dump",
    help="enable proto dumping",
)
ARGS.add_argument(
    "-r",
    "--direct",
    action="store_true",
    dest="direct",
    help="directly connect to device, bypassing library",
)
ARGS.add_argument(
    "-t",
    "--interval",
    action="store",
    dest="interval",
    default=15,
    type=int,
    help="property query interval in seconds",
)
ARGS.add_argument(
    "property",
    nargs="?",
    help="property name",
)
ARGS.add_argument(
    "value",
    nargs="?",
    help="property value",
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "simple": {"format": "%(levelname)s:%(asctime)s:%(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "": {
            "level": "INFO",
            "handlers": ["console"],
        },
        "aiobafi6.device": {
            "level": "DEBUG",
        },
        "aiobafi6.discovery": {
            "level": "DEBUG",
        },
    },
}


async def query_loop(writer: asyncio.StreamWriter, interval: int):
    """Run direct query loop."""
    print(f"starting query loop: interval {interval}s")
    root = aiobafi6_pb2.Root()  # pylint: disable=no-member
    root.root2.query.property_query = aiobafi6_pb2.ALL  # pylint: disable=no-member
    writer.write(wireutils.serialize(root))
    while True:
        await asyncio.sleep(interval)
        print("sending refresh query")
        root = aiobafi6_pb2.Root()  # pylint: disable=no-member
        root.root2.query.property_query = aiobafi6_pb2.ALL  # pylint: disable=no-member
        writer.write(wireutils.serialize(root))


async def direct_query_state(ip_addr: str, dump: bool, interval: int):
    """Query state directly."""
    print(f"directly querying all state from {ip_addr}")
    reader, writer = await asyncio.open_connection(ip_addr, PORT)
    _ = asyncio.create_task(query_loop(writer, interval))
    i = 0
    previous = aiobafi6_pb2.Properties()  # pylint: disable=no-member
    latest = aiobafi6_pb2.Properties()  # pylint: disable=no-member
    unknown: dict[str, t.Any] = {}
    previous_sorted_unknown = []
    while True:
        # The wire format frames protobuf messages with 0xc0, so the first `readuntil`
        # will return just that byte and the next will return the message with the
        # terminating byte.
        raw_buf = await reader.readuntil(b"\xc0")
        if len(raw_buf) == 1:
            continue
        buf = wireutils.remove_emulation_prevention(raw_buf[:-1])
        if dump:
            with open(f"dump-query-{i}.bin", "wb") as writer:
                writer.write(buf)
            i += 1
        root = aiobafi6_pb2.Root()  # pylint: disable=no-member
        root.ParseFromString(buf)
        for prop in root.root2.query_result.properties:
            for field in prop.UnknownFields():  # type: ignore
                unknown[str(field.field_number)] = field.data
            for field in prop.capabilities.UnknownFields():  # type: ignore
                unknown["capabilities." + str(field.field_number)] = field.data
            for field in prop.stats.UnknownFields():  # type: ignore
                unknown["stats." + str(field.field_number)] = field.data
        root.DiscardUnknownFields()  # type: ignore
        for prop in root.root2.query_result.properties:
            prop.ClearField("local_datetime")
            prop.ClearField("utc_datetime")
            prop.stats.ClearField("uptime_minutes")
            latest.MergeFrom(prop)
        diff = "".join(
            difflib.unified_diff(
                text_format.MessageToString(previous).splitlines(keepends=True),
                text_format.MessageToString(latest).splitlines(keepends=True),
            )
        )
        if len(diff) > 0:
            print(diff)
        previous.CopyFrom(latest)
        sorted_unknown = [f"{k}: {str(unknown[k])}\n" for k in sorted(unknown.keys())]
        diff = "".join(difflib.unified_diff(previous_sorted_unknown, sorted_unknown))
        if len(diff) > 0:
            print(diff)
        previous_sorted_unknown = sorted_unknown


def print_device(dev: Device):
    """Print a Device."""
    print("<-- callback")
    print(dev.properties_proto)
    print("callback -->")


async def query_state(ip_addr: str, interval: int):
    """Query state via a Device."""
    print(f"querying all state from {ip_addr}: interval {interval}s")
    dev = Device(
        Service(ip_addresses=[ip_addr], port=PORT), query_interval_seconds=interval
    )
    dev.add_callback(print_device)
    await dev.async_run()


async def direct_set_property(ip_addr: str, prop: str, value: int, dump: bool):
    """Set a property directly."""
    print(f"directly setting {prop} of {ip_addr} to {value}")
    root = aiobafi6_pb2.Root()  # pylint: disable=no-member
    try:
        setattr(root.root2.commit.properties, prop, value)
    except TypeError:
        setattr(root.root2.commit.properties, prop, int(value))
    buf = wireutils.serialize(root)
    if dump:
        with open(f"dump-set-{prop}-{value}.bin", "wb") as writer:
            writer.write(buf)
    _, writer = await asyncio.open_connection(ip_addr, PORT)
    writer.write(buf)
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def set_property(ip_addr: str, prop: str, value: int):
    """Set a property via a Device."""
    print(f"setting {prop} of {ip_addr} to {value}")
    dev = Device(Service(ip_addresses=[ip_addr], port=PORT), query_interval_seconds=0)
    dev.async_run()
    await dev.async_wait_available()
    try:
        setattr(dev, prop, value)
    except TypeError:
        setattr(dev, prop, int(value))


async def async_main():
    """async_main"""
    args = ARGS.parse_args()
    logging.config.dictConfig(LOGGING)
    ip_addr = None
    if args.ip_addr is not None:
        try:
            ip_addr = ipaddress.ip_address(args.ip_addr)
        except ValueError:
            print(f"invalid address: {args.ip_addr}")
            return
    if args.discover:
        aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)
        _ = ServiceBrowser(
            aiozc.zeroconf, lambda services: print(f"== Discover ==\n{services}")
        )
        while True:
            await asyncio.sleep(1)
    elif args.property is not None:
        if args.value is None:
            raise RuntimeError("must specify property value")
        if args.direct:
            await direct_set_property(
                str(ip_addr), args.property, args.value, dump=args.dump
            )
        else:
            await set_property(str(ip_addr), args.property, args.value)
    elif args.direct:
        await direct_query_state(str(ip_addr), dump=args.dump, interval=args.interval)
    else:
        await query_state(str(ip_addr), interval=args.interval)


def main():
    """main"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
