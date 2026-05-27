# Tech Debt Tracker

> A living doc. When the agent finds code drift, duplication, or dead code, it records it here,
> and the entropy-management routine references it when generating cleanup PRs.

## Format
Each item: `location` — `problem` — `proposed action` — `priority(high/med/low)`

## Open items
- (e.g.) `src/legacy/auth.py` — old auth middleware, duplicates the new path — remove and consolidate — med

## Resolved (recent)
- (move completed items here, clear periodically)
