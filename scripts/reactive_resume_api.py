#!/usr/bin/env python3
"""Read and track job applications in Reactive Resume from the command line.

Companion to reactive_resume_publish.py with the same conventions: the API key
is read from .env (never from argv), one JSON result object is printed to
stdout, safe errors go to stderr as JSON, and exit codes are 0 (verified),
1 (error), 2 (created/updated but verification incomplete).

This script intentionally has NO delete subcommand. It never removes remote
resumes or applications.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Endpoint paths, pinned against the Reactive Resume OpenAPI spec v5.2.2
# (https://docs.rxresu.me/spec.json). The Applications API exists in v5+ only;
# older self-hosted instances lack it and `check-auth` reports that.
# ---------------------------------------------------------------------------
SPEC_VERSION = "5.2.2"
EP_RESUMES = "/resumes"
EP_RESUME_BY_ID = "/resumes/{id}"
EP_APPLICATIONS = "/applications"
EP_APPLICATION_BY_ID = "/applications/{id}"
EP_APPLICATION_STATS = "/applications/stats"

DEFAULT_BASE_URL = "https://rxresu.me/api/openapi"
DEFAULT_TIMEOUT_SECONDS = 20
APPLICATION_STATUSES = (
    "saved",
    "applied",
    "screening",
    "interview",
    "offer",
    "rejected",
)
JOB_DESCRIPTION_MAX_CHARS = 20000  # maxLength in the v5.2.2 create/update DTOs
APPLICATION_SUMMARY_FIELDS = (
    "id",
    "company",
    "role",
    "status",
    "source",
    "sourceUrl",
    "location",
    "salary",
    "resumeId",
    "tags",
    "archived",
    "followUpAt",
    "createdAt",
    "updatedAt",
)


class KitError(Exception):
    """A safe, user-facing failure."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ApiError(KitError):
    """An HTTP or response-decoding failure."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str = "",
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            response_body=response_body,
        )
        self.status_code = status_code
        self.response_body = response_body


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE entries without evaluating shell syntax."""
    if not path.is_file():
        raise KitError(
            f"Credential file not found: {path}",
            hint=(
                "Create .env in the repo root with "
                "REACTIVE_RESUME_API_KEY=<your-api-key>."
            ),
        )

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise KitError(
            f"Could not read credential file {path}: {error}"
        ) from error

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            raise KitError(
                f"Invalid entry in {path} on line {line_number}; expected KEY=VALUE."
            )

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise KitError(
                f"Invalid variable name in {path} on line {line_number}."
            )
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value

    return values


class ReactiveResumeClient:
    def __init__(self, base_url: str, api_key: str, timeout: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        body = None
        headers = {"x-api-key": self.api_key, "Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"

        request = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            response_body = error.read().decode("utf-8", errors="replace")[:4000]
            raise ApiError(
                f"Reactive Resume API returned HTTP {error.code} for {method} {path}.",
                status_code=error.code,
                response_body=response_body,
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise ApiError(
                f"Reactive Resume API request failed for {method} {path}: {error}"
            ) from error

        if not response_body.strip():
            return None
        try:
            return json.loads(response_body)
        except json.JSONDecodeError as error:
            raise ApiError(
                f"Reactive Resume API returned invalid JSON for {method} {path}.",
                response_body=response_body[:4000],
            ) from error


def application_path(application_id: str) -> str:
    return EP_APPLICATION_BY_ID.replace(
        "{id}", urllib.parse.quote(application_id, safe="")
    )


def resume_path(resume_id: str) -> str:
    return EP_RESUME_BY_ID.replace(
        "{id}", urllib.parse.quote(resume_id, safe="")
    )


def validate_status(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned not in APPLICATION_STATUSES:
        raise KitError(
            f"Invalid application status: {value!r}.",
            allowed=list(APPLICATION_STATUSES),
        )
    return cleaned


def normalize_follow_up(value: str) -> str:
    """Accept a plain date or a full ISO timestamp for followUpAt."""
    cleaned = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
        return f"{cleaned}T09:00:00.000Z"
    return cleaned


def application_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {key: item.get(key) for key in APPLICATION_SUMMARY_FIELDS if key in item}


def read_job_description(path: Path) -> tuple[str, list[str]]:
    if not path.is_file():
        raise KitError(f"Job description file not found: {path}")
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        raise KitError(
            f"Could not read job description file {path}: {error}"
        ) from error

    warnings: list[str] = []
    if len(text) > JOB_DESCRIPTION_MAX_CHARS:
        text = text[:JOB_DESCRIPTION_MAX_CHARS]
        warnings.append(
            f"Job description truncated to {JOB_DESCRIPTION_MAX_CHARS} characters "
            "(API maximum)."
        )
    return text, warnings


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_check_auth(client: ReactiveResumeClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    resumes = client.request("GET", EP_RESUMES)
    if not isinstance(resumes, list):
        raise ApiError("Reactive Resume list response was not an array.")

    applications_api = False
    warnings: list[str] = []
    try:
        applications = client.request("GET", EP_APPLICATIONS)
        applications_api = isinstance(applications, list)
        if not applications_api:
            warnings.append(
                "GET /applications returned an unexpected shape; treating the "
                "Applications API as unavailable."
            )
    except ApiError as error:
        warnings.append(
            "Applications API unavailable (this instance is likely older than "
            f"v5): {error.message}"
        )

    return (
        {
            "status": "ok",
            "specVersion": SPEC_VERSION,
            "baseUrl": client.base_url,
            "resumesCount": len(resumes),
            "applicationsApi": applications_api,
            "warnings": warnings,
        },
        0,
    )


def cmd_resumes_list(client: ReactiveResumeClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    resumes = client.request("GET", EP_RESUMES)
    if not isinstance(resumes, list):
        raise ApiError("Reactive Resume list response was not an array.")

    summaries = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "slug": item.get("slug"),
            "isPublic": item.get("isPublic"),
            "updatedAt": item.get("updatedAt"),
        }
        for item in resumes
        if isinstance(item, dict)
    ]
    return ({"status": "ok", "count": len(summaries), "resumes": summaries}, 0)


def cmd_resume_get(client: ReactiveResumeClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    out_path: Path = args.out
    if out_path.exists() and not args.force:
        raise KitError(
            f"Output file already exists: {out_path}. Re-run with --force to overwrite."
        )

    remote = client.request("GET", resume_path(args.id))
    if not isinstance(remote, dict):
        raise ApiError("Reactive Resume get response was not an object.")
    data = remote.get("data")
    if not isinstance(data, dict):
        raise ApiError(
            "Resume response did not contain a ResumeData object under 'data'."
        )

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise KitError(f"Could not write {out_path}: {error}") from error

    experience_items = (
        data.get("sections", {}).get("experience", {}).get("items", [])
    )
    return (
        {
            "status": "saved",
            "id": remote.get("id"),
            "name": remote.get("name"),
            "slug": remote.get("slug"),
            "out": str(out_path),
            "experienceItems": len(experience_items)
            if isinstance(experience_items, list)
            else 0,
        },
        0,
    )


def cmd_app_create(client: ReactiveResumeClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    company = args.company.strip()
    role = args.role.strip()
    if not company or not role:
        raise KitError("--company and --role must be non-empty.")

    payload: dict[str, Any] = {
        "company": company,
        "role": role,
        "status": validate_status(args.status),
    }
    warnings: list[str] = []
    if args.resume_id:
        payload["resumeId"] = args.resume_id.strip()
    if args.source:
        payload["source"] = args.source.strip()
    if args.source_url:
        payload["sourceUrl"] = args.source_url.strip()
    if args.location:
        payload["location"] = args.location.strip()
    if args.salary:
        payload["salary"] = args.salary.strip()
    if args.notes:
        payload["notes"] = args.notes.strip()
    if args.jd_file:
        payload["jobDescription"], jd_warnings = read_job_description(args.jd_file)
        warnings.extend(jd_warnings)
    tags = [tag.strip() for tag in args.tags if tag.strip()]
    if tags:
        payload["tags"] = tags

    response = client.request("POST", EP_APPLICATIONS, payload)
    if isinstance(response, str) and response:
        application_id = response
    elif isinstance(response, dict) and isinstance(response.get("id"), str):
        application_id = response["id"]
    else:
        raise ApiError(
            "Application create response did not contain an ID."
        )

    # Verify with GET. The application exists from here on; never delete it.
    result: dict[str, Any] = {
        "status": "created",
        "id": application_id,
        "company": company,
        "role": role,
        "applicationStatus": payload["status"],
        "resumeId": payload.get("resumeId"),
        "verified": False,
        "warnings": warnings,
    }
    try:
        remote = client.request("GET", application_path(application_id))
    except ApiError as error:
        result["status"] = "created_verification_incomplete"
        result["warnings"] = warnings + [
            "Application was created but could not be re-read: " + error.message
        ]
        return (result, 2)

    mismatches = []
    if not isinstance(remote, dict):
        mismatches.append("response-shape")
    else:
        if remote.get("company") != company:
            mismatches.append("company")
        if remote.get("role") != role:
            mismatches.append("role")
        if remote.get("status") != payload["status"]:
            mismatches.append("status")
        if "resumeId" in payload and remote.get("resumeId") != payload["resumeId"]:
            mismatches.append("resumeId")

    if mismatches:
        result["status"] = "created_verification_incomplete"
        result["warnings"] = warnings + [
            "Verification mismatch: " + ", ".join(mismatches)
        ]
        return (result, 2)

    result["verified"] = True
    return (result, 0)


def cmd_app_get(client: ReactiveResumeClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    remote = client.request("GET", application_path(args.id))
    if not isinstance(remote, dict):
        raise ApiError("Application get response was not an object.")
    return ({"status": "ok", "application": remote}, 0)


def cmd_app_list(client: ReactiveResumeClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    query: dict[str, Any] = {}
    if args.status:
        query["status"] = validate_status(args.status)
    if args.include_archived:
        query["includeArchived"] = "true"

    response = client.request("GET", EP_APPLICATIONS, query=query or None)
    if not isinstance(response, list):
        raise ApiError("Applications list response was not an array.")

    applications = [
        application_summary(item) for item in response if isinstance(item, dict)
    ]
    return (
        {"status": "ok", "count": len(applications), "applications": applications},
        0,
    )


def cmd_app_stats(client: ReactiveResumeClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response = client.request("GET", EP_APPLICATION_STATS)
    if not isinstance(response, dict):
        raise ApiError("Applications stats response was not an object.")
    return (
        {
            "status": "ok",
            "total": response.get("total"),
            "byStage": response.get("byStage"),
            "bySource": response.get("bySource"),
        },
        0,
    )


def cmd_app_update(client: ReactiveResumeClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    payload: dict[str, Any] = {}
    if args.status:
        payload["status"] = validate_status(args.status)
    if args.archive and args.unarchive:
        raise KitError("Use either --archive or --unarchive, not both.")
    if args.archive:
        payload["archived"] = True
    if args.unarchive:
        payload["archived"] = False
    if args.follow_up_at:
        payload["followUpAt"] = normalize_follow_up(args.follow_up_at)
    if args.follow_up_note:
        payload["followUpNote"] = args.follow_up_note.strip()

    if not payload:
        raise KitError(
            "Nothing to update. Provide at least one of --status, --archive, "
            "--unarchive, --follow-up-at, --follow-up-note."
        )

    client.request("PUT", application_path(args.id), payload)

    result: dict[str, Any] = {
        "status": "updated",
        "id": args.id,
        "changes": payload,
        "verified": False,
    }
    try:
        remote = client.request("GET", application_path(args.id))
    except ApiError as error:
        result["status"] = "updated_verification_incomplete"
        result["warnings"] = [
            "Update was sent but could not be re-read: " + error.message
        ]
        return (result, 2)

    mismatches = []
    if not isinstance(remote, dict):
        mismatches.append("response-shape")
    else:
        for key, value in payload.items():
            if remote.get(key) != value:
                mismatches.append(key)

    if mismatches:
        result["status"] = "updated_verification_incomplete"
        result["warnings"] = ["Verification mismatch: " + ", ".join(mismatches)]
        return (result, 2)

    result["verified"] = True
    return (result, 0)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def add_common_arguments(parser: argparse.ArgumentParser, repo_root: Path) -> None:
    parser.add_argument(
        "--env-file",
        type=Path,
        default=repo_root / ".env",
        help="Credential file (default: .env in the repo root).",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help=(
            "Testing override; otherwise uses REACTIVE_RESUME_BASE_URL "
            "or the cloud API."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )


def build_parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description=(
            "Track job applications and pull resumes via the Reactive Resume "
            f"API (spec v{SPEC_VERSION}). No delete operations."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser(
        "check-auth",
        help="Verify the API key and report Applications API availability.",
    )
    add_common_arguments(p, repo_root)
    p.set_defaults(handler=cmd_check_auth)

    p = subparsers.add_parser("resumes-list", help="List resumes (id, name, slug).")
    add_common_arguments(p, repo_root)
    p.set_defaults(handler=cmd_resumes_list)

    p = subparsers.add_parser(
        "resume-get",
        help="Download one resume's ResumeData JSON to a local file.",
    )
    p.add_argument("--id", required=True, help="Resume ID.")
    p.add_argument("--out", required=True, type=Path, help="Output JSON file.")
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it exists.",
    )
    add_common_arguments(p, repo_root)
    p.set_defaults(handler=cmd_resume_get)

    p = subparsers.add_parser("app-create", help="Create an application.")
    p.add_argument("--company", required=True)
    p.add_argument("--role", required=True)
    p.add_argument(
        "--status",
        default="saved",
        help=f"One of: {', '.join(APPLICATION_STATUSES)} (default: saved).",
    )
    p.add_argument("--resume-id", default="", help="Linked resume ID.")
    p.add_argument("--source", default="", help="e.g. linkedin, headhunter, direct.")
    p.add_argument("--source-url", default="", help="JD URL.")
    p.add_argument("--location", default="")
    p.add_argument("--salary", default="", help="Free-text salary or range.")
    p.add_argument(
        "--jd-file",
        type=Path,
        default=None,
        help="File containing the job description text.",
    )
    p.add_argument("--notes", default="")
    p.add_argument(
        "--tag",
        action="append",
        default=[],
        dest="tags",
        help="Repeat for each tag.",
    )
    add_common_arguments(p, repo_root)
    p.set_defaults(handler=cmd_app_create)

    p = subparsers.add_parser("app-get", help="Fetch one application by ID.")
    p.add_argument("--id", required=True)
    add_common_arguments(p, repo_root)
    p.set_defaults(handler=cmd_app_get)

    p = subparsers.add_parser("app-list", help="List applications.")
    p.add_argument(
        "--status",
        default="",
        help=f"Filter by status: {', '.join(APPLICATION_STATUSES)}.",
    )
    p.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived applications.",
    )
    add_common_arguments(p, repo_root)
    p.set_defaults(handler=cmd_app_list)

    p = subparsers.add_parser("app-stats", help="Pipeline stats (total, byStage, bySource).")
    add_common_arguments(p, repo_root)
    p.set_defaults(handler=cmd_app_stats)

    p = subparsers.add_parser(
        "app-update",
        help="Partially update an application (status, archive, follow-up).",
    )
    p.add_argument("--id", required=True)
    p.add_argument(
        "--status",
        default="",
        help=f"New status: {', '.join(APPLICATION_STATUSES)}.",
    )
    p.add_argument("--archive", action="store_true", help="Archive the application.")
    p.add_argument(
        "--unarchive", action="store_true", help="Unarchive the application."
    )
    p.add_argument(
        "--follow-up-at",
        default="",
        help="Follow-up date (YYYY-MM-DD or full ISO timestamp).",
    )
    p.add_argument("--follow-up-note", default="")
    add_common_arguments(p, repo_root)
    p.set_defaults(handler=cmd_app_update)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        env = parse_env_file(args.env_file)
        api_key = env.get("REACTIVE_RESUME_API_KEY", "").strip()
        if not api_key:
            raise KitError(
                f"REACTIVE_RESUME_API_KEY is missing from {args.env_file}."
            )

        base_url = (
            args.base_url
            or env.get("REACTIVE_RESUME_BASE_URL", "").strip()
            or DEFAULT_BASE_URL
        )
        if not base_url.startswith(("http://", "https://")):
            raise KitError(
                "REACTIVE_RESUME_BASE_URL must start with http:// or https://."
            )
        if args.timeout <= 0:
            raise KitError("--timeout must be greater than zero.")

        client = ReactiveResumeClient(base_url, api_key, args.timeout)
        result, exit_code = args.handler(client, args)
    except KitError as error:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": error.message,
                    **error.details,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
