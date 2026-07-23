"""Shared test helpers: import the scripts and provide fake API clients.

The tests never touch the network or a real `.env`. Publisher tests drive the
high-level client methods (list/create/update/get); API-client tests drive the
low-level `request` method. Both fakes record their calls so tests can assert
that no delete ever happens and that reconciliation re-reads happen.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import reactive_resume_api as api  # noqa: E402
import reactive_resume_publish as publish  # noqa: E402


def make_resume_data() -> dict:
    """A minimal but structurally valid ResumeData body."""
    return {
        "picture": {"url": ""},
        "basics": {
            "name": "Alex Doe",
            "headline": "Product Manager",
            "email": "alex@example.com",
            "phone": "",
            "location": "Berlin",
            "url": {"href": ""},
            "customFields": [],
        },
        "summary": {
            "id": "sum1",
            "name": "Summary",
            "columns": 1,
            "visible": True,
            "content": "<p>Seasoned product manager.</p>",
        },
        "sections": {
            "experience": {
                "id": "exp",
                "name": "Experience",
                "visible": True,
                "items": [
                    {
                        "id": "e1",
                        "company": "NimbusWorks",
                        "position": "",
                        "period": "",
                        "description": "",
                        "location": "Berlin",
                        "date": "2020 - Present",
                        "summary": "<p>Led product.</p>",
                        "url": {"href": ""},
                        "roles": [
                            {
                                "position": "Senior PM",
                                "period": "2022 - Present",
                                "description": "<ul><li>Shipped X</li></ul>",
                            }
                        ],
                    }
                ],
            },
            "skills": {
                "id": "sk",
                "name": "Skills",
                "visible": True,
                "items": [
                    {
                        "id": "s1",
                        "name": "Roadmapping",
                        "description": "",
                        "level": 0,
                        "keywords": ["OKRs", "Discovery"],
                    }
                ],
            },
            "education": {"id": "ed", "name": "Education", "visible": True, "items": []},
        },
        "customSections": [],
        "metadata": {
            "template": "azurill",
            "layout": [[[]]],
            "css": {"value": "", "visible": False},
            "page": {"format": "a4", "margin": 18},
            "theme": {"background": "#fff", "text": "#000", "primary": "#000"},
            "typography": {},
            "notes": "",
        },
    }


def make_remote(
    local: dict,
    *,
    resume_id: str = "res_1",
    name: str = "Acme — PM — EN — 2026-07-23",
    slug: str = "2026-07-23-acme-pm-en",
) -> dict:
    """Wrap ResumeData as the API's resume object, echoing the data verbatim."""
    return {
        "id": resume_id,
        "name": name,
        "slug": slug,
        "isPublic": False,
        "data": copy.deepcopy(local),
    }


class FakePublishClient:
    """Stand-in for publish.ReactiveResumeClient's high-level methods.

    create_behaviors is a queue of tuples: ("ok", None, id) creates and returns
    the id; ("raise", exc, None) fails without creating; ("raise_after_create",
    exc, id) models a POST the server committed before the response was lost.
    """

    def __init__(self, base_url: str = "https://example.test/api") -> None:
        self.base_url = base_url
        self.existing: list = []
        self.create_behaviors: list = []
        self.update_behavior = ("ok", {})
        self.get_behavior = ("ok", {})
        self.list_behavior_after = None  # set to "raise" to fail reconcile list
        self.list_calls = 0
        self.create_calls = 0
        self.deleted: list = []

    def list_resumes(self) -> list:
        self.list_calls += 1
        if self.list_calls >= 2 and self.list_behavior_after == "raise":
            raise publish.ApiError("Reconcile list failed.", status_code=None)
        return [dict(item) for item in self.existing]

    def create_resume(self, name: str, slug: str, tags: list) -> str:
        self.create_calls += 1
        kind, exc, resume_id = self.create_behaviors.pop(0)
        if kind in ("ok", "raise_after_create"):
            self.existing.append({"slug": slug, "id": resume_id})
        if kind in ("raise", "raise_after_create"):
            raise exc
        return resume_id

    def update_resume(self, resume_id: str, *, name, slug, tags, data) -> dict:
        kind, value = self.update_behavior
        if kind == "raise":
            raise value
        return value or {}

    def get_resume(self, resume_id: str) -> dict:
        kind, value = self.get_behavior
        if kind == "raise":
            raise value
        return value

    def delete_resume(self, resume_id: str) -> None:
        # Present only so tests can prove publish_resume never calls it.
        self.deleted.append(resume_id)


class FakeClient:
    """Stand-in for the low-level request() used by the API-client commands."""

    def __init__(self, handler, base_url: str = "https://example.test/api") -> None:
        self._handler = handler
        self.base_url = base_url
        self.calls: list = []

    def request(self, method, path, payload=None, query=None):
        self.calls.append((method, path, payload, query))
        return self._handler(method, path, payload, query)
