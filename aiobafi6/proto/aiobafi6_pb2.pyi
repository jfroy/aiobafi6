from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

ALL: ProperyQuery
AUTO: OffOnAuto
DESCRIPTOR: _descriptor.FileDescriptor
FAN: ProperyQuery
FIRMWARE_MORE_DATETIME_API: ProperyQuery
LIGHT: ProperyQuery
NETWORK: ProperyQuery
OFF: OffOnAuto
ON: OffOnAuto
SCHEDULES: ProperyQuery
SENSORS: ProperyQuery

class Capabilities(_message.Message):
    __slots__ = ["has_comfort1", "has_comfort3", "has_light"]
    HAS_COMFORT1_FIELD_NUMBER: _ClassVar[int]
    HAS_COMFORT3_FIELD_NUMBER: _ClassVar[int]
    HAS_LIGHT_FIELD_NUMBER: _ClassVar[int]
    has_comfort1: bool
    has_comfort3: bool
    has_light: bool
    def __init__(self, has_comfort1: bool = ..., has_comfort3: bool = ..., has_light: bool = ...) -> None: ...

class Commit(_message.Message):
    __slots__ = ["properties"]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    properties: Properties
    def __init__(self, properties: _Optional[_Union[Properties, _Mapping]] = ...) -> None: ...

class FirmwareProperties(_message.Message):
    __slots__ = ["bootloader_version", "firmware_version", "mac_address"]
    BOOTLOADER_VERSION_FIELD_NUMBER: _ClassVar[int]
    FIRMWARE_VERSION_FIELD_NUMBER: _ClassVar[int]
    MAC_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    bootloader_version: str
    firmware_version: str
    mac_address: str
    def __init__(self, firmware_version: _Optional[str] = ..., bootloader_version: _Optional[str] = ..., mac_address: _Optional[str] = ...) -> None: ...

class Properties(_message.Message):
    __slots__ = ["api_endpoint", "api_version", "auto_comfort_enable", "capabilities", "comfort_heat_assist_enable", "comfort_heat_assist_reverse_enable", "comfort_heat_assist_speed", "comfort_ideal_temperature", "comfort_max_speed", "comfort_min_speed", "current_rpm", "dns_sd_uuid", "eco_enable", "fan_beep_enable", "fan_mode", "fan_occupancy_detected", "firmware", "firmware_version", "humidity", "ip_address", "led_indicators_enable", "legacy_ir_remote_enable", "light_auto_motion_timeout", "light_brightness_level", "light_brightness_percent", "light_color_temperature", "light_coolest_color_temperature", "light_dim_to_warm_enable", "light_mode", "light_occupancy_detected", "light_return_to_auto_enable", "light_return_to_auto_timeout", "light_warmest_color_temperature", "local_datetime", "mac_address", "model", "motion_sense_enable", "motion_sense_timeout", "name", "remote_firmware", "return_to_auto_enable", "return_to_auto_timeout", "reverse_enable", "speed", "speed_percent", "stats", "target_rpm", "temperature", "utc_datetime", "uuid9", "whoosh_enable", "wifi"]
    API_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    API_VERSION_FIELD_NUMBER: _ClassVar[int]
    AUTO_COMFORT_ENABLE_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    COMFORT_HEAT_ASSIST_ENABLE_FIELD_NUMBER: _ClassVar[int]
    COMFORT_HEAT_ASSIST_REVERSE_ENABLE_FIELD_NUMBER: _ClassVar[int]
    COMFORT_HEAT_ASSIST_SPEED_FIELD_NUMBER: _ClassVar[int]
    COMFORT_IDEAL_TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    COMFORT_MAX_SPEED_FIELD_NUMBER: _ClassVar[int]
    COMFORT_MIN_SPEED_FIELD_NUMBER: _ClassVar[int]
    CURRENT_RPM_FIELD_NUMBER: _ClassVar[int]
    DNS_SD_UUID_FIELD_NUMBER: _ClassVar[int]
    ECO_ENABLE_FIELD_NUMBER: _ClassVar[int]
    FAN_BEEP_ENABLE_FIELD_NUMBER: _ClassVar[int]
    FAN_MODE_FIELD_NUMBER: _ClassVar[int]
    FAN_OCCUPANCY_DETECTED_FIELD_NUMBER: _ClassVar[int]
    FIRMWARE_FIELD_NUMBER: _ClassVar[int]
    FIRMWARE_VERSION_FIELD_NUMBER: _ClassVar[int]
    HUMIDITY_FIELD_NUMBER: _ClassVar[int]
    IP_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    LED_INDICATORS_ENABLE_FIELD_NUMBER: _ClassVar[int]
    LEGACY_IR_REMOTE_ENABLE_FIELD_NUMBER: _ClassVar[int]
    LIGHT_AUTO_MOTION_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    LIGHT_BRIGHTNESS_LEVEL_FIELD_NUMBER: _ClassVar[int]
    LIGHT_BRIGHTNESS_PERCENT_FIELD_NUMBER: _ClassVar[int]
    LIGHT_COLOR_TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    LIGHT_COOLEST_COLOR_TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    LIGHT_DIM_TO_WARM_ENABLE_FIELD_NUMBER: _ClassVar[int]
    LIGHT_MODE_FIELD_NUMBER: _ClassVar[int]
    LIGHT_OCCUPANCY_DETECTED_FIELD_NUMBER: _ClassVar[int]
    LIGHT_RETURN_TO_AUTO_ENABLE_FIELD_NUMBER: _ClassVar[int]
    LIGHT_RETURN_TO_AUTO_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    LIGHT_WARMEST_COLOR_TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    LOCAL_DATETIME_FIELD_NUMBER: _ClassVar[int]
    MAC_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    MOTION_SENSE_ENABLE_FIELD_NUMBER: _ClassVar[int]
    MOTION_SENSE_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REMOTE_FIRMWARE_FIELD_NUMBER: _ClassVar[int]
    RETURN_TO_AUTO_ENABLE_FIELD_NUMBER: _ClassVar[int]
    RETURN_TO_AUTO_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    REVERSE_ENABLE_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    SPEED_PERCENT_FIELD_NUMBER: _ClassVar[int]
    STATS_FIELD_NUMBER: _ClassVar[int]
    TARGET_RPM_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    UTC_DATETIME_FIELD_NUMBER: _ClassVar[int]
    UUID9_FIELD_NUMBER: _ClassVar[int]
    WHOOSH_ENABLE_FIELD_NUMBER: _ClassVar[int]
    WIFI_FIELD_NUMBER: _ClassVar[int]
    api_endpoint: str
    api_version: str
    auto_comfort_enable: bool
    capabilities: Capabilities
    comfort_heat_assist_enable: bool
    comfort_heat_assist_reverse_enable: bool
    comfort_heat_assist_speed: int
    comfort_ideal_temperature: int
    comfort_max_speed: int
    comfort_min_speed: int
    current_rpm: int
    dns_sd_uuid: str
    eco_enable: bool
    fan_beep_enable: bool
    fan_mode: OffOnAuto
    fan_occupancy_detected: bool
    firmware: FirmwareProperties
    firmware_version: str
    humidity: int
    ip_address: str
    led_indicators_enable: bool
    legacy_ir_remote_enable: bool
    light_auto_motion_timeout: int
    light_brightness_level: int
    light_brightness_percent: int
    light_color_temperature: int
    light_coolest_color_temperature: int
    light_dim_to_warm_enable: bool
    light_mode: OffOnAuto
    light_occupancy_detected: bool
    light_return_to_auto_enable: bool
    light_return_to_auto_timeout: int
    light_warmest_color_temperature: int
    local_datetime: str
    mac_address: str
    model: str
    motion_sense_enable: bool
    motion_sense_timeout: int
    name: str
    remote_firmware: FirmwareProperties
    return_to_auto_enable: bool
    return_to_auto_timeout: int
    reverse_enable: bool
    speed: int
    speed_percent: int
    stats: Stats
    target_rpm: int
    temperature: int
    utc_datetime: str
    uuid9: str
    whoosh_enable: bool
    wifi: WifiProperties
    def __init__(self, name: _Optional[str] = ..., model: _Optional[str] = ..., local_datetime: _Optional[str] = ..., utc_datetime: _Optional[str] = ..., firmware_version: _Optional[str] = ..., mac_address: _Optional[str] = ..., uuid9: _Optional[str] = ..., dns_sd_uuid: _Optional[str] = ..., api_endpoint: _Optional[str] = ..., api_version: _Optional[str] = ..., firmware: _Optional[_Union[FirmwareProperties, _Mapping]] = ..., capabilities: _Optional[_Union[Capabilities, _Mapping]] = ..., fan_mode: _Optional[_Union[OffOnAuto, str]] = ..., reverse_enable: bool = ..., speed_percent: _Optional[int] = ..., speed: _Optional[int] = ..., whoosh_enable: bool = ..., eco_enable: bool = ..., auto_comfort_enable: bool = ..., comfort_ideal_temperature: _Optional[int] = ..., comfort_heat_assist_enable: bool = ..., comfort_heat_assist_speed: _Optional[int] = ..., comfort_heat_assist_reverse_enable: bool = ..., comfort_min_speed: _Optional[int] = ..., comfort_max_speed: _Optional[int] = ..., motion_sense_enable: bool = ..., motion_sense_timeout: _Optional[int] = ..., return_to_auto_enable: bool = ..., return_to_auto_timeout: _Optional[int] = ..., target_rpm: _Optional[int] = ..., current_rpm: _Optional[int] = ..., fan_occupancy_detected: bool = ..., light_mode: _Optional[_Union[OffOnAuto, str]] = ..., light_brightness_percent: _Optional[int] = ..., light_brightness_level: _Optional[int] = ..., light_color_temperature: _Optional[int] = ..., light_dim_to_warm_enable: bool = ..., light_auto_motion_timeout: _Optional[int] = ..., light_return_to_auto_enable: bool = ..., light_return_to_auto_timeout: _Optional[int] = ..., light_warmest_color_temperature: _Optional[int] = ..., light_coolest_color_temperature: _Optional[int] = ..., light_occupancy_detected: bool = ..., temperature: _Optional[int] = ..., humidity: _Optional[int] = ..., ip_address: _Optional[str] = ..., wifi: _Optional[_Union[WifiProperties, _Mapping]] = ..., led_indicators_enable: bool = ..., fan_beep_enable: bool = ..., legacy_ir_remote_enable: bool = ..., remote_firmware: _Optional[_Union[FirmwareProperties, _Mapping]] = ..., stats: _Optional[_Union[Stats, _Mapping]] = ...) -> None: ...

class Query(_message.Message):
    __slots__ = ["property_query"]
    PROPERTY_QUERY_FIELD_NUMBER: _ClassVar[int]
    property_query: ProperyQuery
    def __init__(self, property_query: _Optional[_Union[ProperyQuery, str]] = ...) -> None: ...

class QueryResult(_message.Message):
    __slots__ = ["properties", "schedules"]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    SCHEDULES_FIELD_NUMBER: _ClassVar[int]
    properties: _containers.RepeatedCompositeFieldContainer[Properties]
    schedules: _containers.RepeatedCompositeFieldContainer[Schedule]
    def __init__(self, properties: _Optional[_Iterable[_Union[Properties, _Mapping]]] = ..., schedules: _Optional[_Iterable[_Union[Schedule, _Mapping]]] = ...) -> None: ...

class Root(_message.Message):
    __slots__ = ["root2"]
    ROOT2_FIELD_NUMBER: _ClassVar[int]
    root2: Root2
    def __init__(self, root2: _Optional[_Union[Root2, _Mapping]] = ...) -> None: ...

class Root2(_message.Message):
    __slots__ = ["commit", "query", "query_result"]
    COMMIT_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    QUERY_RESULT_FIELD_NUMBER: _ClassVar[int]
    commit: Commit
    query: Query
    query_result: QueryResult
    def __init__(self, commit: _Optional[_Union[Commit, _Mapping]] = ..., query: _Optional[_Union[Query, _Mapping]] = ..., query_result: _Optional[_Union[QueryResult, _Mapping]] = ...) -> None: ...

class Schedule(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class Stats(_message.Message):
    __slots__ = ["uptime_minutes"]
    UPTIME_MINUTES_FIELD_NUMBER: _ClassVar[int]
    uptime_minutes: int
    def __init__(self, uptime_minutes: _Optional[int] = ...) -> None: ...

class WifiProperties(_message.Message):
    __slots__ = ["ssid"]
    SSID_FIELD_NUMBER: _ClassVar[int]
    ssid: str
    def __init__(self, ssid: _Optional[str] = ...) -> None: ...

class ProperyQuery(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class OffOnAuto(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
