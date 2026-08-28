# Service Mesh Documentation PR Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the verified service-mesh mTLS and retry guidance commit as a focused GitHub pull request.

**Architecture:** Recover the existing isolated commit or bundle, rebase it onto the current remote `main`, verify the exact 12-file PR scope, then push and create the PR. Do not commit unrelated changes from the dirty primary workspace.

**Tech Stack:** Git, Git bundle, GitHub CLI, Node.js test runner.

**Spec:** `docs/superpowers/specs/2026-08-20-service-mesh-mtls-retry-guidance-design.md`

## Global Constraints

- PR branch: `docs/service-mesh-mtls-retry-guidance`
- PR base: current `origin/main`
- Existing isolated commit: `9688247501ce0003267e2e7eb4ae0573451b21dd`
- Include only 10 ko/en documentation files, `package.json`, and `scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs`
- Exclude Argo Rollouts, VitePress migration, diagrams, translation locales, and other dirty-worktree changes
- Do not force-push an existing remote branch without first confirming its ownership and contents

---

### Task 1: Restore GitHub Connectivity and Authentication

**Files:**
- Read: `/home/atomoh/.ssh/config`
- Read: `/home/atomoh/.config/gh/hosts.yml`

**Interfaces:**
- Consumes: local SSH key and GitHub CLI credential
- Produces: working SSH push access and authenticated `gh api`

- [ ] **Step 1: Verify outbound connectivity**

```bash
getent hosts github.com
curl -I --connect-timeout 10 https://api.github.com
```

Expected: both commands resolve/connect without `Operation not permitted` or DNS errors.

- [ ] **Step 2: Verify GitHub CLI authentication**

```bash
gh auth status
gh api user --jq .login
```

Expected: authenticated account is `Atom-oh`.

- [ ] **Step 3: Refresh authentication only if required**

```bash
gh auth refresh -h github.com -s repo
```

Expected: `gh api user --jq .login` prints `Atom-oh`.

- [ ] **Step 4: Verify SSH with the user config**

```bash
ssh -F /home/atomoh/.ssh/config -o BatchMode=yes -T git@github.com
```

Expected: GitHub reports successful authentication for `Atom-oh`.

### Task 2: Recover and Rebase the Isolated Commit

**Files:**
- Read: `/tmp/kubernetes-docs-service-mesh-pr.Xnjhqo/repo`
- Read: `/tmp/kubernetes-docs-service-mesh-pr.Xnjhqo/service-mesh-mtls-retry-guidance-latest.bundle`
- Read: `/tmp/kubernetes-docs-service-mesh-pr.Xnjhqo/pr-body.md`

**Interfaces:**
- Consumes: commit `9688247` or the verified Git bundle
- Produces: local branch `docs/service-mesh-mtls-retry-guidance` based on current `origin/main`

- [ ] **Step 1: Prefer the existing isolated clone**

```bash
test -d /tmp/kubernetes-docs-service-mesh-pr.Xnjhqo/repo/.git
git -C /tmp/kubernetes-docs-service-mesh-pr.Xnjhqo/repo show \
  --no-patch --oneline 9688247501ce0003267e2e7eb4ae0573451b21dd
```

Expected: the commit subject is `docs: clarify service mesh mTLS and retry guidance`.

- [ ] **Step 2: If the clone is missing, restore from the bundle**

```bash
git clone git@github.com:Atom-oh/kubernetes-docs.git \
  /tmp/kubernetes-docs-service-mesh-pr-restored
git -C /tmp/kubernetes-docs-service-mesh-pr-restored fetch \
  /tmp/kubernetes-docs-service-mesh-pr.Xnjhqo/service-mesh-mtls-retry-guidance-latest.bundle \
  HEAD:refs/heads/docs/service-mesh-mtls-retry-guidance
```

Expected: the restored branch points to commit `9688247`.

- [ ] **Step 3: Rebase onto the latest remote main**

```bash
git fetch origin main
git switch docs/service-mesh-mtls-retry-guidance
git rebase origin/main
```

Expected: one service-mesh documentation commit exists above the latest `origin/main`.

- [ ] **Step 4: Confirm the exact PR scope**

```bash
git diff --name-status origin/main...HEAD
git diff --check origin/main...HEAD
```

Expected: exactly these 12 files are changed:

```text
en/quizzes/service-mesh/istio/comparison.md
en/quizzes/service-mesh/istio/traffic-management.md
en/service-mesh/cilium-service-mesh/03-security.md
en/service-mesh/istio/comparison/03-sidecar-vs-ambient.md
en/service-mesh/istio/traffic-management/05-retry-timeout.md
ko/quizzes/service-mesh/istio/comparison.md
ko/quizzes/service-mesh/istio/traffic-management.md
ko/service-mesh/cilium-service-mesh/03-security.md
ko/service-mesh/istio/comparison/03-sidecar-vs-ambient.md
ko/service-mesh/istio/traffic-management/05-retry-timeout.md
package.json
scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs
```

### Task 3: Verify the Rebased Branch

**Files:**
- Test: `scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs`

**Interfaces:**
- Consumes: rebased branch from Task 2
- Produces: test and diff evidence suitable for the PR body

- [ ] **Step 1: Install or reuse dependencies**

```bash
npm install
```

Expected: dependencies install without changing `package-lock.json`.

- [ ] **Step 2: Run the focused regression test**

```bash
npm run docs:test
```

Expected: 1 test file passes with 0 failures.

- [ ] **Step 3: Verify commit structure**

```bash
git log --oneline origin/main..HEAD
git status --short
```

Expected: one commit above `origin/main` and a clean working tree.

### Task 4: Push and Create the Pull Request

**Files:**
- Read: `/tmp/kubernetes-docs-service-mesh-pr.Xnjhqo/pr-body.md`

**Interfaces:**
- Consumes: verified branch and authenticated GitHub access
- Produces: remote branch and open pull request

- [ ] **Step 1: Check whether the remote branch already exists**

```bash
git ls-remote --heads origin docs/service-mesh-mtls-retry-guidance
```

Expected: no output for a new branch. If a ref exists, inspect it before pushing.

- [ ] **Step 2: Push the branch**

```bash
git push -u origin docs/service-mesh-mtls-retry-guidance
```

Expected: GitHub creates the remote branch without a force push.

- [ ] **Step 3: Create the PR**

```bash
gh pr create \
  --repo Atom-oh/kubernetes-docs \
  --base main \
  --head docs/service-mesh-mtls-retry-guidance \
  --title "docs: clarify service mesh mTLS and retry guidance" \
  --body-file /tmp/kubernetes-docs-service-mesh-pr.Xnjhqo/pr-body.md
```

Expected: command prints the new PR URL.

- [ ] **Step 4: Verify PR metadata and checks**

```bash
gh pr view \
  --repo Atom-oh/kubernetes-docs \
  --json number,url,baseRefName,headRefName,mergeStateStatus,statusCheckRollup
```

Expected: base is `main`, head is `docs/service-mesh-mtls-retry-guidance`, and required checks are visible.

