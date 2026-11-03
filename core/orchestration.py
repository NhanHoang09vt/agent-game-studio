"""
Multi-Agent Orchestration Engine for AI Game Development Studio.
Features:
- Hierarchical Delegation (Executive Producer -> Directors -> Department Leads -> Specialists)
- Directed Acyclic Graph (DAG) Parallel Execution with concurrency limits and file locking
- Inter-Agent Typed Message Bus
- Cross-Model Multi-Provider Review Matrix & Consensus Arbiter
"""

import asyncio
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from core.types import (
    AgentLifecycleStatus,
    CanonicalMessage,
    MessageRole,
    MessageType,
    ProviderCompletionResponse,
)
from core.agent_runtime import AgentManager
from core.security import FileLockManager, PermissionManager


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    REVIEWING = "reviewing"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskNode(BaseModel):
    task_id: str
    title: str
    assigned_agent_id: str
    instruction: str
    dependencies: List[str] = Field(default_factory=list)
    affected_files: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result_content: Optional[str] = None
    review_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class InterAgentMessage(BaseModel):
    message_id: str
    sender_id: str
    receiver_id: str
    task_id: Optional[str] = None
    message_type: MessageType
    context: Dict[str, Any] = Field(default_factory=dict)
    payload: str
    timestamp: float = Field(default_factory=time.time)
    status: str = "delivered"


class MessageBus:
    """Inter-agent communication hub"""

    def __init__(self):
        self._history: List[InterAgentMessage] = []

    def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        message_type: MessageType,
        payload: str,
        task_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> InterAgentMessage:
        msg = InterAgentMessage(
            message_id=f"msg_{int(time.time()*1000)}_{len(self._history)}",
            sender_id=sender_id,
            receiver_id=receiver_id,
            task_id=task_id,
            message_type=message_type,
            context=context or {},
            payload=payload,
        )
        self._history.append(msg)
        return msg

    def get_messages_for_task(self, task_id: str) -> List[InterAgentMessage]:
        return [m for m in self._history if m.task_id == task_id]

    def get_conversation_between(self, agent_a: str, agent_b: str) -> List[InterAgentMessage]:
        return [
            m for m in self._history
            if (m.sender_id == agent_a and m.receiver_id == agent_b)
            or (m.sender_id == agent_b and m.receiver_id == agent_a)
        ]

    def get_all_messages(self, limit: int = 100) -> List[InterAgentMessage]:
        return self._history[-limit:]


class CrossModelReviewEngine:
    """
    Submits an artifact produced by Model A to independent reviewers running Model B, C, D.
    Aggregates findings, identifies conflicts, and synthesizes an actionable consensus report.
    """

    def __init__(self, agent_manager: AgentManager, message_bus: MessageBus):
        self.agent_manager = agent_manager
        self.message_bus = message_bus

    async def conduct_peer_review(
        self,
        task_id: str,
        author_agent_id: str,
        artifact_content: str,
        reviewer_agent_ids: List[str],
    ) -> Dict[str, Any]:
        review_tasks = []

        for rev_id in reviewer_agent_ids:
            rev_instance = self.agent_manager.get_instance(rev_id)
            if not rev_instance:
                continue

            rev_prompt = f"""
You are conducting an independent peer review for task: {task_id}.
Author Agent: {author_agent_id}
Your Model: {rev_instance.definition.assigned_model} ({rev_instance.definition.assigned_provider})

Review the following output against your specialized criteria:
- Technical correctness and stability
- Alignment with core game pillars and design rules
- Potential edge cases or performance bottlenecks
- Data-driven principles (no hardcoded magic numbers)

ARTIFACT TO REVIEW:
{artifact_content}

Output your findings as:
1. VERDICT: [APPROVED / NEEDS_REVISION / REJECTED]
2. SEVERITY: [LOW / MEDIUM / HIGH / CRITICAL]
3. DETAILED FINDINGS: (Bullet points)
4. SUGGESTED FIXES: (Specific code/design changes)
"""
            self.message_bus.send_message(
                sender_id=author_agent_id,
                receiver_id=rev_id,
                message_type=MessageType.REVIEW,
                payload=f"Requesting review for task {task_id}",
                task_id=task_id,
            )

            review_tasks.append((rev_id, rev_instance.execute_task(f"review_{task_id}_{rev_id}", rev_prompt)))

        results = {}
        verdicts = []
        for rev_id, fut in review_tasks:
            try:
                resp = await fut
                review_text = resp.content
                results[rev_id] = review_text

                # Parse verdict
                if "APPROVED" in review_text.upper():
                    verdicts.append("APPROVED")
                elif "REJECTED" in review_text.upper():
                    verdicts.append("REJECTED")
                else:
                    verdicts.append("NEEDS_REVISION")

                self.message_bus.send_message(
                    sender_id=rev_id,
                    receiver_id=author_agent_id,
                    message_type=MessageType.RESPONSE,
                    payload=review_text,
                    task_id=task_id,
                )
            except Exception as e:
                results[rev_id] = f"Review failed: {e}"
                verdicts.append("ERROR")

        # Consensus determination
        approved_count = verdicts.count("APPROVED")
        total_valid = len([v for v in verdicts if v != "ERROR"])
        consensus = "APPROVED" if (total_valid > 0 and approved_count == total_valid) else "NEEDS_REVISION"

        return {
            "task_id": task_id,
            "author_agent_id": author_agent_id,
            "consensus": consensus,
            "verdicts": verdicts,
            "reviewer_feedback": results,
            "reviewers_count": len(review_tasks),
        }


class MultiAgentOrchestrationEngine:
    """
    Core orchestrator supporting DAG task execution, parallel runs,
    file locking, cross-model reviews, and hierarchical delegation.
    """

    def __init__(
        self,
        agent_manager: AgentManager,
        file_lock_manager: Optional[FileLockManager] = None,
        permission_manager: Optional[PermissionManager] = None,
        max_parallel_agents: int = 5,
    ):
        self.agent_manager = agent_manager
        self.file_lock_manager = file_lock_manager or FileLockManager()
        self.permission_manager = permission_manager or PermissionManager()
        self.max_parallel_agents = max_parallel_agents
        self.message_bus = MessageBus()
        self.review_engine = CrossModelReviewEngine(self.agent_manager, self.message_bus)
        self._semaphore = asyncio.Semaphore(max_parallel_agents)

    def validate_dag(self, tasks: List[TaskNode]) -> bool:
        """Ensure task graph has no cycles"""
        adj: Dict[str, List[str]] = {t.task_id: t.dependencies for t in tasks}
        visited: Dict[str, int] = {}  # 0: visiting, 1: visited

        def has_cycle(node: str) -> bool:
            if visited.get(node) == 0:
                return True
            if visited.get(node) == 1:
                return False
            visited[node] = 0
            for dep in adj.get(node, []):
                if dep in adj and has_cycle(dep):
                    return True
            visited[node] = 1
            return False

        for t in tasks:
            if t.task_id not in visited:
                if has_cycle(t.task_id):
                    return False
        return True

    async def execute_task_graph(
        self,
        tasks: List[TaskNode],
        enable_cross_model_review: bool = True,
        reviewer_agent_ids: Optional[List[str]] = None,
    ) -> Dict[str, TaskNode]:
        """
        Executes a graph of tasks with maximum parallel concurrency,
        respecting task dependencies and file-level write mutexes.
        """
        if not self.validate_dag(tasks):
            raise ValueError("Invalid Task Graph: Cycle detected in dependencies.")

        task_dict: Dict[str, TaskNode] = {t.task_id: t for t in tasks}
        completed_tasks: Set[str] = set()
        failed_tasks: Set[str] = set()

        async def run_single_task(task: TaskNode):
            async with self._semaphore:
                task.status = TaskStatus.RUNNING
                task.start_time = time.time()

                # Acquire file locks for affected files
                for fpath in task.affected_files:
                    await self.file_lock_manager.acquire_lock(fpath)

                try:
                    instance = self.agent_manager.get_instance(task.assigned_agent_id)
                    if not instance:
                        raise ValueError(f"Agent '{task.assigned_agent_id}' not found.")

                    # Context includes previous dependency outputs
                    context_docs = {}
                    for dep_id in task.dependencies:
                        dep_task = task_dict.get(dep_id)
                        if dep_task and dep_task.result_content:
                            context_docs[f"Task_{dep_id}_Output"] = dep_task.result_content

                    resp = await instance.execute_task(
                        task_id=task.task_id,
                        task_instruction=task.instruction,
                        context_docs=context_docs,
                    )
                    task.result_content = resp.content

                    # Optional Peer Review Pass
                    if enable_cross_model_review and reviewer_agent_ids:
                        task.status = TaskStatus.REVIEWING
                        review_result = await self.review_engine.conduct_peer_review(
                            task_id=task.task_id,
                            author_agent_id=task.assigned_agent_id,
                            artifact_content=task.result_content,
                            reviewer_agent_ids=reviewer_agent_ids,
                        )
                        task.review_summary = review_result

                    task.status = TaskStatus.COMPLETED
                    completed_tasks.add(task.task_id)

                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    failed_tasks.add(task.task_id)
                finally:
                    task.end_time = time.time()
                    for fpath in task.affected_files:
                        await self.file_lock_manager.release_lock(fpath)

        # Loop until all tasks are executed or blocked
        while len(completed_tasks) + len(failed_tasks) < len(tasks):
            ready_tasks = [
                t for t in tasks
                if t.status == TaskStatus.PENDING
                and all(dep in completed_tasks for dep in t.dependencies)
            ]

            if not ready_tasks:
                # If there are pending tasks but none are ready, they might be blocked by failed tasks
                for t in tasks:
                    if t.status == TaskStatus.PENDING:
                        if any(dep in failed_tasks for dep in t.dependencies):
                            t.status = TaskStatus.BLOCKED
                            t.error_message = "Blocked by failure of dependent task."
                            failed_tasks.add(t.task_id)
                break

            # Execute ready tasks in parallel
            await asyncio.gather(*(run_single_task(t) for t in ready_tasks))

        return task_dict

    async def execute_hierarchical_delegation(
        self,
        project_goal: str,
        director_agent_id: str = "creative-director",
        lead_agent_id: str = "game-designer",
        specialist_agent_id: str = "systems-designer",
    ) -> Dict[str, Any]:
        """
        Executes Tier 1 (Director) -> Tier 2 (Lead) -> Tier 3 (Specialist) delegation flow.
        """
        # Step 1: Director high-level framing
        dir_task = TaskNode(
            task_id="tier1_framing",
            title="Strategic Framing & Goals",
            assigned_agent_id=director_agent_id,
            instruction=f"Establish design pillars and constraints for goal: {project_goal}",
        )

        # Step 2: Department Lead architecture
        lead_task = TaskNode(
            task_id="tier2_breakdown",
            title="Department Specifications",
            assigned_agent_id=lead_agent_id,
            instruction="Break down the director's pillars into concrete mechanics, data schemas, and requirements.",
            dependencies=["tier1_framing"],
        )

        # Step 3: Specialist implementation
        spec_task = TaskNode(
            task_id="tier3_implementation",
            title="Specialist Implementation & Formulas",
            assigned_agent_id=specialist_agent_id,
            instruction="Implement the mathematical formulas, algorithms, and data-driven parameters.",
            dependencies=["tier2_breakdown"],
        )

        results = await self.execute_task_graph(
            [dir_task, lead_task, spec_task],
            enable_cross_model_review=True,
            reviewer_agent_ids=["technical-director"],
        )

        return {
            "director_output": results["tier1_framing"].result_content,
            "lead_output": results["tier2_breakdown"].result_content,
            "specialist_output": results["tier3_implementation"].result_content,
            "review": results["tier3_implementation"].review_summary,
        }
