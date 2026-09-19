# TrendPilot — 해커톤 설계·실행 준비 패키지

작성일: 2026-09-19 KST. 가칭이며 상표·도메인 사용 가능성은 검증하지 않았다.
현재 상태: 설계/공통 계약/작업 분할 준비. 앱 구현, 스폰서 실호출, 배포 완료를 뜻하지 않는다.

## 제품 정의

**트렌드를 나열하는 챗봇이 아니라, 공개 콘텐츠 근거와 내 계정의 변화를 바탕으로 다음 콘텐츠 실험 3개를 설계하고, 실제 촬영만 제외한 제작 준비물을 완성하는 Personal SNS Growth Production Agent.**

장기 방향은 트렌드 관측 → 콘텐츠 기획 → 촬영 → 편집/게시 → 성과 기록 → 다음 실험이다. 이번 MVP는 관측·팔로워 비교와 함께 대본, 촬영 리스트, 편집 지시, 썸네일 기획, 제목/설명/해시태그/CTA까지 자동 생성한다. 실제 카메라 촬영은 사용자가 한다. 원본 영상 자동 편집·자동 게시·성과 자동 수집이 실제로 구현되지 않았다면 구현됐다고 발표하지 않는다.

첫 사용자는 숏폼을 직접 만드는 소규모 1인 크리에이터로 가정한다. 전체 현대인·모든 SNS를 동시에 대상으로 삼지 않는다. 데모 주제는 학습/생산성 콘텐츠이며 실제 유행이라는 근거 없는 주장을 하지 않는다.

## 해커톤 관점 평가

| 항목 | 현재 아이디어의 위험 | 이번 설계의 보정 |
|---|---|---|
| 완성도 | 전 SNS 수집, 예측, 수익화, 팔로워 분석을 한 번에 만들면 연동이 미완성될 위험 | 한 가지 관측 소스, Instagram ZIP 비교, 콘텐츠 실험 3개, 보고서 1개 |
| 혁신성 | 'AI 트렌드 추천 + 언팔 목록'만 붙이면 기능 모음으로 보임 | 출처·관측 시점·미확인 상태를 보여주고 거짓 이탈을 제거하는 신뢰 계층 |
| 실제 문제 해결 | 무엇을 만들지보다 넓은 '유행의 최전선' 목표 | '무엇을 찍을지'에서 끝내지 않고 대본·장면·편집·썸네일·게시 준비까지 한 번에 해결 |
| 스폰서 활용 | 로고나 설명만 붙이면 실제 기능 통합이 아님 | Nosana 추론, Daytona 실제 분석·파일 생성, DNSimple 레코드 API 실행 증거 |
| 수익화 | 조회수와 팔로워가 바로 매출이라는 비약 | 제휴/자체 자료/문의 유도 중 한 전환 가설과 측정 지표만 제시 |

상금·수상 가능성·매출·팔로워 증가를 보장하지 않는다. 심사 기준 가중치와 합격/실격 해석은 주최 측만 확정할 수 있다.

## 행사 조건

공식 행사 페이지: https://luma.com/daytonaseoul
확인된 내용: 최대 6명, 14:00 시작–16:00 종료, 팀당 라이브 데모 3분. 심사 기준은 완성도·혁신성·실제 문제 해결·스폰서 제품 활용이다. 스폰서 제품 통합 의무와 Daytona/DNSimple/Nosana가 확인된다.

'세 제품 모두 미사용이면 실격'이라는 세부 해석은 확인되지 않았다. 본 설계는 세 제품의 실제 API 경로를 준비한다. 하나라도 미연동이면 그 상태를 명시하고, 주최 확인 없이 요건을 충족했다고 단정하지 않는다.

기존 코드/템플릿 재사용 및 사전 준비물 허용 범위는 별도 확인이 필요하다. 기존 follower-diff는 재사용 출처를 명시한다. 이 준비 패키지 작성과 행사 중 신규 구현을 구분한다.

## P0: 반드시 실제로 연결할 사용자 흐름

1. 주제·대상·목표(조회수/팔로워/문의)·제작 가능 시간 입력. 합성 예제 또는 본인 ZIP 두 개 선택.
2. 공개 콘텐츠 관측 근거를 불러오고, 두 ZIP의 팔로워 차이를 보수적으로 계산한다.
3. 계정명 변경/날짜창/검증 미완료를 분리한다. '직접 언팔'이나 '해당 게시물 때문에 이탈'은 단정하지 않는다.
4. Nosana가 제공된 근거에 연결된 콘텐츠 실험 3개를 생성한다. 최소 하나의 SAFE BET과 하나의 GROWTH EXPERIMENT를 포함한다.
5. 각 실험에 완전한 Production Package를 만든다: Script, Shot List, Editing Guide, Thumbnail Plan, Publishing Package(제목·설명·해시태그·CTA·측정 지표).
6. Daytona가 고정된 안전한 코드로 분석을 실행하고 검증된 Production Package를 `report.md`, `content-strategy.json`, `script.md`, `shot-list.json`, `editing-guide.md`, `thumbnail-plan.md`, `publishing-package.md`로 실제 생성한다.
7. 결과 화면에서 출처, 한계, 스폰서 실행 증거와 제작 패키지를 확인하고 실제 생성된 파일을 내려받는다.
8. DNSimple의 별도 게시 동작으로 레코드를 생성/확인한다. sandbox 성공은 공개 URL 성공과 다르게 표시한다.

UI는 한 대시보드 안에서 관측 근거 / 팔로워 변화 / SAFE BET·GROWTH EXPERIMENT / Production Package를 이어서 보여준다. 별도 로그인·결제·관리자 화면은 만들지 않는다. 실제 촬영은 서비스 밖에서 사용자가 수행한다.

## 데이터 경계

- 라이브 트렌드 소스: YouTube Data API의 최근 검색 결과와 영상 통계. Instagram 성장 조언에 쓰더라도 'YouTube 기반 참고 신호'로 명시한다. YouTube 결과를 Instagram에서 유행 중이라고 바꾸지 않는다.
- 메타데이터만 가져왔으면 영상 내용을 봤거나 음원·편집 방식을 분석했다고 말하지 않는다.
- 관측이 한 번뿐이면 총 조회수/게시 후 경과 시간을 '초기 반응 참고치'로 표시한다. 상승 속도는 최소 두 관측, 가속은 최소 세 관측과 실제 계산이 필요하다.
- 라이브 소스 장애는 조용히 합성 데이터로 대체하지 않는다. 명시적 예제 모드 또는 수집 시각이 있는 캐시로 전환하고 화면에 표시한다.
- 팔로워 ZIP만으로 게시물별 조회수·저장·공유·수익·이탈 이유·활동 인구통계를 알 수 없다. 없으면 null/미확인이다.
- 기존 스킬의 최종 후보는 별도 username-change audit 전에는 잠정 후보다. 현재 스크립트가 이 검증을 자동화하지 않는다는 점을 어댑터에서 보완한다.
- 실제 계정명과 관계 목록은 Nosana 프롬프트 및 공개 보고서로 보내지 않는다. 데모는 합성 데이터가 기본이다.

## 수익화 방향

사용자 관점: 조회수·팔로워·문의 중 하나를 목표로 선택하고, 콘텐츠의 CTA와 측정 계획을 받는다. 제휴 링크·디지털 자료·브랜드 문의는 실험 가설이지 수익 보장이 아니다. 팔로워 숫자만으로 특정 플랫폼 수익화 자격을 판정하지 않는다.

서비스 관점: 크리에이터별 반복 분석과 실행 자료 생성에 대한 구독을 가설로 둔다. 이번에는 결제를 구현하지 않고 데모 후 제작 시간 절약, 실제 채택한 실험 수, 재사용 의향을 확인한다. 가격 및 지불의사는 아직 검증되지 않았다.

## 구조

Frontend → FastAPI 오케스트레이터
→ Nosana: 비식별 프로필로 제한된 분석 계획 작성
→ Daytona: 고정 Python 코드로 follower-diff/근거 지표 계산
→ Nosana: 비식별 집계 + 출처 목록으로 SAFE BET/GROWTH EXPERIMENT와 Production Package JSON 작성
→ Daytona: 고정 템플릿으로 대본·촬영 리스트·편집 가이드·썸네일 계획·게시 패키지·Markdown 산출물 생성
→ API: 스키마/근거/수치/안전 검증 후 결과 반환
→ DNSimple: 명시적 게시 요청 시 레코드 처리(별도 경로)

Nosana가 Daytona를 직접 무제한 제어하지 않는다. API가 허용된 작업과 파라미터만 실행한다. DNS는 URL의 경로를 호스팅하거나 TLS를 자동 해결하지 않는다.

## 두 실행 세션

- 세션 A: `frontend/**`만 소유. React/TypeScript/Vite UI, HTTP 클라이언트, 명시적 mock, Production Package UX, 화면 테스트, 로컬 실행 문서. 또한 별도 승인된 예외로 GitHub 원격 저장소 생성/최초 push의 단독 담당자다.
- 세션 B: `backend/**`만 소유. FastAPI, 데이터 검증, 원본 스킬 복사본, provider 어댑터, 안전한 분석, 작업 상태, 보고서, API 테스트.
- 설계·검수 세션: 루트, `contracts/**`, `fixtures/**`, `docs/**`, `handoff/**`만 소유하고 최종 병합한다.
- 공통 기준: `contracts/v1.openapi.json`, `contracts/HTTP.md`, `fixtures/run-sample.json`.
- 같은 브랜치/작업 폴더를 두 세션이 공유하지 않는다. 두 worktree는 동일한 계약 커밋에서 시작한다.

읽을 실행 지시서는 `handoff/SESSION_A.md`, `handoff/SESSION_B.md`이다. 병합/검수는 `handoff/INTEGRATION.md`를 따른다.

## 120분 개발 운영안

이는 실행기의 작업 배분안이며 완료 시간 보장이 아니다. 실제 남은 시간이 더 적으면 P1부터 제외한다.

| 구간 | A | B | 합류 조건 |
|---|---|---|---|
| 0–15분 | 고정 fixture로 화면·타입 | 키/모델/Daytona/DNSimple preflight와 API 뼈대 | 계약·포트 확정 |
| 15–50분 | 입력·진행·결과·실패 화면 | ZIP 어댑터·Daytona 분석·Nosana 추론 | 첫 수직 기능 연결 |
| 50–80분 | 실제 API 연결·보고서 다운로드 | 근거 검증·안전·DNSimple sandbox API | mock 아닌 연결 확인 |
| 80–100분 | 화면/모바일/실패 처리 | 테스트·로그·결함 수정 | 설계자가 깨끗한 통합 worktree에서 검수 |
| 100–120분 | 3분 시연 반복 | 데모 안정화·키/크레딧/상태 확인 | 기능 추가 중단 |

P1: 공개 커스텀 도메인, 커스텀 분석 메트릭, 콘텐츠 성과 CSV, 그래프 고급화, 다중 소스. 모두 P0가 실제로 돌아간 뒤에만 한다.

## 3분 시연

0:00–0:20: '유행을 알려주는 답변보다, 내 계정에서 다음에 무엇을 시도할지와 그 근거가 필요합니다.'
0:20–0:45: 주제/목표와 합성 데이터 선택. 예제 데이터임을 명시한다.
0:45–1:15: Daytona 분석 결과: 단순 누락 4개가 관계 부재 1개·계정명 변경 1개·기간 제외 1개·미확인 1개로 나뉨.
1:15–2:10: SAFE BET/GROWTH EXPERIMENT를 열고 실제 대본, 장면별 촬영 리스트, 편집 지시, 썸네일 문구, 게시 문구까지 확인한다. 촬영만 사용자의 몫임을 보여준다.
2:10–2:35: Nosana/Daytona 실행 기록과 실제 생성 파일 다운로드를 보여준다.
2:35–2:50: DNSimple sandbox 레코드 또는 검증된 공개 URL을 구분해서 보여준다.
2:30–3:00: 사용자 가치와 향후 실험→성과→다음 추천 연결. 이번 구현과 향후 기능을 구분한다.

## 공식 기술 근거 (2026-09-19 확인)

- 행사: https://luma.com/daytonaseoul
- Nosana 추론: https://learn.nosana.com/api/llm.html — OpenAI 호환 API, 가용 모델 조회, 토큰 기반 크레딧 사용.
- Daytona 시작: https://www.daytona.io/docs/ — Python SDK 및 sandbox code execution.
- Daytona 파일: https://www.daytona.io/docs/en/file-system-operations/
- Daytona 실행: https://www.daytona.io/docs/en/process-code-execution/
- DNSimple 레코드: https://developer.dnsimple.com/v2/zones/records/
- DNSimple sandbox: https://developer.dnsimple.com/sandbox/ — 테스트 레코드는 공용 DNS로 해석되지 않음.
- YouTube 검색: https://developers.google.com/youtube/v3/docs/search/list
- YouTube 통계: https://developers.google.com/youtube/v3/docs/videos/list

원본 스킬: `C:\Users\sangh\SKILL\instagram-follower-diff`. 원본 파일/보고서/ZIP은 수정·삭제하지 않는다.
