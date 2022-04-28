"""Utilities for BAF i6 wire serialization and deserialization."""
from __future__ import annotations


def add_emulation_prevention(buf: bytes) -> bytes:
    """Adds emulation prevention sequences.

    The BAF i6 protocol frames its messages on a stream connection using a pair of 0xc0
    bytes. In case a message payload contains 0xc0 bytes, all such bytes are replaced
    with a so-called emulation prevention sequence (`0xdb 0xdc`). In case a message
    payload contains this emulation prevention sequence itself, all `0xdb` bytes are
    replaced with a separate emulation prevention sequence (`0xdb 0xdd`).

    This function adds all such emulation prevention sequences.
    """
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
    """Removes emulation prevention sequences.

    The BAF i6 protocol frames its messages on a stream connection using a pair of 0xc0
    bytes. In case a message payload contains 0xc0 bytes, all such bytes are replaced
    with a so-called emulation prevention sequence (`0xdb 0xdc`). In case a message
    payload contains this emulation prevention sequence itself, all `0xdb` bytes are
    replaced with a separate emulation prevention sequence (`0xdb 0xdd`).

    This function removes all such emulation prevention sequences.
    """
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
