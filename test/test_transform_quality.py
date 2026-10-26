import unittest

from pipeline.transform import parse_nonnegative_int, transform_rows


class TransformQualityTests(unittest.TestCase):
    def test_count_parser_rejects_negative_fractional_and_text_values(self):
        self.assertEqual(parse_nonnegative_int(" 12 "), 12)
        self.assertIsNone(parse_nonnegative_int("-1"))
        self.assertIsNone(parse_nonnegative_int("2.5"))
        self.assertIsNone(parse_nonnegative_int("abc"))

    def test_text_fields_are_not_inferred_as_numeric(self):
        rows, rejected, _ = transform_rows([
            {
                "id": "v1",
                "establishment_id": "e1",
                "report_date": "2026/10/22",
                "status": " submitted ",
                "guest_name": "Guest 2",
                "guest_group_name": "Room 101 guests",
                "room_code": "ROOM-2",
                "room_type": "Deluxe",
            }
        ], "visitor_reports", "TRN_TEST", "BATCH_TEST", {"e1"})
        self.assertEqual(rejected, [])
        self.assertEqual(rows[0]["guest_name"], "Guest 2")
        self.assertEqual(rows[0]["room_code"], "ROOM-2")
        self.assertEqual(rows[0]["report_date"], "2026-10-22")

    def test_invalid_numeric_measure_is_quarantined(self):
        rows, rejected, _ = transform_rows([
            {"id": "v1", "establishment_id": "e1", "report_date": "2026-10-22", "status": "submitted", "total_visitors": "2.5"}
        ], "visitor_reports", "TRN_TEST", "BATCH_TEST", {"e1"})
        self.assertEqual(rows, [])
        self.assertEqual(rejected[0]["rule_id"], "C-06")


if __name__ == "__main__":
    unittest.main()
