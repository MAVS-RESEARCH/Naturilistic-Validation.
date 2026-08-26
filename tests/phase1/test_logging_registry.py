from __future__ import annotations

from pathlib import Path

from scripts.phase1_validate import audit_console_log_adjacency

ROOT = Path(__file__).resolve().parents[2]


def test_every_phase1_console_log_has_an_adjacent_matching_comment() -> None:
    registry = audit_console_log_adjacency(ROOT)
    assert registry["statement_count"] >= 20
    assert registry["all_comments_adjacent"] is True
    assert registry["all_comment_ids_match_statements"] is True
    assert all(record["comment_line"] + 1 == record["log_line"] for record in registry["records"])
