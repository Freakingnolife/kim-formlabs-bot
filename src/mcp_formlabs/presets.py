"""Print presets for common use cases."""

from __future__ import annotations

PRESETS = {
    "miniatures": {
        "name": "Miniatures",
        "description": "High detail for small models and figurines",
        "material_code": "FLGPGR05",
        "material_name": "Grey V5",
        "layer_height": 0.025,
        "support_mode": "reduced",
        "printer_type": "Form 4",
    },
    "prototypes": {
        "name": "Prototypes",
        "description": "Fast printing for functional prototypes",
        "material_code": "FLFMGR01",
        "material_name": "Fast Model V1",
        "layer_height": 0.1,
        "support_mode": "auto-v2",
        "printer_type": "Form 4",
    },
    "functional": {
        "name": "Functional Parts",
        "description": "Strong, durable parts for mechanical use",
        "material_code": "FLTO2K02",
        "material_name": "Tough 2000 V2",
        "layer_height": 0.05,
        "support_mode": "auto-v2",
        "printer_type": "Form 4",
    },
    "clear": {
        "name": "Clear Prints",
        "description": "Transparent or translucent parts",
        "material_code": "FLGPCL05",
        "material_name": "Clear V5",
        "layer_height": 0.05,
        "support_mode": "auto-v2",
        "printer_type": "Form 4",
    },
    "durable": {
        "name": "Durable Parts",
        "description": "Impact-resistant, polypropylene-like",
        "material_code": "FLDUCL21",
        "material_name": "Durable V2.1",
        "layer_height": 0.05,
        "support_mode": "auto-v2",
        "printer_type": "Form 4",
    },
    "flexible": {
        "name": "Flexible Parts",
        "description": "Soft, rubber-like elastic prints",
        "material_code": "FLELCL02",
        "material_name": "Elastic 50A V2",
        "layer_height": 0.1,
        "support_mode": "auto-v2",
        "printer_type": "Form 4",
    },
    "black": {
        "name": "Black Resin",
        "description": "General purpose black prints",
        "material_code": "FLGPBK05",
        "material_name": "Black V5",
        "layer_height": 0.05,
        "support_mode": "auto-v2",
        "printer_type": "Form 4",
    },
}


def get_preset(name: str) -> dict | None:
    """Get a preset by name (case-insensitive)."""
    return PRESETS.get(name.lower())


def list_presets() -> list[dict]:
    """List all available presets."""
    return [
        {
            "name": key,
            "display_name": p["name"],
            "description": p["description"],
            "material": p["material_name"],
            "layer_height": p["layer_height"],
        }
        for key, p in PRESETS.items()
    ]
