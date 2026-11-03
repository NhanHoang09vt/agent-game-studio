"""
Skills & Workflow Engine for AI Game Development Studio.
Loads and executes the 74 game development skills, parses SKILL.md definitions,
runs phased workflows (Concept -> Systems -> Architecture -> Production -> QA -> Release),
and applies cross-platform rule validation.
"""

import os
import re
import yaml
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.types import CanonicalMessage, MessageRole, ProviderCompletionResponse
from core.agent_runtime import AgentManager
from core.orchestration import MultiAgentOrchestrationEngine, TaskNode


class SkillDefinition(BaseModel):
    skill_id: str
    name: str
    description: str
    argument_hint: Optional[str] = None
    allowed_tools: List[str] = Field(default_factory=list)
    model_tier: str = "sonnet"
    instructions: str
    references: Dict[str, str] = Field(default_factory=dict)
    workflow_steps: List[str] = Field(default_factory=list)


class WorkflowStep(BaseModel):
    step_id: str
    title: str
    skill_id: str
    assigned_agent_id: str
    required: bool = True
    repeatable: bool = False
    expected_artifact_path: Optional[str] = None


class WorkflowTemplate(BaseModel):
    workflow_id: str
    name: str
    description: str
    engine_compatibility: List[str] = Field(default_factory=lambda: ["godot", "unity", "unreal", "threejs", "phaser"])
    steps: List[WorkflowStep] = Field(default_factory=list)


class WorkflowEngine:
    """
    Manages all studio skills and executes end-to-end game production pipelines.
    """

    def __init__(self, agent_manager: AgentManager, orchestration_engine: MultiAgentOrchestrationEngine):
        self.agent_manager = agent_manager
        self.orchestration = orchestration_engine
        self._skills: Dict[str, SkillDefinition] = {}
        self._workflows: Dict[str, WorkflowTemplate] = {}
        self._register_default_workflows()

    def register_skill(self, skill: SkillDefinition) -> None:
        self._skills[skill.skill_id] = skill

    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        return self._skills.get(skill_id)

    def list_skills(self) -> List[SkillDefinition]:
        return list(self._skills.values())

    def register_workflow(self, workflow: WorkflowTemplate) -> None:
        self._workflows[workflow.workflow_id] = workflow

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowTemplate]:
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[WorkflowTemplate]:
        return list(self._workflows.values())

    def load_all_upstream_skills(self, skills_dir: str) -> int:
        """Parse all 74 skills from upstream/.claude/skills/*/SKILL.md"""
        if not os.path.exists(skills_dir):
            return 0
        loaded = 0
        for entry in os.listdir(skills_dir):
            skill_folder = os.path.join(skills_dir, entry)
            skill_md = os.path.join(skill_folder, "SKILL.md")
            if os.path.isdir(skill_folder) and os.path.exists(skill_md):
                try:
                    with open(skill_md, "r", encoding="utf-8") as f:
                        raw = f.read()

                    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
                    if not match:
                        continue
                    fm = yaml.safe_load(match.group(1)) or {}
                    body = match.group(2).strip()

                    # Load references if folder exists
                    refs = {}
                    ref_dir = os.path.join(skill_folder, "references")
                    if os.path.exists(ref_dir):
                        for rfile in os.listdir(ref_dir):
                            rpath = os.path.join(ref_dir, rfile)
                            if os.path.isfile(rpath):
                                with open(rpath, "r", encoding="utf-8", errors="ignore") as rf:
                                    refs[rfile] = rf.read()

                    tools_val = fm.get("allowed-tools", [])
                    if isinstance(tools_val, str):
                        tools_list = [t.strip() for t in tools_val.split(",") if t.strip()]
                    else:
                        tools_list = tools_val

                    skill = SkillDefinition(
                        skill_id=fm.get("name", entry),
                        name=fm.get("name", entry).replace("-", " ").title(),
                        description=fm.get("description", ""),
                        argument_hint=fm.get("argument-hint"),
                        allowed_tools=tools_list,
                        model_tier=fm.get("model", "sonnet"),
                        instructions=body,
                        references=refs,
                    )
                    self.register_skill(skill)
                    loaded += 1
                except Exception:
                    continue
        return loaded

    async def execute_skill(
        self,
        skill_id: str,
        assigned_agent_id: str,
        user_arguments: str = "",
        project_context: Optional[Dict[str, str]] = None,
    ) -> ProviderCompletionResponse:
        skill = self.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill '{skill_id}' not found.")

        instance = self.agent_manager.get_instance(assigned_agent_id)
        if not instance:
            raise ValueError(f"Agent '{assigned_agent_id}' not found.")

        task_id = f"skill_{skill_id}_{int(time.time()*1000)}"
        prompt = f"""
EXECUTE SKILL: {skill.name} ({skill.skill_id})
User Arguments: {user_arguments or 'None'}

Instructions:
{skill.instructions}
"""
        context_docs = project_context or {}
        # Include skill references
        for rname, rcontent in skill.references.items():
            context_docs[f"SkillRef_{rname}"] = rcontent[:2000]

        return await instance.execute_task(task_id, prompt, context_docs=context_docs)

    async def run_workflow(
        self,
        workflow_id: str,
        project_name: str,
        game_brief: str,
    ) -> Dict[str, Any]:
        """Runs the entire pipeline using DAG task scheduling"""
        wf = self.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        tasks: List[TaskNode] = []
        prev_id: Optional[str] = None

        for idx, step in enumerate(wf.steps):
            task_node = TaskNode(
                task_id=f"wf_{step.step_id}",
                title=f"{step.title} ({step.skill_id})",
                assigned_agent_id=step.assigned_agent_id,
                instruction=f"Execute workflow step {step.title} using skill {step.skill_id}. Brief: {game_brief}",
                dependencies=[prev_id] if prev_id else [],
                affected_files=[step.expected_artifact_path] if step.expected_artifact_path else [],
            )
            tasks.append(task_node)
            prev_id = task_node.task_id

        results = await self.orchestration.execute_task_graph(tasks, enable_cross_model_review=False)
        return {
            "workflow_id": workflow_id,
            "project_name": project_name,
            "step_results": {k: v.result_content for k, v in results.items()},
        }

    def _register_default_workflows(self) -> None:
        """Register the 7 standard game studio production workflows"""
        # Minimal Path Workflow
        minimal_wf = WorkflowTemplate(
            workflow_id="minimal-game-jam",
            name="Minimal Game Jam Pipeline",
            description="Rapid prototyping: Brief -> Stories -> Dev Story -> Verification",
            steps=[
                WorkflowStep(step_id="brief", title="Game Brief", skill_id="brainstorm", assigned_agent_id="creative-director", expected_artifact_path="design/game-brief.md"),
                WorkflowStep(step_id="stories", title="Create Stories", skill_id="create-stories", assigned_agent_id="producer", expected_artifact_path="production/epics/story-01.md"),
                WorkflowStep(step_id="build", title="Dev Story", skill_id="dev-story", assigned_agent_id="lead-programmer", expected_artifact_path="src/gameplay/core.gd"),
                WorkflowStep(step_id="verify", title="Story Done Verification", skill_id="story-done", assigned_agent_id="qa-lead"),
            ],
        )
        self.register_workflow(minimal_wf)

        # Full Commercial Studio Workflow
        full_wf = WorkflowTemplate(
            workflow_id="full-studio-pipeline",
            name="Full Commercial Studio Pipeline",
            description="Comprehensive AAA/Indie pipeline: Concept -> GDD -> Architecture -> DB -> Prototype -> QA -> Release",
            steps=[
                WorkflowStep(step_id="concept", title="High Concept & Pillars", skill_id="brainstorm", assigned_agent_id="creative-director"),
                WorkflowStep(step_id="gdd", title="Game Design Document", skill_id="design-system", assigned_agent_id="game-designer"),
                WorkflowStep(step_id="art", title="Art Bible & Visual Palette", skill_id="art-bible", assigned_agent_id="art-director"),
                WorkflowStep(step_id="audio", title="Audio Strategy & SFX", skill_id="team-audio", assigned_agent_id="audio-director"),
                WorkflowStep(step_id="arch", title="Technical Architecture & ADR", skill_id="create-architecture", assigned_agent_id="technical-director"),
                WorkflowStep(step_id="code", title="Gameplay Implementation", skill_id="team-combat", assigned_agent_id="lead-programmer"),
                WorkflowStep(step_id="qa", title="Comprehensive QA & Regression", skill_id="qa-plan", assigned_agent_id="qa-lead"),
                WorkflowStep(step_id="release", title="Release Checklist & Packaging", skill_id="release-checklist", assigned_agent_id="release-manager"),
            ],
        )
        self.register_workflow(full_wf)
