"""
AI Agent Management System & Runtime Engine.
Manages Agent definitions, dynamic provider/model assignments, lifecycle state machine,
prompt templates, tools, and execution history.
"""

import os
import re
import json
import yaml
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from core.types import (
    AgentLifecycleStatus,
    CanonicalMessage,
    MessageRole,
    MessageType,
    ProviderCompletionResponse,
    TokenUsage,
)
from core.provider_manager import ProviderManager


class AgentAuditEntry(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    from_status: AgentLifecycleStatus
    to_status: AgentLifecycleStatus
    task_id: Optional[str] = None
    note: Optional[str] = None
    tokens_used: int = 0
    cost_usd: float = 0.0


class AgentDefinition(BaseModel):
    agent_id: str
    name: str
    tier: int = 3  # 1: Director, 2: Department Lead, 3: Specialist
    department: str  # executive, game-design, programming, art, animation, audio, narrative, qa, production, etc.
    role: str
    description: str
    system_prompt: str
    assigned_provider: str = "claude"
    assigned_model: str = "claude-3-7-sonnet-20250219"
    backup_model: Optional[str] = "gpt-4o"
    tools: List[str] = Field(default_factory=lambda: ["Read", "Write", "Edit", "Grep", "Glob"])
    disallowed_tools: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=lambda: ["read_project", "propose_changes"])
    skills: List[str] = Field(default_factory=list)
    knowledge_base_refs: List[str] = Field(default_factory=list)
    memory_scope: str = "project"  # project, session, global
    output_format: str = "markdown"
    quality_criteria: List[str] = Field(default_factory=list)
    max_turns: int = 30
    temperature: float = 0.7


class AgentRuntimeInstance:
    """Live state machine and execution wrapper for an Agent"""

    def __init__(self, definition: AgentDefinition, provider_manager: ProviderManager):
        self.definition = definition
        self.provider_manager = provider_manager
        self.status: AgentLifecycleStatus = AgentLifecycleStatus.IDLE
        self.current_task_id: Optional[str] = None
        self.history: List[AgentAuditEntry] = []
        self.total_tokens_consumed: int = 0
        self.total_cost_consumed: float = 0.0

    def transition_to(self, new_status: AgentLifecycleStatus, task_id: Optional[str] = None, note: Optional[str] = None) -> None:
        entry = AgentAuditEntry(
            from_status=self.status,
            to_status=new_status,
            task_id=task_id or self.current_task_id,
            note=note,
        )
        self.history.append(entry)
        self.status = new_status
        if task_id:
            self.current_task_id = task_id
        if new_status in [AgentLifecycleStatus.IDLE, AgentLifecycleStatus.COMPLETED, AgentLifecycleStatus.FAILED, AgentLifecycleStatus.CANCELLED]:
            self.current_task_id = None

    async def execute_task(
        self,
        task_id: str,
        task_instruction: str,
        context_docs: Optional[Dict[str, str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ProviderCompletionResponse:
        self.transition_to(AgentLifecycleStatus.WORKING, task_id=task_id, note="Started execution")

        # Compose messages
        system_content = self.definition.system_prompt
        if context_docs:
            context_block = "\n\n=== RELEVANT PROJECT CONTEXT ===\n"
            for doc_name, doc_content in context_docs.items():
                context_block += f"--- {doc_name} ---\n{doc_content}\n\n"
            system_content += context_block

        messages = [
            CanonicalMessage(role=MessageRole.SYSTEM, content=system_content),
            CanonicalMessage(role=MessageRole.USER, content=task_instruction),
        ]

        try:
            resp = await self.provider_manager.execute_chat_with_fallback(
                provider_id=self.definition.assigned_provider,
                model_id=self.definition.assigned_model,
                messages=messages,
                temperature=self.definition.temperature,
                tools=tools,
            )

            self.total_tokens_consumed += resp.usage.total_tokens
            self.total_cost_consumed += resp.usage.estimated_cost_usd

            self.history[-1].tokens_used = resp.usage.total_tokens
            self.history[-1].cost_usd = resp.usage.estimated_cost_usd

            self.transition_to(AgentLifecycleStatus.COMPLETED, task_id=task_id, note="Task completed successfully")
            return resp

        except Exception as e:
            self.transition_to(AgentLifecycleStatus.FAILED, task_id=task_id, note=f"Execution error: {e}")
            raise e


class AgentManager:
    """
    Studio-wide manager for all agent definitions.
    Supports importing from upstream markdown files, CRUD, cloning, and dynamic re-assignments.
    """

    def __init__(self, provider_manager: ProviderManager, agents_storage_dir: Optional[str] = None):
        self.provider_manager = provider_manager
        self.storage_dir = agents_storage_dir or "./data/agents"
        self._agents: Dict[str, AgentDefinition] = {}
        self._instances: Dict[str, AgentRuntimeInstance] = {}
        os.makedirs(self.storage_dir, exist_ok=True)
        self._register_default_matrix()

    def register_agent(self, agent: AgentDefinition) -> None:
        self._agents[agent.agent_id] = agent
        self._instances[agent.agent_id] = AgentRuntimeInstance(agent, self.provider_manager)

    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        return self._agents.get(agent_id)

    def get_instance(self, agent_id: str) -> Optional[AgentRuntimeInstance]:
        return self._instances.get(agent_id)

    def list_agents(self, department: Optional[str] = None, tier: Optional[int] = None) -> List[AgentDefinition]:
        res = list(self._agents.values())
        if department:
            res = [a for a in res if a.department.lower() == department.lower()]
        if tier:
            res = [a for a in res if a.tier == tier]
        return res

    def update_agent_model(self, agent_id: str, provider_id: str, model_id: str, backup_model: Optional[str] = None) -> bool:
        agent = self.get_agent(agent_id)
        if not agent:
            return False
        agent.assigned_provider = provider_id
        agent.assigned_model = model_id
        if backup_model:
            agent.backup_model = backup_model
        return True

    def clone_agent(self, source_agent_id: str, new_agent_id: str, new_name: str) -> Optional[AgentDefinition]:
        source = self.get_agent(source_agent_id)
        if not source:
            return None
        cloned_data = source.model_dump()
        cloned_data["agent_id"] = new_agent_id
        cloned_data["name"] = new_name
        new_agent = AgentDefinition(**cloned_data)
        self.register_agent(new_agent)
        return new_agent

    def delete_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            if agent_id in self._instances:
                del self._instances[agent_id]
            return True
        return False

    def export_agent_yaml(self, agent_id: str) -> Optional[str]:
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        return yaml.dump(agent.model_dump(), sort_keys=False)

    def import_agent_yaml(self, yaml_content: str) -> AgentDefinition:
        data = yaml.safe_load(yaml_content)
        agent = AgentDefinition(**data)
        self.register_agent(agent)
        return agent

    def import_from_upstream_markdown(self, file_path: str) -> Optional[AgentDefinition]:
        """Parse CCGS .claude/agents/*.md files with YAML frontmatter"""
        if not os.path.exists(file_path):
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            return None

        frontmatter_str = match.group(1)
        system_prompt = match.group(2).strip()
        fm = yaml.safe_load(frontmatter_str) or {}

        agent_id = fm.get("name", os.path.basename(file_path).replace(".md", ""))
        desc = fm.get("description", "")
        tools_str = fm.get("tools", "")
        tools = [t.strip() for t in tools_str.split(",") if t.strip()] if isinstance(tools_str, str) else []
        disallowed_str = fm.get("disallowedTools", "")
        disallowed = [t.strip() for t in disallowed_str.split(",") if t.strip()] if isinstance(disallowed_str, str) else []

        tier = 3
        dept = "specialists"
        if agent_id in ["creative-director", "technical-director", "producer", "ai-operations-director"]:
            tier = 1
            dept = "executive"
        elif agent_id in ["game-designer", "lead-programmer", "art-director", "audio-director", "narrative-director", "qa-lead", "release-manager", "localization-lead"]:
            tier = 2
            dept = "leads"

        # Multi-provider model assignment mapping
        provider_map = {
            "creative-director": ("claude", "claude-3-7-sonnet-20250219"),
            "technical-director": ("openai", "gpt-4o"),
            "producer": ("claude", "claude-3-5-sonnet-20241022"),
            "ai-operations-director": ("openai", "o3-mini"),
            "game-designer": ("gemini", "gemini-2.5-pro"),
            "lead-programmer": ("deepseek", "deepseek-chat"),
            "art-director": ("gemini", "gemini-2.5-pro"),
            "audio-director": ("muse", "muse-audio-engine"),
            "narrative-director": ("muse", "muse-story-pro"),
            "qa-lead": ("openai", "gpt-4o"),
            "systems-designer": ("dogxiai", "dogxiai-game-master"),
            "economy-designer": ("dogxiai", "dogxiai-balance-bot"),
            "gameplay-programmer": ("deepseek", "deepseek-chat"),
            "engine-programmer": ("deepseek", "deepseek-reasoner"),
            "ai-programmer": ("deepseek", "deepseek-chat"),
        }

        assigned_provider, assigned_model = provider_map.get(agent_id, ("claude", "claude-3-5-sonnet-20241022"))

        agent = AgentDefinition(
            agent_id=agent_id,
            name=agent_id.replace("-", " ").title(),
            tier=tier,
            department=dept,
            role=desc.split(".")[0] if desc else agent_id,
            description=desc,
            system_prompt=system_prompt,
            assigned_provider=assigned_provider,
            assigned_model=assigned_model,
            tools=tools or ["Read", "Write", "Edit"],
            disallowed_tools=disallowed,
            max_turns=fm.get("maxTurns", 30),
            memory_scope=fm.get("memory", "project"),
        )
        self.register_agent(agent)
        return agent

    def load_all_upstream_agents(self, upstream_agents_dir: str) -> int:
        count = 0
        if not os.path.exists(upstream_agents_dir):
            return 0
        for fname in os.listdir(upstream_agents_dir):
            if fname.endswith(".md"):
                fpath = os.path.join(upstream_agents_dir, fname)
                if self.import_from_upstream_markdown(fpath):
                    count += 1
        return count

    def _register_default_matrix(self) -> None:
        """Seed Studio with Tier 1 AI Operations Director and essential Directors"""
        ai_ops = AgentDefinition(
            agent_id="ai-operations-director",
            name="AI Operations Director",
            tier=1,
            department="executive",
            role="Oversees multi-provider model routing, token budgets, and studio-wide agent coordination.",
            description="Manages provider health, budget caps, fallback mechanisms, and cross-model consensus orchestration.",
            system_prompt="You are the AI Operations Director. You ensure model efficiency, optimal provider allocation, and reliable multi-agent orchestration across the entire game studio.",
            assigned_provider="openai",
            assigned_model="o3-mini",
            backup_model="gpt-4o",
            permissions=["manage_providers", "allocate_budgets", "escalate_conflicts"],
        )
        self.register_agent(ai_ops)
