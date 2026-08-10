# Persistent Agent Memory Specification

## Purpose

Persistent agent memory eliminates repeated repository discovery, reduces token spend, and improves cross-session consistency. It is a reviewed repository artifact, not an ungoverned transcript or an agent-owned private database.

## Stored information

The memory store may contain only stable repository context:

- the module map, ownership boundaries, and canonical descriptor patterns;
- contract locations and compatibility rules;
- required gates and the meaning of each failure;
- the release and deployment process;
- agent-role permissions; and
- rolling, bounded task summaries for each agent role.

Repository facts live in `repository-facts.md`. Completed-task summaries use `task-log-template.md` and should record decisions and follow-ups without copying transient logs.

## Prohibited information

Memory must never contain secrets, tokens, credentials, personal data, session identifiers, provider payloads, private keys, or any value read from `.env` or another secret-bearing configuration source. If a useful fact cannot be written without such material, omit the fact and cite only the public repository boundary that governs it.

## Read and write rules

- Every repository agent role may read `agents/memory/`.
- Only the `engineering-manager` role may propose a memory write, and only after the associated task is complete.
- Every write must use a normal branch and pull request, pass the repository gates, and receive review like any other change.
- No agent may approve its own memory edit. The writer and approving reviewer must be distinct roles or actors.
- Memory never grants merge, deployment, provider, secret, production, or policy authority beyond the repository rules that it summarizes.

## Entry format and provenance

Every stable fact is a `## Fact:` section with exactly one `Source path` and one 40-character `Source commit`. The source path is repository-relative and must exist. The source commit identifies the exact revision that was read when the fact was written.

Task summaries must remain concise and use the provided template. A summary may link to issues, pull requests, commits, and repository files, but it must not become a substitute for canonical requirements, contracts, or release evidence.

## Staleness policy

An entry is stale when either condition is true:

1. its source commit is more than 30 days old; or
2. its cited source path changed after the source commit.

Stale entries must be flagged and revalidated against protected main before an agent relies on them. Revalidation updates the fact through a new pull request; it does not silently rewrite provenance. If a stale fact conflicts with current repository source, current source wins.
