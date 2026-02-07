"""Material code resolution with fuzzy matching."""

from __future__ import annotations

MATERIALS = {
    "FLGPGR05": {"name": "Grey V5", "layers": [0.025, 0.05, 0.1]},
    "FLGPBK05": {"name": "Black V5", "layers": [0.025, 0.05, 0.1]},
    "FLGPCL05": {"name": "Clear V5", "layers": [0.025, 0.05, 0.1]},
    "FLGPWH05": {"name": "White V5", "layers": [0.025, 0.05, 0.1]},
    "FLTO2K02": {"name": "Tough 2000 V2", "layers": [0.05, 0.1]},
    "FLTOTL02": {"name": "Tough 1500 V2", "layers": [0.05, 0.1]},
    "FLDUCL21": {"name": "Durable V2.1", "layers": [0.05, 0.1]},
    "FLELCL02": {"name": "Elastic 50A V2", "layers": [0.05, 0.1]},
    "FLFMGR01": {"name": "Fast Model V1", "layers": [0.05, 0.1, 0.2]},
}

# Keyword → (material_code, default_layer_height)
# Ordered by specificity (longer phrases first)
KEYWORD_MAP = [
    ("tough 2000", "FLTO2K02", 0.1),
    ("tough 1500", "FLTOTL02", 0.1),
    ("fast model", "FLFMGR01", 0.1),
    ("grey v5", "FLGPGR05", 0.05),
    ("black v5", "FLGPBK05", 0.05),
    ("clear v5", "FLGPCL05", 0.05),
    ("white v5", "FLGPWH05", 0.05),
    ("elastic", "FLELCL02", 0.1),
    ("flexible", "FLELCL02", 0.1),
    ("durable", "FLDUCL21", 0.1),
    ("tough", "FLTO2K02", 0.1),  # Default tough to 2000
    ("grey", "FLGPGR05", 0.05),
    ("gray", "FLGPGR05", 0.05),
    ("black", "FLGPBK05", 0.05),
    ("clear", "FLGPCL05", 0.05),
    ("white", "FLGPWH05", 0.05),
    ("fast", "FLFMGR01", 0.1),
]

def parse_material(query: str) -> dict:
    """Parse natural language material query into structured config.
    
    Examples:
        - "tough grey resin" → Tough 2000, 0.05mm
        - "fast mode" → Fast Model, 0.1mm
        - "clear v5 0.025" → Clear V5, 0.025mm
    """
    query_lower = query.lower()
    
    # 1. Identify Material
    material_code = None
    default_layer = 0.05
    
    for keyword, code, layer in KEYWORD_MAP:
        if keyword in query_lower:
            material_code = code
            default_layer = layer
            break
            
    if not material_code:
        # Fallback: Default to Grey if nothing matches
        material_code = "FLGPGR05"
        default_layer = 0.05
        
    # 2. Identify Layer Height
    layer_height = None
    
    # Explicit mm
    if "0.025" in query_lower: layer_height = 0.025
    elif "0.05" in query_lower: layer_height = 0.05
    elif "0.1" in query_lower: layer_height = 0.1
    elif "0.2" in query_lower: layer_height = 0.2
    
    # Keywords
    if layer_height is None:
        if "detail" in query_lower or "fine" in query_lower:
            layer_height = 0.025
        elif "draft" in query_lower or "fast" in query_lower or "speed" in query_lower:
            layer_height = 0.1

    # Fallback to material default
    if layer_height is None:
        layer_height = default_layer
        
    # 3. Validation
    valid_layers = MATERIALS[material_code]["layers"]
    if layer_height not in valid_layers:
        # Snap to nearest
        layer_height = min(valid_layers, key=lambda x: abs(x - layer_height))

    return {
        "material_code": material_code,
        "material_name": MATERIALS[material_code]["name"],
        "layer_height": layer_height
    }
