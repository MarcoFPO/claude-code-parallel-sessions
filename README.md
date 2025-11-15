# Claude Code Parallel Sessions

Vollständig implementierte und getestete Architektur für parallele Claude Code Sessions auf LXC 122.

## Übersicht

Dieses Projekt ermöglicht das Ausführen mehrerer paralleler Claude Code Sessions via SSH mit vollständiger Session-Isolation und gemeinsam genutzten Ressourcen (Skills, Agents, Commands).

## Status

- ✅ **Production Ready** auf LXC 122 (10.1.1.184)
- ✅ Architektur vollständig implementiert
- ✅ Session-Isolation getestet und verifiziert
- ✅ Auto-Update-System integriert
- ✅ Parallel-Session-Tests erfolgreich

## Zielsystem

- **Host**: LXC 122 (RClaude)
- **IP**: 10.1.1.184
- **Zugriff**: SSH via `root@10.1.1.184`
- **User**: mdoehler
- **Claude Version**: 2.0.42 (auto-update enabled)

## Features

### Session-Isolation

Jede Session erhält:
- Eigene `history.jsonl` (vollständig isoliert)
- Separate Todo-Listen und Shell-State
- Unabhängige Projekt-Daten
- Isolierte Debug-Logs

### Gemeinsame Ressourcen

Alle Sessions teilen:
- **73 Skills** in `~/.claude/skills/`
- **Custom Agents** in `~/.claude/agents/`
- **Slash Commands** in `~/.claude/commands/`
- **Plugins** in `~/.claude/plugins/`

### Auto-Update-System

- Automatische Update-Checks bei Session-Start
- Non-blocking Background-Updates
- Session-safe (keine Updates bei aktiven Sessions)
- Audit-Trail in `~/.claude/update.log`

## Verwendung

### Session starten

```bash
# SSH zu LXC 122
ssh root@10.1.1.184

# Als mdoehler-User
su - mdoehler

# Session starten
/home/mdoehler/.claude/bin/claude-session
```

### Parallele Sessions

```bash
# Terminal 1: Session 1
ssh root@10.1.1.184
su - mdoehler
/home/mdoehler/.claude/bin/claude-session

# Terminal 2: Session 2 (gleichzeitig)
ssh root@10.1.1.184
su - mdoehler
/home/mdoehler/.claude/bin/claude-session
```

Beide Sessions sind vollständig isoliert:
- Separate History-Dateien
- Keine Interferenz
- Geteilte Skills/Agents

### Update-Log überwachen

```bash
tail -f /home/mdoehler/.claude/update.log
```

## Architektur

### Verzeichnisstruktur

```
/home/mdoehler/.claude/
├── bin/
│   ├── claude-session       # Session-Launcher (mit Auto-Update)
│   ├── check-update.sh      # Auto-Update-Script
│   └── cleanup-sessions.py  # Session-Wartung
├── sessions/
│   ├── {uuid-1}/            # Session 1 (isoliert)
│   │   ├── history.jsonl
│   │   ├── todos/
│   │   └── ...
│   └── {uuid-2}/            # Session 2 (isoliert)
│       ├── history.jsonl
│       ├── todos/
│       └── ...
├── skills/                  # SHARED (73 Skills)
├── agents/                  # SHARED
├── commands/                # SHARED
└── plugins/                 # SHARED
```

### Session-Launcher-Ablauf

```
User startet Session
    ↓
claude-session
    ├─→ check-update.sh (background, non-blocking)
    │   ├─ Version-Check
    │   ├─ Update falls verfügbar
    │   └─ Log zu update.log
    └─→ Claude Code starten
        └─ CLAUDE_CONFIG_DIR="~/.claude/sessions/{uuid}"
```

## Implementierungs-Details

### Session-Isolation Fix

**Problem**: Claude Code schrieb ursprünglich in root-level `history.jsonl`

**Lösung**: 1-Zeilen-Fix im Session-Launcher
```bash
export CLAUDE_CONFIG_DIR="$session_dir"  # Claude liest diese Variable
```

**Resultat**: Jede Session schreibt in eigenes Verzeichnis

### Auto-Update-Mechanismus

**Dateien**:
- `check-update.sh` (42 Zeilen): Update-Logik
- `claude-session` (21 Zeilen): Launcher mit Update-Hook

**Features**:
- Prüft bei jedem Start auf Updates
- Installiert automatisch (wenn keine Sessions laufen)
- 5-Sekunden-Timeout für npm-Registry
- Vollständiges Logging

**Safety**:
```bash
# Kein Update bei aktiven Sessions
if pgrep -f "claude.*code" > /dev/null; then
    exit 0  # Skip update
fi
```

## Getestete Funktionalität

### Parallel-Session-Test ✅

- 2 Sessions gleichzeitig gestartet
- Separate History-Dateien verifiziert (unterschiedliche Inodes)
- Keine Interferenz zwischen Sessions
- Default-Verzeichnis unberührt

### Shared Resources Test ✅

- 73 Skills in shared Location
- Keine Duplikation in Session-Verzeichnissen
- Korrekte Berechtigungen
- Architektur-konform

### Auto-Update Test ✅

- Update 2.0.36 → 2.0.42 erfolgreich
- Safety-Check funktioniert (kein Update bei aktiver Session)
- Logging komplett
- Non-blocking Integration

## Performance

**Ressourcen pro Session**:
- RAM: ~200-500 MB
- Disk: ~10-50 MB (wächst mit History)

**Empfohlene Limits**:
- Max. 2-3 parallele Sessions (LXC hat 1 GB RAM)
- Regelmäßige Cleanup alter Sessions

**Session-Wartung**:
```bash
# Alte/leere Sessions bereinigen
python3 /home/mdoehler/.claude/bin/cleanup-sessions.py

# Dry-run
python3 /home/mdoehler/.claude/bin/cleanup-sessions.py --dry-run
```

## Dokumentation

### Architektur-Dokumentation

- **[Architecture Document](docs/claude-code-parallel-sessions-architecture.md)** (75 KB)
  - Vollständige technische Architektur
  - Design-Entscheidungen
  - Implementierungs-Details

- **[Quick Start Guide](docs/claude-sessions-quick-start.md)** (7 KB)
  - Schnelleinstieg
  - Wichtigste Befehle
  - Troubleshooting

### Implementation Report

- **[LXC122 Implementation Report](LXC122_IMPLEMENTATION_REPORT.md)** (6.4 KB)
  - Implementierungs-Status: 95% komplett
  - Test-Ergebnisse (alle PASS)
  - Deployment-Details
  - Nächste Schritte (optional)

## Troubleshooting

### Session startet nicht

**Problem**: Session-Launcher nicht ausführbar

**Lösung**:
```bash
chmod +x /home/mdoehler/.claude/bin/claude-session
chmod +x /home/mdoehler/.claude/bin/check-update.sh
```

### History wird nicht isoliert

**Problem**: Beide Sessions schreiben in dieselbe Datei

**Lösung**: Prüfe Umgebungsvariable
```bash
# In Claude-Session:
echo $CLAUDE_CONFIG_DIR
# Sollte zeigen: /home/mdoehler/.claude/sessions/{uuid}
```

### Updates schlagen fehl

**Problem**: Permissions für npm global install

**Lösung**: Sudo-Konfiguration prüfen
```bash
cat /etc/sudoers.d/claude-update
# Sollte enthalten:
# mdoehler ALL=(ALL) NOPASSWD: /usr/bin/npm install -g @anthropic-ai/claude-code@*
```

### Zu viele alte Sessions

**Problem**: Sessions-Verzeichnis wird zu groß

**Lösung**: Cleanup-Tool nutzen
```bash
python3 /home/mdoehler/.claude/bin/cleanup-sessions.py
```

## Sicherheit

- Jede Session hat isolierte Historie (kein Cross-Session-Data-Leak)
- Gemeinsame Skills sind read-only
- Auto-Updates nur bei sudo-Berechtigung
- Session-Safe Updates (keine laufenden Sessions betroffen)

## Projekt-Historie

### 2025-11-08: Initial Design
- Architektur-Dokumentation erstellt
- Quick Start Guide geschrieben

### 2025-11-15: Implementation
- Session-Isolation implementiert (1-Zeilen-Fix)
- Registry-Cleanup durchgeführt
- Auto-Update-System integriert
- Parallel-Session-Tests erfolgreich
- Production-Ready Status erreicht

## Verwandte Projekte

- [claude-code-api-local](../claude-code-api-local/) - Node.js API Server für Claude
- [claude-wrapper](../claude-wrapper/) - FastAPI-Wrapper mit Budget-Tracking
- [claude-code-context-cleanup](../claude-code-context-cleanup/) - Context-Management Tools

## Autor

Backend System Architect

---

**Letzte Aktualisierung**: 2025-11-15
**Status**: Production Ready
**Version**: 1.0
