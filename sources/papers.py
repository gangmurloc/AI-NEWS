"""arXiv + OpenAlex + Semantic Scholar를 합쳐서 논문 후보군을 만듦."""
import re
import config
import history
from sources.arxiv_papers import fetch_arxiv_papers
from sources.openalex import fetch_papers as fetch_openalex_papers
from sources.semantic_scholar import fetch_papers as fetch_semantic_scholar_papers

# 한자/한글/키릴 문자가 섞인 제목은 영어가 아닌 것으로 간주하고 제외
# (OpenAlex는 language:en 필터가 있지만, Semantic Scholar/arXiv는 이런 필터가 없어서 안전망으로 둠)
_NON_ENGLISH_SCRIPT = re.compile(r"[一-鿿぀-ヿ가-힣Ѐ-ӿ]")


def _is_english(title: str) -> bool:
    return not _NON_ENGLISH_SCRIPT.search(title)


def fetch_all_papers() -> list:
    papers = fetch_arxiv_papers()

    for topic in config.TOPICS:
        papers += fetch_openalex_papers(topic["hn_query"])
        papers += fetch_semantic_scholar_papers(topic["hn_query"])

    # 같은 논문이 여러 소스에서 잡힐 수 있어 제목 기준으로 중복 제거 (먼저 나온 것 우선)
    seen_titles = set()
    deduped = []
    for p in papers:
        key = p["title"].strip().lower()
        if not key or key in seen_titles or not _is_english(p["title"]):
            continue
        seen_titles.add(key)
        deduped.append(p)

    deduped = history.filter_unsent(deduped)
    return deduped[: config.PAPER_MAX_TOTAL]
