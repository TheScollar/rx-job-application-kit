"""Tests for scripts/reactive_resume_publish.py."""

from __future__ import annotations

import unittest

from support import FakePublishClient, make_remote, make_resume_data, publish


class SlugAndTagTests(unittest.TestCase):
    def test_normalize_slug_lowercases_and_dashes(self):
        self.assertEqual(publish.normalize_slug("Acme Corp / PM"), "acme-corp-pm")

    def test_normalize_slug_empty_raises(self):
        with self.assertRaises(publish.PublishError):
            publish.normalize_slug("///")

    def test_unique_tags_dedupes_case_insensitively(self):
        self.assertEqual(publish.unique_tags(["Job", "job", "EN"]), ["Job", "EN"])

    def test_unique_tags_all_empty_raises(self):
        with self.assertRaises(publish.PublishError):
            publish.unique_tags(["", "  "])

    def test_candidate_name_and_slug_suffixes_on_collision(self):
        name, slug = publish.candidate_name_and_slug(
            "Acme", "acme", {"acme"}, attempt=1
        )
        self.assertEqual(slug, "acme-2")
        self.assertEqual(name, "Acme (2)")


class VerifyResumeDeepCompareTests(unittest.TestCase):
    """verify_resume must catch content corruption, not just identity fields."""

    def _verify(self, remote, local):
        return publish.verify_resume(
            remote,
            resume_id=remote["id"],
            name=remote["name"],
            slug=remote["slug"],
            local_data=local,
        )

    def test_clean_roundtrip_has_no_mismatches(self):
        local = make_resume_data()
        remote = make_remote(local)
        self.assertEqual(self._verify(remote, local), [])

    def test_detects_corrupted_summary_content(self):
        local = make_resume_data()
        remote = make_remote(local)
        remote["data"]["summary"]["content"] = "<p>WRONG</p>"
        self.assertTrue(self._verify(remote, local))

    def test_detects_dropped_skills(self):
        local = make_resume_data()
        remote = make_remote(local)
        remote["data"]["sections"]["skills"]["items"] = []
        self.assertTrue(self._verify(remote, local))

    def test_detects_corrupted_role_bullets(self):
        local = make_resume_data()
        remote = make_remote(local)
        remote["data"]["sections"]["experience"]["items"][0]["roles"][0][
            "description"
        ] = "<ul><li>Different</li></ul>"
        self.assertTrue(self._verify(remote, local))

    def test_detects_changed_template(self):
        local = make_resume_data()
        remote = make_remote(local)
        remote["data"]["metadata"]["template"] = "bronzor"
        self.assertTrue(self._verify(remote, local))

    def test_tolerates_server_added_fields(self):
        # The server may add keys we did not send; that is not a mismatch.
        local = make_resume_data()
        remote = make_remote(local)
        remote["data"]["metadata"]["serverStamp"] = "abc"
        remote["data"]["basics"]["id"] = "server-generated"
        self.assertEqual(self._verify(remote, local), [])


class PublishHappyPathTests(unittest.TestCase):
    def _publish(self, client, name="Acme — PM — EN — 2026-07-23",
                 base_slug="2026-07-23-acme-pm-en"):
        return publish.publish_resume(
            client,
            name=name,
            base_slug=base_slug,
            tags=["job-application"],
            resume_data=make_resume_data(),
        )

    def test_publish_then_verify_succeeds_without_deleting(self):
        local = make_resume_data()
        client = FakePublishClient()
        client.create_behaviors = [("ok", None, "res_1")]
        client.update_behavior = ("ok", {})
        client.get_behavior = ("ok", make_remote(
            local, resume_id="res_1",
            name="Acme — PM — EN — 2026-07-23", slug="2026-07-23-acme-pm-en"))

        result = self._publish(client)

        self.assertEqual(result.status, "published")
        self.assertTrue(result.verified)
        self.assertEqual(result.resume_id, "res_1")
        self.assertEqual(client.deleted, [])

    def test_duplicate_slug_gets_suffixed(self):
        local = make_resume_data()
        dup = publish.ApiError(
            "duplicate", status_code=400, response_body="slug already exists"
        )
        client = FakePublishClient()
        client.create_behaviors = [("raise", dup, None), ("ok", None, "res_2")]
        client.update_behavior = ("ok", {})
        client.get_behavior = ("ok", make_remote(
            local, resume_id="res_2",
            name="Acme — PM — EN — 2026-07-23 (2)",
            slug="2026-07-23-acme-pm-en-2"))

        result = self._publish(client)

        self.assertEqual(result.status, "published")
        self.assertTrue(result.slug.endswith("-2"))


class PublishFailureHandlingTests(unittest.TestCase):
    """The publisher must never delete, and must resolve mutation ambiguity."""

    def _publish(self, client):
        return publish.publish_resume(
            client,
            name="Acme — PM — EN — 2026-07-23",
            base_slug="2026-07-23-acme-pm-en",
            tags=["job-application"],
            resume_data=make_resume_data(),
        )

    def test_client_class_has_no_delete_method(self):
        self.assertFalse(hasattr(publish.ReactiveResumeClient, "delete_resume"))

    def test_update_http_error_keeps_shell_and_returns_incomplete(self):
        bad = publish.ApiError(
            "bad data", status_code=400, response_body="validation failed"
        )
        client = FakePublishClient()
        client.create_behaviors = [("ok", None, "res_1")]
        client.update_behavior = ("raise", bad)

        result = self._publish(client)

        self.assertEqual(result.status, "created_verification_incomplete")
        self.assertFalse(result.verified)
        self.assertEqual(result.resume_id, "res_1")
        self.assertEqual(client.deleted, [])  # never deleted, even on HTTP error

    def test_update_transport_error_keeps_resume(self):
        timeout = publish.ApiError("timed out", status_code=None)
        client = FakePublishClient()
        client.create_behaviors = [("ok", None, "res_1")]
        client.update_behavior = ("raise", timeout)

        result = self._publish(client)

        self.assertEqual(result.status, "created_verification_incomplete")
        self.assertEqual(client.deleted, [])

    def test_create_transport_error_reconciles_and_continues(self):
        # POST connection dropped after the server committed the resume.
        timeout = publish.ApiError("timed out", status_code=None)
        local = make_resume_data()
        client = FakePublishClient()
        client.create_behaviors = [("raise_after_create", timeout, "res_1")]
        client.update_behavior = ("ok", {})
        client.get_behavior = ("ok", make_remote(
            local, resume_id="res_1",
            name="Acme — PM — EN — 2026-07-23", slug="2026-07-23-acme-pm-en"))

        result = self._publish(client)

        self.assertEqual(result.resume_id, "res_1")
        self.assertEqual(client.create_calls, 1)  # no duplicate creation
        self.assertEqual(client.deleted, [])

    def test_create_transport_error_no_resume_created_is_error(self):
        timeout = publish.ApiError("timed out", status_code=None)
        client = FakePublishClient()
        client.create_behaviors = [("raise", timeout, None)]

        with self.assertRaises(publish.PublishError):
            self._publish(client)

    def test_create_transport_error_reconcile_list_fails_is_ambiguous(self):
        timeout = publish.ApiError("timed out", status_code=None)
        client = FakePublishClient()
        client.create_behaviors = [("raise_after_create", timeout, "res_1")]
        client.list_behavior_after = "raise"

        result = self._publish(client)

        self.assertEqual(result.status, "created_verification_incomplete")
        self.assertFalse(result.verified)
        self.assertEqual(client.deleted, [])


class OverrideGatingTests(unittest.TestCase):
    def test_overrides_allowed_truthy_values(self):
        for value in ("1", "true", "TRUE", "yes", "on"):
            self.assertTrue(publish.overrides_allowed(
                {"REACTIVE_RESUME_ALLOW_OVERRIDES": value}))

    def test_overrides_disallowed_by_default(self):
        self.assertFalse(publish.overrides_allowed({}))
        self.assertFalse(publish.overrides_allowed(
            {"REACTIVE_RESUME_ALLOW_OVERRIDES": "0"}))

    def test_resolve_base_url_default(self):
        self.assertEqual(
            publish.resolve_base_url("", "", allow_overrides=False),
            publish.DEFAULT_BASE_URL,
        )

    def test_resolve_base_url_env_https_honored(self):
        self.assertEqual(
            publish.resolve_base_url("", "https://my.host/api", allow_overrides=False),
            "https://my.host/api",
        )

    def test_resolve_base_url_cli_blocked_without_override(self):
        with self.assertRaises(publish.PublishError):
            publish.resolve_base_url("https://evil/api", "", allow_overrides=False)

    def test_resolve_base_url_cli_allowed_with_override(self):
        self.assertEqual(
            publish.resolve_base_url("https://x/api", "", allow_overrides=True),
            "https://x/api",
        )

    def test_resolve_base_url_http_non_loopback_blocked(self):
        with self.assertRaises(publish.PublishError):
            publish.resolve_base_url("", "http://evil.com", allow_overrides=False)

    def test_resolve_base_url_http_loopback_allowed(self):
        for url in ("http://127.0.0.1:3000/api", "http://localhost:3000",
                    "http://[::1]:3000"):
            self.assertEqual(
                publish.resolve_base_url("", url, allow_overrides=False), url)

    def test_resolve_base_url_http_non_loopback_blocked_with_override(self):
        for cli_url, env_url in (
            ("http://192.168.1.9", ""),
            ("", "http://192.168.1.9"),
        ):
            with self.subTest(cli_url=cli_url, env_url=env_url):
                with self.assertRaisesRegex(
                    publish.PublishError, "Use https:// instead"
                ):
                    publish.resolve_base_url(
                        cli_url, env_url, allow_overrides=True
                    )

    def test_resolve_base_url_rejects_non_http_scheme(self):
        with self.assertRaises(publish.PublishError):
            publish.resolve_base_url("", "ftp://x", allow_overrides=True)

    def test_resolve_env_file_default_when_not_provided(self):
        from pathlib import Path
        default = Path("/repo/.env")
        self.assertEqual(
            publish.resolve_env_file(None, default, allow_overrides=False), default)

    def test_resolve_env_file_override_blocked(self):
        from pathlib import Path
        with self.assertRaises(publish.PublishError):
            publish.resolve_env_file(
                Path("/tmp/other"), Path("/repo/.env"), allow_overrides=False)

    def test_resolve_env_file_override_allowed(self):
        from pathlib import Path
        other = Path("/tmp/other")
        self.assertEqual(
            publish.resolve_env_file(other, Path("/repo/.env"), allow_overrides=True),
            other,
        )


if __name__ == "__main__":
    unittest.main()
