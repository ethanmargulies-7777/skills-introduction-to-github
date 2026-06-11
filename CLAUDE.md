# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A GitHub Skills exercise repository — a structured tutorial teaching GitHub basics (branches, commits, PRs, merges) via GitHub Actions workflows. There is no application to build or run.

## Structure

- `.github/workflows/` — 5 GitHub Actions workflows that drive the exercise steps; they trigger on branch events and PR activity
- `.github/steps/` — markdown instructions shown to the user at each step
- `.claude/skills/` — Claude Code skills added for the intern's Mosaic Platforms finance internship

## Active Skills

| Skill | Trigger |
|---|---|
| `/mosaic-context` | Mosaic Platforms company context, MERIT system, John Cosenza |
| `/institutional-trading` | Market microstructure, order flow, execution, regulations |
| `/mosaic-analyst` | Data analytics, TCA, Python/kdb+ tooling, research for the internship role |
| `/mosaic-visual-design` | Marketing design system — McCandless method × Mosaic brand, MERIT visuals, pitch assets |
| `/token-efficiency` | Concise response mode |
| `/run-skills-introduction-to-github` | Verify exercise repo structure via smoke script |

## Development Branch

Active branch: `claude/intelligent-keller-mx90w`

Push all changes here: `git push -u origin claude/intelligent-keller-mx90w`
