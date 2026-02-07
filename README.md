# MCP Formlabs Server

An MCP (Model Context Protocol) server that bridges Claude to the **Formlabs PreForm Local API**, giving Claude the ability to control Formlabs 3D printers — create scenes, import models, generate supports, slice, and send to print.

## Prerequisites

- **PreForm Desktop** running with the Local API enabled (default: `http://localhost:44388`)
- **Python 3.10+**
- **uv** (recommended) or pip

## Setup

```bash
# Clone and install
cd mcp-formlabs-server
uv venv && source .venv/bin/activate
uv pip install -e .

# Copy env and customize if needed
cp .env.example .env
```

## Claude Desktop Configuration

Add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "formlabs": {
      "command": "/Users/markus/.openclaw/workspace-kim/mcp-formlabs-server/.venv/bin/mcp-formlabs"
    }
  }
}
```

Or if using `uv` directly:

```json
{
  "mcpServers": {
    "formlabs": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/mcp-formlabs-server",
        "run", "mcp-formlabs"
      ]
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `get_materials` | List available resins and their supported layer heights |
| `list_printers` | List fleet devices, optionally filtered by group or readiness |
| `login` | Authenticate with Formlabs Dashboard for fleet access |
| `create_scene` | Create a new scene for a printer type, material, and layer height |
| `get_scene_info` | Get information about a specific scene |
| `delete_scene` | Delete a scene |
| `import_model` | Import an STL/OBJ/3MF file into a scene |
| `duplicate_parts` | Duplicate parts in a scene |
| `auto_orient` | Auto-orient models for optimal print quality |
| `generate_supports` | Generate support structures |
| `auto_layout` | Auto-layout models on the build plate |
| `generate_preview` | Generate a screenshot preview |
| `slice_scene` | Slice the scene for printing |
| `send_to_printer` | Send a sliced scene to a printer or queue |
| `print_model` | One-shot: scene → import → orient → support → layout → slice → print |

## Example Usage

Ask Claude:

> "Import my model at ~/models/bracket.stl, set up for Form 4 with Black Resin V5 at 0.05mm, make 3 copies, and send it to print."

Claude will use `print_model` to handle the entire workflow automatically.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PREFORM_API_URL` | `http://localhost:44388` | PreForm Local API endpoint |
