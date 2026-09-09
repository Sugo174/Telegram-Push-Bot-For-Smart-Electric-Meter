# Telegram Push Notification Bot

Python-based Telegram bot for receiving, processing, and delivering real-time push notifications from smart meters.

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [Compatibility and Limitations](#compatibility-and-limitations)

## Overview

This project provides a notification system for monitoring smart meter events.

The bot receives meter events, processes them through a local SQLite database, and delivers relevant notifications to authorized Telegram users.

The system supports multiple users, access control, event history, and integration with smart meter monitoring infrastructure.

## System Architecture

The system consists of three main components:

### 1. Push Server

A server-side component responsible for receiving and processing push messages from smart meters.

The server:

- Receives push packets from meters
- Parses incoming messages
- Filters irrelevant or invalid packets
- Extracts meter numbers and event data
- Records the server processing time in UTC for each stored event
- Stores processed events in a SQLite database
- Maintains daily rotating push logs

Example of a received push:

```text
[2026-01-20 16:43:43.999]
Meter: 97170045477
Packet: 7ea03a030313f952e6e7000f000000010c07ea011402102c16fffed400020309060000190900ff090b39373137303034353437370600000010a3b37e
```

### 2. Group Manager
A standalone utility for managing meter access groups.
It allows administrators to:
- View existing access groups
- Create new groups
- Generate custom access keys
- Add any number of meters to a group
- Edit existing groups
- Manage meter numbers associated with each group
Group access keys are later used by Telegram bot users to subscribe to push notifications from multiple meters.

### 3. Telegram Bot
The Telegram bot provides the user-facing interface for receiving and managing meter notifications.
The bot operates through a proxy to support deployment in environments where direct access to the Telegram API may be restricted.
The interface is designed around a single-message workflow: when the user navigates between sections, the previous message is replaced instead of creating a growing conversation history.
When a new push notification is received, it is displayed as the active message in the bot interface.

## Key Features

### Push Processing

- Receives push messages from smart meters
- Filters irrelevant and invalid packets
- Extracts meter event information
- Stores received events in a local SQLite database
- Automatically creates daily push logs

### Meter and Group Access

Users can configure push notification sources directly through the Telegram bot:

- Connect a single meter using its meter number
- Connect a group of meters using a group access key
- View information about the connected meter or group
- Receive notifications from all meters included in an authorized group

### Telegram Interface

- Single-message navigation interface
- Previous interface messages are automatically replaced
- Incoming push notifications are displayed directly in the active bot message
- Multilingual interface:
  - Russian
  - English
  - Simplified Chinese

### Push Notifications

Each received notification contains:

- Meter number
- Error/event code
- Human-readable error description
- Event timestamp
- Description in the user's selected language

### Push Archive

Users can manage their received notifications through a personal archive:

- View previously received push notifications
- Display five events per page
- Pagination support
- Unread notification counter
- Mark notifications as read by opening the archive
- Clear the notification archive

### Group Management

The Group Manager provides administrative tools for:

- Creating access groups
- Generating custom access keys
- Adding multiple meters to a group
- Editing existing groups
- Viewing registered groups and their meter numbers

## Technology Stack

- Python
- Telegram Bot API
- SQLite
- aiohttp
- aiosqlite
- aiohttp-socks
- python-dotenv
- SOCKS5 proxy

## How It Works

The system processes meter events through the following pipeline:

```text
Smart Meter
     │
     │ Push message
     ▼
Push Server
     │
     ├── Parse packet
     ├── Filter irrelevant data
     └── Store event
     │
     ▼
SQLite Database
     │
     │ Event + meter information
     ▼
Telegram Bot
     │
     ├── Check user access
     ├── Determine notification language
     └── Deliver notification
     │
     ▼
Telegram User
```

## Installation

### Requirements

- Python 3.10+
- Telegram Bot Token
- SOCKS5 proxy (if required by the deployment environment)

### Setup

1. Clone the repository.

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file based on `.env.example`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_CHAT_ID=your_admin_chat_id
PROXY_URL=your_proxy_url
PUSH_SERVER_PORT=23224
```

`PUSH_SERVER_PORT` defines the TCP port used by the server to receive PUSH messages from smart meters.

The default port is `23224`. You can change this value in the `.env` file if another port is required. No changes to the Python source code are necessary.

4. Start the PUSH server:

```bash
python push_server.py
```

5. Start the Telegram bot:

```bash
python app.py
```

### Group Management

The `group_manager.py` utility can be launched separately when access groups need to be created or modified:

```bash
python group_manager.py
```

## Project Structure

- `app.py` — Entry point for the Telegram bot.
- `database.py` — SQLite database operations and event data management.
- `group_manager.py` — Standalone utility for managing meter access groups.
- `handlers.py` — Telegram bot commands and user interaction handlers.
- `push_server.py` — TCP server for receiving and processing smart meter PUSH messages.
- `telegram_api.py` — Helpers for interacting with the Telegram Bot API.
- `requirements.txt` — Required Python dependencies.
- `.env.example` — Template for environment variables and server settings.
- `.gitignore` — Files and directories excluded from version control.
- `README.md` — Project overview and setup instructions.

## Usage

1. Keep both `push_server.py` and `app.py` running in separate terminals.
2. Configure your smart meter to send PUSH messages to the server's IP address and the port specified by `PUSH_SERVER_PORT`. The server must be reachable from the meter's network.
3. Open your Telegram bot and send `/start`.
4. Select your preferred interface language.
5. Connect a single meter using its meter number, or connect a meter group using an access key created with `group_manager.py`.
6. Receive notifications when the server processes events from your connected meters.
7. Open the push archive to browse received notifications or clear your history.

The PUSH server processes messages only for meters already registered through a single-meter connection or an access group.

## Compatibility and Limitations

- The current PUSH parser expects an 11-digit meter serial number starting with `971` or `976`.
- PUSH messages must match the packet format expected by `push_server.py`. Other meter models or packet formats may require parser changes.
- Messages are processed only for meters registered through a single-meter connection or an access group.
- Packets with a zero event bitmask are ignored.
- Stored event timestamps represent the server processing time in UTC, rather than a timestamp extracted from the meter.
