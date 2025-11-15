#!/usr/bin/env python3
"""
Claude Code Session Cleanup Tool

Removes old, empty, or orphaned session directories from ~/.claude/sessions/
to free up disk space and maintain a clean session registry.

Features:
- Dry-run mode (--dry-run) to preview changes
- Configurable age threshold (--days)
- Zero external dependencies (stdlib only)
- Safe: Never deletes registered/active sessions
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


def get_claude_root():
    """Get Claude Code root directory."""
    return Path.home() / ".claude"


def get_sessions_dir():
    """Get sessions directory."""
    return get_claude_root() / "sessions"


def get_active_sessions_dir():
    """Get active sessions directory."""
    return get_sessions_dir() / "active"


def is_session_registered(session_id: str) -> bool:
    """Check if session is registered (has symlink in active/)."""
    active_link = get_active_sessions_dir() / session_id
    return active_link.exists()


def get_session_age_days(session_dir: Path) -> int:
    """Get age of session directory in days."""
    mtime = session_dir.stat().st_mtime
    age = datetime.now() - datetime.fromtimestamp(mtime)
    return age.days


def is_session_empty(session_dir: Path) -> bool:
    """Check if session directory is empty or contains only empty files."""
    history_file = session_dir / "history.jsonl"

    # Session is empty if history.jsonl doesn't exist or is empty
    if not history_file.exists():
        return True

    if history_file.stat().st_size == 0:
        return True

    # Check if history has any actual content (not just empty lines)
    try:
        with open(history_file, 'r') as f:
            for line in f:
                if line.strip():
                    return False  # Has content
        return True  # Only empty lines
    except Exception:
        return True  # Assume empty on error


def get_session_size_mb(session_dir: Path) -> float:
    """Get total size of session directory in MB."""
    total_size = 0
    for entry in session_dir.rglob('*'):
        if entry.is_file():
            total_size += entry.stat().st_size
    return total_size / (1024 * 1024)


def find_cleanable_sessions(min_age_days: int = 7):
    """
    Find session directories that can be cleaned up.

    Returns:
        List of tuples: (session_dir, reason, age_days, size_mb)
    """
    sessions_dir = get_sessions_dir()
    if not sessions_dir.exists():
        return []

    cleanable = []

    for session_dir in sessions_dir.iterdir():
        if not session_dir.is_dir():
            continue

        session_id = session_dir.name

        # Skip special directories
        if session_id in ['active', 'templates']:
            continue

        # Never delete registered/active sessions
        if is_session_registered(session_id):
            continue

        age_days = get_session_age_days(session_dir)
        size_mb = get_session_size_mb(session_dir)

        # Check if session is old enough
        if age_days < min_age_days:
            continue

        # Check cleanup criteria
        if is_session_empty(session_dir):
            reason = f"Empty session (older than {min_age_days} days)"
            cleanable.append((session_dir, reason, age_days, size_mb))
        elif age_days > 30:  # Very old sessions
            reason = f"Very old session ({age_days} days)"
            cleanable.append((session_dir, reason, age_days, size_mb))

    return cleanable


def delete_session(session_dir: Path):
    """Delete session directory and all contents."""
    import shutil
    shutil.rmtree(session_dir)


def format_size(size_mb: float) -> str:
    """Format size in human-readable format."""
    if size_mb < 1:
        return f"{size_mb * 1024:.1f} KB"
    return f"{size_mb:.1f} MB"


def main():
    parser = argparse.ArgumentParser(
        description="Clean up old Claude Code session directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run (preview changes)
  %(prog)s --dry-run

  # Clean up sessions older than 7 days
  %(prog)s

  # Clean up sessions older than 30 days
  %(prog)s --days 30
        """
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without deleting anything'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Minimum age in days for cleanup (default: 7)'
    )

    args = parser.parse_args()

    # Find cleanable sessions
    cleanable = find_cleanable_sessions(min_age_days=args.days)

    if not cleanable:
        print(f"✓ No sessions to clean up (older than {args.days} days)")
        return 0

    # Display summary
    total_size = sum(size for _, _, _, size in cleanable)
    print(f"\nFound {len(cleanable)} session(s) to clean up:")
    print(f"Total space to free: {format_size(total_size)}\n")

    # Display details
    for session_dir, reason, age_days, size_mb in cleanable:
        print(f"  • {session_dir.name}")
        print(f"    Reason: {reason}")
        print(f"    Size: {format_size(size_mb)}")
        print()

    if args.dry_run:
        print("DRY RUN: No changes made. Remove --dry-run to delete.")
        return 0

    # Confirm deletion
    try:
        response = input(f"Delete {len(cleanable)} session(s)? [y/N] ")
        if response.lower() != 'y':
            print("Aborted.")
            return 0
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        return 1

    # Delete sessions
    deleted_count = 0
    for session_dir, _, _, _ in cleanable:
        try:
            delete_session(session_dir)
            print(f"✓ Deleted: {session_dir.name}")
            deleted_count += 1
        except Exception as e:
            print(f"✗ Failed to delete {session_dir.name}: {e}", file=sys.stderr)

    print(f"\n✓ Cleaned up {deleted_count}/{len(cleanable)} sessions")
    print(f"  Freed: {format_size(total_size)}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
