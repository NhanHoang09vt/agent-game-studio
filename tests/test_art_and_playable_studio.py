"""
Comprehensive Tests for AI Game Art & Asset Production Studio + Playable Demo.
"""

import os
import pytest
from fastapi.testclient import TestClient
from dashboard.api_server import app
from core.art_direction import ArtDirectionManager, ArtBible, ArtStyle, CameraPerspective, ColorPalette
from core.character_studio import CharacterStudio, CharacterIdentityProfile
from core.monster_studio import MonsterStudio, MonsterProfile, MonsterTier
from core.environment_studio import EnvironmentStudio, TilesetSpec, BiomeType
from core.asset_processor import AssetProcessor
from core.asset_consistency import AssetConsistencyEngine
from core.playable_pipeline import PlayablePipeline


@pytest.fixture
def client():
    return TestClient(app)


def test_art_bible_creation():
    mgr = ArtDirectionManager("./tests_data/art_bibles")
    bible = mgr.get_bible("project_cyberpunk")
    assert bible.project_id == "project_cyberpunk"
    assert bible.tile_size_px == 32
    assert bible.character_height_px == 48
    assert bible.palette.primary is not None


def test_character_studio_registration():
    studio = CharacterStudio("./tests_data/characters")
    profile = CharacterIdentityProfile(
        character_id="hero_valen",
        name="Valen Blade",
        race="Cyber-Human",
        role="Duelist",
        outfit_description="High-collar nanoweave trench coat with glowing cyan seams",
        key_visual_traits=["Crimson ponytail", "Visor eyepiece", "Plasma katana"],
        color_scheme={"hair": "#e11d48", "coat": "#1e293b", "blade": "#38bdf8"},
    )
    studio.register_character(profile)
    fetched = studio.get_character("hero_valen")
    assert fetched is not None
    assert fetched.name == "Valen Blade"
    assert "Plasma katana" in fetched.key_visual_traits


def test_monster_studio_and_evolution():
    studio = MonsterStudio("./tests_data/monsters")
    m1 = MonsterProfile(
        monster_id="acid_slime",
        name="Acid Slime",
        species="Slime",
        tier=MonsterTier.NORMAL,
        evolution_stage=1,
        evolution_line_id="slime_line",
        silhouette_traits=["Amorphous blob", "Bouncing nucleus"],
        color_palette=["#10b981", "#059669"],
        anatomy_notes="Acidic gelatinous membrane with high bounce elasticity",
        material_types=["slime"],
        combat_role="melee_swarmer",
    )
    m2 = MonsterProfile(
        monster_id="king_slime",
        name="Acid Slime King",
        species="Slime",
        tier=MonsterTier.MINI_BOSS,
        evolution_stage=2,
        evolution_line_id="slime_line",
        silhouette_traits=["Giant crowned blob", "Encrusted jewels"],
        color_palette=["#047857", "#eab308"],
        anatomy_notes="Massive slime holding an absorbed golden crown",
        material_types=["slime", "gold"],
        combat_role="tank",
    )
    studio.register_monster(m1)
    studio.register_monster(m2)

    chain = studio.get_evolution_chain("slime_line")
    assert len(chain) == 2
    assert chain[0].name == "Acid Slime"
    assert chain[1].name == "Acid Slime King"


def test_asset_processor_and_consistency():
    pipeline = PlayablePipeline("./tests_data/playable_test")
    bundle = pipeline.generate_complete_game_bundle("test_game")

    player_img_path = bundle.assets["player"]["output_path"]
    assert os.path.exists(player_img_path)

    # Inspect image metadata
    meta = AssetProcessor.inspect_image(player_img_path)
    assert meta["width"] == 192  # 4 cols * 48px
    assert meta["height"] == 144  # 3 rows * 48px
    assert meta["has_transparency"] is True

    # Audit consistency against Art Bible
    mgr = ArtDirectionManager("./tests_data/art_bibles")
    bible = mgr.get_bible("test_game")
    audit = AssetConsistencyEngine.audit_asset_consistency(player_img_path, bible)
    assert audit["is_engine_ready"] is True
    assert audit["verdict"] in ["APPROVED", "WARNING"]


def test_playable_game_endpoint(client):
    res = client.get("/game")
    assert res.status_code == 200
    assert "<canvas id=\"gameCanvas\"" in res.text
    assert "player_spritesheet.png" in res.text
    assert "monster_slime.png" in res.text
    assert "dungeon_tileset.png" in res.text


def test_art_api_endpoints(client):
    # Test GET Art Bible
    res_b = client.get("/api/art/bible?project_id=neon_chronicles")
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["style"] == "pixel_art_32bit"

    # Test GET Bundle Status
    res_s = client.get("/api/art/bundle-status?project_id=neon_chronicles")
    assert res_s.status_code == 200
    data_s = res_s.json()
    assert data_s["is_generated"] is True
    assert data_s["playable_url"] == "/game"
