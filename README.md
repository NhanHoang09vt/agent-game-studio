# AI Game Development Studio — Multi-Agent Edition
### Enterprise Multi-Provider AI Agent Orchestration Platform for Professional Game Development

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Agents: 50](https://img.shields.io/badge/Agents-50-purple)](#studio-organization)
[![Skills: 74](https://img.shields.io/badge/Skills-74-green)](#skills-and-workflows)
[![Providers: 7](https://img.shields.io/badge/Providers-7-orange)](#supported-ai-providers)
[![Tests: 21 Passing](https://img.shields.io/badge/Tests-21%20Passed-brightgreen)](#automated-testing)

---

## 1. Overview & Vision

**AI Game Development Studio — Multi-Agent Edition** transforms game development into an orchestrated, collaborative virtual game studio. Rather than relying on a single chat window or locking your studio into a single AI provider, this platform allows your studio to recruit models from across the entire AI ecosystem:

- **Anthropic Claude 3.7 Sonnet / Opus** acting as Creative Director and Narrative Lead.
- **OpenAI GPT-4o / o3-mini** serving as Technical Director and AI Operations Director.
- **Google Gemini 2.5 Pro (2M Context & Multimodal)** driving Game Design and Art Direction.
- **DeepSeek-V3 / DeepSeek-R1** providing ultra-fast, data-driven gameplay algorithms and engine programming.
- **Muse AI** designing procedural dialogues, lore bibles, and audio sound palettes.
- **Dogxiai** computing combat balance curves, loot drop economies, and mathematical simulations.
- **Custom / Local AI (vLLM, Ollama, LM Studio)** executing offline or on private hardware.

### 🏛️ Open Source Heritage & Attribution
This project is an advanced, multi-provider architectural expansion built upon the foundational work of [Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) by **Donchitos**, released under the MIT License. 
The Multi-Agent Edition preserves 100% of the game development domain wisdom, agent personas, 74 skills, rules, templates, and collaborative principles from upstream while decoupling from vendor lock-in and introducing a cross-platform orchestration runtime and modern SaaS dashboard.

---

## 2. Key Architecture Pillars

```
+-----------------------------------------------------------------------------------+
|                        STUDIO DASHBOARD & CLI (studio.py)                         |
+-----------------------------------------------------------------------------------+
                                       |
+-----------------------------------------------------------------------------------+
|                        MULTI-AGENT ORCHESTRATION ENGINE                           |
|  - Hierarchical Delegation Engine (Executive -> Directors -> Leads -> Specialists)|
|  - Parallel Task Scheduler & DAG Dependency Engine (Asyncio + File Locking)       |
|  - Cross-Model Peer Review & Consensus Reconciliation Matrix                     |
|  - Inter-Agent Typed Message Bus (Request, Review, Approval, Escalation)        |
+-----------------------------------------------------------------------------------+
                                       |
+-----------------------------------------------------------------------------------+
|                             CORE RUNTIME SERVICES                                 |
|  - Agent Runtime & State Machine (Idle, Assigned, Working, Reviewing, Completed)   |
|  - 4-Tiered Memory Manager (Global, Project, Agent Memory, Task Context)          |
|  - Security & Permission Arbiter (RBAC, File Mutex, Secret Guard, Rollback)       |
|  - Multi-Project & Engine Profiles (Godot 4, Unity 6, UE5, Phaser, Three.js)     |
+-----------------------------------------------------------------------------------+
                                       |
+-----------------------------------------------------------------------------------+
|                          AI PROVIDER ABSTRACTION LAYER                            |
+-----------------------------------------------------------------------------------+
    |             |             |             |            |           |         |
+-------+     +-------+     +-------+     +--------+   +------+    +-------+ +------+
|OpenAI |     |Gemini |     |Claude |     |DeepSeek|   | Muse |    |Dogxiai| |Custom|
|Adapter|     |Adapter|     |Adapter|     |Adapter |   |Adaptr|    |Adapter| |Adaptr|
+-------+     +-------+     +-------+     +--------+   +------+    +-------+ +------+
```

### 1. Multi-Provider AI Abstraction Layer
A unified `AIProviderInterface` normalizes messages, streaming chunks, tool calls, and structured JSON schemas across OpenAI, Claude, Gemini, DeepSeek, Muse, Dogxiai, and Custom endpoints. Every provider tracks request latency, token consumption, and cost in USD.

### 2. Cross-Model Peer Review & Reconciliation
A game artifact produced by one model family can be automatically submitted to independent reviewers running different models.
*Example Workflow:*
1. **Lead Programmer (DeepSeek-V3)** writes a combat damage formula.
2. **QA Lead (OpenAI GPT-4o)** reviews edge cases, divide-by-zero risks, and test coverage.
3. **Technical Director (Claude 3.7 Sonnet)** verifies data-driven rules (no hardcoded constants) and architectural boundaries.
4. **Game Designer (Gemini 2.5 Pro)** validates pacing, player progression, and balance curves.
5. **Consensus Arbiter** compiles feedback, flags conflicts, and seeks Studio Owner approval.

### 3. Hierarchical Delegation & DAG Parallel Execution
Tasks are organized into Directed Acyclic Graphs (DAGs). Independent tasks execute concurrently with concurrency limits and file-locking mutexes (`FileLockManager`) to eliminate race conditions.

### 4. Strict Context & Project Isolation
The 4-tier memory architecture (`Global`, `Project`, `Agent`, `Task`) guarantees that intellectual property, GDDs, and entities from Project A never leak into Project B.

---

## 3. Supported AI Providers & Models

| Provider | Supported Models | Primary Studio Roles |
|---|---|---|
| **Anthropic Claude** | `claude-3-7-sonnet`, `claude-3-5-sonnet`, `claude-3-opus`, `claude-3-5-haiku` | Creative Director, Narrative Director, Localization |
| **OpenAI** | `gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini` | Technical Director, QA Lead, AI Operations Director |
| **Google Gemini** | `gemini-3.8-flash`, `gemini-3.8-pro`, `gemini-2.5-pro` (2M context), `gemini-2.5-flash` | Game Designer, Art Director, Level Designer |
| **DeepSeek** | `deepseek-chat` (V3), `deepseek-reasoner` (R1) | Lead Programmer, Gameplay/Engine/Network Specialists |
| **Muse AI** | `muse-story-pro`, `muse-audio-engine` | World Builder, Dialogue Writer, Audio Director |
| **Dogxiai** | `dogxiai-game-master`, `dogxiai-balance-bot` | Systems Designer, Economy Designer, Combat Balancer |
| **Custom / Local** | Local OpenAI-compatible (`vLLM`, `Ollama`, `LM Studio`) | Offline tasks, custom fine-tuned game studio models |

---

## 4. Studio Organization (50 Agents)

- **Tier 1 — Executive Directors (4 agents):**
  - `creative-director` (Vision, pillars, aesthetic identity, high-level decisions)
  - `technical-director` (Architecture, engine selection, ADRs, performance)
  - `producer` (Scope, schedule, sprint planning, risk management)
  - `ai-operations-director` (Model routing, token budgets, cross-provider health)
- **Tier 2 — Department Leads (8 agents):**
  - `game-designer`, `lead-programmer`, `art-director`, `audio-director`, `narrative-director`, `qa-lead`, `release-manager`, `localization-lead`
- **Tier 3 — Specialists (23 agents):**
  - *Programming:* `gameplay-programmer`, `engine-programmer`, `ai-programmer`, `network-programmer`, `tools-programmer`, `ui-programmer`, `performance-analyst`, `security-engineer`
  - *Design & Art:* `systems-designer`, `level-designer`, `economy-designer`, `technical-artist`, `sound-designer`, `writer`, `world-builder`, `ux-designer`, `prototyper`, `live-ops-designer`
  - *QA & Ops:* `devops-engineer`, `analytics-engineer`, `qa-tester`, `accessibility-specialist`, `community-manager`
- **Engine Specialists (15 dedicated agents):**
  - **Godot 4:** `godot-specialist`, `godot-gdscript-specialist`, `godot-csharp-specialist`, `godot-shader-specialist`, `godot-gdextension-specialist`
  - **Unity:** `unity-specialist`, `unity-dots-specialist`, `unity-shader-specialist`, `unity-addressables-specialist`, `unity-ui-specialist`
  - **Unreal Engine 5:** `unreal-specialist`, `ue-gas-specialist`, `ue-blueprint-specialist`, `ue-replication-specialist`, `ue-umg-specialist`

---

## 5. Quick Start & Installation

### Requirements
- Python 3.10 or higher (Python 3.14 recommended)
- Git (with Git Bash on Windows or standard terminal on Linux/macOS)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/Donchitos/Claude-Code-Game-Studios.git upstream  # If not already present
pip install -r requirements.txt
# Or directly:
pip install fastapi uvicorn pydantic pyyaml httpx pytest pytest-asyncio
```

### 2. Configure Environment Secrets
Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```
*(Any provider left blank will automatically run in dry-run/mock mode for zero-cost testing).*

### 3. Launch Studio Web Dashboard
```bash
python studio.py dashboard
```
Open your browser to:
👉 **`http://localhost:8000`**

To explore interactive REST API documentation:
👉 **`http://localhost:8000/docs`**

---

## 6. CLI Commands

```bash
# Start the Web Dashboard
python studio.py dashboard

# List all connected AI providers and connection states
python studio.py providers

# List all studio agents and their assigned AI models
python studio.py agents

# Run the full automated test suite
python studio.py test
```

---

## 7. Automated Testing & Verification

The project includes an end-to-end automated testing suite with 21 tests covering all layers:

```bash
python -m pytest tests/ -v
```

**Test Matrix:**
- `tests/test_provider_adapters.py`: Provider adapter instantiation, capability checks, cost calculation, and fallback routing.
- `tests/test_orchestration_and_agents.py`: Upstream agent loading (49 agents), dynamic model assignment, DAG cycle detection, parallel execution, and hierarchical delegation.
- `tests/test_workflows_projects_memory.py`: 74 skills loading, multi-project workspace isolation, tiered memory isolation, and 3D/audio asset validation.
- `tests/test_api_server.py`: Complete REST API integration testing with FastAPI TestClient.

---

## 8. License & Attribution

- **Original Upstream Work:** Copyright (c) 2026 Donchitos ([Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios)) under the MIT License.
- **Multi-Agent Edition:** Copyright (c) 2026 AI Game Development Studio Contributors under the MIT License.
