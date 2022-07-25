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
    obuf = bytearray()
    for val in buf:
        if val == 0xC0:
            obuf.extend((0xDB, 0xDC))
        elif val == 0xDB:
            obuf.extend((0xDB, 0xDD))
        else:
            obuf.append(val)
    return bytes(obuf)


def remove_emulation_prevention(buf: bytes) -> bytes:
    """Remove emulation prevention sequences (SLIP ESC)."""
    obuf = bytearray()
    eps = False
    for val in buf:
        if val == 0xDB:
            eps = True
        elif eps:
            if val == 0xDC:
                obuf.append(0xC0)
            elif val == 0xDD:
                obuf.append(0xDB)
            else:
                raise ValueError("invalid emulation prevention sequence")
            eps = False
        else:
            obuf.append(val)
    if eps:
        raise ValueError("truncated emulation prevention sequence")
    return bytes(obuf)
