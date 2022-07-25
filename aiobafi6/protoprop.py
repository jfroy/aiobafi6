"""aiobafi6 protobuf properties.

Descriptor for `Device` attributes backed by a `Properties` protobuf field.
"""
from __future__ import annotations

import typing as t
from enum import IntEnum

from google.protobuf.message import Message

from .const import MIN_API_VERSION
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
    """Descriptor for `Device` properties backed by a protobuf field.

    The descriptor has a public `min_api_version` that clients aware of ProtoProp can
    use to check if a particular property is supported by a given `Device` based on its
    `api_version` property.
    """

    __slots__ = (
        "_writable",
        "_field_name",
        "_to_proto",
        "_from_proto",
        "_name",
        "min_api_version",
    )

    def __init__(
        self,
        writable: bool = False,
        field_name: t.Optional[str] = None,
        to_proto: t.Optional[t.Callable[[T], t.Any]] = None,
        from_proto: t.Optional[t.Callable[[t.Any], t.Optional[T]]] = None,
        min_api_version: int = MIN_API_VERSION,
    ):
        self._name = None

        self._writable = writable
        self._field_name = field_name
        self.min_api_version = min_api_version

        def ident(val: t.Any) -> T:
            return t.cast(T, val)

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
        val = t.cast(t.Optional[T], obj._maybe_property(self._name))
        if val is None:
            return val
        return self._from_proto(val)

    def __set__(self, obj: t.Any, value: T):
        if not self._writable:
            raise AttributeError(f"can't set attribute {self._name}")
        props = aiobafi6_pb2.Properties()  # pylint: disable=no-member
        setattr(props, t.cast(str, self._field_name), self._to_proto(value))
        obj._commit_property(props)


class OffOnAuto(IntEnum):
    """Tri-state mode enum that matches the protocol buffer."""

    OFF = 0
    ON = 1
    AUTO = 2


def maybe_proto_field(message: Message, field: str) -> t.Optional[t.Any]:
    """Returns the value of `field` in `message` or `None` if not set."""
    return getattr(message, field) if message.HasField(field) else None


class ClosedIntervalValidator(t.Generic[TLT]):
    # pylint: disable=invalid-name
    """Callable that checks if an input value is within the closed interval [a, b]."""

    __slots__ = ("a", "b")

    def __init__(self, a: TLT, b: TLT):
        self.a = a
        self.b = b

    def __call__(self, val: TLT) -> TLT:
        if val < self.a:
            raise ValueError(f"value must be inside [{self.a}, {self.b}]")
        if self.b < val:
            raise ValueError(f"value must be inside [{self.a}, {self.b}]")
        return val


def to_proto_temperature(val: float) -> int:
    """Return val multiplied by 100 as an int."""
    return int(val * 100.0)


def from_proto_temperature(val: int) -> float:
    """Return val divided by 100 as a float."""
    return float(val) / 100.0


def from_proto_humidity(val: int) -> t.Optional[int]:
    """Return val if it is in the [0, 100] interval, otherwise None."""
    if val < 0 or val > 100:
        return None
    return val


class SupportsLessThan(t.Protocol):  # pylint: disable=missing-class-docstring
    def __lt__(self, __other: t.Any) -> bool:
        ...
