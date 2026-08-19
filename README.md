# Telegram Push Notification Bot

Python-based Telegram bot for receiving, processing, and delivering real-time push notifications from smart meters.

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
- Extracts meter numbers, timestamps, and event data
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
