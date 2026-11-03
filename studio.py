"""
Main CLI Entrypoint for AI Game Development Studio — Multi-Agent Edition.
Usage:
    python studio.py dashboard       # Start the Web Dashboard server
    python studio.py test            # Run full test suite
    python studio.py providers       # List all configured providers
    python studio.py agents          # List all studio agents
"""

import sys
import os
import uvicorn
import pytest
from core.provider_manager import ProviderManager
from core.agent_runtime import AgentManager


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "dashboard":
        port = int(os.environ.get("STUDIO_PORT", 8000))
        host = os.environ.get("STUDIO_HOST", "127.0.0.1")
        print("==================================================================")
        print("   AI GAME DEVELOPMENT STUDIO — MULTI-AGENT EDITION (v2.0.0)      ")
        print("==================================================================")
        print(f" Studio Dashboard running at: http://{host}:{port}")
        print(f" REST API Docs available at:  http://{host}:{port}/docs")
        print("==================================================================")
        uvicorn.run("dashboard.api_server:app", host=host, port=port, reload=False)

    elif sys.argv[1] == "test":
        print("Running full automated studio test suite...")
        sys.exit(pytest.main(["tests/", "-v"]))

    elif sys.argv[1] == "providers":
        pm = ProviderManager()
        print("\n--- CONNECTED AI PROVIDERS ---")
        for s in pm.get_all_statuses():
            cfg = "Configured" if s.is_configured else "Offline/Mock"
            print(f"• {s.name:<20} | Status: {cfg:<15} | Default Model: {s.default_model}")
        print()

    elif sys.argv[1] == "agents":
        pm = ProviderManager()
        am = AgentManager(pm)
        upstream_dir = os.path.join(os.path.dirname(__file__), "upstream", ".claude", "agents")
        loaded = am.load_all_upstream_agents(upstream_dir)
        print(f"\n--- STUDIO AGENTS ROSTER ({loaded} Loaded) ---")
        for a in am.list_agents():
            print(f"• Tier {a.tier} | {a.name:<26} | Model: {a.assigned_model} ({a.assigned_provider})")
        print()

    elif sys.argv[1] == "play":
        import webbrowser
        port = int(os.environ.get("STUDIO_PORT", 8000))
        host = os.environ.get("STUDIO_HOST", "127.0.0.1")
        url = f"http://{host}:{port}/game"
        print(f"Opening Playable Prototype Demo at: {url}")
        webbrowser.open(url)
        uvicorn.run("dashboard.api_server:app", host=host, port=port, reload=False)

    elif sys.argv[1] == "generate-art":
        from core.playable_pipeline import PlayablePipeline
        print("Generating complete engine-ready playable art bundle...")
        pipe = PlayablePipeline(output_root="dashboard/static/playable")
        pkg = pipe.generate_complete_game_bundle("neon_chronicles")
        print(f"Success! Package: {pkg.package_id}")
        print("Assets created: player_spritesheet.png, monster_slime.png, dungeon_tileset.png, UI icons.")

    else:
        print("Usage: python studio.py [dashboard | play | generate-art | test | providers | agents]")


if __name__ == "__main__":
    main()
