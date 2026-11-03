# Security policy

## Reporting a vulnerability

Do not disclose working credentials or vulnerability details
in a public issue.

Contact the maintainer through an available private channel.
Provide the affected version or commit, reproduction conditions,
and potential impact using sanitized examples.

If no private channel is available, open an issue requesting
one without publishing sensitive details.

## Secrets and operational data

Do not commit or publicly share:

- `.env`;
- Telegram bot tokens;
- proxy credentials;
- group access keys;
- working SQLite databases or backups;
- customer information and confidential meter identifiers;
- full production logs or packet captures.

Use `.env.example` as a configuration template.
It must not contain working secrets.

Restrict access to configuration, databases, logs, and backups.

## Current connection limitations

The current Telegram connection configuration requires a SOCKS5 proxy
and disables TLS certificate verification.

This reduces protection against interception and server impersonation.
Use only trusted infrastructure and assess this limitation
before deployment.

Meter identity extracted from a packet is not, by itself,
proof of sender authenticity.
Do not treat a parsed serial number or event as an authenticated
device statement.

## Network exposure

The PUSH server listens for incoming TCP connections.
Limit access through network and firewall rules
to the intended deployment wherever possible.

Do not expose the SQLite database, configuration files,
or administrative group-management tools as public services.

## Incident response

If a bot token or proxy credential is exposed,
replace it with the issuing service and update `.env`.

If a group access key is exposed, replace the key
and review the affected group's subscriptions.

Removing a secret from the latest Git commit does not remove it
from earlier history. Rotate exposed secrets before considering
repository cleanup.

## Updates and backups

Back up the working database and configuration before updating.
Stop all processes that use the database before making a simple
file-copy backup.

Keep backups outside the public repository
and limit access to authorized administrators.