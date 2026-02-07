"""Mesh analysis and pre-flight checks using trimesh."""

from __future__ import annotations

import os
import trimesh
import numpy as np

def preflight_check(file_path: str) -> dict:
    """Analyze a 3D mesh for printability."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    try:
        # Load mesh
        mesh = trimesh.load(file_path)
        
        # specific to .3mf or scenes, we might get a Scene object
        if isinstance(mesh, trimesh.Scene):
            # For simplicity, combine all geometries if it's a scene
            if len(mesh.geometry) == 0:
                 return {"error": "Empty scene"}
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

        # 1. Volume (cm3 -> ml)
        volume_mm3 = mesh.volume
        volume_ml = abs(volume_mm3) / 1000.0
        
        # 2. Bounding Box
        bbox = mesh.bounds
        dims = bbox[1] - bbox[0]
        
        # 3. Manifold Check
        is_watertight = mesh.is_watertight
        
        # 4. Overhangs (simple normal check)
        # Faces pointing down (z < -0.7 roughly 45 degrees)
        # This is a heuristic approximation
        down_facing = 0
        if hasattr(mesh, "face_normals"):
            # Normals are (N, 3). Z is index 2.
            # Pointing down means Z component is negative.
            # Critical angle usually ~45 deg. cos(135) = -0.707
            down_facing = np.sum(mesh.face_normals[:, 2] < -0.707)
        
        total_faces = len(mesh.faces)
        overhang_ratio = down_facing / total_faces if total_faces > 0 else 0
        
        recommendations = []
        if not is_watertight:
            recommendations.append("Mesh is not watertight. Repair needed.")
        if volume_ml > 500:
            recommendations.append("Large volume (>500ml). Check resin tank level.")
        if overhang_ratio > 0.1:
            recommendations.append("Significant overhangs detected. Supports likely required.")
        if dims[2] > 200:
             recommendations.append("Object is tall. Verify Z-height fits printer.")

        return {
            "file_name": os.path.basename(file_path),
            "volume_ml": round(volume_ml, 2),
            "is_manifold": is_watertight,
            "bounding_box_mm": [round(d, 1) for d in dims],
            "overhang_ratio": round(overhang_ratio, 3),
            "recommendations": recommendations,
            "triangle_count": len(mesh.faces)
        }

    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}
