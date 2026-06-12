# Architecture Boundaries

> The **invariant structural rules** that keep the agent from causing code drift.
> These are enforced mechanically by `.scripts/check-boundaries.sh` — not just described.

## Dependency direction (one-way)
Dependencies flow in one direction. Reverse imports are forbidden and blocked by the linter.

```
{{FILL:dev.architecture_layers}}
(Left does not know right. Depend only in the arrow's direction.)
```

- The leftmost layer imports nothing (pure types / domain models).
- The rightmost layer may use all layers below it, but no lower layer may import it.
- On violation: build fails + the violating path is printed in an agent-readable form.

> If `{{FILL:dev.architecture_layers}}` is empty, this check is skipped (avoids over-constraining).
> Projects without layers can leave the block above empty. To introduce boundaries, list them here as `left -> right`.

## Boundary rules
- Layers communicate only via interfaces/ports. Don't reach across concrete implementations.
- No circular dependencies.
- Isolate external I/O (DB, network, files) in the repository/runtime layers.

## Mechanical enforcement
- Rules left as prose get broken. Enforce with **automated checks + clear error messages**.
- Location: `.scripts/check-boundaries.sh` (part of the verify pipeline).
- Errors state what/where/why was violated and how to fix it, all at once.
