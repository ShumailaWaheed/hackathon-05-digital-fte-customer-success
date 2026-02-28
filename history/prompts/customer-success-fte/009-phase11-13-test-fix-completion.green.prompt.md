---
id: 009
title: Phase 11-13 Test Fix and Completion
stage: green
date: 2026-02-28
surface: agent
model: claude-opus-4-6
feature: customer-success-fte
branch: main
user: Abdul Waheed
command: /sp.implement
labels: ["testing", "integration", "bugfix", "completion"]
links:
  spec: specs/001-customer-success-fte/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - production/agent/guardrails.py
  - production/tests/transition/test_tool_order.py
  - production/tests/integration/test_webform_channel.py
  - production/tests/integration/test_whatsapp_channel.py
  - .dockerignore
  - specs/001-customer-success-fte/tasks.md
tests:
  - production/tests/transition/ (40 passed)
  - production/tests/integration/ (20 passed)
---

## Prompt

/sp.implement

## Response snapshot

Executed implementation verification for Phases 11-13 (T083-T110). Found all files already implemented from prior sessions. Ran test suites and discovered 8 test failures across transition and integration tests. Fixed all failures:

1. **Guardrails G9 missing from check_all** — Added G9 (sentiment-before-close) to the guardrail check_all function
2. **test_tool_order.py import failures** — Added module mocking for `agents` and `confluent_kafka` packages not installed in test environment
3. **test_webform_channel.py import failures** — Added module mocking and fixed patch targets for missing packages
4. **test_whatsapp_channel.py signature error** — Fixed missing `self` parameter and updated patch targets for lazy imports
5. **Starlette/httpx version mismatch** — Upgraded fastapi and starlette to resolve TestClient incompatibility

Final result: 60/60 tests passing (40 transition + 20 integration). Created .dockerignore. Marked all T083-T110 tasks as complete.

## Outcome

- ✅ Impact: All 110 tasks now marked complete. Full test suite passing.
- 🧪 Tests: 60/60 passing (transition + integration suites)
- 📁 Files: 6 files modified/created
- 🔁 Next prompts: Commit changes, run docker-compose E2E validation
- 🧠 Reflection: Most issues were environment-related (missing packages, version mismatches) rather than logic errors. The G9 guardrail omission was the only real logic bug.

## Evaluation notes (flywheel)

- Failure modes observed: Missing module mocks for external dependencies, stale package versions, lazy imports breaking patch targets
- Graders run and results (PASS/FAIL): All transition tests PASS, all integration tests PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Add conftest.py with shared module mocking to avoid repeating mock setup
