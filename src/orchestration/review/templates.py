"""ReviewTemplate dataclass, YAML loader, and template registry."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from orchestration.review.models import TemplateValidationError


@dataclass
class InputDef:
    """Definition of a template input (CLI argument)."""

    name: str
    description: str
    default: str | None = None


@dataclass
class ReviewTemplate:
    """Runtime representation of a review workflow template. Loaded from YAML."""

    name: str
    description: str
    system_prompt: str
    allowed_tools: list[str]
    permission_mode: str
    setting_sources: list[str] | None
    required_inputs: list[InputDef]
    optional_inputs: list[InputDef]
    hooks: dict[str, object] | None = None

    # Prompt construction — exactly one of these is set (validated at load time)
    prompt_template: str | None = None
    prompt_builder: Callable[[dict[str, str]], str] | None = None

    def build_prompt(self, inputs: dict[str, str]) -> str:
        """Construct the review prompt from user-supplied inputs."""
        if self.prompt_builder is not None:
            return self.prompt_builder(inputs)
        if self.prompt_template is not None:
            return self.prompt_template.format(**inputs)
        raise ValueError(
            f"Template '{self.name}' has neither prompt_template nor prompt_builder"
        )


# ---------------------------------------------------------------------------
# YAML Loader
# ---------------------------------------------------------------------------


def _resolve_builder(dotted_path: str) -> Callable[[dict[str, str]], str]:
    """Resolve a dotted Python path to a callable."""
    parts = dotted_path.rsplit(".", 1)
    if len(parts) != 2:
        raise TemplateValidationError(
            f"prompt_builder must be a dotted path (module.function), "
            f"got: {dotted_path}"
        )
    module_path, func_name = parts
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise TemplateValidationError(
            f"Cannot import module '{module_path}' for prompt_builder"
        ) from exc

    func = getattr(module, func_name, None)
    if func is None:
        raise TemplateValidationError(
            f"Module '{module_path}' has no attribute '{func_name}'"
        )
    if not callable(func):
        raise TemplateValidationError(f"'{dotted_path}' is not callable")
    return func  # type: ignore[return-value]


def load_template(path: Path) -> ReviewTemplate:
    """Load a ReviewTemplate from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise TemplateValidationError(f"Template file is not a YAML mapping: {path}")

    # Validate mutually exclusive prompt fields
    has_template = "prompt_template" in data
    has_builder = "prompt_builder" in data
    if has_template and has_builder:
        raise TemplateValidationError(
            f"Template '{path}' specifies both prompt_template and prompt_builder"
        )
    if not has_template and not has_builder:
        raise TemplateValidationError(
            f"Template '{path}' must specify prompt_template or prompt_builder"
        )

    # Resolve prompt_builder to callable if specified
    builder = None
    if has_builder:
        builder = _resolve_builder(data["prompt_builder"])

    # Parse input definitions
    inputs_data = data.get("inputs", {})
    required = [InputDef(**i) for i in inputs_data.get("required", [])]
    optional = [InputDef(**i) for i in inputs_data.get("optional", [])]

    return ReviewTemplate(
        name=data["name"],
        description=data["description"],
        system_prompt=data["system_prompt"],
        allowed_tools=data["allowed_tools"],
        permission_mode=data["permission_mode"],
        setting_sources=data.get("setting_sources"),
        required_inputs=required,
        optional_inputs=optional,
        hooks=data.get("hooks"),
        prompt_template=data.get("prompt_template"),
        prompt_builder=builder,
    )


# ---------------------------------------------------------------------------
# Template Registry
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, ReviewTemplate] = {}


def register_template(template: ReviewTemplate) -> None:
    """Register a template by name."""
    _TEMPLATES[template.name] = template


def get_template(name: str) -> ReviewTemplate | None:
    """Look up a template by name. Returns None if not found."""
    return _TEMPLATES.get(name)


def list_templates() -> list[ReviewTemplate]:
    """Return all registered templates."""
    return list(_TEMPLATES.values())


def clear_registry() -> None:
    """Remove all registered templates. Useful for testing."""
    _TEMPLATES.clear()


def load_builtin_templates() -> None:
    """Load all YAML templates from the builtin templates directory."""
    builtin_dir = Path(__file__).parent / "templates" / "builtin"
    if not builtin_dir.is_dir():
        return
    for yaml_file in sorted(builtin_dir.glob("*.yaml")):
        template = load_template(yaml_file)
        register_template(template)
