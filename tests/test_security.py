#!/usr/bin/env python3
"""Security regression tests for public-repository and deployment boundaries."""

from __future__ import annotations

import importlib.util
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "skill_tooling.py"
SPEC = importlib.util.spec_from_file_location("skill_tooling_security_test_target", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import setup invariant
    raise RuntimeError(f"Could not import {MODULE_PATH}")
TOOLING = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOLING
SPEC.loader.exec_module(TOOLING)


class SecurityBoundaryTests(unittest.TestCase):
    def test_api_urls_require_credential_free_https(self) -> None:
        invalid_urls = [
            "http://api.openai.com/v1",
            "file:///tmp/response.json",
            "https://user:token@example.com/v1",
            "https://example.com/v1?redirect=elsewhere",
            "https://example.com/v1#fragment",
        ]
        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaises(TOOLING.ValidationError):
                TOOLING.validate_https_url(url)

    def test_primary_openai_key_cannot_be_forwarded_to_custom_host(self) -> None:
        config = TOOLING.PublisherConfig(
            mode="openai-skills",
            base_url="https://proxy.example.test/v1",
            api_key_env="OPENAI_API_KEY",
        )
        with self.assertRaisesRegex(TOOLING.ValidationError, "dedicated SKILL_TOOLING_CUSTOM_API_KEY"):
            TOOLING.resolve_openai_api_settings(config)

    def test_custom_host_uses_dedicated_key_name(self) -> None:
        config = TOOLING.PublisherConfig(
            mode="openai-skills",
            base_url="https://proxy.example.test/v1",
        )
        base_url, env_name = TOOLING.resolve_openai_api_settings(config)
        self.assertEqual(base_url, "https://proxy.example.test/v1")
        self.assertEqual(env_name, "SKILL_TOOLING_CUSTOM_API_KEY")

    def test_git_urls_reject_insecure_or_embedded_credentials(self) -> None:
        invalid_repositories = [
            "http://example.com/repo.git",
            "https://token@example.com/repo.git",
            "https://example.com/repo.git?token=value",
            "owner/repo\nmalicious",
        ]
        for repository in invalid_repositories:
            with self.subTest(repository=repository), self.assertRaises(TOOLING.ValidationError):
                TOOLING.repo_to_clone_url(repository)

    def test_private_json_is_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "state" / "receipt.json"
            TOOLING.write_private_json(output, {"safe": True})
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)

    def test_rollback_destination_rejects_wrong_basename_and_root_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory, self.assertRaises(TOOLING.ValidationError):
            TOOLING.validate_rollback_destination(
                Path(temporary_directory) / "not-the-family",
                "expected-family",
                "test",
            )
        with self.assertRaises(TOOLING.ValidationError):
            TOOLING.validate_rollback_destination(Path("/expected-family"), "expected-family", "test")

    def test_external_text_redacts_secrets_and_control_characters(self) -> None:
        sanitized = TOOLING.sanitize_external_text("error token-value\x1b[31m", ["token-value"])
        self.assertNotIn("token-value", sanitized)
        self.assertNotIn("\x1b", sanitized)

    def test_console_output_masks_local_account_names(self) -> None:
        macos_path = "/" + "Users/private-user/project"
        linux_path = "/" + "home/private-user/project"
        windows_path = "C:\\" + r"Users\private-user\project"
        self.assertEqual(TOOLING.redact_local_paths(macos_path), "~/project")
        self.assertEqual(TOOLING.redact_local_paths(linux_path), "~/project")
        self.assertEqual(TOOLING.redact_local_paths(windows_path), r"~\project")

    def test_preflight_does_not_log_credential_variable_name(self) -> None:
        family = TOOLING.Family(
            name="test-family",
            description="Test family",
            version="0.1.0",
            path=Path("."),
            targets=["openai-skills-api"],
        )
        config = TOOLING.PublisherConfig(mode="openai-skills")
        with mock.patch.dict(TOOLING.os.environ, {"OPENAI_API_KEY": "test-only-secret"}):
            mode, detail = TOOLING.preflight_publish_target(
                "openai-skills-api",
                family,
                {},
                {"openai-skills-api": config},
            )
        self.assertEqual(mode, "openai-skills")
        self.assertEqual(detail, "api | credentials present")
        self.assertNotIn("OPENAI_API_KEY", detail)


if __name__ == "__main__":
    unittest.main()
