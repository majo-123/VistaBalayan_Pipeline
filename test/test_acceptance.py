import csv
import tempfile
import unittest
from pathlib import Path

from pipeline.transform import run


FIELDS = {
    "establishments": ["id", "name", "type", "status"],
    "visitor_reports": ["id", "establishment_id", "report_date", "status", "total_visitors"],
    "accommodation_reports": ["id", "establishment_id", "report_date", "status", "total_rooms", "occupied_rooms"],
    "room_occupancy_details": ["id", "accommodation_report_id", "room_type", "number_of_rooms", "occupied_rooms"],
}


def make_raw(raw: Path, invalid: bool = False) -> None:
    rows = {
        "establishments": [{"id": "e1", "name": "Stay", "type": "Hotel", "status": "active"}],
        "visitor_reports": [{"id": "v1", "establishment_id": "e1", "report_date": "2026-10-22", "status": "submitted", "total_visitors": "bad" if invalid else "4"}],
        "accommodation_reports": [{"id": "a1", "establishment_id": "e1", "report_date": "2026-10-22", "status": "submitted", "total_rooms": "10", "occupied_rooms": "2"}],
        "room_occupancy_details": [{"id": "r1", "accommodation_report_id": "a1", "room_type": "Deluxe", "number_of_rooms": "10", "occupied_rooms": "2"}],
    }
    raw.mkdir(parents=True, exist_ok=True)
    for name, values in rows.items():
        with (raw / f"{name}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS[name])
            writer.writeheader()
            writer.writerows(values)


class AcceptanceTests(unittest.TestCase):
    def handover(self, root: Path, decision: str = "APPROVED FOR TRANSFORMATION", pipeline_run_id: str = "EXT_FIXTURE_001") -> Path:
        path = root / "handover.md"
        path.write_text(
            f"Stage 1 Decision: {decision}\n"
            f"pipeline_run_id: {pipeline_run_id}\n",
            encoding="utf-8",
        )
        return path

    def test_valid_fixture_is_approved_for_load(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_raw(root / "raw")
            result = run(root / "missing.sqlite", root / "raw", root / "out", root / "logs", "TRN_VALID", "EXT_FIXTURE_001", self.handover(root))
            self.assertEqual(result["acceptance_decision"], "APPROVED FOR LOAD")
            self.assertEqual(result["quarantine_count"], 0)

    def test_invalid_fixture_returns_manual_review_with_quarantine(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_raw(root / "raw", invalid=True)
            result = run(root / "missing.sqlite", root / "raw", root / "out", root / "logs", "TRN_INVALID", "EXT_FIXTURE_001", self.handover(root))
            self.assertEqual(result["acceptance_decision"], "MANUAL REVIEW")
            self.assertEqual(result["quarantine_count"], 1)
            self.assertIn("C-06", (root / "out" / "transformation_quarantine.csv").read_text(encoding="utf-8"))

    def test_parent_run_id_mismatch_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_raw(root / "raw")
            result = run(root / "missing.sqlite", root / "raw", root / "out", root / "logs", "TRN_MISMATCH", "EXT_OTHER", self.handover(root))
            self.assertEqual(result["error_code"], "PARENT_RUN_ID_MISMATCH")
            self.assertFalse((root / "out").exists())

    def test_unapproved_handover_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run(root / "missing.sqlite", root / "raw", root / "out", root / "logs", "TRN_BLOCKED", "EXT_FIXTURE_001", self.handover(root, "MANUAL REVIEW"))
            self.assertEqual(result["error_code"], "STAGE1_NOT_APPROVED")
            self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
