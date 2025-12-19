# Reachy Mini MCP

MCP server for [Pollen Robotics Reachy Mini](https://www.pollen-robotics.com/reachy-mini/) robot control.

**For AI systems** - Token-efficient reference for programmatic use.

## Quick Start

```bash
# Install
cd reachy-mini-mcp
poetry install

# Set TTS key (optional, for speak())
export DEEPGRAM_API_KEY=your_key_here

# Start simulator daemon
mjpython -m reachy_mini.daemon.app.main --sim --scene minimal

# Run MCP server
poetry run python src/server.py
```

## Architecture

```
MCP Tool → SDK Call → Daemon → Robot/Simulator
```

High-level `express()` abstracts motor control into semantic actions.
Low-level tools available for precise control when needed.

## Tools

### Expression (Preferred)

| Tool | Args | Purpose |
|------|------|---------|
| `express` | `emotion: str` | Execute emotion choreography |
| `nod` | `times: int = 2` | Agreement gesture |
| `shake` | `times: int = 2` | Disagreement gesture |
| `rest` | - | Return to neutral pose |

**Emotions:** `neutral`, `curious`, `uncertain`, `recognition`, `joy`, `thinking`, `listening`, `agreeing`, `disagreeing`, `sleepy`, `surprised`, `focused`

### Motor Control

| Tool | Args | Purpose |
|------|------|---------|
| `look_at` | `roll, pitch, yaw, z, duration` | Head positioning (degrees) |
| `antenna` | `left, right, duration` | Antenna angles (degrees) |
| `rotate` | `direction, degrees` | Body rotation |

### I/O

| Tool | Args | Purpose |
|------|------|---------|
| `speak` | `text: str` | TTS output (requires DEEPGRAM_API_KEY) |
| `listen` | `duration: float = 3.0` | Audio capture (base64) |
| `see` | - | Camera capture (base64 JPEG) |

### Lifecycle

| Tool | Purpose |
|------|---------|
| `wake_up` | Initialize robot motors |
| `sleep` | Power down motors |

## Expression Vocabulary

Each emotion maps to choreography:
- **Head pose:** roll, pitch, yaw (degrees)
- **Antennas:** left, right angles (degrees)
- **Duration:** movement time (seconds)
- **Interpolation:** linear, minjerk, ease_in_out, cartoon

Example: `curious` → head forward (pitch +10, yaw +8), antennas up (+20, +20), 1.2s, ease_in_out

## MCP Config

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "reachy-mini": {
      "command": "poetry",
      "args": ["-C", "/path/to/reachy-mini-mcp", "run", "python", "src/server.py"],
      "env": {
        "DEEPGRAM_API_KEY": "your_key_here"
      }
    }
  }
}
```

### Claude Code

`~/.claude.json`:

```json
{
  "mcpServers": {
    "reachy-mini": {
      "command": "poetry",
      "args": ["run", "python", "src/server.py"],
      "cwd": "/path/to/reachy-mini-mcp"
    }
  }
}
```

## Requirements

- Python 3.10+
- [reachy-mini SDK](https://github.com/pollen-robotics/reachy_mini) (installed via poetry)
- MuJoCo (for simulation)
- Deepgram API key (for TTS, optional)

## Hardware Notes

- **Simulator:** `mjpython` required on macOS for MuJoCo visualization
- **Real hardware:** Same MCP server, daemon auto-connects
- **Port conflicts:** Zenoh uses 7447, daemon uses 8765 by default

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

This project uses the [Reachy Mini SDK](https://github.com/pollen-robotics/reachy_mini) by [Pollen Robotics](https://www.pollen-robotics.com/), licensed under Apache 2.0.

## Links

- [Reachy Mini SDK](https://github.com/pollen-robotics/reachy_mini) (Apache 2.0)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [mVara](https://mvara.ai/)
