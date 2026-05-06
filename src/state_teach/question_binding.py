"""Typed question binding for opencode's question tool — MCP-T-04.

Defines Pydantic models mirroring the opencode question/answer schema
and a skeleton ``ask_structured()`` function. The real MCP client call
will be wired in a later phase (Phase 123 integration test).

Module is physically siloed in ``state_teach`` — must not import from
``state_build``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Option(BaseModel):
    """A single choice in a structured question.

    Mirrors opencode's QuestionOption: label is the display text
    (1-5 words), description explains the choice.
    """

    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., description="Display text for the option (1-5 words, concise)")
    description: str = Field(..., description="Explanation of what choosing this option means")


class Question(BaseModel):
    """A structured question with a fixed set of options.

    Mirrors opencode's QuestionPrompt. The header is a very short label
    (max 30 chars) shown in the UI. Options define the valid answers.
    """

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., description="The complete question text shown to the user")
    header: str = Field(
        ...,
        max_length=30,
        description="Very short label for the question (max 30 characters)",
    )
    options: list[Option] = Field(
        ..., min_length=1, description="Available answer choices (at least one required)"
    )
    multiple: bool = Field(
        default=False, description="Whether the user can select multiple options"
    )


class Answer(BaseModel):
    """The user's response to a structured question.

    Contains the list of selected option labels. Matches opencode's
    question tool answer shape.
    """

    model_config = ConfigDict(extra="forbid")

    selected_labels: list[str] = Field(
        ..., description="Labels of the options the user selected"
    )


def ask_structured(questions: list[Question]) -> list[Answer]:
    """Ask structured questions and return typed answers.

    This is a SKELETON binding for MCP-T-04. The full implementation
    (Phase 123) will call opencode's MCP question tool via
    ``client.question.ask(...)`` to present questions to the user and
    collect their answers.

    For now, returns one placeholder ``Answer`` per input ``Question``
    so that downstream code can integrate against the type signature
    before the real MCP wire-up.

    Args:
        questions: The structured questions to ask the user.

    Returns:
        One ``Answer`` per question, each containing a single placeholder
        label matching the question index.
    """
    return [
        Answer(selected_labels=[f"__placeholder_{i}__"])
        for i in range(len(questions))
    ]
