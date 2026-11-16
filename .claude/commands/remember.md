---
description: Record a new owner rule or preference in project memory, on a docs branch, pushed
argument-hint: <rule>
---
Rule: $ARGUMENTS

1. `git fetch origin && git checkout -b docs/<short-topic> origin/main`.
2. Append `- [stated] <rule as stated> (<today's date>)` to the bottom of `docs/knowledge/project_memory.md`.
   Prefix it with "standing rule (date):" if it applies to all future work.
3. If it is a standing rule, add it to the matching part of AGENTS.md §4 with `[USER]` and the date.
   If it contradicts an older rule, say so and replace the old wording.
4. Commit, `git push -u origin docs/<short-topic>`, open a PR into main. Show me the lines you added.
