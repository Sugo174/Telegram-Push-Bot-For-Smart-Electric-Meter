# Changelog

All notable changes to this project will be documented in this file.

The project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.2] - 2026-09-16

### Added

- Added a custom application icon for Windows shortcuts.
- Added `setup_windows.bat` to create a desktop shortcut automatically.
- Added a PowerShell shortcut setup script that works from any extracted project folder.
- Added Windows desktop shortcut instructions to the README.

## [1.0.1] - 2026-09-15

### Changed

- Pinned tested Python dependency versions for reproducible installation.
- Expanded installation and environment configuration instructions.
- Documented proxy and TLS limitations of the current release.
- Improved README structure, screenshots, demo links, and project metadata.

## [1.0.0] - 2026-09-10

### Added

- TCP server for receiving PUSH messages from compatible smart meters.
- Smart meter packet parsing and event bitmask decoding.
- Telegram notifications with human-readable event descriptions.
- Support for individual meters and meter access groups.
- SQLite storage for users, groups, settings, and notification history.
- Paginated PUSH notification archive with unread event tracking.
- Single-message Telegram interface.
- Russian, English, and Simplified Chinese interface languages.
- Standalone utility for creating and managing meter groups.
- Configurable PUSH server port through `PUSH_SERVER_PORT`.
- SOCKS5 proxy support for Telegram API connections.
- Example environment configuration.
- Demo video and interface screenshots.
- MIT License.

[Unreleased]: https://github.com/Sugo174/Telegram-Push-Bot-For-Smart-Electric-Meter/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/Sugo174/Telegram-Push-Bot-For-Smart-Electric-Meter/compare/v.1.0.1...v1.0.2
[1.0.1]: https://github.com/Sugo174/Telegram-Push-Bot-For-Smart-Electric-Meter/releases/tag/v.1.0.1
[1.0.0]: https://github.com/Sugo174/Telegram-Push-Bot-For-Smart-Electric-Meter/releases/tag/v1.0.0