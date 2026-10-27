"""Lightweight local text matching utilities (no external AI service required)."""
import math
import re

try:  # jieba is optional: fall back to character n-grams below
    import jieba

    jieba.setLogLevel(20)
except Exception:  # pragma: no cover
    jieba = None

STOPWORDS = {
    "研究", "应用", "技术", "方法", "基于", "分析", "系统", "设计", "实现", "问题", "方向",
    "相关", "进行", "通过", "以及", "一个", "我们", "可以", "主要", "具有", "发展",
    "the", "and", "for", "with", "of", "in", "on", "to", "a", "an",
}


def tokenize(text: str | None) -> list[str]:
    if not text:
        return []
    text = str(text).lower()
    if jieba is not None:
        raw = jieba.lcut(text)
    else:  # char bigrams + latin words
        raw = re.findall(r"[a-z0-9]+", text) + re.findall(r"[一-龥]{2,}", text)
        raw += [text[i:i + 2] for i in range(len(text) - 1)
                if "一" <= text[i] <= "龥" and "一" <= text[i + 1] <= "龥"]
    tokens = []
    for token in raw:
        token = token.strip()
        if len(token) < 2:
            continue
        if token in STOPWORDS:
            continue
        tokens.append(token)
    return tokens


def _tfidf_vectors(query: str, docs: list[str]):
    q_tokens = tokenize(query)
    doc_tokens = [tokenize(d) for d in docs]
    vocab = set(q_tokens)
    for tokens in doc_tokens:
        vocab.update(tokens)
    if not vocab:
        return None, None
    n_docs = len(docs) + 1

    def df(term):
        count = 1 if term in q_tokens else 0
        for tokens in doc_tokens:
            if term in tokens:
                count += 1
        return count

    idf = {term: math.log((n_docs + 1) / (df(term) + 1)) + 1 for term in vocab}

    def vector(tokens):
        counts = {}
        for t in tokens:
            counts[t] = counts.get(t, 0) + 1
        if not counts:
            return {}
        total = len(tokens)
        return {t: (c / total) * idf[t] for t, c in counts.items()}

    return vector(q_tokens), [vector(tokens) for tokens in doc_tokens]


def _cosine(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


def tfidf_similarities(query: str, docs: list[str]) -> list[float]:
    if not docs:
        return []
    q_vec, d_vecs = _tfidf_vectors(query, docs)
    if q_vec is None:
        return [0.0] * len(docs)
    return [round(_cosine(q_vec, v), 4) for v in d_vecs]


def keyword_match(user_text: str, candidate_text: str, extra_terms: list[str] | None = None):
    """Return (score 0-1, matched keyword list) based on explicit keyword coverage."""
    user_terms = []
    for part in re.split(r"[,，;；、/\s]+", user_text or ""):
        part = part.strip().lower()
        if part:
            user_terms.append(part)
    # also add meaningful tokens from longer phrases
    for token in tokenize(user_text):
        if token not in user_terms:
            user_terms.append(token)
    user_terms = list(dict.fromkeys(user_terms))
    if not user_terms:
        return 0.0, []

    haystack = (candidate_text or "").lower()
    for term in extra_terms or []:
        haystack += " " + str(term).lower()

    matched = []
    score = 0.0
    for term in user_terms:
        if term in haystack:
            matched.append(term)
            score += 1.0
        else:
            parts = tokenize(term)
            if parts and any(p in haystack for p in parts):
                matched.append(term)
                score += 0.5
    return round(min(1.0, score / len(user_terms)), 4), matched[:12]


def keyword_match_terms(terms: list[str], candidate_text: str) -> tuple[float, list[str]]:
    haystack = (candidate_text or "").lower()
    clean = [t.strip().lower() for t in terms if t and t.strip()]
    if not clean:
        return 0.0, []
    matched = [t for t in clean if t in haystack]
    return round(len(matched) / len(clean), 4), matched
