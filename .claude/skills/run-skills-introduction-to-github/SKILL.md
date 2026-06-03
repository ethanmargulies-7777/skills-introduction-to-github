---
name: run-skills-introduction-to-github
description: Verify, run, or check the Introduction to GitHub skills exercise repository. Use when asked to run, start, verify, or check the project.
---

This is a GitHub Skills tutorial repository ("Introduction to GitHub"). It has no application to build or serve — it is a structured exercise teaching GitHub fundamentals (branches, commits, pull requests, merges) driven by GitHub Actions workflows. The "run" for this project is verifying the repository structure is intact and the exercise workflows are in place.

## Prerequisites

No additional packages required — only `git` and `bash` (standard).

## Build

No build step. There are no source files to compile or dependencies to install.

## Run (agent path)

```bash
bash .claude/skills/run-skills-introduction-to-github/smoke.sh
```

This verifies all exercise step files and GitHub Actions workflows are present, lists branches, and prints the exercise URL.

## Run (human path)

Open the exercise link from README.md in a browser and follow the steps:
- https://github.com/ethanmargulies-7777/skills-introduction-to-github/issues/1

The exercise walks through: creating a branch → committing a file → opening a pull request → merging it. Each step is validated automatically by GitHub Actions workflows in `.github/workflows/`.

## Gotchas

- This repo has no `package.json`, no language runtime, and no server. It is purely a Git/GitHub workflow exercise.
- The GitHub Actions workflows require the repo to be hosted on GitHub and triggered via GitHub events — they cannot be run locally.
- The exercise expects a branch named `my-first-branch` for step 1 validation.

## Troubleshooting

No errors were encountered during verification in this session.
