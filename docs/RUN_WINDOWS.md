# Running Smart Meter PUSH Notifications on Windows

[Русская версия](RUN_WINDOWS_RU.md) · [Project overview](../README.md)

## Before you start

You need:

- Python 3.14;
- the project source files;
- a Telegram bot token;
- SOCKS5 proxy connection settings;
- a server reachable from the meters' network.

Run all commands below in PowerShell from the repository root.

Before updating an existing installation, back up its working
SQLite database and `.env`. Do not replace them with files
from another installation.

## First installation

Create a separate environment and install dependencies:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create `.env` using `.env.example` as a template.
Set the bot token, administrator Telegram ID,
proxy URL, and PUSH server TCP port.

Do not publish `.env` or include it in screenshots
or problem reports.

## Start the bot

In the first terminal, run:

```powershell
.\.venv\Scripts\python.exe app.py
```

Wait for `Bot started`.
The bot initializes the required database tables at startup.

## Start the PUSH server

In a second terminal, from the same project folder, run:

```powershell
.\.venv\Scripts\python.exe push_server.py
```

Wait for `PUSH server started on port ...`.

Keep both terminals open.
Press Ctrl+C in each terminal to stop the processes.

Run only one bot instance per token
and one PUSH server per listening port.

## Verify operation

1. Configure the meter with a reachable server address and
   a TCP port matching `PUSH_SERVER_PORT`.
2. Send `/start` to your Telegram bot.
3. Select a language and connect a meter or group.
4. Send a test PUSH from the meter.
5. Check packet reception in the server terminal
   and notification delivery in Telegram.

A successful manual test confirms delivery of that test packet.
Automatic transmission when a meter event occurs
must be checked separately.

## Combined startup and desktop shortcut

`start_all.bat` opens the server and bot terminals
using the `python` command from its launch environment.

If dependencies are installed in `.venv`, activate it first:

```powershell
.\.venv\Scripts\Activate.ps1
.\start_all.bat
```

If PowerShell blocks activation, use the direct Python commands
from the preceding sections.

`setup_windows.bat` creates a desktop shortcut.
It does not install Python or dependencies.

Launching the shortcut does not guarantee use of `.venv`.
If modules cannot be found, start the components directly
with `.venv\Scripts\python.exe`.

## Updating

1. Stop the server, bot, and group manager.
2. Back up the working SQLite database and `.env`.
3. Update application files while preserving the database and settings.
4. Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

5. Start the bot and wait for initialization.
6. Start the PUSH server.
7. Check the archive, meter subscription, and a new test event.

The repository uses `meter_events.db` beside `database.py`.
If your deployment uses a different name or location,
back up and restore the database actually used by that deployment.

## Delivery troubleshooting

### No new connection appears on the server

Check the meter's destination address and port,
server reachability from the meter network,
and firewall rules.

A missing connection log alone does not identify the cause:
the meter may not have started transmission,
or the connection may not have reached the server.

### A connection appears, but no complete packet is received

Save the connection, timeout, and disconnect messages.
Check whether the meter transmitted data and whether
its transport format is supported.

### A packet is received, but no notification appears

Check whether:

- the serial number was recognized;
- the meter is registered;
- the event bitmask is nonzero;
- an event was recorded for the user;
- the Telegram bot is running;
- the bot terminal contains Telegram or proxy errors.

A packet in the server log does not by itself confirm
notification delivery to Telegram.

### Database table errors

For a first installation, start `app.py` first.
Check that all components use the same working database.

Do not delete an existing database to resolve an error
without backing it up and investigating the cause.

## Requesting help

Include the application version or commit, Python version,
steps to reproduce, and the test event time.

Provide sanitized excerpts from the server and bot terminals
covering the relevant period.

Do not publish the bot token, proxy credentials,
group access keys, working database, or full production logs.