#!/usr/bin/env python3
"""Create a private Reactive Resume from a local ResumeData JSON file.

The script keeps credentials out of command arguments, creates a named resume
shell, replaces its data, and verifies the persisted result. It prints one JSON
result object to stdout so callers can record the created resume metadata.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


DEFAULT_BASE_URL = "https://rxresu.me/api/openapi"
DEFAULT_TIMEOUT_SECONDS = 20
MAX_SLUG_ATTEMPTS = 20
REQUIRED_TOP_LEVEL_KEYS = {
    "picture",
    "basics",
    "summary",
    "sections",
    "customSections",
    "metadata",
}


class PublishError(Exception):
    """A safe, user-facing publishing failure."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ApiError(PublishError):
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


@dataclass
class PublishResult:
    status: str
    resume_id: str
    name: str
    slug: str
    tags: list[str]
    api_url: str
    verified: bool
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "id": self.resume_id,
            "name": self.name,
            "slug": self.slug,
            "tags": self.tags,
            "isPublic": False,
            "apiUrl": self.api_url,
            "verified": self.verified,
            "warnings": self.warnings,
        }


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE entries without evaluating shell syntax."""
    if not path.is_file():
        raise PublishError(
            f"Credential file not found: {path}",
            hint=(
                "Create .env in the repo root with "
                "REACTIVE_RESUME_API_KEY=<your-api-key>."
            ),
        )

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise PublishError(
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
            raise PublishError(
                f"Invalid entry in {path} on line {line_number}; expected KEY=VALUE."
            )

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise PublishError(
                f"Invalid variable name in {path} on line {line_number}."
            )
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value

    return values


def load_resume_data(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise PublishError(f"Resume JSON file not found: {path}")

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PublishError(f"Resume JSON is invalid: {error}") from error

    if not isinstance(raw_data, dict):
        raise PublishError("Resume JSON must contain a top-level object.")

    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - raw_data.keys())
    if missing:
        raise PublishError(
            "Resume JSON is structurally incomplete.",
            missing_keys=missing,
        )

    if not isinstance(raw_data["basics"], dict):
        raise PublishError("Resume JSON field 'basics' must be an object.")
    if not isinstance(raw_data["summary"], dict):
        raise PublishError("Resume JSON field 'summary' must be an object.")
    if not isinstance(raw_data["sections"], dict):
        raise PublishError("Resume JSON field 'sections' must be an object.")

    experience = raw_data["sections"].get("experience")
    if not isinstance(experience, dict) or not isinstance(
        experience.get("items"), list
    ):
        raise PublishError(
            "Resume JSON field 'sections.experience.items' must be an array."
        )

    validate_multi_position_employers(experience["items"])

    # `$schema` is useful in local exports but is not part of the API ResumeData body.
    return {key: value for key, value in raw_data.items() if key != "$schema"}


def validate_multi_position_employers(items: list[Any]) -> None:
    """Ensure multi-position employers do not duplicate role-level content."""
    violations: list[dict[str, Any]] = []

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise PublishError(
                "Each sections.experience.items entry must be an object.",
                item_index=index,
            )

        roles = item.get("roles", [])
        if not isinstance(roles, list):
            raise PublishError(
                "Experience item field 'roles' must be an array.",
                company=item.get("company", ""),
                item_index=index,
            )
        if not roles:
            continue

        invalid_role_indexes = [
            role_index
            for role_index, role in enumerate(roles)
            if not isinstance(role, dict)
            or not isinstance(role.get("position"), str)
            or not role["position"].strip()
        ]
        if invalid_role_indexes:
            raise PublishError(
                "Every multi-position role must be an object with a non-empty "
                "position.",
                company=item.get("company", ""),
                role_indexes=invalid_role_indexes,
            )

        non_empty_fields = [
            field
            for field in ("position", "period", "description")
            if item.get(field) != ""
        ]
        if non_empty_fields:
            violations.append(
                {
                    "company": item.get("company", "") or f"item {index}",
                    "item_index": index,
                    "non_empty_fields": non_empty_fields,
                }
            )

    if violations:
        raise PublishError(
            "Multi-position employers must keep top-level position, period, "
            "and description empty; put all titles and role content in roles[].",
            multi_position_violations=violations,
        )


def normalize_slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode(
        "ascii", "ignore"
    ).decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    if not slug:
        raise PublishError("The resume slug is empty after normalization.")
    return slug


def unique_tags(tags: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        cleaned = tag.strip()
        if cleaned and cleaned.casefold() not in seen:
            result.append(cleaned)
            seen.add(cleaned.casefold())
    if not result:
        raise PublishError("At least one non-empty resume tag is required.")
    return result


TRUTHY_OVERRIDE_VALUES = {"1", "true", "yes", "on"}


def overrides_allowed(environ: Mapping[str, str]) -> bool:
    """Whether the insecure --base-url/--env-file overrides are permitted."""
    return (
        environ.get("REACTIVE_RESUME_ALLOW_OVERRIDES", "").strip().lower()
        in TRUTHY_OVERRIDE_VALUES
    )


def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def resolve_base_url(
    cli_base_url: str, env_base_url: str, *, allow_overrides: bool
) -> str:
    """Resolve and security-check the API base URL.

    The --base-url override is refused unless overrides are explicitly allowed.
    The resolved URL must use https, except http is accepted for loopback hosts.
    """
    if cli_base_url and not allow_overrides:
        raise PublishError(
            "--base-url is disabled by default; set "
            "REACTIVE_RESUME_ALLOW_OVERRIDES=1 to use it."
        )
    base_url = (cli_base_url or env_base_url or DEFAULT_BASE_URL).strip()
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in ("http", "https"):
        raise PublishError(
            "The API base URL must start with http:// or https://."
        )
    if parsed.scheme == "http" and not _is_loopback_host(parsed.hostname):
        raise PublishError(
            "Refusing to send the API key over http:// to a non-loopback host. "
            "Use https:// instead."
        )
    return base_url


def resolve_env_file(
    cli_env_file: Path | None,
    default_env_file: Path,
    *,
    allow_overrides: bool,
) -> Path:
    """Resolve the credential file path, gating the --env-file override."""
    if (
        cli_env_file is not None
        and cli_env_file != default_env_file
        and not allow_overrides
    ):
        raise PublishError(
            "--env-file is disabled by default; set "
            "REACTIVE_RESUME_ALLOW_OVERRIDES=1 to use it."
        )
    return cli_env_file if cli_env_file is not None else default_env_file


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
    ) -> Any:
        body = None
        headers = {"x-api-key": self.api_key, "Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"{self.base_url}{path}",
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

    def list_resumes(self) -> list[dict[str, Any]]:
        response = self.request("GET", "/resumes")
        if not isinstance(response, list):
            raise ApiError("Reactive Resume list response was not an array.")
        return [item for item in response if isinstance(item, dict)]

    def create_resume(self, name: str, slug: str, tags: list[str]) -> str:
        response = self.request(
            "POST",
            "/resumes",
            {
                "name": name,
                "slug": slug,
                "tags": tags,
                "withSampleData": False,
            },
        )
        if isinstance(response, str) and response:
            return response
        if isinstance(response, dict) and isinstance(response.get("id"), str):
            return response["id"]
        raise ApiError("Reactive Resume create response did not contain an ID.")

    def update_resume(
        self,
        resume_id: str,
        *,
        name: str,
        slug: str,
        tags: list[str],
        data: dict[str, Any],
    ) -> dict[str, Any]:
        response = self.request(
            "PUT",
            f"/resumes/{urllib.parse.quote(resume_id, safe='')}",
            {
                "name": name,
                "slug": slug,
                "tags": tags,
                "data": data,
                "isPublic": False,
            },
        )
        if not isinstance(response, dict):
            raise ApiError("Reactive Resume update response was not an object.")
        return response

    def get_resume(self, resume_id: str) -> dict[str, Any]:
        response = self.request(
            "GET", f"/resumes/{urllib.parse.quote(resume_id, safe='')}"
        )
        if not isinstance(response, dict):
            raise ApiError("Reactive Resume get response was not an object.")
        return response


def is_duplicate_slug_error(error: ApiError) -> bool:
    body = error.response_body.casefold()
    return (
        error.status_code == 400
        and "slug" in body
        and ("already" in body or "exists" in body)
    )


def candidate_name_and_slug(
    base_name: str,
    base_slug: str,
    existing_slugs: set[str],
    attempt: int,
) -> tuple[str, str]:
    ordinal = attempt + 1
    if ordinal == 1 and base_slug not in existing_slugs:
        return base_name, base_slug

    suffix = 2
    while f"{base_slug}-{suffix}" in existing_slugs:
        suffix += 1
    return f"{base_name} ({suffix})", f"{base_slug}-{suffix}"


IGNORED_DATA_KEYS = {"id"}


def content_mismatches(local: Any, remote: Any, path: str = "data") -> list[str]:
    """Paths where the remote data does not preserve the authored local data.

    Only fields present locally are checked, so server-added keys are ignored;
    keys named ``id`` are ignored because the server may reassign them.
    """
    mismatches: list[str] = []
    _compare_subset(local, remote, path, mismatches)
    return mismatches


def _compare_subset(local: Any, remote: Any, path: str, out: list[str]) -> None:
    if isinstance(local, dict):
        if not isinstance(remote, dict):
            out.append(path)
            return
        for key, value in local.items():
            if key in IGNORED_DATA_KEYS:
                continue
            if key not in remote:
                out.append(f"{path}.{key}")
            else:
                _compare_subset(value, remote[key], f"{path}.{key}", out)
    elif isinstance(local, list):
        if not isinstance(remote, list) or len(remote) != len(local):
            out.append(path)
            return
        for index, (local_item, remote_item) in enumerate(zip(local, remote)):
            _compare_subset(local_item, remote_item, f"{path}[{index}]", out)
    else:
        if local != remote:
            out.append(path)


def verify_resume(
    remote: dict[str, Any],
    *,
    resume_id: str,
    name: str,
    slug: str,
    local_data: dict[str, Any],
) -> list[str]:
    mismatches: list[str] = []
    if remote.get("id") != resume_id:
        mismatches.append("id")
    if remote.get("name") != name:
        mismatches.append("name")
    if remote.get("slug") != slug:
        mismatches.append("slug")
    if remote.get("isPublic") is not False:
        mismatches.append("isPublic")

    remote_data = remote.get("data")
    if not isinstance(remote_data, dict):
        return mismatches + ["data"]

    mismatches.extend(content_mismatches(local_data, remote_data))
    return mismatches


def find_resume_id_by_slug(
    client: ReactiveResumeClient, slug: str
) -> str | None:
    """Return the ID of an existing resume with this slug, if any."""
    for item in client.list_resumes():
        if item.get("slug") == slug and isinstance(item.get("id"), str):
            return item["id"]
    return None


def publish_resume(
    client: ReactiveResumeClient,
    *,
    name: str,
    base_slug: str,
    tags: list[str],
    resume_data: dict[str, Any],
) -> PublishResult:
    existing_slugs = {
        item["slug"]
        for item in client.list_resumes()
        if isinstance(item.get("slug"), str)
    }

    resume_id = ""
    selected_name = name
    selected_slug = base_slug
    for attempt in range(MAX_SLUG_ATTEMPTS):
        selected_name, selected_slug = candidate_name_and_slug(
            name, base_slug, existing_slugs, attempt
        )
        try:
            resume_id = client.create_resume(selected_name, selected_slug, tags)
            break
        except ApiError as error:
            if is_duplicate_slug_error(error):
                existing_slugs.add(selected_slug)
                continue
            if error.status_code is None:
                # The connection dropped mid-request; the server may already
                # have created the resume. Reconcile by slug instead of blindly
                # recreating (which would duplicate) or deleting.
                try:
                    recovered_id = find_resume_id_by_slug(client, selected_slug)
                except ApiError:
                    return PublishResult(
                        status="created_verification_incomplete",
                        resume_id="",
                        name=selected_name,
                        slug=selected_slug,
                        tags=tags,
                        api_url=f"{client.base_url}/resumes",
                        verified=False,
                        warnings=[
                            "Create request failed and the outcome could not be "
                            f"reconciled; a resume with slug '{selected_slug}' "
                            "may or may not exist. Check your Reactive Resume "
                            "account before retrying."
                        ],
                    )
                if recovered_id:
                    resume_id = recovered_id
                    break
                raise PublishError(
                    "Resume creation failed and no resume with the intended "
                    "slug exists; nothing was created.",
                    slug=selected_slug,
                    create_error=error.message,
                ) from error
            raise
    else:
        raise PublishError(
            f"Could not allocate a unique slug after {MAX_SLUG_ATTEMPTS} attempts."
        )

    api_url = (
        f"{client.base_url}/resumes/"
        f"{urllib.parse.quote(resume_id, safe='')}"
    )

    try:
        client.update_resume(
            resume_id,
            name=selected_name,
            slug=selected_slug,
            tags=tags,
            data=resume_data,
        )
    except PublishError as update_error:
        # The resume shell exists from here on. Never delete it: keep it and
        # report an ambiguous result so the user decides (retry population or
        # remove it in the UI). This holds for both transport failures and HTTP
        # errors returned after the shell was created.
        transport = (
            isinstance(update_error, ApiError)
            and update_error.status_code is None
        )
        cause = "transport failure" if transport else "API error"
        return PublishResult(
            status="created_verification_incomplete",
            resume_id=resume_id,
            name=selected_name,
            slug=selected_slug,
            tags=tags,
            api_url=api_url,
            verified=False,
            warnings=[
                f"Resume data update did not complete ({cause}): "
                + update_error.message
                + f" The resume '{selected_slug}' (id {resume_id}) exists as an "
                "empty or partial shell; retry population or remove it in the "
                "Reactive Resume UI. This script never deletes remote resumes."
            ],
        )

    try:
        remote = client.get_resume(resume_id)
        mismatches = verify_resume(
            remote,
            resume_id=resume_id,
            name=selected_name,
            slug=selected_slug,
            local_data=resume_data,
        )
    except PublishError as verification_error:
        return PublishResult(
            status="created_verification_incomplete",
            resume_id=resume_id,
            name=selected_name,
            slug=selected_slug,
            tags=tags,
            api_url=api_url,
            verified=False,
            warnings=[verification_error.message],
        )

    if mismatches:
        return PublishResult(
            status="created_verification_incomplete",
            resume_id=resume_id,
            name=selected_name,
            slug=selected_slug,
            tags=tags,
            api_url=api_url,
            verified=False,
            warnings=["Verification mismatch: " + ", ".join(mismatches)],
        )

    return PublishResult(
        status="published",
        resume_id=resume_id,
        name=selected_name,
        slug=selected_slug,
        tags=tags,
        api_url=api_url,
        verified=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and verify a private Reactive Resume from JSON."
    )
    parser.add_argument("--json", required=True, type=Path, dest="json_path")
    parser.add_argument("--name", default="")
    parser.add_argument("--slug", default="")
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        dest="tags",
        help="Repeat for each tag.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help=(
            "Credential file (default: .env in the repo root). Disabled "
            "unless REACTIVE_RESUME_ALLOW_OVERRIDES=1."
        ),
    )
    parser.add_argument(
        "--base-url",
        default="",
        help=(
            "Base URL override, disabled unless "
            "REACTIVE_RESUME_ALLOW_OVERRIDES=1; otherwise uses "
            "REACTIVE_RESUME_BASE_URL from .env or the cloud API."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Validate the local ResumeData JSON without reading credentials "
            "or calling the API."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        resume_data = load_resume_data(args.json_path)
        if args.validate_only:
            experience_items = resume_data["sections"]["experience"]["items"]
            multi_position_count = sum(
                bool(item.get("roles"))
                for item in experience_items
                if isinstance(item, dict)
            )
            print(
                json.dumps(
                    {
                        "status": "valid",
                        "experienceItems": len(experience_items),
                        "multiPositionEmployers": multi_position_count,
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        allow_overrides = overrides_allowed(os.environ)
        repo_root = Path(__file__).resolve().parent.parent
        env_file = resolve_env_file(
            args.env_file, repo_root / ".env", allow_overrides=allow_overrides
        )
        env = parse_env_file(env_file)
        api_key = env.get("REACTIVE_RESUME_API_KEY", "").strip()
        if not api_key:
            raise PublishError(
                f"REACTIVE_RESUME_API_KEY is missing from {env_file}."
            )

        base_url = resolve_base_url(
            args.base_url,
            env.get("REACTIVE_RESUME_BASE_URL", "").strip(),
            allow_overrides=allow_overrides,
        )
        if args.timeout <= 0:
            raise PublishError("--timeout must be greater than zero.")

        name = args.name.strip()
        if not name:
            raise PublishError("The resume name cannot be empty.")

        tags = unique_tags(args.tags)
        client = ReactiveResumeClient(base_url, api_key, args.timeout)
        result = publish_resume(
            client,
            name=name,
            base_slug=normalize_slug(args.slug),
            tags=tags,
            resume_data=resume_data,
        )
    except PublishError as error:
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

    print(json.dumps(result.as_dict(), ensure_ascii=False))
    return 0 if result.verified else 2


if __name__ == "__main__":
    raise SystemExit(main())
