"""
Leaderboard rank score on a 0–100 scale from session position.
"""


def leaderboard_rank_score_100(position: int, session_total: int) -> float:
    """
    ``position``: 1-based index in session (1 = highest composite score).
    ``session_total``: N candidates in that run.

    Returns a score in [0, 100]: best place → 100, worst → 100/N.

    Examples: N=3 → pos 1 → 100.0, pos 2 → 66.6667, pos 3 → 33.3333.
    """
    n = int(session_total)
    pos = int(position)
    if n <= 0:
        return 0.0
    pos = max(1, min(pos, n))
    return round(100.0 * (n - pos + 1) / n, 4)
