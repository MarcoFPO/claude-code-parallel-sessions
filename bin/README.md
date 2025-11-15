# Claude Code Parallel Sessions - Implementation Scripts

This directory contains the production-ready implementation scripts for the parallel Claude Code sessions system.

## Scripts Overview

### 1. `claude-session` (Bash, 21 lines)
**Main session launcher with auto-update integration**

- Creates isolated session directories
- Sets up proper environment variables for session isolation
- Launches Claude Code with dedicated configuration directory
- Triggers background update check (non-blocking)

**Key Feature**: 1-line fix for session isolation:
```bash
export CLAUDE_CONFIG_DIR="$session_dir"  # Claude reads this variable
```

### 2. `check-update.sh` (Bash, 42 lines)
**Auto-update system for Claude Code**

- Checks npm registry for latest Claude Code version
- Installs updates automatically when no sessions are running
- Session-safe: Never updates during active sessions
- Full audit trail in `~/.claude/update.log`

**Safety Features**:
- Lock file prevents concurrent updates
- `pgrep` check ensures no active sessions
- Non-blocking execution (runs in background)
- Requires sudo/root for global npm install

### 3. `cleanup-sessions.py` (Python, 230+ lines)
**Session maintenance tool**

- Removes old, empty, or orphaned session directories
- Dry-run mode for safe preview
- Configurable age threshold (default: 7 days)
- Zero external dependencies (stdlib only)
- Never deletes registered/active sessions

**Usage Examples**:
```bash
# Preview what would be deleted
python3 cleanup-sessions.py --dry-run

# Clean up sessions older than 7 days
python3 cleanup-sessions.py

# Clean up sessions older than 30 days
python3 cleanup-sessions.py --days 30
```

## Installation

### Automated Installation

Copy all scripts to your Claude Code installation:

```bash
# Copy scripts to ~/.claude/bin/
mkdir -p ~/.claude/bin
cp claude-session ~/.claude/bin/
cp check-update.sh ~/.claude/bin/
cp cleanup-sessions.py ~/.claude/bin/

# Make executable
chmod +x ~/.claude/bin/claude-session
chmod +x ~/.claude/bin/check-update.sh
chmod +x ~/.claude/bin/cleanup-sessions.py
```

### Configure sudo for Auto-Updates (Optional)

To enable passwordless auto-updates:

```bash
# Create sudoers entry for npm updates
echo "$(whoami) ALL=(ALL) NOPASSWD: /usr/bin/npm install -g @anthropic-ai/claude-code@*" | \
    sudo tee /etc/sudoers.d/claude-update

# Verify
sudo visudo -c
```

### Verify Installation

```bash
# Test session launcher
~/.claude/bin/claude-session --help

# Test cleanup tool
python3 ~/.claude/bin/cleanup-sessions.py --dry-run

# Check auto-update log
tail -f ~/.claude/update.log
```

## Directory Structure

After installation, your `~/.claude/` directory will have this structure:

```
~/.claude/
├── bin/
│   ├── claude-session        # Session launcher
│   ├── check-update.sh        # Auto-update system
│   └── cleanup-sessions.py    # Maintenance tool
├── sessions/
│   ├── {uuid-1}/              # Session 1 (isolated)
│   │   ├── history.jsonl      # Session-specific history
│   │   ├── todos/
│   │   ├── shell-snapshots/
│   │   └── ...
│   ├── {uuid-2}/              # Session 2 (isolated)
│   └── active/                # Symlinks to active sessions
├── skills/                    # SHARED across all sessions
├── agents/                    # SHARED across all sessions
├── commands/                  # SHARED across all sessions
├── plugins/                   # SHARED across all sessions
└── update.log                 # Auto-update audit trail
```

## Session Isolation

Each session gets:
- **Isolated history**: Separate `history.jsonl` per session
- **Isolated state**: Separate todos, shell snapshots, project data
- **Shared resources**: All sessions share skills, agents, commands, plugins

This is achieved by setting `CLAUDE_CONFIG_DIR` to the session-specific directory:
```bash
export CLAUDE_CONFIG_DIR="$HOME/.claude/sessions/{uuid}"
```

Claude Code then writes all session-specific data to this directory instead of the default `~/.claude/` location.

## Auto-Update System

The auto-update system runs automatically when starting a new session:

1. **Session starts** → `claude-session` script
2. **Background check** → `check-update.sh` (non-blocking)
3. **Version comparison** → npm registry vs. local version
4. **Update decision**:
   - No sessions running? → Install update
   - Sessions running? → Skip (try next time)
5. **Logging** → All actions logged to `~/.claude/update.log`

**View update log**:
```bash
tail -f ~/.claude/update.log
```

## Maintenance

### Regular Cleanup

Schedule periodic cleanup of old sessions:

```bash
# Add to crontab (weekly cleanup)
0 0 * * 0 python3 ~/.claude/bin/cleanup-sessions.py --days 30
```

### Monitor Sessions

Check active sessions:
```bash
ls -la ~/.claude/sessions/active/
```

Check session sizes:
```bash
du -sh ~/.claude/sessions/*/ | sort -h
```

## Troubleshooting

### Session not isolated
**Problem**: Multiple sessions write to same history

**Solution**: Check environment variable
```bash
echo $CLAUDE_CONFIG_DIR
# Should show: /home/UserID/.claude/sessions/{uuid}
```

### Updates not working
**Problem**: Permission denied for npm install

**Solution**: Configure sudo (see above) or run manually:
```bash
sudo npm install -g @anthropic-ai/claude-code@latest
```

### Too many old sessions
**Problem**: Disk space filling up

**Solution**: Run cleanup tool
```bash
python3 ~/.claude/bin/cleanup-sessions.py
```

## Development

### Testing Scripts Locally

```bash
# Test session launcher (dry-run)
bash -x ./claude-session --help

# Test cleanup tool (dry-run)
python3 ./cleanup-sessions.py --dry-run

# Test update check
bash -x ./check-update.sh
```

### Customization

All scripts use environment variables and can be customized:

- `CLAUDE_ROOT`: Claude Code root directory (default: `~/.claude`)
- `SESSIONS_DIR`: Sessions directory (default: `$CLAUDE_ROOT/sessions`)
- `CLAUDE_BIN`: Claude Code binary path (default: auto-detect)

## Architecture

For complete architectural documentation, see:
- [Architecture Document](../docs/claude-code-parallel-sessions-architecture.md)
- [Quick Start Guide](../docs/claude-sessions-quick-start.md)

## License

Part of the Claude Code Parallel Sessions project.

---

**Version**: 1.0
**Last Updated**: 2025-11-15
**Status**: Production Ready
