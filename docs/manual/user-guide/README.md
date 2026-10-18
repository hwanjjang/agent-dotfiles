# Agent-dotfiles bilingual user manual

English and Korean editions cover the same 18 scenarios, captured on 2026-10-17.
Read `manual-en.md` or `manual-ko.md`, or use the delivered PDFs. Screenshot paths
are relative to these sources. The actual map UI remains English in both editions.

## Product identity and coverage

- Repository: https://github.com/hwanjjang/agent-dotfiles
- Installation baseline: `ed1da039fdac3da7639f6d9d361f564ad2dffb92`.
- Map and observation examples: the feature candidate based on that commit, captured before its commit;
  file hashes are recorded in `capture-manifest.json`. A fresh clone of the
  baseline does not contain the observation candidate or updated map.
- Exercised in a disposable account: preview, install, status, unchanged update,
  uninstall, guarded rollback; synthetic grant, capture, retry, read, index,
  revoke, old-epoch disabling and empty read after deletion.
- Map browser recipe: `docs/verification/verify-repository/scripts/check-workflow.cjs`;
  scenario authority: `docs/verification/verify-repository/features/workflow-map.md`.
  Navigation, new improvement-cycle nodes, status boundaries and source links passed.
- Authenticated native clients, live MCP services, native observation hooks and
  model-driven SDLC execution were not exercised. No model evaluation or measured
  improvement is claimed. Comparative eval and automatic promotion remain planned.

Map images are screenshots of the real local map. Console images are screenshots
of a document showing selected actual CLI JSON, with sanitized paths and shortened
command prefixes. They are not screenshots of a native terminal application.
`eval-cases.png` and `eval-plan.png` are clearly labeled design illustrations.
The overview is for orientation; use the interactive map to read individual nodes.

For the later account qualification commands, use the
[doctor guide](../../../account/README.md#diagnose-and-exercise-the-installation)
and [screenshot walkthrough](../README.md#account-installation-guide-walkthrough).
The screenshots here retain their capture baseline; they do not demonstrate the
doctor or a comparative eval run. The improvement design owns the
[connection between qualification and eval](../../decisions/account-improvement-loop.md#account-qualification-and-reuse).
The later [Claude/Codex collection guide](../../../account/observation/native.md) covers
explicit native opt-in, verification and revocation. The bilingual editions' native
collection status describes their earlier capture baseline; current support is
documented in that guide. No screenshot here is evidence of native collection.

## Current held-out design amendment — 2026-10-18

The editable `eval-plan.example.json` now follows the
[same-host held-out protocol](../../decisions/account-improvement-loop.md#same-host-held-out-evaluation):
fresh contexts and recorded exposure on the existing host/account, with no external
custodian or additional environment. The PDFs and design-illustration screenshots
retain their explicitly dated 2026-10-17 capture baseline; they are not evidence
of the revised protocol or an executed comparison. Use the linked design for
current requirements. The capture hashes remain historical, not rewritten to
claim a new capture. PDF source instructions and screenshots were not changed.

## SDLC text amendment - 2026-10-19

Pages 5-7 in both languages now explain the single `sdlc` entry, outcome and
endpoint, evidence-based method selection, artifact reuse and reassessment on
resumption or scope change. The source is the [intake method](../../../skills/sdlc/references/intake.md).
The [native verification record](../../verification/sdlc-intake.md) and
[separate intake walkthrough](../sdlc-intake.pdf) provide bounded execution evidence;
these map screenshots do not demonstrate model-driven intake.

Only these three steps changed. Screenshots and their 2026-10-17 capture hashes
remain historical. The capture manifest preserves the earlier delivered-PDF hashes
and records the current PDFs under `post_capture_updates.sdlc_intake`. Other sections retain their original status statements and
later amendments above. The two PDFs were rebuilt with Nanum Gothic (SIL OFL 1.1,
editable embedding permitted); no font file is redistributed. All 36 pages were
rendered and visually inspected; both editions retain 18 pages, with matching
JSON/Markdown text and extractable page titles.

## Edit and rebuild

`manual-en.json` and `manual-ko.json` are direct PDF inputs. Edit matching step IDs
in both languages and keep the readable Markdown copies and aligned
`bilingual-source.json` in sync. Retain the implemented/planned distinctions.

Use an isolated Python environment and an appropriately licensed TTF covering
both Latin and Korean. The font used for this build permitted editable embedding;
no font file is redistributed. Install the pinned packages in `requirements.txt`.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python build-guide.py manual-en.json manual-en.pdf --font /path/to/korean-capable.ttf
.venv/bin/python build-guide.py manual-ko.json manual-ko.pdf --font /path/to/korean-capable.ttf
.venv/bin/python render-pages.py manual-en.pdf renders-en
.venv/bin/python render-pages.py manual-ko.pdf renders-ko
```

Use `--overwrite` only for an intentional PDF replacement and use a new render
directory for each review. Inspect every page after edits: rendering alone is not
visual review. The delivered editions each have 18 pages. All 36 rendered pages
were inspected for clipping, overlap, missing glyphs, captions and legibility;
page titles and expected-outcome labels were also checked through PDF extraction.
After PR review, the English page 12 caption was corrected from “rejected” to
“disabled”. All 18 English pages were re-rendered: page 12 was visually rechecked,
and the other 17 pages were pixel-identical to the reviewed edition. The Korean
PDF was unchanged.

The bundled builder and renderer are reproduction snapshots, not new authoritative skill implementations. They come from `skills/screenshot-manual/scripts/` in the
repository (MIT; see LICENSE). The only builder adaptation is a localized
`expected_label` read from the source JSON.

## Try the included observation demo

Use Python 3.11+ and a candidate checkout with `account/observation/store.py`:

```sh
python3.11 demo-observations.py --repo /path/to/candidate-checkout
```

The demo creates and removes its own temporary home and project. It makes no model
calls and does not enable native collection. It requires no third-party packages.

`eval-plan.example.json` and `eval-cases.example.json` are editable design
worksheets, not an executable eval suite or completed results. Replace placeholders
and implement and qualify runners, fixtures and graders before a real comparison.
No evaluator holdouts are included. Raw operational logs, account data, credentials,
authenticated browser state and private filesystem paths are excluded from this
bundle. This delivery does not publish or activate account settings.

## 한국어 안내

`manual-ko.md`와 한국어 PDF는 영문판과 같은 18개 절차를 다룹니다.
두 JSON에서 같은 step ID를 함께 수정하고 PDF를 다시 만든 뒤 모든 페이지를
확인하세요. 실제 지도 UI는 영어이므로 두 언어판에 같은 화면을 사용했습니다.
설치 예제는 위 커밋, 관찰 예제와 지도는 현재 로컬 후보 소스 기준입니다.
`demo-observations.py`는 임시 계정만 사용합니다. 두 eval 예제 JSON은 아직
실행할 수 없는 설계용 문서이며 실제 비교 점수나 개선 성과를 뜻하지 않습니다.
