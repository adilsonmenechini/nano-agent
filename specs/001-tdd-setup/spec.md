# Feature Specification: TDD Setup

**Feature Branch**: `001-tdd-setup`

**Created**: 2026-06-27

**Status**: Draft

**Input**: User description: "criar TDD"

**Constitution Reference**: This feature implements **Principle I (Test-First)**, **Principle III (Quality Gates)**, and **Principle IV (Static Analysis & Linting)** from the project constitution — establishing the infrastructure and conventions that make quality checks mandatory and enforceable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer runs existing test suite to verify project health (Priority: P1)

As a developer working on the NanoAgent project, I want to run the full test suite with a single command so that I can verify my changes don't break existing functionality.

**Why this priority**: Foundational capability — every other TDD workflow depends on knowing tests pass. Without this, no red-green-refactor cycle can start.

**Independent Test**: Can be verified by running the test command from the project root and observing all existing tests execute with clear pass/fail output.

**Acceptance Scenarios**:

1. **Given** the project is set up, **When** the developer runs the test command, **Then** all tests execute and results are reported with pass/fail counts and duration.
2. **Given** a test failure exists, **When** the developer runs the test command, **Then** the failing test is identified with the assertion that failed and a traceback.
3. **Given** the developer runs the verbose test command, **Then** each test name and its status is printed individually.

---

### User Story 2 - Developer writes a failing test first (Priority: P1)

As a developer following TDD, I want to write a test that fails before implementing the corresponding feature so that I can confirm the test correctly detects the absence of the feature.

**Why this priority**: Core TDD practice — red-green-refactor. The project infrastructure must support writing tests that validate unimplemented behavior.

**Independent Test**: Write a test for a function that does not yet exist, run it, confirm it fails; then implement the function, run again, confirm it passes.

**Acceptance Scenarios**:

1. **Given** no implementation exists for feature X, **When** the developer writes a test for feature X and runs it, **Then** the test fails with a clear error indicating the missing implementation.
2. **Given** a failing test for feature X exists, **When** the developer implements feature X and runs the test, **Then** the test passes.

---

### User Story 3 - Developer follows TDD conventions across all modules (Priority: P2)

As a developer, I want clear conventions for test organization, naming, and structure so that tests are consistent, readable, and maintainable across the entire project.

**Why this priority**: Consistency reduces cognitive overhead and makes tests self-documenting and reviewable.

**Independent Test**: Review any test file against the documented conventions and verify it conforms.

**Acceptance Scenarios**:

1. **Given** the project test conventions are documented, **When** a new test is written, **Then** it follows the naming, structure, and organization guidelines.
2. **Given** an existing test file, **When** reviewed, **Then** it conforms to the project's testing standards.

---

### User Story 4 - Developer measures test coverage (Priority: P2)

As a project maintainer, I want to measure test coverage so that I can identify untested code and track coverage trends over time.

**Why this priority**: Coverage metrics provide objective quality gates and prevent untested code from accumulating.

**Independent Test**: Run the coverage command, observe report output showing percentages per module.

**Acceptance Scenarios**:

1. **Given** the coverage tool is configured, **When** the developer runs the coverage command, **Then** a report shows line coverage percentages per module.
2. **Given** new code is added without tests, **When** coverage is measured, **Then** the report reflects the lower coverage.

---

### User Story 5 - Developer integrates tests into CI pipeline (Priority: P3)

As a project maintainer, I want tests to run automatically on every push or pull request so that regressions are caught before merging.

**Why this priority**: CI automation enforces TDD discipline at the team level and prevents broken code from reaching production.

**Independent Test**: Push a change and observe the CI pipeline executing the test suite and reporting results.

**Acceptance Scenarios**:

1. **Given** a feature branch is pushed, **When** CI runs, **Then** the full test suite executes automatically.
2. **Given** a change introduces a test failure, **When** CI runs, **Then** the pipeline fails and reports which tests broke.

---

### Edge Cases

- **Long-running test suite**: Tests must be organized into unit (fast) and integration (potentially slower) categories so developers can run only unit tests during active development.
- **External dependencies**: Tests depending on external services (LLM APIs, network) must be mocked or use in-memory alternatives and be marked with a test marker for exclusion from default runs.
- **Coverage drop below threshold**: CI pipeline must fail, preventing merge, when coverage drops below the minimum.
- **Flaky tests**: Flaky tests must be identified and quarantined; they should not block CI but must be tracked for resolution.
- **No tests for new feature**: Coverage gates and mandatory code review should catch new modules without corresponding tests.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Project MUST have a test runner configuration that discovers and runs all tests under the `tests/` directory.
- **FR-002**: Test files MUST follow the convention `tests/test_<module>.py` matching source modules under `src/nanoagent/`.
- **FR-003**: Every module in `src/nanoagent/` MUST have a corresponding test file covering its public API.
- **FR-004**: Tests MUST be independently runnable — no test shall depend on the side effects of another test.
- **FR-005**: Tests MUST use fixtures (provided by the test framework) for shared setup and teardown rather than module-level state.
- **FR-006**: External services (APIs, databases, filesystems) MUST be mocked or use in-memory alternatives in unit tests.
- **FR-007**: Coverage measurement MUST be configured with a minimum threshold of 80% line coverage for the `src/nanoagent/` package.
- **FR-008**: The project MUST provide commands for running tests: a standard test run, a test run with coverage reporting, and a mechanism to run only unit tests (excluding externally-dependent tests).
- **FR-009**: CI pipeline MUST run the full test suite on push and pull request events to the main branch.
- **FR-010**: CI pipeline MUST enforce the minimum coverage threshold; a drop below 80% MUST fail the pipeline.
- **FR-011**: Ruff linter MUST be configured and MUST pass without errors on all source code in `src/` and `tests/`.
- **FR-012**: Pyright type checker MUST be configured and MUST pass without type errors on all source code in `src/`.
- **FR-013**: Vulture dead code detector MUST be configured and MUST achieve a minimum score of 65 (no more than 35% unused code reported) on `src/nanoagent/`.
- **FR-014**: The project MUST provide commands for running all quality checks: `lint` (ruff), `typecheck` (pyright), `deadcode` (vulture), and a combined `quality` command that runs all checks including tests.

### Key Entities

- **Test Suite**: The collection of all tests under `tests/`, organized by source module.
- **Test Fixture**: A reusable pytest fixture for setup and teardown of test dependencies.
- **Coverage Report**: Output from the coverage tool showing which lines and branches are exercised by tests.
- **CI Pipeline**: Automated workflow running tests and enforcing quality gates on every push and PR.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running the test suite from the project root executes all tests and completes in under 30 seconds.
- **SC-002**: Line coverage for `src/nanoagent/` is at or above 80%.
- **SC-003**: Every source module in `src/nanoagent/` (excluding `__init__.py` and `cli.py`) has at least one corresponding test file.
- **SC-004**: No test depends on the output or state of another test — tests can be run in random order without failures.
- **SC-005**: CI pipeline completes test run and coverage check within 5 minutes of push.
- **SC-006**: Developers can run the test suite with a single intuitive command without reading documentation.
- **SC-007**: Ruff linter runs without errors across `src/` and `tests/`.
- **SC-008**: Pyright type checking completes without type errors across `src/`.
- **SC-009**: Vulture reports a dead code score of 65 or higher on `src/nanoagent/`.
- **SC-010**: CI pipeline blocks merge if any quality check (ruff, pyright, vulture, coverage below 80%) fails.

## Constitution Alignment

This spec is a direct implementation of **Principle I (Test-First)**, **Principle III (Quality Gates)**, and **Principle IV (Static Analysis & Linting)** from the project constitution. The functional requirements and success criteria below are designed to make these constitutional principles operational and enforceable through automation (CI gates, coverage thresholds, type checking, linting, dead code detection).

## Assumptions

- Tests will use the existing test framework already set up as a project dependency.
- Ruff, Pyright, and Vulture will be configured via `pyproject.toml` (already listed as dev dependencies).
- Python 3.13+ is the target runtime (as defined in `.python-version`).
- Existing test files (`test_agent.py`, `test_memory.py`, `test_handlers.py`) serve as the starting point and will be brought under the new conventions.
- Mocking will use `unittest.mock` from the Python standard library.
- Coverage will use the `pytest-cov` plugin wrapping `coverage.py`.
- CI will use GitHub Actions (standard for the ecosystem).
- Tests requiring live API calls must be marked with `@pytest.mark.external` and excluded from default runs.
- Test data will be minimal and inline in v1, with no large fixture files.
