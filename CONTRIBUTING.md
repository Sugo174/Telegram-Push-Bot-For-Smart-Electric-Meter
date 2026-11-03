# Contributing

## Reporting a problem

Check the [Windows guide](docs/RUN_WINDOWS.md)
or [Russian Windows guide](docs/RUN_WINDOWS_RU.md) first.

Include:

- the application version or commit;
- the Python version and operating system;
- steps to reproduce;
- expected and actual behaviour;
- the test event time;
- sanitized server and bot error messages.

Never attach `.env`, working databases, bot tokens,
proxy credentials, group keys, or full production logs.

For security issues, follow [SECURITY.md](SECURITY.md).

## Development setup

Use Python 3.14 and a separate virtual environment.
Follow the setup instructions in [docs/RUN_WINDOWS.md](docs/RUN_WINDOWS.md).

Use a separate test bot and test database when running
integration checks. Do not run a development bot against
the production token while the production bot is active.

## Code changes

- Keep changes focused on one problem or feature.
- Preserve handling of fragmented and consecutive TCP packets.
- Validate packet contents before accessing parsed fields.
- Preserve notification delivery checks and retry behaviour.
- Document database schema changes and the update procedure.
- Update Russian, English, and Chinese interface messages when applicable.
- Update documentation when configuration or behaviour changes.
- Use synthetic or sanitized data in tests and examples.

## Validation

Run automated tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests
```

For communication changes, describe the integration checks performed:
packet reception, event storage, notification delivery,
and repeated events where applicable.

Automated tests do not by themselves verify meter network access,
Telegram delivery, or automatic event transmission by the meter.

## Commits and pull requests

Use clear English commit messages.

Explain the problem, the resulting behaviour,
and how the change was checked.
Mention database migration or deployment requirements.

Do not commit local configuration, databases, backups,
logs, Python environments, or release archives.