https://claude.com/blog/the-ai-native-sdlc-playbook

멀티모델 환경에서는 `Claude`가 아니라 **artifact·policy·gate가 중심**이 되어야 합니다.
Anthropic이 강조하는 `intent → spec → plan → diff/test → review → incident`의 연결 구조는 그대로 유지하되, 어떤 모델이 들어와도 교체 가능하도록 만드는 것이 핵심입니다.

특히 `AGENTS.md`를 공통 원본으로 두는 것이 좋습니다. Codex는 이를 지속적인 repository context로 권장하고, Grok Build도 직접 지원하며, Claude Code는 `CLAUDE.md`에서 AGENTS.md를 import하는 방식을 공식 문서에서 제시합니다.

# Model-Agnostic AI-Native SDLC Playbook v2

## 1. 기본 원칙

AI-Native SDLC의 중심은 특정 모델이나 agent harness가 아니다.

중심은 다음 흐름이다.

`Intent → Spec → Plan → Build → Verify → Review → Merge → Deploy → Observe → Intent`

각 단계는 다음 단계가 읽을 수 있는 **명시적인 artifact**를 남긴다.

Claude Code, Codex, Grok Build, Cursor, 자체 Agent Harness 등은 이 artifact를 읽고 작업하는 interchangeable worker로 취급한다.

따라서 다음과 같이 생각한다.

> Model은 작업자다.
> Harness는 실행 환경이다.
> Git/Jira/CI와 artifact가 시스템이다.

Anthropic의 원문도 각 단계가 version-controlled artifact를 생성하고 다음 단계가 이를 읽도록 하는 것을 핵심 구조로 제시한다.

## 2. Claude 전용 개념을 범용 개념으로 변경

|Anthropic 표현|Model-neutral 표현|
|---|---|
|Claude|Coding Agent|
|Claude Code|Agent Harness|
|`CLAUDE.md`|Repository Instructions|
|Claude Skills|Reusable Agent Procedure / Policy|
|Hooks|Deterministic Guardrail|
|Plan Mode|Read/Plan-only phase|
|Subagent|Isolated worker/verifier|
|Claude Code Review|AI PR Reviewer|
|Claude Code Action|CI Agent Runner|
|MCP|Controlled Tool Interface|
|Claude Tag|Event-triggered Agent|
|Auto Mode|Bounded Autonomous Execution|

여기서 중요한 원칙은 **instruction과 enforcement를 구분하는 것**이다.

`AGENTS.md`, Skills, 프롬프트:

> "이렇게 행동해야 한다."

CI, hooks, sandbox, branch protection:

> "이 행동 외에는 실제로 할 수 없다."

Anthropic도 Skills 같은 instruction은 advisory control이고 반드시 지켜야 하는 정책은 hook이나 PR check 같은 deterministic control로 보강해야 한다고 설명한다.

OpenAI 역시 Codex를 실제 조직에서 운영할 때 sandbox, approval policy, network policy, command rules, managed configuration을 별도 enforcement layer로 사용한다.

## 3. Repository 구조

권장 구조:

```
repo/
│
├── AGENTS.md
├── CLAUDE.md
│
├── intent/
│   └── INT-123.md
│
├── specs/
│   └── INT-123.md
│
├── plans/
│   └── INT-123.md
│
├── agent/
│   ├── policies/
│   │   ├── security.md
│   │   ├── architecture.md
│   │   ├── frontend.md
│   │   └── database.md
│   │
│   ├── review/
│   │   └── REVIEW.md
│   │
│   ├── evals/
│   └── templates/
│
├── .claude/
│   ├── skills/
│   ├── agents/
│   └── rules/
│
├── .grok/
│   ├── skills/
│   └── config.toml
│
└── .github/
    └── workflows/
```

### AGENTS.md

이 파일을 **공통 Source of Truth**로 사용한다.

포함할 내용:
- 시스템과 제품의 핵심 invariant
- architecture boundaries
- 디렉터리 구조
- build/test/lint 명령
- coding conventions
- dependency 정책
- database migration 규칙
- 기본 개발 workflow
- 반드시 수행해야 하는 검증
- 금지된 행동
- Done Definition
- 상세 정책 문서의 위치

Business rule이나 architecture rule을 `.claude/` 또는 `.grok/` 안에 직접 넣지 않는 것이 중요하다.
특정 vendor 디렉터리는 adapter 역할만 한다.

### CLAUDE.md

```
@AGENTS.md

# Claude-specific instructions

...
```

Claude Code 공식 문서도 여러 agent를 사용하는 repository에서는 이 구조를 권장한다.
Codex는 `AGENTS.md`를 repository-level persistent context로 사용하도록 권장한다.

Grok Build 역시 `AGENTS.md`를 읽으며 동시에 Claude Code의 `CLAUDE.md`, skills, hooks, agents, MCP 구성을 읽을 수 있다.

결과적으로:

```
                AGENTS.md
                    │
          ┌─────────┼─────────┐
          │         │         │
       Codex      Claude     Grok
                   │
                CLAUDE.md
                @AGENTS.md
```

가 된다.

## 4. Stage 1 — Intent

모든 작업은 Code가 아니라 **Intent**에서 시작한다.

입력은 다음 어느 것이든 가능하다.

```
Product Idea
Customer Feedback
Bug
Incident
Jira Issue
GitHub Issue
Monitoring Alert
Technical Debt
```

이를 Agent가 `intent.md` 형태로 정규화한다.

필수 항목:

```
# Intent
## Problem
## Desired Outcome
## Users / Systems affected
## Constraints
## Out of Scope
## Acceptance Criteria
## Risks
## Open Questions
## Source
JIRA-123 / GH-456 / INCIDENT-23
```

AI가 intent를 작성할 수 있지만 **Product/Issue owner가 intent를 승인한다.**
이것이 첫 번째 human gate다.

## 5. Stage 2 — Spec

승인된 Intent를 기반으로 Agent가 technical/product spec을 작성한다.
이 단계에서는 구현하지 않는다.
Agent에게 다음을 요구한다.

```
Read intent.
Read architecture policies.
Read security policies.
Inspect the relevant code.

Produce spec.md.

Do not modify source code.
```

Spec은 최소 다음을 포함한다.

```
Requirements
Architecture
Interfaces
Data model
Security
UX behavior
Failure behavior
Migration
Observability
Testing strategy
Alternatives considered
Risks
```

중요한 변화는 **policy review를 개발이 끝난 뒤 하지 않는 것**이다.

Security / UX / Architecture / Compliance 정책을 spec 작성 시점에 이미 적용한다.
Anthropic playbook의 중요한 주장 중 하나도 이것이다.

## 6. Stage 3 — Plan

Build Agent는 바로 코딩하지 않는다.
먼저 repository를 분석한 뒤 `plan.md`를 작성한다.

```
Intent
   ↓
Spec
   ↓
Repository inspection
   ↓
Plan
   ↓
Approval
   ↓
Implementation
```

Plan은 다음을 명확하게 해야 한다.

```
Files to change
Files to add/delete
Implementation order
Dependencies
Tests to add
Migration
Rollback
Risks
Expected blast radius
```

그리고 다음 질문을 반드시 수행한다.

```
What could this break?

What is the riskiest part?

What alternative implementation did you reject?

How will you prove the implementation works?
```

Codex 역시 큰 변경은 먼저 Ask/계획 단계에서 implementation plan을 만들고 그 후 코드 작업으로 넘어가는 방식을 권장한다.
Grok Build 역시 별도의 Plan Mode와 plan approval gate를 제공한다.

즉 Plan Mode는 Claude 기능이 아니라 **Agentic Engineering Pattern**으로 취급한다.

## 7. Stage 4 — Build

각 작업 Agent는 독립된 worktree/branch에서 작업한다.

원칙:

```
1 task
=
1 agent session
=
1 worktree
=
1 branch
=
1 PR
```

가능하면 서로 같은 파일을 수정하는 두 Agent를 동시에 실행하지 않는다.

큰 기능은 dependency graph를 만들어 독립적인 작업으로 분할한다.

예:

```
                 API
                  │
          ┌───────┴────────┐
          │                │
       Frontend          Tests
          │
          └───────┬────────┘
                  │
              Integration
```

각 node는 별도 Agent가 맡을 수 있다.

Anthropic 역시 parallel agent session에 worktree isolation을 권장한다.

## 8. Stage 5 — Self Verification

Builder는 "코딩 완료"라고 말할 수 없다.

다음 상태가 되어야 완료다.

```
Implementation
      ↓
Unit tests
      ↓
Integration tests
      ↓
Lint / Type check
      ↓
Build
      ↓
Runtime verification
      ↓
Artifact comparison
      ↓
Ready for review
```

특히 버그 수정은 다음 순서를 기본으로 한다.

```
Reproduce
↓
Failing Test
↓
Confirm Failure
↓
Fix
↓
Test Pass
↓
Regression Tests
```

가능하면 기존 failing test를 Builder가 수정하지 못하도록 제한한다.

UI 변경은:

```
Implement
→ Browser
→ Screenshot
→ Compare
→ Adjust
```

와 같은 feedback loop를 만든다.

Anthropic 역시 "모든 세션이 사람이 보기 전에 자신의 작업을 검증해야 한다"고 강조한다.

# 9. Stage 6 — Independent Verification

여기서 기존 playbook을 한 단계 강화한다.

**Builder와 Verifier를 분리한다.**

최소 조건:

```
Builder context != Verifier context
```

보다 중요한 변경에서는:

```
Builder model != Verifier model
```

을 사용한다.

예:

```
Claude → build
Codex → verify
```

또는

```
Codex → build
Grok → verify
```

Verifier에게는 가능하면 write 권한을 주지 않는다.

Verifier의 역할은:

```
Run
Inspect
Test
Challenge
Report
```

이지,

```
Fix
```

가 아니다.

Builder 자신의 가정을 그대로 가진 context에서 self-review하면 오류가 그대로 전달될 가능성이 있기 때문이다. Anthropic도 final verifier를 별도 fresh context로 실행하는 패턴을 권장한다.

## 10. Stage 7 — PR Review

여기서 멀티모델의 이점을 적극적으로 사용한다.

권장 구조:

```
                PR
                 │
        ┌────────┴─────────┐
        │                  │
  Deterministic CI       AI Review
        │                  │
        │          ┌───────┼───────┐
        │          │       │       │
        │        Logic  Security  Spec
        │
        └──────────┬───────────────
                   │
             Human Review
                   │
                 Merge
```

## AI reviewer 역할을 나눈다

모든 모델에게 똑같이

> "이 PR 리뷰해."

라고 하지 않는다.

예:
### Reviewer A
Correctness / regression
```
Logic errors
Edge cases
Concurrency
Data consistency
Error handling
```

### Reviewer B
Security / abuse
```
Auth
Authorization
Injection
Secrets
PII
Dependency risk
Privilege escalation
```

### Reviewer C
Intent / architecture
```
intent.md
spec.md
plan.md
architecture policy
scope creep
```

이렇게 review lens를 나누는 것이 낫다.

## 11. Cross-Model Review

다음 정책을 추천한다.

| PR 작성  | 1차 리뷰  | 2차 리뷰 |
| ------ | ------ | ----- |
| Claude | Codex  | Grok  |
| Codex  | Claude | Grok  |
| Grok   | Claude | Codex |

단, 모델 이름 자체가 중요한 것은 아니다.

실제 내부 eval에서 각 역할별 성능을 측정해서:

```
Builder
Reviewer
Security reviewer
Planner
Debugging
Frontend
Migration
```

역할별 모델을 선택한다.

즉:

> Best Model을 찾지 말고
> Best Model × Role 조합을 찾는다.

그리고 **PR을 만든 모델을 유일한 reviewer로 사용하지 않는다.**

## 12. Review Comment Protocol

AI Review 결과를 자유로운 자연어 comment로 남기지 않는다.

다음 schema로 통일한다.

```
Severity:
BLOCKER / HIGH / MEDIUM / LOW / NIT

Category:
Bug / Security / Architecture / Spec / Test / Performance

Location:
file + line

Finding:

Evidence:

Why this matters:

How to reproduce:

Related policy/spec:

Confidence:
High / Medium / Low
```

LOW confidence + LOW severity comment는 PR에 남기지 않도록 할 수도 있다.

목표는 AI가 수십 개의 사소한 comment를 만드는 것이 아니라:

> 인간이 확인해야 할 정보량을 줄이는 것

이다.

# 13. Fix Loop

PR 작성 Agent가 review comment를 처리한다.

예:

```
Codex creates PR
      ↓
Claude review
Grok review
CI
      ↓
Codex receives findings
      ↓
Codex:
accept / reject each finding
fix accepted findings
explain rejected findings
      ↓
CI again
      ↓
Claude/Grok re-review changed diff
      ↓
Human approval
      ↓
Merge
```

원칙적으로 Reviewer가 author branch를 직접 수정하지 않는다.

그래야:

```
Generator
↓
Critic
↓
Generator
↓
Critic
```

의 역할 분리가 유지된다.
서로 다른 Agent가 계속 코드를 덮어쓰는 구조는 피한다.

## 14. Human Review의 역할도 변경

사람이 AI가 생성한 수천 줄을 전부 다시 읽는 방식은 결국 병목이 된다.
Human reviewer가 주로 보는 것은 다음이다.

```
Does this solve the Intent?
Is the risk acceptable?
Did the architecture direction change?
Are the assumptions correct?
Do I trust the evidence?
Is production impact acceptable?
```

즉 인간은:

```
code reviewer
```

에서

```
intent + risk reviewer
```

로 점차 이동한다.

Anthropic playbook도 AI review가 기본적인 review passes를 수행하고 사람의 관심은 intent와 risk 판단으로 이동하는 구조를 제안한다.

## 15. Agent Governance

Agent에 규칙을 "말해주는 것"만으로 보안을 처리하지 않는다.

다음 계층을 사용한다.

```
Layer 1
AGENTS.md / Skills
→ Guidance

Layer 2
Tool allowlist
→ Capability

Layer 3
Sandbox
→ Execution boundary

Layer 4
Hooks / Policy
→ Action control

Layer 5
CI
→ Artifact verification

Layer 6
Branch protection
→ Repository control

Layer 7
Production approval
→ Deployment boundary
```

OpenAI도 Codex 내부 운영 시 sandbox와 approval을 별개 control로 두고 network access, credentials, command rules, managed configs, telemetry를 함께 사용하고 있다.

Grok Build 역시 permission과 sandbox가 서로 별개의 계층이라고 명시한다.

## 16. Autonomy Levels

팀 차원에서 Agent 권한을 명시적으로 정의한다.

|Level|Agent 권한|
|---|---|
|A0|Read only|
|A1|Plan 작성|
|A2|Local code 수정 + test|
|A3|Branch push + PR 생성|
|A4|PR comment 자동 수정|
|A5|Staging deploy|
|A6|Production release 준비|
|A7|Pre-approved runbook 실행|

기본적으로 production deploy 자체는 human gate 뒤에 둔다.

```
Agent can prepare production.
Agent cannot authorize production.
```

Anthropic playbook 역시 개발 환경에서는 높은 autonomy를 허용하더라도 production에서는 명시적 gate를 두는 구조를 권장한다.

## 17. Agent Identity

자동 Agent는 가능하면 사람의 credential을 공유하지 않는다.

예:
```
agent-codex-builder
agent-claude-reviewer
agent-grok-security
agent-release-bot
```

각 agent action이 누구에 의해 발생했는지 추적 가능해야 한다.

저장해야 할 것은:
```
Agent
Harness
Model/version
Task/Issue ID
Base commit
Result commit
Tools invoked
Tests executed
Approval events
Policy violations
PR
Deployment
```

저장하지 않아도 되는 것은 모델의 비공개 internal chain-of-thought다.

대신 **결정 요약, evidence, tool/action log**를 남긴다.

OpenAI 역시 agent 운영에서 prompt, tool approval, execution result, MCP 사용, network policy decision 등을 telemetry/audit 대상으로 활용한다.

## 18. Model/Harness 변경을 코드 변경처럼 취급

중요한 추가 원칙이다.
다음 변경도 production behavior 변경이다.

```
AGENTS.md
CLAUDE.md
Skill
Hook
Prompt
MCP
Tool permission
Agent definition
Model
Reasoning level
Harness version
```

따라서 변경되면 Agent Eval을 실행한다.

예:

```
AGENTS.md modified
      ↓
Agent Eval CI
      ↓
50 representative tasks
      ↓
Pass / regression comparison
      ↓
Merge
```

Anthropic도 agent configuration 자체를 regression test하는 continuous eval 구조를 권장한다.

## 19. Incident → Eval

Production incident가 발생하면 단순히 bug fix만 하지 않는다.

```
Incident
   ↓
Root cause
   ↓
Fix
   ↓
Regression test
   ↓
Agent eval
   ↓
Policy/AGENTS update if required
```

같은 종류의 실수를 Agent가 다시 만들 수 없도록 해야 한다.
Anthropic playbook도 production incident를 permanent eval로 전환하는 것을 권장한다.

## 20. Jira/GitHub와 Markdown의 관계

`intent.md` 때문에 Jira를 없앨 필요는 없다.
Source of Truth를 artifact 종류별로 하나씩 정의한다.

예:
```
Business Issue
→ Jira

Code change
→ GitHub PR

Intent / Spec / Plan
→ Git repository

Design
→ Figma

Production incident
→ Incident system
```

서로 ID를 연결한다.

```
JIRA-142
 ↓
intent/142.md
 ↓
specs/142.md
 ↓
plans/142.md
 ↓
PR #931
 ↓
commit abc123
 ↓
deploy #1923
```

Anthropic 역시 기존 Jira나 requirement system을 제거하는 것이 아니라 각 artifact에 대해 Source of Truth를 정하고 commit SHA/record ID로 연결하는 방식을 권장한다.

## 21. 자동화할 최종 Workflow

목표 상태는 다음이다.

```
Issue created
     ↓
Triage Agent
     ↓
intent.md
     ↓
Product Owner Gate
     ↓
Spec Agent
     ↓
spec.md
     ↓
Technical Gate
     ↓
Planner Agent
     ↓
plan.md
     ↓
Builder Agent
     ↓
worktree
     ↓
Self verification
     ↓
PR
     ↓
Deterministic CI
     ↓
Independent Verifier
     ↓
Claude/Codex/Grok Reviewers
     ↓
Author Agent Fix
     ↓
Re-review
     ↓
Human Risk/Intent Approval
     ↓
Merge
     ↓
Staging
     ↓
Production Gate
     ↓
Production
     ↓
Monitoring
     ↓
Incident / Feedback
     ↓
new intent.md
```

이것이 AI-Native SDLC의 실제 loop다.

## 22. 반드시 지킬 운영 규칙

**Rule 1 — No build without intent**
모든 의미 있는 변경은 Issue/Intent에서 시작한다.

**Rule 2 — No coding before plan for non-trivial changes**
바로 코딩하지 않는다.

**Rule 3 — Every agent must have feedback**
Test/build/runtime/browser 중 하나 이상으로 자신의 작업을 검증해야 한다.

**Rule 4 — Generator and evaluator are separate roles**
동일 session에서 생성과 최종 검증을 끝내지 않는다.

**Rule 5 — Deterministic checks beat model instructions**
반드시 지켜야 하는 것은 prompt가 아니라 code/policy로 강제한다.

**Rule 6 — Agent writes branch, not main**
모든 Agent 변경은 PR을 거친다.

**Rule 7 — Production requires explicit authorization**
Agent가 production 준비는 해도 production 승인자가 되어서는 안 된다.

**Rule 8 — Every incident becomes knowledge**
Regression test 또는 eval 또는 policy 중 최소 하나가 추가되어야 한다.

**Rule 9 — Repeated review comment becomes instruction**
동일 실수가 반복되면 `AGENTS.md`, policy 또는 deterministic check로 승격한다.

**Rule 10 — Models are replaceable**
Workflow가 Claude/Codex/Grok API나 특정 UI에 종속되어서는 안 된다.

## 23. 권장 멀티모델 운영 형태

초기에는 복잡한 multi-agent framework부터 만들 필요가 없다.

### Phase 1

```
Developer
↓
Claude / Codex / Grok
↓
PR
↓
Human
```

### Phase 2

```
Builder Agent
↓
PR
↓
Different-model Reviewer
↓
Human
```

### Phase 3

```
Builder
↓
Verifier
↓
PR
↓
Correctness Reviewer
↓
Security Reviewer
↓
Human
```

### Phase 4

```
Issue
↓
Orchestrator
↓
Plan
↓
Parallel Builders
↓
Verifiers
↓
Cross-model Review
↓
Human Gate
↓
Deploy
```

### Phase 5

```
Monitoring
       ↑
       │
Issue → Agents → PR → Deploy
  ↑                    │
  └──── incident ──────┘
```

이 단계에서야 autonomous software factory에 가까워진다.


## 24. 최종 Architecture

```
                      ┌──────────────────┐
                      │ Jira / GitHub    │
                      │ Intent / Incident│
                      └────────┬─────────┘
                               │
                        ORCHESTRATOR
                               │
              ┌────────────────┼────────────────┐
              │                │                │
          Planner          Researcher       Architect
              │
              └────────────────┬────────────────┘
                               │
                            plan.md
                               │
                    ┌──────────┴──────────┐
                    │                     │
                 Builder A             Builder B
                 worktree              worktree
                    │                     │
                    └──────────┬──────────┘
                               │
                            Verifier
                               │
                               PR
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
      Static/CI          AI Reviewer A        AI Reviewer B
                            Claude                Grok
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                         Author Agent
                             fixes
                               │
                            re-review
                               │
                          Human Gate
                               │
                             Merge
                               │
                            Staging
                               │
                        Production Gate
                               │
                          Production
                               │
                           Monitoring
                               │
                            Incident
                               │
                          new intent.md
```

이 구조에서는 Claude, Codex, Grok 중 하나가 없어져도 SDLC 자체에는 영향이 없다.

그것이 model-agnostic AI-Native SDLC가 가져야 할 가장 중요한 특성이다.

특히 지금 구성하려는 **“PR을 만든 모델과 다른 모델들이 리뷰하고, 원 작성 모델이 수정한 뒤 다시 리뷰받는 구조”** 는 이 playbook에 매우 잘 맞습니다.
다만 `Claude→Codex→Grok`처럼 모델 이름 중심으로 orchestration하기보다는 **Builder / Verifier / Correctness Reviewer / Security Reviewer 역할을 먼저 정의하고 그 역할별 eval 성능이 좋은 모델을 배치하는 방식**이 더 안정적입니다.

Anthropic 원안보다 가장 크게 보완하고 싶은 부분은 세 가지입니다.

① `AGENTS.md`를 vendor-neutral source of truth로 만들 것,
② 생성 모델과 최종 검증 모델을 분리할 것,
③ 프롬프트보다 CI·sandbox·branch protection 같은 deterministic enforcement를 상위 제어수단으로 둘 것

입니다. 이 세 가지만 적용해도 Claude Code에 종속되지 않는 구조가 됩니다.

![[20260821 Model-Agnostic AI-Native SDLC Playbook.png]]
