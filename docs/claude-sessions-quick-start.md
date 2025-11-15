# Claude Code Parallel Sessions - Quick Start Guide

**TL;DR:** Run multiple Claude Code sessions simultaneously via SSH without conflicts.

## One-Minute Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  SSH #1              SSH #2              SSH #3                  │
│    ↓                   ↓                   ↓                      │
│  Session A          Session B          Session C                 │
│  (Backend)          (Frontend)         (Docs)                    │
│    ↓                   ↓                   ↓                      │
│  Isolated           Isolated           Isolated                  │
│  History            History            History                   │
│  Todos              Todos              Todos                     │
│  State              State              State                     │
│                                                                   │
│  All share: Skills, Agents, Commands                             │
└─────────────────────────────────────────────────────────────────┘
```

## Installation (5 Minutes)

```bash
# 1. Create session directory structure
mkdir -p "$HOME/.claude/sessions"
mkdir -p "$HOME/.claude/bin"

# 2. Download management scripts (see full doc)
# Or create them manually following the architecture doc

# 3. Add to PATH
echo 'export PATH="$HOME/.claude/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 4. Create first session
claude-session my-first-session
```

## Basic Usage

### Start a New Session
```bash
# Named session
claude-session my-project

# Auto-named session
claude-session
```

### List Sessions
```bash
claude-session-list
```

### Resume a Session
```bash
claude-session --resume <SESSION_ID>
```

### Parallel Sessions (Different SSH Terminals)
```bash
# Terminal 1
ssh user@server
claude-session backend-work

# Terminal 2
ssh user@server
claude-session frontend-work

# Terminal 3
ssh user@server
claude-session docs-update
```

## How It Works

### Directory Structure

```
~/.claude/
├── skills/          → SHARED across all sessions
├── agents/          → SHARED
├── commands/        → SHARED
├── settings.json    → SHARED
└── sessions/        → ISOLATED per session
    ├── {UUID-1}/
    │   ├── history.jsonl
    │   ├── todos/
    │   └── ...
    ├── {UUID-2}/
    │   ├── history.jsonl
    │   ├── todos/
    │   └── ...
    └── {UUID-3}/
        ├── history.jsonl
        ├── todos/
        └── ...
```

### Key Isolation Points

Each session has its own:
- ✅ Conversation history
- ✅ Todo lists
- ✅ Shell state
- ✅ File edit history
- ✅ MCP server instances
- ✅ Debug logs

All sessions share:
- ✅ Skills (read-only)
- ✅ Custom agents (read-only)
- ✅ Slash commands (read-only)
- ✅ API credentials (read-only)

## Core Concept

**Environment Variables** control isolation:

```bash
CLAUDE_SESSION_ID="<unique-uuid>"
CLAUDE_SESSION_DIR="~/.claude/sessions/<uuid>"
CLAUDE_HISTORY_FILE="$CLAUDE_SESSION_DIR/history.jsonl"
# ... etc
```

Each session wrapper sets these variables, redirecting all writes to session-specific directories.

## Key Benefits

1. **No Conflicts**: Multiple SSH users can work simultaneously
2. **No Cross-Talk**: Sessions never interfere with each other
3. **Shared Resources**: All sessions use the same skills
4. **Full Isolation**: Each session maintains its own state
5. **Easy Management**: Simple CLI tools for session control

## Troubleshooting

### Sessions Don't Isolate
- Check environment variables: `echo $CLAUDE_SESSION_ID`
- Verify session directory exists: `ls ~/.claude/sessions/`

### History Conflicts
- Each session should have its own lock file
- Check: `ls ~/.claude/sessions/*/history.lock`

### MCP Server Issues
- Ensure MCP servers don't hardcode ports
- Use dynamic port allocation (port: 0)

## Performance

**Per Session Resource Usage:**
- RAM: 200-500 MB
- CPU: 1-50% (idle to active)
- Disk: ~100 MB - 1 GB over time

**Recommended Limits:**
- Light server (8 GB RAM): 5-10 sessions
- Medium server (16 GB RAM): 15-20 sessions
- Heavy server (32+ GB RAM): 30+ sessions

## Security

- Each user has own `~/.claude/` directory
- Sessions isolated per user
- No cross-user access possible
- Credentials shared across user's sessions (stored in `~/.claude/.credentials.json`)

## Full Documentation

See complete architecture document:
`/home/UserID/claude-code-parallel-sessions-architecture.md`

Contains:
- Detailed technical design
- Complete implementation plan
- Testing procedures
- Troubleshooting guide
- Performance tuning
- Security considerations

## Quick Reference Commands

```bash
# Session Management
claude-session <name>              # Create new session
claude-session --resume <id>       # Resume session
claude-session-list                # List all sessions
claude-session-cleanup             # Clean old sessions

# Aliases (after setup)
cs <name>                          # Create session
cs-list                            # List sessions
cs-resume <id>                     # Resume session
csn <name>                         # Create new named session
csl                                # Resume last session
```

## Architecture Overview

```
Session Wrapper (claude-session)
         ↓
   Set Environment Variables
   (CLAUDE_SESSION_ID, paths, etc.)
         ↓
   Launch Claude Code
   (--session-id <UUID>)
         ↓
   Claude Code Process
         ↓
   ┌──────────────┬──────────────┐
   ↓              ↓              ↓
Shared         Isolated       Isolated
Resources      Storage        MCP Servers
(skills,       (history,      (per session
 agents,        todos,         instances)
 commands)      state)
```

## Implementation Status

- [ ] Phase 1: Backup current setup
- [ ] Phase 2: Create directory structure
- [ ] Phase 3: Install management scripts
- [ ] Phase 4: Add shell integration
- [ ] Phase 5: Run test suite
- [ ] Phase 6: Document and train

Estimated total implementation time: **2-3 hours**

## Next Steps

1. Read full architecture document
2. Back up current `.claude/` directory
3. Follow implementation plan (Phases 1-6)
4. Test with 2 parallel sessions
5. Scale to production usage

---

**Document Version:** 1.0
**Created:** 2025-11-08
**Companion to:** claude-code-parallel-sessions-architecture.md
