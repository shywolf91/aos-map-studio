---
model: haiku
description: Pull main and report branches, PRs and anything not pushed
---
Read-only report; change no files.

1. `git fetch --prune origin`. In the main checkout also `git checkout main && git pull`
   (in a worktree, only fetch: main is held by the main checkout).
2. List local and remote `map/*`, `tooling/*` and `docs/*` branches with ahead/behind counts against
   `origin/main` and against their own upstream.
3. `gh pr list --state open`, plus PRs merged in the last 7 days.
4. Flag: commits not pushed, branches without an upstream, branches without a PR, uncommitted or
   untracked files (ignoring git-ignored paths), and anything waiting in `_updates/`.
5. Summarise in one table and suggest the next action per branch.
