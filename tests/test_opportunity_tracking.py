import unittest
from datetime import date, timedelta
import os
from unittest.mock import patch

from bs4 import BeautifulSoup

os.environ.setdefault("LLM_API_KEY", "test-key-not-used")

import config
import live_monitor
from opportunity_tracker import collect_deadline_reminders, upsert_items
from sources.korea_opportunities import (
    _rank_application_links,
    build_preparation_checklist,
    extract_deadline,
)


class OpportunityExtractionTests(unittest.TestCase):
    def test_extracts_end_of_application_period(self):
        text = "접수 기간: 2026. 9. 1. ~ 2026. 9. 24. 참가 신청은 온라인으로 진행"
        self.assertEqual(extract_deadline(text, date(2026, 9, 17)), "2026-09-24")

    def test_builds_checklist_only_from_present_documents(self):
        text = "참가신청서와 개인정보 수집 동의서, 발표자료(PPT)를 제출해야 합니다."
        checklist = build_preparation_checklist(text)
        self.assertIn("참가신청서 작성", checklist)
        self.assertIn("개인정보 수집·이용 동의서 준비", checklist)
        self.assertIn("발표자료 준비", checklist)
        self.assertNotIn("소스 코드 및 저장소 정리", checklist)

    def test_prefers_explicit_application_link(self):
        soup = BeautifulSoup(
            '<main><a href="/story">관련 기사</a>'
            '<a href="https://forms.gle/example">참가 신청하기</a></main>',
            "html.parser",
        )
        links = _rank_application_links(soup, "https://news.example.com/article")
        self.assertEqual(links[0], "https://forms.gle/example")


class OpportunityTrackerTests(unittest.TestCase):
    def _item(self, deadline):
        return {
            "title": "테스트 AI 경진대회",
            "link": "https://example.com/notice/1",
            "body": f"참가 신청 마감은 {deadline.year}. {deadline.month}. {deadline.day}. 입니다. 참가신청서 제출",
            "application_links": ["https://example.com/apply/1"],
        }

    def test_detects_deadline_change(self):
        state = {"records": {}}
        first = config.today_kst() + timedelta(days=7)
        changes, _ = upsert_items(state, [self._item(first)])
        self.assertEqual(changes, [])

        changed = config.today_kst() + timedelta(days=10)
        changes, _ = upsert_items(state, [self._item(changed)])
        self.assertTrue(any("접수 마감일" in line for line in changes[0]["differences"]))

    def test_creates_d7_reminder(self):
        state = {"records": {}}
        deadline = config.today_kst() + timedelta(days=7)
        _, new_keys = upsert_items(state, [self._item(deadline)])
        self.assertEqual(collect_deadline_reminders(state, new_keys), [])
        self.assertEqual(collect_deadline_reminders(state), [])

        record = next(iter(state["records"].values()))
        record["sent_reminders"] = []
        reminders = collect_deadline_reminders(state)
        self.assertEqual(reminders[0]["days_left"], 7)

    @patch.object(live_monitor, "_save_cursor")
    @patch.object(live_monitor, "save_state")
    @patch.object(live_monitor, "mark_reminders_sent")
    @patch.object(live_monitor.history, "mark_sent")
    @patch.object(live_monitor, "send_message")
    @patch.object(live_monitor, "refresh_due_records", return_value=[])
    @patch.object(live_monitor, "upsert_items", return_value=([], set()))
    @patch.object(live_monitor, "load_state", return_value={"records": {}})
    @patch.object(live_monitor, "build_live_update", return_value=("", [], [], []))
    def test_sends_reminder_without_new_articles(
        self,
        _build,
        _load,
        _upsert,
        _refresh,
        send_message,
        _mark_history,
        mark_reminders,
        _save_state,
        _save_cursor,
    ):
        reminder = {
            "key": "notice-1",
            "token": "2026-09-24:D-7",
            "days_left": 7,
            "title": "AI contest",
            "deadline": "2026-09-24",
            "checklist": ["check application"],
            "application_link": "https://example.com/apply",
        }
        with patch.object(live_monitor, "collect_deadline_reminders", return_value=[reminder]):
            self.assertTrue(live_monitor.check_once())
        send_message.assert_called_once()
        mark_reminders.assert_called_once()


if __name__ == "__main__":
    unittest.main()
