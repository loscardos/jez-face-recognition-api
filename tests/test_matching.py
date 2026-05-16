import numpy as np

from jez_face_api.cache import FaceTemplateCache
from jez_face_api.recognition.matching import MatchConfig, match_embedding


def test_match_embedding_accepts_clear_top_candidate():
    matrix = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.6, 0.8, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    user_ids = [101, 202, 303]
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    result = match_embedding(
        query,
        matrix,
        user_ids,
        MatchConfig(auto_match_threshold=0.45, ambiguous_threshold=0.38, min_margin=0.05),
    )

    assert result.status == "matched"
    assert result.user_id == 101
    assert result.best_score == 1.0
    assert result.second_score == 0.6
    assert result.margin == 0.4


def test_match_embedding_marks_small_margin_as_ambiguous():
    matrix = np.array(
        [
            [1.0, 0.0],
            [0.99, 0.01],
        ],
        dtype=np.float32,
    )
    user_ids = [101, 202]
    query = np.array([1.0, 0.0], dtype=np.float32)

    result = match_embedding(
        query,
        matrix,
        user_ids,
        MatchConfig(auto_match_threshold=0.45, ambiguous_threshold=0.38, min_margin=0.05),
    )

    assert result.status == "ambiguous"
    assert result.user_id is None
    assert result.best_candidate == 101
    assert result.second_candidate == 202


def test_match_embedding_ignores_same_user_samples_for_margin():
    matrix = np.array(
        [
            [1.0, 0.0],
            [0.99, 0.01],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )
    user_ids = [101, 101, 202]
    query = np.array([1.0, 0.0], dtype=np.float32)

    result = match_embedding(
        query,
        matrix,
        user_ids,
        MatchConfig(auto_match_threshold=0.45, ambiguous_threshold=0.38, min_margin=0.05),
    )

    assert result.status == "matched"
    assert result.user_id == 101
    assert result.best_candidate == 101
    assert result.second_candidate == 202
    assert result.best_score == 1.0
    assert result.second_score == 0.0
    assert result.margin == 1.0


def test_template_cache_builds_matrix_from_laravel_samples():
    cache = FaceTemplateCache()
    cache.reload_from_users_face_data(
        {
            101: {"samples": [[1.0, 0.0, 0.0], [0.9, 0.1, 0.0]]},
            202: {"samples": [[0.0, 1.0, 0.0]]},
        }
    )

    snapshot = cache.snapshot()

    assert snapshot.matrix.shape == (3, 3)
    assert snapshot.user_ids == [101, 101, 202]
