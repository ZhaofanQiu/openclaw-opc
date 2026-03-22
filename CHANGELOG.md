# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Planned
- Memory hygiene system for automatic memory cleanup
- Advanced analytics dashboard
- Multi-company support

## [0.4.0-alpha] - 2026-03-22

### Added

#### Sub-task System (P0)
- **Complex task splitting** - Break down large tasks into manageable sub-tasks
- **SubTask model** with dependency support, sequence order, and critical path marking
- **SubTaskService** for complete sub-task lifecycle management
  - `create_sub_task()` - Create individual sub-tasks
  - `split_task()` - Split parent task into multiple sub-tasks
  - `assign_sub_task()` - Assign to agents with dependency checking
  - `update_sub_task_status()` - Status updates with parent progress sync
  - `get_next_executable_sub_task()` - Get next available sub-task
  - `get_sub_task_stats()` - Progress statistics
- **API endpoints** (`/api/sub-tasks`)
  - Full CRUD operations for sub-tasks
  - Task splitting endpoint
  - Progress tracking and statistics
- **Dependency management** - Automatic unblocking when dependencies complete
- **Parent task sync** - Auto-update parent progress when sub-tasks complete

#### Task Dependencies (P0)
- **Workflow automation** - Upstream tasks trigger downstream tasks
- **TaskDependency model** with trigger conditions and delay support
- **TaskDependencyService**
  - `create_dependency()` - Define task relationships
  - `check_and_trigger_dependencies()` - Auto-trigger on task completion
  - `get_dependency_chain()` - Full workflow visualization
  - `get_workflow_status()` - Workflow progress tracking
- **Trigger conditions** - completed/failed/any
- **Delay support** - Schedule downstream tasks with delay
- **Integration** - Automatic triggering when tasks complete

#### Approval Workflow (P1)
- **Budget approval system** - High-budget tasks require Partner approval
- **ApprovalRequest model** with expiration support
- **ApprovalService**
  - `requires_approval()` - Check if task needs approval
  - `create_approval_request()` - Submit approval request
  - `approve_request()` / `reject_request()` - Partner decisions
  - `get_pending_for_partner()` - Partner's approval queue
  - `cleanup_expired_requests()` - Auto-cleanup expired requests
- **Configurable threshold** - Default 1000 OC coins
- **24-hour expiration** - Auto-cancel expired requests
- **Integration** - Task assignment blocked until approved

#### Skill Growth System (P1)
- **Agent skill progression** - Earn experience from task completion
- **AgentSkillGrowth & SkillGrowthHistory models**
- **SkillGrowthService**
  - `add_experience()` - Award XP with level-up handling
  - `calculate_task_completion_exp()` - Smart XP calculation
  - `award_task_completion_exp()` - Auto-award on task completion
  - `get_skill_leaderboard()` - Company-wide rankings
  - `get_growth_stats()` - Overall statistics
- **Experience formula**
  - Base: 50 XP
  - Difficulty multiplier: low(0.8)/normal(1.0)/high(1.5)/urgent(2.0)
  - Efficiency bonus: Save budget, earn extra XP
  - Skill match bonus: +15 XP for using relevant skills
  - Level curve: 100 * 1.1^(level-1) XP to next level
- **Leaderboards** - Overall and per-skill rankings

#### OpenClaw Memory Sharing (P2)
- **Company-wide shared memory** - All agents can read/write
- **SharedMemory & MemoryAccessLog models**
- **Categories**: GENERAL, PROJECT, DECISION, LESSON, PREFERENCE, CONTACT, TODO, NOTE
- **SharedMemoryService**
  - Full CRUD operations
  - `search_memories()` - Text search with filters
  - `get_memories_for_agent_context()` - Relevant memories for agents
  - Access tracking and statistics
- **Integration** - Task assignments include relevant memories as context
- **Permission control** - Creator or Partner can edit/delete

### Changed
- Task assignment now checks for required approvals
- Message delivery includes shared memory context
- Task completion triggers dependency workflows

## [0.3.0-beta] - 2026-03-22

### Added
- **Async Message System (Phase 1-6)** - Full async communication infrastructure
  - AsyncMessage model with 7 states (pending/sending/sent/delivered/responded/failed/timeout)
  - 30-minute timeout tolerance
  - Non-blocking UI - users can close window and check later
  - Unified MessageCenter for polling optimization
  - Agent callback endpoint for task reporting
- **Phase 1: Infrastructure** - Database model and CRUD API
  - `/api/async-messages/send` - Send async message
  - `/api/async-messages/{id}` - Query message status
  - `/api/async-messages/{id}/status` - Get status updates
  - Background polling with 5-second intervals
- **Phase 2: Employee Chat Async** - Non-blocking employee messaging
  - Employee detail modal uses async API
  - Real-time status display (sending/delivered/responded/failed)
  - 5-second polling for response
  - Support closing modal and checking later
  - Toast notifications for replies
- **Phase 3: Partner Chat Async** - Non-blocking Partner communication
  - Partner floating widget uses async API
  - Auto-wake Partner on message send
  - Browser notification support
  - Message history with async status
- **Phase 4: Task Assignment Async** - Non-blocking task distribution
  - `TaskExecutionService._send_via_sessions` uses async message API
  - Frontend shows "Notifying Agent..." with loading state
  - 5-second polling to check Agent acceptance
  - Stores message_id in `task.execution_session_id`
- **Phase 5: Polling Optimization** - Unified MessageCenter
  - Single polling mechanism (5s interval) instead of multiple setIntervals
  - Subscribe/unsubscribe pattern for message tracking
  - Reduced API calls from multiple 5s intervals to single polling
  - Memory-efficient message management
- **Phase 6: Agent Callback** - Proactive task reporting
  - `POST /api/tasks/{task_id}/report` endpoint
  - Agents can report task completion/failure
  - Exact token tracking support (is_exact + session_key)
  - Agent verification against task assignment
  - Automatic budget deduction on report
- **Agent Lifecycle Management** - Automatic agent creation/deletion
  - 3-step confirmation flow for agent auto-creation
  - Backup/archival mechanism for agent deletion
  - Partner-designed avatars for new employees
- **Exact Token Tracking** - Real consumption via session_status API
  - Integration with OpenClaw session_status API
  - Automatic token reconciliation after task completion
  - Budget adjustment based on actual consumption
- **PostgreSQL Migration** - Production database support
  - Dual database support (SQLite for dev, PostgreSQL for prod)
  - Migration script from SQLite to PostgreSQL
  - Docker Compose profile for PostgreSQL stack
- **Pixel Avatar V2** - Personalized avatar system
  - Partner-designed avatars based on employee characteristics
  - User upload support (PNG/JPG/SVG, max 5MB)
  - AI-generated avatars via skills
  - Removed system random generation
  - Unified avatar display across all components
- **Chart Visualization** - Data visualization for reports
  - Dashboard: 7-day budget usage trend chart
  - Daily report: Budget distribution pie chart
  - Weekly report: 7-day trend line chart
- **Post-Fuse Options** - Actions when budget fuse triggers
  - Add Budget, Split Task, Reassign, Pause options
  - Dashboard UI with fuse alert banner
- **i18n Multi-language Support** - Chinese and English
  - Complete Chinese/English translations
  - Language switcher in UI
- **Employee Detail Modal** - 3-tab design
  - Info, Tasks, Chat tabs
  - Pause auto-refresh when modal open
- **Tab Integration** - Pixel Office as Dashboard tab
  - Seamless navigation between views
  - Consistent styling

### Changed
- **Avatar Architecture** - Single source of truth via `agent.avatar_url`
- **Async Task Assignment** - Changed from sync `sessions_send` to async API
- **Frontend Polling** - Unified MessageCenter instead of scattered intervals

### Fixed
- Avatar display consistency across employee list, detail modal, and pixel office
- Upload avatar "Internal server error" but actually succeeds
- Avatar modal showing old avatar after change
- System-generated avatars looking too abstract
- Missing cache refresh hints after upload
- Partner not bound handling in avatar design task
- PARTNER_ID loading before hire operation
- Task report endpoint using correct Agent ID

## [0.2.0-alpha] - 2026-03-21

### Added
- **Pixel Office** - CSS Grid-based 8-desk visualization with real-time status
- **Daily/Weekly Reports** - Automatic work summary generation
- **Employee Skills System** - 8 default skills with proficiency tracking
- **Notifications System** - Task/budget/overdue alerts with bell UI
- **Partner Health Monitoring** - Heartbeat detection and online status
- **System Config Panel** - Configurable timeout, token rate, budget threshold
- **SVG Pixel Avatars** - Position-based pixel art avatars
- Structured logging with structlog (JSON/text formats)
- API rate limiting with slowapi
- Global exception handler
- Complete API reference documentation

### Changed
- Updated README with v0.2.0 features and API documentation
- Improved task assignment with skill matching

### Fixed
- Fixed version number in root API endpoint (0.1.0 → 0.2.0-alpha)

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

- `v0.3.0-beta` - Async Message System Complete (Current)
- `v0.2.0-alpha` - Week 4 Complete Demo
- `v0.1.0-alpha` - Week 1-3 MVP

## Planned Versions

- `v0.3.0` - Production release (bug fixes)
- `v0.4.0-alpha` - Sub-tasks, workflows, memory sharing
- `v1.0.0` - Production ready
