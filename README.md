# Reachy Mini MCP

**Give your AI a body.**

This MCP server lets AI systems control [Pollen Robotics' Reachy Mini](https://www.pollen-robotics.com/reachy-mini/) robot—speak, listen, see, and express emotions through physical movement. Works with Claude, GPT, Grok, or any MCP-compatible AI.

7 tools. 30 minutes to first demo. Zero robotics expertise required.

---

## For AI Systems

Token-efficient tool reference for programmatic use:

| Tool | Args | Purpose |
|------|------|---------|
| `speak` | `text, listen_after=0` | Voice + gesture, optionally listen after |
| `listen` | `duration=3` | STT via Deepgram Nova-2 |
| `snap` | - | Camera capture (base64 JPEG) |
| `show` | `emotion, move=""` | Express emotion or play recorded move |
| `look` | `roll, pitch, yaw, z, duration` | Head positioning (degrees) |
| `rest` | `mode="neutral"` | neutral / sleep / wake |
| `discover` | `library="emotions"` | Find available recorded moves |

### speak()

Supports embedded move markers for choreographed speech:

```
speak("[move:curious1] What's this? [move:surprised1] Oh wow!")
```

Moves fire right before their speech chunk. Use `listen_after=5` to hear response.

### show()

Built-in emotions (fast, local):
`neutral`, `curious`, `uncertain`, `recognition`, `joy`, `thinking`, `listening`, `agreeing`, `disagreeing`, `sleepy`, `surprised`, `focused`

Recorded moves (81 from Pollen):
```
show(move="loving1")
show(move="fear1")
show(move="serenity1")
```

Use `discover()` to see all available moves.

---

## Quick Start

```bash
# Install
cd reachy-mini-mcp
poetry install

# Set API key (required for speak/listen)
export DEEPGRAM_API_KEY=your_key_here

# Start simulator daemon
mjpython -m reachy_mini.daemon.app.main --sim --scene minimal

# Run MCP server
poetry run python src/server.py
```

## Architecture

```
AI (Claude/GPT/Grok) → MCP Server → SDK → Daemon → Robot/Simulator
```

7 tools following Miller's Law—fits in working memory.

## Voice Providers

| Provider | Status | Use Case |
|----------|--------|----------|
| [Deepgram](https://deepgram.com/) | Supported | TTS (Aura 2) + STT (Nova 2) |
| [Grok Voice](https://x.ai/news/grok-voice-agent-api) | Coming soon | xAI's expressive voice API |

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
      "args": ["-C", "/path/to/reachy-mini-mcp", "run", "python", "src/server.py"],
      "env": {
        "DEEPGRAM_API_KEY": "your_key_here"
      }
    }
  }
}
```

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DEEPGRAM_API_KEY` | Yes | - | TTS and STT via Deepgram |
| `REACHY_DAEMON_URL` | No | `http://localhost:8321/api` | Daemon API endpoint |

## Requirements

- Python 3.10+
- [reachy-mini SDK](https://github.com/pollen-robotics/reachy_mini) (installed via poetry)
- MuJoCo (for simulation)
- Deepgram API key (for speak/listen)

## Hardware Notes

- **Simulator:** `mjpython` required on macOS for MuJoCo visualization
- **Real hardware:** Same MCP server, daemon auto-connects
- **Port conflicts:** Zenoh uses 7447, daemon uses 8321 by default

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

This project uses the [Reachy Mini SDK](https://github.com/pollen-robotics/reachy_mini) by [Pollen Robotics](https://www.pollen-robotics.com/), licensed under Apache 2.0.

## Links

- [Reachy Mini SDK](https://github.com/pollen-robotics/reachy_mini) (Apache 2.0)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [mVara](https://mvara.ai/)
