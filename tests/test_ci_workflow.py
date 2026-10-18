"""AC-59: the core CI workflow runs the core gates and Postgres tests."""

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "core.yml"
FULL_SHA = re.compile(r"[^@\s]+@[0-9a-f]{40}")
PINNED_POSTGRES = re.compile(r"postgres:\d+\.\d+(?:-alpine)?@sha256:[0-9a-f]{64}")


def workflow() -> dict[Any, Any]:
    return yaml.safe_load(WORKFLOW.read_text())


def core_commands() -> dict[str, str]:
    """The core module's commands, from the frontmatter of docs/mobua-swe.md."""
    frontmatter = (ROOT / "docs" / "mobua-swe.md").read_text().split("---")[1]
    modules = yaml.safe_load(frontmatter)["modules"]
    return next(module for module in modules if module["name"] == "core")["commands"]


def commands_of(job: dict[str, Any]) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def test_it_runs_on_every_pull_request_and_every_push_to_main() -> None:
    # YAML 1.1 reads the bare key `on` as a boolean.
    triggers = workflow()[True]

    assert triggers["pull_request"] is None
    assert triggers["push"] == {"branches": ["main"]}


def test_each_core_gate_runs_in_its_own_job() -> None:
    commands = core_commands()
    jobs = workflow()["jobs"]

    assert commands_of(jobs["typecheck"])[-1] == commands["typecheck"]
    assert commands_of(jobs["lint"])[1:] == commands["lint"].split(" && ")
    assert commands_of(jobs["test-sqlite"])[-1] == commands["test_all"]
    assert "NEWS_TEST_DATABASE_URL" not in jobs["test-sqlite"].get("env", {})


def test_the_postgres_job_runs_the_repository_and_schema_tests_on_a_pinned_service() -> None:
    job = workflow()["jobs"]["test-postgres"]

    assert PINNED_POSTGRES.fullmatch(job["services"]["postgres"]["image"])
    assert job["env"]["NEWS_TEST_DATABASE_URL"].startswith("postgresql+psycopg://")
    assert commands_of(job)[-1] == "uv run pytest tests/service tests/test_test_database.py"


def test_core_ci_runs_only_the_required_application_gates() -> None:
    assert set(workflow()["jobs"]) == {"typecheck", "lint", "test-sqlite", "test-postgres"}


def test_every_action_is_pinned_to_a_full_commit_sha() -> None:
    uses = [
        step["uses"]
        for job in workflow()["jobs"].values()
        for step in job["steps"]
        if "uses" in step
    ]

    assert uses
    assert [use for use in uses if not FULL_SHA.fullmatch(use)] == []


def test_no_step_or_job_is_allowed_to_fail() -> None:
    jobs = workflow()["jobs"].values()
    steps = [step for job in jobs for step in job["steps"]]

    assert [item for item in [*jobs, *steps] if "continue-on-error" in item] == []
