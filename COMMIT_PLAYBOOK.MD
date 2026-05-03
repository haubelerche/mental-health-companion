# COMMIT_PLAYBOOK.md — Main-Safe Commit & PR Procedure

> Mandatory Git procedure for Claude / Cursor / Codex after a completed implementation unit.  
> Goal: create **high-signal, competition-grade** commits on working branches, open PR(s) targeting `main` (default: one PR per branch; optional: **2–5 commits per PR** in multi-PR batching — more PRs, smaller reviews), and reduce GitHub Actions backend failures before review.

---

## 1. Core Objective

The agent must:

1. commit only meaningful, reviewable work units,
2. keep all commits on one working branch created from the latest `main`,
3. push only to that working branch,
4. create or update PR(s) with `base=main`: normally **one PR** per working branch; in **multi-PR batching** (§8), use **one PR per batch branch** with **2–5 commits** per PR unless the user specifies another cap,
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
- Reuse the existing PR for the same branch; do not create duplicate PRs for that branch. (In **multi-PR batching** (§8), each batch branch has at most one open PR.)
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
- **2–5** meaningful commits in **one** PR when using the multi-PR batching workflow (§8): more PRs, smaller reviews; otherwise one reviewable unit per commit and one PR per branch unless the user asks to split further.
- **many small real commits** for separate files/features is not “micro-farming”; splitting unrelated files is encouraged in §3.1.

Forbidden:

- direct push to `main`,
- artificial micro-commits (note: **many small real commits** for separate files/features is not “micro-farming”; splitting unrelated files is encouraged in §3.1),
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

### 3.1 Competition-grade granularity (Vingroup / high-stakes review)

Use this mode when the work is graded on **Git hygiene, traceability, and review fairness** (e.g. internal or external competition). The objective is **not** to minimize commit count — it is to **maximize defensible units of work** so each commit maps to a clear artifact.

**Skew: one primary file ≈ one commit** when changes are independent:

- Stage with **explicit paths**: `git add path/to/OneFile.py` — not `git add -A` for mixed worktrees.
- If two files are **the same story** (e.g. component + its CSS module only for that component), one commit is fine; if they are unrelated, **split**.

**Forbidden for this mode:**

- **Mega-commits**: one commit that bundles unrelated areas (e.g. migrations + unrelated UI + random test fixes) only to “finish faster”.
- **Blob commits** that hide thousands of lines across many files behind a single vague message.

**Mandatory exceptions** (one commit may include multiple files when inseparable):

- **Migration + matching persistence layer**: the Alembic revision and the ORM/schema (or equivalent) that must stay in lockstep.
- **Import graph**: a new package file plus the smallest `__init__.py` change required for the package to load.
- **Feature + its contract tests**: the code and tests that only exist to lock that behavior; if the diff is huge, prefer **tests in the immediately following commit** with a message that references the prior commit scope.

**One huge file** (hundreds of lines in a single file):

- Use **`git add -p`** to split into **hunk-sized** commits with distinct messages (e.g. types/constants, then behavior), each still green if your branch policy requires it between commits.

**Relationship to §8 (2–5 commits per PR):**

- File-level commits **stack** into PR batches; each pushed branch should contain **at least 2** and **at most 5** commits before opening that PR (unless the slice is genuinely one commit and the user waives the minimum).

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

**Preferred (competition / §3.1):** one path (or inseparable bundle) per commit — **no** `git add -A` on a dirty tree with mixed concerns.

Single coherent unit (one file or one explicit list):

```bash
git add path/to/one_file.py
git commit -m "type(scope): concise summary"
```

Multiple unrelated meaningful units:

```bash
git add path/to/unit-a
git commit -m "fix(safety): finalize high-risk turns"

git add path/to/unit-b
git commit -m "fix(tts): deduplicate repeated voice payloads"
```

Single file, multiple independent hunks (optional):

```bash
git add -p path/to/large_file.py
git commit -m "refactor(scope): extract types only"
git add -p path/to/large_file.py
git commit -m "feat(scope): add behavior using new types"
```

Only when the **entire** staged set is one story (rare after bulk codegen):

```bash
git add path/a path/b path/c
git commit -m "feat(scope): one inseparable bundle (see §3.1 exceptions)"
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

## 8. Multi-PR batch mode (2–5 commits per PR)

When the user wants **many PRs** to `main`, each PR should contain **at least 2** and **at most 5** commits (tunable, but stay in this band for competition scoring unless waived).

- each **batch branch** holds only that slice of commits (typically **stacked**: branch `pr-02` from `pr-01` so CI sees prior slices; open each PR with **base `main`** and note **merge order** in the PR body),
- **first batch branch** is always created from **`origin/main`** at batch start,
- do not create fake commits just to reach 2,
- do not squash away batch boundaries unless the user asks,
- merge **PR batch 01 before PR batch 02** when stacked, or rebase later batches onto updated `main` after each merge.

Before committing, propose:

```text
## Proposed Commit Split (grouped by PR batch, 2–5 commits each)

### PR batch 01 (branch: …, from origin/main)
1. type(scope): …
   - files:
   - reason:
…

### PR batch 02 (branch: …, from batch-01 tip)
…
```

---

## 9. Agent Prompt

```md
Use `COMMIT_PLAYBOOK.md` as the mandatory Git procedure.

Commit completed work into **meaningful, high-signal units** on the current working branch (see **§3.1** for competition-grade **one-file-skewed** commits and anti–mega-commit rules), then create/update PR(s) targeting `main`.

Hard rules:
- Never push directly to `main`.
- Ensure the branch is based on latest `origin/main` before PR.
- Rebase the working branch on `origin/main` before push if needed.
- Create PR only if no PR exists **for this branch** (in multi-PR mode, each batch branch gets its own first PR).
- Do not merge the PR.
- If the user wants multi-PR batching, follow **§8**: **2–5 commits per PR**, branches from **`origin/main`** for batch 01 and stacked for later batches until merged to `main`.
- Run relevant backend/frontend validation before push.
- If validation fails, fix first or document a pre-existing blocker.
- Do not create artificial commits for XP.
- Prefer **`git add <path>`** (or **`git add -p`**) over **`git add -A`** when the worktree mixes unrelated files (§7.2, §3.1).
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
