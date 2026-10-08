"""Проверки PUSH по реальным пакетам и независимым примерам A-XDR."""

import unittest

from push_parser import PushParseError, parse_push_packet


SHORT_2012 = bytes.fromhex(
    "00010001004000730f400000010c07ea0a07030e3611fffed400020301030206120028"
    "09060000190900ff0f0112000002021600000100020612000109060000600100ff0f02"
    "12000002021600000100020612000109060000616214ff0f02120000020216000001"
    "00090b39373630303030313935310600002012"
)
SHORT_10 = bytes.fromhex(
    "00010001004000730f400000010c07ea0a07030f1209fffed400020301030206120028"
    "09060000190900ff0f0112000002021600000100020612000109060000600100ff0f02"
    "12000002021600000100020612000109060000616214ff0f02120000020216000001"
    "00090b39373630303030313935310600000010"
)
SINGLE_PHASE = bytes.fromhex(
    "00010001004000730f400000010c07ea0a0703100500ffff4c00020301030206120028"
    "09060000190900ff0f0112000002021600000100020612000109060000600100ff0f02"
    "12000002021600000100020612000109060000616214ff0f02120000020216000001"
    "00090b39373130303030303030330600010000"
)
LONG_ENERGY = bytes.fromhex(
    "000100010040018f0f400000010c07ea0a07030e3129fffed400020c010c0206120028"
    "09060001190900ff0f0212000002021600000100020612000109060001600586ff0f02"
    "120000020216000001000206120001090600002a0000ff0f02120000020216000001"
    "00020612000109060000600100ff0f02120000020216000001000206120003090601"
    "00010800ff0f0212000002021600000100020612000309060100010800ff0f031200"
    "0002021600000100020612000309060100020800ff0f021200000202160000010002"
    "0612000309060100020800ff0f031200000202160000010002061200030906010003"
    "0800ff0f0212000002021600000100020612000309060100030800ff0f031200000202"
    "1600000100020612000309060100040800ff0f02120000020216000001000206120003"
    "09060100040800ff0f031200000202160000010016020910454c433038323653334430"
    "3031393531090b3937363030303031393531060000005102020f01161e060000000d"
    "02020f01161e060000005502020f011620060000000602020f011620"
)

SERIAL = bytes((0, 0, 96, 1, 0, 255))
PENDING = bytes((0, 0, 97, 98, 20, 255))
REGISTER = bytes((0, 0, 97, 98, 0, 255))
MODEL = bytes((0, 0, 42, 0, 0, 255))
ENERGY = bytes((1, 0, 1, 8, 0, 255))


def _length(size):
    if size < 128:
        return bytes((size,))
    return b"\x82" + size.to_bytes(2, "big")


def _octets(value):
    return b"\x09" + _length(len(value)) + value


def _uint32(value):
    return b"\x06" + value.to_bytes(4, "big")


def _object(obis, class_id=1, attribute=2, data_index=0, extended=False):
    fields = (
        b"\x12" + class_id.to_bytes(2, "big") + _octets(obis)
        + b"\x0f" + attribute.to_bytes(1, "big", signed=True)
        + b"\x12" + data_index.to_bytes(2, "big")
    )
    if extended:
        return b"\x02\x06" + fields + b"\x02\x02\x16\x00\x00\x01\x00"
    return b"\x02\x04" + fields


def _wrap(payload):
    return b"\x00\x01\x00\x01\x00\x40" + len(payload).to_bytes(2, "big") + payload


def _packet(entries, extended=False):
    # entries: (capture bytes, encoded value bytes), independent of parser.
    own = _object(bytes((0, 0, 25, 9, 0, 255)), class_id=40, extended=extended)
    captures = b"\x01" + _length(len(entries) + 1) + own
    captures += b"".join(capture for capture, value in entries)
    body = b"\x02" + _length(len(entries) + 1) + captures
    body += b"".join(value for capture, value in entries)
    return _wrap(b"\x0f\x40\x00\x00\x01\x00" + body)


def _serial(number=b"97600001951"):
    return _object(SERIAL), _octets(number)


def _alarm(mask=16, obis=PENDING, **kwargs):
    return _object(obis, **kwargs), _uint32(mask)


class PushPacketParserTests(unittest.TestCase):
    def test_real_three_phase_alarm(self):
        result = parse_push_packet(SHORT_2012)
        self.assertEqual((result.serial, result.bitmask), ("97600001951", 0x2012))
        self.assertEqual(result.alarm_obis, "0.0.97.98.20.255")

    def test_real_cover_open_alarm(self):
        self.assertEqual(parse_push_packet(SHORT_10).bitmask, 16)

    def test_real_single_phase_alarm(self):
        result = parse_push_packet(SINGLE_PHASE)
        self.assertEqual((result.serial, result.bitmask), ("97100000003", 0x10000))

    def test_real_zero_mask_is_present(self):
        result = parse_push_packet(SHORT_10[:-4] + bytes(4))
        self.assertEqual(result.bitmask, 0)
        self.assertIsNotNone(result.alarm_obis)

    def test_real_energy_packet_has_no_alarm(self):
        self.assertEqual(len(LONG_ENERGY), 407)
        result = parse_push_packet(LONG_ENERGY)
        self.assertEqual(result.serial, "97600001951")
        self.assertIsNone(result.bitmask)
        self.assertIsNone(result.alarm_obis)

    def test_later_numeric_value_does_not_replace_alarm(self):
        packet = _packet([_serial(), _alarm(), (_object(ENERGY, class_id=3), _uint32(0x02020F01))])
        self.assertEqual(parse_push_packet(packet).bitmask, 16)

    def test_marker_inside_mask_is_not_another_value(self):
        self.assertEqual(parse_push_packet(_packet([_serial(), _alarm(0x06000001)])).bitmask, 0x06000001)

    def test_other_eleven_digits_are_not_meter_number(self):
        packet = _packet([(_object(MODEL), _octets(b"97112345678")), _serial(), _alarm()])
        self.assertEqual(parse_push_packet(packet).serial, "97600001951")

    def test_reordered_objects(self):
        self.assertEqual(parse_push_packet(_packet([_alarm(), _serial()])).bitmask, 16)

    def test_register_fallback(self):
        result = parse_push_packet(_packet([_serial(), _alarm(0x2000, REGISTER)]))
        self.assertEqual(result.bitmask, 0x2000)
        self.assertEqual(result.alarm_obis, "0.0.97.98.0.255")

    def test_pending_zero_has_priority_over_nonzero_register(self):
        packet = _packet([_serial(), _alarm(0x2000, REGISTER), _alarm(0)])
        self.assertEqual(parse_push_packet(packet).bitmask, 0)

    def test_other_attributes_and_indices_are_not_alarm(self):
        packet = _packet([_serial(), _alarm(attribute=3), _alarm(data_index=1)])
        self.assertIsNone(parse_push_packet(packet).bitmask)

    def test_signed_mask_rejected(self):
        packet = _packet([_serial(), (_object(PENDING), b"\x05\x00\x00\x00\x10")])
        with self.assertRaises(PushParseError):
            parse_push_packet(packet)

    def test_missing_serial_object_rejected(self):
        packet = _packet([(_object(MODEL), _octets(b"97600001951")), _alarm()])
        with self.assertRaises(PushParseError):
            parse_push_packet(packet)

    def test_invalid_serial_rejected(self):
        for number in (b"9760000195", b"9760000195x", b"9760000195\xff"):
            with self.subTest(number=number), self.assertRaises(PushParseError):
                parse_push_packet(_packet([_serial(number), _alarm()]))

    def test_conflicting_duplicate_alarm_rejected(self):
        with self.assertRaises(PushParseError):
            parse_push_packet(_packet([_serial(), _alarm(16), _alarm(32)]))

    def test_identical_duplicate_alarm_allowed(self):
        self.assertEqual(parse_push_packet(_packet([_serial(), _alarm(), _alarm()])).bitmask, 16)

    def test_conflicting_duplicate_serial_rejected(self):
        with self.assertRaises(PushParseError):
            parse_push_packet(_packet([_serial(), _serial(b"97100000003"), _alarm()]))

    def test_object_count_mismatch_rejected(self):
        packet = bytearray(_packet([_serial(), _alarm()]))
        packet[17] = 4  # Root count is 3, descriptor count changed to 4.
        with self.assertRaises(PushParseError):
            parse_push_packet(bytes(packet))

    def test_trailing_bytes_rejected(self):
        packet = _packet([_serial(), _alarm()])
        with self.assertRaises(PushParseError):
            parse_push_packet(_wrap(packet[8:] + b"\x00"))

    def test_bad_wrapper_rejected(self):
        for packet in (b"", SHORT_10[:7], SHORT_10[:-1], b"\x00\x02" + SHORT_10[2:]):
            with self.subTest(packet=packet[:8]), self.assertRaises(PushParseError):
                parse_push_packet(packet)

    def test_unknown_apdu_and_missing_schema_rejected(self):
        packets = (
            _wrap(b"\xdb" + SHORT_10[9:]),
            _wrap(b"\x0f\x40\x00\x00\x01\x00\x02\x02" + _octets(b"97600001951") + _uint32(16)),
        )
        for packet in packets:
            with self.subTest(packet=packet[:16]), self.assertRaises(PushParseError):
                parse_push_packet(packet)

    def test_long_length_for_unrelated_string(self):
        packet = _packet([(_object(MODEL), _octets(b"x" * 128)), _serial(), _alarm()], extended=True)
        self.assertEqual(parse_push_packet(packet).bitmask, 16)

    def test_malformed_axdr_rejected(self):
        for value in (b"\x09\x80", b"\x09\x85\x00\x00\x00\x00\x01x", b"\x13", b"\x02\x7f"):
            with self.subTest(value=value), self.assertRaises(PushParseError):
                parse_push_packet(_packet([_serial(), _alarm(), (_object(MODEL), value)]))

    def test_excessive_nesting_rejected(self):
        nested = b"\x02\x01" * 40 + b"\x00"
        with self.assertRaises(PushParseError):
            parse_push_packet(_packet([_serial(), _alarm(), (_object(MODEL), nested)]))

    def test_every_truncated_body_rejected(self):
        for end in range(9, len(LONG_ENERGY)):
            with self.subTest(end=end), self.assertRaises(PushParseError):
                parse_push_packet(_wrap(LONG_ENERGY[8:end]))


if __name__ == "__main__":
    unittest.main()

