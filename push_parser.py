"""Разбор открытых DLMS Data Notification со списком объектов PUSH."""

from dataclasses import dataclass
from typing import Any

SERIAL_OBIS = bytes((0, 0, 96, 1, 0, 255))
# Дескриптор ожидающих отправки тревог имеет приоритет перед регистром.
ALARM_OBIS = (bytes((0, 0, 97, 98, 20, 255)), bytes((0, 0, 97, 98, 0, 255)))


class PushParseError(ValueError):
    """Пакет повреждён или имеет неподдерживаемую структуру."""


@dataclass(frozen=True)
class ParsedPush:
    serial: str
    bitmask: int | None
    alarm_obis: str | None


@dataclass(frozen=True)
class _Value:
    tag: int
    value: Any


@dataclass(frozen=True)
class _Capture:
    class_id: int
    obis: bytes
    attribute: int
    data_index: int


class _Reader:
    """Читает значения A-XDR, сохраняя тип каждого значения."""

    _INTEGERS = {
        5: (4, True), 6: (4, False), 15: (1, True), 16: (2, True),
        17: (1, False), 18: (2, False), 20: (8, True),
        21: (8, False), 22: (1, False),
    }
    _FIXED_BYTES = {13: 1, 23: 4, 24: 8, 25: 12, 26: 5, 27: 4}

    def __init__(self, data: bytes):
        self.data = data
        self.position = 0
        self.budget = 10000

    @property
    def remaining(self) -> int:
        return len(self.data) - self.position

    def take(self, size: int) -> bytes:
        if size < 0 or size > self.remaining:
            raise PushParseError("Значение A-XDR обрезано.")
        result = self.data[self.position:self.position + size]
        self.position += size
        return result

    def byte(self) -> int:
        return self.take(1)[0]

    def count(self) -> int:
        first = self.byte()
        if first < 128:
            return first
        width = first & 127
        if not 1 <= width <= 4:
            raise PushParseError("Неподдерживаемая длина A-XDR.")
        size = int.from_bytes(self.take(width), "big")
        if size > 65535:
            raise PushParseError("Слишком большая длина A-XDR.")
        return size

    def value(self, depth: int = 0) -> _Value:
        self.budget -= 1
        if depth > 32 or self.budget < 0:
            raise PushParseError("Превышены ограничения структуры A-XDR.")
        tag = self.byte()
        if tag == 0:
            return _Value(tag, None)
        if tag in (1, 2):
            count = self.count()
            if count > self.remaining or count > self.budget:
                raise PushParseError("Некорректное число элементов A-XDR.")
            return _Value(tag, tuple(self.value(depth + 1) for _ in range(count)))
        if tag == 3:
            return _Value(tag, self.byte() != 0)
        if tag == 4:
            bits = self.count()
            return _Value(tag, (bits, self.take((bits + 7) // 8)))
        if tag in self._INTEGERS:
            size, signed = self._INTEGERS[tag]
            return _Value(tag, int.from_bytes(self.take(size), "big", signed=signed))
        if tag in (9, 10, 12):
            return _Value(tag, self.take(self.count()))
        if tag in self._FIXED_BYTES:
            return _Value(tag, self.take(self._FIXED_BYTES[tag]))
        raise PushParseError(f"Неподдерживаемый тип A-XDR: {tag}.")


def _capture(value: _Value) -> _Capture:
    if value.tag != 2 or len(value.value) < 4:
        raise PushParseError("Некорректное описание объекта PUSH.")
    class_id, obis, attribute, data_index = value.value[:4]
    if (
        class_id.tag != 18 or obis.tag != 9 or len(obis.value) != 6
        or attribute.tag != 15 or data_index.tag != 18
    ):
        raise PushParseError("Некорректные поля описания объекта PUSH.")
    return _Capture(class_id.value, obis.value, attribute.value, data_index.value)


def _find_value(captures, values, obis: bytes) -> _Value | None:
    matches = [
        value for capture, value in zip(captures, values)
        if capture.class_id == 1 and capture.obis == obis
        and capture.attribute == 2 and capture.data_index == 0
    ]
    if not matches:
        return None
    if any(value != matches[0] for value in matches[1:]):
        raise PushParseError("Один объект PUSH содержит разные значения.")
    return matches[0]


def parse_push_packet(data: bytes) -> ParsedPush:
    """Извлекает номер и маску из соответствующих объектов DLMS.

    Поддерживает открытый Data Notification в DLMS Wrapper со списком
    объектов в первом значении. Отсутствующая маска возвращается как None,
    присутствующая нулевая маска — как 0. Схему пакета не угадываем.
    """
    if len(data) < 8 or int.from_bytes(data[:2], "big") != 1:
        raise PushParseError("Некорректный заголовок DLMS Wrapper.")
    payload_size = int.from_bytes(data[6:8], "big")
    if payload_size == 0 or payload_size != len(data) - 8:
        raise PushParseError("Длина DLMS Wrapper не совпадает с размером пакета.")

    reader = _Reader(data[8:])
    if reader.byte() != 15:
        raise PushParseError("Ожидался открытый DLMS Data Notification.")
    reader.take(4)  # long-invoke-id-and-priority
    time_size = reader.byte()
    if time_size not in (0, 12):
        raise PushParseError("Некорректная длина времени Data Notification.")
    reader.take(time_size)
    body = reader.value()
    if reader.remaining:
        raise PushParseError("Лишние байты после тела Data Notification.")
    if body.tag != 2 or not body.value or body.value[0].tag != 1:
        raise PushParseError("В PUSH отсутствует список передаваемых объектов.")

    values = body.value
    captures = tuple(_capture(item) for item in values[0].value)
    if not captures or len(captures) != len(values):
        raise PushParseError("Число объектов PUSH не совпадает с числом значений.")
    first = captures[0]
    # В реальных пакетах список приходит при атрибуте 1 или 2.
    if (
        first.class_id != 40 or first.obis[0] != 0
        or first.obis[2:] != bytes((25, 9, 0, 255))
        or first.attribute not in (1, 2) or first.data_index != 0
    ):
        raise PushParseError("Первое значение не описано как список Push Setup.")

    serial_value = _find_value(captures, values, SERIAL_OBIS)
    if serial_value is None or serial_value.tag not in (9, 10, 12):
        raise PushParseError("В PUSH отсутствует строковый объект номера счётчика.")
    try:
        serial = serial_value.value.decode("ascii")
    except UnicodeDecodeError as error:
        raise PushParseError("Номер счётчика содержит символы вне ASCII.") from error
    if len(serial) != 11 or not all("0" <= char <= "9" for char in serial):
        raise PushParseError("Номер счётчика должен содержать ровно 11 цифр.")

    for obis in ALARM_OBIS:
        alarm = _find_value(captures, values, obis)
        if alarm is not None:
            if alarm.tag != 6:
                raise PushParseError("Маска тревог имеет тип, отличный от uint32.")
            return ParsedPush(serial, alarm.value, ".".join(map(str, obis)))
    return ParsedPush(serial, None, None)
