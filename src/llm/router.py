"""LLM router for model selection based on task type."""

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from src.config import get_config

logger = logging.getLogger(__name__)


class TaskType(StrEnum):
    """Task type enumeration for model routing."""
    # Architecture & Planning
    ARCHITECTURE = "architecture"  # System design, high-level planning
    PLAN = "plan"  # Implementation plan, task breakdown

    # Code Implementation
    CODE = "code"  # Writing functions, classes, implementations
    DEBUG = "debug"  # Debugging, fixing errors
    REFACTOR = "refactor"  # Code refactoring, optimization

    # Review & Testing
    REVIEW = "review"  # Code review, quality checking
    TEST = "test"  # Writing tests, test validation
    VALIDATION = "validation"  # Logic validation, edge cases

    # Analysis & Reasoning
    REASONING = "reasoning"  # Complex reasoning, decision making
    ANALYSIS = "analysis"  # Data analysis, pattern recognition
    STRATEGY = "strategy"  # Trading strategy formulation

    # Long Context
    DOCUMENTATION = "documentation"  # Writing docs, comments
    REPORT = "report"  # Generating reports, summaries
    LOG_ANALYSIS = "log_analysis"  # Analyzing logs, traces

    # Quick Interactions
    QUERY = "query"  # Simple questions, lookups
    CONFIG = "config"  # Configuration changes
    STATUS = "status"  # Status checks, health


@dataclass
class ModelRouting:
    """Model routing configuration."""
    model_name: str
    provider: str
    max_tokens: int
    temperature: float
    description: str
    cost_per_1k_tokens: float | None = None


class LLMRouter:
    """Router for selecting appropriate LLM model based on task."""

    # Model registry with default configurations
    MODEL_REGISTRY: dict[str, ModelRouting] = {
        # DeepSeek models (reasoning, code)
        "deepseek-v3.2": ModelRouting(
            model_name="deepseek-v3.2",
            provider="deepseek",
            max_tokens=32768,
            temperature=0.1,
            description="Strong reasoning and complex logic, best for code implementation and debugging",
            cost_per_1k_tokens=0.14
        ),

        # GLM models (planning, architecture)
        "glm5.1": ModelRouting(
            model_name="glm5.1",
            provider="glm",
            max_tokens=16384,
            temperature=0.2,
            description="Good for architecture design and planning, balanced capabilities",
            cost_per_1k_tokens=0.10
        ),

        # Kimi models (review, testing, long context)
        "kimi": ModelRouting(
            model_name="kimi",
            provider="kimi",
            max_tokens=128000,
            temperature=0.1,
            description="Excellent for code review, testing, and long context analysis",
            cost_per_1k_tokens=0.12
        ),

        # Gemini models (long text processing)
        "gemini-pro": ModelRouting(
            model_name="gemini-pro",
            provider="gemini",
            max_tokens=32768,
            temperature=0.2,
            description="Good for long text processing, documentation, reports",
            cost_per_1k_tokens=0.15
        ),

        # MiniMax models (quick interactions)
        "minimax-2.7": ModelRouting(
            model_name="minimax-2.7",
            provider="minimax",
            max_tokens=4096,
            temperature=0.3,
            description="Fast response, good for quick queries and simple tasks",
            cost_per_1k_tokens=0.08
        )
    }

    # Task type to default model mapping - 统一使用 deepseek-v3.2
    DEFAULT_ROUTING: dict[TaskType, str] = {
        # 所有任务类型都使用 deepseek-v3.2
        TaskType.ARCHITECTURE: "deepseek-v3.2",
        TaskType.PLAN: "deepseek-v3.2",
        TaskType.CODE: "deepseek-v3.2",
        TaskType.DEBUG: "deepseek-v3.2",
        TaskType.REFACTOR: "deepseek-v3.2",
        TaskType.REVIEW: "deepseek-v3.2",
        TaskType.TEST: "deepseek-v3.2",
        TaskType.VALIDATION: "deepseek-v3.2",
        TaskType.REASONING: "deepseek-v3.2",
        TaskType.ANALYSIS: "deepseek-v3.2",
        TaskType.STRATEGY: "deepseek-v3.2",
        TaskType.DOCUMENTATION: "deepseek-v3.2",
        TaskType.REPORT: "deepseek-v3.2",
        TaskType.LOG_ANALYSIS: "deepseek-v3.2",
        TaskType.QUERY: "deepseek-v3.2",
        TaskType.CONFIG: "deepseek-v3.2",
        TaskType.STATUS: "deepseek-v3.2"
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize router with configuration."""
        self.config = config or {}
        self._user_overrides = self.config.get("model_overrides", {})

    def get_model_for_task(self, task_type: TaskType | str,
                          context_length: int | None = None) -> ModelRouting:
        """
        Get appropriate model for a given task type.

        Args:
            task_type: Task type enum or string
            context_length: Optional context length to consider for model selection

        Returns:
            ModelRouting configuration
        """
        # Convert string to enum if needed
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type)
            except ValueError:
                # Fallback to default if unknown task type
                task_type = TaskType.REASONING
                logger.warning(f"Unknown task type: {task_type}, falling back to {task_type}")

        # Check for user override first
        if task_type.value in self._user_overrides:
            model_name = self._user_overrides[task_type.value]
            if model_name in self.MODEL_REGISTRY:
                return self.MODEL_REGISTRY[model_name]
            else:
                logger.warning(f"Unknown override model: {model_name}, using default")

        # Use default routing
        model_name = self.DEFAULT_ROUTING[task_type]

        # Handle long context cases
        if context_length and context_length > 32000:
            # 对于长上下文，仍然使用 deepseek-v3.2（支持 32k tokens）
            logger.info(f"Context length {context_length} > 32k, deepseek-v3.2 可以处理")
            # 保持使用 deepseek-v3.2，因为项目契约要求统一使用该模型

        return self.MODEL_REGISTRY[model_name]

    def get_model_by_name(self, model_name: str) -> ModelRouting | None:
        """Get model configuration by name."""
        return self.MODEL_REGISTRY.get(model_name)

    def list_available_models(self) -> list[str]:
        """List all available model names."""
        return list(self.MODEL_REGISTRY.keys())

    def get_models_by_provider(self, provider: str) -> list[ModelRouting]:
        """Get all models from a specific provider."""
        return [model for model in self.MODEL_REGISTRY.values()
                if model.provider == provider]

    def estimate_cost(self, model_name: str, input_tokens: int,
                     output_tokens: int) -> float | None:
        """
        Estimate cost for a given model and token usage.

        Args:
            model_name: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD, or None if cost not available
        """
        model = self.get_model_by_name(model_name)
        if not model or not model.cost_per_1k_tokens:
            return None

        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1000) * model.cost_per_1k_tokens

    def get_recommendation(self, task_description: str,
                          context_length: int = 0) -> ModelRouting:
        """
        Get model recommendation based on task description.

        Args:
            task_description: Natural language description of the task
            context_length: Estimated context length

        Returns:
            Recommended model configuration
        """
        # Simple keyword-based routing (can be enhanced with ML)
        task_lower = task_description.lower()

        # Architecture & Planning keywords
        if any(word in task_lower for word in ["design", "architecture", "plan", "scheme", "structure"]):
            return self.get_model_for_task(TaskType.ARCHITECTURE, context_length)

        # Code implementation keywords
        if any(word in task_lower for word in ["code", "implement", "write", "function", "class", "debug", "fix"]):
            return self.get_model_for_task(TaskType.CODE, context_length)

        # Review & Testing keywords
        if any(word in task_lower for word in ["review", "test", "validate", "check", "inspect", "audit", "testing", "validation"]):
            return self.get_model_for_task(TaskType.REVIEW, context_length)

        # Analysis & Strategy keywords
        if any(word in task_lower for word in ["analyze", "reason", "strategy", "decision", "evaluate"]):
            return self.get_model_for_task(TaskType.ANALYSIS, context_length)

        # Long text keywords
        if any(word in task_lower for word in ["document", "report", "summary", "explain", "describe"]):
            return self.get_model_for_task(TaskType.REPORT, context_length)

        # Quick interaction keywords
        if any(word in task_lower for word in ["query", "ask", "config", "setting", "status"]):
            return self.get_model_for_task(TaskType.QUERY, context_length)

        # Default to reasoning
        return self.get_model_for_task(TaskType.REASONING, context_length)


# Global router instance
_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    """Get the global router instance."""
    global _router
    if _router is None:
        config = get_config()
        _router = LLMRouter(config.model_dump())
    return _router


def set_router(router: LLMRouter) -> None:
    """Set the global router instance."""
    global _router
    _router = router
