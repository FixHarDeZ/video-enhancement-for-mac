# Release Skill

When the user invokes `/release`, **do NOT use the Skill tool** — read this file and execute each step directly with Bash, Edit, and other tools.

---

## Step 1 — Ask release type

Ask the user: **"What type of release? (patch / minor / major)"**

Read the current version from `src/app.py`:
```python
VERSION = "x.y.z"
```

Calculate the new version:
- **patch**: increment Z  (1.1.0 → 1.1.1)
- **minor**: increment Y, reset Z  (1.1.0 → 1.2.0)
- **major**: increment X, reset Y and Z  (1.1.0 → 2.0.0)

Confirm: **"Release v{NEW_VERSION} ({type}) — proceed?"**

---

## Step 2 — Check working tree

```bash
git status
git diff --stat
```

Unstaged changes to `src/app.py`, `README.md`, or other project files are **expected** — they will be included in the release commit (Step 5). Only warn and pause if you see changes that look completely unrelated (e.g. personal config files the user didn't mention).

---

## Step 3 — Create release branch

```bash
git checkout -b release/v{NEW_VERSION}
```

---

## Step 4 — Bump version in source

Edit `src/app.py` — change the `VERSION` line:
```python
VERSION = "{NEW_VERSION}"
```

---

## Step 5 — Commit everything into one release commit

Stage all relevant files (skip `.pyc`, `__pycache__`, `.DS_Store`):

```bash
git add src/app.py README.md
# also stage any other modified project files the user mentioned
git status  # confirm what's staged
```

Commit with a message that lists the actual changes (read the diff to write a real summary, not a placeholder):

```bash
git commit -m "$(cat <<'EOF'
{type}: {one-line summary of what changed in this release}

- {change 1}
- {change 2}
...
- Bump version to v{NEW_VERSION}

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Step 6 — Push release branch

```bash
git push -u origin release/v{NEW_VERSION}
```

---

## Step 7 — Open Pull Request

Build the PR body from the actual commit diff, then:

```bash
gh pr create \
  --base main \
  --head release/v{NEW_VERSION} \
  --title "Release v{NEW_VERSION}" \
  --body "$(cat <<'EOF'
## Release v{NEW_VERSION}

### Changes
- {list the real changes from the diff}

### Checklist
- [x] Version updated in `src/app.py`
- [ ] Tested on Apple Silicon Mac
- [ ] Ready to merge and tag

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Show the PR URL to the user.

---

## Step 8 — Merge Pull Request

Ask: **"Merge PR and tag v{NEW_VERSION} now?"**

If yes:

```bash
gh pr merge release/v{NEW_VERSION} \
  --squash \
  --subject "Release v{NEW_VERSION}" \
  --delete-branch
```

---

## Step 9 — Tag on main

```bash
git checkout main
git pull origin main
git tag -a "v{NEW_VERSION}" -m "Release v{NEW_VERSION}"
git push origin "v{NEW_VERSION}"
```

---

## Step 10 — Summary

Report:

```
Version : v{NEW_VERSION}
PR      : {URL}
Commit  : {git log -1 --format="%h %s"}
Tag     : v{NEW_VERSION} pushed to origin
```

---

## Notes

- Never use the `Skill` tool to invoke this — read and execute directly.
- Never force-push to main.
- Tag always goes on main after merge, never on the release branch.
- Version lives only in `src/app.py:VERSION`.
- If `gh` is missing: `brew install gh && gh auth login`.
