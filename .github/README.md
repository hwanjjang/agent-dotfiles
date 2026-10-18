# Pull request CI

[The workflow](workflows/ci.yml) provides the stable `Repository checks` job for
pull requests targeting any branch, including stacked PRs and documentation-only
changes. It runs on opening, updates, reopening, edits (including retargeting), and
ready-for-review events. It checks GitHub's proposed merge result, not only the
source branch. Merge conflicts or GitHub's fork-workflow approval requirements can
prevent a run; a missing check is not a pass. A newer run cancels the older run for
the same PR. This workflow does not configure branch protection or authorize merges.

The job uses Ubuntu 24.04 and Python 3.11, with a 15-minute limit. Python 3.11 meets
the account tooling's `tomllib` requirement. The runner installs only the existing
[screenshot manual dependencies](../skills/screenshot-manual/requirements.txt).
An explicit import check prevents their absence from silently skipping the manual
tests. The token has only `contents: read`; checkout does not persist credentials.
No account configuration, model credentials or repository secrets are supplied.
Tests use their existing disposable synthetic fixtures.

## Reproduce the checks

Use Python 3.11 in a disposable virtual environment from the checkout root:

```sh
python3.11 -m venv .local/ci-venv
.local/ci-venv/bin/python -m pip install -r skills/screenshot-manual/requirements.txt
.local/ci-venv/bin/python -c "import reportlab, pypdf, PIL"
.local/ci-venv/bin/python -m unittest discover -s tests -v
.local/ci-venv/bin/python -m unittest discover -s skills/sdlc/scripts -p 'test_*.py' -v
.local/ci-venv/bin/python scripts/build_map.py --check
.local/ci-venv/bin/python scripts/build_workflow.py --check
git diff --check
```

The workflow fetches the merge commit and its parents, checks whitespace in
`git diff --check HEAD^1 HEAD` (the PR merge result against its target parent),
parses all tracked JSON, and requires tests to leave tracked
source unchanged (`git diff --exit-code`). Its inline JSON step can be run locally
with the same interpreter. The map builders validate catalog/workflow schemas and
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
