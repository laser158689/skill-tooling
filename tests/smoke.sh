#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

unset OPENAI_API_KEY
unset ANTHROPIC_API_KEY
unset CODEX_HOME
unset SKILL_TOOLING_CONFIG
unset SKILL_TOOLING_ENV_FILE
unset SKILL_TOOLING_GROK_INSTALL_ROOT
unset SKILL_TOOLING_GROK_BUILD_INSTALL_ROOT
unset SKILL_TOOLING_CLAUDE_INSTALL_ROOT
unset SKILL_TOOLING_CLAUDE_CODE_INSTALL_ROOT
unset SKILL_TOOLING_OPENAI_SKILLS_API_INSTALL_ROOT
unset SKILL_TOOLING_CODEX_INSTALL_ROOT

FAMILY_NAME="customer-support"
FAMILY_DIR="$TMP_DIR/$FAMILY_NAME"
PUBLISH_ROOT="$TMP_DIR/published"
CONFIG_FILE="$REPO_ROOT/publish-config.json"
CODEX_CONFIG_FILE="$TMP_DIR/codex-publish-config.json"
CODEX_DEFAULT_CONFIG_FILE="$TMP_DIR/codex-default-publish-config.json"
HISTORY_DIR="$TMP_DIR/history"
CODEX_HOME_ROOT="$TMP_DIR/codex-home"
CODEX_DEFAULT_HOME="$TMP_DIR/default-home"
CLAUDE_CONFIG_FILE="$TMP_DIR/claude-publish-config.json"
CLAUDE_CONFIG_ROOT="$TMP_DIR/claude-home"

"$REPO_ROOT/scripts/create-family" "$FAMILY_NAME" "Reusable support skills" --path "$TMP_DIR"
"$REPO_ROOT/scripts/validate-family" --source "$FAMILY_DIR"
"$REPO_ROOT/scripts/skill-deploy" --source "$FAMILY_DIR"

cp "$FAMILY_DIR/family.json" "$TMP_DIR/bad-family.json"
python3 - <<EOF
import json
from pathlib import Path
path = Path("$TMP_DIR/bad-family.json")
payload = json.loads(path.read_text())
payload["skill_family"]["name"] = "Bad Name"
path.write_text(json.dumps(payload))
EOF
mkdir -p "$TMP_DIR/bad-family"
cp "$TMP_DIR/bad-family.json" "$TMP_DIR/bad-family/family.json"
cp -R "$FAMILY_DIR/source" "$TMP_DIR/bad-family/source"
if "$REPO_ROOT/scripts/validate-family" --source "$TMP_DIR/bad-family" > /dev/null 2>&1; then
  echo "Expected schema validation failure for invalid skill_family.name"
  exit 1
fi

TMP_CONFIG_FILE="$TMP_DIR/publish-config.json"
cat > "$TMP_CONFIG_FILE" <<EOF
{
  "targets": {
    "grok": { "mode": "copy", "install_root": "$PUBLISH_ROOT/grok" },
    "grok-build": { "mode": "copy", "install_root": "$PUBLISH_ROOT/grok-build" },
    "claude": { "mode": "copy", "install_root": "$PUBLISH_ROOT/claude" },
    "claude-code": { "mode": "copy", "install_root": "$PUBLISH_ROOT/claude-code" },
    "openai-skills-api": { "mode": "copy", "install_root": "$PUBLISH_ROOT/openai-skills-api" },
    "codex": { "mode": "copy", "install_root": "$PUBLISH_ROOT/codex" }
  }
}
EOF

cat > "$CODEX_CONFIG_FILE" <<EOF
{
  "targets": {
    "codex": { "mode": "codex-skills" }
  }
}
EOF

cat > "$CODEX_DEFAULT_CONFIG_FILE" <<EOF
{
  "targets": {
    "codex": { "mode": "codex-skills" }
  }
}
EOF

cat > "$CLAUDE_CONFIG_FILE" <<EOF
{
  "targets": {
    "claude": { "mode": "claude-skills" },
    "claude-code": { "mode": "claude-skills" }
  }
}
EOF

cat > "$TMP_DIR/family.env" <<EOF
CODEX_HOME=$CODEX_HOME_ROOT
EOF

git -C "$FAMILY_DIR" init -q
git -C "$FAMILY_DIR" config user.name "Skill Tooling Test"
git -C "$FAMILY_DIR" config user.email "skill-tooling@example.com"
git -C "$FAMILY_DIR" add .
git -C "$FAMILY_DIR" commit -q -m "Initial family"

"$REPO_ROOT/scripts/skill-deploy" --repo "$FAMILY_DIR" --publish --config "$TMP_CONFIG_FILE" --history-dir "$HISTORY_DIR"
SKILL_TOOLING_ENV_FILE="$TMP_DIR/family.env" "$REPO_ROOT/scripts/skill-deploy" --source "$FAMILY_DIR" --publish --target codex --config "$CODEX_CONFIG_FILE" --history-dir "$TMP_DIR/codex-history"
HOME="$CODEX_DEFAULT_HOME" CODEX_HOME="" SKILL_TOOLING_CODEX_INSTALL_ROOT="" "$REPO_ROOT/scripts/skill-deploy" --source "$FAMILY_DIR" --publish --target codex --config "$CODEX_DEFAULT_CONFIG_FILE" --history-dir "$TMP_DIR/codex-default-history"
CLAUDE_CONFIG_DIR="$CLAUDE_CONFIG_ROOT" "$REPO_ROOT/scripts/skill-deploy" --source "$FAMILY_DIR" --publish --target claude --config "$CLAUDE_CONFIG_FILE" --history-dir "$TMP_DIR/claude-history"
printf '\n<!-- release smoke -->\n' >> "$FAMILY_DIR/source/orchestrator.md"
"$REPO_ROOT/scripts/skill-deploy" --source "$FAMILY_DIR" --target codex --git --branch codex/release-smoke --commit-message "Release family" --history-dir "$TMP_DIR/release-history"

cat > "$TMP_DIR/missing-command-config.json" <<EOF
{
  "targets": {
    "grok": { "mode": "command", "command": ["/definitely/missing/publish-grok-skill-family", "{bundle_dir}", "{family_name}"] }
  }
}
EOF

if "$REPO_ROOT/scripts/skill-deploy" --source "$FAMILY_DIR" --publish --target grok --config "$TMP_DIR/missing-command-config.json" >"$TMP_DIR/missing-command.stdout" 2>"$TMP_DIR/missing-command.stderr"; then
  echo "Expected command publisher failure for missing executable"
  exit 1
fi
grep -q "Publish preflight failed:" "$TMP_DIR/missing-command.stderr"
grep -q "required publish executable not found" "$TMP_DIR/missing-command.stderr"

test -f "$FAMILY_DIR/family.json"
test -f "$FAMILY_DIR/source/orchestrator.md"
test -f "$FAMILY_DIR/overrides/orchestrator/claude.md"
test -f "$REPO_ROOT/pyproject.toml"
test -f "$REPO_ROOT/poetry.lock"
test -f "$REPO_ROOT/examples/.env.example"
test -f "$REPO_ROOT/publish-config.json"
find "$FAMILY_DIR/.skill-tooling/deployments/receipts" -name '*.json' | grep -q .

test -f "$FAMILY_DIR/grok/README.md"
test -f "$FAMILY_DIR/grok/manifest.json"
test -f "$FAMILY_DIR/grok/family.grok"
test -f "$FAMILY_DIR/grok/orchestrator.grok"

test -f "$FAMILY_DIR/claude/README.md"
test -f "$FAMILY_DIR/claude/family.skill"
test -f "$FAMILY_DIR/claude/orchestrator.skill"
grep -q "Claude-specific" "$FAMILY_DIR/claude/orchestrator.skill"

test -f "$FAMILY_DIR/codex/family.prompt"
test -f "$FAMILY_DIR/openai-skills-api/orchestrator.prompt"
test -f "$CODEX_HOME_ROOT/skills/${FAMILY_NAME}--orchestrator/SKILL.md"
grep -q "name: \"${FAMILY_NAME}--orchestrator\"" "$CODEX_HOME_ROOT/skills/${FAMILY_NAME}--orchestrator/SKILL.md"
test -f "$CODEX_DEFAULT_HOME/.agents/skills/${FAMILY_NAME}--orchestrator/SKILL.md"
grep -q "name: \"${FAMILY_NAME}--orchestrator\"" "$CODEX_DEFAULT_HOME/.agents/skills/${FAMILY_NAME}--orchestrator/SKILL.md"
test -f "$CLAUDE_CONFIG_ROOT/skills/${FAMILY_NAME}--orchestrator/SKILL.md"
grep -q "description: Primary orchestrator for the ${FAMILY_NAME} family" "$CLAUDE_CONFIG_ROOT/skills/${FAMILY_NAME}--orchestrator/SKILL.md"

test -f "$PUBLISH_ROOT/grok/$FAMILY_NAME/orchestrator.grok"
test -f "$PUBLISH_ROOT/claude/$FAMILY_NAME/orchestrator.skill"
test -f "$PUBLISH_ROOT/codex/$FAMILY_NAME/family.prompt"
test "$(git -C "$FAMILY_DIR" branch --show-current)" = "codex/release-smoke"
test "$(git -C "$FAMILY_DIR" log -1 --pretty=%s)" = "Release family"

RECEIPT_PATH=$(find "$HISTORY_DIR/receipts" -name '*.json' | head -n 1)
test -n "$RECEIPT_PATH"
"$REPO_ROOT/scripts/rollback-deploy" --receipt "$RECEIPT_PATH"
test ! -e "$PUBLISH_ROOT/grok/$FAMILY_NAME"
test ! -e "$PUBLISH_ROOT/codex/$FAMILY_NAME"

echo "Smoke test passed."
