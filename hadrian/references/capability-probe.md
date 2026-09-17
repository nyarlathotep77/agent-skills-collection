# Capability Probe

Run once per goal (Phase 1). Record results in the `.hadrian/state.md` header. Adapt, don't fail: every missing capability has a degraded mode.

| Capability | What to check | Full mode | Degraded mode |
|---|---|---|---|
| Independent verifier | Is a `hadrian-verifier` (or equivalent read-only reviewer) subagent available? | Review Gate runs in a separate context with fresh eyes | In-process adversarial pass: re-read the diff clause by clause, actively try to falsify each PASS, run the weakening check yourself |
| Loop engine | Does the harness auto-continue after idle? | Let the harness drive cycles | Self-prompted: at the end of each cycle explicitly issue "Cycle N+1 — continue per contract" as your own next action; stop only on a Phase 3 condition |
| Contract freeze | Is the hadrian-guard hook/plugin active (PreToolUse / tool.execute.before)? | Edits to `.hadrian/contract.md` are hard-blocked | Prompt-enforced: treat Hard Rule 1 as absolute; additionally verify contract integrity each cycle (`git diff -- .hadrian/contract.md` must be empty when in a repo) |
| State persistence | File tools available (true in all supported harnesses) | Append to `.hadrian/state.md` every cycle | n/a — if file writes are impossible, Hadrian cannot run; stop and report |

## Notes
- Probe cheaply: check for the subagent by name in your tool list; assume loop-engine = self-prompted unless you know the harness auto-continues.
- A degraded mode is recorded, not hidden — it appears in every completion/escalation report so the human knows which guarantees were active.
