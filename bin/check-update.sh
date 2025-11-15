#!/bin/bash
# Claude Code Auto-Update Check Script
set -euo pipefail

CLAUDE_ROOT="${HOME}/.claude"
UPDATE_LOG="${CLAUDE_ROOT}/update.log"
LOCK_FILE="${CLAUDE_ROOT}/update.lock"

log_update() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$UPDATE_LOG"
}

check_active_sessions() {
    # Check if any Claude sessions are running
    if pgrep -u "$(whoami)" -f "claude.*--dangerously-skip-permissions" > /dev/null 2>&1; then
        return 0  # Sessions found
    fi
    return 1  # No sessions
}

get_current_version() {
    claude --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' || echo "0.0.0"
}

get_latest_version() {
    npm view @anthropic-ai/claude-code version 2>/dev/null || echo "0.0.0"
}

compare_versions() {
    local current="$1"
    local latest="$2"
    
    if [ "$current" = "$latest" ]; then
        return 1  # Same version
    fi
    
    # Simple version comparison (assumes semver)
    if [ "$(printf '%s\n' "$current" "$latest" | sort -V | head -n1)" = "$current" ] && [ "$current" != "$latest" ]; then
        return 0  # Update available
    fi
    
    return 1  # No update needed
}

perform_update() {
    log_update "Starting update from $1 to $2"
    
    # Check if we have permissions to update (running as root or with sudo)
    if [ "$EUID" -eq 0 ]; then
        # Running as root
        if npm install -g @anthropic-ai/claude-code@latest; then
            log_update "✓ Successfully updated Claude Code to $2"
            return 0
        else
            log_update "✗ Update failed"
            return 1
        fi
    elif sudo -n true 2>/dev/null; then
        # Can run sudo without password
        if sudo npm install -g @anthropic-ai/claude-code@latest; then
            log_update "✓ Successfully updated Claude Code to $2"
            return 0
        else
            log_update "✗ Update failed"
            return 1
        fi
    else
        log_update "⚠ Insufficient permissions to update (need root or sudo)"
        log_update "→ Please run manually: sudo npm install -g @anthropic-ai/claude-code@latest"
        return 1
    fi
}

main() {
    mkdir -p "$CLAUDE_ROOT"
    
    # Acquire lock to prevent concurrent updates
    if [ -f "$LOCK_FILE" ]; then
        log_update "Update already in progress (lock file exists)"
        exit 0
    fi
    
    touch "$LOCK_FILE"
    trap 'rm -f "$LOCK_FILE"' EXIT
    
    # Get versions
    CURRENT_VERSION=$(get_current_version)
    LATEST_VERSION=$(get_latest_version)
    
    log_update "Version check: current=$CURRENT_VERSION, latest=$LATEST_VERSION"
    
    # Check if update is needed
    if ! compare_versions "$CURRENT_VERSION" "$LATEST_VERSION"; then
        log_update "✓ Claude Code is up to date ($CURRENT_VERSION)"
        exit 0
    fi
    
    log_update "Update available: $CURRENT_VERSION → $LATEST_VERSION"
    
    # Safety check: Don't update if sessions are running
    if check_active_sessions; then
        log_update "⚠ Skipping update: Active Claude sessions detected"
        log_update "→ Update will be applied when no sessions are running"
        exit 0
    fi
    
    # Perform the update
    perform_update "$CURRENT_VERSION" "$LATEST_VERSION"
}

main "$@"
