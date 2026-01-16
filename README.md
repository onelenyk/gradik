# Gradik 🚀

A lightweight dashboard to monitor Gradle daemons, Kotlin daemons, Android Studio, IDEs, and more.

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Installation

### Option 1: pip install (Recommended)

```bash
pip install git+https://github.com/onelenyk/gradik.git
gradik start
```

### Option 2: Quick run (No install)

```bash
git clone https://github.com/onelenyk/gradik.git
cd gradik
./run.sh
```

### Option 3: One-liner install

```bash
curl -fsSL https://raw.githubusercontent.com/onelenyk/gradik/master/install.sh | bash
```

Installs globally. After install, just run:
```bash
gradik start
```

### Option 4: Standalone binary

```bash
./build.sh
./dist/gradik start
```

## Usage

```bash
# Start in background
gradik start

# Start on specific port
gradik start --port 8080

# Check status
gradik status

# Stop
gradik stop

# Restart
gradik restart

# Uninstall completely
gradik uninstall

# Run in foreground (for debugging)
gradik start --foreground

# Or just run directly (foreground)
gradik
```

### Uninstall

```bash
# Remove all Gradik files and config
gradik uninstall

# Then remove pip package
pip3 uninstall gradik
```

## Features

- 📊 **Real-time monitoring** - Gradle, Kotlin, Android Studio, Emulators, IDEs
- 🔄 **Stuck detection** - Warns when processes are stuck (high CPU for 30s+)
- 💤 **Idle detection** - Finds zombie daemons wasting RAM
- ⚠️ **Alerts** - High CPU (>50%), high memory (>1GB), total memory warnings
- 🔪 **Kill processes** - One-click to terminate any process
- 🌓 **Dark/Light mode** - Toggle theme
- ⚙️ **Port configuration** - Change port, saved to `~/.gradik/config.json`
- 📝 **IDE tracking** - Cursor, VS Code, Windsurf, Zed, Sublime, and more
- 🚀 **Background mode** - Run as a daemon with `gradik start`

## What it tracks

| Category | Processes |
|----------|-----------|
| ⚙️ Gradle | GradleDaemon, Gradle wrapper |
| K Kotlin | KotlinCompileDaemon |
| 📱 Android Studio | Main IDE, File Watcher |
| 📟 Emulators | Android Emulator, QEMU |
| 📝 IDEs | Cursor, VS Code, Windsurf, Zed, Fleet, Sublime, Neovim |
| ☕ Java | Other JVM processes |

## CLI Commands

| Command | Description |
|---------|-------------|
| `gradik start` | Start in background |
| `gradik start -p 8080` | Start on port 8080 |
| `gradik start -f` | Start in foreground |
| `gradik stop` | Stop running instance |
| `gradik restart` | Restart |
| `gradik status` | Show status (PID, port, CPU, RAM) |
| `gradik` | Run directly in foreground |

## Configuration

Config file: `~/.gradik/config.json`

```json
{
  "port": 5050
}
```

Change port via:
- UI: Click the port button in header
- CLI: `gradik start --port 8080`

## Files

| Path | Description |
|------|-------------|
| `~/.gradik/config.json` | Port configuration |
| `~/.gradik/gradik.pid` | PID of running instance |
| `~/.gradik/gradik.log` | Log file (background mode) |

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/status` | GET | JSON status of all processes |
| `/api/config` | GET | Current configuration |
| `/api/config/port` | POST | Change port |
| `/api/kill/<pid>` | POST | Kill a specific process |
| `/api/stop-daemons` | POST | Stop all Gradle daemons |

## Requirements

- Python 3.8+
- macOS / Linux

## License

MIT
