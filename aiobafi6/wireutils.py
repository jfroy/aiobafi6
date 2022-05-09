"""Utilities for BAF message encoding and decoding.

BAF uses SLIP (Serial Line IP, https://datatracker.ietf.org/doc/html/rfc1055.html) to
frame protocol buffer messages on a TCP/IP stream connection.
"""
from __future__ import annotations

from google.protobuf.message import Message


def serialize(message: Message) -> bytes:
    """Serialize `message` to bytes and put it in a SLIP frame."""
    buf = bytearray([0xC0])
    buf.extend(add_emulation_prevention(message.SerializeToString()))
    buf.append(0xC0)
    return buf


def add_emulation_prevention(buf: bytes) -> bytes:
    """Add emulation prevention sequences (SLIP ESC)."""
    o = bytearray()
    for b in buf:
        if b == 0xC0:
            o.extend((0xDB, 0xDC))
        elif b == 0xDB:
            o.extend((0xDB, 0xDD))
        else:
            o.append(b)
    return bytes(o)


def remove_emulation_prevention(buf: bytes) -> bytes:
    """Remove emulation prevention sequences (SLIP ESC)."""
    o = bytearray()
    eps = False
    for b in buf:
        if b == 0xDB:
            eps = True
        elif eps:
            if b == 0xDC:
                o.append(0xC0)
            elif b == 0xDD:
                o.append(0xDB)
            else:
                raise ValueError("invalid emulation prevention sequence")
            eps = False
        else:
            o.append(b)
    if eps:
        raise ValueError("truncated emulation prevention sequence")
    return bytes(o)
