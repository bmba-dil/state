"""Tests for state-teach question binding — Phase 117.

Covers: Question/Option/Answer model validation, ask_structured skeleton,
import lint (no cross-mode violations).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from state_teach.question_binding import Answer, Option, Question, ask_structured


def test_question_valid_construction() -> None:
    """Question accepts valid fields and rejects extra fields."""
    q = Question(
        question="Which language?",
        header="Language",
        options=[Option(label="Python", description="Python 3.12+")],
        multiple=False,
    )
    assert q.question == "Which language?"
    assert q.header == "Language"
    assert len(q.options) == 1
    assert q.options[0].label == "Python"
    assert q.multiple is False


def test_question_rejects_extra_fields() -> None:
    """extra='forbid' prevents unknown fields on Question."""
    with pytest.raises(ValidationError):
        Question(
            question="Q",
            header="H",
            options=[Option(label="A", description="desc")],
            unknown_field="nope",  # type: ignore[call-arg]
        )


def test_question_header_max_length() -> None:
    """header is limited to 30 characters max."""
    with pytest.raises(ValidationError):
        Question(
            question="Q",
            header="This header is way too long for 30 chars",
            options=[Option(label="A", description="desc")],
        )


def test_question_rejects_empty_options() -> None:
    """options list must have at least one entry."""
    with pytest.raises(ValidationError):
        Question(
            question="Q",
            header="H",
            options=[],
        )


def test_question_multiple_defaults_false() -> None:
    """Question.multiple defaults to False when omitted."""
    q = Question(
        question="Q",
        header="H",
        options=[Option(label="A", description="desc")],
    )
    assert q.multiple is False


def test_answer_valid_construction() -> None:
    """Answer accepts selected_labels and rejects extra fields."""
    a = Answer(selected_labels=["Yes", "No"])
    assert a.selected_labels == ["Yes", "No"]

    with pytest.raises(ValidationError):
        Answer(selected_labels=["x"], extra="nope")  # type: ignore[call-arg]


def test_ask_structured_returns_n_answers_for_n_questions() -> None:
    """ask_structured returns one Answer per Question, each with placeholder label."""
    questions = [
        Question(
            question=f"Q{i}?",
            header=f"H{i}",
            options=[Option(label="Yes", description="desc")],
        )
        for i in range(3)
    ]
    answers = ask_structured(questions)
    assert len(answers) == 3
    assert answers[0].selected_labels == ["__placeholder_0__"]
    assert answers[1].selected_labels == ["__placeholder_1__"]
    assert answers[2].selected_labels == ["__placeholder_2__"]


def test_ask_structured_empty_input() -> None:
    """ask_structured with empty list returns empty list."""
    assert ask_structured([]) == []


def test_import_lint_clean() -> None:
    """state_teach.question_binding must not cause cross-mode import violations."""
    from state_core.import_lint import lint

    result = lint()
    assert result.exit_code == 0, (
        f"Found {len(result.violations)} cross-mode import violations:\n"
        + "\n".join(str(v) for v in result.violations)
    )
