"""Command line tool for aiobaf6."""
from __future__ import annotations

import argparse
import asyncio
import ipaddress

from aiobafi6.generated import aiobafi6_pb2
from aiobafi6 import wireutils

ARGS = argparse.ArgumentParser(description="Command line tool for aiobaf6.")
ARGS.add_argument(
    "-i",
    "--ip",
    action="store",
    dest="ip_addr",
    help="device address",
)
ARGS.add_argument(
    "-s",
    "--speed",
    action="store",
    dest="speed",
    help="set fan speed",
)
ARGS.add_argument(
    "-m",
    "--mode",
    action="store",
    dest="fan_mode",
    help="set fan mode",
)

PORT = 31415


async def query_state(ip_addr: str):
    print("Connecting to ", ip_addr)
    reader, writer = await asyncio.open_connection(ip_addr, PORT)
    writer.write(b"\xc0\x12\x02\x1a\x00\xc0")
    await writer.drain()
    i = 0
    while True:
        try:
            # The wire format frames protobuf messages with 0xc0, so the first
            # `readuntil` will return just that byte and the next will return the
            # message with the terminating byte.
            raw_buf = await asyncio.wait_for(reader.readuntil(b"\xc0"), 10)
            if len(raw_buf) == 1:
                continue
            buf = wireutils.remove_emulation_prevention(raw_buf[:-1])
        except asyncio.TimeoutError:
            return
        with open(f"baf_dump-{i}.bin", "wb") as f:
            f.write(buf)
        i += 1
        root = aiobafi6_pb2.Root()
        root.ParseFromString(buf)
        print(root)


async def set_speed(ip_addr: str, speed: int):
    if speed < 0 or speed > 7:
        raise ValueError(f"invalid speed value: {speed}")
    print(f"Setting speed of fan at {ip_addr} to {speed}")
    root = aiobafi6_pb2.Root()
    root.root2.command.command3.set_speed = speed
    reader, writer = await asyncio.open_connection(ip_addr, PORT)
    writer.write(wireutils.serialize(root))
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def set_fan_mode(ip_addr: str, mode: int):
    if mode < 0 or mode > 2:
        raise ValueError(f"invalid mode value: {mode}")
    print(f"Setting mode of fan at {ip_addr} to {mode}")
    root = aiobafi6_pb2.Root()
    root.root2.command.command3.set_fan_mode = mode
    reader, writer = await asyncio.open_connection(ip_addr, PORT)
    writer.write(wireutils.serialize(root))
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def async_main():
    args = ARGS.parse_args()
    try:
        # do some checking on IP address
        ip_addr = ipaddress.ip_address(args.ip_addr)
    except ValueError:
        print("invalid address ", args.ip_addr)
        return
    if args.speed is not None:
        await set_speed(str(ip_addr), int(args.speed))
    elif args.fan_mode is not None:
        await set_fan_mode(str(ip_addr), int(args.fan_mode))
    else:
        await query_state(str(ip_addr))


def main():
    task = asyncio.Task(async_main())
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
