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

    # Debate Tasks
    DEBATE_QUICK = "debate_quick"  # Bull/Bear single-side argument, fast response
    DEBATE_DEEP = "debate_deep"  # Debate arbitration/final decision, deep reasoning
    DEBATE_SYNTHESIS = "debate_synthesis"  # Debate synthesis summary

    # Position Tasks
    POSITION_MONITOR = "position_monitor"  # Position monitoring, quick check
    POSITION_REFLECT = "position_reflect"  # Delayed reflection, reasoning


@dataclass
class ModelCost:
    """Model cost per million tokens."""
    input_per_million: float
    output_per_million: float

    def estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD."""
        return (input_tokens * self.input_per_million + output_tokens * self.output_per_million) / 1_000_000


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

    # Per-model cost table (input / output per million tokens)
    MODEL_COSTS: dict[str, ModelCost] = {
        "deepseek-v3.2": ModelCost(input_per_million=0.50, output_per_million=1.50),
        "minimax-2.7": ModelCost(input_per_million=0.30, output_per_million=0.80),
        "glm5.1": ModelCost(input_per_million=0.40, output_per_million=1.20),
        "gemini-pro": ModelCost(input_per_million=1.25, output_per_million=5.00),
        "kimi": ModelCost(input_per_million=0.60, output_per_million=1.80),
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize router with configuration."""
        self.config = config or {}
        self._user_overrides = self.config.get("model_overrides", {})
        self._routing = self._build_default_routing()
        self._default_model = get_config().llm.reasoning_model

    @staticmethod
    def _build_default_routing() -> dict[TaskType, str]:
        """基于 LLMConfig 构建默认路由表。"""
        llm_config = get_config().llm
        reasoning = llm_config.model or llm_config.reasoning_model
        quick = llm_config.model or llm_config.quick_model
        long_ctx = llm_config.model or llm_config.long_context_model
        code = llm_config.model or llm_config.code_model

        return {
            # Architecture & Planning
            TaskType.ARCHITECTURE: reasoning,
            TaskType.PLAN: reasoning,
            # Code Implementation
            TaskType.CODE: code,
            TaskType.DEBUG: code,
            TaskType.REFACTOR: code,
            # Review & Testing
            TaskType.REVIEW: reasoning,
            TaskType.TEST: code,
            TaskType.VALIDATION: reasoning,
            # Analysis & Reasoning
            TaskType.REASONING: reasoning,
            TaskType.ANALYSIS: reasoning,
            TaskType.STRATEGY: reasoning,
            # Long Context
            TaskType.DOCUMENTATION: long_ctx,
            TaskType.REPORT: long_ctx,
            TaskType.LOG_ANALYSIS: long_ctx,
            # Quick Interactions
            TaskType.QUERY: quick,
            TaskType.CONFIG: quick,
            TaskType.STATUS: quick,
            # Debate
            TaskType.DEBATE_QUICK: quick,
            TaskType.DEBATE_DEEP: reasoning,
            TaskType.DEBATE_SYNTHESIS: reasoning,
            # Position
            TaskType.POSITION_MONITOR: quick,
            TaskType.POSITION_REFLECT: reasoning,
        }

    LONG_CONTEXT_THRESHOLD = 32000

    def get_model_for_task(self, task_type: TaskType | str,
                          context_length: int | None = None) -> ModelRouting:
        """Get appropriate model for a given task type."""
        # Convert string to enum if needed
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type)
            except ValueError:
                task_type = TaskType.REASONING
                logger.warning(f"Unknown task type: {task_type}, falling back to {task_type}")

        # 1. User override — highest priority, must be a known model
        if task_type.value in self._user_overrides:
            model_name = self._user_overrides[task_type.value]
            if model_name in self.MODEL_REGISTRY:
                return self.MODEL_REGISTRY[model_name]
            logger.warning(f"Unknown override model: {model_name}, falling back to routing")

        # 2. Long context auto-switch (only when no override hit)
        if context_length and context_length > self.LONG_CONTEXT_THRESHOLD:
            long_ctx_model = get_config().llm.long_context_model
            resolved = self._resolve_model(long_ctx_model)
            if resolved:
                logger.info(f"Switching to long-context model {long_ctx_model} for {task_type} (ctx={context_length})")
                return resolved

        # 3. Default routing table
        model_name = self._routing.get(task_type, self._default_model)
        return self._resolve_model(model_name) or self.MODEL_REGISTRY[self._default_model]

    def _resolve_model(self, model_name: str) -> ModelRouting | None:
        """Resolve model name to ModelRouting, supporting dynamic fallback."""
        if model_name in self.MODEL_REGISTRY:
            return self.MODEL_REGISTRY[model_name]

        # Unregistered model — try to infer provider
        provider = self._infer_provider(model_name)
        if provider:
            return ModelRouting(
                model_name=model_name,
                provider=provider,
                max_tokens=4096,
                temperature=0.7,
                description=f"Dynamic routing for {model_name}",
            )
        return None

    @staticmethod
    def _infer_provider(model_name: str) -> str | None:
        """Infer provider from model name."""
        name_lower = model_name.lower()
        if "deepseek" in name_lower:
            return "deepseek"
        if "glm" in name_lower or "chatglm" in name_lower:
            return "glm"
        if "kimi" in name_lower or "moonshot" in name_lower:
            return "kimi"
        if "gemini" in name_lower:
            return "gemini"
        if "minimax" in name_lower:
            return "minimax"
        if "gpt" in name_lower or "openai" in name_lower:
            return "openai"
        if "claude" in name_lower or "anthropic" in name_lower:
            return "anthropic"
        # Generic fallback for custom providers — use provider from config
        return get_config().llm.provider or "deepseek"

    def get_model_by_name(self, model_name: str) -> ModelRouting | None:
        """Get model configuration by name. Returns None for unregistered models."""
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

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for a given text.

        Heuristic: CJK characters ~ 0.5 token/char, others ~ 0.25 token/char.
        """
        if not text:
            return 0
        total = 0.0
        for char in text:
            code = ord(char)
            # CJK Unified Ideographs, Hiragana, Katakana, Hangul
            if (
                0x4E00 <= code <= 0x9FFF
                or 0x3400 <= code <= 0x4DBF
                or 0xF900 <= code <= 0xFAFF
                or 0x3040 <= code <= 0x309F
                or 0x30A0 <= code <= 0x30FF
                or 0xAC00 <= code <= 0xD7AF
            ):
                total += 0.5
            else:
                total += 0.25
        return max(1, int(total))

    def get_cheapest_model(
        self, candidates: list[str], input_tokens: int = 1000, output_tokens: int = 500
    ) -> ModelRouting | None:
        """Return the cheapest model among candidates."""
        cheapest: tuple[float, ModelRouting] | None = None
        for name in candidates:
            routing = self._resolve_model(name)
            if not routing:
                continue
            cost_info = self.MODEL_COSTS.get(name)
            if not cost_info:
                continue
            cost = cost_info.estimate(input_tokens, output_tokens)
            if cheapest is None or cost < cheapest[0]:
                cheapest = (cost, routing)
        return cheapest[1] if cheapest else None

    def get_model_for_task_with_cost_limit(
        self,
        task_type: TaskType | str,
        context_length: int | None = None,
        max_cost_per_request: float | None = None,
        estimated_input_tokens: int = 1000,
        estimated_output_tokens: int = 500,
    ) -> ModelRouting:
        """Get model with optional cost limit."""
        model = self.get_model_for_task(task_type, context_length)

        if max_cost_per_request is None:
            return model

        cost_info = self.MODEL_COSTS.get(model.model_name)
        if cost_info is None:
            return model

        estimated_cost = cost_info.estimate(estimated_input_tokens, estimated_output_tokens)
        if estimated_cost <= max_cost_per_request:
            return model

        # Over budget — try to find a cheaper alternative
        logger.warning(
            f"Model {model.model_name} estimated cost ${estimated_cost:.4f} exceeds "
            f"limit ${max_cost_per_request:.4f}, searching for cheaper alternative"
        )

        # Try quick models first, then others
        candidates = [
            get_config().llm.quick_model,
            get_config().llm.code_model,
            get_config().llm.reasoning_model,
        ]
        cheaper = self.get_cheapest_model(candidates, estimated_input_tokens, estimated_output_tokens)
        if cheaper:
            return cheaper

        return model


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
