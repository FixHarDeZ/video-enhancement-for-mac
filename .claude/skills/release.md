# Release Skill

When the user invokes `/release`, follow these steps to create a versioned release of Video Enhancer.

---

## Step 1 — Determine the new version

Ask the user: **"What type of release? (patch / minor / major)"**

Then read the current version from `src/app.py`:
```python
VERSION = "x.y.z"
```

Calculate the new version:
- **patch**: increment Z (1.0.0 → 1.0.1)
- **minor**: increment Y, reset Z (1.0.1 → 1.1.0)
- **major**: increment X, reset Y and Z (1.1.0 → 2.0.0)

Confirm with the user: **"Release v{NEW_VERSION} as a {type} release — proceed?"**

---

## Step 2 — Check working tree

Run `git status`. If there are uncommitted changes unrelated to the release, warn the user and ask them to stash or commit those first before continuing.

---

## Step 3 — Create release branch

```bash
git checkout -b release/v{NEW_VERSION}
```

---

## Step 4 — Bump version in source

Edit `src/app.py` — change the `VERSION` line:
```python
VERSION = "NEW_VERSION"
```

---

## Step 5 — Commit the version bump

```bash
git add src/app.py
git commit -m "$(cat <<'EOF'
chore: bump version to v{NEW_VERSION}

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

If the user has other changes they want included in this release, add and commit those too before moving on.

---

## Step 6 — Push release branch

```bash
git push -u origin release/v{NEW_VERSION}
```

---

## Step 7 — Open Pull Request

```bash
gh pr create \
  --base main \
  --head release/v{NEW_VERSION} \
  --title "Release v{NEW_VERSION}" \
  --body "$(cat <<'EOF'
## Release v{NEW_VERSION}

### Changes
- Version bump to v{NEW_VERSION}

### Checklist
- [ ] Version updated in `src/app.py`
- [ ] Tested on Apple Silicon Mac
- [ ] Ready to merge and tag

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Show the user the PR URL returned by `gh pr create`.

---

## Step 8 — Merge Pull Request

Ask the user: **"Merge PR and tag v{NEW_VERSION} now?"**

If yes, merge using squash merge to keep main history clean:

```bash
gh pr merge release/v{NEW_VERSION} \
  --squash \
  --subject "Release v{NEW_VERSION}" \
  --delete-branch
```

---

## Step 9 — Tag on main

Switch to main and pull the merged commit, then tag:

```bash
git checkout main
git pull origin main
git tag -a "v{NEW_VERSION}" -m "Release v{NEW_VERSION}"
git push origin "v{NEW_VERSION}"
```

---

## Step 10 — Summary

Report back to the user:

- New version: `v{NEW_VERSION}`
- PR: (URL from step 7)
- Merge commit: `git log -1 --format="%h %s"`
- Tag: `v{NEW_VERSION}` pushed to origin

---

## Notes

- Never force-push to main.
- Never skip the confirmation in step 1.
- Tag is always created on main after the merge — never on the release branch.
- The version lives only in `src/app.py:VERSION`. Do not change `pyproject.toml` separately unless the user asks.
- If `gh` CLI is not installed or not authenticated, tell the user to run `brew install gh && gh auth login` first.
