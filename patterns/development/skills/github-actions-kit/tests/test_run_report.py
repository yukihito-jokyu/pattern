"""run-report アクションのスクリプトのテスト。REST API は偽物（FakeApi）に置き換える。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import run_report
from tests.support import FakeApi, job_payload


class FailedNeedsTest(unittest.TestCase):
    def test_returns_jobs_that_neither_succeeded_nor_skipped(self) -> None:
        needs = {"lint": {"result": "success"}, "docs": {"result": "skipped"}, "test": {"result": "failure"}}

        self.assertEqual(run_report.failed_needs(json.dumps(needs)), ["test"])

    def test_rejects_empty_needs(self) -> None:
        with self.assertRaises(ValueError):
            run_report.failed_needs("{}")


class ToJobsTest(unittest.TestCase):
    def test_drops_running_jobs_and_measures_queue_and_run_time(self) -> None:
        raw: list[dict[str, object]] = [
            job_payload("lint", "2026-10-23T00:00:00Z", "2026-10-23T00:00:05Z", "2026-10-23T00:00:45Z"),
            {"name": "report", "status": "in_progress", "created_at": "2026-10-23T00:01:00Z", "steps": []},
        ]

        jobs = run_report.to_jobs(raw)

        self.assertEqual([(job.name, job.queued, job.seconds) for job in jobs], [("lint", 5, 40)])
        self.assertEqual(jobs[0].steps[0].seconds, 40)


class RenderTest(unittest.TestCase):
    def test_starts_with_the_workflow_marker_and_lists_every_job_and_step(self) -> None:
        jobs = run_report.to_jobs(
            [
                job_payload("lint", "2026-10-23T00:00:00Z", "2026-10-23T00:00:02Z", "2026-10-23T00:01:02Z"),
                job_payload("test", "2026-10-23T00:00:00Z", "2026-10-23T00:00:03Z", "2026-10-23T00:02:03Z"),
            ]
        )

        body = run_report.render(run_report.Run("ci", "https://example.test/run", "7", "1"), jobs, [])

        self.assertTrue(body.startswith("<!-- run-report:ci -->"))
        self.assertIn("| [lint](https://example.test/lint) | ✅ 成功 | 2秒 | 1分0秒 |", body)
        self.assertIn("<summary>test のステップ（2分0秒）</summary>", body)
        self.assertIn("    test : done, j2, 3, 123", body)

    def test_fit_drops_step_details_over_the_limit(self) -> None:
        jobs = run_report.to_jobs(
            [job_payload("lint", "2026-10-23T00:00:00Z", "2026-10-23T00:00:02Z", "2026-10-23T00:01:02Z")]
        )
        run = run_report.Run("ci", "https://example.test/run", "7", "1")

        body = run_report.fit(run, jobs, [], limit=200)

        self.assertNotIn("lint のステップ", body)
        self.assertIn("ステップの内訳は、上限を超えるため省いた", body)


class MainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        event = self.tmp / "event.json"
        event.write_text(json.dumps({"pull_request": {"number": 12}}), encoding="utf-8")
        self.summary = self.tmp / "summary.md"
        self.env = {
            "GH_TOKEN": "token",
            "GITHUB_API_URL": "https://api.example.test",
            "GITHUB_SERVER_URL": "https://example.test",
            "GITHUB_REPOSITORY": "octo/kit",
            "GITHUB_RUN_ID": "99",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_NUMBER": "7",
            "GITHUB_WORKFLOW": "ci",
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_EVENT_PATH": str(event),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "NEEDS": json.dumps({"lint": {"result": "success", "outputs": {}}}),
        }
        self.jobs_url = "https://api.example.test/repos/octo/kit/actions/runs/99/attempts/1/jobs?per_page=100&page=1"
        self.comments_url = "https://api.example.test/repos/octo/kit/issues/12/comments"

    def test_posts_a_new_comment_and_writes_the_summary(self) -> None:
        api = FakeApi(
            {
                self.jobs_url: {
                    "jobs": [
                        job_payload("lint", "2026-10-23T00:00:00Z", "2026-10-23T00:00:01Z", "2026-10-23T00:00:31Z")
                    ]
                },
                f"{self.comments_url}?per_page=100&page=1": [],
            }
        )

        code = run_report.main(self.env, api)

        self.assertEqual(code, 0)
        self.assertEqual([call[:2] for call in api.calls][-1], ("POST", self.comments_url))
        self.assertIn("<!-- run-report:ci -->", self.summary.read_text(encoding="utf-8"))

    def test_updates_the_previous_comment_of_the_same_workflow(self) -> None:
        previous = {"body": "<!-- run-report:ci -->\n古い報告", "url": "https://api.example.test/comments/5"}
        api = FakeApi({self.jobs_url: {"jobs": []}, f"{self.comments_url}?per_page=100&page=1": [previous]})

        run_report.main(self.env, api)

        self.assertEqual([call[:2] for call in api.calls][-1], ("PATCH", "https://api.example.test/comments/5"))

    def test_keeps_going_when_a_fork_token_cannot_comment(self) -> None:
        api = FakeApi({self.jobs_url: {"jobs": []}}, fail={self.comments_url + "?per_page=100&page=1": 403})

        code = run_report.main(self.env, api)

        self.assertEqual(code, 0)

    def test_fails_when_a_needed_job_failed(self) -> None:
        self.env["NEEDS"] = json.dumps({"lint": {"result": "failure", "outputs": {}}})
        api = FakeApi({self.jobs_url: {"jobs": []}, f"{self.comments_url}?per_page=100&page=1": []})

        code = run_report.main(self.env, api)

        self.assertEqual(code, 1)

    def test_writes_only_the_summary_outside_pull_requests(self) -> None:
        self.env["GITHUB_EVENT_NAME"] = "push"
        api = FakeApi({self.jobs_url: {"jobs": []}})

        run_report.main(self.env, api)

        self.assertEqual([call[0] for call in api.calls], ["GET"])


if __name__ == "__main__":
    unittest.main()
