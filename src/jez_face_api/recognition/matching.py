from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class MatchConfig:
    auto_match_threshold: float
    ambiguous_threshold: float
    min_margin: float


@dataclass(frozen=True)
class MatchResult:
    status: str
    user_id: int | None
    best_candidate: int | None
    second_candidate: int | None
    best_score: float
    second_score: float
    margin: float


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector.astype(np.float32)
    return (vector / norm).astype(np.float32)


def _normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    matrix = matrix.astype(np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return (matrix / norms).astype(np.float32)


def match_embedding(
    query_embedding: np.ndarray,
    template_matrix: np.ndarray,
    user_ids: Sequence[int],
    config: MatchConfig,
) -> MatchResult:
    if template_matrix.size == 0 or len(user_ids) == 0:
        return MatchResult("not_found", None, None, None, 0.0, 0.0, 0.0)

    if template_matrix.shape[0] != len(user_ids):
        raise ValueError("template_matrix rows must match user_ids length")

    query = _normalize(query_embedding)
    matrix = _normalize_matrix(template_matrix)
    scores = matrix @ query
    best_score_by_user: dict[int, float] = {}
    for score, user_id in zip(scores, user_ids):
        candidate_id = int(user_id)
        candidate_score = float(score)
        if candidate_score > best_score_by_user.get(candidate_id, float("-inf")):
            best_score_by_user[candidate_id] = candidate_score

    ranked_users = sorted(best_score_by_user.items(), key=lambda item: item[1], reverse=True)
    best_candidate, best_score = ranked_users[0]
    if len(ranked_users) > 1:
        second_candidate, second_score = ranked_users[1]
    else:
        second_candidate, second_score = None, 0.0
    margin = best_score - second_score

    if best_score >= config.auto_match_threshold and margin >= config.min_margin:
        status = "matched"
        user_id = best_candidate
    elif best_score >= config.ambiguous_threshold:
        status = "ambiguous"
        user_id = None
    else:
        status = "not_found"
        user_id = None

    return MatchResult(
        status=status,
        user_id=user_id,
        best_candidate=best_candidate,
        second_candidate=second_candidate,
        best_score=round(best_score, 6),
        second_score=round(second_score, 6),
        margin=round(margin, 6),
    )
