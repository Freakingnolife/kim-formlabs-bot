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

### Material & Presets
| Tool | Description |
|------|-------------|
| `get_materials` | List available resins and their supported layer heights |
| `parse_material_query` | Parse natural language like "tough grey resin" or "fast mode" |
| `list_presets` | List available print presets (miniatures, prototypes, etc.) |
| `print_with_preset` | Print using a preset configuration |

### Printer & Job Management
| Tool | Description |
|------|-------------|
| `list_printers` | List fleet devices, optionally filtered by group or readiness |
| `login` | Authenticate with Formlabs Dashboard for fleet access |
| `list_jobs` | List print jobs in the queue |
| `get_job_status` | Check status of a specific print job |
| `cancel_job` | Cancel a queued or running print job |

### Scene Management
| Tool | Description |
|------|-------------|
| `create_scene` | Create a new scene for a printer type, material, and layer height |
| `get_scene_info` | Get information about a specific scene |
| `delete_scene` | Delete a scene |
| `import_model` | Import an STL/OBJ/3MF file into a scene |
| `import_batch` | Import all models from a folder into one scene |
| `duplicate_parts` | Duplicate parts in a scene |
| `auto_orient` | Auto-orient models for optimal print quality |
| `generate_supports` | Generate support structures |
| `auto_layout` | Auto-layout models on the build plate |
| `generate_preview` | Generate a screenshot preview |
| `slice_scene` | Slice the scene for printing |
| `send_to_printer` | Send a sliced scene to a printer or queue |

### Pre-Flight Analysis
| Tool | Description |
|------|-------------|
| `preflight_check` | Analyze mesh before printing (volume, manifold check, overhangs) |

### Workflows
| Tool | Description |
|------|-------------|
| `print_model` | One-shot: scene → import → orient → support → layout → slice → print |

## Example Usage

Ask Claude:

> "Import my model at ~/models/bracket.stl, set up for Form 4 with Black Resin V5 at 0.05mm, make 3 copies, and send it to print."

Claude will use `print_model` to handle the entire workflow automatically.

### Natural Language Materials

> "Print this in tough grey resin at fine detail"

Claude parses "tough grey" → Tough 2000, "fine detail" → 0.025mm.

### Print Presets

> "Print the bracket using the functional preset"

Available presets: `miniatures`, `prototypes`, `functional`, `clear`, `durable`, `flexible`, `black`

### Batch Import

> "Import all models from ~/models/batch/ and set up for Grey V5"

Imports all STL/OBJ/3MF files from the folder into a single scene with auto-layout.

### Pre-Flight Check

> "Check this model for issues before printing"

Analyzes mesh for watertightness, overhangs, and provides recommendations.

### Job Management

> "Show me the print queue" / "Cancel job abc123"

Monitor and manage active print jobs.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PREFORM_API_URL` | `http://localhost:44388` | PreForm Local API endpoint |
