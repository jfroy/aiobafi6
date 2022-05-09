# aiobafi6

[![PyPI version](https://badge.fury.io/py/aiobafi6.svg)](https://badge.fury.io/py/aiobafi6)
[![Downloads](https://pepy.tech/badge/aiobafi6)](https://pepy.tech/project/aiobafi6)

aiobafi6 is a python library to discovery, query and control
[Big Ass Fans](https://bigassfans.com) products that use the i6 protocol, which
includes i6 fans and Haiku fans with the 3.0 firmware.

It supports almost all the features of the previous protocol ("SenseMe"), with
the exception of presence sensing, rooms, and sleep mode.

## Command line

The aiobafi6 package comes with a minimal command line (`aiobafi6`) that uses
either the library or direct communication with a target device. It is useful
for debugging and interacting with the firmware. Run with `--help` for usage.

## Compiling the aiobafi6 protocol buffer

The BAF i6 protocol uses
[protocol buffers](https://developers.google.com/protocol-buffers) for message
wire serialization. This library maintains a
[single proto file](proto/aiobafi6.proto) with all known messages and contants.

The generated Python client for this proto file is checked in the repo to avoid
depending on the protocol buffer compiler for installation. Whenever the source
proto file is changed, the Python client files must be re-generated.

`poe protoc`

## Special thanks

[@bdraco](https://github.com/bdraco) for writing the HASS integration, helping with
Python, and suggesting BAF is using protobufs.

[@oogje](https://github.com/oogje) for a reference homebridge implementation.

[Big Ass Fans](https://www.bigassfans.com) for making great products.
