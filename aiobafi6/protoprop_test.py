"""Tests for protoprop."""
import typing as t

import pytest
from google.protobuf.message import Message

from .proto import aiobafi6_pb2
from .protoprop import (
    ClosedIntervalValidator,
    OffOnAuto,
    ProtoProp,
    from_proto_humidity,
    from_proto_temperature,
    maybe_proto_field,
    to_proto_temperature,
)


class FakeDevice:
    """A class that implements the interface expected by ProtoProp."""

    def __init__(self):
        self.properties = aiobafi6_pb2.Properties()

    def _maybe_property(self, field: str) -> t.Optional[t.Any]:
        return maybe_proto_field(t.cast(Message, self.properties), field)

    def _commit_property(self, p: aiobafi6_pb2.Properties) -> None:
        self.properties.MergeFrom(p)


def test_off_on_auto():
    class D(FakeDevice):
        fan_mode = ProtoProp[OffOnAuto](
            writable=True, from_proto=lambda v: OffOnAuto(v)
        )

    d = D()
    d.properties.fan_mode = aiobafi6_pb2.AUTO
    assert d.fan_mode == OffOnAuto.AUTO
    d.fan_mode = OffOnAuto.AUTO
    with pytest.raises(ValueError):
        d.properties.fan_mode = t.cast(aiobafi6_pb2.OffOnAuto, 3)


def test_temperature():
    class D(FakeDevice):
        temperature = ProtoProp[float](
            writable=True,
            to_proto=to_proto_temperature,
            from_proto=from_proto_temperature,
        )

    d = D()
    d.properties.temperature = 2250
    assert d.temperature == 22.5
    d.temperature = 23.5
    assert d.properties.temperature == 2350


def test_humidity():
    class D(FakeDevice):
        humidity = ProtoProp[int](from_proto=from_proto_humidity)

    d = D()
    for i in range(100):
        d.properties.humidity = i
        assert d.humidity == i
    d.properties.humidity = -1
    assert d.humidity is None
    d.properties.humidity = 101
    assert d.humidity is None
    d.properties.humidity = 1000
    assert d.humidity is None


def test_closed_interval():
    class D(FakeDevice):
        speed = ProtoProp[int](
            writable=True, to_proto=ClosedIntervalValidator[int](0, 0)
        )

    d = D()
    d.speed = 0
    with pytest.raises(ValueError):
        d.speed = -1
    with pytest.raises(ValueError):
        d.speed = 1
