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

try:
    from scipy.spatial import ConvexHull
    from scipy.cluster.hierarchy import fcluster, linkage
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


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


@dataclass
class FlatSurfaceCluster:
    """A cluster of co-planar faces forming a flat surface."""
    normal: tuple[float, float, float]
    area: float  # mm² (convex hull area of the cluster)
    center: tuple[float, float, float]
    face_count: int
    face_indices: list[int] = field(default_factory=list)


@dataclass
class OrientationScore:
    """Score for a candidate print orientation."""
    rotation: tuple[float, float, float]  # (rx, ry, rz) in degrees
    overhang_area: float  # mm² of faces needing supports
    base_contact_area: float  # mm² touching the build plate
    support_volume_estimate: float  # mm³ rough support volume
    score: float = 0.0  # lower is better


@dataclass
class GripPointSuggestion:
    """A suggested grip/fixture contact point on the mesh."""
    position: tuple[float, float, float]
    normal: tuple[float, float, float]  # outward surface normal at this point
    flatness: float  # 0-1, how flat the local neighbourhood is
    stability: float  # 0-1, how close to COM projection
    accessibility: float  # 0-1, how exposed the point is
    score: float = 0.0  # composite score (higher is better)


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

    # ------------------------------------------------------------------
    # Advanced analysis methods
    # ------------------------------------------------------------------

    def find_flat_surface_clusters(
        self, mesh: trimesh.Trimesh, angle_threshold: float = 10.0, min_area: float = 5.0
    ) -> list[FlatSurfaceCluster]:
        """Cluster faces by normal direction and compute accurate surface areas.

        Uses scipy hierarchical clustering on face normals, then ConvexHull
        to measure the projected area of each cluster.

        Args:
            mesh: A trimesh mesh object.
            angle_threshold: Max angle (degrees) between normals in a cluster.
            min_area: Discard clusters smaller than this (mm²).

        Returns:
            List of FlatSurfaceCluster sorted by area descending.
        """
        if not HAS_SCIPY:
            raise ImportError("scipy is required for clustering. Install with: pip install scipy")

        normals = mesh.face_normals
        areas = mesh.area_faces
        centroids = mesh.triangles_center

        # Hierarchical clustering on unit normals (cosine distance via 1 - dot)
        # Ward linkage needs Euclidean, so we cluster the normal vectors directly
        Z = linkage(normals, method="ward")
        # Convert angle threshold to a rough Euclidean distance between unit vectors
        # |a - b|² = 2 - 2*cos(θ)  =>  |a - b| = sqrt(2 - 2*cos(θ))
        cos_thresh = np.cos(np.radians(angle_threshold))
        dist_thresh = np.sqrt(2.0 - 2.0 * cos_thresh)
        labels = fcluster(Z, t=dist_thresh, criterion="distance")

        clusters: list[FlatSurfaceCluster] = []
        for label in np.unique(labels):
            mask = labels == label
            face_idx = np.nonzero(mask)[0]
            cluster_area_simple = float(np.sum(areas[mask]))
            if cluster_area_simple < min_area:
                continue

            avg_normal = np.mean(normals[mask], axis=0)
            norm = np.linalg.norm(avg_normal)
            if norm < 1e-8:
                continue
            avg_normal /= norm

            centers = centroids[mask]
            avg_center = np.mean(centers, axis=0)

            # Project face centres onto the plane perpendicular to avg_normal
            # to compute the ConvexHull area of the cluster footprint.
            cluster_area = cluster_area_simple  # fallback
            if len(centers) >= 3:
                try:
                    # Build a 2D basis on the plane
                    arbitrary = np.array([1, 0, 0]) if abs(avg_normal[0]) < 0.9 else np.array([0, 1, 0])
                    u = np.cross(avg_normal, arbitrary)
                    u /= np.linalg.norm(u)
                    v = np.cross(avg_normal, u)
                    pts_2d = np.column_stack([centers @ u, centers @ v])
                    hull = ConvexHull(pts_2d)
                    cluster_area = float(hull.volume)  # 2D ConvexHull: volume == area
                except Exception:
                    pass  # keep fallback sum of triangle areas

            clusters.append(FlatSurfaceCluster(
                normal=tuple(avg_normal),
                area=cluster_area,
                center=tuple(avg_center),
                face_count=int(mask.sum()),
                face_indices=face_idx.tolist(),
            ))

        clusters.sort(key=lambda c: c.area, reverse=True)
        return clusters

    def find_optimal_orientation(
        self, mesh: trimesh.Trimesh, steps: int = 12
    ) -> OrientationScore:
        """Sample rotations and return the one that minimises supports.

        For each candidate rotation the method computes:
        - overhang area   (faces whose rotated normal has z < -0.1)
        - base contact    (faces whose rotated normal has z >  0.95)
        - support volume  (rough: overhang_area × average overhang height)

        A simple composite score = overhang_area - 0.5 * base_contact_area
        is minimised.

        Args:
            mesh: A trimesh mesh object.
            steps: Number of angle samples per axis (total candidates = steps³).

        Returns:
            The best OrientationScore.
        """
        normals = mesh.face_normals
        areas = mesh.area_faces
        centroids = mesh.triangles_center
        bounds = mesh.bounds
        mesh_height = bounds[1][2] - bounds[0][2]

        angles = np.linspace(0, 360, steps, endpoint=False)

        best: OrientationScore | None = None

        for rx in angles:
            for ry in angles:
                for rz in angles:
                    R = trimesh.transformations.euler_matrix(
                        np.radians(rx), np.radians(ry), np.radians(rz), axes="sxyz"
                    )[:3, :3]
                    rot_normals = normals @ R.T

                    # Overhangs: rotated normal pointing down (z < -0.1)
                    overhang_mask = rot_normals[:, 2] < -0.1
                    overhang_area = float(np.sum(areas[overhang_mask]))

                    # Base contact: rotated normal pointing up (z > 0.95)
                    base_mask = rot_normals[:, 2] > 0.95
                    base_contact = float(np.sum(areas[base_mask]))

                    # Rough support volume: avg height of overhang centroids × area
                    if np.any(overhang_mask):
                        rot_centroids = centroids[overhang_mask] @ R.T
                        avg_height = float(np.mean(np.abs(rot_centroids[:, 2] - bounds[0][2])))
                        support_vol = overhang_area * avg_height
                    else:
                        support_vol = 0.0

                    score = overhang_area - 0.5 * base_contact
                    candidate = OrientationScore(
                        rotation=(float(rx), float(ry), float(rz)),
                        overhang_area=overhang_area,
                        base_contact_area=base_contact,
                        support_volume_estimate=support_vol,
                        score=score,
                    )
                    if best is None or score < best.score:
                        best = candidate

        assert best is not None
        return best

    def suggest_grip_points(
        self, mesh: trimesh.Trimesh, n_points: int = 6
    ) -> list[GripPointSuggestion]:
        """Score candidate grip points on the mesh surface.

        Candidates are face centroids. Each is scored on:
        - flatness:      alignment of the face normal with neighbours.
        - stability:     proximity to the vertical projection of the COM.
        - accessibility: how exposed/exterior the point is (distance from COM).

        Args:
            mesh: A trimesh mesh object.
            n_points: How many top suggestions to return.

        Returns:
            List of GripPointSuggestion sorted by composite score descending.
        """
        normals = mesh.face_normals
        centroids = mesh.triangles_center

        try:
            com = mesh.center_mass
        except Exception:
            com = np.mean(mesh.bounds, axis=0)

        # Pre-compute adjacency for flatness
        adjacency = mesh.face_adjacency  # (N, 2) pairs of adjacent faces

        # Build neighbour normal map
        n_faces = len(normals)
        neighbour_normals: dict[int, list[int]] = {i: [] for i in range(n_faces)}
        for a, b in adjacency:
            neighbour_normals[a].append(b)
            neighbour_normals[b].append(a)

        # Flatness: average dot product with neighbour normals
        flatness = np.zeros(n_faces)
        for i in range(n_faces):
            nbrs = neighbour_normals[i]
            if nbrs:
                dots = normals[nbrs] @ normals[i]
                flatness[i] = float(np.mean(dots))
            else:
                flatness[i] = 0.0
        # Clamp to [0, 1]
        flatness = np.clip(flatness, 0.0, 1.0)

        # Stability: inverse of horizontal distance from COM projection
        horiz_dist = np.sqrt(
            (centroids[:, 0] - com[0]) ** 2 + (centroids[:, 1] - com[1]) ** 2
        )
        max_horiz = horiz_dist.max() if horiz_dist.max() > 0 else 1.0
        stability = 1.0 - (horiz_dist / max_horiz)

        # Accessibility: distance from COM (farther = more exposed)
        dist_from_com = np.linalg.norm(centroids - com, axis=1)
        max_dist = dist_from_com.max() if dist_from_com.max() > 0 else 1.0
        accessibility = dist_from_com / max_dist

        # Composite score (equal weights)
        composite = (flatness + stability + accessibility) / 3.0

        # Top n indices
        top_idx = np.argsort(composite)[::-1][:n_points]

        suggestions: list[GripPointSuggestion] = []
        for i in top_idx:
            suggestions.append(GripPointSuggestion(
                position=tuple(centroids[i]),
                normal=tuple(normals[i]),
                flatness=float(flatness[i]),
                stability=float(stability[i]),
                accessibility=float(accessibility[i]),
                score=float(composite[i]),
            ))
        return suggestions


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

    # ------------------------------------------------------------------
    # Example 4: Advanced mesh analysis on a simple box
    # ------------------------------------------------------------------
    if HAS_TRIMESH and HAS_NUMPY and HAS_SCIPY:
        print("\n--- Advanced Mesh Analysis (box 40x30x20) ---")
        box = trimesh.primitives.Box(extents=[40, 30, 20])
        mesh = box.to_mesh()
        analyzer = MeshAnalyzer()

        # 4a – Flat surface clusters
        clusters = analyzer.find_flat_surface_clusters(mesh, angle_threshold=10.0)
        print(f"\nFlat surface clusters: {len(clusters)}")
        for c in clusters:
            print(f"  normal={tuple(round(n, 2) for n in c.normal)}, "
                  f"area={c.area:.1f} mm², faces={c.face_count}")

        # 4b – Optimal orientation (use coarse steps for speed)
        best = analyzer.find_optimal_orientation(mesh, steps=6)
        print(f"\nBest orientation: rotation={best.rotation}")
        print(f"  overhang={best.overhang_area:.1f} mm², "
              f"base_contact={best.base_contact_area:.1f} mm², "
              f"support_vol={best.support_volume_estimate:.1f} mm³, "
              f"score={best.score:.1f}")

        # 4c – Grip point suggestions
        grips = analyzer.suggest_grip_points(mesh, n_points=4)
        print(f"\nGrip point suggestions: {len(grips)}")
        for g in grips:
            print(f"  pos=({g.position[0]:.1f}, {g.position[1]:.1f}, {g.position[2]:.1f}), "
                  f"flat={g.flatness:.2f}, stab={g.stability:.2f}, "
                  f"acc={g.accessibility:.2f}, score={g.score:.2f}")
    else:
        print("\nSkipping advanced analysis (trimesh/numpy/scipy not available)")
