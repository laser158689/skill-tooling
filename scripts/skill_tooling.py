#!/usr/bin/env python3
"""Core CLI for scaffolding, validating, and deploying skill family repositories."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


TARGET_INSTALL_ENV = {
    "grok": "SKILL_TOOLING_GROK_INSTALL_ROOT",
    "grok-build": "SKILL_TOOLING_GROK_BUILD_INSTALL_ROOT",
    "claude": "SKILL_TOOLING_CLAUDE_INSTALL_ROOT",
    "claude-code": "SKILL_TOOLING_CLAUDE_CODE_INSTALL_ROOT",
    "openai-chatgpt": "SKILL_TOOLING_OPENAI_CHATGPT_INSTALL_ROOT",
    "codex": "SKILL_TOOLING_CODEX_INSTALL_ROOT",
}

TARGET_ALIASES = {
    "chatgpt": "openai-chatgpt",
    "openai": "openai-chatgpt",
    "openai-chatgpt": "openai-chatgpt",
    "claude": "claude",
    "claude-code": "claude-code",
    "grok": "grok",
    "grok-build": "grok-build",
    "codex": "codex",
}

TARGET_FILE_EXTENSIONS = {
    "grok": ".grok",
    "grok-build": ".grokbuild",
    "claude": ".skill",
    "claude-code": ".skill",
    "openai-chatgpt": ".prompt",
    "codex": ".prompt",
}

DEFAULT_TARGETS = [
    "grok",
    "grok-build",
    "claude",
    "claude-code",
    "openai-chatgpt",
    "codex",
]
TARGET_DISPLAY_NAMES = {
    "grok": "Grok",
    "grok-build": "Grok Build",
    "claude": "Claude",
    "claude-code": "Claude Code",
    "openai-chatgpt": "OpenAI/ChatGPT",
    "codex": "Codex",
}
DEFAULT_PUBLISH_CONFIG_FILENAMES = ("publish-config.json",)

HISTORY_ROOT_DIRNAME = ".skill-tooling"
DEFAULT_DOTENV_FILENAMES = (".env", ".skill-tooling.env")
ALLOWED_DOTENV_KEYS = {
    "ANTHROPIC_API_KEY",
    "CODEX_HOME",
    "OPENAI_API_KEY",
    "SKILL_TOOLING_CONFIG",
    "SKILL_TOOLING_ENV_FILE",
    *TARGET_INSTALL_ENV.values(),
}

FAMILY_MANIFEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.com/skill-tooling/family.schema.json",
    "title": "Skill Tooling Family Manifest",
    "type": "object",
    "additionalProperties": False,
    "required": ["skill_family", "targets"],
    "properties": {
        "skill_family": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "description", "version"],
            "properties": {
                "name": {
                    "type": "string",
                    "pattern": "^[a-z0-9][a-z0-9-]*$",
                    "description": "Lowercase slug for the family.",
                },
                "description": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Human-readable family description.",
                },
                "version": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Family version identifier.",
                },
            },
        },
        "targets": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": DEFAULT_TARGETS,
            },
            "description": "Targets enabled for this family by default.",
        },
    },
}

PUBLISH_CONFIG_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.com/skill-tooling/publish-config.schema.json",
    "title": "Skill Tooling Publish Config",
    "type": "object",
    "additionalProperties": False,
    "required": ["targets"],
    "properties": {
        "targets": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "additionalProperties": False,
                "required": ["mode"],
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["copy", "command", "openai-skills", "claude-agent", "codex-skills"],
                    },
                    "install_root": {"type": "string"},
                    "command": {"type": "array", "items": {"type": "string"}},
                    "verify_command": {"type": "array", "items": {"type": "string"}},
                    "rollback_command": {"type": "array", "items": {"type": "string"}},
                    "api_key_env": {"type": "string"},
                    "base_url": {"type": "string"},
                    "cli_path": {"type": "string"},
                    "model": {"type": "string"},
                    "tool": {"type": "string"},
                },
            },
            "description": "Map of target id to publisher configuration.",
        },
    },
}

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SKILL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
GITHUB_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class ValidationError(RuntimeError):
    """Raised when a family repository is structurally invalid."""


@dataclass(frozen=True)
class Family:
    name: str
    description: str
    version: str
    path: Path
    targets: list[str]


@dataclass(frozen=True)
class Skill:
    skill_id: str
    display_name: str
    description: str
    path: Path
    frontmatter: dict[str, str]
    body: str
    targets: list[str]
    target_overrides: dict[str, str]

    @property
    def title(self) -> str:
        for line in self.body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return self.display_name


@dataclass(frozen=True)
class PublisherConfig:
    mode: str
    install_root: Path | None = None
    command: list[str] | None = None
    verify_command: list[str] | None = None
    rollback_command: list[str] | None = None
    api_key_env: str | None = None
    base_url: str | None = None
    cli_path: str | None = None
    model: str | None = None
    tool: str | None = None


@dataclass(frozen=True)
class SourceContext:
    path: Path
    descriptor: str


@dataclass(frozen=True)
class PublishResult:
    target: str
    mode: str
    bundle_dir: Path
    destination: Path | None
    publish_result: str
    verification_result: str
    rollback_mode: str
    backup_path: Path | None = None
    had_existing_destination: bool = False
    rollback_command: list[str] | None = None


def canonicalize_target(target: str) -> str:
    normalized = target.strip().lower()
    if normalized == "all":
        return normalized
    if normalized not in TARGET_ALIASES:
        raise ValidationError(f"Unsupported target: {target}")
    return TARGET_ALIASES[normalized]


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def parse_target_list(raw_value: str | None, default: Iterable[str]) -> list[str]:
    if raw_value is None or not raw_value.strip():
        return list(default)
    targets = [canonicalize_target(part) for part in raw_value.split(",") if part.strip()]
    if not targets:
        raise ValidationError("Target list cannot be empty")
    return dedupe_preserve_order(targets)


def ensure_slug(value: str, label: str) -> None:
    if not SLUG_RE.match(value):
        raise ValidationError(f"{label} must be a lowercase slug using letters, numbers, and hyphens: {value}")


def ensure_skill_id(value: str) -> None:
    if not SKILL_ID_RE.match(value):
        raise ValidationError(
            f"Skill id must start with a letter or number and use only letters, numbers, dots, underscores, or hyphens: {value}"
        )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path} is not valid JSON: {exc}") from exc


def schema_error(path: str, message: str) -> ValidationError:
    location = path or "$"
    return ValidationError(f"Manifest schema error at {location}: {message}")


def parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].strip()
    if "=" not in stripped:
        raise ValidationError(f"Invalid .env line: {line.rstrip()}")
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        raise ValidationError(f"Invalid .env line: {line.rstrip()}")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return key, value


def load_dotenv_file(path: Path, protected_keys: set[str], loaded_keys: set[str]) -> bool:
    if not path.exists():
        return False
    for line in read_text(path).splitlines():
        parsed = parse_dotenv_line(line)
        if parsed is None:
            continue
        key, value = parsed
        if key not in ALLOWED_DOTENV_KEYS:
            raise ValidationError(f"Unsupported environment key in {path}: {key}")
        if key in protected_keys:
            continue
        os.environ[key] = value
        loaded_keys.add(key)
    return True


def autoload_dotenv(source_root: Path | None = None, include_source_root: bool = True) -> list[Path]:
    loaded: list[Path] = []
    candidates: list[Path] = []
    tooling_root = Path(__file__).resolve().parent.parent
    for name in DEFAULT_DOTENV_FILENAMES:
        candidate = tooling_root / name
        if candidate not in candidates:
            candidates.append(candidate)
    explicit_path = os.environ.get("SKILL_TOOLING_ENV_FILE")
    if explicit_path:
        explicit_candidate = Path(explicit_path).expanduser().resolve()
        if explicit_candidate not in candidates:
            candidates.append(explicit_candidate)

    protected_keys = set(os.environ.keys())
    loaded_keys: set[str] = set()

    for candidate in candidates:
        if load_dotenv_file(candidate, protected_keys, loaded_keys):
            loaded.append(candidate)
    return loaded


def validate_against_schema(data: object, schema: dict, path: str = "$") -> None:
    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(data, dict):
            raise schema_error(path, f"expected object, found {type(data).__name__}")

        required = schema.get("required", [])
        for key in required:
            if key not in data:
                raise schema_error(path, f"missing required property `{key}`")

        properties = schema.get("properties", {})
        additional_properties = schema.get("additionalProperties", True)
        for key, value in data.items():
            child_path = f"{path}.{key}" if path != "$" else key
            if key in properties:
                validate_against_schema(value, properties[key], child_path)
            elif additional_properties is False:
                raise schema_error(path, f"unexpected property `{key}`")
        return

    if schema_type is None:
        return

    if schema_type == "array":
        if not isinstance(data, list):
            raise schema_error(path, f"expected array, found {type(data).__name__}")

        min_items = schema.get("minItems")
        if min_items is not None and len(data) < min_items:
            raise schema_error(path, f"expected at least {min_items} item(s)")

        if schema.get("uniqueItems"):
            seen: set[str] = set()
            for item in data:
                marker = json.dumps(item, sort_keys=True)
                if marker in seen:
                    raise schema_error(path, "array items must be unique")
                seen.add(marker)

        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(data):
                validate_against_schema(item, item_schema, f"{path}[{index}]")
        return

    if schema_type == "string":
        if not isinstance(data, str):
            raise schema_error(path, f"expected string, found {type(data).__name__}")

        min_length = schema.get("minLength")
        if min_length is not None and len(data) < min_length:
            raise schema_error(path, f"string must be at least {min_length} character(s)")

        pattern = schema.get("pattern")
        if pattern and re.fullmatch(pattern, data) is None:
            raise schema_error(path, f"value `{data}` does not match pattern `{pattern}`")

        enum_values = schema.get("enum")
        if enum_values and data not in enum_values:
            raise schema_error(path, f"value `{data}` must be one of {', '.join(enum_values)}")
        return


def parse_frontmatter(markdown: str, source: Path) -> tuple[dict[str, str], str]:
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValidationError(f"{source} must start with frontmatter delimited by ---")

    frontmatter: dict[str, str] = {}
    body_start = None
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            body_start = index + 1
            break
        if not line.strip():
            continue
        if ":" not in line:
            raise ValidationError(f"{source} frontmatter line is invalid: {line}")
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip()

    if body_start is None:
        raise ValidationError(f"{source} frontmatter is missing a closing ---")

    body = "\n".join(lines[body_start:]).strip() + "\n"
    return frontmatter, body


def load_manifest(source: Path) -> Family:
    manifest_path = source / "family.json"
    if not manifest_path.exists():
        raise ValidationError(
            f"Missing family manifest. Expected canonical manifest file at {manifest_path}. "
            "This tool currently requires the manifest filename `family.json`."
        )

    try:
        manifest = json.loads(read_text(manifest_path))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{manifest_path} is not valid JSON: {exc}") from exc

    validate_against_schema(manifest, FAMILY_MANIFEST_SCHEMA)

    family_data = manifest.get("skill_family")
    name = str(family_data.get("name", "")).strip()
    description = str(family_data.get("description", "")).strip()
    version = str(family_data.get("version", "")).strip()

    ensure_slug(name, "skill_family.name")
    manifest_targets = manifest.get("targets", DEFAULT_TARGETS)
    targets = dedupe_preserve_order(canonicalize_target(str(target)) for target in manifest_targets)
    return Family(name=name, description=description, version=version, path=source, targets=targets)


def build_template_vars(
    bundle_dir: Path,
    target: str,
    family: Family,
    source_context: SourceContext,
    output_root: Path,
    destination: Path | None = None,
) -> dict[str, str]:
    vars_map = {
        "bundle_dir": str(bundle_dir),
        "family_name": family.name,
        "target": target,
        "source": str(source_context.path),
        "source_descriptor": source_context.descriptor,
        "output_root": str(output_root),
    }
    if destination is not None:
        vars_map["destination"] = str(destination)
    return vars_map


def run_templated_command(command_template: list[str], template_vars: dict[str, str], error_prefix: str) -> str:
    command = [part.format(**template_vars) for part in command_template]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        quoted = shlex.join(command)
        raise ValidationError(
            f"{error_prefix}\nRequired executable was not found: {exc.filename}\nCommand: {quoted}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        raise ValidationError(error_prefix + (f"\n{stderr}" if stderr else "")) from exc
    stdout = completed.stdout.strip()
    return stdout or "command completed"


def run_command(command: list[str], error_prefix: str, cwd: Path | None = None) -> str:
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, cwd=str(cwd) if cwd else None)
    except FileNotFoundError as exc:
        quoted = shlex.join(command)
        raise ValidationError(
            f"{error_prefix}\nRequired executable was not found: {exc.filename}\nCommand: {quoted}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        raise ValidationError(error_prefix + (f"\n{stderr}" if stderr else "")) from exc
    return completed.stdout.strip()


def http_json_request(method: str, url: str, headers: dict[str, str], data: bytes | None = None) -> dict:
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace").strip()
        raise ValidationError(f"HTTP {exc.code} calling {url}\n{error_body}") from exc
    except urllib.error.URLError as exc:
        raise ValidationError(f"Network error calling {url}: {exc}") from exc

    if not payload:
        return {}
    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Non-JSON response from {url}: {payload[:200]!r}") from exc


def build_multipart_form(files: list[tuple[str, str, str, bytes]]) -> tuple[bytes, str]:
    boundary = f"skilltooling-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for field_name, filename, content_type, content in files:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                content,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def publisher_api_key(target: str, config: PublisherConfig, default_env: str) -> str:
    env_name = config.api_key_env or default_env
    api_key = os.environ.get(env_name)
    if not api_key:
        raise ValidationError(f"Missing API key for {target}. Set {env_name} in your shell or .env file.")
    return api_key


def parse_version_number(payload: dict) -> int | None:
    for key in ("default_version", "latest_version", "version", "number"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return None


def state_file(history_dir: Path, name: str) -> Path:
    return history_dir / "state" / f"{name}.json"


def codex_skill_name(family: Family, skill: Skill) -> str:
    return f"{family.name}--{skill.skill_id}"


def resolve_codex_skills_root(
    install_paths: dict[str, Path],
    config: PublisherConfig | None,
) -> Path:
    direct_root = resolve_install_root("codex", install_paths, config)
    if direct_root is not None:
        return direct_root
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser().resolve() / "skills"
    return Path.home() / ".codex" / "skills"


def load_skill_overrides(repo_root: Path, skill_id: str, skill_targets: list[str]) -> dict[str, str]:
    overrides_root = repo_root / "overrides" / skill_id
    if not overrides_root.exists():
        return {}
    if not overrides_root.is_dir():
        raise ValidationError(f"Override path must be a directory: {overrides_root}")

    overrides: dict[str, str] = {}
    for override_file in sorted(overrides_root.glob("*.md")):
        target = canonicalize_target(override_file.stem)
        if target not in skill_targets:
            raise ValidationError(
                f"Override {override_file} targets {target}, but {skill_id} is not enabled for that target"
            )
        overrides[target] = read_text(override_file).strip() + "\n"
    return overrides


def load_skills(family: Family) -> list[Skill]:
    source_dir = family.path / "source"
    if not source_dir.is_dir():
        raise ValidationError(f"Missing source directory: {source_dir}")

    skills: list[Skill] = []
    for source_file in sorted(source_dir.glob("*.md")):
        skill_id = source_file.stem
        ensure_skill_id(skill_id)

        frontmatter, body = parse_frontmatter(read_text(source_file), source_file)
        display_name = frontmatter.get("name", "").strip() or skill_id
        description = frontmatter.get("description", "").strip()
        if not description:
            raise ValidationError(f"{source_file} frontmatter must include description")

        skill_targets = parse_target_list(frontmatter.get("targets"), family.targets)
        target_overrides = load_skill_overrides(family.path, skill_id, skill_targets)

        skills.append(
            Skill(
                skill_id=skill_id,
                display_name=display_name,
                description=description,
                path=source_file,
                frontmatter=frontmatter,
                body=body,
                targets=skill_targets,
                target_overrides=target_overrides,
            )
        )

    if not skills:
        raise ValidationError(f"No source skill files found under {source_dir}")
    return skills


def load_family_repo(source: Path) -> tuple[Family, list[Skill]]:
    family = load_manifest(source)
    skills = load_skills(family)
    return family, skills


def get_target_body(skill: Skill, target: str) -> str:
    return skill.target_overrides.get(target, skill.body)


def strip_leading_h1(body: str) -> str:
    lines = body.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).strip()
    return body.strip()


def render_target_skill_text(family: Family, skill: Skill, target: str) -> str:
    body = get_target_body(skill, target)
    title = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), skill.display_name)
    content = [
        f"# {title}",
        "",
        f"Family: `{family.name}`",
        f"Skill: `{skill.skill_id}`",
        f"Target: `{target}`",
        f"Description: {skill.description}",
        "",
        "## Instructions",
        strip_leading_h1(body),
        "",
    ]
    return "\n".join(content)


def render_family_target_text(family: Family, skills: list[Skill], target: str) -> str:
    lines = [
        f"# {family.name} - {target}",
        "",
        family.description,
        "",
        f"Version: `{family.version}`",
        "",
        "This file aggregates the target-specific skill text for the whole family.",
        "",
    ]
    for skill in skills:
        body = get_target_body(skill, target)
        title = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), skill.display_name)
        lines.extend(
            [
                f"## {title}",
                "",
                f"Skill: `{skill.skill_id}`",
                f"Description: {skill.description}",
                "",
                strip_leading_h1(body),
                "",
            ]
        )
    return "\n".join(lines)


def render_target_readme(family: Family, skills: list[Skill], target: str) -> str:
    ext = TARGET_FILE_EXTENSIONS[target]
    lines = [
        f"# {family.name} - {target}",
        "",
        "This directory is the generated target-specific view of the family.",
        "",
        "Editing rule:",
        "",
        "- Edit `source/*.md` for canonical skill content.",
        "- Edit `overrides/<skill-id>/<target>.md` only when this tool needs different wording.",
        "- Re-run `skill-deploy` to regenerate this directory.",
        "",
        "Files in this directory:",
        "",
        f"- `family{ext}` is the aggregated target-specific family text.",
        f"- `*.{ext.lstrip('.')}` files are the per-skill target-specific text used for this tool.",
        "- `manifest.json` records the generated bundle metadata.",
        "",
        "Skills:",
        "",
        *[f"- `{skill.skill_id}`" for skill in skills],
        "",
    ]
    return "\n".join(lines)


def build_manifest_payload(family: Family, skills: list[Skill], target: str) -> dict:
    return {
        "skill_family": {
            "name": family.name,
            "description": family.description,
            "version": family.version,
        },
        "target": target,
        "extension": TARGET_FILE_EXTENSIONS[target],
        "skills": [
            {
                "id": skill.skill_id,
                "name": skill.display_name,
                "description": skill.description,
            }
            for skill in skills
        ],
    }


def render_target_bundle(output_root: Path, family: Family, skills: list[Skill], target: str) -> Path:
    target_skills = [skill for skill in skills if target in skill.targets]
    if not target_skills:
        raise ValidationError(f"No skills in family {family.name} are enabled for target {target}")

    bundle_dir = output_root / target
    if bundle_dir.exists():
        try:
            shutil.rmtree(bundle_dir)
        except PermissionError as exc:
            raise ValidationError(
                f"Cannot rewrite generated target directory {bundle_dir}. "
                "The deploy process needs write permission to remove and recreate that folder. "
                "If the repo is outside the writable environment, run the command locally or use --output to write elsewhere."
            ) from exc
    bundle_dir.mkdir(parents=True, exist_ok=True)

    ext = TARGET_FILE_EXTENSIONS[target]
    write_json(bundle_dir / "manifest.json", build_manifest_payload(family, target_skills, target))
    write_text(bundle_dir / "README.md", render_target_readme(family, target_skills, target))
    write_text(bundle_dir / f"family{ext}", render_family_target_text(family, target_skills, target))
    for skill in target_skills:
        write_text(bundle_dir / f"{skill.skill_id}{ext}", render_target_skill_text(family, skill, target))

    return bundle_dir


def parse_install_paths(raw_install_paths: list[str]) -> dict[str, Path]:
    install_paths: dict[str, Path] = {}
    for raw_value in raw_install_paths:
        if "=" not in raw_value:
            raise ValidationError(f"Invalid --install-path value: {raw_value}. Expected target=/path")
        target_name, raw_path = raw_value.split("=", 1)
        target = canonicalize_target(target_name)
        if not raw_path.strip():
            raise ValidationError(f"Install path for target {target} cannot be empty")
        install_paths[target] = Path(raw_path).expanduser().resolve()
    return install_paths


def resolve_install_root(target: str, install_paths: dict[str, Path], config: PublisherConfig | None) -> Path | None:
    if target in install_paths:
        return install_paths[target]
    if config and config.install_root:
        return config.install_root
    raw_env_value = os.environ.get(TARGET_INSTALL_ENV[target])
    if not raw_env_value:
        return None
    return Path(raw_env_value).expanduser().resolve()


def load_publish_config(config_path: Path | None) -> dict[str, PublisherConfig]:
    if config_path is None:
        return {}
    if not config_path.exists():
        raise ValidationError(f"Publish config not found: {config_path}")

    try:
        payload = json.loads(read_text(config_path))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{config_path} is not valid JSON: {exc}") from exc

    validate_against_schema(payload, PUBLISH_CONFIG_SCHEMA)

    raw_targets = payload.get("targets")
    if not isinstance(raw_targets, dict):
        raise ValidationError(f"{config_path} must contain a targets object")

    configs: dict[str, PublisherConfig] = {}
    for raw_target, raw_config in raw_targets.items():
        target = canonicalize_target(raw_target)
        if not isinstance(raw_config, dict):
            raise ValidationError(f"Publisher config for {target} must be an object")

        mode = str(raw_config.get("mode", raw_config.get("publish", "copy"))).strip().lower()
        if mode not in {"copy", "command", "openai-skills", "claude-agent", "codex-skills"}:
            raise ValidationError(
                f"Publisher mode for {target} must be copy, command, openai-skills, claude-agent, or codex-skills"
            )

        install_root = None
        if "install_root" in raw_config:
            install_root = Path(str(raw_config["install_root"])).expanduser().resolve()

        command = None
        if mode == "command":
            raw_command = raw_config.get("command")
            if not isinstance(raw_command, list) or not raw_command or not all(isinstance(item, str) for item in raw_command):
                raise ValidationError(f"Publisher command for {target} must be a non-empty list of strings")
            command = list(raw_command)

        verify_command = None
        raw_verify_command = raw_config.get("verify_command")
        if raw_verify_command is not None:
            if not isinstance(raw_verify_command, list) or not raw_verify_command or not all(
                isinstance(item, str) for item in raw_verify_command
            ):
                raise ValidationError(f"verify_command for {target} must be a non-empty list of strings")
            verify_command = list(raw_verify_command)

        rollback_command = None
        raw_rollback_command = raw_config.get("rollback_command")
        if raw_rollback_command is not None:
            if not isinstance(raw_rollback_command, list) or not raw_rollback_command or not all(
                isinstance(item, str) for item in raw_rollback_command
            ):
                raise ValidationError(f"rollback_command for {target} must be a non-empty list of strings")
            rollback_command = list(raw_rollback_command)

        api_key_env = None
        if "api_key_env" in raw_config:
            api_key_env = str(raw_config["api_key_env"])

        base_url = None
        if "base_url" in raw_config:
            base_url = str(raw_config["base_url"]).rstrip("/")

        cli_path = None
        if "cli_path" in raw_config:
            cli_path = str(raw_config["cli_path"])

        model = None
        if "model" in raw_config:
            model = str(raw_config["model"])

        tool = None
        if "tool" in raw_config:
            tool = str(raw_config["tool"])

        configs[target] = PublisherConfig(
            mode=mode,
            install_root=install_root,
            command=command,
            verify_command=verify_command,
            rollback_command=rollback_command,
            api_key_env=api_key_env,
            base_url=base_url,
            cli_path=cli_path,
            model=model,
            tool=tool,
        )

    return configs


def resolve_publish_config_path(args: argparse.Namespace, source_root: Path | None = None) -> Path | None:
    tooling_root = Path(__file__).resolve().parent.parent

    if args.config:
        return Path(args.config).expanduser().resolve()

    env_path = os.environ.get("SKILL_TOOLING_CONFIG")
    if env_path:
        env_candidate = Path(env_path).expanduser()
        if not env_candidate.is_absolute():
            env_candidate = tooling_root / env_candidate
        return env_candidate.resolve()

    search_roots: list[Path] = []
    if source_root is not None:
        search_roots.append(source_root)
    search_roots.append(Path.cwd())
    search_roots.append(tooling_root)

    seen: set[Path] = set()
    for root in search_roots:
        if root in seen:
            continue
        seen.add(root)
        for filename in DEFAULT_PUBLISH_CONFIG_FILENAMES:
            candidate = root / filename
            if candidate.exists():
                return candidate.resolve()

    return None


def resolve_command_executable(executable: str) -> Path | None:
    candidate = Path(executable).expanduser()
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    resolved = shutil.which(executable)
    return Path(resolved).resolve() if resolved else None


def ensure_writable_directory(path: Path, label: str) -> None:
    probe_root = path if path.exists() else path.parent
    if not probe_root.exists():
        probe_root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(dir=probe_root, prefix=".skill-tooling-write-test-", delete=True):
            pass
    except PermissionError as exc:
        raise ValidationError(f"{label} is not writable: {probe_root}") from exc


def preflight_publish_target(
    target: str,
    family: Family,
    install_paths: dict[str, Path],
    publish_configs: dict[str, PublisherConfig],
) -> tuple[str, str]:
    config = publish_configs.get(target)
    if config is None:
        config = PublisherConfig(mode="copy")

    mode = config.mode
    if mode == "copy":
        install_root = resolve_install_root(target, install_paths, config)
        if install_root is None:
            env_name = TARGET_INSTALL_ENV[target]
            raise ValidationError(
                f"{target}: no install root configured for copy publish. "
                f"Use --install-path {target}=/path, set {env_name}, or define install_root in publish-config.json."
            )
        ensure_writable_directory(install_root, f"{target} install root")
        return mode, f"install root {install_root}"

    if mode == "command":
        if not config.command:
            raise ValidationError(f"{target}: command publish mode is configured but no command is defined")
        executable = resolve_command_executable(config.command[0])
        if executable is None:
            raise ValidationError(f"{target}: required publish executable not found: {config.command[0]}")
        return mode, str(executable)

    if mode == "openai-skills":
        env_name = config.api_key_env or "OPENAI_API_KEY"
        publisher_api_key(target, config, "OPENAI_API_KEY")
        return mode, f"API key {env_name}"

    if mode == "claude-agent":
        cli_path = config.cli_path or "ant"
        executable = resolve_command_executable(cli_path)
        if executable is None:
            raise ValidationError(f"{target}: required Claude executable not found: {cli_path}")
        return mode, str(executable)

    if mode == "codex-skills":
        install_root = resolve_codex_skills_root(install_paths, config)
        ensure_writable_directory(install_root, f"{target} skills root")
        return mode, f"skills root {install_root}"

    raise ValidationError(f"{target}: unsupported publish mode {mode}")


def preflight_publish_targets(
    selected_targets: list[str],
    family: Family,
    install_paths: dict[str, Path],
    publish_configs: dict[str, PublisherConfig],
) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []
    errors: list[str] = []
    for target in selected_targets:
        try:
            mode, detail = preflight_publish_target(target, family, install_paths, publish_configs)
            results.append((target, mode, detail))
        except ValidationError as exc:
            errors.append(str(exc))
    if errors:
        lines = ["Publish preflight failed:"] + [f"- {error}" for error in errors]
        raise ValidationError("\n".join(lines))
    return results


def publish_copy(
    bundle_dir: Path,
    target: str,
    family: Family,
    install_paths: dict[str, Path],
    config: PublisherConfig | None,
    backup_root: Path,
) -> tuple[Path, Path | None, bool]:
    install_root = resolve_install_root(target, install_paths, config)
    if install_root is None:
        env_name = TARGET_INSTALL_ENV[target]
        raise ValidationError(
            f"Publish requested for target {target}, but no install root was provided. "
            f"Use --install-path {target}=/path, set {env_name}, or define install_root in the publish config."
        )

    destination = install_root / family.name
    had_existing_destination = destination.exists()
    backup_path = backup_root / target if had_existing_destination else None

    if backup_path and backup_path.exists():
        shutil.rmtree(backup_path)

    if had_existing_destination and backup_path is not None:
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(destination), str(backup_path))

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bundle_dir, destination)
    except Exception as exc:  # pragma: no cover - exercised through failure path only
        if destination.exists():
            shutil.rmtree(destination)
        if had_existing_destination and backup_path is not None and backup_path.exists():
            shutil.move(str(backup_path), str(destination))
        raise ValidationError(f"Copy publish failed for target {target}: {exc}") from exc

    return destination, backup_path, had_existing_destination


def publish_command(
    bundle_dir: Path,
    target: str,
    family: Family,
    source_context: SourceContext,
    output_root: Path,
    config: PublisherConfig,
) -> str:
    if not config.command:
        raise ValidationError(f"Target {target} is configured for command publishing but no command is defined")

    template_vars = build_template_vars(bundle_dir, target, family, source_context, output_root)
    return run_templated_command(
        config.command,
        template_vars,
        f"Publish command failed for target {target}: {' '.join(config.command)}",
    )


def build_openai_skill_bundle(skill: Skill, family: Family, target: str, work_dir: Path) -> Path:
    skill_root = work_dir / skill.skill_id
    skill_root.mkdir(parents=True, exist_ok=True)
    skill_markdown = "\n".join(
        [
            "---",
            f"name: {family.name}-{skill.skill_id}",
            f"description: {skill.description}",
            "---",
            strip_leading_h1(get_target_body(skill, target)),
            "",
        ]
    )
    write_text(skill_root / "SKILL.md", skill_markdown)
    zip_path = work_dir / f"{skill.skill_id}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(skill_root / "SKILL.md", arcname=f"{skill.skill_id}/SKILL.md")
    return zip_path


def render_codex_skill_markdown(family: Family, skill: Skill, target: str) -> str:
    return "\n".join(
        [
            "---",
            f"name: {json.dumps(codex_skill_name(family, skill))}",
            f"description: {json.dumps(f'{family.name}: {skill.description}')}",
            "---",
            get_target_body(skill, target).rstrip(),
            "",
        ]
    )


def publish_codex_skills(
    bundle_dir: Path,
    target: str,
    family: Family,
    skills: list[Skill],
    install_paths: dict[str, Path],
    history_dir: Path,
    config: PublisherConfig | None,
) -> PublishResult:
    install_root = resolve_codex_skills_root(install_paths, config)
    state_path = state_file(history_dir, f"codex-skills-{target}-{family.name}")
    installed_skills: dict[str, dict[str, str]] = {}
    installed_count = 0

    for skill in skills:
        if target not in skill.targets:
            continue
        skill_name = codex_skill_name(family, skill)
        destination = install_root / skill_name
        try:
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(parents=True, exist_ok=True)
            write_text(destination / "SKILL.md", render_codex_skill_markdown(family, skill, target))
        except PermissionError as exc:
            raise ValidationError(
                f"Cannot install Codex skill {skill_name} into {destination}. "
                "The deploy process needs write permission to the Codex skills directory. "
                "Set CODEX_HOME or SKILL_TOOLING_CODEX_INSTALL_ROOT to a writable location, or run locally with sufficient permissions."
            ) from exc
        installed_skills[skill.skill_id] = {
            "skill_name": skill_name,
            "destination": str(destination),
        }
        installed_count += 1

    write_json(
        state_path,
        {
            "target": target,
            "family": family.name,
            "skills_root": str(install_root),
            "skills": installed_skills,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return PublishResult(
        target=target,
        mode="codex-skills",
        bundle_dir=bundle_dir,
        destination=state_path,
        publish_result=f"installed {installed_count} Codex skill(s) into {install_root}; state {state_path}",
        verification_result=f"verified {installed_count} Codex skill directory(s)",
        rollback_mode="none",
    )


def publish_openai_skills(
    bundle_dir: Path,
    target: str,
    family: Family,
    skills: list[Skill],
    history_dir: Path,
    config: PublisherConfig,
) -> PublishResult:
    api_key = publisher_api_key(target, config, "OPENAI_API_KEY")
    base_url = config.base_url or "https://api.openai.com/v1"
    state_path = state_file(history_dir, f"openai-skills-{target}-{family.name}")
    state = read_json_if_exists(state_path) or {"skills": {}}
    state_skills = state.setdefault("skills", {})
    created = 0
    updated = 0

    with tempfile.TemporaryDirectory(prefix="skill-tooling-openai-") as temp_dir:
        temp_path = Path(temp_dir)
        for skill in skills:
            if target not in skill.targets:
                continue

            zip_path = build_openai_skill_bundle(skill, family, target, temp_path / skill.skill_id)
            zip_bytes = zip_path.read_bytes()
            body, content_type = build_multipart_form(
                [("files", zip_path.name, "application/zip", zip_bytes)]
            )
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": content_type,
            }
            record = state_skills.get(skill.skill_id)
            if record and record.get("remote_id"):
                remote_id = str(record["remote_id"])
                response = http_json_request(
                    "POST",
                    f"{base_url}/skills/{remote_id}/versions",
                    headers,
                    body,
                )
                version_number = parse_version_number(response)
                if version_number is not None:
                    http_json_request(
                        "POST",
                        f"{base_url}/skills/{remote_id}",
                        {
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json.dumps({"default_version": version_number}).encode("utf-8"),
                    )
                record["latest_version"] = version_number
                updated += 1
            else:
                response = http_json_request(
                    "POST",
                    f"{base_url}/skills",
                    headers,
                    body,
                )
                remote_id = response.get("id")
                if not isinstance(remote_id, str) or not remote_id:
                    raise ValidationError(f"OpenAI create skill response missing id for {skill.skill_id}")
                version_number = parse_version_number(response)
                state_skills[skill.skill_id] = {
                    "remote_id": remote_id,
                    "latest_version": version_number,
                    "name": f"{family.name}-{skill.skill_id}",
                }
                created += 1

    write_json(state_path, state)
    return PublishResult(
        target=target,
        mode="openai-skills",
        bundle_dir=bundle_dir,
        destination=state_path,
        publish_result=f"created {created}, updated {updated} hosted skills; state {state_path}",
        verification_result=f"API responses succeeded for {created + updated} skill bundle(s)",
        rollback_mode="none",
    )


def publish_claude_agent(
    bundle_dir: Path,
    target: str,
    family: Family,
    history_dir: Path,
    config: PublisherConfig,
) -> PublishResult:
    cli_path = config.cli_path or "ant"
    model = config.model or "claude-opus-4-8"
    tool = config.tool or "{type: agent_toolset_20260401}"
    state_path = state_file(history_dir, f"claude-agent-{target}-{family.name}")
    state = read_json_if_exists(state_path) or {}
    system_prompt = read_text(bundle_dir / f"family{TARGET_FILE_EXTENSIONS[target]}")

    if state.get("agent_id") and state.get("version") is not None:
        command = [
            cli_path,
            "beta:agents",
            "update",
            "--agent-id",
            str(state["agent_id"]),
            "--version",
            str(state["version"]),
            "--system",
            system_prompt,
            "--format",
            "json",
        ]
    else:
        command = [
            cli_path,
            "beta:agents",
            "create",
            "--name",
            family.name,
            "--model",
            f"{{id: {model}}}",
            "--system",
            system_prompt,
            "--tool",
            tool,
            "--format",
            "json",
        ]

    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        quoted = shlex.join(command)
        raise ValidationError(
            f"Claude agent publish failed for target {target}: required executable was not found: {exc.filename}\nCommand: {quoted}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        raise ValidationError(
            f"Claude agent command failed for target {target}: {' '.join(command)}"
            + (f"\n{stderr}" if stderr else "")
        ) from exc

    stdout = completed.stdout.strip()
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Claude agent command returned non-JSON output: {stdout[:200]!r}") from exc

    agent_id = response.get("id")
    version = response.get("version")
    if not isinstance(agent_id, str) or not isinstance(version, int):
        raise ValidationError("Claude agent response missing id/version")

    write_json(
        state_path,
        {
            "agent_id": agent_id,
            "version": version,
            "name": family.name,
            "target": target,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    action = "updated" if state.get("agent_id") else "created"
    return PublishResult(
        target=target,
        mode="claude-agent",
        bundle_dir=bundle_dir,
        destination=state_path,
        publish_result=f"{action} Claude agent {agent_id} version {version}; state {state_path}",
        verification_result=f"CLI response succeeded for agent {agent_id}",
        rollback_mode="none",
    )


def verify_published_target(
    bundle_dir: Path,
    target: str,
    family: Family,
    source_context: SourceContext,
    output_root: Path,
    destination: Path | None,
    config: PublisherConfig | None,
) -> str:
    if config and config.verify_command:
        template_vars = build_template_vars(bundle_dir, target, family, source_context, output_root, destination)
        return run_templated_command(
            config.verify_command,
            template_vars,
            f"Verify command failed for target {target}: {' '.join(config.verify_command)}",
        )

    if destination is None:
        return "no verification hook configured"

    manifest_path = destination / "manifest.json"
    if not destination.exists() or not manifest_path.exists():
        raise ValidationError(f"Built-in verification failed for target {target}: destination or manifest missing")
    return f"verified destination {destination}"


def resolve_history_dir(args: argparse.Namespace, source_context: SourceContext, family: Family) -> Path:
    if getattr(args, "history_dir", None):
        return Path(args.history_dir).expanduser().resolve()
    if getattr(args, "repo", None):
        return Path.cwd() / HISTORY_ROOT_DIRNAME / "deployments" / family.name
    return source_context.path / HISTORY_ROOT_DIRNAME / "deployments"


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_receipt(history_dir: Path, deployment_id: str, payload: dict) -> Path:
    receipts_dir = history_dir / "receipts"
    receipt_path = receipts_dir / f"{deployment_id}.json"
    write_json(receipt_path, payload)
    return receipt_path


def publish_with_rollback(
    bundle_dir: Path,
    target: str,
    family: Family,
    source_context: SourceContext,
    output_root: Path,
    install_paths: dict[str, Path],
    publish_configs: dict[str, PublisherConfig],
    backup_root: Path,
    history_dir: Path,
    skills: list[Skill],
) -> PublishResult:
    config = publish_configs.get(target)
    if config is None:
        config = PublisherConfig(mode="copy")

    if config.mode == "openai-skills":
        return publish_openai_skills(bundle_dir, target, family, skills, history_dir, config)

    if config.mode == "claude-agent":
        return publish_claude_agent(bundle_dir, target, family, history_dir, config)

    if config.mode == "codex-skills":
        return publish_codex_skills(bundle_dir, target, family, skills, install_paths, history_dir, config)

    if config.mode == "copy":
        destination, backup_path, had_existing_destination = publish_copy(
            bundle_dir,
            target,
            family,
            install_paths,
            config,
            backup_root,
        )
        try:
            verification_result = verify_published_target(
                bundle_dir,
                target,
                family,
                source_context,
                output_root,
                destination,
                config,
            )
        except ValidationError:
            if destination.exists():
                shutil.rmtree(destination)
            if had_existing_destination and backup_path is not None and backup_path.exists():
                shutil.move(str(backup_path), str(destination))
            raise

        return PublishResult(
            target=target,
            mode="copy",
            bundle_dir=bundle_dir,
            destination=destination,
            publish_result=f"copied to {destination}",
            verification_result=verification_result,
            rollback_mode="copy_restore",
            backup_path=backup_path,
            had_existing_destination=had_existing_destination,
        )

    publish_result = publish_command(bundle_dir, target, family, source_context, output_root, config)
    verification_result = verify_published_target(
        bundle_dir,
        target,
        family,
        source_context,
        output_root,
        None,
        config,
    )
    rollback_mode = "command" if config.rollback_command else "none"
    rollback_command = None
    if config.rollback_command:
        rollback_command = [
            part.format(**build_template_vars(bundle_dir, target, family, source_context, output_root))
            for part in config.rollback_command
        ]

    return PublishResult(
        target=target,
        mode="command",
        bundle_dir=bundle_dir,
        destination=None,
        publish_result=publish_result,
        verification_result=verification_result,
        rollback_mode=rollback_mode,
        rollback_command=rollback_command,
    )


def publish_result_to_dict(result: PublishResult) -> dict:
    return {
        "target": result.target,
        "mode": result.mode,
        "bundle_dir": str(result.bundle_dir),
        "destination": str(result.destination) if result.destination else None,
        "publish_result": result.publish_result,
        "verification_result": result.verification_result,
        "rollback": {
            "mode": result.rollback_mode,
            "backup_path": str(result.backup_path) if result.backup_path else None,
            "had_existing_destination": result.had_existing_destination,
            "command": result.rollback_command,
        },
    }


def repo_to_clone_url(repo: str) -> str:
    repo = repo.strip()
    repo_path = Path(repo).expanduser()
    if repo_path.exists():
        return str(repo_path.resolve())
    if repo.startswith("http://"):
        raise ValidationError("Insecure http:// git URLs are not allowed. Use https://, ssh://, git@, or a local path.")
    if repo.startswith(("https://", "ssh://", "git@", "file://")):
        return repo
    if GITHUB_REPO_RE.match(repo):
        return f"https://github.com/{repo}.git"
    raise ValidationError(
        f"Unsupported --repo value: {repo}. Use a local path, a git URL, or an owner/repo GitHub identifier."
    )


def ensure_git_repo(path: Path) -> None:
    run_command(["git", "rev-parse", "--show-toplevel"], f"{path} is not inside a git repository", cwd=path)


def git_current_branch(path: Path) -> str:
    return run_command(["git", "branch", "--show-current"], "Failed to determine current git branch", cwd=path)


def git_has_staged_or_unstaged_changes(path: Path) -> bool:
    status = run_command(["git", "status", "--porcelain"], "Failed to determine git status", cwd=path)
    return bool(status.strip())


def checkout_release_branch(path: Path, branch: str) -> None:
    existing = run_command(["git", "branch", "--list", branch], f"Failed checking whether branch {branch} exists", cwd=path)
    if existing.strip():
        run_command(["git", "checkout", branch], f"Failed to checkout existing branch {branch}", cwd=path)
    else:
        run_command(["git", "checkout", "-b", branch], f"Failed to create branch {branch}", cwd=path)


def run_git_workflow(args: argparse.Namespace, repo_path: Path, family: Family) -> None:
    if getattr(args, "repo", None):
        raise ValidationError("Git workflow options are only supported with --source, not --repo")
    ensure_git_repo(repo_path)

    if args.merge_pr and not args.open_pr:
        raise ValidationError("--merge-pr requires --open-pr")
    if args.open_pr and not args.push:
        raise ValidationError("--open-pr requires --push")

    if args.branch:
        checkout_release_branch(repo_path, args.branch)
        print(f"Git branch: {args.branch}")
    else:
        print(f"Git branch: {git_current_branch(repo_path)}")

    run_command(["git", "add", "."], "Failed to stage changes for release", cwd=repo_path)
    if not git_has_staged_or_unstaged_changes(repo_path):
        print("Git: no changes to commit")
        return

    commit_message = args.commit_message or f"Deploy {family.name}"
    run_command(["git", "commit", "-m", commit_message], "Failed to create release commit", cwd=repo_path)
    print(f"Git commit: {commit_message}")

    branch_name = git_current_branch(repo_path)
    if args.push:
        run_command(["git", "push", "-u", "origin", branch_name], f"Failed to push branch {branch_name}", cwd=repo_path)
        print(f"Git push: {branch_name}")

    if args.open_pr:
        base = args.base or "main"
        pr_title = args.pr_title or commit_message
        pr_body = "\n".join(
            [
                f"Automated skill release for `{family.name}`.",
                "",
                "Generated by `skill-deploy --git`.",
            ]
        )
        pr_url = run_command(
            [
                "gh",
                "pr",
                "create",
                "--base",
                base,
                "--head",
                branch_name,
                "--title",
                pr_title,
                "--body",
                pr_body,
            ],
            f"Failed to create pull request for branch {branch_name}",
            cwd=repo_path,
        )
        print(f"Git PR: {pr_url.splitlines()[-1]}")

        if args.merge_pr:
            merge_command = ["gh", "pr", "merge", branch_name, "--merge"]
            if args.delete_branch:
                merge_command.append("--delete-branch")
            run_command(merge_command, f"Failed to merge pull request for branch {branch_name}", cwd=repo_path)
            print(f"Git merge: {branch_name} -> {base}")


@contextlib.contextmanager
def resolve_source_context(args: argparse.Namespace) -> Iterable[SourceContext]:
    if getattr(args, "repo", None):
        clone_url = repo_to_clone_url(args.repo)
        with tempfile.TemporaryDirectory(prefix="skill-tooling-repo-") as temp_dir:
            clone_path = Path(temp_dir) / "repo"
            command = ["git", "clone", "--depth", "1"]
            if getattr(args, "ref", None):
                command.extend(["--branch", args.ref])
            command.extend([clone_url, str(clone_path)])
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr.strip()
                raise ValidationError(
                    f"Failed to clone repo {args.repo}"
                    + (f" at ref {args.ref}" if getattr(args, "ref", None) else "")
                    + (f"\n{stderr}" if stderr else "")
                ) from exc
            yield SourceContext(path=clone_path.resolve(), descriptor=f"repo:{args.repo}")
        return

    source = Path(getattr(args, "source", ".")).expanduser().resolve()
    yield SourceContext(path=source, descriptor=str(source))


def create_family_repo(args: argparse.Namespace) -> int:
    family_name = args.family_name.strip()
    description = args.description.strip()

    ensure_slug(family_name, "family-name")
    if not description:
        raise ValidationError("description must be non-empty")

    targets = dedupe_preserve_order(canonicalize_target(target) for target in (args.target or DEFAULT_TARGETS))
    repo_path = Path(args.path).expanduser().resolve() / family_name
    if repo_path.exists():
        raise ValidationError(f"Destination already exists: {repo_path}")

    orchestrator_id = "orchestrator"
    write_json(
        repo_path / "family.json",
        {
            "skill_family": {
                "name": family_name,
                "description": description,
                "version": "0.1.0",
            },
            "targets": targets,
        },
    )

    readme = "\n".join(
        [
            f"# {family_name}",
            "",
            description,
            "",
            "## Repository Contract",
            "",
            "- `family.json` is family metadata, not a manually maintained skill index.",
            "- `source/` contains the canonical authored skill files.",
            "- Top-level tool folders like `grok/` and `claude/` are generated by `skill-tooling`.",
            "- `overrides/<skill-id>/<target>.md` is optional and only used when a tool needs different wording.",
            "",
            "## Layout",
            "",
            "```text",
            f"{family_name}/",
            "  family.json",
            "  source/",
            f"    {orchestrator_id}.md",
            "  overrides/",
            f"    {orchestrator_id}/",
            "      claude.md",
            "  grok/",
            "  claude/",
            "  codex/",
            "```",
            "",
            "## Common Commands",
            "",
            "Generate tool-specific folders in this repo:",
            "",
            "```bash",
            "path/to/skill-tooling/scripts/skill-deploy --source .",
            "```",
            "",
            "Publish every enabled target with one command:",
            "",
            "```bash",
            "path/to/skill-tooling/scripts/skill-deploy --source . --publish --config path/to/publish-config.json",
            "```",
            "",
        ]
    )
    write_text(repo_path / "README.md", readme)
    gitignore_lines = [
        "grok/",
        "grok-build/",
        "claude/",
        "claude-code/",
        "openai-chatgpt/",
        "codex/",
        ".skill-tooling/",
        ".env",
        ".env.*",
        "!.env.example",
        ".skill-tooling.env",
        ".skill-tooling.env.*",
        "!.skill-tooling.env.example",
    ]
    write_text(repo_path / ".gitignore", "\n".join(gitignore_lines) + "\n")

    source_markdown = "\n".join(
        [
            "---",
            "name: Orchestrator",
            f"description: Primary orchestrator for the {family_name} family",
            f"targets: {', '.join(targets)}",
            "---",
            "",
            "# Orchestrator",
            "",
            "## Purpose",
            "",
            f"Coordinate the {family_name} family and route work to specialist skills when they exist.",
            "",
            "## Operating Rules",
            "",
            "- Start from the user's explicit objective.",
            "- Decompose the work into the smallest set of steps that preserves quality.",
            "- Escalate only when a specialist skill materially improves the result.",
            "",
        ]
    )
    write_text(repo_path / "source" / f"{orchestrator_id}.md", source_markdown)

    example_override = "\n".join(
        [
            "# Orchestrator",
            "",
            "Use the Claude-specific framing for this skill when needed.",
            "",
        ]
    )
    write_text(repo_path / "overrides" / orchestrator_id / "claude.md", example_override)

    print(f"Created family repository at {repo_path}")
    print("Next steps:")
    print(f"1. Replace the scaffolded content in {repo_path / 'source' / f'{orchestrator_id}.md'}")
    print(f"2. Remove or replace the example override in {repo_path / 'overrides' / orchestrator_id / 'claude.md'}")
    print(f"3. Adjust {repo_path / 'family.json'} only if you need different metadata, version, or targets")
    print("4. Run scripts/skill-deploy from the family repo to generate tool folders")
    return 0


def validate_family_repo(args: argparse.Namespace) -> int:
    with resolve_source_context(args) as source_context:
        family, skills = load_family_repo(source_context.path)

    print(f"Family: {family.name}")
    print(f"Description: {family.description}")
    print(f"Version: {family.version}")
    print(f"Targets: {', '.join(family.targets)}")
    print(f"Skills: {len(skills)}")
    for skill in skills:
        overrides = ", ".join(sorted(skill.target_overrides))
        suffix = f" | overrides: {overrides}" if overrides else ""
        print(f"- {skill.skill_id}: {', '.join(skill.targets)}{suffix}")
    print("Validation passed.")
    return 0


def deploy_family_repo(args: argparse.Namespace) -> int:
    requested_targets = args.target or ["all"]
    install_paths = parse_install_paths(args.install_path or [])
    publish_requested = args.publish or args.install or bool(args.install_path)
    if (args.push or args.open_pr or args.merge_pr or args.branch or args.commit_message or args.pr_title or args.delete_branch) and not args.git:
        raise ValidationError("Git workflow flags require --git")

    with resolve_source_context(args) as source_context:
        loaded_env_files = autoload_dotenv(
            source_context.path,
            include_source_root=not bool(getattr(args, "repo", None)),
        )
        config_path = resolve_publish_config_path(args, source_context.path)
        publish_configs = load_publish_config(config_path)
        family, skills = load_family_repo(source_context.path)

        selected_targets: list[str] = []
        for requested_target in requested_targets:
            canonical = canonicalize_target(requested_target)
            if canonical == "all":
                selected_targets.extend(family.targets)
            else:
                selected_targets.append(canonical)
        selected_targets = dedupe_preserve_order(selected_targets)

        output_root = Path(args.output).expanduser().resolve() if args.output else source_context.path
        output_root.mkdir(parents=True, exist_ok=True)
        history_dir = resolve_history_dir(args, source_context, family)
        deployment_id = timestamp_id()
        backup_root = history_dir / "backups" / deployment_id

        print(f"Deploying family {family.name}")
        print(f"Source: {source_context.descriptor}")
        print(f"Resolved source: {source_context.path}")
        print(f"Output root: {output_root}")
        print(f"History dir: {history_dir}")
        if config_path is not None:
            print(f"Publish config: {config_path}")
        if loaded_env_files:
            print("Loaded env files:")
            for env_file in loaded_env_files:
                print(f"- {env_file}")

        if publish_requested:
            preflight_results = preflight_publish_targets(selected_targets, family, install_paths, publish_configs)
            print("Publish preflight:")
            for target, mode, detail in preflight_results:
                print(f"- {target}: {mode} | {detail}")

        receipt_targets: list[dict] = []

        for target in selected_targets:
            bundle_dir = render_target_bundle(output_root, family, skills, target)
            print(f"- Generated {target}: {bundle_dir}")
            if publish_requested:
                result = publish_with_rollback(
                    bundle_dir,
                    target,
                    family,
                    source_context,
                    output_root,
                    install_paths,
                    publish_configs,
                    backup_root,
                    history_dir,
                    skills,
                )
                receipt_targets.append(publish_result_to_dict(result))
                print(f"  Deployed to {TARGET_DISPLAY_NAMES.get(target, target)}: {result.publish_result}")
                print(f"  Verified {target}: {result.verification_result}")
            else:
                receipt_targets.append(
                    {
                        "target": target,
                        "mode": "generate-only",
                        "bundle_dir": str(bundle_dir),
                        "destination": None,
                        "publish_result": "not published",
                        "verification_result": "not verified",
                        "rollback": {"mode": "none", "backup_path": None, "had_existing_destination": False, "command": None},
                    }
                )

        if publish_requested:
            print(f"Published targets: {', '.join(selected_targets)}")
        else:
            print(
                "Generated target bundles only. Nothing was published. "
                "Re-run with --publish to publish all family-enabled targets "
                "or combine --publish with --target to limit the publish set."
            )

        receipt_payload = {
            "deployment_id": deployment_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "skill_family": {
                "name": family.name,
                "description": family.description,
                "version": family.version,
            },
            "source_descriptor": source_context.descriptor,
            "resolved_source": str(source_context.path),
            "output_root": str(output_root),
            "history_dir": str(history_dir),
            "published": publish_requested,
            "targets": receipt_targets,
        }
        receipt_path = write_receipt(history_dir, deployment_id, receipt_payload)
        print(f"Receipt: {receipt_path}")

        if args.git:
            run_git_workflow(args, source_context.path, family)

    print("Deployment complete.")
    return 0


def rollback_deployment(args: argparse.Namespace) -> int:
    receipt_path = Path(args.receipt).expanduser().resolve()
    if not receipt_path.exists():
        raise ValidationError(f"Receipt not found: {receipt_path}")

    try:
        receipt = json.loads(read_text(receipt_path))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{receipt_path} is not valid JSON: {exc}") from exc

    selected_targets = None
    if args.target:
        selected_targets = {canonicalize_target(target) for target in args.target}

    for target_entry in receipt.get("targets", []):
        target = canonicalize_target(str(target_entry.get("target")))
        if selected_targets and target not in selected_targets:
            continue

        rollback_info = target_entry.get("rollback", {})
        rollback_mode = rollback_info.get("mode", "none")
        destination = target_entry.get("destination")
        destination_path = Path(destination).expanduser().resolve() if destination else None

        if rollback_mode == "copy_restore":
            if destination_path is None:
                raise ValidationError(f"Receipt is missing destination for target {target}")

            had_existing_destination = bool(rollback_info.get("had_existing_destination"))
            backup_path_value = rollback_info.get("backup_path")
            backup_path = Path(backup_path_value).expanduser().resolve() if backup_path_value else None

            if destination_path.exists():
                shutil.rmtree(destination_path)

            if had_existing_destination:
                if backup_path is None or not backup_path.exists():
                    raise ValidationError(f"Rollback backup missing for target {target}")
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(backup_path), str(destination_path))
                print(f"Rolled back {target}: restored {destination_path}")
            else:
                print(f"Rolled back {target}: removed {destination_path}")
            continue

        if rollback_mode == "command":
            if not args.allow_command_rollback:
                raise ValidationError(
                    "Command rollback is disabled by default because receipts may execute arbitrary commands. "
                    "Re-run with --allow-command-rollback if you trust this receipt."
                )
            rollback_command = rollback_info.get("command")
            if not isinstance(rollback_command, list) or not rollback_command:
                raise ValidationError(f"Receipt is missing rollback command for target {target}")
            run_templated_command(rollback_command, {}, f"Rollback command failed for target {target}: {' '.join(rollback_command)}")
            print(f"Rolled back {target}: command completed")
            continue

        print(f"Skipped {target}: target is not rollbackable from this receipt")

    print("Rollback complete.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scaffold, validate, and deploy skill family repositories.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create-family", help="Scaffold a new skill family repository.")
    create_parser.add_argument("family_name", help="Lowercase slug for the new family repository.")
    create_parser.add_argument("description", help="Short description of the family.")
    create_parser.add_argument("--path", default=".", help="Parent directory where the new family repository should be created.")
    create_parser.add_argument("--target", action="append", help="Enabled deployment target. Repeatable. Defaults to all supported targets.")
    create_parser.set_defaults(func=create_family_repo)

    validate_parser = subparsers.add_parser("validate", help="Validate an existing family repository.")
    validate_source_group = validate_parser.add_mutually_exclusive_group()
    validate_source_group.add_argument("--source", help="Path to the family repository.")
    validate_source_group.add_argument("--repo", help="Local git path, git URL, or GitHub owner/repo.")
    validate_parser.add_argument("--ref", help="Git branch, tag, or ref to clone when using --repo.")
    validate_parser.set_defaults(func=validate_family_repo)

    deploy_parser = subparsers.add_parser("deploy", help="Generate and optionally publish target folders.")
    deploy_source_group = deploy_parser.add_mutually_exclusive_group()
    deploy_source_group.add_argument("--source", help="Path to the family repository.")
    deploy_source_group.add_argument("--repo", help="Local git path, git URL, or GitHub owner/repo.")
    deploy_parser.add_argument("--ref", help="Git branch, tag, or ref to clone when using --repo.")
    deploy_parser.add_argument("--output", help="Output root for generated tool directories. Defaults to the source repo root.")
    deploy_parser.add_argument("--target", action="append", help="Deployment target. Repeatable. Use all to deploy every family-enabled target.")
    deploy_parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish every selected target using the configured publishers. If --target is omitted, publishes all targets listed in family.json.",
    )
    deploy_parser.add_argument("--install", action="store_true", help="Compatibility alias for --publish when using copy-based publishers.")
    deploy_parser.add_argument("--install-path", action="append", help="Copy-publisher install root in the form target=/path. Repeatable.")
    deploy_parser.add_argument("--config", help="Path to the publish config JSON. Defaults to SKILL_TOOLING_CONFIG if set.")
    deploy_parser.add_argument("--history-dir", help="Directory where deployment receipts and backups should be stored.")
    deploy_parser.add_argument("--git", action="store_true", help="Stage and commit the resulting repo changes after deploy. Local --source repos only.")
    deploy_parser.add_argument("--branch", help="Git branch to create or checkout before committing deploy changes.")
    deploy_parser.add_argument("--commit-message", help="Git commit message to use when --git is enabled. Defaults to `Deploy <family-name>`.")
    deploy_parser.add_argument("--push", action="store_true", help="Push the current branch after committing. Requires --git.")
    deploy_parser.add_argument("--open-pr", action="store_true", help="Open a pull request with gh after pushing. Requires --git and --push.")
    deploy_parser.add_argument("--merge-pr", action="store_true", help="Merge the pull request after opening it. Requires --open-pr.")
    deploy_parser.add_argument("--delete-branch", action="store_true", help="Delete the remote branch when merging a pull request with --merge-pr.")
    deploy_parser.add_argument("--base", default="main", help="Base branch for pull requests created with --open-pr. Defaults to main.")
    deploy_parser.add_argument("--pr-title", help="Optional pull request title. Defaults to the commit message.")
    deploy_parser.set_defaults(func=deploy_family_repo)

    rollback_parser = subparsers.add_parser("rollback", help="Rollback a previous deployment from a receipt.")
    rollback_parser.add_argument("--receipt", required=True, help="Path to a deployment receipt JSON file.")
    rollback_parser.add_argument("--target", action="append", help="Optional target(s) to roll back. Defaults to all rollbackable targets in the receipt.")
    rollback_parser.add_argument(
        "--allow-command-rollback",
        action="store_true",
        help="Allow execution of command-based rollback steps from the receipt. Use only for trusted receipts.",
    )
    rollback_parser.set_defaults(func=rollback_deployment)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "source", None) is None and not getattr(args, "repo", None):
        args.source = "."
    try:
        return args.func(args)
    except ValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
