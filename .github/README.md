# Pull request CI

[The workflow](workflows/ci.yml) provides the stable `Repository checks` job for
pull requests targeting any branch, including stacked PRs and documentation-only
changes. It runs on opening, updates, reopening, edits (including retargeting), and
ready-for-review events. It checks GitHub's proposed merge result, not only the
source branch. Merge conflicts or GitHub's fork-workflow approval requirements can
prevent a run; a missing check is not a pass. A newer run cancels the older run for
the same PR. This workflow does not configure branch protection or authorize merges.

A base branch advancing does not by itself trigger a new child-PR run. After a
stacked parent or `main` changes, an earlier green result may describe an old
merge result. Before integration, compare the recorded head/base/merge revisions
with the current PR, update the head branch from its intended target through the
normal review process, and verify a new successful run on that combination.
Rerunning an old workflow run does not establish coverage of a newer base.
[Strict required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)
can require the branch to be up to date before merging; that is separate repository
configuration, not enforcement provided or enabled by this workflow.

The job uses Ubuntu 24.04 and Python 3.11, with a 15-minute limit. Python 3.11 meets
the account tooling's `tomllib` requirement. The runner installs the existing
[screenshot manual dependencies](../skills/screenshot-manual/requirements.txt).
An explicit import check prevents their absence from silently skipping the manual
tests. It also installs Java 17 (Temurin), Node.js 24 and TLA+ tools v1.7.4, whose
download is checked against the sha256 that [`tools/registry.json`](../tools/registry.json)
records, and exports `TLA2TOOLS`. With them the vendored [statechart](../skills/statechart/SKILL.md)
test runs a small model through TLC; in CI it fails instead of skipping when the jar
or a supported runtime is missing. The token has only `contents: read`; checkout does not persist credentials.
No account configuration, model credentials or repository secrets are supplied.
Tests use their existing disposable synthetic fixtures.

The job also runs the [account transaction verifier's](../docs/verification/verify-account-transactions/SKILL.md)
real-code harness with its paired code mutations (stdlib only, about a minute). It
does not run that verifier's full run, whose TLA+ model check is available but whose
sync check walks history from the recorded sync commit, or its `--check-sync`; their
history depth and sync-commit timing are not yet defined for pull requests. Run both
locally as the verifier describes.

## Reproduce the checks

Start from a clean, committed checkout and use Python 3.11 in a disposable virtual
environment. Resolve an up-to-date local ref for the PR's actual target first;
`origin/main` below is an example, and a stacked PR must name its parent branch.
The commands do not fetch, rebase or merge for you.

```sh
(
set -e
python3.11 -m venv .local/ci-venv
.local/ci-venv/bin/python -m pip install -r skills/screenshot-manual/requirements.txt
.local/ci-venv/bin/python -c "import reportlab, pypdf, PIL"
# For the statechart TLC test: Java 11+, Node.js 22.18+ and the pinned jar (see tools/registry.json).
export TLA2TOOLS="$PWD/.local/tools/tla2tools-1.7.4/tla2tools.jar"
.local/ci-venv/bin/python -m unittest discover -s tests -v
.local/ci-venv/bin/python -m unittest discover -s skills/sdlc/scripts -p 'test_*.py' -v
.local/ci-venv/bin/python docs/verification/verify-account-transactions/scripts/conformance.py --mutations docs/verification/verify-account-transactions/model/expectations.json
.local/ci-venv/bin/python scripts/build_map.py --check
.local/ci-venv/bin/python scripts/build_workflow.py --check

.local/ci-venv/bin/python - <<'PY'
import json
import subprocess
from pathlib import Path

paths = subprocess.check_output(['git', 'ls-files', '-z', '*.json']).decode().split('\0')
for name in filter(None, paths):
    json.loads(Path(name).read_text(encoding='utf-8'))
print('Tracked JSON is valid.')
PY

CI_TARGET_REF=origin/main  # Replace with the PR's actual local target ref.
git diff --check "$CI_TARGET_REF"...HEAD
git diff --check
git diff --exit-code
checkout_status=$(git status --porcelain --untracked-files=all)
if [ -n "$checkout_status" ]; then
  printf '%s\n' "$checkout_status"
  exit 1
fi
)
```

The local three-dot diff checks committed branch changes since the merge base;
it is not an exact simulation of GitHub's merge result. In CI, checkout fetches
the proposed merge commit and its parents, and the whitespace command is instead:

```sh
git diff --check HEAD^1 HEAD
```

Use that command only on the actual proposed merge checkout, where `HEAD^1` is
the target parent. The local block additionally checks working-tree whitespace.
Both paths check preservation: CI's committed-diff check covers PR whitespace,
while `git diff --exit-code` and the porcelain status guard refuse tracked changes
and nonignored untracked files. Ignored local outputs such as `.local/` remain
allowed; the guard is not a secret scanner. The map builders validate catalog/workflow schemas and
their repository source links. This is not a complete Markdown-link, secret,
outgoing-history, browser, cross-platform, native-client or live-model audit.
The imported Archify package's separate Node/browser suite is not included.
Existing test skips remain visible in the job log; only the known missing manual
dependency skip is explicitly prevented. No generated artifacts are uploaded;
GitHub run logs follow repository retention settings. Preserve material readiness
results and exact revisions in the PR before those logs expire.

## Selected action revisions

Both actions are pinned to full commit hashes. Updates require checking the
upstream release and rerunning this workflow; comments are labels, not trust anchors.

- [actions/checkout v6.0.2](https://github.com/actions/checkout/releases/tag/v6.0.2):
  [`de0fac2e4500dabe0009e67214ff5f5447ce83dd`](https://github.com/actions/checkout/commit/de0fac2e4500dabe0009e67214ff5f5447ce83dd).
- [actions/setup-python v6.2.0](https://github.com/actions/setup-python/releases/tag/v6.2.0):
  [`a309ff8b426b58ec0e2a45f0f869d46889d02405`](https://github.com/actions/setup-python/commit/a309ff8b426b58ec0e2a45f0f869d46889d02405).

These selected releases use Node 24 and run on GitHub-hosted runners. They are
reviewed fixed revisions, not a promise to track the newest release automatically.
The design follows GitHub's [workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
and [secure use guidance](https://docs.github.com/en/actions/reference/security/secure-use).
No branch or path filter is used: skipped required workflows can remain pending,
as documented by GitHub and reported in this [community discussion](https://github.com/orgs/community/discussions/44490).
