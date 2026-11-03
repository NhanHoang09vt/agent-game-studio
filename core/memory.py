"""
AI Memory & Knowledge Base Management for AI Game Development Studio.
Features 4-tiered memory:
1. Global Knowledge (Studio-wide design patterns, game theory, industry standards)
2. Project Knowledge (Project-specific GDD, lore, architecture, entities)
3. Agent Memory (Agent's learned domain notes, preferred patterns)
4. Task Context (Transient execution scratchpad for active sprint task)
Strict project data isolation guarantees zero cross-project leakage.
"""

import os
import re
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryTier(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"
    AGENT = "agent"
    TASK = "task"


class KnowledgeEntry(BaseModel):
    entry_id: str
    tier: MemoryTier
    project_id: Optional[str] = None  # Mandatory for PROJECT tier
    agent_id: Optional[str] = None    # Mandatory for AGENT tier
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    version: int = 1
    updated_at: float = Field(default_factory=time.time)


class TieredMemoryManager:
    """
    Indexes, retrieves, and isolates studio knowledge across the 4 tiers.
    """

    def __init__(self, storage_dir: str = "./data/memory"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._seed_global_knowledge()

    def store_entry(
        self,
        tier: MemoryTier,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> KnowledgeEntry:
        if tier == MemoryTier.PROJECT and not project_id:
            raise ValueError("project_id is required for PROJECT tier memory.")
        if tier == MemoryTier.AGENT and not agent_id:
            raise ValueError("agent_id is required for AGENT tier memory.")

        entry_id = f"{tier.value}_{int(time.time()*1000)}_{len(self._entries)}"
        entry = KnowledgeEntry(
            entry_id=entry_id,
            tier=tier,
            project_id=project_id,
            agent_id=agent_id,
            title=title,
            content=content,
            tags=tags or [],
        )
        self._entries[entry_id] = entry
        return entry

    def update_entry(self, entry_id: str, new_content: str, new_tags: Optional[List[str]] = None) -> bool:
        if entry_id not in self._entries:
            return False
        entry = self._entries[entry_id]
        entry.content = new_content
        entry.version += 1
        entry.updated_at = time.time()
        if new_tags is not None:
            entry.tags = new_tags
        return True

    def retrieve_context_for_agent(
        self,
        agent_id: str,
        project_id: str,
        query: str,
        limit: int = 5,
    ) -> List[KnowledgeEntry]:
        """
        Retrieves relevant knowledge strictly within:
        - Global Knowledge
        - This Project's Knowledge (strictly no other project)
        - This Agent's Memory
        """
        tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        scored_results: List[tuple[float, KnowledgeEntry]] = []

        for entry in self._entries.values():
            # Check strict project isolation
            if entry.tier == MemoryTier.PROJECT and entry.project_id != project_id:
                continue
            # Check agent isolation
            if entry.tier == MemoryTier.AGENT and entry.agent_id != agent_id:
                continue

            score = 0.0
            entry_text = (entry.title + " " + entry.content + " " + " ".join(entry.tags)).lower()

            for token in tokens:
                if token in entry_text:
                    score += 1.0
                if token in [t.lower() for t in entry.tags]:
                    score += 2.0

            if score > 0 or not tokens:
                scored_results.append((score, entry))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored_results[:limit]]

    def _seed_global_knowledge(self) -> None:
        """Seed foundational game development principles into Global Memory"""
        self.store_entry(
            tier=MemoryTier.GLOBAL,
            title="Separation of Concerns in Gameplay Architecture",
            content="Always keep gameplay formulas and state isolated from presentation and rendering. Use delta time for all time-dependent motion. Use events or signals for cross-system triggers.",
            tags=["architecture", "gameplay", "standard"],
        )
        self.store_entry(
            tier=MemoryTier.GLOBAL,
            title="Data-Driven Combat Formulas",
            content="Never hardcode damage, attack speed, or loot drop multipliers in scripts. Read all curves from external configuration or resource assets.",
            tags=["combat", "balance", "data-driven"],
        )
