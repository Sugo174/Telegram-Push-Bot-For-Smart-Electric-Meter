# Changelog

All notable changes to this project will be documented in this file.

The project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/Sugo174/Telegram-Push-Bot-For-Smart-Electric-Meter/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Sugo174/Telegram-Push-Bot-For-Smart-Electric-Meter/releases/tag/v1.0.0
