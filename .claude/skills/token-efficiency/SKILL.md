---
name: token-efficiency
description: |
  Token conservation and response efficiency mode. Auto-load when user asks to save tokens,
  be concise, reduce length, compress responses, or be efficient with context.
---

# Token Efficiency Mode

When this skill is active, apply all of the following:

## Response Rules

1. **Answer only what was asked.** No preamble, no summary, no "great question."
2. **Default to short.** One sentence if one sentence works. Bullet if list. Table if comparison.
3. **No padding phrases.** Cut: "Certainly!", "Of course!", "To summarize…", "As mentioned above…"
4. **No restating the question.** Jump straight to the answer.
5. **Code over prose.** If the answer is code, show code. Skip the surrounding explanation unless it adds non-obvious value.
6. **No closing offers.** Don't end with "Let me know if you need anything else!"
7. **Abbreviate known context.** If a concept was explained earlier in the session, reference it by name — don't re-explain.
8. **Compress file reads.** Read only the lines needed, not whole files.
9. **One tool call at a time only when order matters.** Parallelize independent tool calls.
10. **Skip confirmations.** If the task is clear and reversible, do it — don't ask "Should I proceed?"

## Prompt Tips for the User

To get the most out of each token:

- **Be specific.** "Fix the null check on line 42" uses fewer tokens than "something seems broken."
- **Reference by name.** "Update the MERIT scoring section in mosaic-context skill" not "update the thing we talked about."
- **Use slash commands.** `/mosaic-context`, `/institutional-trading` load focused context without re-explaining.
- **State format preference upfront.** "One-liner answer", "bullet list only", "show code not explanation."
- **Chain tasks in one message.** "Fix X, then run tests, then commit" = one turn, not three.
- **Avoid open-ended questions.** "What should I do?" is expensive. "Should I use approach A or B?" is cheap.

## When to Override This Skill

Turn off concise mode when:
- Onboarding to a complex new system (depth saves tokens long-term)
- Debugging a subtle bug (full context prevents wrong fixes)
- Drafting something for external use (quality > brevity)
