"""Тесты разбора входящих PUSH-пакетов."""

import unittest

from push_server import extract_bitmask, extract_serial


class PushPacketParserTests(unittest.TestCase):
    """Проверяет извлечение данных из PUSH-пакета."""

    def test_extract_serial_finds_eleven_digit_meter_number(self):
        """Должен находить номер счётчика внутри пакета."""
        packet = b"\x01\x02header97600000003payload"

        self.assertEqual(
            extract_serial(packet),
            "97600000003",
        )

    def test_extract_serial_returns_empty_string_without_meter_number(self):
        """Пакет без 11 цифр подряд не должен давать серийный номер."""
        packet = b"meter-976000000"

        self.assertEqual(
            extract_serial(packet),
            "",
        )

    def test_extract_bitmask_reads_value_after_marker(self):
        """Должен читать 32-битную маску после байта 0x06."""
        packet = b"\x01\x06\x00\x00\x00\x05\xFF"

        self.assertEqual(
            extract_bitmask(packet),
            5,
        )

    def test_extract_bitmask_uses_last_marker(self):
        """При нескольких маркерах используется последняя маска."""
        packet = (
            b"\x06\x00\x00\x00\x05"
            b"\x10\x20"
            b"\x06\x00\x00\x00\x0A"
        )

        self.assertEqual(
            extract_bitmask(packet),
            10,
        )

    def test_extract_bitmask_returns_zero_without_marker(self):
        """Пакет без маркера 0x06 должен возвращать ноль."""
        self.assertEqual(
            extract_bitmask(b"\x01\x02\x03"),
            0,
        )


if __name__ == "__main__":
    unittest.main()