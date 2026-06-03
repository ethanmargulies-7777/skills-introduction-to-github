#!/usr/bin/env bash
# smoke.sh — verify the Introduction to GitHub skills repository structure
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

echo "=== Introduction to GitHub Skills Repo Verification ==="

# Verify README exists
[ -f "$REPO_ROOT/README.md" ] && echo "✓ README.md present" || { echo "✗ README.md missing"; exit 1; }

# Verify exercise steps
STEPS_DIR="$REPO_ROOT/.github/steps"
for step in 1-create-a-branch.md 2-commit-a-file.md 3-open-a-pull-request.md 4-merge-your-pull-request.md; do
  [ -f "$STEPS_DIR/$step" ] && echo "✓ Step: $step" || { echo "✗ Missing: $step"; exit 1; }
done

# Verify workflows
WORKFLOWS_DIR="$REPO_ROOT/.github/workflows"
for wf in 0-start-exercise.yml 1-create-a-branch.yml 2-commit-a-file.yml 3-open-a-pull-request.yml 4-merge-your-pull-request.yml; do
  [ -f "$WORKFLOWS_DIR/$wf" ] && echo "✓ Workflow: $wf" || { echo "✗ Missing: $wf"; exit 1; }
done

# Show current exercise branches
echo ""
echo "=== Current branches ==="
git -C "$REPO_ROOT" branch -a

echo ""
echo "=== Exercise links ==="
grep -o 'https://github.com[^)]*issues[^)]*' "$REPO_ROOT/README.md" || true

echo ""
echo "All checks passed. This is a GitHub Skills exercise repository."
echo "No build/run steps required — follow the exercise at the link above."
