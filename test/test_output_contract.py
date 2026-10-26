import csv
import tempfile
import unittest
from pathlib import Path

from pipeline.transform import OUTPUT_COLUMNS, OUTPUT_FILENAMES, validate_output_headers, validate_outputs


class OutputContractTests(unittest.TestCase):
    def test_empty_outputs_keep_required_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for dataset, columns in OUTPUT_COLUMNS.items():
                with (output / OUTPUT_FILENAMES[dataset]).open("w", newline="", encoding="utf-8") as handle:
                    csv.writer(handle).writerow(columns)
            self.assertEqual(set(validate_output_headers(output).values()), {"PASS"})

    def test_orphan_child_is_rejected_by_referential_integrity(self):
        transformed = {
            "establishments": [{"id": "e1", "name": "Stay", "type": "Hotel", "status": "active"}],
            "visitor_reports": [{"id": "v1", "establishment_id": "missing", "report_date": "2026-10-22", "status": "submitted"}],
            "accommodation_reports": [],
            "room_occupancy_details": [],
        }
        stats = {name: {"records_read": len(rows), "records_output": len(rows), "records_rejected": 0} for name, rows in transformed.items()}
        result = validate_outputs(transformed, [], stats)
        self.assertEqual(result["checks"]["visitor_reports.referential_integrity"], "FAIL")
        self.assertEqual(result["acceptance_decision"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
