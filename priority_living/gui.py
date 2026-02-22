"""Priority Living CLI — Local WebGUI dashboard (FastAPI + embedded React SPA)."""

import json
import os
import platform
import shutil
import sys
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path

from priority_living import __version__
from priority_living.config_manager import load_config

# ── HTML Dashboard (embedded React SPA) ──────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Priority Living — Local Command Center</title>
<script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
<style>
:root {
  --bg: #0a0a0f;
  --bg-card: #12121a;
  --bg-card-hover: #1a1a25;
  --border: #1e1e2e;
  --text: #e0e0e8;
  --text-muted: #6e6e80;
  --primary: #8b5cf6;
  --primary-dim: #6d3fd0;
  --green: #22c55e;
  --yellow: #eab308;
  --red: #ef4444;
  --blue: #3b82f6;
  --font-mono: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: var(--bg); color: var(--text); font-family: var(--font-sans); }
.container { max-width: 1280px; margin: 0 auto; padding: 16px; }

/* Header */
.header { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
.header h1 { font-size: 16px; font-weight: 600; letter-spacing: -0.02em; }
.header h1 span { color: var(--primary); }
.badge { padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 500; font-family: var(--font-mono); }
.badge-online { background: rgba(34,197,94,0.15); color: var(--green); border: 1px solid rgba(34,197,94,0.3); }
.badge-offline { background: rgba(239,68,68,0.15); color: var(--red); border: 1px solid rgba(239,68,68,0.3); }

/* Stats Row */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.stat-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }
.stat-card .label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.stat-card .value { font-size: 22px; font-weight: 700; font-family: var(--font-mono); }

/* Layout */
.main-grid { display: grid; grid-template-columns: 340px 1fr; gap: 16px; margin-bottom: 16px; }
@media (max-width: 900px) { .main-grid { grid-template-columns: 1fr; } .stats-row { grid-template-columns: repeat(2, 1fr); } }

/* Panels */
.panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.panel-title { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 12px; }

/* Agent Config */
.select-wrap select { width: 100%; background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 8px 10px; border-radius: 6px; font-size: 13px; margin-bottom: 12px; }
.mode-buttons { display: flex; gap: 6px; margin-bottom: 12px; }
.mode-btn { flex: 1; padding: 7px; border: 1px solid var(--border); background: var(--bg); color: var(--text-muted); border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 500; transition: all 0.15s; }
.mode-btn:hover { border-color: var(--primary); color: var(--text); }
.mode-btn.active { background: var(--primary); color: white; border-color: var(--primary); }
.tool-toggle { display: flex; align-items: center; justify-content: space-between; padding: 6px 0; font-size: 13px; border-bottom: 1px solid var(--border); }
.tool-toggle:last-child { border-bottom: none; }
.toggle-switch { width: 36px; height: 20px; border-radius: 10px; background: var(--border); cursor: pointer; position: relative; transition: background 0.2s; }
.toggle-switch.on { background: var(--primary); }
.toggle-switch::after { content: ''; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: white; transition: transform 0.2s; }
.toggle-switch.on::after { transform: translateX(16px); }
.save-btn { width: 100%; padding: 8px; background: var(--primary); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; margin-top: 12px; transition: background 0.15s; }
.save-btn:hover { background: var(--primary-dim); }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Feed */
.feed-container { max-height: 420px; overflow-y: auto; }
.feed-container::-webkit-scrollbar { width: 4px; }
.feed-container::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
.feed-item { padding: 10px; border-bottom: 1px solid var(--border); font-family: var(--font-mono); font-size: 12px; cursor: pointer; transition: background 0.1s; }
.feed-item:hover { background: var(--bg-card-hover); }
.feed-item:last-child { border-bottom: none; }
.feed-item .meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.feed-item .type { color: var(--primary); font-weight: 500; }
.feed-item .time { color: var(--text-muted); font-size: 10px; }
.feed-item .desc { color: var(--text); line-height: 1.4; }
.feed-item .result { margin-top: 6px; padding: 6px 8px; background: var(--bg); border-radius: 4px; font-size: 11px; white-space: pre-wrap; word-break: break-all; max-height: 120px; overflow-y: auto; }
.status-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 6px; }
.status-completed { background: var(--green); }
.status-pending { background: var(--yellow); }
.status-failed { background: var(--red); }
.status-running { background: var(--blue); }

/* Task Input */
.task-input-row { display: flex; gap: 8px; }
.task-input { flex: 1; background: var(--bg-card); border: 1px solid var(--border); color: var(--text); padding: 10px 14px; border-radius: 8px; font-size: 13px; font-family: var(--font-sans); }
.task-input:focus { outline: none; border-color: var(--primary); }
.send-btn { padding: 10px 20px; background: var(--primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; transition: background 0.15s; }
.send-btn:hover { background: var(--primary-dim); }
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Hardware */
.hw-panel { margin-top: 16px; }
.hw-row { display: flex; justify-content: space-between; font-size: 13px; padding: 5px 0; }
.hw-row .lbl { color: var(--text-muted); }
.vram-bar { height: 6px; background: var(--border); border-radius: 3px; margin-top: 6px; overflow: hidden; }
.vram-fill { height: 100%; background: var(--primary); border-radius: 3px; transition: width 0.5s; }

/* Empty state */
.empty { text-align: center; padding: 40px; color: var(--text-muted); font-size: 13px; }
</style>
</head>
<body>
<div id="root"></div>
<script type="text/babel">
const { useState, useEffect, useCallback, useRef } = React;

const API = '';

function App() {
  const [status, setStatus] = useState(null);
  const [feed, setFeed] = useState([]);
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [autonomyMode, setAutonomyMode] = useState('manual');
  const [localTools, setLocalTools] = useState({shell: true, python: true, file_transfer: false, headless_browse: false});
  const [taskInput, setTaskInput] = useState('');
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState(false);
  const [expandedTask, setExpandedTask] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(API + '/api/status');
      const d = await r.json();
      setStatus(d);
      setConnected(d.connected || false);
    } catch { setConnected(false); }
  }, []);

  const fetchFeed = useCallback(async () => {
    try {
      const r = await fetch(API + '/api/feed?limit=50');
      const d = await r.json();
      if (d.feed) setFeed(d.feed);
    } catch {}
  }, []);

  const fetchAgents = useCallback(async () => {
    try {
      const r = await fetch(API + '/api/agents');
      const d = await r.json();
      if (d.agents) {
        setAgents(d.agents);
        if (!selectedAgent && d.agents.length > 0) {
          setSelectedAgent(d.agents[0].agent_id);
          setAutonomyMode(d.agents[0].autonomy_mode || 'manual');
          const tools = d.agents[0].local_tools || [];
          setLocalTools({shell: tools.includes('shell'), python: tools.includes('python'), file_transfer: tools.includes('file_transfer'), headless_browse: tools.includes('headless_browse')});
        }
      }
    } catch {}
  }, [selectedAgent]);

  useEffect(() => {
    fetchStatus();
    fetchFeed();
    fetchAgents();
    const si = setInterval(fetchStatus, 10000);
    const fi = setInterval(fetchFeed, 5000);
    return () => { clearInterval(si); clearInterval(fi); };
  }, []);

  // WebSocket for live feed
  useEffect(() => {
    try {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(proto + '://' + location.host + '/ws/feed');
      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.feed) setFeed(data.feed);
        } catch {}
      };
      ws.onclose = () => setTimeout(() => {}, 3000);
      wsRef.current = ws;
      return () => ws.close();
    } catch {}
  }, []);

  const sendTask = async () => {
    if (!taskInput.trim() || sending) return;
    setSending(true);
    try {
      await fetch(API + '/api/task', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({description: taskInput, action_type: 'manual_task'}),
      });
      setTaskInput('');
      fetchFeed();
    } catch {}
    setSending(false);
  };

  const saveConfig = async () => {
    if (!selectedAgent || saving) return;
    setSaving(true);
    try {
      const tools = Object.entries(localTools).filter(([,v]) => v).map(([k]) => k);
      await fetch(API + '/api/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({agent_id: selectedAgent, autonomy_mode: autonomyMode, local_tools: tools}),
      });
    } catch {}
    setSaving(false);
  };

  const stats = {
    total: feed.length,
    done: feed.filter(t => t.result_status === 'completed').length,
    pending: feed.filter(t => t.result_status === 'pending').length,
    avgLatency: (() => {
      const c = feed.filter(t => t.completed_at && t.created_at);
      if (!c.length) return '—';
      const avg = c.reduce((s, t) => s + (new Date(t.completed_at) - new Date(t.created_at)), 0) / c.length / 1000;
      return avg < 60 ? avg.toFixed(1) + 's' : (avg / 60).toFixed(1) + 'm';
    })(),
  };

  const fmtTime = (ts) => {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const diff = (now - d) / 1000;
    if (diff < 60) return Math.floor(diff) + 's ago';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return d.toLocaleDateString();
  };

  return (
    <div className="container">
      <div className="header">
        <h1><span>Priority Living</span> — Local Command Center v""" + __version__ + """</h1>
        <span className={'badge ' + (connected ? 'badge-online' : 'badge-offline')}>
          {connected ? '● Connected' : '○ Disconnected'}
        </span>
      </div>

      <div className="stats-row">
        <div className="stat-card"><div className="label">Total Tasks</div><div className="value">{stats.total}</div></div>
        <div className="stat-card"><div className="label">Completed</div><div className="value" style={{color:'var(--green)'}}>{stats.done}</div></div>
        <div className="stat-card"><div className="label">Pending</div><div className="value" style={{color:'var(--yellow)'}}>{stats.pending}</div></div>
        <div className="stat-card"><div className="label">Avg Latency</div><div className="value">{stats.avgLatency}</div></div>
      </div>

      <div className="main-grid">
        <div>
          <div className="panel">
            <div className="panel-title">Agent Configuration</div>
            <div className="select-wrap">
              <select value={selectedAgent} onChange={e => {
                setSelectedAgent(e.target.value);
                const a = agents.find(a => a.agent_id === e.target.value);
                if (a) {
                  setAutonomyMode(a.autonomy_mode || 'manual');
                  const tools = a.local_tools || [];
                  setLocalTools({shell: tools.includes('shell'), python: tools.includes('python'), file_transfer: tools.includes('file_transfer'), headless_browse: tools.includes('headless_browse')});
                }
              }}>
                {agents.length === 0 && <option value="">No agents bound</option>}
                {agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.name || a.agent_id.slice(0,8)}</option>)}
              </select>
            </div>
            <div className="panel-title" style={{marginTop: 4}}>Autonomy Mode</div>
            <div className="mode-buttons">
              {['manual', 'supervised', 'autonomous'].map(m => (
                <button key={m} className={'mode-btn' + (autonomyMode === m ? ' active' : '')} onClick={() => setAutonomyMode(m)}>
                  {m.charAt(0).toUpperCase() + m.slice(1)}
                </button>
              ))}
            </div>
            <div className="panel-title" style={{marginTop: 4}}>Local Tools</div>
            {Object.entries(localTools).map(([tool, enabled]) => (
              <div className="tool-toggle" key={tool}>
                <span>{tool.replace('_', ' ')}</span>
                <div className={'toggle-switch' + (enabled ? ' on' : '')} onClick={() => setLocalTools(prev => ({...prev, [tool]: !prev[tool]}))} />
              </div>
            ))}
            <button className="save-btn" onClick={saveConfig} disabled={saving || !selectedAgent}>
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>

          <div className="panel hw-panel">
            <div className="panel-title">Hardware</div>
            <div className="hw-row"><span className="lbl">GPU</span><span>{status?.gpu_name || 'Detecting...'}</span></div>
            <div className="hw-row"><span className="lbl">OS</span><span>{status?.os_info || '—'}</span></div>
            <div className="hw-row"><span className="lbl">Python</span><span>{status?.python_version || '—'}</span></div>
            <div className="hw-row"><span className="lbl">Disk Free</span><span>{status?.disk_free_gb ? status.disk_free_gb + ' GB' : '—'}</span></div>
            <div className="hw-row"><span className="lbl">Models</span><span>{status?.installed_models?.length || 0} installed</span></div>
            {status?.vram_total && (
              <div>
                <div className="hw-row"><span className="lbl">VRAM</span><span>{status.vram_used?.toFixed(1) || 0} / {status.vram_total?.toFixed(1)} GB</span></div>
                <div className="vram-bar"><div className="vram-fill" style={{width: ((status.vram_used || 0) / status.vram_total * 100) + '%'}} /></div>
              </div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-title">Live Task Feed</div>
          <div className="feed-container">
            {feed.length === 0 && <div className="empty">No tasks yet. Queue one below or wait for agent activity.</div>}
            {feed.map(task => (
              <div className="feed-item" key={task.id} onClick={() => setExpandedTask(expandedTask === task.id ? null : task.id)}>
                <div className="meta">
                  <span><span className={'status-dot status-' + task.result_status} /><span className="type">{task.action_type}</span></span>
                  <span className="time">{fmtTime(task.created_at)}</span>
                </div>
                <div className="desc">{task.action_description}</div>
                {expandedTask === task.id && task.result_data && (
                  <div className="result">{typeof task.result_data === 'string' ? task.result_data : JSON.stringify(task.result_data, null, 2)}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="task-input-row">
        <input className="task-input" placeholder="Queue a task..." value={taskInput}
          onChange={e => setTaskInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendTask()} />
        <button className="send-btn" onClick={sendTask} disabled={sending || !taskInput.trim()}>
          {sending ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
</script>
</body>
</html>"""


# ── FastAPI Application ──────────────────────────────────────

def create_app(backend_url, anon_key):
    """Create the FastAPI app with API routes and embedded dashboard."""
    try:
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse, JSONResponse
    except ImportError:
        print("❌ FastAPI is required for the GUI. Install it:")
        print("   pip install priority-living-cli[gui]")
        sys.exit(1)

    app = FastAPI(title="Priority Living Local Command Center", version=__version__)
    cfg = load_config()
    api_key = cfg.get("bridge_key", "")

    def _cloud_request(endpoint, data=None, method="POST"):
        url = f"{backend_url}/functions/v1/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
            "x-bridge-key": api_key,
        }
        try:
            if data:
                body = json.dumps(data).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
            else:
                req = urllib.request.Request(url, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}

    def _get_hardware_info():
        info = {
            "gpu_name": "CPU only",
            "gpu_available": False,
            "vram_total": None,
            "vram_used": None,
            "os_info": f"{platform.system()} {platform.release()}",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "disk_free_gb": None,
            "installed_models": [],
        }
        try:
            disk = shutil.disk_usage(str(Path.home()))
            info["disk_free_gb"] = round(disk.free / (1024**3), 1)
        except Exception:
            pass
        try:
            import torch
            if torch.cuda.is_available():
                info["gpu_name"] = torch.cuda.get_device_name(0)
                info["gpu_available"] = True
                info["vram_total"] = round(torch.cuda.get_device_properties(0).total_mem / (1024**3), 1)
                info["vram_used"] = round(torch.cuda.memory_allocated(0) / (1024**3), 1)
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                info["gpu_name"] = "Apple Silicon (MPS)"
                info["gpu_available"] = True
        except ImportError:
            pass
        models_dir = Path.home() / ".priority-living" / "models"
        if models_dir.exists():
            info["installed_models"] = [d.name for d in models_dir.iterdir() if d.is_dir()]
        return info

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return DASHBOARD_HTML

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": __version__}

    @app.get("/api/status")
    async def get_status():
        hw = _get_hardware_info()
        connected = False
        if api_key:
            result = _cloud_request("bridge-poll", {"machine_name": platform.node(), "capabilities": []})
            connected = result is not None and "error" not in result
        return {
            "connected": connected,
            "bridge_key": api_key[:6] + "..." if api_key else None,
            "cli_version": __version__,
            "machine_name": platform.node(),
            **hw,
        }

    @app.get("/api/feed")
    async def get_feed(limit: int = 50):
        if not api_key:
            return {"feed": [], "error": "No bridge key configured"}
        # Direct query would need auth — use sovereign-agent-control
        result = _cloud_request("sovereign-agent-control", {
            "action": "get_live_feed",
            "limit": limit,
        })
        return {"feed": result.get("feed", []) if result else []}

    @app.get("/api/agents")
    async def get_agents():
        if not api_key:
            return {"agents": []}
        result = _cloud_request("sovereign-agent-control", {
            "action": "get_config",
            "agent_id": None,
        })
        agents = []
        if result and result.get("config"):
            c = result["config"]
            agents.append({
                "agent_id": c.get("agent_id"),
                "name": c.get("agent_deployments", {}).get("name", c.get("agent_id", "")[:8]),
                "autonomy_mode": c.get("autonomy_mode", "manual"),
                "local_tools": c.get("local_tools", []),
                "workspace_path": c.get("workspace_path", "/workspace"),
            })
        return {"agents": agents}

    @app.get("/api/models")
    async def get_models():
        models_dir = Path.home() / ".priority-living" / "models"
        models = []
        if models_dir.exists():
            for d in models_dir.iterdir():
                if d.is_dir():
                    size_mb = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / (1024 * 1024)
                    models.append({"name": d.name, "size_mb": round(size_mb, 1)})
        return {"models": models}

    @app.post("/api/task")
    async def queue_task(body: dict = {}):
        if not api_key:
            return JSONResponse({"error": "No bridge key configured"}, status_code=400)
        result = _cloud_request("sovereign-agent-control", {
            "action": "queue_manual_task",
            "task_description": body.get("description", ""),
            "action_type": body.get("action_type", "manual_task"),
        })
        return result or {"error": "Failed to queue task"}

    @app.post("/api/config")
    async def update_config(body: dict = {}):
        if not api_key:
            return JSONResponse({"error": "No bridge key configured"}, status_code=400)
        result = _cloud_request("sovereign-agent-control", {
            "action": "bind_agent",
            "agent_id": body.get("agent_id"),
            "autonomy_mode": body.get("autonomy_mode", "manual"),
            "local_tools": body.get("local_tools", []),
        })
        return result or {"error": "Failed to update config"}

    @app.websocket("/ws/feed")
    async def ws_feed(websocket: WebSocket):
        await websocket.accept()
        import asyncio
        last_ids = set()
        try:
            while True:
                result = _cloud_request("sovereign-agent-control", {
                    "action": "get_live_feed",
                    "limit": 50,
                })
                feed = result.get("feed", []) if result else []
                current_ids = {t.get("id") for t in feed}
                if current_ids != last_ids:
                    await websocket.send_json({"feed": feed})
                    last_ids = current_ids
                await asyncio.sleep(3)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    return app


def handle_gui(args, default_backend, default_anon_key):
    """CLI entry point for 'pl gui' command."""
    try:
        import uvicorn
    except ImportError:
        print("❌ uvicorn is required for the GUI. Install it:")
        print("   pip install priority-living-cli[gui]")
        sys.exit(1)

    cfg = load_config()
    backend = cfg.get("backend_url", default_backend)
    anon_key = cfg.get("anon_key", default_anon_key)
    port = getattr(args, "port", 8420) or 8420
    no_browser = getattr(args, "no_browser", False)

    print(f"""
╔═══════════════════════════════════════════╗
║  Priority Living CLI  v{__version__:<18}║
║  Local Command Center — WebGUI            ║
╚═══════════════════════════════════════════╝
""")
    print(f"🌐 Starting server on http://localhost:{port}")
    print(f"🔗 Backend: {backend}")

    if not no_browser:
        def open_browser():
            import webbrowser
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=open_browser, daemon=True).start()

    app = create_app(backend, anon_key)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
