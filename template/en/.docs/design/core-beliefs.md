# Core Beliefs

> The **unchanging principles** the agent falls back on for judgment calls.
> Use these to resolve edge cases that the concrete rules (`AGENT.md`) don't answer.

## 1. Simple beats clever
- Three similar lines beat a premature abstraction.
- Don't design for hypothetical future requirements.

## 2. The environment matters more than the code (harness first)
- When the same mistake recurs, don't fix it case by case — add a **rule/check to the environment** that prevents it.
- Inspect the harness (instructions, checks, feedback) before changing the model or approach.

## 3. Feedback loops must be fast and readable
- A verification failure should tell the cause and the fix so the agent can self-correct.
- A check that only returns "pass/fail" delivers half the value.

## 4. Entropy grows if left alone
- Actively clean up code drift, duplication, and dead code (garbage collection).
- But out-of-scope cleanup goes into a separate task.

## 5. Stop and confirm for irreversible actions
- Destructive, externally visible, or hard-to-recover actions need user confirmation before running.
