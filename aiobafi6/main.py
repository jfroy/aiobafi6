"""Command line tool for aiobaf6."""
from __future__ import annotations

import argparse
import asyncio
import ipaddress

from enum import IntEnum

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

PORT = 31415


class OnOffAuto(IntEnum):
    OFF = 0
    ON = 1
    AUTO = 2


# Property value decoders


def decode_text(buf: bytes) -> str:
    size, varint_size = decode_varint_128(buf)
    buf = buf[varint_size : varint_size + size]
    if len(buf) < size:
        raise ValueError("buf is too small")
    return buf.decode("utf-8")


def decode_ssid(buf: bytes):
    # The property is something like:
    # - 0x12 0x0A
    # - Length-prefixed string (SSID)
    # - Other data (RSSI, password hash?)
    size, varint_size = decode_varint_128(buf[2:])
    buf = buf[2 + varint_size : 2 + varint_size + size]
    if len(buf) < size:
        raise ValueError("buf is too small")
    return buf.decode("utf-8")


def decode_firmware_0x82_0x01(buf: bytes) -> str:
    size, varint_size = decode_varint_128(buf)
    buf = buf[varint_size : varint_size + size]
    if len(buf) < size:
        raise ValueError("buf is too small")
    # One particular fan returns 2 such properties. One has length 0x7 followed by 0xA1
    # followed by length-prefixed string. The other has length 0x09 followed by
    # 0x08 0x01 0x12 followed by length-prefixed string.
    if buf[0] == 0x1A:
        size = buf[1]
        buf = buf[2:]
    elif buf[0] == 0x08:
        if buf[1] == 0x01 and buf[2] == 0x12:
            size = buf[3]
            buf = buf[4:]
        else:
            raise ValueError(f"unknown firmware 0x82 0x01 value: {buf}")
    return buf[:size].decode("ascii")


def decode_data(buf: bytes) -> bytes:
    return buf


def decode_int8(buf: bytes) -> int:
    return int(buf[0])


def decode_bool(buf: bytes) -> bool:
    return bool(buf[0] != 0)


def decode_on_off_auto(buf: bytes) -> OnOffAuto:
    return OnOffAuto(buf[0])


def decode_varint128(buf: bytes) -> int:
    v, _ = decode_varint_128(buf)
    return v


def decode_varint128_float(buf: bytes) -> float:
    v, _ = decode_varint_128(buf)
    return float(v) / 100.0


# Property handlers


def handle_name(v: str):
    print(f"name: {v}")


def handle_model(v: str):
    print(f"model: {v}")


def handle_datetime(v: str):
    print(f"datetime: {v}")


def handle_firmware_version(v: str):
    print(f"firmware_version: {v}")


def handle_mac(v: str):
    print(f"mac: {v}")


def handle_token(v: str):
    print(f"token: {v}")


def handle_website(v: str):
    print(f"website: {v}")


def handle_comfort_ideal_temperature(v: str):
    print(f"comfort_ideal_temperature: {v}")


def handle_unknown_firmware_version(v: str):
    print(f"unknown_firmware_version: {v}")


def handle_eco_mode_enable(v: str):
    print(f"eco_mode_enable: {v}")


def handle_capabilities(v: str):
    print(f"capabilities: {v}")


def handle_comfort_min_speed(v: str):
    print(f"comfort_min_speed: {v}")


def handle_comfort_max_speed(v: str):
    print(f"comfort_max_speed: {v}")


def handle_motion_sense_enable(v: str):
    print(f"motion_sense_enable: {v}")


def handle_light_enable(v: str):
    print(f"light_enable: {v}")


def handle_motion_sense_delay(v: str):
    print(f"motion_sense_delay: {v}")


def handle_light_brightness(v: str):
    print(f"light_brightness: {v}")


def handle_return_to_auto_enable(v: str):
    print(f"return_to_auto_enable: {v}")


def handle_brightness_level(v: str):
    print(f"brightness_level: {v}")


def handle_temperature(v: str):
    print(f"temperature: {v}")


def handle_led_enable(v: str):
    print(f"led_enable: {v}")


def handle_prevent_additional_controls_enable(v: str):
    print(f"prevent_additional_controls_enable: {v}")


def handle_return_to_auto_delay(v: str):
    print(f"return_to_auto_delay: {v}")


def handle_light_color_temperature(v: str):
    print(f"light_color_temperature: {v}")


def handle_relative_humidity(v: str):
    print(f"relative_humidity: {v}")


def handle_fan_beep_enable(v: str):
    print(f"fan_beep_enable: {v}")


def handle_ip_addr(v: str):
    print(f"ip_addr: {v}")


def handle_light_auto_motion_delay(v: str):
    print(f"light_auto_motion_delay: {v}")


def handle_whoosh_enable(v: str):
    print(f"whoosh_enable: {v}")


def handle_light_return_to_auto_enable(v: str):
    print(f"light_return_to_auto_enable: {v}")


def handle_fan_enable(v: str):
    print(f"fan_enable: {v}")


def handle_light_return_to_auto_delay(v: str):
    print(f"light_return_to_auto_delay: {v}")


def handle_fan_reverse_enable(v: str):
    print(f"fan_reverse_enable: {v}")


def handle_heat_assist_enable(v: str):
    print(f"heat_assist_enable: {v}")


def handle_ssid(v: str):
    print(f"ssid: {v}")


def handle_fan_speed_percent(v: str):
    print(f"fan_speed_percent: {v}")


def handle_light_dim_to_warm_enable(v: str):
    print(f"light_dim_to_warm_enable: {v}")


def handle_fan_speed(v: str):
    print(f"fan_speed: {v}")


def handle_warmest_color_temperature(v: str):
    print(f"warmest_color_temperature: {v}")


def handle_fan_auto_comfort_enable(v: str):
    print(f"fan_auto_comfort_enable: {v}")


def handle_rpm(v: str):
    print(f"rpm: {v}")


def handle_coolest_color_temperature(v: str):
    print(f"coolest_color_temperature: {v}")


# Map property code to a decode function and a handler function.
# Credits to https://github.com/oogje/homebridge-i6-bigAssFans
PROPERTIES = [
    (b"\x0a", (decode_text, handle_name)),
    (b"\x12", (decode_text, handle_model)),
    (b"\x22", (decode_text, handle_datetime)),
    (b"\x2a", (decode_text, handle_datetime)),
    (b"\x32", (decode_text, handle_datetime)),
    (b"\x3a", (decode_text, handle_firmware_version)),
    (b"\x42", (decode_text, handle_mac)),
    (b"\x4a", (decode_text, handle_token)),
    (b"\x52", (decode_text, handle_token)),
    (b"\x5a", (decode_text, handle_website)),
    (b"\x80\x03", (decode_varint128_float, handle_comfort_ideal_temperature)),
    (b"\x82\x01", (decode_firmware_0x82_0x01, handle_unknown_firmware_version)),
    (b"\x88\x04", (decode_int8, handle_eco_mode_enable)),
    (b"\x8a\x01", (decode_data, handle_capabilities)),
    (b"\x90\x03", (decode_int8, handle_comfort_min_speed)),
    (b"\x98\x03", (decode_int8, handle_comfort_max_speed)),
    (b"\xa0\x03", (decode_bool, handle_motion_sense_enable)),
    (b"\xa0\x04", (decode_on_off_auto, handle_light_enable)),
    (b"\xa8\x03", (decode_varint128, handle_motion_sense_delay)),
    (b"\xa8\x04", (decode_int8, handle_light_brightness)),
    (b"\xb0\x03", (decode_bool, handle_return_to_auto_enable)),
    (b"\xb0\x04", (decode_int8, handle_brightness_level)),
    (b"\xb0\x05", (decode_varint128_float, handle_temperature)),
    (b"\xb0\x08", (decode_bool, handle_led_enable)),
    (b"\xb0\x09", (decode_bool, handle_prevent_additional_controls_enable)),
    (b"\xb8\x03", (decode_varint128, handle_return_to_auto_delay)),
    (b"\xb8\x04", (decode_varint128, handle_light_color_temperature)),
    (b"\xb8\x05", (decode_varint128_float, handle_relative_humidity)),
    (b"\xb8\x08", (decode_bool, handle_fan_beep_enable)),
    (b"\xc2\x07", (decode_text, handle_ip_addr)),
    (b"\xc8\x04", (decode_varint128, handle_light_auto_motion_delay)),
    (b"\xd0\x03", (decode_bool, handle_whoosh_enable)),
    (b"\xd0\x04", (decode_bool, handle_light_return_to_auto_enable)),
    (b"\xd8\x02", (decode_on_off_auto, handle_fan_enable)),
    (b"\xd8\x04", (decode_varint128, handle_light_return_to_auto_delay)),
    (b"\xe0\x02", (decode_bool, handle_fan_reverse_enable)),
    (b"\xe0\x03", (decode_bool, handle_heat_assist_enable)),
    (b"\xe2\x07", (decode_ssid, handle_ssid)),
    (b"\xe8\x02", (decode_int8, handle_fan_speed_percent)),
    (b"\xe8\x04", (decode_bool, handle_light_dim_to_warm_enable)),
    (b"\xf0\x02", (decode_int8, handle_fan_speed)),
    (b"\xf0\x04", (decode_varint128, handle_warmest_color_temperature)),
    (b"\xf8\x02", (decode_bool, handle_fan_auto_comfort_enable)),
    (b"\xf8\x03", (decode_int8, handle_rpm)),
    (b"\xf8\x04", (decode_varint128, handle_coolest_color_temperature)),
]


def remove_chunk_separator_emulation_prevention_bytes(d: bytes) -> bytes:
    """Remove chunk separator emulation prevention bytes."""
    o = bytearray()
    epb = False
    for b in d:
        if b == "\xdb":
            epb = True
        elif epb:
            if b == "\xdc":
                o.append("\xc0")
            elif b == "\xdd":
                o.append("\xdb")
            else:
                raise ValueError(
                    "invalid chunk separator emulation prevention byte code"
                )
            epb = False
        else:
            o.append(b)
    if epb:
        raise ValueError("truncated chunk separator emulation prevention sequence")
    return bytes(o)


def decode_varint_128(d: bytes) -> (int, int):
    """Reads a varint 128 and returns its value and encoded size in bytes."""
    result = 0
    shift = 0
    for i in range(len(d)):
        b = d[i]
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return (result, i + 1)
        shift += 7
        if shift >= 64:
            raise ValueError("varint too large")
    raise ValueError("varint truncated")


def process_outter_0x12_message(buf: bytes) -> int:
    """Process a 0x12 message whose parent is a top-level 0xc0 message."""
    if buf[0] != 0x12:
        raise ValueError("expected 0x12 header byte")
    size, varint_size = decode_varint_128(buf[1:])
    buf_size = 1 + varint_size + size
    if buf_size < len(buf):
        # This seems corrolated to the appearance of unknown 0x01 bytes in the inner
        # 0x22 message. The number of such 0x01 bytes will match the size delta.
        print(
            f"WARNING: outter 0x12 message size {buf_size} smaller than input buffer size {len(buf)}; hypothesis is firmware accounting bug"
        )
        buf_size = len(buf)
        size = buf_size - (1 + varint_size)
    buf = buf[1 + varint_size : buf_size]
    if len(buf) < size:
        raise ValueError("buf is too small")
    if buf[0] == 0x22:
        process_0x22_message(buf)
    else:
        raise RuntimeError(f"unexpected value in buffer: {hex(buf[0])}")
    return buf_size


def process_0x22_message(buf: bytes) -> int:
    """Process a 0x22 message."""
    if buf[0] != 0x22:
        raise ValueError("expected 0x22 header byte")
    size, varint_size = decode_varint_128(buf[1:])
    buf_size = 1 + varint_size + size
    if buf_size < len(buf):
        # This seems corrolated to the appearance of unknown 0x01 bytes in the 0x22
        # message. The number of such 0x01 bytes will match the size delta.
        print(
            f"WARNING: 0x22 message size {buf_size} smaller than input buffer size {len(buf)}; hypothesis is firmware accounting bug"
        )
        buf_size = len(buf)
        size = buf_size - (1 + varint_size)
    buf = buf[1 + varint_size : buf_size]
    if len(buf) < size:
        raise ValueError("buf is too small")
    while len(buf) > 0:
        if buf[0] == 0x12:
            sub_size = process_inner_0x12_message(buf)
            buf = buf[sub_size:]
        elif buf[0] == 0x1A:
            # Speculate this is a client command?
            print("unknown 0x1a sub-message in 0x22 message")
            size, varint_size = decode_varint_128(buf[1:])
            buf = buf[1 + varint_size + size :]
        elif buf[0] == 0x1:
            print("unknown 0x1 sub-message in 0x22 message")
            buf = buf[1:]
        else:
            raise RuntimeError(f"unexpected value in buffer: {hex(buf[0])}")
    return buf_size


def process_inner_0x12_message(buf: bytes) -> int:
    """Process a 0x12 message whose parent is a 0x22 message."""
    if buf[0] != 0x12:
        raise ValueError("expected 0x12 header byte")
    size, varint_size = decode_varint_128(buf[1:])
    buf_size = 1 + varint_size + size
    buf = buf[1 + varint_size : buf_size]
    if len(buf) < size:
        raise ValueError("buf is too small")

    # The next byte is a property code. Some properties have a sub-property bytes.
    prop_match = None
    for prop_id, prop_fns in PROPERTIES:
        if len(buf) < len(prop_id):
            continue
        match = True
        for i in range(len(prop_id)):
            if buf[i] != prop_id[i]:
                match = False
                break
        if match:
            prop_match = (prop_id, prop_fns)
            break
    if prop_match is None:
        print(f"unknown property {hex(buf[0])}: {buf}")
        return buf_size
    print("matched property ", prop_match)
    prop_id, prop_fns = prop_match
    buf = buf[len(prop_id) :]
    prop_fns[1](prop_fns[0](buf))
    return buf_size


async def query_state(ip_addr: str):
    print("Connecting to ", ip_addr)
    reader, writer = await asyncio.open_connection(ip_addr, PORT)
    writer.write(b"\xc0\x12\x02\x1a\x00\xc0")
    await writer.drain()
    while True:
        try:
            # The wire format _brackets_ chunks with 0xc0, so the first `readuntil`
            # will return just that byte and the next will return the chunk with the
            # terminating marker.
            raw_buf = await asyncio.wait_for(reader.readuntil(b"\xc0"), 10)
            if len(raw_buf) == 1:
                continue
            buf = remove_chunk_separator_emulation_prevention_bytes(raw_buf[:-1])
        except asyncio.TimeoutError:
            return
        if len(buf) < 2:
            raise ValueError("buffer less than 2 bytes (not enough for code and size)")
        print("processing chunk")
        while len(buf) > 0:
            if buf[0] == 0x12:
                size = process_outter_0x12_message(buf)
                buf = buf[size:]
            else:
                raise RuntimeError(f"unexpected value in buffer: {hex(buf[0])}")


async def set_speed(ip_addr: str, speed: int):
    if speed < 0 or speed > 7:
        raise ValueError(f"invalid speed value: {speed}")
    packet = bytearray(b"\xc0\x12\x07\x12\x05\x1a\x03\xf0\x02")
    packet.extend([speed, 0xC0])
    print(f"Setting speed of fan at {ip_addr} to {speed}")
    reader, writer = await asyncio.open_connection(ip_addr, PORT)
    writer.write(packet)
    await writer.drain()
    writer.close()
    b = await reader.read()
    print(f"set_speed response data: {b}")
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
