"""Tests for scripts/reactive_resume_api.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from support import FakeClient, api


def app_create_args(**overrides) -> SimpleNamespace:
    base = dict(
        company="Acme",
        role="PM",
        status="saved",
        resume_id="res_1",
        source="",
        source_url="",
        location="",
        salary="",
        notes="",
        jd_file=None,
        tags=[],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class EnvParsingTests(unittest.TestCase):
    def _parse(self, text: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(text, encoding="utf-8")
            return api.parse_env_file(path)

    def test_parses_plain_and_quoted_values(self):
        env = self._parse('REACTIVE_RESUME_API_KEY="abc123"\nOTHER=plain\n')
        self.assertEqual(env["REACTIVE_RESUME_API_KEY"], "abc123")
        self.assertEqual(env["OTHER"], "plain")

    def test_handles_export_prefix(self):
        env = self._parse("export REACTIVE_RESUME_API_KEY=xyz\n")
        self.assertEqual(env["REACTIVE_RESUME_API_KEY"], "xyz")

    def test_missing_file_raises(self):
        with self.assertRaises(api.KitError):
            api.parse_env_file(Path("/no/such/.env"))


class ValidationHelperTests(unittest.TestCase):
    def test_validate_status_accepts_known(self):
        self.assertEqual(api.validate_status(" Applied "), "applied")

    def test_validate_status_rejects_unknown(self):
        with self.assertRaises(api.KitError):
            api.validate_status("ghosted")

    def test_normalize_follow_up_date_becomes_timestamp(self):
        self.assertEqual(
            api.normalize_follow_up("2026-08-01"), "2026-08-01T09:00:00.000Z")

    def test_normalize_follow_up_passthrough_timestamp(self):
        stamp = "2026-08-01T12:30:00.000Z"
        self.assertEqual(api.normalize_follow_up(stamp), stamp)


class CheckAuthCapabilityTests(unittest.TestCase):
    """Only a genuine 404/405 means the Applications API is absent."""

    def _run(self, applications_action):
        def handler(method, path, payload=None, query=None):
            if method == "GET" and path == api.EP_RESUMES:
                return [{"id": "r1"}]
            if method == "GET" and path == api.EP_APPLICATIONS:
                return applications_action()
            raise AssertionError(f"unexpected {method} {path}")

        return api.cmd_check_auth(FakeClient(handler), SimpleNamespace())

    def test_applications_present(self):
        result, code = self._run(lambda: [])
        self.assertEqual(code, 0)
        self.assertTrue(result["applicationsApi"])

    def test_404_means_unsupported(self):
        def raise_404():
            raise api.ApiError("not found", status_code=404, response_body="{}")

        result, code = self._run(raise_404)
        self.assertEqual(code, 0)
        self.assertFalse(result["applicationsApi"])

    def test_405_means_unsupported(self):
        def raise_405():
            raise api.ApiError("method", status_code=405, response_body="{}")

        result, _ = self._run(raise_405)
        self.assertFalse(result["applicationsApi"])

    def test_401_is_a_hard_error(self):
        def raise_401():
            raise api.ApiError("unauth", status_code=401, response_body="{}")

        with self.assertRaises(api.ApiError):
            self._run(raise_401)

    def test_500_is_a_hard_error(self):
        def raise_500():
            raise api.ApiError("boom", status_code=500, response_body="{}")

        with self.assertRaises(api.ApiError):
            self._run(raise_500)

    def test_network_failure_is_a_hard_error(self):
        def raise_transport():
            raise api.ApiError("no route", status_code=None)

        with self.assertRaises(api.ApiError):
            self._run(raise_transport)


class AppCreateTests(unittest.TestCase):
    def test_happy_path_verified(self):
        def handler(method, path, payload=None, query=None):
            if method == "POST" and path == api.EP_APPLICATIONS:
                return "app_1"
            if method == "GET" and path == "/applications/app_1":
                return {"id": "app_1", "company": "Acme", "role": "PM",
                        "status": "saved", "resumeId": "res_1"}
            raise AssertionError(f"unexpected {method} {path}")

        result, code = api.cmd_app_create(FakeClient(handler), app_create_args())
        self.assertEqual(code, 0)
        self.assertTrue(result["verified"])

    def test_verification_mismatch_is_incomplete(self):
        def handler(method, path, payload=None, query=None):
            if method == "POST" and path == api.EP_APPLICATIONS:
                return "app_1"
            if method == "GET" and path == "/applications/app_1":
                return {"id": "app_1", "company": "Wrong", "role": "PM",
                        "status": "saved", "resumeId": "res_1"}
            raise AssertionError(f"unexpected {method} {path}")

        result, code = api.cmd_app_create(FakeClient(handler), app_create_args())
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "created_verification_incomplete")

    def test_post_transport_failure_is_ambiguous_not_error(self):
        # A dropped POST connection may have created the application; retrying
        # blindly would duplicate it, so this must be exit 2, never exit 1.
        def handler(method, path, payload=None, query=None):
            if method == "POST" and path == api.EP_APPLICATIONS:
                raise api.ApiError("timed out", status_code=None)
            if method == "GET" and path == api.EP_APPLICATIONS:
                return [{"id": "app_9", "company": "Acme", "role": "PM",
                         "status": "saved"}]
            raise AssertionError(f"unexpected {method} {path}")

        result, code = api.cmd_app_create(FakeClient(handler), app_create_args())
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "created_verification_incomplete")

    def test_post_http_error_is_a_hard_error(self):
        def handler(method, path, payload=None, query=None):
            if method == "POST" and path == api.EP_APPLICATIONS:
                raise api.ApiError("bad", status_code=400, response_body="{}")
            raise AssertionError(f"unexpected {method} {path}")

        with self.assertRaises(api.ApiError):
            api.cmd_app_create(FakeClient(handler), app_create_args())


class OverrideGatingTests(unittest.TestCase):
    def test_overrides_allowed(self):
        self.assertTrue(api.overrides_allowed(
            {"REACTIVE_RESUME_ALLOW_OVERRIDES": "yes"}))
        self.assertFalse(api.overrides_allowed({}))

    def test_resolve_base_url_cli_blocked_without_override(self):
        with self.assertRaises(api.KitError):
            api.resolve_base_url("https://evil/api", "", allow_overrides=False)

    def test_resolve_base_url_http_non_loopback_blocked(self):
        with self.assertRaises(api.KitError):
            api.resolve_base_url("", "http://evil.com", allow_overrides=False)

    def test_resolve_base_url_http_loopback_allowed(self):
        self.assertEqual(
            api.resolve_base_url("", "http://localhost:3000", allow_overrides=False),
            "http://localhost:3000",
        )

    def test_resolve_env_file_override_blocked(self):
        with self.assertRaises(api.KitError):
            api.resolve_env_file(
                Path("/tmp/other"), Path("/repo/.env"), allow_overrides=False)


if __name__ == "__main__":
    unittest.main()
