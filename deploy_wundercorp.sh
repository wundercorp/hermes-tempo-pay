#!/usr/bin/env bash
set -Eeuo pipefail

GITHUB_ORG="${GITHUB_ORG:-wundercorp}"
GITHUB_REPO="${GITHUB_REPO:-hermes-tempo-pay}"
GITHUB_VISIBILITY="${GITHUB_VISIBILITY:-public}"
GITHUB_DESCRIPTION="${GITHUB_DESCRIPTION:-Hermes plugin for Tempo Wallet onboarding and payment-aware HTTP 402/MPP requests.}"
TARGET_REPOSITORY="${GITHUB_ORG}/${GITHUB_REPO}"
SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIRECTORY="$SCRIPT_DIRECTORY"

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

require_command git
require_command gh

[[ -f "$SOURCE_DIRECTORY/plugin.yaml" ]] || fail "plugin.yaml not found next to deploy_wundercorp.sh"
[[ -f "$SOURCE_DIRECTORY/README.md" ]] || fail "README.md not found next to deploy_wundercorp.sh"

case "$GITHUB_VISIBILITY" in
  public|private|internal) ;;
  *) fail "GITHUB_VISIBILITY must be public, private, or internal" ;;
esac

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  fail "GitHub CLI is not authenticated. Run: gh auth login"
fi

secret_match="$(
  find "$SOURCE_DIRECTORY" -type f \
    \( -name '.env' -o -name '.env.*' -o -name '*.pem' -o -name '*.key' -o -name 'id_rsa' -o -name 'id_ed25519' -o -name 'credentials.json' \) \
    -not -path '*/.git/*' -print -quit
)"
if [[ -n "$secret_match" ]]; then
  fail "refusing to publish possible secret file: $secret_match"
fi

find "$SOURCE_DIRECTORY" -type d \( -name '__pycache__' -o -name '.pytest_cache' \) -prune -exec rm -rf {} + 2>/dev/null || true
find "$SOURCE_DIRECTORY" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

if [[ ! -d "$SOURCE_DIRECTORY/.git" ]]; then
  if git -C "$SOURCE_DIRECTORY" init -b main >/dev/null 2>&1; then
    :
  else
    git -C "$SOURCE_DIRECTORY" init >/dev/null
    git -C "$SOURCE_DIRECTORY" branch -M main
  fi
else
  git -C "$SOURCE_DIRECTORY" branch -M main
fi

if [[ -z "$(git -C "$SOURCE_DIRECTORY" config --get user.name || true)" ]]; then
  github_login="$(gh api user --jq '.login')"
  git -C "$SOURCE_DIRECTORY" config user.name "$github_login"
fi

if [[ -z "$(git -C "$SOURCE_DIRECTORY" config --get user.email || true)" ]]; then
  github_login="$(gh api user --jq '.login')"
  github_id="$(gh api user --jq '.id')"
  git -C "$SOURCE_DIRECTORY" config user.email "${github_id}+${github_login}@users.noreply.github.com"
fi

git -C "$SOURCE_DIRECTORY" add -A

if ! git -C "$SOURCE_DIRECTORY" rev-parse --verify HEAD >/dev/null 2>&1; then
  git -C "$SOURCE_DIRECTORY" commit -m "Initial release: Hermes Tempo Pay"
elif ! git -C "$SOURCE_DIRECTORY" diff --cached --quiet; then
  git -C "$SOURCE_DIRECTORY" commit -m "Publish Hermes Tempo Pay"
fi

if gh repo view "$TARGET_REPOSITORY" >/dev/null 2>&1; then
  printf 'GitHub repository already exists: https://github.com/%s\n' "$TARGET_REPOSITORY"
else
  visibility_flag="--${GITHUB_VISIBILITY}"
  gh repo create "$TARGET_REPOSITORY" \
    "$visibility_flag" \
    --description "$GITHUB_DESCRIPTION"
fi

TARGET_HTTPS_URL="https://github.com/${TARGET_REPOSITORY}.git"
TARGET_SSH_URL="git@github.com:${TARGET_REPOSITORY}.git"
PUBLISH_REMOTE="origin"

if git -C "$SOURCE_DIRECTORY" remote get-url origin >/dev/null 2>&1; then
  current_origin="$(git -C "$SOURCE_DIRECTORY" remote get-url origin)"
  if [[ "$current_origin" != "$TARGET_HTTPS_URL" && "$current_origin" != "$TARGET_SSH_URL" ]]; then
    PUBLISH_REMOTE="wundercorp"
    if git -C "$SOURCE_DIRECTORY" remote get-url "$PUBLISH_REMOTE" >/dev/null 2>&1; then
      git -C "$SOURCE_DIRECTORY" remote set-url "$PUBLISH_REMOTE" "$TARGET_HTTPS_URL"
    else
      git -C "$SOURCE_DIRECTORY" remote add "$PUBLISH_REMOTE" "$TARGET_HTTPS_URL"
    fi
  fi
else
  git -C "$SOURCE_DIRECTORY" remote add origin "$TARGET_HTTPS_URL"
fi

git -C "$SOURCE_DIRECTORY" push -u "$PUBLISH_REMOTE" main

gh repo edit "$TARGET_REPOSITORY" \
  --enable-issues=true \
  --enable-wiki=false >/dev/null

printf '\nPublished successfully.\n'
printf 'Repository: https://github.com/%s\n' "$TARGET_REPOSITORY"
printf 'Install:    hermes plugins install %s --enable\n' "$TARGET_REPOSITORY"
printf 'Onboard:    hermes tempo setup --install\n'
