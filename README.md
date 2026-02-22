# Priority Living CLI

> Sovereign AI command & control for your local machine.

## Features

- 🖥 **Bridge Worker** — Connect your machine to the Priority Living platform
- 🤖 **Agent Management** — List, start, stop, and deploy agents locally
- 🧠 **Model Operations** — Download, run inference, and serve HuggingFace models
- 📊 **System Diagnostics** — GPU detection, dependency checks, connectivity tests
- ⚙️ **Local Config** — Persistent configuration in `~/.priority-living/`
- 📡 **Streaming Output** — Real-time command output to the cloud dashboard
- 🛡 **Safety Guards** — Blocks dangerous commands automatically
- 📦 **Offline Resilience** — Queues commands when backend is unreachable
- 🔄 **Self-Update** — `pl update` checks GitHub for newer versions
- 🌐 **WebGUI** — Local browser dashboard at `localhost:8420`

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/YOUR_USERNAME/priority-living-cli.git
cd priority-living-cli
pip install -e .

# 2. Configure
pl config set bridge_key pb_YOUR_KEY

# 3. Check status
pl status

# 4. Start the bridge
pl bridge start
```

## Commands

| Command | Description |
|---------|-------------|
| `pl bridge start` | Start the bridge worker |
| `pl agents list` | List bound agents |
| `pl agents start <id>` | Start a local agent worker |
| `pl agents stop <id>` | Stop a running agent worker |
| `pl agents deploy <platform> --agent-id <id>` | Deploy and start an agent |
| `pl models download <name>` | Download a HuggingFace model |
| `pl models infer <name> -p "..."` | Run local inference |
| `pl models serve <name>` | Start local model API server |
| `pl status` | Show system status |
| `pl diagnose` | Deep diagnostic scan |
| `pl update` | Check for updates and self-update |
| `pl config set <key> <val>` | Set config value |
| `pl config get <key>` | Get config value |
| `pl gui` | Launch local WebGUI dashboard |
| `pl gui --port 9000` | Launch on custom port |
| `pl gui --no-browser` | Launch without opening browser |

## Agent Workers

Agents run as local subprocesses that poll for tasks and execute them:

```bash
# Start an agent worker (runs until Ctrl+C)
pl agents start <agent_id>

# Stop a running agent
pl agents stop <agent_id>

# Deploy and start in one step
pl agents deploy telegram --agent-id <agent_id>
```

Agent PIDs are tracked in `~/.priority-living/agents/`.

## Offline Resilience

When the backend is unreachable, the CLI queues failed API requests locally in `~/.priority-living/offline_queue.json`. Queued requests are automatically replayed on each poll cycle when connectivity returns.

- Max queue size: 500 entries (oldest dropped if exceeded)
- Client errors (4xx) are discarded; server errors (5xx) are retried
- Queue status shown in `pl status` and `pl diagnose`

## Self-Update

```bash
# Check for updates and install if available
pl update

# First, set your GitHub username (auto-set on first deploy)
pl config set github_repo_owner YOUR_USERNAME
```

## WebGUI Dashboard

Launch a local browser-based control panel that mirrors the cloud Sovereign Command Center:

```bash
# Install GUI extras
pip install -e ".[gui]"

# Launch (opens browser automatically)
pl gui

# Custom port
pl gui --port 9000

# Don't auto-open browser
pl gui --no-browser
```

The GUI runs at `http://localhost:8420` and provides:
- Real-time task feed with status badges
- Agent configuration (autonomy mode, local tools)
- Hardware/GPU monitoring
- Quick task input
- Stats dashboard (total/done/pending/latency)

## AI Features (Optional)

For model download, inference, and serving:

```bash
pip install priority-living-cli[ai]
# or
pip install torch transformers huggingface_hub
```

## Configuration

Config is stored in `~/.priority-living/config.json`:

| Key | Description | Default |
|-----|-------------|---------|
| `bridge_key` | Your bridge API key (pb_...) | — |
| `backend_url` | Priority Living backend URL | auto |
| `poll_interval` | Bridge poll interval (seconds) | 3 |
| `auto_restart` | Auto-restart on crash | true |
| `default_model_path` | Model storage directory | ~/.priority-living/models |
| `github_repo_owner` | GitHub username for updates | auto |
| `connection_token` | Sandbox connection token for agents | — |

## Security

- Dangerous commands (`rm -rf /`, `mkfs`, etc.) are automatically blocked
- Output truncated at 50KB
- Commands timeout after 5 minutes
- Bridge keys are scoped to your account
- Errors are reported to the cloud for diagnostics

## License

MIT — Built with ❤️ by Priority Living Labs
