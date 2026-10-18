# Plugin Draft workspaces

New Reader-owned Plugins start at a valid no-op Revision 1. Create one by name:

```sh
news plugin create --reader R "Example"
# {"plugin_id":"P","revision_id":"V"}
news plugin draft create --reader R --plugin P --from-revision V
# D
news plugin draft list --reader R --plugin P
news plugin draft read --reader R --plugin P --draft D
news plugin draft export --reader R --plugin P --draft D --directory ./experiment
```

Replace `R`, `P`, `V`, and `D` with UUIDs. `--from-revision` accepts a Revision id, including
an older Revision of the same Plugin. Multiple Drafts can share a parent. The previous
`plugin create --manifest ... --code ...` interface is replaced by named starter creation
and explicit Draft editing.

An export creates a new directory:

```text
experiment/
  .news-draft.json             Reader/Plugin/Draft ids and expected saved version
  implementation/
    manifest.toml
    main.py
```

Edit files under `implementation/`, then explicitly save:

```sh
news plugin draft save --reader R --plugin P --draft D --directory ./experiment
news plugin draft delete --reader R --plugin P --draft D
```

For now, a workspace holds exactly two files: `implementation/manifest.toml` and
`implementation/main.py`. This is an interim rule until the Plugin design session
([ADR 0026](adr/0026-interim-two-file-plugin-workspaces.md)). Save reads
only those two files and ignores everything else in the folder, such as `.DS_Store`,
`__pycache__/`, editor backups, and other `.py` files. Save replaces the saved Manifest and
code; deleting `main.py` saves an empty code set. Export refuses a Draft whose saved code
has files other than `main.py` (possible only through the API) instead of dropping them.
It preserves unfinished code, invalid TOML, and unpinned dependency declarations. It does
not create a Revision or change current selections or Channel Bindings. Local edits have
no effect until saved. Discard deletes only the saved Draft and leaves exported files alone.

The version marker stays outside the implementation tree. Save checks its identity and
expected version and advances it only after the database commit. If another save wins,
the stale save fails without overwriting contents or advancing its marker. Export to a
new directory, inspect the latest saved contents, and reapply the edits you want to keep.
Existing directories are never overwritten by export. If the database save commits but
the marker cannot be written, the error states the saved version; export again to reconcile.

Workspace files are UTF-8 text; newlines are preserved. A Manifest or `main.py` that is a
symbolic link, a directory, or a special file is rejected, as is a symbolically linked
workspace or `implementation/` directory. A read failure aborts the import before saving
any files. A failed export leaves no partial destination. The API still accepts a map of
relative code paths and rejects unsafe, reserved, or colliding names.

The API uses the same saved-data services. The FastAPI app is `news.api.app:app` and reads
`NEWS_DATABASE_URL`, as the CLI does. Apply migrations with `news db upgrade` first.

| Method | Route | Body / result |
|---|---|---|
| POST | `/readers/R/plugins` | `{"name":"Example"}` → Plugin/Revision ids |
| POST | `/readers/R/plugins/P/drafts` | `{"parent_revision_id":"V"}` → saved Draft |
| GET | `/readers/R/plugins/P/drafts` | Saved Drafts, including Manifest/code/version |
| GET | `/readers/R/plugins/P/drafts/D` | Saved Draft |
| PUT | `/readers/R/plugins/P/drafts/D` | `{"expected_version":1,"manifest":"...","code":{"main.py":"..."}}` → saved Draft |
| DELETE | `/readers/R/plugins/P/drafts/D` | 204 after commit |

Unknown and foreign resources return the same 404. Invalid request fields or filenames
return 422; stale saves return 409 with expected/actual versions. A database transaction
failure returns 503 without a success response. CLI events use its configured log file;
API events use stdout. Logs exclude Manifest/code payloads and database bound values.

Promotion and Revision history/current selection are ticket 04. Restricted execution is
ticket 05; ephemeral Draft Test Runs are tickets 15–16. This ticket exposes saved editing
operations only. Existing database histories retain their ids, contents, numbers, selections,
and Bindings; the new migration leaves unrecorded ancestry empty.
