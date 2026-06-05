#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${WORKFLOW_CHAT_REPO_URL:-https://github.com/hepingan11/Workflow-Chat.git}"
BRANCH="${WORKFLOW_CHAT_BRANCH:-main}"
INSTALL_DIR="${WORKFLOW_CHAT_INSTALL_DIR:-$(pwd)/Workflow-Chat}"

require_command() {
  local name="$1"
  local hint="$2"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing command: $name. $hint" >&2
    exit 1
  fi
}

ask_yes() {
  local prompt="$1"
  local default="$2"
  local suffix="y/N"
  local answer=""

  if [ "${WORKFLOW_CHAT_YES:-}" = "1" ] || [ "${WORKFLOW_CHAT_YES:-}" = "true" ]; then
    return 0
  fi

  if [ "$default" = "true" ]; then
    suffix="Y/n"
  fi

  read -r -p "$prompt ($suffix): " answer
  answer="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')"
  if [ -z "$answer" ]; then
    [ "$default" = "true" ]
    return
  fi

  [ "$answer" = "y" ] || [ "$answer" = "yes" ] || [ "$answer" = "1" ] || [ "$answer" = "true" ]
}

git_output() {
  git "$@" 2>/dev/null || true
}

update_existing_repository() {
  echo "Existing repository found. Checking latest version..."

  local origin_url
  origin_url="$(git_output -C "$INSTALL_DIR" remote get-url origin | tr -d '\r')"
  if [ -n "$origin_url" ] && [ "$origin_url" != "$REPO_URL" ]; then
    echo "Warning: repository origin is different from bootstrap repo." >&2
    echo "Current origin: $origin_url"
    echo "Bootstrap repo: $REPO_URL"
    if ! ask_yes "Continue with the current repository origin" "true"; then
      echo "Stopped before setup."
      exit 0
    fi
  fi

  git -C "$INSTALL_DIR" fetch origin "$BRANCH"

  local current_branch
  current_branch="$(git_output -C "$INSTALL_DIR" rev-parse --abbrev-ref HEAD | tr -d '\r')"
  if [ "$current_branch" != "$BRANCH" ]; then
    echo "Warning: current branch is '$current_branch', target branch is '$BRANCH'." >&2
    if ask_yes "Checkout target branch '$BRANCH'" "true"; then
      git -C "$INSTALL_DIR" checkout "$BRANCH"
    else
      echo "Keeping current branch. Version check will continue on current HEAD."
    fi
  fi

  local local_head remote_head merge_base dirty
  local_head="$(git_output -C "$INSTALL_DIR" rev-parse HEAD | tr -d '\r')"
  remote_head="$(git_output -C "$INSTALL_DIR" rev-parse "origin/$BRANCH" | tr -d '\r')"
  merge_base="$(git_output -C "$INSTALL_DIR" merge-base HEAD "origin/$BRANCH" | tr -d '\r')"
  dirty="$(git_output -C "$INSTALL_DIR" status --porcelain)"

  if [ -z "$local_head" ] || [ -z "$remote_head" ] || [ -z "$merge_base" ]; then
    echo "Warning: could not compare local and remote versions. Setup will continue without updating." >&2
    return
  fi

  if [ "$local_head" = "$remote_head" ]; then
    echo "Current version is already up to date."
    return
  fi

  if [ "$local_head" = "$merge_base" ]; then
    echo "A newer version is available on origin/$BRANCH."
    echo "Local:  $local_head"
    echo "Remote: $remote_head"

    if [ -n "$dirty" ]; then
      echo "Warning: local uncommitted changes were detected. The update uses git pull --ff-only and will not reset files." >&2
      echo "$dirty"
      if ! ask_yes "Try updating anyway" "false"; then
        echo "Skipped update. Setup will continue with the current version."
        return
      fi
    elif ! ask_yes "Update to the latest version before setup" "true"; then
      echo "Skipped update. Setup will continue with the current version."
      return
    fi

    git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
    return
  fi

  if [ "$remote_head" = "$merge_base" ]; then
    echo "Warning: local repository is ahead of origin/$BRANCH. No update is needed." >&2
    return
  fi

  echo "Warning: local and remote branches have diverged. Auto update was skipped to avoid overwriting your work." >&2
  echo "Please resolve with Git manually, then run bootstrap again."
}

echo
echo "Guiwuli Digital Employee bootstrap"
echo "Repo:    $REPO_URL"
echo "Branch:  $BRANCH"
echo "Install: $INSTALL_DIR"
echo

require_command git "Install Git first: https://git-scm.com/downloads"

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "Missing Python. Install Python 3.11+ first: https://www.python.org/downloads/" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Warning: npm not found. Web dependency installation will fail until Node.js is installed." >&2
fi

if [ -d "$INSTALL_DIR" ]; then
  if [ -d "$INSTALL_DIR/.git" ]; then
    update_existing_repository
  else
    echo "Install directory exists but is not a Git repository: $INSTALL_DIR" >&2
    exit 1
  fi
else
  echo "Cloning repository..."
  git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
chmod +x ./setup.sh
./setup.sh
