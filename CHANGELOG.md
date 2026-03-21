# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- **Agent Communication** - Inter-agent messaging system
  - Partner can send messages to employees via sessions_send
  - Task assignment notifications
  - Message status tracking: pending → sent → delivered
  - Retry logic (max 3 attempts)
  - Inbox and conversation history
  - Broadcast messages to multiple agents
- **Pixel Avatar V2** - Three-mode avatar system
  - System-generated: 4 pixel art styles (humanoid, robot, alien, spirit)
  - User upload: Support PNG/JPG/SVG, max 5MB
  - AI-generated: Partner calls skill for generation
  - Avatar editor modal with live preview
  - Status animations (idle/busy/offline/fused)
- **Chart Visualization** - Data visualization for reports
  - Dashboard: 7-day budget usage trend chart
  - Daily report: Budget distribution pie chart by employee
  - Weekly report: 7-day trend line chart (tasks + budget)
  - Dark theme styling with Chart.js
- **PostgreSQL Migration** - Production database support
  - Dual database support (SQLite for dev, PostgreSQL for prod)
  - Environment-based configuration (DB_TYPE, DATABASE_URL)
  - Data migration script from SQLite to PostgreSQL
  - Docker Compose profile for PostgreSQL stack
  - Connection pooling and health checks
  - Complete migration guide
- **Post-Fuse Options** - Actions when budget fuse is triggered
  - 💰 Add Budget - Increase agent's monthly budget
  - ✂️ Split Task - Break into smaller sub-tasks
  - 🔄 Reassign - Move task to another agent
  - ⏸️ Pause - Keep paused for later decision
  - Dashboard UI with fuse alert banner
  - API endpoints: /api/fuse/events/*
- **Share Link System** - JWT-signed temporary access links
  - Support expiration (1h to 7d)
  - Optional password protection
  - Max usage limits
  - Dashboard UI with share modal
  - API endpoints: POST /api/share/generate, GET /api/share/validate
- **Dashboard Login Protection** - API Key authentication for Dashboard and Reports pages
  - Login page with API Key input
  - Automatic Authorization header injection for all API requests
  - Logout functionality
  - Configurable via `API_KEY_AUTH_ENABLED` env var
- Structured logging with structlog (JSON/text formats)
- API rate limiting with slowapi
- Global exception handler
- Complete API reference documentation

### Fixed
- Fixed version number in root API endpoint (0.1.0 → 0.2.0-alpha)

## [0.2.0-alpha] - 2026-03-21

### Added
- **Pixel Office** - CSS Grid-based 8-desk visualization with real-time status
- **Daily/Weekly Reports** - Automatic work summary generation
- **Employee Skills System** - 8 default skills with proficiency tracking
- **Notifications System** - Task/budget/overdue alerts with bell UI
- **Partner Health Monitoring** - Heartbeat detection and online status
- **System Config Panel** - Configurable timeout, token rate, budget threshold
- **SVG Pixel Avatars** - Position-based pixel art avatars

### Changed
- Updated README with v0.2.0 features and API documentation
- Improved task assignment with skill matching

## [0.1.0-alpha] - 2026-03-07

### Added
- Core Service (FastAPI + SQLite)
- Employee/Task/Budget models
- Budget fuse mechanism (80% warning, 100% pause)
- Partner Agent auto-assignment (budget/workload/combined strategies)
- OPC Bridge Skill for Agent integration
- Web Dashboard (dark theme, real-time refresh)
- Docker deployment support
- Basic Web UI for employee/task/budget display

---

## Version History

- `v0.2.0-alpha` - Week 4 Complete Demo (Current)
- `v0.1.0-alpha` - Week 1-3 MVP

## Planned Versions

- `v0.2.1` - Maintenance release (bug fixes, docs)
- `v0.3.0-beta` - PostgreSQL, Pixel Office V2, Token tracking
- `v1.0.0` - Production ready
