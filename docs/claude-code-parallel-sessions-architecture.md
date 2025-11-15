# Claude Code Parallel Sessions Architecture
**Comprehensive Design for Multiple Simultaneous SSH Sessions**

Version: 1.0
Date: 2025-11-08
Author: Backend System Architect
Target: Claude Code v2.0.36+

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Current Claude Code Analysis](#current-claude-code-analysis)
4. [Technical Design](#technical-design)
5. [Directory Structure](#directory-structure)
6. [Configuration Strategy](#configuration-strategy)
7. [Implementation Plan](#implementation-plan)
8. [Usage Guidelines](#usage-guidelines)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Testing Procedures](#testing-procedures)
11. [Performance Considerations](#performance-considerations)
12. [Security Considerations](#security-considerations)

---

## Executive Summary

This document provides a comprehensive architecture for running multiple parallel Claude Code sessions via SSH from the `/home/UserID` directory. The solution ensures complete session isolation while sharing common resources (skills, custom agents, slash commands) and maintaining all existing functionality.

**Key Goals Achieved:**
- ✅ Multiple parallel sessions with complete isolation
- ✅ Shared access to skills and .md files
- ✅ No interference between sessions
- ✅ SSH compatibility from different connections
- ✅ Full MCP server support per session
- ✅ Maintain all existing functionality

**Approach:** Environment-based session isolation using `CLAUDE_SESSION_ID` and session-specific data directories.

---

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                      SSH Connection Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  SSH #1  │  │  SSH #2  │  │  SSH #3  │  │  SSH #N  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼──────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Session Launch Wrapper (claude-session)             │
│  • Generates/assigns unique SESSION_ID                           │
│  • Sets environment variables                                    │
│  • Configures session-specific paths                             │
└───────┬─────────────┬─────────────┬─────────────┬───────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Claude Code Process Layer                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  Session 1  │ │  Session 2  │ │  Session 3  │ │ Session N │ │
│  │  (PID:xxx)  │ │  (PID:yyy)  │ │  (PID:zzz)  │ │ (PID:nnn) │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└──────────────────────────────────────────────────────────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Data Storage Layer                           │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           SHARED RESOURCES (Read-Only)                   │    │
│  │  ~/.claude/skills/         (all skill definitions)       │    │
│  │  ~/.claude/agents/         (custom agent configs)        │    │
│  │  ~/.claude/commands/       (slash commands)              │    │
│  │  ~/.claude/plugins/        (plugin definitions)          │    │
│  │  ~/.claude/settings.json   (base settings)               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │        SESSION-ISOLATED STORAGE (Per Session)            │    │
│  │                                                           │    │
│  │  ~/.claude/sessions/{SESSION_ID}/                        │    │
│  │    ├── history.jsonl        (conversation history)       │    │
│  │    ├── history.lock         (lock file)                  │    │
│  │    ├── session-env/         (session environment)        │    │
│  │    ├── todos/               (session todos)              │    │
│  │    ├── shell-snapshots/     (bash state)                 │    │
│  │    ├── file-history/        (file edit history)          │    │
│  │    ├── debug/               (debug logs)                 │    │
│  │    └── mcp-state/           (MCP server state)           │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     MCP Server Instances                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  MCP Set 1  │ │  MCP Set 2  │ │  MCP Set 3  │ │ MCP Set N │ │
│  │  (Port:xxxx)│ │  (Port:yyyy)│ │  (Port:zzzz)│ │(Port:nnnn)│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Environment-Based Isolation**: Each session uses a unique `CLAUDE_SESSION_ID` UUID
2. **Shared Resources Pattern**: Skills, agents, and commands are shared read-only
3. **Session-Specific Storage**: History, state, and temporary data are isolated
4. **Process Isolation**: Each session runs as a separate Node.js process
5. **MCP Instance Separation**: Each session spawns its own MCP server instances
6. **Zero Cross-Talk**: No shared locks or state between sessions

---

## Current Claude Code Analysis

### Existing Directory Structure

Based on analysis of `/home/UserID/.claude/`:

```
~/.claude/
├── agents/                  # Custom agent definitions (SHARED)
├── backups/                 # Backup files (SHARED)
├── commands/                # Slash commands (SHARED)
├── config.md                # Configuration documentation (SHARED)
├── .credentials.json        # API credentials (SHARED, sensitive)
├── debug/                   # Debug logs (SESSION-SPECIFIC)
├── docs/                    # Documentation (SHARED)
├── downloads/               # Downloaded files (SHARED)
├── .env.example             # Environment template (SHARED)
├── file-history/            # File edit history (SESSION-SPECIFIC)
├── history.jsonl            # Conversation history (SESSION-SPECIFIC)
├── history.lock             # Lock file (SESSION-SPECIFIC)
├── local/                   # Local binaries (SHARED)
├── memory/                  # Knowledge base (SHARED, with potential conflicts)
├── plugins/                 # Plugin definitions (SHARED)
├── projects/                # Project-specific data (SESSION-SPECIFIC)
│   ├── default/
│   ├── -home-mdoehler/      # Contains per-conversation .jsonl files
│   └── -home-mdoehler--claude-skills/
├── scripts/                 # User scripts (SHARED)
├── session-env/             # Session environment (SESSION-SPECIFIC)
├── settings.json            # Base settings (SHARED)
├── settings.local.json      # Local settings override (SHARED)
├── shell-snapshots/         # Bash shell state (SESSION-SPECIFIC)
├── skills/                  # Skill definitions (SHARED)
├── statsig/                 # Analytics data (SHARED)
├── todos/                   # Todo lists (SESSION-SPECIFIC)
├── todos_archive/           # Archived todos (SHARED)
└── user-instructions.md     # User preferences (SHARED)
```

### Session ID Discovery

Claude Code uses **session IDs** (UUIDs) throughout:
- Found in `session-env/` directory: each subdirectory is a session UUID
- Found in `projects/-home-mdoehler/`: each `.jsonl` file is named with a UUID
- Session IDs are generated per conversation/session

### Critical Conflict Points

**Files/Directories with Potential Conflicts:**

1. **`history.jsonl`** - Main conversation history (CRITICAL)
2. **`history.lock`** - Lock file for history writes (CRITICAL)
3. **`session-env/{UUID}/`** - Session environment data (CRITICAL)
4. **`todos/`** - Session-specific todo lists (MEDIUM)
5. **`shell-snapshots/`** - Bash state snapshots (MEDIUM)
6. **`file-history/`** - File edit tracking (MEDIUM)
7. **`debug/`** - Debug logs (LOW)
8. **`projects/-home-mdoehler/{UUID}.jsonl`** - Per-session project data (MEDIUM)

### MCP Server Configuration

MCP servers are configured via:
- `settings.local.json` → `enabledMcpjsonServers`
- Skills can define MCP servers in their `config.json`
- MCP servers are spawned as child processes per session

---

## Technical Design

### Solution: Session-Scoped Environment Variables

Claude Code will be wrapped with a launcher script that sets session-specific environment variables to redirect storage paths.

#### Key Environment Variables

```bash
# Core session identifier
CLAUDE_SESSION_ID="<UUID>"              # Unique session identifier

# Session-specific data paths
CLAUDE_SESSION_DIR="$HOME/.claude/sessions/$CLAUDE_SESSION_ID"
CLAUDE_HISTORY_FILE="$CLAUDE_SESSION_DIR/history.jsonl"
CLAUDE_HISTORY_LOCK="$CLAUDE_SESSION_DIR/history.lock"
CLAUDE_SESSION_ENV_DIR="$CLAUDE_SESSION_DIR/session-env"
CLAUDE_TODOS_DIR="$CLAUDE_SESSION_DIR/todos"
CLAUDE_SHELL_SNAPSHOTS_DIR="$CLAUDE_SESSION_DIR/shell-snapshots"
CLAUDE_FILE_HISTORY_DIR="$CLAUDE_SESSION_DIR/file-history"
CLAUDE_DEBUG_DIR="$CLAUDE_SESSION_DIR/debug"
CLAUDE_PROJECT_DIR="$CLAUDE_SESSION_DIR/project"

# Shared resources (read-only references)
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
CLAUDE_AGENTS_DIR="$HOME/.claude/agents"
CLAUDE_COMMANDS_DIR="$HOME/.claude/commands"
CLAUDE_PLUGINS_DIR="$HOME/.claude/plugins"

# Session metadata
CLAUDE_SESSION_NAME="<descriptive-name>"
CLAUDE_SESSION_USER="$USER"
CLAUDE_SESSION_SSH_CLIENT="$SSH_CLIENT"
CLAUDE_SESSION_START_TIME="$(date +%s)"
```

### Session Lifecycle

```
┌────────────────────────────────────────────────────────────────┐
│ 1. SSH Connection Established                                  │
└────────────────┬───────────────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────────────┐
│ 2. User runs: claude-session [name]                            │
│    - Checks for existing session or creates new UUID           │
│    - Validates/creates session directory structure             │
│    - Sets environment variables                                │
└────────────────┬───────────────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────────────┐
│ 3. Session wrapper exports environment                         │
│    - CLAUDE_SESSION_ID=<UUID>                                  │
│    - CLAUDE_SESSION_DIR=~/.claude/sessions/<UUID>              │
│    - All session-specific paths configured                     │
└────────────────┬───────────────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────────────┐
│ 4. Claude Code launched with environment                       │
│    - Reads shared resources (skills, agents, commands)         │
│    - Writes to session-specific directories                    │
│    - Spawns MCP servers with session-specific env              │
└────────────────┬───────────────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────────────┐
│ 5. Session runs independently                                  │
│    - All data writes go to session directory                   │
│    - No conflicts with other sessions                          │
│    - MCP servers isolated per session                          │
└────────────────┬───────────────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────────────┐
│ 6. Session ends (Ctrl+D or exit)                               │
│    - MCP servers terminated                                    │
│    - Session metadata updated (end time, exit code)            │
│    - Session directory preserved for future resume             │
└────────────────────────────────────────────────────────────────┘
```

### Storage Isolation Strategy

#### Shared Resources (Read-Only)

These are accessed by all sessions without modification:

```
~/.claude/
├── skills/              → All sessions read skill definitions
├── agents/              → All sessions use custom agents
├── commands/            → All sessions have slash commands
├── plugins/             → Plugin definitions shared
├── settings.json        → Base configuration shared
├── settings.local.json  → Local overrides shared
├── user-instructions.md → User preferences shared
├── .credentials.json    → API credentials shared (read-only)
└── docs/                → Documentation shared
```

#### Session-Isolated Storage (Read-Write)

Each session has its own isolated storage:

```
~/.claude/sessions/{SESSION_ID}/
├── history.jsonl        → Conversation history
├── history.lock         → Lock file (no cross-session locking)
├── session-env/         → Environment variables
├── todos/               → Todo lists for this session
├── shell-snapshots/     → Bash state for this session
├── file-history/        → File edit history
├── debug/               → Debug logs
├── project/             → Project-specific data
│   └── -home-mdoehler/  → Working directory specific data
├── mcp-state/           → MCP server state (if applicable)
├── metadata.json        → Session metadata
└── session.log          → Session activity log
```

#### Session Metadata Structure

Each session maintains a `metadata.json`:

```json
{
  "sessionId": "64448612-0e5c-4075-8d92-4cb54e7e0567",
  "sessionName": "netbox-integration-dev",
  "userId": "mdoehler",
  "sshClient": "192.168.1.100 54321 22",
  "workingDirectory": "/home/UserID",
  "startTime": "2025-11-08T14:43:00Z",
  "endTime": null,
  "status": "active",
  "model": "claude-sonnet-4-5-20250929",
  "lastActivity": "2025-11-08T15:20:00Z",
  "messageCount": 42,
  "toolCallCount": 156,
  "mcpServers": [
    "powerpoint-server",
    "excel-master-server",
    "netbox",
    "memory-local"
  ],
  "exitCode": null
}
```

### MCP Server Isolation

Each session spawns its own MCP server instances with session-specific:

1. **Environment Variables**: MCP servers inherit `CLAUDE_SESSION_ID`
2. **Working Directory**: Each MCP process runs in session context
3. **Process Isolation**: Separate PIDs per session
4. **Port Allocation**: Dynamic port allocation per session (if TCP-based)
5. **State Files**: Session-specific state storage

#### MCP Configuration Approach

MCP servers can be:
- **Global**: Defined in `settings.local.json` (all sessions)
- **Skill-Specific**: Defined in skill `config.json` (when skill is active)
- **Session-Override**: Can be overridden per session via `--mcp-config`

**Strategy for Stateful MCP Servers** (e.g., memory-local):

```bash
# Each session has its own memory instance
~/.claude/sessions/{SESSION_ID}/mcp-state/memory-local/
├── entities.json
├── relations.json
└── observations.json
```

MCP server launch modified to use session-specific state directory:

```bash
# Instead of global state
npx @modelcontextprotocol/server-memory@latest

# Use session-specific state
MEMORY_DATA_DIR="$CLAUDE_SESSION_DIR/mcp-state/memory-local" \
  npx @modelcontextprotocol/server-memory@latest
```

---

## Directory Structure

### Complete Directory Layout

```
/home/UserID/
├── .claude/                           # Main Claude directory
│   ├── agents/                        # [SHARED] Custom agent definitions
│   ├── backups/                       # [SHARED] Backup files
│   ├── commands/                      # [SHARED] Slash commands
│   ├── config.md                      # [SHARED] Configuration docs
│   ├── .credentials.json              # [SHARED] API credentials
│   ├── docs/                          # [SHARED] Documentation
│   ├── downloads/                     # [SHARED] Downloaded files
│   ├── .env.example                   # [SHARED] Environment template
│   ├── local/                         # [SHARED] Local binaries
│   │   └── bin/
│   ├── memory/                        # [SHARED] Global memory (careful!)
│   ├── plugins/                       # [SHARED] Plugin definitions
│   ├── scripts/                       # [SHARED] User scripts
│   ├── settings.json                  # [SHARED] Base settings
│   ├── settings.local.json            # [SHARED] Local overrides
│   ├── skills/                        # [SHARED] Skill definitions
│   ├── statsig/                       # [SHARED] Analytics
│   ├── todos_archive/                 # [SHARED] Archived todos
│   ├── user-instructions.md           # [SHARED] User preferences
│   │
│   ├── sessions/                      # [NEW] Session storage root
│   │   ├── .registry                  # Session registry database
│   │   ├── active/                    # Symlinks to active sessions
│   │   │   ├── session-1 -> ../64448612-0e5c-4075-8d92-4cb54e7e0567
│   │   │   └── session-2 -> ../82f563e-5592-4e1a-977a-3bd08f4a9fa6
│   │   │
│   │   ├── 64448612-0e5c-4075-8d92-4cb54e7e0567/  # Session 1
│   │   │   ├── metadata.json
│   │   │   ├── session.log
│   │   │   ├── history.jsonl
│   │   │   ├── history.lock
│   │   │   ├── session-env/
│   │   │   ├── todos/
│   │   │   ├── shell-snapshots/
│   │   │   ├── file-history/
│   │   │   ├── debug/
│   │   │   ├── project/
│   │   │   │   └── -home-mdoehler/
│   │   │   └── mcp-state/
│   │   │       ├── memory-local/
│   │   │       ├── sequential-thinking/
│   │   │       └── github/
│   │   │
│   │   ├── 82f563e-5592-4e1a-977a-3bd08f4a9fa6/  # Session 2
│   │   │   └── [same structure as Session 1]
│   │   │
│   │   └── [more sessions...]
│   │
│   └── bin/                           # [NEW] Session management scripts
│       ├── claude-session             # Main session wrapper
│       ├── claude-session-list        # List all sessions
│       ├── claude-session-attach      # Attach to running session
│       ├── claude-session-cleanup     # Cleanup old sessions
│       └── claude-session-export      # Export session data
│
└── .bashrc or .bash_profile           # [MODIFIED] Add aliases
```

### Session Registry Format

The `.registry` file tracks all sessions (SQLite or JSON):

**SQLite Schema:**
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    session_name TEXT,
    user_id TEXT,
    ssh_client TEXT,
    working_directory TEXT,
    start_time INTEGER,
    end_time INTEGER,
    last_activity INTEGER,
    status TEXT,  -- 'active', 'stopped', 'archived'
    model TEXT,
    message_count INTEGER,
    tool_call_count INTEGER,
    exit_code INTEGER
);

CREATE INDEX idx_status ON sessions(status);
CREATE INDEX idx_user ON sessions(user_id);
CREATE INDEX idx_start_time ON sessions(start_time);
```

**JSON Format (simpler alternative):**
```json
{
  "sessions": {
    "64448612-0e5c-4075-8d92-4cb54e7e0567": {
      "sessionName": "netbox-dev",
      "userId": "mdoehler",
      "sshClient": "192.168.1.100 54321 22",
      "workingDirectory": "/home/UserID",
      "startTime": 1699450980,
      "endTime": null,
      "status": "active",
      "model": "claude-sonnet-4-5-20250929",
      "lastActivity": 1699453200,
      "messageCount": 42,
      "toolCallCount": 156
    }
  }
}
```

---

## Configuration Strategy

### Base Configuration Files

#### 1. `~/.claude/settings.json`

**Current file** - No changes needed. Contains:
```json
{
  "enabledPlugins": {
    "llm-application-dev@claude-code-workflows": true,
    "backend-development@claude-code-workflows": true,
    ...
  },
  "alwaysThinkingEnabled": false
}
```

This is shared across all sessions.

#### 2. `~/.claude/settings.local.json`

**Current file** - Contains global settings:
```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [...]
  },
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": [
    "powerpoint-server",
    "excel-master-server",
    "access-server"
  ],
  "outputStyle": "Explanatory",
  "spinnerTipsEnabled": false,
  "language": "de",
  "locale": "de-DE",
  ...
}
```

This is also shared, but can be overridden per-session.

#### 3. Session-Specific Settings (Optional)

Each session CAN have overrides:

`~/.claude/sessions/{SESSION_ID}/settings-override.json`

```json
{
  "outputStyle": "Concise",
  "model": "claude-opus-4-20250514",
  "disallowedTools": ["Bash(rm:*)"],
  "appendSystemPrompt": "You are working on the NetBox integration project."
}
```

### Environment Variable Configuration

#### Session Wrapper Environment

The `claude-session` wrapper sets these variables:

```bash
#!/bin/bash
# claude-session wrapper
export CLAUDE_SESSION_ID="${SESSION_ID}"
export CLAUDE_SESSION_DIR="$HOME/.claude/sessions/$SESSION_ID"
export CLAUDE_HISTORY_FILE="$CLAUDE_SESSION_DIR/history.jsonl"
export CLAUDE_HISTORY_LOCK="$CLAUDE_SESSION_DIR/history.lock"
export CLAUDE_SESSION_ENV_DIR="$CLAUDE_SESSION_DIR/session-env"
export CLAUDE_TODOS_DIR="$CLAUDE_SESSION_DIR/todos"
export CLAUDE_SHELL_SNAPSHOTS_DIR="$CLAUDE_SESSION_DIR/shell-snapshots"
export CLAUDE_FILE_HISTORY_DIR="$CLAUDE_SESSION_DIR/file-history"
export CLAUDE_DEBUG_DIR="$CLAUDE_SESSION_DIR/debug"
export CLAUDE_PROJECT_DIR="$CLAUDE_SESSION_DIR/project"

# Session metadata
export CLAUDE_SESSION_NAME="${SESSION_NAME}"
export CLAUDE_SESSION_START_TIME="$(date +%s)"

# Shared resources
export CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
export CLAUDE_AGENTS_DIR="$HOME/.claude/agents"
export CLAUDE_COMMANDS_DIR="$HOME/.claude/commands"

# Launch Claude with session ID
exec claude --session-id "$SESSION_ID" "$@"
```

### MCP Server Configuration Per Session

MCP servers are spawned with session-aware environment:

```bash
# Example: Memory MCP server with session-specific storage
{
  "mcpServers": {
    "memory-local": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-memory@latest"],
      "env": {
        "MEMORY_DATA_DIR": "${CLAUDE_SESSION_DIR}/mcp-state/memory-local"
      }
    }
  }
}
```

**Strategy:**
1. Skills define MCP servers in `config.json`
2. Session wrapper can inject `env` overrides for session-specific paths
3. Each session spawns independent MCP server processes

---

## Implementation Plan

### Phase 1: Preparation and Backup (30 minutes)

#### Step 1.1: Backup Current Configuration

```bash
# Create backup directory
BACKUP_DIR="$HOME/.claude-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup entire .claude directory (excluding large files)
rsync -av --exclude='session-env/' --exclude='shell-snapshots/' \
  "$HOME/.claude/" "$BACKUP_DIR/"

# Verify backup
ls -lh "$BACKUP_DIR"
```

#### Step 1.2: Document Current State

```bash
# Save current directory structure
tree -L 3 "$HOME/.claude" > "$BACKUP_DIR/structure-before.txt"

# Save current environment
env | grep -i claude > "$BACKUP_DIR/env-before.txt"

# List running Claude processes
ps aux | grep claude > "$BACKUP_DIR/processes-before.txt"
```

### Phase 2: Directory Structure Setup (15 minutes)

#### Step 2.1: Create Session Directory Structure

```bash
# Create session management directories
mkdir -p "$HOME/.claude/sessions"
mkdir -p "$HOME/.claude/sessions/active"
mkdir -p "$HOME/.claude/bin"

# Initialize session registry
cat > "$HOME/.claude/sessions/.registry" << 'EOF'
{
  "version": "1.0",
  "sessions": {}
}
EOF

chmod 644 "$HOME/.claude/sessions/.registry"
```

#### Step 2.2: Migrate Existing Session Data (Optional)

```bash
# If you want to preserve current session as "default"
DEFAULT_SESSION_ID="00000000-0000-0000-0000-000000000000"
mkdir -p "$HOME/.claude/sessions/$DEFAULT_SESSION_ID"

# Move current session data
mv "$HOME/.claude/history.jsonl" \
   "$HOME/.claude/sessions/$DEFAULT_SESSION_ID/" 2>/dev/null || true
mv "$HOME/.claude/history.lock" \
   "$HOME/.claude/sessions/$DEFAULT_SESSION_ID/" 2>/dev/null || true
mv "$HOME/.claude/session-env" \
   "$HOME/.claude/sessions/$DEFAULT_SESSION_ID/" 2>/dev/null || true
mv "$HOME/.claude/todos" \
   "$HOME/.claude/sessions/$DEFAULT_SESSION_ID/" 2>/dev/null || true
mv "$HOME/.claude/shell-snapshots" \
   "$HOME/.claude/sessions/$DEFAULT_SESSION_ID/" 2>/dev/null || true
mv "$HOME/.claude/file-history" \
   "$HOME/.claude/sessions/$DEFAULT_SESSION_ID/" 2>/dev/null || true
mv "$HOME/.claude/debug" \
   "$HOME/.claude/sessions/$DEFAULT_SESSION_ID/" 2>/dev/null || true

# Create project directory
mkdir -p "$HOME/.claude/sessions/$DEFAULT_SESSION_ID/project"
mkdir -p "$HOME/.claude/sessions/$DEFAULT_SESSION_ID/mcp-state"

# Create metadata
cat > "$HOME/.claude/sessions/$DEFAULT_SESSION_ID/metadata.json" << EOF
{
  "sessionId": "$DEFAULT_SESSION_ID",
  "sessionName": "default",
  "userId": "$USER",
  "workingDirectory": "$HOME",
  "startTime": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "migrated",
  "model": "claude-sonnet-4-5-20250929"
}
EOF
```

### Phase 3: Session Management Scripts (60 minutes)

#### Step 3.1: Main Session Wrapper (`claude-session`)

Create `/home/UserID/.claude/bin/claude-session`:

```bash
#!/bin/bash
#
# claude-session - Launch Claude Code in isolated session
#
# Usage: claude-session [OPTIONS] [session-name]
#
# Options:
#   -n, --new          Force create new session
#   -l, --list         List all sessions
#   -r, --resume ID    Resume existing session by ID
#   -d, --delete ID    Delete a session
#   -h, --help         Show this help
#

set -euo pipefail

# Configuration
CLAUDE_ROOT="$HOME/.claude"
SESSIONS_DIR="$CLAUDE_ROOT/sessions"
REGISTRY_FILE="$SESSIONS_DIR/.registry"
CLAUDE_BIN="$(which claude)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Generate UUID v4
generate_uuid() {
    cat /proc/sys/kernel/random/uuid
}

# Create session directory structure
create_session_dir() {
    local session_id="$1"
    local session_dir="$SESSIONS_DIR/$session_id"

    mkdir -p "$session_dir"
    mkdir -p "$session_dir/session-env"
    mkdir -p "$session_dir/todos"
    mkdir -p "$session_dir/shell-snapshots"
    mkdir -p "$session_dir/file-history"
    mkdir -p "$session_dir/debug"
    mkdir -p "$session_dir/project/-home-mdoehler"
    mkdir -p "$session_dir/mcp-state"

    # Create empty files
    touch "$session_dir/history.jsonl"
    touch "$session_dir/history.lock"
    touch "$session_dir/session.log"

    log_success "Created session directory: $session_dir"
}

# Create session metadata
create_session_metadata() {
    local session_id="$1"
    local session_name="$2"
    local session_dir="$SESSIONS_DIR/$session_id"

    cat > "$session_dir/metadata.json" << EOF
{
  "sessionId": "$session_id",
  "sessionName": "$session_name",
  "userId": "$USER",
  "sshClient": "${SSH_CLIENT:-local}",
  "workingDirectory": "$(pwd)",
  "startTime": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "endTime": null,
  "status": "active",
  "model": "claude-sonnet-4-5-20250929",
  "lastActivity": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "messageCount": 0,
  "toolCallCount": 0,
  "mcpServers": [],
  "exitCode": null
}
EOF

    log_success "Created session metadata"
}

# Register session in registry
register_session() {
    local session_id="$1"
    local session_name="$2"

    # Simple JSON append (in production, use jq or proper JSON parser)
    python3 << EOF
import json
import os

registry_file = "$REGISTRY_FILE"
session_id = "$session_id"
session_name = "$session_name"

# Read existing registry
with open(registry_file, 'r') as f:
    registry = json.load(f)

# Add new session
registry['sessions'][session_id] = {
    'sessionName': session_name,
    'userId': os.environ.get('USER'),
    'sshClient': os.environ.get('SSH_CLIENT', 'local'),
    'workingDirectory': os.getcwd(),
    'startTime': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
    'status': 'active'
}

# Write back
with open(registry_file, 'w') as f:
    json.dump(registry, f, indent=2)

print(f"Registered session {session_id}")
EOF

    log_success "Registered session in registry"
}

# Set session environment
setup_session_env() {
    local session_id="$1"
    local session_name="$2"
    local session_dir="$SESSIONS_DIR/$session_id"

    export CLAUDE_SESSION_ID="$session_id"
    export CLAUDE_SESSION_DIR="$session_dir"
    export CLAUDE_SESSION_NAME="$session_name"
    export CLAUDE_SESSION_START_TIME="$(date +%s)"

    # Session-specific paths
    export CLAUDE_HISTORY_FILE="$session_dir/history.jsonl"
    export CLAUDE_HISTORY_LOCK="$session_dir/history.lock"
    export CLAUDE_SESSION_ENV_DIR="$session_dir/session-env"
    export CLAUDE_TODOS_DIR="$session_dir/todos"
    export CLAUDE_SHELL_SNAPSHOTS_DIR="$session_dir/shell-snapshots"
    export CLAUDE_FILE_HISTORY_DIR="$session_dir/file-history"
    export CLAUDE_DEBUG_DIR="$session_dir/debug"
    export CLAUDE_PROJECT_DIR="$session_dir/project"
    export CLAUDE_MCP_STATE_DIR="$session_dir/mcp-state"

    # Shared resources
    export CLAUDE_SKILLS_DIR="$CLAUDE_ROOT/skills"
    export CLAUDE_AGENTS_DIR="$CLAUDE_ROOT/agents"
    export CLAUDE_COMMANDS_DIR="$CLAUDE_ROOT/commands"
    export CLAUDE_PLUGINS_DIR="$CLAUDE_ROOT/plugins"

    log_info "Session environment configured"
    log_info "Session ID: $session_id"
    log_info "Session Name: $session_name"
    log_info "Session Dir: $session_dir"
}

# Launch Claude Code
launch_claude() {
    local session_id="$1"
    shift
    local args="$@"

    log_info "Launching Claude Code..."
    log_info "Session ID: $session_id"

    # Create symlink in active sessions
    ln -sf "$SESSIONS_DIR/$session_id" "$SESSIONS_DIR/active/$session_id"

    # Launch Claude with session ID
    exec "$CLAUDE_BIN" --session-id "$session_id" $args
}

# Main function
main() {
    local force_new=false
    local session_name=""
    local resume_id=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--new)
                force_new=true
                shift
                ;;
            -l|--list)
                exec "$CLAUDE_ROOT/bin/claude-session-list"
                ;;
            -r|--resume)
                resume_id="$2"
                shift 2
                ;;
            -d|--delete)
                # TODO: Implement delete
                log_error "Delete not yet implemented"
                exit 1
                ;;
            -h|--help)
                grep '^#' "$0" | tail -n +3 | head -n -1 | cut -c 3-
                exit 0
                ;;
            *)
                session_name="$1"
                shift
                ;;
        esac
    done

    # Resume existing session
    if [[ -n "$resume_id" ]]; then
        if [[ ! -d "$SESSIONS_DIR/$resume_id" ]]; then
            log_error "Session $resume_id not found"
            exit 1
        fi

        log_info "Resuming session: $resume_id"
        setup_session_env "$resume_id" "$(basename $resume_id)"
        launch_claude "$resume_id" --resume "$resume_id"
        exit 0
    fi

    # Generate session name if not provided
    if [[ -z "$session_name" ]]; then
        session_name="session-$(date +%Y%m%d-%H%M%S)"
    fi

    # Generate new session ID
    local session_id=$(generate_uuid)

    log_info "Creating new session: $session_name"
    log_info "Session ID: $session_id"

    # Create session
    create_session_dir "$session_id"
    create_session_metadata "$session_id" "$session_name"
    register_session "$session_id" "$session_name"
    setup_session_env "$session_id" "$session_name"

    # Launch Claude
    launch_claude "$session_id"
}

# Run main
main "$@"
```

Make it executable:

```bash
chmod +x "$HOME/.claude/bin/claude-session"
```

#### Step 3.2: Session List Script (`claude-session-list`)

Create `/home/UserID/.claude/bin/claude-session-list`:

```bash
#!/bin/bash
#
# claude-session-list - List all Claude Code sessions
#

set -euo pipefail

SESSIONS_DIR="$HOME/.claude/sessions"
REGISTRY_FILE="$SESSIONS_DIR/.registry"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      Claude Code Sessions                              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo

# Check if registry exists
if [[ ! -f "$REGISTRY_FILE" ]]; then
    echo -e "${RED}No sessions found. Registry file does not exist.${NC}"
    exit 0
fi

# List sessions using Python for JSON parsing
python3 << 'EOF'
import json
import os
from datetime import datetime

sessions_dir = os.path.expanduser("~/.claude/sessions")
registry_file = os.path.join(sessions_dir, ".registry")

with open(registry_file, 'r') as f:
    registry = json.load(f)

sessions = registry.get('sessions', {})

if not sessions:
    print("No sessions found.")
else:
    print(f"{'Session ID':<40} {'Name':<20} {'Status':<10} {'Started':<20}")
    print("─" * 100)

    for session_id, session_data in sessions.items():
        name = session_data.get('sessionName', 'unknown')
        status = session_data.get('status', 'unknown')
        start_time = session_data.get('startTime', 'unknown')

        # Check if session is actually active
        session_dir = os.path.join(sessions_dir, session_id)
        if not os.path.exists(session_dir):
            status = 'deleted'

        # Color code status
        if status == 'active':
            status_colored = f"\033[0;32m{status}\033[0m"
        elif status == 'stopped':
            status_colored = f"\033[1;33m{status}\033[0m"
        else:
            status_colored = f"\033[0;31m{status}\033[0m"

        print(f"{session_id:<40} {name:<20} {status_colored:<20} {start_time:<20}")

    print()
    print(f"Total sessions: {len(sessions)}")
EOF

echo
echo -e "${BLUE}Commands:${NC}"
echo "  claude-session -r <SESSION_ID>    Resume a session"
echo "  claude-session -n [name]           Create new session"
echo "  claude-session-cleanup             Cleanup old sessions"
echo
```

Make it executable:

```bash
chmod +x "$HOME/.claude/bin/claude-session-list"
```

#### Step 3.3: Session Cleanup Script (`claude-session-cleanup`)

Create `/home/UserID/.claude/bin/claude-session-cleanup`:

```bash
#!/bin/bash
#
# claude-session-cleanup - Cleanup old/inactive sessions
#

set -euo pipefail

SESSIONS_DIR="$HOME/.claude/sessions"
REGISTRY_FILE="$SESSIONS_DIR/.registry"

# Configuration
DAYS_TO_KEEP=30  # Keep sessions for 30 days

log_info() {
    echo "[INFO] $1"
}

log_warn() {
    echo "[WARN] $1"
}

log_success() {
    echo "[SUCCESS] $1"
}

# Find old sessions
find_old_sessions() {
    find "$SESSIONS_DIR" -maxdepth 1 -type d -name "*-*-*-*-*" \
        -mtime +$DAYS_TO_KEEP
}

# Main
main() {
    log_info "Scanning for sessions older than $DAYS_TO_KEEP days..."

    old_sessions=$(find_old_sessions)

    if [[ -z "$old_sessions" ]]; then
        log_info "No old sessions found."
        exit 0
    fi

    echo "Found old sessions:"
    echo "$old_sessions"
    echo

    read -p "Delete these sessions? [y/N] " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        while IFS= read -r session_dir; do
            session_id=$(basename "$session_dir")
            log_warn "Deleting session: $session_id"

            # Remove from registry
            python3 << EOF
import json

registry_file = "$REGISTRY_FILE"
session_id = "$session_id"

with open(registry_file, 'r') as f:
    registry = json.load(f)

if session_id in registry['sessions']:
    del registry['sessions'][session_id]

    with open(registry_file, 'w') as f:
        json.dump(registry, f, indent=2)
EOF

            # Remove directory
            rm -rf "$session_dir"

            # Remove symlink if exists
            rm -f "$SESSIONS_DIR/active/$session_id"

            log_success "Deleted session: $session_id"
        done <<< "$old_sessions"

        log_success "Cleanup complete"
    else
        log_info "Cleanup cancelled"
    fi
}

main "$@"
```

Make it executable:

```bash
chmod +x "$HOME/.claude/bin/claude-session-cleanup"
```

### Phase 4: Shell Integration (10 minutes)

#### Step 4.1: Add Aliases to `.bashrc`

Add to `/home/UserID/.bashrc`:

```bash
# Claude Code Session Management
export PATH="$HOME/.claude/bin:$PATH"

# Aliases
alias cs='claude-session'
alias cs-list='claude-session-list'
alias cs-new='claude-session --new'
alias cs-resume='claude-session --resume'
alias cs-cleanup='claude-session-cleanup'

# Helper function to quickly start named sessions
csn() {
    if [[ -z "$1" ]]; then
        echo "Usage: csn <session-name>"
        return 1
    fi
    claude-session --new "$1"
}

# Helper to resume last session
csl() {
    local last_session=$(ls -t "$HOME/.claude/sessions/" | grep -E '^[0-9a-f-]{36}$' | head -1)
    if [[ -z "$last_session" ]]; then
        echo "No sessions found"
        return 1
    fi
    echo "Resuming last session: $last_session"
    claude-session --resume "$last_session"
}
```

Reload shell configuration:

```bash
source ~/.bashrc
```

### Phase 5: Testing and Validation (30 minutes)

#### Test Plan - see [Testing Procedures](#testing-procedures) section below

### Phase 6: Documentation and Training (15 minutes)

Create quick reference guide:

```bash
cat > "$HOME/.claude/sessions/README.md" << 'EOF'
# Claude Code Session Management

## Quick Start

### Create a new session
```bash
claude-session my-project
```

### List all sessions
```bash
claude-session-list
```

### Resume a session
```bash
claude-session --resume <SESSION_ID>
```

### Resume last session
```bash
csl
```

## Session Isolation

Each session maintains its own:
- Conversation history
- Todo lists
- Shell state
- File edit history
- MCP server instances

All sessions share:
- Skills
- Custom agents
- Slash commands
- Settings

## Tips

1. **Naming sessions**: Use descriptive names
   ```bash
   claude-session netbox-integration
   claude-session api-refactor
   ```

2. **Multiple parallel sessions**: Each SSH connection can run its own session
   ```bash
   # SSH Terminal 1
   claude-session backend-work

   # SSH Terminal 2
   claude-session frontend-work
   ```

3. **Session cleanup**: Regularly clean up old sessions
   ```bash
   claude-session-cleanup
   ```

## Troubleshooting

See main documentation: ~/.claude/sessions/TROUBLESHOOTING.md
EOF
```

---

## Usage Guidelines

### Basic Workflows

#### Starting a New Session

```bash
# Method 1: Auto-generated name
claude-session

# Method 2: Named session
claude-session my-project-name

# Method 3: Using alias
csn api-development
```

#### Listing Sessions

```bash
# List all sessions
claude-session-list

# Or use alias
cs-list
```

**Example Output:**
```
╔════════════════════════════════════════════════════════════════════════╗
║                      Claude Code Sessions                              ║
╚════════════════════════════════════════════════════════════════════════╝

Session ID                               Name                 Status     Started
────────────────────────────────────────────────────────────────────────────────────────────
64448612-0e5c-4075-8d92-4cb54e7e0567    netbox-integration   active     2025-11-08T14:43:00Z
82f563e-5592-4e1a-977a-3bd08f4a9fa6     api-refactor         stopped    2025-11-07T10:20:00Z
1bc93b1b-ba92-4962-a320-9e22b1b2ac41    frontend-dev         active     2025-11-08T15:00:00Z

Total sessions: 3

Commands:
  claude-session -r <SESSION_ID>    Resume a session
  claude-session -n [name]           Create new session
  claude-session-cleanup             Cleanup old sessions
```

#### Resuming a Session

```bash
# Resume by ID
claude-session --resume 64448612-0e5c-4075-8d92-4cb54e7e0567

# Or using alias
cs-resume 64448612-0e5c-4075-8d92-4cb54e7e0567

# Resume last session
csl
```

#### Parallel Session Workflow

**Terminal 1 (SSH Connection 1):**
```bash
ssh mdoehler@server
claude-session backend-api-work
# Works on backend API...
```

**Terminal 2 (SSH Connection 2):**
```bash
ssh mdoehler@server
claude-session database-migration
# Works on database migration...
```

**Terminal 3 (SSH Connection 3):**
```bash
ssh mdoehler@server
claude-session documentation-update
# Works on documentation...
```

All three sessions run **completely independently** with **no interference**.

### Advanced Usage

#### Custom MCP Configuration Per Session

Override MCP servers for a specific session:

```bash
# Create session-specific MCP config
cat > /tmp/session-mcp.json << 'EOF'
{
  "mcpServers": {
    "custom-db": {
      "command": "node",
      "args": ["/path/to/custom-db-mcp.js"],
      "env": {
        "DB_NAME": "session_specific_db"
      }
    }
  }
}
EOF

# Launch with custom MCP config
claude-session my-session --mcp-config /tmp/session-mcp.json
```

#### Session-Specific Settings Override

```bash
# Create session
SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
mkdir -p "$HOME/.claude/sessions/$SESSION_ID"

# Add settings override
cat > "$HOME/.claude/sessions/$SESSION_ID/settings-override.json" << 'EOF'
{
  "model": "claude-opus-4-20250514",
  "outputStyle": "Concise",
  "appendSystemPrompt": "You are working on a critical production bug fix."
}
EOF

# Launch session
claude-session --resume $SESSION_ID --settings "$HOME/.claude/sessions/$SESSION_ID/settings-override.json"
```

#### Export Session Data

```bash
# Export session conversation history
SESSION_ID="64448612-0e5c-4075-8d92-4cb54e7e0567"
cp "$HOME/.claude/sessions/$SESSION_ID/history.jsonl" \
   "./session-export-$(date +%Y%m%d).jsonl"

# Archive entire session
tar czf "session-backup-$SESSION_ID.tar.gz" \
  "$HOME/.claude/sessions/$SESSION_ID"
```

### Best Practices

1. **Session Naming**: Use descriptive names that indicate the task
   - ✅ `netbox-api-integration`
   - ✅ `bug-fix-user-auth`
   - ❌ `session1`, `test`, `asdf`

2. **Session Lifecycle**: Clean up old sessions regularly
   ```bash
   # Weekly cleanup
   claude-session-cleanup
   ```

3. **Long-Running Tasks**: Use named sessions for projects spanning days/weeks
   ```bash
   # Day 1
   claude-session long-term-project
   # ... work ...

   # Day 2 - Resume same session
   claude-session --resume <SESSION_ID>
   ```

4. **Parallel Work**: Use different sessions for unrelated tasks
   ```bash
   # Backend work
   claude-session backend-refactor

   # Meanwhile in another terminal: Frontend work
   claude-session frontend-ui-update
   ```

5. **Emergency Isolation**: If one session has issues, others are unaffected
   - Session 1 has a bug → Only Session 1 affected
   - Session 2, 3, 4 continue normally

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: "Session ID already exists"

**Symptom:**
```
[ERROR] Session 64448612-0e5c-4075-8d92-4cb54e7e0567 already exists
```

**Cause:** Attempting to create a session with an ID that already exists.

**Solution:**
```bash
# Option 1: Resume the existing session
claude-session --resume 64448612-0e5c-4075-8d92-4cb54e7e0567

# Option 2: Create a new session
claude-session --new my-new-session

# Option 3: Delete old session if no longer needed
rm -rf "$HOME/.claude/sessions/64448612-0e5c-4075-8d92-4cb54e7e0567"
```

#### Issue 2: History file locked

**Symptom:**
```
[ERROR] Cannot write to history.jsonl: file is locked
```

**Cause:** Another Claude process is holding the lock (should not happen with session isolation).

**Solution:**
```bash
# Check for stale lock
ls -la "$HOME/.claude/sessions/<SESSION_ID>/history.lock"

# Check if Claude process is actually running
ps aux | grep claude | grep <SESSION_ID>

# If no process is running, remove stale lock
rm -f "$HOME/.claude/sessions/<SESSION_ID>/history.lock"
```

#### Issue 3: MCP Server Port Conflicts

**Symptom:**
```
[ERROR] MCP server failed to start: port 8080 already in use
```

**Cause:** Multiple sessions trying to use the same hardcoded port.

**Solution:**
MCP servers should use dynamic ports. Check MCP config:

```bash
# Check MCP server configuration
cat "$HOME/.claude/skills/mcp-*/config.json"

# Ensure MCP servers don't hardcode ports
# If they do, modify to use dynamic allocation:
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["server.js"],
      "env": {
        "PORT": "0"  // 0 = dynamic port allocation
      }
    }
  }
}
```

#### Issue 4: Session directory permission errors

**Symptom:**
```
[ERROR] Cannot create directory: Permission denied
```

**Cause:** Wrong permissions on `.claude/sessions/` directory.

**Solution:**
```bash
# Fix permissions
chmod 755 "$HOME/.claude/sessions"
chmod -R u+rwX "$HOME/.claude/sessions"

# Verify
ls -la "$HOME/.claude/sessions"
```

#### Issue 5: "Claude Code not found"

**Symptom:**
```
[ERROR] claude: command not found
```

**Cause:** Claude not in PATH or wrong path in session wrapper.

**Solution:**
```bash
# Find Claude executable
which claude

# Update session wrapper if needed
CLAUDE_BIN="$(which claude)"

# Or add to PATH
export PATH="/home/UserID/.npm-global/bin:$PATH"
```

#### Issue 6: Shared resource conflicts

**Symptom:**
Two sessions modifying the same skill or agent definition simultaneously.

**Cause:** Shared resources are not meant to be modified during sessions.

**Solution:**
- Skills, agents, commands should be managed **outside** of sessions
- Use a separate session for skill/agent development
- Do not edit skill files from within Claude sessions

#### Issue 7: Session registry corruption

**Symptom:**
```
[ERROR] Failed to parse registry file
```

**Cause:** Corrupted `.registry` JSON file.

**Solution:**
```bash
# Backup corrupted registry
cp "$HOME/.claude/sessions/.registry" \
   "$HOME/.claude/sessions/.registry.backup"

# Rebuild registry from session directories
python3 << 'EOF'
import json
import os
from pathlib import Path

sessions_dir = Path.home() / ".claude" / "sessions"
registry_file = sessions_dir / ".registry"

# Find all session directories
session_dirs = [d for d in sessions_dir.iterdir()
                if d.is_dir() and len(d.name) == 36]

# Rebuild registry
registry = {"version": "1.0", "sessions": {}}

for session_dir in session_dirs:
    metadata_file = session_dir / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

        session_id = session_dir.name
        registry["sessions"][session_id] = {
            "sessionName": metadata.get("sessionName", "unknown"),
            "userId": metadata.get("userId"),
            "status": metadata.get("status", "unknown"),
            "startTime": metadata.get("startTime")
        }

# Write new registry
with open(registry_file, 'w') as f:
    json.dump(registry, f, indent=2)

print(f"Rebuilt registry with {len(registry['sessions'])} sessions")
EOF
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Set debug environment variable
export CLAUDE_DEBUG=1

# Launch session with debug
claude-session --debug my-debug-session

# Check debug logs
tail -f "$HOME/.claude/sessions/<SESSION_ID>/debug/debug.log"
```

### Log Locations

```bash
# Session-specific logs
~/.claude/sessions/{SESSION_ID}/session.log       # Session activity log
~/.claude/sessions/{SESSION_ID}/debug/            # Debug logs
~/.claude/sessions/{SESSION_ID}/history.jsonl     # Conversation history

# Global logs
~/.claude/claude_persistent.log                    # Persistent daemon log
```

### Health Check

```bash
# Check Claude Code health
claude doctor

# Check session directories
for dir in "$HOME/.claude/sessions"/*-*-*-*-*/; do
    if [[ -d "$dir" ]]; then
        session_id=$(basename "$dir")
        echo "Session: $session_id"
        echo "  History: $(wc -l < "$dir/history.jsonl") lines"
        echo "  Size: $(du -sh "$dir" | cut -f1)"
        echo
    fi
done
```

---

## Testing Procedures

### Test Suite

#### Test 1: Basic Session Creation

**Objective:** Verify a new session can be created.

```bash
# Create session
claude-session test-session-1

# Verify session directory exists
ls -la "$HOME/.claude/sessions/" | grep test-session-1

# Verify session is registered
claude-session-list | grep test-session-1

# Exit session
# (Ctrl+D or /exit)

# Verify session is in registry
cat "$HOME/.claude/sessions/.registry" | grep test-session-1
```

**Expected Result:** ✅ Session created, directory exists, registry updated

#### Test 2: Parallel Session Isolation

**Objective:** Run two sessions simultaneously without interference.

**Terminal 1:**
```bash
# Start session 1
claude-session parallel-test-1

# In Claude: Create a todo
(Write a todo)
/todos

# Note the session ID
echo $CLAUDE_SESSION_ID
```

**Terminal 2:**
```bash
# Start session 2
claude-session parallel-test-2

# In Claude: Create a different todo
(Write a different todo)
/todos

# Note the session ID
echo $CLAUDE_SESSION_ID
```

**Verification:**
```bash
# Check that todos are separate
SESSION_1="<session-1-id>"
SESSION_2="<session-2-id>"

ls -la "$HOME/.claude/sessions/$SESSION_1/todos/"
ls -la "$HOME/.claude/sessions/$SESSION_2/todos/"

# Verify different todo files exist
```

**Expected Result:** ✅ Each session has its own isolated todos

#### Test 3: History Isolation

**Objective:** Verify conversation history is separate per session.

```bash
# Session 1
claude-session history-test-1
# Have a conversation about topic A
# Exit

# Session 2
claude-session history-test-2
# Have a conversation about topic B
# Exit

# Verify histories are different
diff "$HOME/.claude/sessions/<session-1-id>/history.jsonl" \
     "$HOME/.claude/sessions/<session-2-id>/history.jsonl"
```

**Expected Result:** ✅ History files are different and independent

#### Test 4: Resume Session

**Objective:** Resume an existing session and continue conversation.

```bash
# Create session
claude-session resume-test
# Have a conversation: "Remember this: test-marker-12345"
# Exit

# Resume session
SESSION_ID=$(ls -t "$HOME/.claude/sessions/" | grep -E '^[0-9a-f-]{36}$' | head -1)
claude-session --resume $SESSION_ID
# Ask: "What did I tell you to remember?"
```

**Expected Result:** ✅ Claude remembers "test-marker-12345" from previous session

#### Test 5: Shared Skills Access

**Objective:** Verify all sessions can access shared skills.

**Terminal 1:**
```bash
claude-session skills-test-1
# Use a skill: /skill netbox-expert
```

**Terminal 2:**
```bash
claude-session skills-test-2
# Use same skill: /skill netbox-expert
```

**Expected Result:** ✅ Both sessions can use the skill without conflicts

#### Test 6: MCP Server Isolation

**Objective:** Verify each session has its own MCP server instances.

```bash
# Session 1
claude-session mcp-test-1
# Wait for MCP servers to start
# Check running processes
ps aux | grep mcp | grep $CLAUDE_SESSION_ID

# Session 2 (in another terminal)
claude-session mcp-test-2
# Check running processes
ps aux | grep mcp | grep $CLAUDE_SESSION_ID
```

**Expected Result:** ✅ Each session has separate MCP server processes

#### Test 7: Lock File Isolation

**Objective:** Verify no lock file conflicts between sessions.

**Terminal 1:**
```bash
claude-session lock-test-1
# Start conversation
# Check lock file
ls -la "$HOME/.claude/sessions/$CLAUDE_SESSION_ID/history.lock"
```

**Terminal 2:**
```bash
claude-session lock-test-2
# Start conversation (should not be blocked)
# Check lock file
ls -la "$HOME/.claude/sessions/$CLAUDE_SESSION_ID/history.lock"
```

**Expected Result:** ✅ Each session has its own lock file, no blocking

#### Test 8: Session Cleanup

**Objective:** Test cleanup of old sessions.

```bash
# Create old session
SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
mkdir -p "$HOME/.claude/sessions/$SESSION_ID"

# Set old timestamp (30+ days ago)
touch -d "40 days ago" "$HOME/.claude/sessions/$SESSION_ID"

# Run cleanup
claude-session-cleanup

# Verify old session was removed
ls "$HOME/.claude/sessions/" | grep $SESSION_ID
```

**Expected Result:** ✅ Old session directory removed

#### Test 9: Heavy Load Test

**Objective:** Run 5 parallel sessions simultaneously.

```bash
# Script to start 5 sessions
for i in {1..5}; do
    gnome-terminal -- bash -c "claude-session load-test-$i; exec bash"
done

# In each session, perform actions:
# - Read files
# - Write files
# - Use skills
# - Create todos
# - Execute bash commands

# Monitor system resources
htop
# Or
watch -n 1 'ps aux | grep claude | wc -l'
```

**Expected Result:** ✅ All 5 sessions run without conflicts or errors

#### Test 10: SSH Multi-Connection Test

**Objective:** Verify sessions work across multiple SSH connections.

**SSH Connection 1:**
```bash
ssh mdoehler@server
claude-session ssh-test-1
# Work on task 1
```

**SSH Connection 2:**
```bash
ssh mdoehler@server
claude-session ssh-test-2
# Work on task 2
```

**SSH Connection 3:**
```bash
ssh mdoehler@server
claude-session-list
# Verify both ssh-test-1 and ssh-test-2 are listed
```

**Expected Result:** ✅ Each SSH connection can run independent sessions

### Automated Test Suite

Create test automation script at `~/.claude/bin/test-sessions.sh`:

```bash
#!/bin/bash
#
# test-sessions.sh - Automated test suite for session isolation
#

set -euo pipefail

TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_func="$2"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "TEST: $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if $test_func; then
        echo "✅ PASSED: $test_name"
        ((TESTS_PASSED++))
    else
        echo "❌ FAILED: $test_name"
        ((TESTS_FAILED++))
    fi
    echo
}

test_session_creation() {
    local session_id=$(uuidgen | tr '[:upper:]' '[:lower:]')
    mkdir -p "$HOME/.claude/sessions/$session_id"
    [[ -d "$HOME/.claude/sessions/$session_id" ]]
}

test_directory_structure() {
    local session_id=$(uuidgen | tr '[:upper:]' '[:lower:]')
    mkdir -p "$HOME/.claude/sessions/$session_id"/{session-env,todos,debug}

    [[ -d "$HOME/.claude/sessions/$session_id/session-env" ]] && \
    [[ -d "$HOME/.claude/sessions/$session_id/todos" ]] && \
    [[ -d "$HOME/.claude/sessions/$session_id/debug" ]]
}

test_registry_operations() {
    # Test registry read
    [[ -f "$HOME/.claude/sessions/.registry" ]]
}

test_shared_resources() {
    # Verify shared directories exist
    [[ -d "$HOME/.claude/skills" ]] && \
    [[ -d "$HOME/.claude/agents" ]] && \
    [[ -d "$HOME/.claude/commands" ]]
}

# Run tests
run_test "Session Creation" test_session_creation
run_test "Directory Structure" test_directory_structure
run_test "Registry Operations" test_registry_operations
run_test "Shared Resources" test_shared_resources

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"
echo "Total:  $((TESTS_PASSED + TESTS_FAILED))"
echo

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo "✅ ALL TESTS PASSED"
    exit 0
else
    echo "❌ SOME TESTS FAILED"
    exit 1
fi
```

---

## Performance Considerations

### Resource Usage Per Session

Each Claude Code session consumes:

```
┌────────────────────────────────────────────┐
│ Resource Usage per Session (Approximate)   │
├────────────────────────────────────────────┤
│ Memory (RAM):         200-500 MB           │
│ CPU (idle):           1-5%                 │
│ CPU (active):         20-50%               │
│ Disk I/O:             Low-Medium           │
│ Network:              API calls only       │
│ Open Files:           50-100 descriptors   │
│ MCP Servers:          3-5 processes        │
│ Total Processes:      5-10 per session     │
└────────────────────────────────────────────┘
```

### Scaling Recommendations

**Server Specifications:**

```
┌─────────────────────────┬─────────────────────────────────────┐
│ Sessions                │ Recommended Server Specs            │
├─────────────────────────┼─────────────────────────────────────┤
│ 1-3 sessions            │ 4 GB RAM, 2 CPU cores               │
│ 4-8 sessions            │ 8 GB RAM, 4 CPU cores               │
│ 9-15 sessions           │ 16 GB RAM, 8 CPU cores              │
│ 16-30 sessions          │ 32 GB RAM, 16 CPU cores             │
└─────────────────────────┴─────────────────────────────────────┘
```

**Practical Limits:**

- **Conservative**: 5-10 parallel sessions on typical server (8 GB RAM)
- **Aggressive**: 15-20 parallel sessions on beefy server (16+ GB RAM)
- **Enterprise**: 30+ sessions requires dedicated infrastructure (32+ GB RAM)

### Performance Optimization Tips

1. **Session Cleanup**: Regularly clean up inactive sessions
   ```bash
   # Automated cleanup via cron
   0 2 * * * /home/UserID/.claude/bin/claude-session-cleanup --days 30
   ```

2. **MCP Server Optimization**: Disable unused MCP servers
   ```json
   {
     "enabledMcpjsonServers": [
       // Only enable what you need
       "powerpoint-server"
     ]
   }
   ```

3. **Session History Rotation**: Archive old conversation history
   ```bash
   # Archive sessions older than 90 days
   find "$HOME/.claude/sessions" -name "history.jsonl" -mtime +90 \
     -exec gzip {} \;
   ```

4. **Monitoring**: Track session resource usage
   ```bash
   # Monitor Claude processes
   watch -n 5 'ps aux | grep claude | grep -v grep'

   # Monitor disk usage
   du -sh "$HOME/.claude/sessions/"
   ```

### Disk Space Management

**Estimated Disk Usage:**

```
┌─────────────────────────────────────────────────────────┐
│ Component              │ Size per Session  │ Growth Rate│
├────────────────────────┼───────────────────┼────────────┤
│ history.jsonl          │ 50 KB - 5 MB      │ ~10 KB/msg │
│ session-env/           │ 1-10 MB           │ Stable     │
│ todos/                 │ 10-100 KB         │ Stable     │
│ shell-snapshots/       │ 1-50 MB           │ ~100 KB/cmd│
│ file-history/          │ 10-500 MB         │ Per edit   │
│ debug/                 │ 1-100 MB          │ ~1 MB/day  │
│ mcp-state/             │ 1-50 MB           │ Variable   │
├────────────────────────┼───────────────────┼────────────┤
│ Total per session      │ ~100 MB - 1 GB    │            │
└─────────────────────────────────────────────────────────┘
```

**Disk Space Planning:**

- **10 active sessions**: ~1-10 GB
- **50 archived sessions**: ~5-50 GB
- **Recommendation**: 50-100 GB dedicated to `.claude/sessions/`

---

## Security Considerations

### Access Control

1. **Session Directory Permissions**

```bash
# Ensure proper permissions
chmod 700 "$HOME/.claude/sessions"  # Only owner can access
chmod 600 "$HOME/.claude/.credentials.json"  # Credentials protected
```

2. **Multi-User Considerations**

If multiple users share the same server:

```bash
# Each user has their own .claude directory
/home/user1/.claude/
/home/user2/.claude/

# No cross-user access possible
```

3. **Credential Isolation**

- API credentials in `~/.claude/.credentials.json` are shared across all sessions
- Consider using different API keys per project if needed

### Data Privacy

1. **Sensitive Data in Sessions**

- Each session's `history.jsonl` contains full conversation history
- Be mindful of storing sensitive data in conversations
- Consider encrypting session directories for highly sensitive work

2. **Log Sanitization**

```bash
# Sanitize logs before sharing
grep -v "password\|token\|secret" \
  "$HOME/.claude/sessions/$SESSION_ID/session.log" > sanitized.log
```

3. **Session Cleanup**

```bash
# Securely delete old sessions
SESSION_ID="<old-session-id>"
shred -uvz "$HOME/.claude/sessions/$SESSION_ID/history.jsonl"
rm -rf "$HOME/.claude/sessions/$SESSION_ID"
```

### SSH Security

1. **SSH Key-Based Authentication**: Use SSH keys instead of passwords

2. **Session Hijacking Prevention**: Each session is tied to SSH connection metadata

3. **Audit Logging**
```bash
# Log all session creations
cat >> "$HOME/.claude/sessions/audit.log" << EOF
$(date -u +%Y-%m-%dT%H:%M:%SZ) | User: $USER | SSH: $SSH_CLIENT | Session: $SESSION_ID
EOF
```

---

## Appendix

### A. Environment Variable Reference

Complete list of environment variables used:

| Variable | Description | Scope | Example |
|----------|-------------|-------|---------|
| `CLAUDE_SESSION_ID` | Unique session identifier | Session | `64448612-0e5c-4075-8d92-4cb54e7e0567` |
| `CLAUDE_SESSION_DIR` | Session data directory | Session | `~/.claude/sessions/<UUID>` |
| `CLAUDE_SESSION_NAME` | Human-readable session name | Session | `netbox-integration` |
| `CLAUDE_HISTORY_FILE` | Session conversation history | Session | `$SESSION_DIR/history.jsonl` |
| `CLAUDE_HISTORY_LOCK` | History lock file | Session | `$SESSION_DIR/history.lock` |
| `CLAUDE_SESSION_ENV_DIR` | Session environment directory | Session | `$SESSION_DIR/session-env` |
| `CLAUDE_TODOS_DIR` | Session todos directory | Session | `$SESSION_DIR/todos` |
| `CLAUDE_SHELL_SNAPSHOTS_DIR` | Shell state directory | Session | `$SESSION_DIR/shell-snapshots` |
| `CLAUDE_FILE_HISTORY_DIR` | File edit history directory | Session | `$SESSION_DIR/file-history` |
| `CLAUDE_DEBUG_DIR` | Debug logs directory | Session | `$SESSION_DIR/debug` |
| `CLAUDE_PROJECT_DIR` | Project-specific data | Session | `$SESSION_DIR/project` |
| `CLAUDE_MCP_STATE_DIR` | MCP server state directory | Session | `$SESSION_DIR/mcp-state` |
| `CLAUDE_SKILLS_DIR` | Skills directory (shared) | Global | `~/.claude/skills` |
| `CLAUDE_AGENTS_DIR` | Agents directory (shared) | Global | `~/.claude/agents` |
| `CLAUDE_COMMANDS_DIR` | Commands directory (shared) | Global | `~/.claude/commands` |
| `CLAUDE_PLUGINS_DIR` | Plugins directory (shared) | Global | `~/.claude/plugins` |

### B. File Structure Reference

Complete file structure with descriptions:

```
~/.claude/
├── [SHARED] - Never modified during sessions
│   ├── skills/                  # Skill definitions
│   ├── agents/                  # Custom agent configs
│   ├── commands/                # Slash commands
│   ├── plugins/                 # Plugin definitions
│   ├── settings.json            # Base settings
│   ├── settings.local.json      # Local overrides
│   ├── .credentials.json        # API credentials
│   └── user-instructions.md     # User preferences
│
├── [SESSION-ISOLATED] - Per session
│   └── sessions/
│       ├── .registry            # Session registry
│       ├── active/              # Active session symlinks
│       └── {SESSION_ID}/
│           ├── metadata.json    # Session metadata
│           ├── session.log      # Activity log
│           ├── history.jsonl    # Conversation history
│           ├── history.lock     # Lock file
│           ├── session-env/     # Environment data
│           ├── todos/           # Todo lists
│           ├── shell-snapshots/ # Bash state
│           ├── file-history/    # File edits
│           ├── debug/           # Debug logs
│           ├── project/         # Project data
│           └── mcp-state/       # MCP server state
│
└── [MANAGEMENT] - Session tools
    └── bin/
        ├── claude-session       # Session launcher
        ├── claude-session-list  # List sessions
        ├── claude-session-cleanup # Cleanup tool
        └── test-sessions.sh     # Test suite
```

### C. Migration from Single to Multi-Session

If you have an existing Claude Code installation with data:

```bash
#!/bin/bash
# migrate-to-sessions.sh

CLAUDE_ROOT="$HOME/.claude"
DEFAULT_SESSION_ID="00000000-0000-0000-0000-000000000000"
DEFAULT_SESSION_DIR="$CLAUDE_ROOT/sessions/$DEFAULT_SESSION_ID"

echo "Migrating existing Claude data to session structure..."

# Create session structure
mkdir -p "$CLAUDE_ROOT/sessions"
mkdir -p "$DEFAULT_SESSION_DIR"

# Move session-specific data to default session
[[ -f "$CLAUDE_ROOT/history.jsonl" ]] && \
  mv "$CLAUDE_ROOT/history.jsonl" "$DEFAULT_SESSION_DIR/"

[[ -f "$CLAUDE_ROOT/history.lock" ]] && \
  mv "$CLAUDE_ROOT/history.lock" "$DEFAULT_SESSION_DIR/"

[[ -d "$CLAUDE_ROOT/session-env" ]] && \
  mv "$CLAUDE_ROOT/session-env" "$DEFAULT_SESSION_DIR/"

[[ -d "$CLAUDE_ROOT/todos" ]] && \
  mv "$CLAUDE_ROOT/todos" "$DEFAULT_SESSION_DIR/"

[[ -d "$CLAUDE_ROOT/shell-snapshots" ]] && \
  mv "$CLAUDE_ROOT/shell-snapshots" "$DEFAULT_SESSION_DIR/"

[[ -d "$CLAUDE_ROOT/file-history" ]] && \
  mv "$CLAUDE_ROOT/file-history" "$DEFAULT_SESSION_DIR/"

[[ -d "$CLAUDE_ROOT/debug" ]] && \
  mv "$CLAUDE_ROOT/debug" "$DEFAULT_SESSION_DIR/"

# Create other directories
mkdir -p "$DEFAULT_SESSION_DIR/project"
mkdir -p "$DEFAULT_SESSION_DIR/mcp-state"

# Create metadata
cat > "$DEFAULT_SESSION_DIR/metadata.json" << EOF
{
  "sessionId": "$DEFAULT_SESSION_ID",
  "sessionName": "default (migrated)",
  "userId": "$USER",
  "workingDirectory": "$HOME",
  "startTime": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "migrated",
  "model": "claude-sonnet-4-5-20250929"
}
EOF

# Create registry
cat > "$CLAUDE_ROOT/sessions/.registry" << EOF
{
  "version": "1.0",
  "sessions": {
    "$DEFAULT_SESSION_ID": {
      "sessionName": "default (migrated)",
      "userId": "$USER",
      "status": "migrated",
      "startTime": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    }
  }
}
EOF

echo "Migration complete!"
echo "Default session ID: $DEFAULT_SESSION_ID"
echo "You can now use: claude-session --resume $DEFAULT_SESSION_ID"
```

### D. Additional Resources

**Official Documentation:**
- Claude Code Docs: https://code.claude.com/docs
- MCP Specification: https://modelcontextprotocol.io/
- Anthropic API Docs: https://docs.anthropic.com/

**Community Resources:**
- GitHub Discussions: Various claude-conductor and session management tools
- ccswitch: Tool for managing multiple Claude sessions (reference for ideas)

**Related Tools:**
- `tmux`: Terminal multiplexer for persistent sessions
- `screen`: Alternative terminal multiplexer
- `byobu`: Enhanced terminal multiplexer

---

## Conclusion

This architecture provides a robust, scalable solution for running multiple parallel Claude Code sessions via SSH with complete isolation and shared resource access. The design leverages environment variables and directory-based separation to ensure no cross-session interference while maintaining ease of use.

**Key Achievements:**
- ✅ Complete session isolation
- ✅ Shared skills, agents, and commands
- ✅ SSH multi-connection support
- ✅ MCP server per-session instances
- ✅ Simple management tools
- ✅ Comprehensive testing procedures
- ✅ Production-ready design

**Next Steps:**
1. Follow implementation plan (Phases 1-6)
2. Run test suite to validate
3. Monitor performance with real workloads
4. Iterate based on usage patterns

For questions or issues, refer to the Troubleshooting Guide or create custom diagnostic scripts based on the templates provided.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-08
**Maintainer:** mdoehler
**License:** Internal Use
