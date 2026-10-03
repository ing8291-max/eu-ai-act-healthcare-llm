import re
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 섹션 제목 찾기: 줄 전체가 "제목:" 형태인 줄
# 예) "Discharge Medications:"  "Brief Hospital Course:"
HEADER_RE = re.compile(r"^([A-Z][A-Za-z /]+):\s*$", re.M)


def split_by_section(doc_text: str, doc_id: str,
                     size: int = 500, overlap: int = 50) -> list[Document]:
    """문서를 섹션 제목 위치에서 먼저 자르고, 긴 섹션만 글자 수로 한 번 더 자른다.

    반환되는 각 청크의 metadata:
      doc_id      어느 문서인지
      section     어느 섹션인지 (예: "Discharge Medications")
      char_start  원문 전체 기준 시작 위치
      char_end    원문 전체 기준 끝 위치
    """
    # 1) 섹션 제목 위치 찾기. 첫 제목 앞부분(이름·날짜 등)은 "Header"로 묶는다
    marks = [(0, "Header")] + [(m.start(), m.group(1))
                                 for m in HEADER_RE.finditer(doc_text)]

    inner = RecursiveCharacterTextSplitter(
        chunk_size=size, chunk_overlap=overlap, add_start_index=True
    )

    chunks = []
    for i, (start, name) in enumerate(marks):
        # 2) 이번 섹션의 끝 = 다음 섹션의 시작
        end = marks[i + 1][0] if i + 1 < len(marks) else len(doc_text)
        body = doc_text[start:end].rstrip()
        if not body.strip():
            continue

        # 3) 섹션이 size보다 길 때만 여러 조각으로 나뉜다
        for piece in inner.create_documents([body]):
            s = start + piece.metadata["start_index"]   # 섹션 기준 → 원문 기준
            e = s + len(piece.page_content)
            text = piece.page_content

            # 4) 긴 섹션이 나뉘어 제목이 떨어진 조각에는 제목을 다시 붙인다
            #    (char_start/char_end는 원문 위치를 그대로 가리킴)
            if name != "Header" and not text.startswith(name + ":"):
                text = f"{name}:\n{text}"

            chunks.append(Document(
                page_content=text,
                metadata={"doc_id": doc_id, "section": name,
                          "char_start": s, "char_end": e},
            ))
    return chunks


if __name__ == "__main__":
    import pathlib

    # 합성 문서 10건 전부 분할
    all_chunks = []
    for path in sorted(pathlib.Path("data/synthetic").glob("doc_*.txt")):
        all_chunks += split_by_section(path.read_text(encoding="utf-8"), path.stem)
    print(f"청크 {len(all_chunks)}개")

    # 확인: 03번 문서의 퇴원 약 청크
    for c in all_chunks:
        if c.metadata["doc_id"] == "doc_03" and c.metadata["section"] == "Discharge Medications":
            print(c.metadata)
            print(c.page_content)

            # 원문 위치로 잘라낸 글자가 청크와 같은지 검사
            doc = pathlib.Path("data/synthetic/doc_03.txt").read_text(encoding="utf-8")
            s, e = c.metadata["char_start"], c.metadata["char_end"]
            print("원문 위치 일치:", doc[s:e] == c.page_content)
