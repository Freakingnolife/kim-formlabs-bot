"""
Fixture Generator for Kim Formlabs Bot

Generates custom holding fixtures/jigs for 3D printing operations.
Supports both standard object library and custom STL file analysis.

Author: Kim (OpenClaw)
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Optional imports - handle gracefully if not available
try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ObjectDimensions:
    """Dimensions for a standard object."""
    name: str
    length: float  # mm
    width: float   # mm
    height: float  # mm
    grip_points: list[tuple[float, float, float]] = field(default_factory=list)
    flat_surfaces: list[str] = field(default_factory=list)  # "top", "bottom", "left", "right", "front", "back"


@dataclass
class FixtureConfig:
    """Configuration for fixture generation."""
    operation: Literal["drilling", "soldering", "painting", "cnc", "inspection", "gluing"]
    clearance: float = 5.0  # mm clearance for tools
    orientation: Literal["flat", "vertical", "angled"] = "flat"
    grip_type: Literal["cradle", "clamp", "vacuum", "magnetic"] = "cradle"
    tool_access: list[str] = field(default_factory=lambda: ["top"])
    wall_thickness: float = 3.0  # mm
    base_height: float = 10.0  # mm

    def __post_init__(self):
        for name in ("clearance", "wall_thickness", "base_height"):
            value = getattr(self, name)
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {value}")


@dataclass
class AnalysisResult:
    """Result from analyzing a custom STL file."""
    filename: str
    dimensions: tuple[float, float, float]  # (x, y, z)
    center_of_mass: tuple[float, float, float]
    volume: float
    flat_surfaces: list[dict]  # List of {normal: (x,y,z), area: float, center: (x,y,z)}
    grip_points: list[tuple[float, float, float]]
    bounding_box: tuple[tuple[float, float, float], tuple[float, float, float]]  # min, max


# ============================================================================
# Standard Library
# ============================================================================

class StandardLibrary:
    """Pre-defined object dimensions for common items."""
    
    LIBRARY: dict[str, ObjectDimensions] = {
        # iPhone models
        "iphone_15_pro": ObjectDimensions(
            name="iPhone 15 Pro",
            length=146.6,
            width=70.6,
            height=8.25,
            grip_points=[(70, 35, 4), (70, 35, 4)],
            flat_surfaces=["bottom", "back"]
        ),
        "iphone_15_pro_max": ObjectDimensions(
            name="iPhone 15 Pro Max",
            length=159.9,
            width=76.7,
            height=8.25,
            grip_points=[(76, 38, 4)],
            flat_surfaces=["bottom", "back"]
        ),
        "iphone_14": ObjectDimensions(
            name="iPhone 14",
            length=146.7,
            width=71.5,
            height=7.8,
            grip_points=[(71, 36, 4)],
            flat_surfaces=["bottom", "back"]
        ),
        
        # Samsung
        "samsung_s24": ObjectDimensions(
            name="Samsung Galaxy S24",
            length=147.0,
            width=70.6,
            height=7.6,
            grip_points=[(70, 35, 4)],
            flat_surfaces=["bottom", "back"]
        ),
        
        # Tools
        "soldering_iron": ObjectDimensions(
            name="Standard Soldering Iron",
            length=220.0,
            width=25.0,
            height=25.0,
            grip_points=[(110, 12, 12)],
            flat_surfaces=["bottom"]
        ),
        
        # Electronics
        "raspberry_pi_4": ObjectDimensions(
            name="Raspberry Pi 4",
            length=85.0,
            width=56.0,
            height=17.0,
            grip_points=[(42, 28, 8)],
            flat_surfaces=["bottom"]
        ),
        "arduino_uno": ObjectDimensions(
            name="Arduino Uno",
            length=68.6,
            width=53.4,
            height=13.0,
            grip_points=[(34, 26, 6)],
            flat_surfaces=["bottom"]
        ),
        
        # Common parts
        "bearing_608": ObjectDimensions(
            name="608 Bearing (8x22x7mm)",
            length=22.0,
            width=22.0,
            height=7.0,
            grip_points=[(11, 11, 3.5)],
            flat_surfaces=["bottom", "sides"]
        ),
    }
    
    @classmethod
    def get(cls, key: str) -> ObjectDimensions | None:
        """Get object dimensions by key."""
        # Normalize key
        key = key.lower().replace(" ", "_").replace("-", "_")
        return cls.LIBRARY.get(key)
    
    @classmethod
    def search(cls, query: str) -> list[tuple[str, ObjectDimensions]]:
        """Search for objects matching query."""
        query = query.lower()
        results = []
        for key, obj in cls.LIBRARY.items():
            if query in key or query in obj.name.lower():
                results.append((key, obj))
        return results
    
    @classmethod
    def list_all(cls) -> list[str]:
        """List all available object keys."""
        return list(cls.LIBRARY.keys())


# ============================================================================
# Mesh Analyzer
# ============================================================================

class MeshAnalyzer:
    """Analyze custom STL files to extract geometry information."""
    
    def __init__(self):
        if not HAS_TRIMESH:
            raise ImportError("trimesh is required for mesh analysis. Install with: pip install trimesh")
        if not HAS_NUMPY:
            raise ImportError("numpy is required for mesh analysis. Install with: pip install numpy")
    
    def analyze(self, filepath: str | Path) -> AnalysisResult:
        """Analyze an STL file and extract key features."""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Load mesh
        mesh = trimesh.load_mesh(filepath)

        # Validate mesh is not empty
        if not hasattr(mesh, 'faces') or len(mesh.faces) == 0:
            raise ValueError(f"Mesh is empty or invalid: {filepath}")

        # Basic dimensions
        bounds = mesh.bounds
        dimensions = tuple(bounds[1] - bounds[0])

        # Center of mass (may fail for non-watertight meshes)
        try:
            com = tuple(mesh.center_mass)
        except Exception:
            com = tuple(np.mean(bounds, axis=0))

        # Volume (may fail for non-watertight meshes)
        try:
            volume = float(mesh.volume)
        except Exception:
            volume = 0.0
        
        # Find flat surfaces (faces with similar normals)
        flat_surfaces = self._find_flat_surfaces(mesh)
        
        # Calculate grip points (center of mass projected to surfaces)
        grip_points = self._calculate_grip_points(mesh, com, flat_surfaces)
        
        return AnalysisResult(
            filename=filepath.name,
            dimensions=dimensions,
            center_of_mass=com,
            volume=volume,
            flat_surfaces=flat_surfaces,
            grip_points=grip_points,
            bounding_box=(tuple(bounds[0]), tuple(bounds[1]))
        )
    
    def _find_flat_surfaces(self, mesh: trimesh.Trimesh) -> list[dict]:
        """Find large flat surfaces on the mesh."""
        surfaces = []
        
        # Get face normals and areas
        normals = mesh.face_normals
        areas = mesh.area_faces
        centroids = mesh.triangles_center
        
        # Group faces by similar normal direction
        directions = {
            "top": [0, 0, 1],
            "bottom": [0, 0, -1],
            "front": [0, -1, 0],
            "back": [0, 1, 0],
            "left": [-1, 0, 0],
            "right": [1, 0, 0],
        }
        
        for name, target_normal in directions.items():
            # Find faces with normals aligned to target
            dot_products = np.dot(normals, target_normal)
            aligned_faces = dot_products > 0.95  # Within ~18 degrees
            
            if np.any(aligned_faces):
                total_area = np.sum(areas[aligned_faces])
                if total_area > 10:  # Minimum 10mm²
                    # Calculate average center
                    centers = centroids[aligned_faces]
                    avg_center = tuple(np.mean(centers, axis=0))
                    
                    surfaces.append({
                        "name": name,
                        "normal": tuple(target_normal),
                        "area": float(total_area),
                        "center": avg_center,
                        "face_count": int(np.sum(aligned_faces))
                    })
        
        # Sort by area (largest first)
        surfaces.sort(key=lambda x: x["area"], reverse=True)
        return surfaces
    
    def _calculate_grip_points(
        self, 
        mesh: trimesh.Trimesh, 
        center_of_mass: tuple,
        flat_surfaces: list[dict]
    ) -> list[tuple[float, float, float]]:
        """Calculate optimal grip point locations."""
        grip_points = []
        
        # Use center of mass as primary grip point
        grip_points.append(center_of_mass)
        
        # Add points from flat surfaces
        for surface in flat_surfaces[:3]:  # Top 3 surfaces
            # Offset from surface center toward interior
            normal = np.array(surface["normal"])
            center = np.array(surface["center"])
            
            # Move 2mm inward from surface
            grip_point = tuple(center - normal * 2)
            grip_points.append(grip_point)
        
        return grip_points


# ============================================================================
# Fixture Generator
# ============================================================================

class FixtureGenerator:
    """Generate OpenSCAD code for fixtures."""
    
    def __init__(self, output_dir: str | Path = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        obj: ObjectDimensions | AnalysisResult,
        config: FixtureConfig,
        name: str = "fixture"
    ) -> str:
        """Generate OpenSCAD code for a fixture."""
        
        # Sanitize name for OpenSCAD (replace special chars with underscores)
        name = re.sub(r'[^a-zA-Z0-9_\- ]', '_', name)

        if isinstance(obj, ObjectDimensions):
            dims = (obj.length, obj.width, obj.height)
            grip_points = obj.grip_points
            flat_surfaces = obj.flat_surfaces
        else:
            dims = obj.dimensions
            grip_points = obj.grip_points
            flat_surfaces = [s["name"] for s in obj.flat_surfaces]

        length, width, height = dims

        # Generate OpenSCAD code
        scad = self._generate_scad(
            name=name,
            dims=dims,
            grip_points=grip_points,
            config=config,
            flat_surfaces=flat_surfaces
        )
        
        # Save to file
        output_path = self.output_dir / f"{name}.scad"
        with open(output_path, 'w') as f:
            f.write(scad)
        
        return str(output_path)
    
    def _generate_scad(
        self,
        name: str,
        dims: tuple[float, float, float],
        grip_points: list,
        config: FixtureConfig,
        flat_surfaces: list
    ) -> str:
        """Generate OpenSCAD code."""
        
        length, width, height = dims
        wall = config.wall_thickness
        base_h = config.base_height
        clearance = config.clearance
        
        # Calculate fixture dimensions
        fx = length + wall * 2 + clearance * 2
        fy = width + wall * 2 + clearance * 2
        fz = height + base_h + wall
        
        # Generate SCAD code
        scad = f'''// Fixture for: {name}
// Generated by Kim Formlabs Bot
// Operation: {config.operation}

// Dimensions
object_length = {length:.2f};
object_width = {width:.2f};
object_height = {height:.2f};
wall_thickness = {wall:.2f};
base_height = {base_h:.2f};
clearance = {clearance:.2f};

// Calculated
total_length = object_length + wall_thickness * 2 + clearance * 2;
total_width = object_width + wall_thickness * 2 + clearance * 2;
total_height = object_height + base_height + wall_thickness;

module object_cutout() {{
    translate([wall_thickness + clearance, 
               wall_thickness + clearance, 
               base_height])
        cube([object_length, object_width, object_height + 1]);
}}

module grip_cutouts() {{
    // Side access cutouts
    translate([total_length/2 - 10, -1, base_height + object_height/2])
        cube([20, total_width + 2, 10]);
    
    // Front/back access
    translate([-1, total_width/2 - 10, base_height + object_height/2])
        cube([total_length + 2, 20, 10]);
}}

module fixture() {{
    difference() {{
        // Main block
        cube([total_length, total_width, total_height]);
        
        // Object cavity
        object_cutout();
        
        // Tool access
        grip_cutouts();
        
        // Text label
        translate([total_length/2, total_width/2, total_height - 0.5])
            linear_extrude(1)
                text("{name}", size=5, halign="center", valign="center");
    }}
}}

// Render
fixture();
'''
        return scad
    
    def render_stl(self, scad_path: str | Path) -> str:
        """Render OpenSCAD file to STL."""
        scad_path = Path(scad_path)
        
        if not scad_path.exists():
            raise FileNotFoundError(f"SCAD file not found: {scad_path}")
        
        # Output STL path
        stl_path = scad_path.with_suffix('.stl')
        
        # Run OpenSCAD CLI
        try:
            subprocess.run(
                ['openscad', str(scad_path), '-o', str(stl_path)],
                check=True,
                capture_output=True,
                timeout=60
            )
            return str(stl_path)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"OpenSCAD rendering failed: {e.stderr.decode()}")
        except FileNotFoundError:
            raise RuntimeError("OpenSCAD not found. Install with: brew install openscad")
        except subprocess.TimeoutExpired:
            raise RuntimeError("OpenSCAD rendering timed out")


# ============================================================================
# Main API
# ============================================================================

def generate_fixture(
    target: str | Path,
    operation: str,
    clearance: float = 5.0,
    orientation: str = "flat",
    grip_type: str = "cradle",
    output_dir: str = "."
) -> dict:
    """
    Main entry point for fixture generation.
    
    Args:
        target: Object key (e.g., "iphone_15_pro") or path to STL file
        operation: Type of operation (drilling, soldering, painting, etc.)
        clearance: Tool clearance in mm
        orientation: Object orientation (flat, vertical, angled)
        grip_type: How to hold the object (cradle, clamp, etc.)
        output_dir: Where to save generated files
    
    Returns:
        dict with paths to generated files and metadata
    """
    config = FixtureConfig(
        operation=operation,
        clearance=clearance,
        orientation=orientation,
        grip_type=grip_type
    )
    
    generator = FixtureGenerator(output_dir)
    
    # Check if target is a file path or standard library key
    target_path = Path(target)
    
    if target_path.exists() and target_path.suffix.lower() in ['.stl', '.obj']:
        # Custom STL file
        if not HAS_TRIMESH:
            return {
                "success": False,
                "error": "trimesh required for STL analysis. Install: pip install trimesh"
            }
        
        analyzer = MeshAnalyzer()
        obj = analyzer.analyze(target_path)
        name = target_path.stem + "_fixture"
        
    else:
        # Standard library
        obj = StandardLibrary.get(str(target))
        if obj is None:
            # Try search
            results = StandardLibrary.search(str(target))
            if results:
                obj = results[0][1]
                name = results[0][0] + "_fixture"
            else:
                available = ", ".join(StandardLibrary.list_all()[:10])
                return {
                    "success": False,
                    "error": f"Object '{target}' not found. Try: {available}..."
                }
        else:
            name = str(target).lower().replace(" ", "_") + "_fixture"
    
    # Generate SCAD
    try:
        scad_path = generator.generate(obj, config, name)
        
        # Try to render STL
        stl_path = None
        try:
            stl_path = generator.render_stl(scad_path)
        except RuntimeError as e:
            # OpenSCAD not installed - return SCAD only
            pass
        
        return {
            "success": True,
            "scad_path": scad_path,
            "stl_path": stl_path,
            "object_type": "custom_stl" if isinstance(obj, AnalysisResult) else "standard",
            "object_name": obj.name if isinstance(obj, ObjectDimensions) else obj.filename,
            "dimensions": obj.dimensions if isinstance(obj, AnalysisResult) else (obj.length, obj.width, obj.height),
            "config": {
                "operation": operation,
                "clearance": clearance,
                "orientation": orientation,
                "grip_type": grip_type
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Example 1: Standard library object
    print("Example 1: iPhone 15 Pro fixture for soldering")
    result = generate_fixture(
        target="iphone_15_pro",
        operation="soldering",
        clearance=10.0,
        output_dir="./fixtures"
    )
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"SCAD: {result['scad_path']}")
        print(f"STL: {result['stl_path']}")
    print()
    
    # Example 2: List available objects
    print("Available standard objects:")
    for key in StandardLibrary.list_all():
        print(f"  - {key}")
    print()
    
    # Example 3: Search
    print("Search for 'iphone':")
    results = StandardLibrary.search("iphone")
    for key, obj in results:
        print(f"  - {key}: {obj.name}")
