import unittest
from datetime import date, timedelta

from pydantic import ValidationError

from app.crud.pastoral import due_state
from app.schemas.pastoral import PastoralLogCreate, PastoralLogUpdate


class PastoralWorkflowTests(unittest.TestCase):
    def test_due_state_distinguishes_overdue_today_upcoming_and_completed(self):
        today = date(2026, 7, 29)
        self.assertEqual(due_state(today - timedelta(days=1), "open", today), "overdue")
        self.assertEqual(due_state(today, "open", today), "due_today")
        self.assertEqual(due_state(today + timedelta(days=1), "open", today), "upcoming")
        self.assertEqual(due_state(None, "open", today), "unscheduled")
        self.assertEqual(due_state(today - timedelta(days=1), "completed", today), "completed")

    def test_create_accepts_assignment_priority_and_attendance_source(self):
        payload = PastoralLogCreate(
            member_id="00000000-0000-0000-0000-000000000001",
            log_type="call",
            notes="Attendance follow-up",
            priority="high",
            source="attendance",
            log_date=date(2026, 7, 29),
        )
        self.assertEqual(payload.priority, "high")
        self.assertEqual(payload.source, "attendance")

    def test_invalid_priority_is_rejected(self):
        with self.assertRaises(ValidationError):
            PastoralLogUpdate(priority="immediate")


if __name__ == "__main__":
    unittest.main()
