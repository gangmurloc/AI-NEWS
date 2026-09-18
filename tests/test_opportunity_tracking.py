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
    is_excluded_local_opportunity,
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

    def test_excludes_opportunity_limited_to_non_capital_region(self):
        body = "부산광역시 거주 청년만 참가할 수 있는 AI 창업 경진대회입니다."
        self.assertTrue(is_excluded_local_opportunity("부산 AI 경진대회", body))

    def test_excludes_unknown_local_city_residents(self):
        body = "동해시민 및 동해시 소재 대학 재학생만 신청할 수 있습니다."
        self.assertTrue(is_excluded_local_opportunity("AI 특강 참가자 모집", body))

    def test_keeps_seoul_or_gyeonggi_local_opportunity(self):
        self.assertFalse(
            is_excluded_local_opportunity(
                "AI 교육생 모집", "수원시 거주 청년과 수원시 소재 대학생 대상"
            )
        )

    def test_keeps_gyeonggi_gwangju_residents(self):
        self.assertFalse(
            is_excluded_local_opportunity(
                "AI 교육생 모집", "경기도 광주시 거주 청년을 모집합니다."
            )
        )

    def test_excludes_named_non_capital_region_group(self):
        self.assertTrue(
            is_excluded_local_opportunity(
                "AI 창업 교육", "부산 청년 대상으로 참가자를 모집합니다."
            )
        )

    def test_keeps_nationwide_opportunity_held_outside_capital_region(self):
        body = "행사는 부산에서 오프라인으로 열리며 전국 누구나 참가할 수 있습니다."
        self.assertFalse(is_excluded_local_opportunity("전국 AI 해커톤", body))

    def test_keeps_outside_event_when_target_is_not_region_restricted(self):
        body = "부산에서 오프라인으로 개최하며 대학생 대상 AI 강연입니다."
        self.assertFalse(is_excluded_local_opportunity("AI 공개 강연", body))


class OpportunityTrackerTests(unittest.TestCase):
    def _item(self, deadline):
        return {
            "title": "테스트 AI 경진대회",
            "link": "https://example.com/notice/1",
            "body": f"참가 신청 마감은 {deadline.year}. {deadline.month}. {deadline.day}. 입니다. 참가신청서 제출",
            "application_links": ["https://example.com/apply/1"],
        }

    def test_ignores_deadline_only_change(self):
        state = {"records": {}}
        first = config.today_kst() + timedelta(days=7)
        changes, _ = upsert_items(state, [self._item(first)])
        self.assertEqual(changes, [])

        changed = config.today_kst() + timedelta(days=10)
        changes, _ = upsert_items(state, [self._item(changed)])
        self.assertEqual(changes, [])

    def test_detects_only_substantial_notice_rewrite(self):
        state = {"records": {}}
        old_body = (
            "참가자는 공개 데이터로 AI 분류 모델을 개발하고 결과 보고서를 제출합니다. "
            "개인 또는 세 명 이하 팀으로 참가하며 온라인 예선을 거쳐 발표 평가를 진행합니다. "
            "참가신청서와 개인정보 동의서를 제출하고 모든 산출물은 지정 양식을 따라야 합니다. "
        ) * 2
        new_body = (
            "교육 과정은 생성형 AI 서비스 기획과 윤리 강의로 전면 개편되었습니다. "
            "수강생은 매주 오프라인 실습에 출석하고 마지막 주에 사업 아이디어를 발표합니다. "
            "별도 경진이나 모델 제출은 없으며 출석률을 기준으로 수료증을 발급합니다. "
        ) * 2
        item = {
            "title": "AI 프로그램 참가자 모집",
            "link": "https://example.com/notice/rewrite",
            "body": old_body,
            "application_links": ["https://example.com/apply/rewrite"],
        }
        upsert_items(state, [item])

        changes, _ = upsert_items(state, [{**item, "body": new_body}])

        self.assertEqual(len(changes), 1)
        self.assertIn("대폭 변경", changes[0]["differences"][0])

    def test_does_not_track_non_capital_local_only_opportunity(self):
        state = {"records": {}}
        item = {
            "title": "부산 AI 경진대회",
            "link": "https://example.com/notice/busan",
            "body": "부산광역시 소재 대학 재학생만 참가할 수 있습니다.",
            "application_links": [],
        }

        changes, new_keys = upsert_items(state, [item])

        self.assertEqual(changes, [])
        self.assertEqual(new_keys, set())
        self.assertEqual(state["records"], {})

    def test_removes_tracked_item_when_it_becomes_region_restricted(self):
        state = {"records": {}}
        item = {
            "title": "AI 경진대회",
            "link": "https://example.com/notice/region-change",
            "body": "전국 누구나 참가할 수 있는 AI 경진대회입니다.",
            "application_links": [],
        }
        upsert_items(state, [item])
        self.assertEqual(len(state["records"]), 1)

        restricted = {
            **item,
            "body": "부산광역시 소재 대학 재학생만 참가할 수 있는 AI 경진대회입니다.",
        }
        changes, _ = upsert_items(state, [restricted])

        self.assertEqual(changes, [])
        self.assertEqual(state["records"], {})

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
