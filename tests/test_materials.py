"""Tests for materials.py."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_formlabs.materials import MATERIALS, KEYWORD_MAP, parse_material


class TestMaterials:
    def test_all_materials_have_category(self):
        for code, info in MATERIALS.items():
            assert "category" in info, f"{code} missing category"
            assert info["category"] in ("Standard", "Engineering", "Specialty", "Draft")

    def test_all_materials_have_name(self):
        for code, info in MATERIALS.items():
            assert "name" in info
            assert len(info["name"]) > 0

    def test_all_materials_have_layers(self):
        for code, info in MATERIALS.items():
            assert "layers" in info
            assert len(info["layers"]) > 0
            for layer in info["layers"]:
                assert 0 < layer < 1.0

    def test_parse_grey(self):
        result = parse_material("grey resin")
        assert result["material_code"] == "FLGPGR05"
        assert result["material_name"] == "Grey V5"

    def test_parse_tough_2000(self):
        result = parse_material("tough 2000")
        assert result["material_code"] == "FLTO2K02"

    def test_parse_layer_height_explicit(self):
        result = parse_material("grey 0.025")
        assert result["layer_height"] == 0.025

    def test_parse_detail_keyword(self):
        result = parse_material("grey detail")
        assert result["layer_height"] == 0.025

    def test_parse_draft_keyword(self):
        result = parse_material("grey draft")
        assert result["layer_height"] == 0.1

    def test_parse_unknown_defaults_to_grey(self):
        result = parse_material("something random")
        assert result["material_code"] == "FLGPGR05"

    def test_parse_snaps_invalid_layer(self):
        result = parse_material("elastic 0.025")
        # Elastic doesn't support 0.025, should snap to nearest
        assert result["layer_height"] in MATERIALS["FLELCL02"]["layers"]

    def test_keyword_map_covers_all_materials(self):
        mapped_codes = set(kw[1] for kw in KEYWORD_MAP)
        for code in MATERIALS:
            assert code in mapped_codes, f"{code} has no keyword mapping"
