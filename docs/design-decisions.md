# Design Decisions

| Date | Article | Decision | Session |
|---|---|---|---|
| 2026-09-20 | Art. 10(2)(c) | 섹션 우선 분할. 일반 분할(size≥300)은 정답 청크의 90%에 입원 목록이 섞임 | S02 |
| 2026-09-20 | Art. 10(2)(c) | size=800. 최장 섹션(715자)이 통째로 들어감. 검색 기준 최적화는 S07에서 MRR로 재검토 | S02 |
| 2026-09-20 | Art. 10(2)(h) | BM25 토크나이저를 소문자·구두점 제거로 교체. 기본값은 약 이름을 못 찾음 | S02 |

| 2026-09-22 | Art. 10(2)(c) | 문서 21건·정답 46개로 확장. 섹션 우선 분할은 문서가 2배가 되어도 300/500/800 전부 intact·labeled·clean 100% 유지 | S02 |
| 2026-09-22 | Art. 15 (미독) | 검색에 doc_id 필터 필수. 미적용 hit@1 65%, 적용 91% (n=46). 같은 약이 여러 환자 문서에 존재 | S02 |
| 2026-09-22 | Art. 15 (미독) | 남은 실패 4건 전부 섹션 선택 문제. Discharge Medications 우선, 포인터면 Discharge Instructions로 폴백, Medications on Admission은 근거 금지 → S03 retrieve 노드 규칙 | S02 |