# Development Workflow

## 1. Repository workflow

Use a shared Git repository with a protected default branch where available.

Recommended branch naming:
- `main` — stable, reviewed work.
- `develop` — integration branch, if the team chooses to use one.
- `feature/HS-012-missing-data-gate`
- `fix/HS-014-assessment-api`
- `docs/phase-4-workflow`

For a small team, `main` plus short-lived feature branches is sufficient; a separate `develop` branch is optional. Avoid long-lived personal branches.

## 2. Task lifecycle

`BACKLOG → READY → IN_PROGRESS → REVIEW → TESTING → DONE`

A task may move to `READY` only when its scope, dependencies, and acceptance criteria are clear.

A task may move to `DONE` only when:
- Code is committed on its feature branch.
- Tests pass.
- A teammate reviews the change.
- Documentation/API contracts are updated.
- No known blocker is hidden.

## 3. Pull request checklist

- [ ] Linked task ID and clear summary.
- [ ] Scope is limited to the task.
- [ ] Acceptance criteria are addressed.
- [ ] Tests added or updated.
- [ ] Local build/lint/test results recorded.
- [ ] No secrets, credentials, database dumps, or private datasets committed.
- [ ] Data provenance and licence obligations respected.
- [ ] Screenshots or API examples added for user-facing changes.
- [ ] Documentation updated.
- [ ] Reviewer approval received.

## 4. Commit message convention

Use concise imperative messages with task IDs:

```text
feat(api): add area assessment endpoint [HS-014]
fix(scoring): reject zero eligible weight [HS-012]
docs(data): clarify source verification status
test(scoring): cover inverse indicator normalization
```

Do not bundle unrelated changes into one commit.

## 5. Reviews and coordination

- Every task has one owner and one reviewer.
- Agree API request/response changes before frontend and backend work diverge.
- Review database migrations before merging.
- Review scoring configuration changes with the scoring owner.
- Keep `DOCUMENTATION_STATUS.md` and the task tracker updated.
- Record unresolved decisions in a decision log rather than making silent assumptions.

## 6. Daily team sync

Keep the sync short. Each member reports:
- What task moved forward?
- What is the next concrete deliverable?
- What is blocked?
- Does the work change an API, data definition, scoring rule, or demo assumption?

A blocker that affects a dependency should be raised before parallel work continues.

## 7. Repository hygiene

Recommended `.gitignore` exclusions include:
- `.env` and local secret files.
- Python virtual environments and caches.
- Node dependencies and build output.
- Local database files and temporary exports.
- IDE settings that are personal rather than shared.
- Raw datasets that cannot legally be redistributed.

Commit `.env.example`, not `.env`. Commit only datasets that the licence permits the team to share. Use a documented fixture-generation or authorised download process where data cannot be committed.
