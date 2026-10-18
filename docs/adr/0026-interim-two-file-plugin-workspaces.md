# 0026. Plugin workspaces hold a Manifest and one Python file, for now

Status: Accepted
Date: 2026-10-17
Amends: ADR 0024

## Context

ADR 0024 makes CLI editing an explicit export/edit/save of local files, and ticket 03
implemented save as "replace the Draft with every file in the exported folder". On a
real machine that folder also collects files nobody meant as Plugin code. Finder writes
binary `.DS_Store` files, running the code locally writes `__pycache__/*.pyc`, and editors
leave backups and swap files. The binary files made every save fail, and the text ones
would have been saved as Plugin code.

The fuller question, what files a Plugin consists of, needs a deeper design session.
Until then the project assumes a Plugin is two files: a Manifest holding metadata and
configuration, and one Python file holding the executable code.

## Decision

- An exported CLI workspace holds exactly `implementation/manifest.toml` and
  `implementation/main.py`, plus the version marker outside `implementation/`.
- Save reads only those two files and ignores everything else in the folder. Deleting
  `main.py` saves an empty code set, so removal is still an explicit edit.
- The two files must be regular files. A symbolic link, directory, or special file in
  either place is rejected, as is a linked workspace or `implementation/` directory.
- Export refuses a Draft whose saved code has any file other than `main.py`, with an
  actionable error, instead of silently dropping files on the next save.
- This rule applies to the CLI workspace only. Storage, the service layer, and the API
  still accept a map of relative code paths with the existing path-safety checks.
- This is interim. The Plugin design session replaces or confirms it with a superseding ADR.

## Alternatives rejected

- **Ignore a list of known clutter patterns** (`.DS_Store`, `__pycache__/`, `*~`, `*.swp`).
  The list never ends, and anything it misses either breaks saves or becomes Plugin code.
- **Reject clutter with an error.** It keeps the "complete file set" promise, but forces
  cleanup before every save on a normal macOS setup.
- **A Reader-maintained ignore file.** It adds a configuration surface before the file
  model itself is decided.
- **Enforce two files in the service layer and API now.** It rewrites storage-level
  validation and its tests, which the design session may undo.

## Consequences

- CLI saves no longer fail because of operating-system or editor files in the workspace.
- Additional `.py` files beside `main.py` are not saved. Readers wanting more files must
  wait for the design session or save through the API.
- The CLI and the API accept different file shapes until the design session. Export's
  refusal is the guard where they meet.
- AC-63's "including removals" now means removing `main.py` (spec D-70).
