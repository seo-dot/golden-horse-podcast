import datetime as dt
import unittest

from src import publish_schedule as ps

UTC = dt.timezone.utc


class PickPublishAt(unittest.TestCase):
    def setUp(self):
        self.tz = ps._tz()
        self.start, self.end = ps.parse_window(ps.DEFAULT_WINDOW)

    def _local_minutes(self, slot):
        l = slot.astimezone(self.tz)
        return l.hour * 60 + l.minute

    def test_slots_inside_window_and_future(self):
        for i in range(120):
            now = dt.datetime(2026, 1, 1, 5, 0, tzinfo=UTC) + dt.timedelta(days=i, minutes=i * 7)
            slot = ps.pick_publish_at(now=now)
            self.assertGreaterEqual(slot, now + dt.timedelta(minutes=ps.MIN_LEAD_MINUTES))
            self.assertLessEqual(slot - now, dt.timedelta(hours=48))
            self.assertTrue(self.start <= self._local_minutes(slot) <= self.end, slot)

    def test_deterministic_per_day(self):
        a = ps.pick_publish_at(now=dt.datetime(2026, 5, 3, 3, 0, tzinfo=UTC))
        b = ps.pick_publish_at(now=dt.datetime(2026, 5, 3, 9, 0, tzinfo=UTC))
        self.assertEqual(a, b)

    def test_varies_between_days(self):
        slots = {self._local_minutes(ps.pick_publish_at(
            now=dt.datetime(2026, 5, 1, 3, 0, tzinfo=UTC) + dt.timedelta(days=i)))
            for i in range(30)}
        self.assertGreater(len(slots), 15)

    def test_late_run_rolls_to_next_day(self):
        # запуск в 23:50 по Дубаю — окно сегодняшнего дня закрыто
        now = dt.datetime(2026, 5, 3, 19, 50, tzinfo=UTC)
        slot = ps.pick_publish_at(now=now)
        self.assertEqual(slot.astimezone(self.tz).date(), dt.date(2026, 5, 4))

    def test_run_inside_window_uses_remaining_or_next_day(self):
        now = dt.datetime(2026, 5, 3, 16, 0, tzinfo=UTC)  # 20:00 Dubai
        slot = ps.pick_publish_at(now=now)
        self.assertGreaterEqual(slot, now + dt.timedelta(minutes=ps.MIN_LEAD_MINUTES))

    def test_iso_format(self):
        s = ps.publish_at_iso(now=dt.datetime(2026, 5, 3, 3, 0, tzinfo=UTC))
        dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.000Z")

    def test_bad_window_falls_back(self):
        self.assertEqual(ps.parse_window("garbage"), self.start and (self.start, self.end))

    def test_only_public_is_scheduled(self):
        self.assertTrue(ps.schedule_enabled("public"))
        self.assertFalse(ps.schedule_enabled("private"))
        self.assertFalse(ps.schedule_enabled("unlisted"))


class SkipDays(unittest.TestCase):
    def test_one_or_two_non_adjacent_never_sunday(self):
        counts = set()
        for week in range(1, 53):
            days = ps.skip_days_for_week(2026, week)
            counts.add(len(days))
            self.assertIn(len(days), (1, 2))
            self.assertNotIn(6, days)
            if len(days) == 2:
                self.assertGreater(days[1] - days[0], 1)
        self.assertEqual(counts, {1, 2})

    def test_deterministic(self):
        self.assertEqual(ps.skip_days_for_week(2026, 10), ps.skip_days_for_week(2026, 10))

    def test_should_skip_matches_week_plan(self):
        if not ps.SKIP_DAYS_SUPPORTED:
            self.assertFalse(ps.should_skip_today(dt.datetime(2026, 5, 4, 8, 0, tzinfo=UTC)))
            return
        skipped = 0
        for i in range(70):
            now = dt.datetime(2026, 3, 2, 8, 0, tzinfo=UTC) + dt.timedelta(days=i)
            skipped += ps.should_skip_today(now)
        self.assertTrue(10 <= skipped <= 20, skipped)  # 10 недель по 1–2 дня


if __name__ == "__main__":
    unittest.main()
