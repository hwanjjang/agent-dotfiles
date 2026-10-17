# Agent-dotfiles 사용자 매뉴얼

설치, AK SDLC, 근거에 기반한 skill 개선 | 2026-10-17

## 1. 이 매뉴얼을 따라가는 순서

설치와 확인은 2-4쪽, 일상 작업과 AK SDLC map은 5-8쪽, 업데이트는 9쪽, 개인 기록은 10-12쪽, skill 개선과 eval은 13-17쪽에서 설명합니다. 18쪽은 문제 해결입니다.
현재 실행 가능: 커밋 기반 계정 설치, 로컬 합성 기록 CLI. 구현 예정: native 자동 수집, 작업 분석, 모델 비교 eval, 자동 개선 반영.
설치는 커밋 ed1da03으로 검증했습니다. 기록 예제는 해당 배포 버전이 아닌 현재 로컬 후보 체크아웃을 사용합니다. 화면에는 합성 데이터만 담았습니다.

![현재 AK SDLC map의 실제 화면입니다. 지도를 여는 것만으로 skill이 실행되지는 않습니다.](screenshots/map-overview.png)

현재 AK SDLC map의 실제 화면입니다. 지도를 여는 것만으로 skill이 실행되지는 않습니다.

**확인할 결과:** 지금 실행할 수 있는 절차와 앞으로 구현할 절차를 구분할 수 있습니다. 전체 모델 기반 SDLC 실행이나 skill 성능 향상을 검증했다는 뜻은 아닙니다.

## 2. 설치 환경을 준비하고 안내서 열기

macOS 또는 Linux를 사용합니다. WSL 내부 Linux도 지원합니다. Git, Python 3.11 이상과 사용할 에이전트 클라이언트를 먼저 설치하세요. 이 installer는 native Windows를 지원하지 않습니다. 클라이언트 계정과 인증 정보는 별도로 준비합니다.
https://github.com/hwanjjang/agent-dotfiles 를 clone하고 체크아웃으로 이동합니다. docs/map/workflow.html을 로컬에서 열고 Anytime의 account-source → Sources에서 account/README.md를 읽습니다.
기본 클라이언트 디렉터리가 지원 대상입니다. CODEX_HOME 등의 사용자 지정 경로가 있다면 적용 전에 정리합니다.

![실제 account-source 상세 화면입니다. 사용 시점, 설치 안내와 원본 문서 링크가 보입니다.](screenshots/map-install.png)

실제 account-source 상세 화면입니다. 사용 시점, 설치 안내와 원본 문서 링크가 보입니다.

**확인할 결과:** 로컬 소스와 필요한 도구가 준비됩니다. clone만으로 계정 설정, 클라이언트, 모델 이용 권한이나 인증 정보가 설치되지는 않습니다.

## 3. 변경 내용을 확인한 뒤 설치하기

체크아웃에서 먼저 실행합니다.
sh scripts/setup-account.sh install
버전, 대상 경로, 충돌과 필요한 실행 파일을 확인합니다. 영향을 받는 에이전트 세션을 닫고, 의도한 변경이면 적용합니다.
sh scripts/setup-account.sh install --apply
연습할 때는 체크아웃 밖에 빈 디렉터리를 만들고 두 명령 모두에 --home /path/to/disposable-account를 추가합니다. HOME 자체를 바꾸지 않습니다.
installer는 기본적으로 HEAD 커밋을 읽습니다. 커밋하지 않은 수정은 설치되지 않습니다. 충돌이 있으면 정확히 저장한 preview를 검토하고 --approve-plan으로 지정합니다.

![임시 계정에서 실제 실행한 설치 결과 중 필요한 JSON 필드를 표시했습니다. 경로와 명령 접두어는 축약했습니다.](screenshots/console-install.png)

임시 계정에서 실제 실행한 설치 결과 중 필요한 JSON 필드를 표시했습니다. 경로와 명령 접두어는 축약했습니다.

**확인할 결과:** 관리 대상 파일과 설정이 설치되고 소스 버전과 복구용 transaction이 남습니다. 클라이언트에서 별도로 확인하기 전에는 native_activation_verified가 false입니다.

## 4. 설치 상태와 실제 클라이언트 동작 확인하기

sh scripts/setup-account.sh status를 실행합니다. installed: true, drift: []인지 확인합니다. 이는 관리 대상 파일과 설정의 상태 검사입니다.
다음으로 임시 프로젝트에서 native 클라이언트를 열어 skill 목록과 로드된 지침 출처를 확인합니다. 작은 작업에 적절한 skill 하나를 사용하고 실제 결과를 확인하세요. planning hook을 쓴다면 클라이언트에서 Codex hook 신뢰 설정을 확인하고 선택한 계획이 복구되는지도 확인합니다.
MCP 도구 발견과 인증은 연결 검사로 따로 확인합니다. 토큰을 매뉴얼, 스크린샷이나 추적 파일에 넣지 않습니다. 이번 매뉴얼에서는 인증된 native 클라이언트를 실행하지 않았습니다.

![실제 status와 변경 없는 update의 출력입니다. 파일 설치가 정상이어도 native_activation_verified는 false입니다.](screenshots/console-status.png)

실제 status와 변경 없는 update의 출력입니다. 파일 설치가 정상이어도 native_activation_verified는 false입니다.

**확인할 결과:** 파일 전달, skill 발견, 지침 준수, hook 동작, MCP 연결을 각각 확인합니다. 설치 영수증이 정상이라고 정책을 지켰다고 판단하지 않습니다.

## 5. AK SDLC map을 필요한 만큼 사용하기

docs/map/workflow.html을 열고 왼쪽부터 읽습니다. Triage → Intent → Investigation → Specification → Design → Plan → Test design → Build → Self-verification → PR review → Correction → Merge → Completion 순서입니다.
현재 작업에 필요한 방법만 고릅니다. 작은 로컬 작업은 개별 skill을 바로 사용할 수 있습니다. 전체 SDLC를 시작할 필요는 없습니다. Intent의 두 인터뷰는 선택지이며 모두 수행하는 필수 순서가 아닙니다.
+ / -, Fit과 배경 드래그로 이동합니다. Search는 배치를 유지하면서 관련 없는 노드를 흐리게 만듭니다. 노드를 열고 상세 설명과 Sources를 확인합니다. Escape로 닫습니다.

![현재 지도의 실제 전체 화면입니다. 전체 흐름을 확인한 다음 확대해서 개별 노드를 읽으세요.](screenshots/map-overview.png)

현재 지도의 실제 전체 화면입니다. 전체 흐름을 확인한 다음 확대해서 개별 노드를 읽으세요.

**확인할 결과:** 작업에 맞는 방법과 그 원본 지침을 찾을 수 있습니다. 지도는 조건과 관계를 설명할 뿐, merge 권한을 부여하거나 작업을 실행하지 않습니다.

## 6. 확인 가능한 결과가 있는 첫 작업 실행하기

작은 로컬 버그에는 이렇게 요청할 수 있습니다. "빈 입력에서 문서에 정의된 오류를 반환하도록 파서를 수정해줘. TDD로 실패하는 검사와 수정 후 통과 결과를 보여주고, 로컬 검증까지 진행해줘."
지도에서 tdd를 엽니다. 빠진 동작을 드러내는 검사부터 시작하고, 최소한으로 수정한 뒤 관련 검사도 실행합니다. test-first가 어렵다면 대체 검증과 한계를 기록합니다.
규모가 있는 PR 작업은 종료 지점을 명시합니다. "AK SDLC로 pre-merge까지 진행하되 merge는 하지 마." pre-merge는 리뷰와 준비 완료이며 merge 권한은 아닙니다. skill 호출 문법은 클라이언트에서 실제 제공하는 방식을 확인하세요.

![실제 TDD 상세 화면입니다. 요청 문장은 사용법 예시이며 모델이 실행한 기록은 아닙니다.](screenshots/map-tdd.png)

실제 TDD 상세 화면입니다. 요청 문장은 사용법 예시이며 모델이 실행한 기록은 아닙니다.

**확인할 결과:** 실제 변경, 실행한 검사와 남은 한계가 완료 근거가 됩니다. 실행 결과 없이 테스트가 통과했다는 설명만으로 완료를 판단하지 않습니다.

## 7. 긴 작업을 중단 후에도 이어가기

여러 단계나 세션에 걸친 작업은 planning-with-files로 이름 있는 계획 하나를 유지합니다. 선택한 비공개 .planning/ 디렉터리에 task_plan.md, findings.md, progress.md를 둡니다. 재개할 때 기록된 진행 상황과 현재 체크아웃을 비교합니다.
여러 호스트가 동시에 작업하면 각각 PLAN_ID와 PWF_PLAN_ROOT를 지정하거나 별도 worktree를 사용합니다. 도구의 하위 프로세스에서 변수를 설정해도 이미 실행 중인 에이전트 호스트에 적용되지는 않습니다. 모호한 공용 active-plan 포인터에 의존하지 마세요.
다른 작업에는 Anytime을 이용합니다. 예를 들어 glossary를 검색하고 domain-modeling을 열 수 있습니다. 이런 방법을 쓴다고 전체 lifecycle을 시작해야 하는 것은 아닙니다.

![실제 planning-with-files 상세 화면입니다. native 자동 복구는 클라이언트별 hook 검증이 별도로 필요합니다.](screenshots/map-planning.png)

실제 planning-with-files 상세 화면입니다. native 자동 복구는 클라이언트별 hook 검증이 별도로 필요합니다.

**확인할 결과:** 작업별 현재 계획 하나에 실제 진행 상황과 다음 행동이 남습니다. 계획 기록은 로컬 자료이며 자동으로 공개 문서가 되지 않습니다.

## 8. 추가 연동은 필요한 것만 선택하기

기본 전달 대상은 Codex와 Claude Code입니다. Hermes가 이미 설치되어 있다면 --with-hermes로 preview합니다. Hermes 전달에는 native hook과 MCP 연동이 포함되지 않습니다.
MCP는 선택 사항입니다. 먼저 확인합니다.
sh scripts/setup-account.sh update --mcp github,context7,playwright
검토한 뒤 같은 선택에 --apply를 추가합니다. 이 템플릿의 GitHub 연결은 읽기 전용입니다. GITHUB_MCP_TOKEN과 CONTEXT7_API_KEY는 클라이언트 환경에 로컬로 제공하고 추적 JSON에는 넣지 않습니다.
planning hook 등록은 update --without-hooks --apply로 제거할 수 있습니다. 이는 앞으로 만들 관찰용 collector와 다릅니다. 선택 플래그를 생략하면 기존 선택을 유지합니다.

![지도에서 연 실제 planning-hooks 안내입니다. 계획 복구와 실행 관찰 수집은 서로 다른 기능입니다.](screenshots/map-hooks.png)

지도에서 연 실제 planning-hooks 안내입니다. 계획 복구와 실행 관찰 수집은 서로 다른 기능입니다.

**확인할 결과:** 의도한 연동만 선택됩니다. 설정 전달, 실행 파일, 신뢰 설정, 인증과 실제 작업 효과는 따로 검증합니다.

## 9. 업데이트·제거·복구하기

새 버전을 fetch하고 검토합니다. installer가 대신 fetch하지는 않습니다. 먼저 preview하고 적용합니다.
sh scripts/setup-account.sh update --revision origin/main
sh scripts/setup-account.sh update --revision origin/main --apply
적용 후 status를 확인합니다. 관리 대상 설치 내용을 제거하려면 uninstall을 preview한 다음 --apply를 추가합니다. 개인 설정과 소유하지 않은 파일은 보존합니다.
기록된 transaction은 rollback --transaction TRANSACTION_ID로 preview하고 --apply로 복구합니다. 최신 transaction부터 되돌립니다. 이후 수정 때문에 충돌하면 원인을 확인하고 강제 삭제하지 않습니다. 영수증과 백업은 비공개로 보관합니다.

![임시 계정에서 uninstall 후 guarded rollback을 실제 실행한 결과입니다. 설치가 drift 없이 복구됐습니다.](screenshots/console-rollback.png)

임시 계정에서 uninstall 후 guarded rollback을 실제 실행한 결과입니다. 설치가 drift 없이 복구됐습니다.

**확인할 결과:** 설치 버전과 관리 상태가 의도와 일치합니다. uninstall은 native 세션 로그나 관찰 기록을 삭제하지 않습니다. 관찰 등록은 별도로 철회해야 합니다.

## 10. self-improving loop의 전체 흐름 이해하기

Anytime의 Self-improvement & eval (1-6)을 엽니다. 관찰 → 재현 사례 → 수정 후보 → 비교 eval → 리뷰 → 배포 → 재관찰 순서이며, 기존 13단계 PR 절차와 별도입니다. 각 노드에서 현재 지원 상태와 원본 안내를 확인합니다.
배포와 롤백은 기존 installer가 담당합니다. 관찰 저장소가 설치된 skill이나 installer 상태를 직접 고치지 않습니다. 수집 동의는 원격 모델 전송이나 공개 권한이 아닙니다.
현재 이 흐름에서 구현된 것은 합성 관찰 저장소입니다. native 수집, 작업 연결, 분석, 모델 비교와 개선 반영의 자동화는 예정 단계입니다. 분석과 유료 eval은 우선 사용자가 직접 시작하도록 설계했습니다.

![업데이트한 지도의 실제 Self-improvement & eval 그룹입니다. 안내 문서는 제공되지만 그 안의 일부 실행 기능은 아직 예정 단계입니다.](screenshots/map-loop.png)

업데이트한 지도의 실제 Self-improvement & eval 그룹입니다. 안내 문서는 제공되지만 그 안의 일부 실행 기능은 아직 예정 단계입니다.

**확인할 결과:** 기록, 수정 제안, 평가와 배포의 담당 경계를 이해할 수 있습니다. 에이전트가 몰래 자기 지침을 바꾸는 것이 아니라 근거를 통해 개선하는 과정입니다.

## 11. 임시 계정에서 합성 관찰 기록 사용하기

scripts/improvement/observations.py가 포함된 후보 체크아웃과 Python 3.11 이상이 필요합니다. 함께 제공한 demo-observations.py에 --repo /path/to/checkout을 지정하세요. 스스로 임시 홈을 만들고 삭제하며 native 자동 수집은 켜지 않습니다.
직접 사용할 때 observations.py에는 --home을 명시합니다. grant는 --project, --profile, --source, --start-after에 범위를 묶습니다. 반환된 registration_id와 epoch를 capture에 지정하고 합성 JSON을 stdin으로 보냅니다. events로 허용된 메타데이터를 읽습니다.
안정적인 source ID는 재시도를 중복 제거합니다. ID가 없으면 중복 가능성을 남깁니다. response_end는 작업 성공이 아닙니다. 이 어댑터의 환경 manifest는 미확인입니다.

![합성 기록의 수집·재시도·조회·인덱스 생성 실제 결과입니다. 도구 실패만으로 skill 사용 여부나 작업 성공을 판단하지 않습니다.](screenshots/console-record.png)

합성 기록의 수집·재시도·조회·인덱스 생성 실제 결과입니다. 도구 실패만으로 skill 사용 여부나 작업 성공을 판단하지 않습니다.

**확인할 결과:** 동일 기록을 재시도해도 한 건만 남고, 제외된 출력 본문은 저장되지 않습니다. 동의를 반영한 조회는 events를 사용합니다. index.sqlite는 재생성할 수 있는 캐시입니다.

## 12. 기록의 범위·보관·삭제를 통제하기

개인 저장 위치는 <선택한 홈>/.agents/agent-dotfiles/observations/입니다. 정확한 프로젝트·프로필·source 등록에만 수집을 허용합니다. 계정 기록 전체를 재귀 탐색하지 않습니다. 프롬프트, 도구 인자, 출력과 transcript 본문은 제외합니다. 허용된 ID에도 비밀이나 사용자 본문을 넣지 않습니다.
revoke --registration ID로 등록 하나를 비활성화하고 삭제합니다. 프로젝트를 잊으려면 그 프로젝트의 등록을 모두 철회합니다. 과거 epoch는 계속 차단됩니다. 재등록에는 새 epoch와 source의 현재 high-water mark가 필요합니다.
grant는 최대 30일 안에 만료됩니다. 실제 파일 정리는 prune으로 실행하며 scheduler는 없습니다. 삭제가 중단돼도 조회는 차단되고 revoke/prune으로 마칠 수 있습니다. native 원본과 백업은 별도 관리 대상입니다.

![실제 revoke 후 과거 epoch의 수집이 비활성화되고, 동의를 반영한 조회 결과가 비어 있는 모습입니다.](screenshots/console-revoke.png)

실제 revoke 후 과거 epoch의 수집이 비활성화되고, 동의를 반영한 조회 결과가 비어 있는 모습입니다.

**확인할 결과:** 수집을 멈추고 소유한 근거를 지울 수 있습니다. 원격 분석이나 판정 전에 입력 범위, 대상, 목적과 예산을 별도로 승인합니다. 원본 기록이나 백업은 공개하지 않습니다.

## 13. 증상을 검토 가능한 재현 사례로 바꾸기

가상 예제입니다. 설치된 skill에서 측정한 결함이라는 뜻은 아닙니다. 테스트 명령이 시작되지 않았는데 에이전트가 검증에 통과했다고 보고했다고 가정합니다. 명령 실패만으로 허위 보고가 증명되지는 않습니다. 승인된 주장 근거가 없으면 근거 부족으로 남깁니다.
개인 경로나 인증 정보 없는 합성 재현을 만듭니다. 기대 결과는 검증이 막혔음을 알리고 원인을 설명하며 통과를 주장하지 않는 것입니다. 실제 통과 사례, 테스트 요청이 없는 유사 사례, 도구를 사용할 수 없는 사례도 추가합니다. 한국어와 영어 요청을 포함합니다.
개발 사례와 평가자 소유 holdout을 분리합니다. 수정 에이전트가 holdout 입력이나 숨겨진 정답을 보지 못하게 합니다.

![앞으로 사용할 eval 사례의 설명용 체크리스트입니다. 모델 실험의 결과표가 아닙니다.](screenshots/eval-cases.png)

앞으로 사용할 eval 사례의 설명용 체크리스트입니다. 모델 실험의 결과표가 아닙니다.

**확인할 결과:** 입력, 기대 결과, 중요한 절차 조건과 근거를 갖춘 사례가 생깁니다. 사용자 피드백은 분석의 출발점이지 skill 문제의 확정 진단은 아닙니다.

## 14. skill 수정 후보를 최소 변경으로 만들기

먼저 인프라, 빠진 도구, 모호한 지침, 잘못된 routing과 skill 자체의 문제를 구분합니다. 결정적인 결함은 설명을 늘리는 대신 스크립트나 검사로 해결하는 편이 맞을 수 있습니다.
가상의 허위 통과 보고에는 이런 후보를 생각할 수 있습니다. "실행 결과가 성공한 검사만 통과로 보고하고, 실패·차단·미실행을 구분한다." 기존 지침에 이미 같은 규칙이 있는지 먼저 확인하고 중복을 추가하지 않습니다.
실제로 skill을 수정할 때는 writing-for-agents와 호스트 skill-creator 지침을 사용합니다. 기준 버전, 최소 diff, 가설과 의존 범위를 기록합니다. 비교 중 후보가 채점기, fixture나 기대 정답을 바꾸면 안 됩니다.

![방법을 참고하기 위한 실제 TDD 안내 화면입니다. 위 수정 문구는 예제이며 저장소에 적용한 변경이 아닙니다.](screenshots/map-tdd.png)

방법을 참고하기 위한 실제 TDD 안내 화면입니다. 위 수정 문구는 예제이며 저장소에 적용한 변경이 아닙니다.

**확인할 결과:** 작고 검토 가능한 가설과 고정된 후보 버전이 준비됩니다. 불필요한 지침을 줄이는 것도 개선입니다. skill이 길어졌다고 좋아진 것은 아닙니다.

## 15. 실험 조건을 먼저 고정하고 비교하기

지도에서 4단계 improvement-eval을 엽니다. 비교 runner는 아직 구현되지 않았습니다. 함께 제공한 eval-plan.example.json은 실행 명령이 아닌 설계용 작성 예시입니다.
사례, 기존·후보 해시, runner와 채점기 버전, 실제 모델·provider·설정, 환경, 예산과 합격 규칙을 먼저 고정합니다. 각 실행에 새로운 격리 상태를 쓰고 비교 순서를 바꿉니다. worktree만 분리해도 계정 기록이나 숨겨진 정답 접근이 차단되는 것은 아닙니다.
경쟁하는 skill 목록에서 skill 이름을 강제로 지정하지 않고 자연스러운 routing을 검사합니다. 강제 호출 동작 검사는 따로 둡니다. 6-10개 사례를 각 버전에서 3회 반복하는 소규모 실험은 결함 탐색용이며 통계적 우월성을 증명하지 않습니다. 실패·차단·불확실한 실행도 모두 보존합니다.

![조건을 고정한 실험 계획의 설명용 도식입니다. 실제 모델 실행, 토큰 비용이나 점수를 나타내지 않습니다.](screenshots/eval-plan.png)

조건을 고정한 실험 계획의 설명용 도식입니다. 실제 모델 실행, 토큰 비용이나 점수를 나타내지 않습니다.

**확인할 결과:** 두 버전을 비교 가능한 조건에서 평가합니다. 후보, 채점기, fixture나 관련 환경이 바뀌면 해당 결과는 다시 검증해야 합니다. 근거가 불분명하면 기존 버전을 유지합니다.

## 16. 점수를 믿기 전에 채점기를 검증하기

실제 파일과 명령 결과를 검사하는 결정적 검증을 우선합니다. 작업 결과, 중요한 절차와 관찰된 skill 사용을 분리해서 평가합니다. 저장소 단위 테스트 통과가 skill의 행동 개선을 증명하지는 않습니다.
주관적 판단은 정답 예시, 미묘한 오답, 허위 성공, 근거 누락과 주입 사례로 블라인드 모델 판정기를 교정합니다. 판정기에게 숨겨진 정답 파일에 대한 도구나 파일시스템 접근을 주지 않습니다. 이런 사례를 구별하지 못하면 후보 승인에 쓸 수 없습니다.
MCP는 설정 유효성, 합성 도구 계약과 실제 서비스에서의 작업 성공을 구분합니다. 인프라 실패나 없는 근거를 통과로 바꾸지 않습니다. 반복 피드백은 holdout을 노출할 수 있으므로 제공 횟수를 제한하고 교체합니다.

![실제 code-review-and-quality 상세 화면입니다. 리뷰 참고 자료이며 내장 모델 eval 화면이 아닙니다.](screenshots/map-review.png)

실제 code-review-and-quality 상세 화면입니다. 리뷰 참고 자료이며 내장 모델 eval 화면이 아닙니다.

**확인할 결과:** 통과·실패·차단·불확실 판정의 이유를 설명할 수 있습니다. 평균 점수가 높아도 중요한 정책 위반을 상쇄할 수는 없습니다.

## 17. 검증한 버전을 반영하고 복구 가능하게 유지하기

실험 전에 목표 개선, 허용할 회귀와 비용을 정합니다. 목표 결과 개선, 관찰된 중요 위반 없음, 검증된 holdout 근거와 독립 리뷰를 요구합니다. 결과가 모호하면 기존 버전을 유지합니다.
정확한 소스 diff와 정제한 보고서를 리뷰합니다. 승인된 commit/merge 후 기존 installer로 그 커밋을 preview하고 적용합니다. 전달된 해시가 시험한 후보와 같은지 확인한 뒤 native 발견과 영향을 받는 동작을 점검합니다.
배포 후 회귀를 관찰하되 작업·모델·도구 차이 때문에 생긴 변화를 skill 탓으로 단정하지 않습니다. 조건을 고정한 비교로 재현합니다. 필요하면 guarded rollback을 사용하며 installer 복구 과정에서 관찰 근거를 삭제하지 않습니다.

![운영 절차를 설명하기 위해 실제 installer 복구 예제를 다시 사용했습니다. eval에서 개선 반영까지의 자동 연동은 예정 단계입니다.](screenshots/console-rollback.png)

운영 절차를 설명하기 위해 실제 installer 복구 예제를 다시 사용했습니다. eval에서 개선 반영까지의 자동 연동은 예정 단계입니다.

**확인할 결과:** 리뷰하고 검증한 소스 버전만 전달됩니다. 관찰, 모델 전송, 공개, merge와 계정 활성화는 각각 허용된 범위 안에서 수행합니다.

## 18. 문제를 진단하고 원본 안내로 돌아가기

skill이 안 보이면 설치 버전, native 목록, 중복 설치와 프로젝트 override를 확인합니다. hook이 조용하면 신뢰 설정, 선택한 계획과 클라이언트 지원 범위를 봅니다. MCP가 안 되면 실행 파일과 필요한 환경 변수를 값 노출 없이 확인합니다.
일반 세션에서 관찰 기록이 없는 것은 현재 정상입니다. CLI는 합성 입력만 받습니다. disabled는 동의 없음·만료·철회, rejected는 범위·스키마·ID 오류, busy는 나중에 재시도하라는 뜻입니다. 기록 손상 후 철회했다면 새 source generation이 필요할 수 있습니다.
최신 기준은 account/README.md, account/observation/README.md, docs/map/workflow.md, docs/decisions/account-improvement-loop.md입니다. 원본 묶음에는 두 언어의 편집용 텍스트, 스크린샷, 임시 실행 예제와 실행되지 않는 eval 작성 예시가 있습니다.

![실제 Anytime 검색 예제입니다. glossary로 domain-modeling을 열었습니다. 같은 방식으로 필요한 안내를 찾을 수 있습니다.](screenshots/map-anytime.png)

실제 Anytime 검색 예제입니다. glossary로 domain-modeling을 열었습니다. 같은 방식으로 필요한 안내를 찾을 수 있습니다.

**확인할 결과:** skill 문제라고 단정하지 않고 올바른 계층을 진단합니다. 사실과 검증 공백을 기록하고 공유할 자료를 정제한 다음 해당 원본 문서나 작업 단계로 돌아갑니다.
