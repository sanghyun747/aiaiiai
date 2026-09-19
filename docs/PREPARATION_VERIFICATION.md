# 준비 단계 검증 기록 — 2026-09-19

이 기록은 설계·계약·예제·병렬 작업 준비에 관한 것이다. 앱 구현, 실제 SNS 분석, 스폰서 통합, 배포가 완료됐다는 의미가 아니다.

## 실제 실행한 검사

명령: `python -X utf8 -B docs/verify_prep.py`
종료 코드: 0.

기본 검사 4개: 필수 준비 파일 존재, 스키마 내부 참조, 예제 Profile의 사용된 스키마 규칙, 예제 Run의 스키마·팔로워 분할·검증 범위·출처·시간 예산·Production Package·보고서 해시.

메모리에서만 오류를 주입한 반례 10개: 잘못된 상태값, 존재하지 않는 출처, 관계 부재 수 조작, 계정명 변경을 관계 부재로 승격, mock을 live로 변경, 제작 시간 예산 초과, GROWTH EXPERIMENT 누락, 성장 실험의 weakness_target 누락, Shot List 순서 오류, 보고서 해시 불일치. 모두 거부됨. 파일을 변조하거나 삭제하지 않았다.

이는 전체 JSON Schema/OpenAPI 표준 인증이 아닌, 이 계약에서 사용하는 규칙의 부분 검사다. 앱 동작 테스트·외부 제공자 호출 테스트·독립 코치 검증은 수행하지 않았다. 실제 구현은 별도 수용 테스트가 필요하다.

## 고정 기준

- API 계약 SHA-256: `f6a65e2872fc27c3ef901cbcbde84281657d27470ffcd4dfcaabfd553471b9bd`
- 합성 예제 보고서 SHA-256: `16704d030cb55ed548e009443876fb7eb850b51c9342878e291dc3421e59dc81`
- 읽은 원본 비교 스크립트 SHA-256: `7f58141df33ccfde3f6c2ccb31fdca89e5f3238553b8d4134c6251847a6dc268`
- 원본: `C:\Users\sangh\SKILL\instagram-follower-diff\scripts\instagram_follower_diff.py`
- 최초 설계서 복구 스냅샷: `4399394` (추가 준비 파일 생성 전 README 기준)
- 실행 세션의 공통 기준은 로컬 Git 태그 `contracts-v2`(계약 1.1.0)로 지정한다. 실제 생성/동일성 확인은 Git 결과로 판단한다.

## 외부 확인과 미검증

공식 행사 페이지에서 최대 6명, 14:00–16:00 해킹, 팀당 3분 데모, 스폰서 통합 요구, 네 가지 심사 기준을 확인했다. 세 스폰서 전체 미사용 시 실격인지와 사전 작성 코드 허용 범위는 별도 주최 확인이 필요하다.

Nosana의 호환 추론 API 및 현재 모델 조회, Daytona 파일/코드 실행, DNSimple 테스트 DNS의 비공개 해석 특성, YouTube 검색·통계 API는 공식 문서를 확인했다. 계정 권한/크레딧/실호출/실제 레코드/공개 DNS/TLS는 확인하지 않았다.

현재 연결 프로세스 환경에는 DAYTONA_API_KEY, NOSANA_API_KEY, DNSIMPLE_TOKEN, YOUTUBE_API_KEY가 없었다. 다른 저장 위치나 사용자의 계정 존재 여부는 조사하지 않았다. 키는 채팅이 아닌 실행기용 로컬 환경파일에 직접 설정해야 한다.

원본 스킬·원본 ZIP·기존 보고서는 이 작업에서 수정/추출/삭제하지 않았다. 실데이터 외부 전송, 도메인 구매, 운영 DNS 변경, 추가 DevSpace 서버/앱/실행기 프로세스 시작을 하지 않았다. GitHub 원격 저장소 생성/최초 push는 사용자 요청에 따라 Session A 지시서에 승인 범위를 명시했으나 이 준비 세션에서는 아직 실행하지 않았다.

## Production Agent revision

- Contract 1.1.0 adds strategy_mode (`safe_bet` / `growth_experiment`), weakness_target and a required ProductionPackage to every action.
- ProductionPackage contains Script, ordered Shot List, Editing Guide, Thumbnail Plan and Publishing Package.
- Daytona runtime contract now allows verified generated production artifacts in addition to report.md.
- Physical shooting remains the user's task. An editing guide is not represented as proof that a finished video was automatically rendered.
- Pre-edit restore snapshot: `c373986`.
