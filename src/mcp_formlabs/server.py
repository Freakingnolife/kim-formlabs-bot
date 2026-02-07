"""MCP server for Formlabs PreForm Local API."""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from mcp_formlabs.preform_client import PreFormClient, PreFormError
from mcp_formlabs.materials import parse_material
from mcp_formlabs.presets import get_preset, list_presets as _list_presets
from mcp_formlabs.preflight import preflight_check as _preflight_check

load_dotenv()

mcp = FastMCP("Formlabs PreForm")

# Shared client instance — connects to PreForm Desktop running locally.
_client = PreFormClient()

# Track the most-recently created scene so callers can omit scene_id.
_current_scene_id: str | None = None


def _scene_id(scene_id: str | None) -> str:
    """Resolve a scene_id, falling back to the current scene."""
    sid = scene_id or _current_scene_id
    if not sid:
        raise ValueError(
            "No scene_id provided and no scene has been created yet. "
            "Call create_scene first."
        )
    return sid


def _fmt(data: object) -> str:
    """Format API response for tool output."""
    if isinstance(data, (dict, list)):
        return json.dumps(data, indent=2)
    return str(data)


# ── Tools ────────────────────────────────────────────────────────────


@mcp.tool()
def list_printers(group: str | None = None, can_print: bool = False) -> str:
    """List Formlabs printers available on the network.

    Args:
        group: Filter by printer group name.
        can_print: Only show printers ready to accept a print job.
    """
    try:
        devices = _client.list_devices(group=group, can_print=can_print)
        return _fmt(devices)
    except PreFormError as e:
        return f"Error listing printers: {e}"


@mcp.tool()
def get_materials() -> str:
    """List available materials and their supported layer heights."""
    materials = [
        {"code": "FLGPGR05", "name": "Grey V5", "layers": [0.025, 0.05, 0.1]},
        {"code": "FLGPBK05", "name": "Black V5", "layers": [0.025, 0.05, 0.1]},
        {"code": "FLGPCL05", "name": "Clear V5", "layers": [0.025, 0.05, 0.1]},
        {"code": "FLGPWH05", "name": "White V5", "layers": [0.025, 0.05, 0.1]},
        {"code": "FLTO2K02", "name": "Tough 2000 V2", "layers": [0.025, 0.05, 0.1]},
        {"code": "FLTOTL02", "name": "Tough 1500 V2", "layers": [0.025, 0.05, 0.1]},
        {"code": "FLDUCL21", "name": "Durable V2.1", "layers": [0.025, 0.05, 0.1]},
        {"code": "FLELCL02", "name": "Elastic 50A V2", "layers": [0.05, 0.1]},
        {"code": "FLFMGR01", "name": "Fast Model V1", "layers": [0.05, 0.1]},
    ]
    return _fmt(materials)


@mcp.tool()
def parse_material_query(query: str) -> str:
    """Parse a natural language material query.

    Args:
        query: Natural language query like "tough grey resin", "fast mode",
               "clear v5 detail", "0.05mm elastic".

    Returns: Material code, layer height, and material name.
    """
    result = parse_material(query)
    return _fmt(result)


@mcp.tool()
def list_presets() -> str:
    """List available print presets for common use cases."""
    return _fmt(_list_presets())


@mcp.tool()
def print_with_preset(
    file_path: str,
    preset_name: str,
    copies: int = 1,
    printer_id: str | None = None,
    group_id: str | None = None,
) -> str:
    """Print a model using a predefined preset configuration.

    Args:
        file_path: Path to the 3D model file.
        preset_name: Preset name (miniatures, prototypes, functional, clear,
                     durable, flexible, black).
        copies: Number of copies (default 1).
        printer_id: Target printer ID (optional).
        group_id: Target printer group (optional).
    """
    preset = get_preset(preset_name)
    if not preset:
        return f"Unknown preset: {preset_name}. Available: {', '.join([p['name'] for p in _list_presets()])}"

    # Use the print_model tool with preset values
    return print_model(
        file_path=file_path,
        material=preset["material_code"],
        layer_height=preset["layer_height"],
        printer_type=preset["printer_type"],
        copies=copies,
        printer_id=printer_id,
        group_id=group_id,
    )


@mcp.tool()
def preflight_check(file_path: str) -> str:
    """Analyze a 3D model before printing for issues and recommendations.

    Args:
        file_path: Path to the 3D model file (STL, OBJ, 3MF).

    Returns: Volume, manifold status, dimensions, overhangs, and recommendations.
    """
    result = _preflight_check(file_path)
    return _fmt(result)


@mcp.tool()
def list_jobs(status: str | None = None) -> str:
    """List print jobs in the queue.

    Args:
        status: Filter by status (running, queued, completed).
    """
    try:
        jobs = _client.list_jobs(status=status)
        return _fmt(jobs)
    except PreFormError as e:
        return f"Error listing jobs: {e}"


@mcp.tool()
def get_job_status(job_id: str) -> str:
    """Get the status of a specific print job.

    Args:
        job_id: The job ID to check.
    """
    try:
        result = _client.get_job_status(job_id)
        return _fmt(result)
    except PreFormError as e:
        return f"Error getting job status: {e}"


@mcp.tool()
def cancel_job(job_id: str) -> str:
    """Cancel a print job.

    Args:
        job_id: The job ID to cancel.
    """
    try:
        result = _client.cancel_job(job_id)
        return f"Job {job_id} cancelled.\n{_fmt(result)}"
    except PreFormError as e:
        return f"Error cancelling job: {e}"


@mcp.tool()
def import_batch(
    folder_path: str,
    material: str,
    layer_height: float,
    printer_type: str = "Form 4",
    max_density: float = 0.8,
) -> str:
    """Import all STL/OBJ files from a folder into a single scene.

    Args:
        folder_path: Path to folder containing model files.
        material: Material code (e.g. "FLGPGR05").
        layer_height: Layer thickness in mm.
        printer_type: Printer model (default "Form 4").
        max_density: Maximum packing density (0.0-1.0).
    """
    global _current_scene_id

    import os
    expanded = os.path.expanduser(folder_path)

    # Find all model files
    extensions = (".stl", ".obj", ".3mf", ".form")
    files = [f for f in os.listdir(expanded) if f.lower().endswith(extensions)]

    if not files:
        return f"No model files found in {folder_path}"

    steps = []
    try:
        # Create scene
        scene = _client.create_scene(printer_type, material, layer_height)
        sid = str(scene.get("id", scene.get("scene_id", "")))
        _current_scene_id = sid
        steps.append(f"1. Scene created (id: {sid})")

        # Import all models
        imported = 0
        for filename in files:
            filepath = os.path.join(expanded, filename)
            try:
                _client.import_model(sid, filepath, auto_orient=True, repair=False)
                imported += 1
            except PreFormError as e:
                steps.append(f"  ⚠️ Failed to import {filename}: {e}")

        steps.append(f"2. Imported {imported}/{len(files)} models")

        # Auto-layout
        _client.auto_layout(sid)
        steps.append("3. Auto-layout complete")

        return f"Batch import complete:\n" + "\n".join(steps)

    except PreFormError as e:
        steps.append(f"FAILED: {e}")
        return "Batch import stopped:\n" + "\n".join(steps)


@mcp.tool()
def login(username: str, password: str) -> str:
    """Authenticate with Formlabs Dashboard to access fleet printers.

    Args:
        username: Formlabs Dashboard email.
        password: Formlabs Dashboard password.
    """
    try:
        result = _client.login(username, password)
        return _fmt(result)
    except PreFormError as e:
        return f"Login failed: {e}"


@mcp.tool()
def create_scene(
    printer_type: str, material: str, layer_height: float
) -> str:
    """Create a new PreForm scene for a specific printer and material.

    Args:
        printer_type: Printer model (e.g. "Form 4", "Form 3+", "Form 4B", "Form 4L").
        material: Material code (e.g. "FLGPBK05" for Black Resin V5).
        layer_height: Layer thickness in mm (e.g. 0.05, 0.1).
    """
    global _current_scene_id
    try:
        result = _client.create_scene(printer_type, material, layer_height)
        _current_scene_id = str(result.get("id", result.get("scene_id", "")))
        return f"Scene created (id: {_current_scene_id}).\n{_fmt(result)}"
    except PreFormError as e:
        return f"Error creating scene: {e}"


@mcp.tool()
def import_model(
    file_path: str,
    scene_id: str | None = None,
    auto_orient: bool = True,
    repair: bool = False,
) -> str:
    """Import a 3D model file (STL, OBJ, FORM, 3MF) into a scene.

    Args:
        file_path: Absolute path to the model file on disk.
        scene_id: Target scene ID. Uses the current scene if omitted.
        auto_orient: Automatically orient the model for best results.
        repair: Attempt to repair mesh errors on import.
    """
    try:
        sid = _scene_id(scene_id)
        result = _client.import_model(sid, file_path, auto_orient, repair)
        return f"Model imported into scene {sid}.\n{_fmt(result)}"
    except (PreFormError, ValueError, FileNotFoundError) as e:
        return f"Error importing model: {e}"


@mcp.tool()
def duplicate_parts(
    count: int,
    scene_id: str | None = None,
    model_id: str | None = None,
) -> str:
    """Duplicate parts in a scene.

    Args:
        count: Number of copies to create.
        scene_id: Target scene. Uses the current scene if omitted.
        model_id: Specific model to duplicate. Duplicates all if omitted.
    """
    try:
        sid = _scene_id(scene_id)
        result = _client.duplicate_model(sid, count, model_id)
        return f"Duplicated {count} copies in scene {sid}.\n{_fmt(result)}"
    except (PreFormError, ValueError) as e:
        return f"Error duplicating parts: {e}"


@mcp.tool()
def auto_orient(scene_id: str | None = None) -> str:
    """Auto-orient all models in a scene for optimal print quality.

    Args:
        scene_id: Target scene. Uses the current scene if omitted.
    """
    try:
        sid = _scene_id(scene_id)
        result = _client.auto_orient(sid)
        return f"Auto-orient complete for scene {sid}.\n{_fmt(result)}"
    except (PreFormError, ValueError) as e:
        return f"Error auto-orienting: {e}"


@mcp.tool()
def generate_supports(
    scene_id: str | None = None, mode: str = "auto-v2"
) -> str:
    """Generate support structures for models in a scene.

    Args:
        scene_id: Target scene. Uses the current scene if omitted.
        mode: Support generation mode ("auto-v2" recommended).
    """
    try:
        sid = _scene_id(scene_id)
        result = _client.auto_support(sid, mode)
        return f"Supports generated for scene {sid}.\n{_fmt(result)}"
    except (PreFormError, ValueError) as e:
        return f"Error generating supports: {e}"


@mcp.tool()
def auto_layout(scene_id: str | None = None) -> str:
    """Auto-layout models on the build plate to optimize packing.

    Args:
        scene_id: Target scene. Uses the current scene if omitted.
    """
    try:
        sid = _scene_id(scene_id)
        result = _client.auto_layout(sid)
        return f"Auto-layout complete for scene {sid}.\n{_fmt(result)}"
    except (PreFormError, ValueError) as e:
        return f"Error auto-laying out: {e}"


@mcp.tool()
def generate_preview(scene_id: str | None = None) -> str:
    """Generate a screenshot preview of the current scene.

    Args:
        scene_id: Target scene. Uses the current scene if omitted.
    """
    try:
        sid = _scene_id(scene_id)
        result = _client.screenshot(sid)
        return f"Preview generated for scene {sid}.\n{_fmt(result)}"
    except (PreFormError, ValueError) as e:
        return f"Error generating preview: {e}"


@mcp.tool()
def slice_scene(scene_id: str | None = None) -> str:
    """Slice the scene — prepares it for printing (may take a while).

    Args:
        scene_id: Target scene. Uses the current scene if omitted.
    """
    try:
        sid = _scene_id(scene_id)
        result = _client.slice(sid)
        return f"Scene {sid} sliced successfully.\n{_fmt(result)}"
    except (PreFormError, ValueError) as e:
        return f"Error slicing scene: {e}"


@mcp.tool()
def send_to_printer(
    scene_id: str | None = None,
    printer_id: str | None = None,
    group_id: str | None = None,
    job_name: str | None = None,
    queue: bool = True,
) -> str:
    """Send a sliced scene to a printer or print queue.

    Args:
        scene_id: Scene to print. Uses the current scene if omitted.
        printer_id: Send to a specific printer by ID.
        group_id: Send to a printer group (uses remote-print fleet queue).
        job_name: Optional human-readable job name.
        queue: Whether to queue the job (default True).
    """
    try:
        sid = _scene_id(scene_id)
        result = _client.print_scene(
            sid,
            printer_id=printer_id,
            group_id=group_id,
            job_name=job_name,
            queue=queue,
        )
        return f"Print job submitted for scene {sid}.\n{_fmt(result)}"
    except (PreFormError, ValueError) as e:
        return f"Error sending to printer: {e}"


@mcp.tool()
def get_scene_info(scene_id: str | None = None) -> str:
    """Get information about the current scene.

    Args:
        scene_id: Target scene. Uses the current scene if omitted.
    """
    try:
        sid = _scene_id(scene_id)
        result = _client.get_scene(sid)
        return _fmt(result)
    except (PreFormError, ValueError) as e:
        return f"Error getting scene info: {e}"


@mcp.tool()
def delete_scene(scene_id: str | None = None) -> str:
    """Delete a scene.

    Args:
        scene_id: Target scene to delete. Uses the current scene if omitted.
    """
    global _current_scene_id
    try:
        sid = _scene_id(scene_id)
        result = _client.delete_scene(sid)
        if _current_scene_id == sid:
            _current_scene_id = None
        return f"Scene {sid} deleted.\n{_fmt(result)}"
    except (PreFormError, ValueError) as e:
        return f"Error deleting scene: {e}"


@mcp.tool()
def print_model(
    file_path: str,
    material: str,
    layer_height: float,
    printer_type: str = "Form 4",
    copies: int = 1,
    printer_id: str | None = None,
    group_id: str | None = None,
) -> str:
    """One-shot workflow: create scene, import model, orient, support, layout, slice, and send to printer.

    Args:
        file_path: Path to the 3D model file.
        material: Material code (e.g. "FLGPBK05").
        layer_height: Layer thickness in mm.
        printer_type: Printer model (default "Form 4").
        copies: Number of copies (default 1).
        printer_id: Target printer ID (optional).
        group_id: Target printer group (optional).
    """
    global _current_scene_id
    steps: list[str] = []

    try:
        # 1. Create scene
        scene = _client.create_scene(printer_type, material, layer_height)
        sid = str(scene.get("id", scene.get("scene_id", "")))
        _current_scene_id = sid
        steps.append(f"1. Scene created (id: {sid})")

        # 2. Import model
        _client.import_model(sid, file_path, auto_orient=True, repair=False)
        steps.append("2. Model imported")

        # 3. Duplicate if copies > 1
        if copies > 1:
            _client.duplicate_model(sid, copies - 1)
            steps.append(f"3. Duplicated to {copies} copies")
        else:
            steps.append("3. Single copy (no duplication needed)")

        # 4. Auto-orient
        _client.auto_orient(sid)
        steps.append("4. Auto-oriented")

        # 5. Generate supports
        _client.auto_support(sid, mode="auto-v2")
        steps.append("5. Supports generated")

        # 6. Auto-layout
        _client.auto_layout(sid)
        steps.append("6. Auto-layout complete")

        # 7. Preview
        try:
            _client.screenshot(sid)
            steps.append("7. Preview generated")
        except PreFormError:
            steps.append("7. Preview skipped (non-critical)")

        # 8. Slice
        _client.slice(sid)
        steps.append("8. Scene sliced")

        # 9. Send to printer
        if printer_id or group_id:
            _client.print_scene(
                sid, printer_id=printer_id, group_id=group_id
            )
            steps.append("9. Sent to printer")
        else:
            steps.append("9. Ready to print (no printer specified)")

        return "Print workflow complete:\n" + "\n".join(steps)

    except PreFormError as e:
        steps.append(f"FAILED: {e}")
        return "Print workflow stopped:\n" + "\n".join(steps)
    except FileNotFoundError as e:
        steps.append(f"FAILED: File not found — {e}")
        return "Print workflow stopped:\n" + "\n".join(steps)


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
