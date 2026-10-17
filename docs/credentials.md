# Encrypted credentials

Apply migrations with `uv run news db upgrade` before setting up credentials.
The service stores one encrypted Data Key per Reader. Secrets and LLM Provider credentials
are encrypted with that Data Key; the deploy-time Master Key wraps the Data Keys (ADR 0009).

For initial local setup, run `uv run news key generate`. It prints one base64-encoded
Master Key to stdout, without saving it or changing the environment. Save it outside the
database and supply it to later CLI and server processes using exactly one of:

- `NEWS_MASTER_KEY`: the generated base64 text.
- `NEWS_MASTER_KEY_FILE`: a file containing that text, for example a mounted Docker secret.

Generation refuses when a key source is configured or encrypted Data Keys already exist.
It is an explicit setup command, not automatic generation on every CLI invocation.
An absent, malformed or incorrect key fails; it never replaces an existing Data Key.
An unreadable key file fails without falling back to another key source.

Create a Reader with `uv run news reader create Ada`, then use its printed id:

```sh
uv run news secret set --reader <reader-id> FEED_TOKEN
uv run news provider add --reader <reader-id> --url https://example.test/v1 Local
```

Both commands prompt for the credential with input hidden and ask for confirmation.
They print the record id only after the transaction commits. Reusing a name updates that
Reader's record, retaining the Reader's Data Key. Credential values are not accepted as
command arguments. There is no CLI command to print decrypted credentials.

The CLI writes JSON logs to `--log-file` / `NEWS_CLI_LOG_FILE`; the server logs to stdout.
Key-source failures log `keys.source_failed` with a fixed reason. Decryption failures log
`credentials.decrypt_failed` with the Reader id. A missing or inaccessible Secret logs
`credentials.secret_not_found`. These events contain no key or credential material.

Plugin Secret delivery and Provider calls through the Gateway are implemented by later
tickets. Master Key rotation and KMS/Vault adapters are out of scope here; the service
accepts a callable key source so these can be added without changing credential storage.
