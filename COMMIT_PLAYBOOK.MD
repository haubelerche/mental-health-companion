# COMMIT_PLAYBOOK.md — Main-Safe Commit & PR Procedure

> Mandatory Git procedure for Claude / Cursor / Codex after a completed implementation unit.  
> Goal: create meaningful commits on one working branch, open/update one PR targeting `main`, and reduce GitHub Actions backend failures before review.

---

## 1. Core Objective

The agent must:

1. commit only meaningful, reviewable work units,
2. keep all commits on one working branch created from the latest `main`,
3. push only to that working branch,
4. create or update exactly one PR with `base=main` and `head=current branch`,
5. run backend/frontend validation before push when relevant,
6. never push directly to `main`.

---

## 2. Main-Safe Branch Policy

Use one daily branch unless the user specifies another branch:

```text
work/YYYY-MM-DD-serene
```

Required branch invariant:

```text
origin/main
   └── work/YYYY-MM-DD-serene
          └── PR base: main
```

Rules:

- If currently on `main`, create/reuse a working branch before committing.
- Always sync with latest `origin/main` before creating a new branch.
- Before PR creation, ensure the branch is not stale against `main`.
- PR base must be `main`.
- PR head must be the current working branch.
- Reuse the existing PR for the same branch; do not create duplicate PRs.
- Do not merge PRs unless explicitly instructed.
- Do not run `git stash` unless explicitly requested.

---

## 3. XP-Compliant Commit Policy

Commit meaningful, reviewable units only.

Allowed:

- one feature slice,
- one bug fix,
- one API/schema change,
- one test group,
- one frontend/backend integration boundary,
- one refactor with clear purpose,
- up to 5 meaningful commits in one PR when the work naturally contains 5 reviewable units.

Forbidden:

- direct push to `main`,
- artificial micro-commits,
- whitespace/comment-only farming,
- vague `update/fix/wip/done` commits,
- duplicate PRs,
- timing/rate-limit tricks,
- fake review or merge patterns,
- bypassing validation to gain XP faster.

Standard:

```text
More commits are acceptable only when each commit improves reviewability, traceability, or rollback safety.
```

---

## 4. Pre-Commit Review

Run:

```bash
git branch --show-current
git status --short
git diff --stat
git diff
```

If staged files exist:

```bash
git diff --cached --stat
git diff --cached
```

Report:

```text
## Git Checkpoint Review
- Current branch:
- Changed files:
- Diff summary:
- Commit unit classification:
- Meaningful: yes/no
- Proposed commit message:
- Validation run:
- Validation not run:
```

Proceed only if the diff is meaningful, coherent, and safe.

---

## 5. Backend / Frontend CI Guard

Before push, run the checks relevant to changed files.

### Backend changed

Run the project’s real backend commands. If unknown, inspect repo scripts first:

```bash
ls
find . -maxdepth 3 -iname "package.json" -o -iname "pyproject.toml" -o -iname "requirements.txt"
```

Common backend checks:

```bash
# Python backend
python -m pytest
python -m compileall .

# Node backend
npm test
npm run build
npm run typecheck
```

### Frontend changed

```bash
npm run build
npm run typecheck
npm test -- --run
```

### Safety rule

- If validation fails because of the new changes, fix before commit/push.
- If failure is pre-existing, document it clearly in the PR body.
- Do not create a success-style report when checks fail.
- Do not push code that obviously breaks backend startup, routes, imports, migrations, or type contracts.

---

## 6. Commit Message Format

Use Conventional Commit:

```text
type(scope): concise summary
```

Allowed types:

```text
feat | fix | refactor | test | docs | chore | perf | build | ci
```

Recommended scopes:

```text
safety | persona | router | conversation | analyst | memory | rewards | unlock | tts | voice | frontend | backend | schema | db | neo4j | tests | observability
```

Examples:

```text
fix(safety): finalize high-risk turns before normal conversation
refactor(router): separate persona style selection from agent routing
fix(tts): deduplicate repeated safety voice payloads
test(rewards): add heart ledger idempotency checks
```

---

## 7. Standard Command Flow

### 7.1 Create or reuse branch from latest main

Bash:

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
git checkout -B work/$(date +%F)-serene
```

PowerShell:

```powershell
git fetch origin
git checkout main
git pull --ff-only origin main
git checkout -B "work/$(Get-Date -Format 'yyyy-MM-dd')-serene"
```

If already on an existing working branch:

```bash
git fetch origin
git rebase origin/main
```

If rebase conflicts occur, stop and report the conflicts. Do not force-resolve blindly.

---

### 7.2 Commit one or more meaningful units

Single coherent unit:

```bash
git add -A
git commit -m "type(scope): concise summary"
```

Multiple unrelated meaningful units:

```bash
git add path/to/unit-a
git commit -m "fix(safety): finalize high-risk turns"

git add path/to/unit-b
git commit -m "fix(tts): deduplicate repeated voice payloads"
```

---

### 7.3 Push working branch only

```bash
git push -u origin HEAD
```

Never run:

```bash
git push origin main
```

---

### 7.4 Create or update PR to main

Check existing PR:

```bash
gh pr view --head "$(git branch --show-current)"
```

Create PR only if none exists:

```bash
gh pr create \
  --base main \
  --head "$(git branch --show-current)" \
  --title "Daily Serene Implementation — YYYY-MM-DD" \
  --body "## Summary
Daily implementation checkpoints.

## Branch Contract
- Base: main
- Head: current working branch
- Branch was synced/rebased from origin/main before PR.

## Validation
- [ ] Backend tests/build passed
- [ ] Frontend build/typecheck passed
- [ ] Safety flow checked
- [ ] TTS flow checked
- [ ] Known pre-existing failures documented

## Review Notes
Review commit-by-commit. Each commit must represent one coherent implementation unit."
```

If PR already exists, push only. The PR updates automatically.

---

## 8. Five-Commit PR Mode

When the user requests `5 commits / 1 PR`:

- target up to 5 meaningful commits,
- keep all commits on the same branch,
- keep exactly one PR targeting `main`,
- do not create fake commits just to reach 5,
- if fewer than 5 meaningful units exist, create fewer and explain why.

Before committing, propose:

```text
## Proposed Commit Split
1. type(scope): ...
   - files:
   - reason:
2. type(scope): ...
   - files:
   - reason:
...
```

---

## 9. Agent Prompt

```md
Use `COMMIT_PLAYBOOK.md` as the mandatory Git procedure.

Commit completed work into meaningful reviewable units on the current working branch, then create/update one PR targeting `main`.

Hard rules:
- Never push directly to `main`.
- Ensure the branch is based on latest `origin/main` before PR.
- Rebase the working branch on `origin/main` before push if needed.
- Create PR only if no PR exists for this branch.
- Do not merge the PR.
- Run relevant backend/frontend validation before push.
- If validation fails, fix first or document a pre-existing blocker.
- Do not create artificial commits for XP.
- Do not run `git stash` unless explicitly instructed.

Before committing, report:
1. Current branch
2. Base branch relationship to `origin/main`
3. Changed files
4. Diff summary
5. Proposed commit split
6. Proposed commit messages
7. Validation commands run
8. Validation result

Proceed only if the diff is meaningful, coherent, main-safe, and CI-safe.
```

---

## 10. Failure Rules

| Case | Action |
|---|---|
| On `main` | Create/reuse working branch from latest `origin/main` |
| Branch stale | Rebase on `origin/main` before push |
| Rebase conflict | Stop and report conflicts |
| No meaningful diff | Skip commit |
| Unrelated changes | Split into separate commits |
| Backend/frontend checks fail | Fix first or document pre-existing failure |
| PR exists | Push only, do not create duplicate PR |
| Dirty tree blocks branch work | Do not stash silently; ask or use worktree |
| Suspected XP abuse path | Stop and document a security report |
