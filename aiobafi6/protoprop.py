"""aiobafi6 protobuf properties.

Descriptor for `Device` attributes backed by a `Properties` protobuf field.
"""
from __future__ import annotations

import typing as t
from enum import IntEnum

from google.protobuf.message import Message

from .proto import aiobafi6_pb2

__all__ = (
    "ProtoProp",
    "OffOnAuto",
    "ClosedIntervalValidator",
    "maybe_proto_field",
    "to_proto_temperature",
    "from_proto_temperature",
    "from_proto_humidity",
)

T = t.TypeVar("T")
TLT = t.TypeVar("TLT", bound="SupportsLessThan")


class ProtoProp(t.Generic[T]):
    """Descriptor for `Device` properties backed by a protobuf field."""

    def __init__(
        self,
        writable: bool = False,
        field_name: t.Optional[str] = None,
        to_proto: t.Optional[t.Callable[[T], t.Any]] = None,
        from_proto: t.Optional[t.Callable[[t.Any], t.Optional[T]]] = None,
    ):
        self._writable = writable
        self._field_name = field_name

        def ident(x: t.Any) -> T:
            return t.cast(T, x)

        if to_proto is None:
            to_proto = ident
        self._to_proto = to_proto
        if from_proto is None:
            from_proto = ident
        self._from_proto = from_proto

    def __set_name__(self, owner: type[object], name: str) -> None:
        self._name = name
        if self._field_name is None:
            self._field_name = name

    def __get__(self, obj: t.Any, objtype: type[object]) -> t.Optional[T]:
        v = t.cast(t.Optional[T], obj._maybe_property(self._name))
        if v is None:
            return v
        return self._from_proto(v)

    def __set__(self, obj: t.Any, value: T):
        if not self._writable:
            raise AttributeError(f"can't set attribute {self._name}")
        p = aiobafi6_pb2.Properties()
        setattr(p, t.cast(str, self._field_name), self._to_proto(value))
        obj._commit_property(p)


class OffOnAuto(IntEnum):
    """Tri-state mode enum that matches the protocol buffer."""

    OFF = 0
    ON = 1
    AUTO = 2


def maybe_proto_field(message: Message, field: str) -> t.Optional[t.Any]:
    """Returns the value of `field` in `message` or `None` if not set."""
    return getattr(message, field) if message.HasField(field) else None


class ClosedIntervalValidator(t.Generic[TLT]):
    """Callable that checks if an input value is within the closed interval [a, b]."""

    __slots__ = ("a", "b")

    def __init__(self, a: TLT, b: TLT):
        self.a = a
        self.b = b

    def __call__(self, x: TLT) -> TLT:
        if x < self.a:
            raise ValueError(f"value must be inside [{self.a}, {self.b}]")
        if self.b < x:
            raise ValueError(f"value must be inside [{self.a}, {self.b}]")
        return x


def to_proto_temperature(x: float) -> int:
    return int(x * 100.0)


def from_proto_temperature(x: int) -> float:
    return float(x) / 100.0


def from_proto_humidity(x: int) -> t.Optional[int]:
    if x < 0 or x > 100:
        return None
    return x


class SupportsLessThan(t.Protocol):
    def __lt__(self, __other: t.Any) -> bool:
        ...
