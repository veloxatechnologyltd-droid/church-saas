import unittest
from datetime import time

from app.crud.communication import _membership_status_for_audience
from app.schemas.communication import ReminderScheduleCreate, ReminderScheduleUpdate, SMSCreate


class CommunicationAudienceTests(unittest.TestCase):
    def test_member_status_audiences_are_valid_for_sms(self):
        for audience_type in ("all_members", "active_members", "inactive_members"):
            with self.subTest(audience_type=audience_type):
                payload = SMSCreate(message="Church announcement", audience_type=audience_type)
                self.assertEqual(payload.audience_type, audience_type)

    def test_member_status_audiences_are_valid_for_reminders(self):
        for audience_type in ("all_members", "active_members", "inactive_members"):
            with self.subTest(audience_type=audience_type):
                payload = ReminderScheduleCreate(
                    name="Weekly reminder",
                    message_template="Church announcement",
                    weekday=6,
                    send_time=time(18, 0),
                    audience_type=audience_type,
                )
                self.assertEqual(payload.audience_type, audience_type)
                self.assertEqual(
                    ReminderScheduleUpdate(audience_type=audience_type).audience_type,
                    audience_type,
                )

    def test_only_active_and_inactive_audiences_apply_status_filters(self):
        self.assertIsNone(_membership_status_for_audience("all_members"))
        self.assertEqual(_membership_status_for_audience("active_members"), "active")
        self.assertEqual(_membership_status_for_audience("inactive_members"), "inactive")
        self.assertIsNone(_membership_status_for_audience("department"))
        self.assertIsNone(_membership_status_for_audience("selected_members"))


if __name__ == "__main__":
    unittest.main()
