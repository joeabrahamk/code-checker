import math
from typing import Dict, List, Tuple


def _lazy_import():
    try:
        import torch  # type: ignore
        from transformers import AutoModel, AutoTokenizer  # type: ignore
        return torch, AutoModel, AutoTokenizer, None
    except Exception as exc:
        return None, None, None, exc


_MODEL_NAME = "microsoft/graphcodebert-base"
_TOKENIZER = None
_MODEL = None


def _load_model():
    global _TOKENIZER, _MODEL
    torch, AutoModel, AutoTokenizer, error = _lazy_import()
    if error:
        raise RuntimeError(
            "GraphCodeBERT requires 'transformers' and 'torch'. "
            "Install them to enable graphcodebert scoring."
        )

    if _TOKENIZER is None or _MODEL is None:
        _TOKENIZER = AutoTokenizer.from_pretrained(_MODEL_NAME)
        _MODEL = AutoModel.from_pretrained(_MODEL_NAME)
        _MODEL.eval()

    return torch, _TOKENIZER, _MODEL


def _mean_pooling(last_hidden_state, attention_mask):
    torch, _, _ = _load_model()
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    masked = last_hidden_state * mask
    summed = masked.sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)
    return summed / counts


def _embed_texts(texts: List[str]):
    torch, tokenizer, model = _load_model()
    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    )
    with torch.no_grad():
        outputs = model(**inputs)
    return _mean_pooling(outputs.last_hidden_state, inputs["attention_mask"])


def _independent_stack_score(similarities: List[float]) -> float:
    """Compute an independent 0-100 stack score from similarity distribution."""
    if not similarities:
        return 0.0

    positives = [max(0.0, s) for s in similarities]
    if not positives:
        return 0.0

    max_sim = max(positives)
    top_k = sorted(positives, reverse=True)[: min(3, len(positives))]
    mean_top_k = sum(top_k) / len(top_k)
    coverage = sum(1 for s in positives if s >= 0.25) / len(positives)

    # Weighted blend scaled to 0-100.
    score_0_1 = (0.55 * max_sim) + (0.35 * mean_top_k) + (0.10 * coverage)
    return round(max(0.0, min(100.0, score_0_1 * 100)), 1)


def _score_band(score: float) -> str:
    if score >= 75:
        return "strong"
    if score >= 50:
        return "moderate"
    if score >= 30:
        return "weak"
    return "none"


def score_stacks_with_graphcodebert(
    code_samples: List[Dict[str, str]],
    stack_queries: Dict[str, str]
) -> Tuple[Dict[str, Dict[str, object]], str]:
    if not code_samples:
        return {}, "No code samples provided"
    if not stack_queries:
        return {}, "No stack queries provided"

    code_texts = [c["content"] for c in code_samples]
    query_labels = list(stack_queries.keys())
    query_texts = [stack_queries[k] for k in query_labels]

    try:
        torch, _, _ = _load_model()
        code_embeddings = _embed_texts(code_texts)
        query_embeddings = _embed_texts(query_texts)

        code_norm = torch.nn.functional.normalize(code_embeddings, p=2, dim=1)
        query_norm = torch.nn.functional.normalize(query_embeddings, p=2, dim=1)

        sims = torch.mm(code_norm, query_norm.T)
        results = {}

        for idx, label in enumerate(query_labels):
            column = sims[:, idx]
            best_idx = int(torch.argmax(column).item())
            best_score = float(column[best_idx].item())
            similarities = [float(v.item()) for v in column]
            independent_score = _independent_stack_score(similarities)

            top_matches = sorted(
                [
                    (float(column[i].item()), code_samples[i]["path"])
                    for i in range(len(code_samples))
                ],
                key=lambda x: x[0],
                reverse=True
            )[:3]

            results[label] = {
                "similarity": round(best_score, 4),
                "best_file": code_samples[best_idx]["path"],
                "independent_score": independent_score,
                "evidence_strength": _score_band(independent_score),
                "matched_files": [m[1] for m in top_matches],
                "matched_similarities": [round(m[0], 4) for m in top_matches]
            }

        return results, None

    except Exception as exc:
        return {}, f"GraphCodeBERT scoring failed: {exc}"
