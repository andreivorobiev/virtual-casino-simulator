# Agent coordination channel

An asynchronous, conflict-free status channel between the two automation agents that work this
repository in parallel: **Claude** (composes pull requests, never merges) and **Codex** (shared-
integration owner, independent reviewer, sole merge executor). The human owner routes decisions
between them and remains the fastest link; this channel is the durable, git-mediated record so a
coordination pass does not depend on chat history.

There is no shared filesystem and no real-time link between the agents. The only shared substrate
is this git repository. These files are therefore **asynchronous**: an entry is only visible to the
other agent after it is committed, pushed, and the reader has pulled the branch it lives on. Until a
change here reaches `main`, the other agent sees it only if pointed at the branch.

## Files and ownership

Ownership is partitioned so the two agents never edit the same file, which means these files never
produce a merge conflict.

| File | Writer | Reader | Purpose |
|---|---|---|---|
| `claude.md` | Claude only | Codex | Claude's current status: open PRs, active work, file claims, questions, blockers. |
| `codex.md` | Codex only | Claude | Codex's current status: merge queue, ID renames, answers, file claims, decisions. |
| `log.jsonl` | Both (append-only) | Both | Timestamped shared history. Append one line; never edit or reorder existing lines. |

## Rules

1. **Never edit the other agent's status file.** Write only your own (`claude.md` for Claude,
   `codex.md` for Codex). This is what keeps the channel conflict-free.
2. **`log.jsonl` is append-only.** Add new lines at the end. Never rewrite or delete a prior line.
   Because appends do not overlap, conflicts here resolve by keeping both sides' lines.
3. **Read the other agent's file at the start of every coordination pass**, before changing
   repository or GitHub state.
4. **Keep it factual and bounded.** PR numbers, branch names, requirement IDs, file claims, and
   one-line notes. No secrets, credentials, tokens, IP addresses, or personal data — this file is
   public. Detailed rationale belongs in the relevant PR or issue.
5. **GitHub remains the primary channel.** Pull-request bodies, issue comments, and commit messages
   are still where proposals and reviews live. This channel is a lightweight status overlay, not a
   replacement for them.

## `log.jsonl` line shape

```json
{"ts": "2026-07-24T00:00:00Z", "agent": "claude", "kind": "status|claim|question|answer|merge|handoff", "ref": "#381 or branch or REQ-ID", "note": "one bounded line"}
```

`ts` is an ISO-8601 UTC timestamp; `agent` is `claude` or `codex`; `kind` categorizes the entry;
`ref` points at the PR, issue, branch, or requirement it concerns; `note` is a single short line.
