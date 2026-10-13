import operator
from typing import Annotated, Optional, TypedDict


class AgentState(TypedDict):
    # 입력
    doc_id: str                    # 어느 환자 문서인지 (처음부터 주어짐)
    question: str                  # 사용자 질문

    # load_document
    doc_text: str                  # 원문 전체. verify가 위치 대조할 때 필요

    # route_intent
    med_name: str                  # 질문에서 뽑은 약 이름
    section_plan: list[str]        # 찾을 섹션 순서. 예: ["Discharge Medications", "Discharge Instructions"]
    section_idx: int               # 지금 section_plan의 몇 번째를 보는 중인지

    # retrieve
    chunks: list                   # doc_id·섹션 필터(+ threshold, 켰을 때)를 통과한 조각들

    # extract
    candidate: Optional[dict]      # {"dose", "frequency", "evidence_text", "char_start", "char_end"}

    # verify_evidence
    verdict: str                   # ok / no_dose / multiple_doses / not_found / span_mismatch / name_mismatch / wrong_section

    # 재시도 제어
    attempts: int                  # extract→verify 재시도 횟수. 최대 2

    # compare_admission (다음 세션 구현 예정)
    admission: Optional[dict]      # 입원 목록의 같은 약 {"dose", "char_start", "char_end"}. 없으면 None

    # 최종
    result: Optional[dict]         # emit_result가 채움
    abstain_reason: Optional[str]  # abstain이 채움

    # 기록 (나중에 Art. 12 로깅으로 이어짐)
    trace: Annotated[list[str], operator.add]
    usage: Annotated[list[dict], operator.add]   # LLM 호출마다 1줄: 토큰 · 지연 · 모델
