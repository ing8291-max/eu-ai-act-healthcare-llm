# Testing & Monitoring Strategy

> AI(LLM)가 만든 코드와 LLM 에이전트의 동작을 **사람이 정한 기준으로** 계속 확인하기 위한 규칙.
> 원칙: 판정은 결정적인 코드가 한다. 사람은 시나리오와 기대값을 정한다. AI는 구현한다.

---

## 1. 7개 층: 무엇이 무엇을 잡나

| # | 층 | 잡는 것 | 언제 | 비용 | 명령 |
|---|---|---|---|---|---|
| 1 | **diff 읽기** | 요청하지 않은 변경 (기본값·삭제된 파일) | 커밋 전 매번 | 0 | `git diff --stat` → `git diff 파일` |
| 2 | **ruff · mypy** | 모양 실수: 안 쓰는 import, None 처리 누락 | 커밋마다 자동 (pre-commit) | 0 | `ruff check agents tests` · `mypy agents --ignore-missing-imports` |
| 3 | **unit test** | 노드 하나의 의미 실수: verify 판정, 위치 찾기, 파싱 | 커밋마다 자동 | 0 | `python -m pytest -q` |
| 4 | **e2e (가짜 LLM)** | 그래프 전체의 배선: 53문항이 끝까지 흐르는지, 나쁜 LLM에도 틀린 답 0인지 | 커밋마다 자동 | 0 | (3번에 포함: `tests/test_graph_fake.py`) |
| 5 | **e2e (실제 LLM)** | 실제 모델의 행동: 줄글, 함정, 출력 잘림 | 프롬프트·모델·LLM 코드가 바뀔 때 | 수십 원 | `python -m pytest -m llm -v` |
| 6 | **전체 평가 + 회귀 비교** | 53문항 숫자 변화: 새로 틀린 것, 새로 놓친 것, 토큰 | 기능 변경 후 · 태그 전 | 수백 원 | `evaluate(app, run_name=...)` → `python scripts/compare_runs.py --latest` |
| 7 | **실행 관찰 (Langfuse)** | 왜 틀렸는지: LLM이 본 조각과 답 원문 | 1단계부터 상시 | 무료 플랜 | 1단계 2주차 연결 |

**위로 갈수록 싸고 빠르고, 아래로 갈수록 비싸고 현실에 가깝다.** 아래 층에서 문제를 찾으면 위 층에 테스트를 하나 추가해서 다시는 같은 문제가 비싼 층까지 내려오지 않게 한다.

---

## 2. 이 프로젝트에서 실제로 잡힌 것 (층별 증거)

| 날짜 | 문제 | 잡은 층 | 이후 추가한 것 |
|---|---|---|---|
| 10/10 | `len(doses) > 2` 한 글자 변경이 테스트를 통과 (재현 실험) | 3 (coverage로 빈칸 발견) | `test_dose_count.py` |
| 10/11 | zip 풀 때 `test_verify.py` 삭제 | 1 (diff --stat) | 규칙: 터미널 `unzip`만 사용 |
| 10/11 | 평가가 틀린 인용을 "missed"로 셈 | 코드 리뷰 | `evaluate.py`가 wrong/missed 분리 |
| 10/11 | `.env` 값 옆 주석을 값으로 읽음 | 5 (실행 에러) | `.env.example` 주석 분리 |
| 10/11 | 기대값 착각 (doc_02 pantoprazole) | 정답 키 확인 | e2e 기대값은 정답 키에서만 |
| 10/11 | max_tokens=300에서 잘림 → "약 없음"으로 보고 | 6 (doc_08 trace) | `stop_reason` 기록 · TRUNCATED 표시 · unit test 1 · e2e 2 (doc_08) |

---

## 3. 테스트 파일 지도

| 파일 | 층 | 개수 | 내용 |
|---|---|---|---|
| `tests/test_verify.py` | 3 | 5 | 허용 섹션 · 위치 불일치 · 다른 약 줄 |
| `tests/test_dose_count.py` | 3 | 3 | 용량 없음 · 테이퍼 |
| `tests/test_extract.py` | 3 | 12 | 인용 → 원문 위치 · 줄바꿈 · 지어낸 인용 · 파싱 실패 · 잘림 · 재시도 피드백 · 토큰 기록 · A/D 맥락 |
| `tests/test_compare_runs.py` | 3 | 4 | 회귀 판정 규칙 |
| `tests/test_graph_fake.py` | 4 | 4 | 정직한/다른 약/지어내는 가짜 LLM × 53문항 |
| `tests/test_e2e_llm.py` | 5 | 7 | 실제 Claude: 목록 · 입원 함정 · 줄글 2 · 없는 약 · 테이퍼 · 용량 없음 |
| `tests/fakes.py` | — | — | `SectionStore` (Chroma 대체, 임베딩 불필요) |

`python -m pytest -q` 는 1~4층만 돈다 (LLM 테스트는 `pyproject.toml` 설정으로 자동 제외).

---

## 4. AI가 만든 코드를 받을 때 순서

1. **시나리오 (사람):** 무엇이 들어가면 무엇이 나와야 하나. 기대값은 정답 키에서 가져온다
2. **테스트 먼저:** 시나리오를 unit test로. LLM이 필요하면 가짜 LLM으로
3. **구현 (AI)**
4. **diff 읽기 (사람):** 요청한 것만 바뀌었나 · 숫자/기본값 · 설명 못 하는 줄
5. **`python -m pytest -q`** → 전부 통과
6. LLM 프롬프트·모델·LLM 코드가 바뀌었으면 **`pytest -m llm`**
7. 기능이 바뀌었으면 **전체 평가 → `compare_runs.py --latest`** → REGRESSION 0
8. 커밋 (pre-commit이 2~3층 자동 재확인) → push (CI가 한 번 더)
9. verification-log 한 줄

---

## 5. 회귀 규칙 (compare_runs.py 종료 코드 1)

- 어떤 문항이든 **wrong이 새로 생기면** 실패
- correct/abstain_ok였던 문항이 **다른 상태로 바뀌면** 실패
- 합계에서 correct 또는 abstain_ok가 줄면 실패
- 토큰·호출 수 변화는 보고만 한다 (판정은 사람이)

**변동성 주의:** 실제 LLM은 temperature를 못 써서 실행마다 다를 수 있다. 회귀가 1문항이면 **같은 설정으로 한 번 더** 돌려 재현되는지 먼저 확인한다. 재현되면 회귀, 안 되면 "변동"으로 기록.

---

## 6. 도입 일정

| 시점 | 넣는 것 | 층 |
|---|---|---|
| ✅ 10/11 | unit · 가짜 e2e · `stop_reason` | 3 · 4 |
| **10/12~13 (동결 전)** | `test_e2e_llm.py` · `compare_runs.py` · 이 문서 (동작 코드 변경 없음) | 5 · 6 |
| 10/18 주 (1단계 1주차) | pre-commit (ruff · gitleaks · pytest) · pytest-cov · GitHub Actions (1~4층) | 1~4 자동화 |
| 10/26 주 (2주차) | Langfuse 연결 · 평가 점수 → Langfuse score | 7 |
| 11/2 주 (3주차) | `scenarios.md` 30개 → 각 시나리오에 테스트 연결 | 3~5 |
| 11/9 주 (4주차) | CI에서 회귀 시 실패 (저장된 runs 비교) | 6 자동화 |

---

## 7. 규칙

1. 기대값은 **정답 키(fixtures)에서만** 가져온다. 기억으로 쓰지 않는다
2. 버그를 고치면 **그 버그를 재현하는 테스트를 먼저** 추가한다
3. `pytest -q`가 실패하면 커밋하지 않는다
4. 실제 LLM 테스트는 돈이 드니 **바뀐 게 있을 때만** 돌린다
5. 평가 결과(`runs/*.jsonl`)는 커밋한다. 숫자의 근거다
6. 결과를 보고 프롬프트를 고쳤다면 **"평가셋을 보고 고침"이라고 기록**하고 새 문서로 다시 확인한다
