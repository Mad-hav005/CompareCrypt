"""
Tests for the Entity Resolution subsystem.

Covers:
- Dataset parsing (CSV)
- Blocking candidate generation
- Multi-attribute matching (fuzzy + exact)
- Weighted scoring
- API endpoints (upload, start, status, results, export)
"""

from __future__ import annotations

import csv
import io
import time
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.entity_resolution.dataset_parser import parse_csv_bytes, parse_file_bytes
from app.entity_resolution.blocking import generate_candidate_pairs, BLOCKING_THRESHOLD
from app.entity_resolution.multi_attribute_matcher import MultiAttributeMatcher
from app.entity_resolution.weighted_scorer import build_match_result, compute_overall_score
from app.models.er_schemas import (
    AttributeMapping,
    AttributeScore,
    MatchStrategy,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_csv(rows: List[Dict[str, str]], columns: List[str]) -> bytes:
    """Serialize rows to CSV bytes."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


DATASET_A_COLUMNS = ["Name", "Email", "City"]
DATASET_B_COLUMNS = ["Full Name", "Email ID", "Location"]

ROWS_A = [
    {"Name": "Alice Johnson", "Email": "alice@example.com", "City": "New York"},
    {"Name": "Bob Smith", "Email": "bob@example.com", "City": "Chicago"},
    {"Name": "Charlie Brown", "Email": "charlie@example.com", "City": "Houston"},
]

ROWS_B = [
    {"Full Name": "Alice Johnsun", "Email ID": "alice@example.com", "Location": "New York"},
    {"Full Name": "Robert Smith", "Email ID": "bob@example.com", "Location": "Chicago"},
    {"Full Name": "David Lee", "Email ID": "david@example.com", "Location": "Phoenix"},
]

CSV_A = _make_csv(ROWS_A, DATASET_A_COLUMNS)
CSV_B = _make_csv(ROWS_B, DATASET_B_COLUMNS)


# ---------------------------------------------------------------------------
# Dataset parser tests
# ---------------------------------------------------------------------------

class TestDatasetParser:
    def test_parse_csv_basic(self):
        rows, schema = parse_csv_bytes(CSV_A, "test_a.csv", "A")
        assert len(rows) == 3
        assert schema.row_count == 3
        assert len(schema.columns) == 3
        assert schema.columns[0].name == "Name"
        assert "Alice Johnson" in schema.columns[0].sample_values
        assert schema.party == "A"
        assert schema.filename == "test_a.csv"

    def test_parse_csv_column_samples(self):
        rows, schema = parse_csv_bytes(CSV_B, "test_b.csv", "B")
        col_names = [c.name for c in schema.columns]
        assert "Full Name" in col_names
        assert "Email ID" in col_names
        assert "Location" in col_names

    def test_parse_csv_preview_rows(self):
        rows, schema = parse_csv_bytes(CSV_A, "test_a.csv", "A")
        assert len(schema.preview_rows) <= 10
        assert schema.preview_rows[0]["Name"] == "Alice Johnson"

    def test_parse_empty_csv(self):
        empty_csv = b"Name,Email\n"
        rows, schema = parse_csv_bytes(empty_csv, "empty.csv", "A")
        assert len(rows) == 0
        assert schema.row_count == 0

    def test_parse_file_dispatch_csv(self):
        rows, schema = parse_file_bytes(CSV_A, "data.csv", "A")
        assert len(rows) == 3

    def test_parse_csv_non_empty_count(self):
        csv_with_blanks = b"Name,Email\nAlice,\nBob,bob@example.com\n,\n"
        rows, schema = parse_csv_bytes(csv_with_blanks, "blanks.csv", "A")
        name_col = next(c for c in schema.columns if c.name == "Name")
        email_col = next(c for c in schema.columns if c.name == "Email")
        assert name_col.non_empty_count == 2
        assert email_col.non_empty_count == 1


# ---------------------------------------------------------------------------
# Blocking tests
# ---------------------------------------------------------------------------

class TestBlocking:
    def test_small_dataset_no_blocking(self):
        """Small datasets should use full cross-join without blocking."""
        rows_a = [{"Name": f"Person {i}"} for i in range(5)]
        rows_b = [{"Full Name": f"Person {i}"} for i in range(5)]
        pairs, blocking_applied, note = generate_candidate_pairs(rows_a, rows_b, "Name", "Full Name")
        assert not blocking_applied
        assert len(pairs) == 25  # 5 * 5

    def test_large_dataset_uses_blocking(self):
        """Datasets with product > BLOCKING_THRESHOLD should use blocking.
        Use deliberately dissimilar names so blocking eliminates most pairs."""
        import string
        # Create 300 records per party with very different first characters
        # so that most pairs share NO block tokens
        rows_a = [{"Name": f"{chr(65 + (i % 26))}{chr(97 + (i % 10))}_{i:04d}"} for i in range(300)]
        rows_b = [{"Full Name": f"Zz_{i:04d}"} for i in range(300)]  # all start with 'Zz'
        pairs, blocking_applied, note = generate_candidate_pairs(rows_a, rows_b, "Name", "Full Name")
        assert blocking_applied
        # All of rows_b start with 'Zz_' so they share no bigrams with most of rows_a
        # (which start with A-Z + a-j prefix)
        # We just verify blocking is applied and pairs < full cross-join
        assert len(pairs) < 300 * 300  # Blocking should reduce pairs
        assert "PRIVACY NOTE" in note

    def test_blocking_finds_similar_pairs(self):
        """Blocking should include pairs with overlapping shingles."""
        rows_a = [{"Name": "Alice Johnson"}, {"Name": "Completely Different"}]
        rows_b = [{"Name": "Alice Johnsun"}, {"Name": "Another Unrelated"}]
        # Small enough → full cross-join
        pairs, _, _ = generate_candidate_pairs(rows_a, rows_b, "Name", "Name")
        assert (0, 0) in pairs  # Alice Johnson / Alice Johnsun should be a candidate

    def test_blocking_returns_sorted_pairs(self):
        """Candidate pairs should be in sorted order."""
        rows_a = [{"Name": f"Name {i}"} for i in range(5)]
        rows_b = [{"Name": f"Name {i}"} for i in range(5)]
        pairs, _, _ = generate_candidate_pairs(rows_a, rows_b, "Name", "Name")
        assert pairs == sorted(pairs)

    def test_blocking_reordered_name_preserved(self):
        """Reordered names (e.g. 'Smith, Alice' vs 'Alice Smith') must not be eliminated by blocking."""
        # Dataset product > BLOCKING_THRESHOLD to enforce blocking
        rows_a = [{"Name": "Smith, Alice"}] + [{"Name": f"Z_FillerA_{i:04d}"} for i in range(210)]
        rows_b = [{"Name": "Alice Smith"}] + [{"Name": f"X_FillerB_{i:04d}"} for i in range(210)]
        pairs, blocking_applied, _ = generate_candidate_pairs(rows_a, rows_b, "Name", "Name")
        assert blocking_applied is True
        assert (0, 0) in pairs, "Pair with reordered name was incorrectly eliminated by blocking"

    def test_blocking_leading_typo_preserved(self):
        """Leading typo (e.g. 'Cathy' vs 'Kathy') must not be eliminated by blocking."""
        rows_a = [{"Name": "Cathy Henderson"}] + [{"Name": f"Z_FillerA_{i:04d}"} for i in range(210)]
        rows_b = [{"Name": "Kathy Henderson"}] + [{"Name": f"X_FillerB_{i:04d}"} for i in range(210)]
        pairs, blocking_applied, _ = generate_candidate_pairs(rows_a, rows_b, "Name", "Name")
        assert blocking_applied is True
        assert (0, 0) in pairs, "Pair with leading typo was incorrectly eliminated by blocking"

    def test_blocking_genuine_fuzzy_match_lost_by_prefix_rule_preserved(self):
        """Prefix additions/variations (e.g. 'Dr. Catherine Miller' vs 'Catherine Miller') preserved."""
        rows_a = [{"Name": "Dr. Catherine Miller"}] + [{"Name": f"Z_FillerA_{i:04d}"} for i in range(210)]
        rows_b = [{"Name": "Catherine Miller"}] + [{"Name": f"X_FillerB_{i:04d}"} for i in range(210)]
        pairs, blocking_applied, _ = generate_candidate_pairs(rows_a, rows_b, "Name", "Name")
        assert blocking_applied is True
        assert (0, 0) in pairs, "Genuine match with prefix addition was eliminated by blocking"


# ---------------------------------------------------------------------------
# Multi-attribute matcher tests
# ---------------------------------------------------------------------------

class TestMultiAttributeMatcher:
    def _make_mappings(self):
        return [
            AttributeMapping(column_a="Name", column_b="Full Name", strategy=MatchStrategy.FUZZY, weight=2.0, fuzzy_threshold=0.70),
            AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=3.0),
            AttributeMapping(column_a="City", column_b="Location", strategy=MatchStrategy.FUZZY, weight=1.0, fuzzy_threshold=0.70),
        ]

    def test_fuzzy_similar_names(self):
        """Near-identical names should produce high fuzzy score."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {"Name": "Alice Johnson"}
        row_b = {"Full Name": "Alice Johnsun"}
        mappings = [AttributeMapping(column_a="Name", column_b="Full Name", strategy=MatchStrategy.FUZZY, weight=1.0, fuzzy_threshold=0.60)]
        scores = matcher.evaluate_pair(row_a, row_b, mappings)
        assert scores is not None
        assert len(scores) == 1
        assert scores[0].score is not None
        assert scores[0].score > 0.7  # One character typo should still match

    def test_exact_match_same_email(self):
        """Identical emails should produce score 1.0 for exact strategy."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {"Email": "alice@example.com"}
        row_b = {"Email ID": "alice@example.com"}
        mappings = [AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=1.0)]
        scores = matcher.evaluate_pair(row_a, row_b, mappings)
        assert scores is not None
        assert scores[0].score == 1.0

    def test_exact_match_different_email(self):
        """Different emails should produce score 0.0 for exact strategy."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {"Email": "alice@example.com"}
        row_b = {"Email ID": "bob@example.com"}
        mappings = [AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=1.0)]
        scores = matcher.evaluate_pair(row_a, row_b, mappings)
        assert scores is not None
        assert scores[0].score == 0.0

    def test_ignore_strategy(self):
        """Ignored attributes should have score=None."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {"City": "New York"}
        row_b = {"Location": "New York"}
        mappings = [AttributeMapping(column_a="City", column_b="Location", strategy=MatchStrategy.IGNORE, weight=1.0)]
        scores = matcher.evaluate_pair(row_a, row_b, mappings)
        assert scores is not None
        assert scores[0].score is None

    def test_multi_attribute_scoring(self):
        """Multi-attribute matching should return a score per mapping."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {"Name": "Bob Smith", "Email": "bob@example.com"}
        row_b = {"Full Name": "Bob Smith", "Email ID": "bob@example.com"}
        mappings = [
            AttributeMapping(column_a="Name", column_b="Full Name", strategy=MatchStrategy.FUZZY, weight=1.0, fuzzy_threshold=0.60),
            AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=2.0),
        ]
        scores = matcher.evaluate_pair(row_a, row_b, mappings)
        assert scores is not None
        assert len(scores) == 2
        assert scores[0].score is not None
        assert scores[1].score == 1.0

    def test_normalize_case_insensitive_exact(self):
        """Normalization should allow case-insensitive exact match."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {"Email": "Alice@Example.COM"}
        row_b = {"Email ID": "alice@example.com"}
        mappings = [AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=1.0)]
        scores = matcher.evaluate_pair(row_a, row_b, mappings)
        assert scores is not None
        assert scores[0].score == 1.0

    def test_both_attributes_missing_excluded_from_score(self):
        """When an attribute is missing in both records, score is None and excluded from weighted score."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {"Name": "Alice Johnson", "Phone": ""}
        row_b = {"Full Name": "Alice Johnson", "Phone": ""}
        mappings = [
            AttributeMapping(column_a="Name", column_b="Full Name", strategy=MatchStrategy.FUZZY, weight=2.0),
            AttributeMapping(column_a="Phone", column_b="Phone", strategy=MatchStrategy.EXACT, weight=3.0),
        ]
        scores = matcher.evaluate_pair(row_a, row_b, mappings)
        assert scores is not None
        assert len(scores) == 2
        assert scores[0].score is not None
        assert scores[0].score > 0.9
        # Phone: both missing -> score must be None, NOT 1.0
        assert scores[1].score is None
        # Overall score should equal the Name score alone (Phone excluded from denominator and numerator)
        overall = compute_overall_score(scores)
        assert overall == scores[0].score

    def test_one_attribute_missing_scores_zero(self):
        """When an attribute is missing in only one record, score must be 0.0 (penalizing with weight)."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {"Name": "Alice Johnson", "Phone": "1234567890"}
        row_b = {"Full Name": "Alice Johnson", "Phone": ""}
        mappings = [
            AttributeMapping(column_a="Name", column_b="Full Name", strategy=MatchStrategy.FUZZY, weight=2.0),
            AttributeMapping(column_a="Phone", column_b="Phone", strategy=MatchStrategy.EXACT, weight=3.0),
        ]
        scores = matcher.evaluate_pair(row_a, row_b, mappings)
        assert scores is not None
        assert len(scores) == 2
        assert scores[0].score is not None
        # Phone: one missing -> score must be 0.0
        assert scores[1].score == 0.0
        overall = compute_overall_score(scores)
        expected = round((2.0 * scores[0].score + 3.0 * 0.0) / (2.0 + 3.0), 5)
        assert overall == expected

    def test_multiple_missing_optional_attributes(self):
        """Multiple missing optional attributes in both records are excluded without inflating score."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {"Name": "Alice Johnson", "Phone": "", "Email": "", "City": "Boston"}
        row_b = {"Full Name": "Alice Johnson", "Phone": "", "Email": "", "City": "Boston"}
        mappings = [
            AttributeMapping(column_a="Name", column_b="Full Name", strategy=MatchStrategy.FUZZY, weight=2.0),
            AttributeMapping(column_a="Phone", column_b="Phone", strategy=MatchStrategy.EXACT, weight=3.0),
            AttributeMapping(column_a="Email", column_b="Email", strategy=MatchStrategy.EXACT, weight=4.0),
            AttributeMapping(column_a="City", column_b="City", strategy=MatchStrategy.EXACT, weight=1.0),
        ]
        scores = matcher.evaluate_pair(row_a, row_b, mappings)
        assert scores is not None
        assert scores[0].score is not None
        assert scores[1].score is None  # Phone excluded
        assert scores[2].score is None  # Email excluded
        assert scores[3].score == 1.0   # City exact match
        overall = compute_overall_score(scores)
        # Expected: only Name (wt 2.0) and City (wt 1.0) contribute
        expected = round((2.0 * scores[0].score + 1.0 * 1.0) / (2.0 + 1.0), 5)
        assert overall == expected


# ---------------------------------------------------------------------------
# Weighted scorer tests
# ---------------------------------------------------------------------------

class TestWeightedScorer:
    def _make_scores(self, score_a, score_b, strategy_a=MatchStrategy.FUZZY, strategy_b=MatchStrategy.EXACT):
        return [
            AttributeScore(column_a="Name", column_b="Full Name", strategy=strategy_a, score=score_a, weight=2.0),
            AttributeScore(column_a="Email", column_b="Email ID", strategy=strategy_b, score=score_b, weight=3.0),
        ]

    def test_weighted_average(self):
        scores = self._make_scores(0.8, 1.0)
        overall = compute_overall_score(scores)
        assert overall is not None
        expected = (2.0 * 0.8 + 3.0 * 1.0) / (2.0 + 3.0)
        assert abs(overall - expected) < 1e-4

    def test_all_ignored_returns_none(self):
        scores = [
            AttributeScore(column_a="Name", column_b="Full Name", strategy=MatchStrategy.IGNORE, score=None, weight=1.0),
        ]
        assert compute_overall_score(scores) is None

    def test_build_match_result_above_threshold(self):
        scores = self._make_scores(0.9, 1.0)
        result = build_match_result(0, 0, scores, 0.75, {"Name": "Alice"}, {"Full Name": "Alice"})
        assert result is not None
        assert result.is_match is True
        assert result.overall_score > 0.75

    def test_build_match_result_below_threshold(self):
        scores = self._make_scores(0.0, 0.0)
        result = build_match_result(0, 1, scores, 0.75, {}, {})
        assert result is None

    def test_mixed_ignore_and_scored(self):
        scores = [
            AttributeScore(column_a="Name", column_b="Name", strategy=MatchStrategy.FUZZY, score=0.9, weight=2.0),
            AttributeScore(column_a="City", column_b="City", strategy=MatchStrategy.IGNORE, score=None, weight=5.0),
        ]
        overall = compute_overall_score(scores)
        assert overall == pytest.approx(0.9, abs=1e-4)


# ---------------------------------------------------------------------------
# API endpoint integration tests
# ---------------------------------------------------------------------------

class TestERAPIEndpoints:
    def _create_job(self):
        resp = client.post("/api/er/new")
        assert resp.status_code == 201
        return resp.json()["job_id"]

    def _upload(self, job_id: str, party: str, csv_bytes: bytes, filename: str) -> dict:
        resp = client.post(
            f"/api/er/upload/{party}",
            data={"job_id": job_id},
            files={"file": (filename, csv_bytes, "text/csv")},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    def _start_job(self, job_id: str, mappings: list, threshold: float = 0.5) -> dict:
        payload = {
            "job_id": job_id,
            "mappings": mappings,
            "overall_threshold": threshold,
            "normalize": True,
        }
        resp = client.post("/api/er/start", json=payload)
        assert resp.status_code == 202, resp.text
        return resp.json()

    def _wait_for_completion(self, job_id: str, timeout: float = 60.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = client.get(f"/api/er/status/{job_id}")
            assert resp.status_code == 200
            status = resp.json()
            if status["phase"] in ("complete", "error"):
                return status
            time.sleep(0.2)
        pytest.fail(f"Job {job_id} did not complete within {timeout}s")

    def test_create_job(self):
        job_id = self._create_job()
        assert len(job_id) > 0

    def test_upload_party_a(self):
        job_id = self._create_job()
        result = self._upload(job_id, "A", CSV_A, "dataset_a.csv")
        assert result["party"] == "A"
        assert result["dataset_schema"]["row_count"] == 3
        assert len(result["dataset_schema"]["columns"]) == 3

    def test_upload_party_b(self):
        job_id = self._create_job()
        result = self._upload(job_id, "B", CSV_B, "dataset_b.csv")
        assert result["party"] == "B"
        assert result["dataset_schema"]["row_count"] == 3

    def test_invalid_party_upload(self):
        job_id = self._create_job()
        resp = client.post(
            f"/api/er/upload/X",
            data={"job_id": job_id},
            files={"file": ("data.csv", CSV_A, "text/csv")},
        )
        assert resp.status_code == 400

    def test_start_without_datasets_fails(self):
        job_id = self._create_job()
        payload = {
            "job_id": job_id,
            "mappings": [{"column_a": "Name", "column_b": "Full Name", "strategy": "fuzzy", "weight": 1.0, "fuzzy_threshold": 0.7}],
            "overall_threshold": 0.5,
        }
        resp = client.post("/api/er/start", json=payload)
        assert resp.status_code == 422  # Missing dataset A

    def test_full_er_pipeline_small(self):
        """End-to-end test: upload → start → wait → results."""
        job_id = self._create_job()
        self._upload(job_id, "A", CSV_A, "dataset_a.csv")
        self._upload(job_id, "B", CSV_B, "dataset_b.csv")

        mappings = [
            {"column_a": "Name", "column_b": "Full Name", "strategy": "fuzzy", "weight": 2.0, "fuzzy_threshold": 0.60},
            {"column_a": "Email", "column_b": "Email ID", "strategy": "exact", "weight": 3.0},
            {"column_a": "City", "column_b": "Location", "strategy": "fuzzy", "weight": 1.0, "fuzzy_threshold": 0.70},
        ]
        self._start_job(job_id, mappings, threshold=0.5)

        status = self._wait_for_completion(job_id)
        assert status["phase"] == "complete"

        # Check results
        resp = client.get(f"/api/er/results/{job_id}")
        assert resp.status_code == 200
        results = resp.json()

        assert results["dataset_size_a"] == 3
        assert results["dataset_size_b"] == 3
        assert results["total_matches"] > 0  # At least Alice and Bob should match

        # Ensure attribute_scores are present
        first_match = results["results"][0]
        assert "attribute_scores" in first_match
        assert "overall_score" in first_match
        assert first_match["overall_score"] >= 0.5

    def test_results_pagination(self):
        """Test paginated results."""
        # Generate a small dataset with more records for pagination
        large_rows_a = [{"Name": f"Person {i}", "Email": f"p{i}@example.com"} for i in range(10)]
        large_rows_b = [{"Full Name": f"Person {i}", "Email ID": f"p{i}@example.com"} for i in range(10)]
        large_csv_a = _make_csv(large_rows_a, ["Name", "Email"])
        large_csv_b = _make_csv(large_rows_b, ["Full Name", "Email ID"])

        job_id = self._create_job()
        self._upload(job_id, "A", large_csv_a, "large_a.csv")
        self._upload(job_id, "B", large_csv_b, "large_b.csv")

        mappings = [
            {"column_a": "Email", "column_b": "Email ID", "strategy": "exact", "weight": 1.0},
        ]
        self._start_job(job_id, mappings, threshold=0.5)
        self._wait_for_completion(job_id)

        resp = client.get(f"/api/er/results/{job_id}?page=1&page_size=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) <= 3
        assert data["page"] == 1

    def test_status_endpoint(self):
        job_id = self._create_job()
        resp = client.get(f"/api/er/status/{job_id}")
        assert resp.status_code == 200
        status = resp.json()
        assert status["phase"] == "queued"
        assert status["job_id"] == job_id

    def test_results_not_ready_returns_202(self):
        job_id = self._create_job()
        # Don't run the job — results should not be available
        resp = client.get(f"/api/er/results/{job_id}")
        assert resp.status_code == 202

    def test_export_csv(self):
        """Test CSV export endpoint."""
        job_id = self._create_job()
        self._upload(job_id, "A", CSV_A, "dataset_a.csv")
        self._upload(job_id, "B", CSV_B, "dataset_b.csv")

        mappings = [
            {"column_a": "Email", "column_b": "Email ID", "strategy": "exact", "weight": 1.0},
        ]
        self._start_job(job_id, mappings, threshold=0.5)
        self._wait_for_completion(job_id)

        resp = client.get(f"/api/er/export/{job_id}")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        content = resp.text
        assert "overall_score" in content  # CSV header

    def test_unknown_job_returns_404(self):
        resp = client.get("/api/er/status/nonexistent-job-id")
        assert resp.status_code == 404

    def test_upload_invalid_party_char(self):
        job_id = self._create_job()
        resp = client.post(
            "/api/er/upload/C",
            data={"job_id": job_id},
            files={"file": ("data.csv", CSV_A, "text/csv")},
        )
        assert resp.status_code == 400

    def test_exact_match_finds_shared_emails(self):
        """Exact email matching should find matching pairs and not false positives."""
        rows_a = [{"Email": "alice@x.com"}, {"Email": "bob@x.com"}, {"Email": "carol@x.com"}]
        rows_b = [{"Email ID": "bob@x.com"}, {"Email ID": "dave@x.com"}]
        csv_a = _make_csv(rows_a, ["Email"])
        csv_b = _make_csv(rows_b, ["Email ID"])

        job_id = self._create_job()
        self._upload(job_id, "A", csv_a, "a.csv")
        self._upload(job_id, "B", csv_b, "b.csv")

        mappings = [{"column_a": "Email", "column_b": "Email ID", "strategy": "exact", "weight": 1.0}]
        self._start_job(job_id, mappings, threshold=0.9)
        self._wait_for_completion(job_id)

        resp = client.get(f"/api/er/results/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        # Only bob@x.com should match
        assert data["total_matches"] == 1
        match = data["results"][0]
        assert match["overall_score"] == 1.0


# ---------------------------------------------------------------------------
# Alice OPRF Memoization & Precomputation Tests
# ---------------------------------------------------------------------------

class TestAliceOPRFMemoization:
    def test_repeated_alice_shingles_reused(self):
        """When the same Alice record is compared with multiple B records, Alice's OPRF work is reused."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {"Name": "Alice Johnson", "Email": "alice@example.com"}
        row_b1 = {"Full Name": "Alice Johnson", "Email ID": "alice@example.com"}
        row_b2 = {"Full Name": "Alicia Johnson", "Email ID": "alice_alt@example.com"}

        mappings = [
            AttributeMapping(column_a="Name", column_b="Full Name", strategy=MatchStrategy.FUZZY, weight=1.0),
            AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=1.0),
        ]

        # First comparison: computes Alice's shingles & exact value
        scores1 = matcher.evaluate_pair(row_a, row_b1, mappings)
        initial_alice_evals = matcher.stats["alice_shingle_evaluations"] + matcher.stats["alice_exact_evaluations"]
        assert initial_alice_evals > 0

        # Second comparison: same Alice record
        scores2 = matcher.evaluate_pair(row_a, row_b2, mappings)
        # Alice should NOT perform any new OPRF exponentiations for row_a!
        new_alice_evals = (
            matcher.stats["alice_shingle_evaluations"] + matcher.stats["alice_exact_evaluations"]
        ) - initial_alice_evals
        assert new_alice_evals == 0, f"Alice performed {new_alice_evals} redundant OPRF evaluations!"
        assert matcher.stats["alice_fuzzy_hits"] >= 1
        assert matcher.stats["alice_exact_hits"] >= 1

    def test_multiple_alice_records_sharing_values_reuse_cache(self):
        """Different Alice records with identical attribute values reuse the cached OPRF representation."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a1 = {"City": "San Francisco"}
        row_a2 = {"City": "San Francisco"}
        row_b = {"Location": "San Francisco"}

        mappings = [
            AttributeMapping(column_a="City", column_b="Location", strategy=MatchStrategy.EXACT, weight=1.0),
        ]

        matcher.evaluate_pair(row_a1, row_b, mappings)
        evals_after_first = matcher.stats["alice_exact_evaluations"]
        assert evals_after_first == 1

        matcher.evaluate_pair(row_a2, row_b, mappings)
        assert matcher.stats["alice_exact_evaluations"] == 1
        assert matcher.stats["alice_exact_hits"] >= 1

    def test_different_values_do_not_share_cached_representations(self):
        """Distinct values produce distinct OPRF representations and are not cross-contaminated."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a1 = {"Email": "alice@domain1.com"}
        row_a2 = {"Email": "bob@domain2.com"}
        row_b = {"Email ID": "alice@domain1.com"}

        mappings = [
            AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=1.0),
        ]

        scores1 = matcher.evaluate_pair(row_a1, row_b, mappings)
        scores2 = matcher.evaluate_pair(row_a2, row_b, mappings)
        assert scores1 is not None and scores2 is not None

        assert scores1[0].score == 1.0
        assert scores2[0].score == 0.0

        digest_a1 = matcher._alice_exact_cache["alice@domain1.com"]
        digest_a2 = matcher._alice_exact_cache["bob@domain2.com"]
        assert digest_a1 != digest_a2

    def test_cache_isolated_between_sessions(self):
        """Separate MultiAttributeMatcher instances have fresh secret keys and isolated caches."""
        matcher1 = MultiAttributeMatcher(normalize=True)
        matcher2 = MultiAttributeMatcher(normalize=True)

        row_a = {"Email": "alice@example.com"}
        row_b = {"Email ID": "alice@example.com"}
        mappings = [
            AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=1.0),
        ]

        matcher1.evaluate_pair(row_a, row_b, mappings)
        assert len(matcher1._alice_exact_cache) == 1
        assert len(matcher2._alice_exact_cache) == 0  # isolated!

        # Different server keys produce different PRF outputs for the same input
        digest1 = matcher1._alice_exact_cache["alice@example.com"]
        matcher2.evaluate_pair(row_a, row_b, mappings)
        digest2 = matcher2._alice_exact_cache["alice@example.com"]
        assert digest1 != digest2  # Fresh keys per session!

    def test_precompute_alice_populates_caches(self):
        """precompute_alice populates all mapped attribute caches upfront."""
        matcher = MultiAttributeMatcher(normalize=True)
        rows_a = [
            {"Name": "John Doe", "Email": "john@example.com"},
            {"Name": "Jane Doe", "Email": "jane@example.com"},
        ]
        mappings = [
            AttributeMapping(column_a="Name", column_b="Full Name", strategy=MatchStrategy.FUZZY, weight=1.0),
            AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=1.0),
        ]

        matcher.precompute_alice(rows_a, mappings)
        assert len(matcher._alice_fuzzy_cache) == 2
        assert len(matcher._alice_exact_cache) == 2
        assert "john doe" in matcher._alice_fuzzy_cache
        assert "jane doe" in matcher._alice_fuzzy_cache

        # When evaluate_pair is subsequently called, Alice incurs 0 misses
        row_b = {"Full Name": "John Doe", "Email ID": "john@example.com"}
        misses_before = matcher.stats["alice_fuzzy_misses"]
        matcher.evaluate_pair(rows_a[0], row_b, mappings)
        assert matcher.stats["alice_fuzzy_misses"] == misses_before
        assert matcher.stats["alice_fuzzy_hits"] >= 1


# ---------------------------------------------------------------------------
# Short-circuit attribute evaluation regression tests (Optimization 2)
# ---------------------------------------------------------------------------

class TestShortCircuitEvaluation:
    """
    Regression tests proving that mathematically safe short-circuit attribute
    evaluation never introduces false negatives, correctly handles missing values,
    and skips remaining attributes when maximum possible score < overall_threshold.
    """

    @pytest.fixture
    def standard_mappings(self):
        return [
            AttributeMapping(column_a="Name", column_b="Full Name", strategy=MatchStrategy.FUZZY, weight=2.0, fuzzy_threshold=0.75),
            AttributeMapping(column_a="Address", column_b="Residential Address", strategy=MatchStrategy.FUZZY, weight=1.0, fuzzy_threshold=0.70),
            AttributeMapping(column_a="Phone", column_b="Mobile", strategy=MatchStrategy.EXACT, weight=2.0),
            AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=3.0),
            AttributeMapping(column_a="City", column_b="Location", strategy=MatchStrategy.FUZZY, weight=1.0, fuzzy_threshold=0.80),
        ]

    def test_candidate_reaching_threshold_not_short_circuited(self, standard_mappings):
        """1. A candidate that reaches the threshold must NOT be short-circuited."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {
            "Name": "John Smith",
            "Address": "123 Main St",
            "Phone": "555-0101",
            "Email": "john.smith@example.com",
            "City": "New York",
        }
        row_b = {
            "Full Name": "John Smith",
            "Residential Address": "123 Main St",
            "Mobile": "555-0101",
            "Email ID": "john.smith@example.com",
            "Location": "New York",
        }

        scores = matcher.evaluate_pair(row_a, row_b, standard_mappings, overall_threshold=0.75)
        assert scores is not None
        assert len(scores) == 5
        assert matcher.stats["pairs_short_circuited"] == 0
        assert matcher.stats["pairs_fully_evaluated"] == 1
        assert matcher.stats["attributes_skipped"] == 0
        assert compute_overall_score(scores) == 1.0

    def test_candidate_cannot_reach_threshold_is_short_circuited(self, standard_mappings):
        """2. A candidate that cannot possibly reach the threshold IS short-circuited."""
        matcher = MultiAttributeMatcher(normalize=True)
        # Completely disjoint non-matching pair
        row_a = {
            "Name": "John Smith",
            "Address": "123 Main St",
            "Phone": "555-0101",
            "Email": "john.smith@example.com",
            "City": "New York",
        }
        row_b = {
            "Full Name": "Alice Williams",
            "Residential Address": "999 Oak Ave",
            "Mobile": "555-9999",
            "Email ID": "alice.williams@other.org",
            "Location": "Chicago",
        }

        scores = matcher.evaluate_pair(row_a, row_b, standard_mappings, overall_threshold=0.75)
        assert scores is None  # Immediately rejected
        assert matcher.stats["pairs_short_circuited"] == 1
        assert matcher.last_pair_short_circuited is True
        assert matcher.stats["attributes_skipped"] >= 3

    def test_candidate_with_name_zero_still_matches(self, standard_mappings):
        """3. A candidate with Name=0 but enough remaining weighted attributes to still match."""
        matcher = MultiAttributeMatcher(normalize=True)
        # Name is completely different (e.g. maiden vs married name), but Phone, Email, Address, City match
        row_a = {
            "Name": "Jane Brown",
            "Address": "123 Main St",
            "Phone": "555-0101",
            "Email": "jane.doe@example.com",
            "City": "New York",
        }
        row_b = {
            "Full Name": "Jane Zzzzzzzzzz",
            "Residential Address": "123 Main St",
            "Mobile": "555-0101",
            "Email ID": "jane.doe@example.com",
            "Location": "New York",
        }

        # Weights: Name(2.0)=0, Address(1.0)=1.0, Phone(2.0)=1.0, Email(3.0)=1.0, City(1.0)=1.0
        # Score = (0 + 1 + 2 + 3 + 1) / 9 = 7 / 9 = 0.77778 >= 0.75 threshold
        scores = matcher.evaluate_pair(row_a, row_b, standard_mappings, overall_threshold=0.75)
        assert scores is not None  # Must NOT be short-circuited!
        assert matcher.stats["pairs_short_circuited"] == 0
        overall = compute_overall_score(scores)
        assert overall is not None
        assert overall >= 0.75

    def test_candidate_several_low_scores_short_circuited(self, standard_mappings):
        """4. A candidate with several low scores where remaining maximum cannot reach threshold."""
        matcher = MultiAttributeMatcher(normalize=True)
        # Email matches (weight 3.0), but Phone fails (2.0) and Name fails (2.0)
        # Max remaining score: (3.0 + 2.0) / 9.0 = 0.5555 < 0.75 threshold
        row_a = {
            "Name": "John Smith",
            "Address": "123 Main St",
            "Phone": "555-0101",
            "Email": "user@shared.com",
            "City": "New York",
        }
        row_b = {
            "Full Name": "Zack Miller",
            "Residential Address": "123 Main St",
            "Mobile": "555-9999",
            "Email ID": "user@shared.com",
            "Location": "New York",
        }

        scores = matcher.evaluate_pair(row_a, row_b, standard_mappings, overall_threshold=0.75)
        assert scores is None
        assert matcher.stats["pairs_short_circuited"] == 1
        assert matcher.stats["attributes_skipped"] >= 1

    def test_both_missing_attributes_excluded_from_denominator(self, standard_mappings):
        """5. Both-missing attributes must have score=None and be excluded from weighted denominator."""
        matcher = MultiAttributeMatcher(normalize=True)
        # Address and City missing in BOTH records
        row_a = {
            "Name": "John Smith",
            "Address": "",
            "Phone": "555-0101",
            "Email": "john@example.com",
            "City": "",
        }
        row_b = {
            "Full Name": "John Smith",
            "Residential Address": "",
            "Mobile": "555-0101",
            "Email ID": "john@example.com",
            "Location": "",
        }

        # Total weight of present attributes: Name(2.0) + Phone(2.0) + Email(3.0) = 7.0
        # All 3 match -> score = 7.0 / 7.0 = 1.0 >= 0.75
        scores = matcher.evaluate_pair(row_a, row_b, standard_mappings, overall_threshold=0.75)
        assert scores is not None
        addr_score = next(s for s in scores if s.column_a == "Address")
        city_score = next(s for s in scores if s.column_a == "City")
        assert addr_score.score is None
        assert city_score.score is None
        overall = compute_overall_score(scores)
        assert overall == 1.0

    def test_one_missing_attribute_counts_in_denominator_as_zero(self, standard_mappings):
        """6. One-missing attributes must have score=0.0 and count in denominator."""
        matcher = MultiAttributeMatcher(normalize=True)
        # Address is present in A but missing in B
        row_a = {
            "Name": "John Smith",
            "Address": "123 Main St",
            "Phone": "555-0101",
            "Email": "john@example.com",
            "City": "New York",
        }
        row_b = {
            "Full Name": "John Smith",
            "Residential Address": "",
            "Mobile": "555-0101",
            "Email ID": "john@example.com",
            "Location": "New York",
        }

        # Address contributes 0.0, weight 1.0 counts in denominator
        # Numerator: Name(2*1) + Address(1*0) + Phone(2*1) + Email(3*1) + City(1*1) = 8.0
        # Denominator: 9.0 -> 8/9 = 0.88889 >= 0.75
        scores = matcher.evaluate_pair(row_a, row_b, standard_mappings, overall_threshold=0.75)
        assert scores is not None
        addr_score = next(s for s in scores if s.column_a == "Address")
        assert addr_score.score == 0.0
        overall = compute_overall_score(scores)
        assert overall is not None
        assert round(overall, 3) == 0.889

    def test_all_attributes_present(self, standard_mappings):
        """7. A candidate with all attributes present evaluates correctly."""
        matcher = MultiAttributeMatcher(normalize=True)
        row_a = {
            "Name": "Alice Johnson",
            "Address": "456 Oak Rd",
            "Phone": "555-1234",
            "Email": "alice@example.com",
            "City": "Chicago",
        }
        row_b = {
            "Full Name": "Alice Johnson",
            "Residential Address": "456 Oak Rd",
            "Mobile": "555-1234",
            "Email ID": "alice@example.com",
            "Location": "Chicago",
        }

        scores = matcher.evaluate_pair(row_a, row_b, standard_mappings, overall_threshold=0.75)
        assert scores is not None
        assert all(s.score is not None for s in scores)
        assert all(s.score == 1.0 for s in scores)

    def test_exact_attributes_short_circuit(self):
        """8. Exact attributes short-circuit when mismatch prevents reaching threshold."""
        matcher = MultiAttributeMatcher(normalize=True)
        mappings = [
            AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=3.0),
            AttributeMapping(column_a="Phone", column_b="Mobile", strategy=MatchStrategy.EXACT, weight=2.0),
        ]
        row_a = {"Email": "a@example.com", "Phone": "111-2222"}
        row_b = {"Email ID": "b@example.com", "Mobile": "111-2222"}

        # Email fails (0.0). Max remaining score: (0 + 2.0) / 5.0 = 0.40 < 0.75
        scores = matcher.evaluate_pair(row_a, row_b, mappings, overall_threshold=0.75)
        assert scores is None
        assert matcher.stats["pairs_short_circuited"] == 1
        assert matcher.stats["attributes_skipped"] == 1  # Phone was skipped!

    def test_fuzzy_attributes_short_circuit(self):
        """9. Fuzzy attributes short-circuit when low similarity prevents reaching threshold."""
        matcher = MultiAttributeMatcher(normalize=True)
        mappings = [
            AttributeMapping(column_a="Name", column_b="Full Name", strategy=MatchStrategy.FUZZY, weight=3.0, fuzzy_threshold=0.70),
            AttributeMapping(column_a="Address", column_b="Address", strategy=MatchStrategy.FUZZY, weight=2.0, fuzzy_threshold=0.70),
        ]
        row_a = {"Name": "Alexander Hamilton", "Address": "123 Wall St"}
        row_b = {"Full Name": "Zackary Taylor", "Address": "123 Wall St"}

        # Name has 0 Dice similarity (< 0.70 -> score 0.0). Max remaining: 2.0 / 5.0 = 0.40 < 0.75
        scores = matcher.evaluate_pair(row_a, row_b, mappings, overall_threshold=0.75)
        assert scores is None
        assert matcher.stats["pairs_short_circuited"] == 1
        assert matcher.stats["attributes_skipped"] == 1  # Address was skipped!

    def test_short_circuit_produces_identical_final_matches_as_full_eval(self, standard_mappings):
        """10. Verify that short-circuiting produces exactly the same final matches and scores as full evaluation."""
        from benchmarks.run_scalability_benchmark import generate_benchmark_datasets

        rows_a, rows_b, expected_matches = generate_benchmark_datasets(20, seed=42)

        # Run 1: Full evaluation without short-circuiting
        matcher_full = MultiAttributeMatcher(normalize=True)
        matcher_full.precompute_alice(rows_a, standard_mappings)
        full_matches = {}
        for i, ra in enumerate(rows_a):
            for j, rb in enumerate(rows_b):
                scores = matcher_full.evaluate_pair(ra, rb, standard_mappings, overall_threshold=None)
                if scores is not None:
                    overall = compute_overall_score(scores)
                    if overall is not None and overall >= 0.75:
                        full_matches[(i, j)] = (overall, [s.score for s in scores])

        # Run 2: With short-circuiting
        matcher_sc = MultiAttributeMatcher(normalize=True)
        matcher_sc.precompute_alice(rows_a, standard_mappings)
        sc_matches = {}
        for i, ra in enumerate(rows_a):
            for j, rb in enumerate(rows_b):
                scores = matcher_sc.evaluate_pair(ra, rb, standard_mappings, overall_threshold=0.75)
                if scores is not None:
                    overall = compute_overall_score(scores)
                    if overall is not None and overall >= 0.75:
                        sc_matches[(i, j)] = (overall, [s.score for s in scores])

        # Assert identical matches and identical scores
        assert set(full_matches.keys()) == set(sc_matches.keys())
        assert len(full_matches) == expected_matches
        for key in full_matches:
            full_score, full_attr_scores = full_matches[key]
            sc_score, sc_attr_scores = sc_matches[key]
            assert full_score == sc_score
            assert full_attr_scores == sc_attr_scores

        # Verify short-circuiting actually skipped attributes on rejected pairs
        assert matcher_sc.stats["pairs_short_circuited"] > 0
        assert matcher_sc.stats["attributes_skipped"] > 0

    def test_precomputation_and_memoization_intact_with_short_circuit(self, standard_mappings):
        """11. Verify that Alice OPRF memoization/precomputation still works with short-circuiting."""
        rows_a = [{"Name": "John Doe", "Address": "123 Elm St", "Phone": "555-1111", "Email": "john@doe.com", "City": "Denver"}]
        rows_b = [{"Full Name": "John Doe", "Residential Address": "123 Elm St", "Mobile": "555-1111", "Email ID": "john@doe.com", "Location": "Denver"}]

        matcher = MultiAttributeMatcher(normalize=True)
        matcher.precompute_alice(rows_a, standard_mappings)

        # Alice fuzzy and exact caches populated
        assert len(matcher._alice_fuzzy_cache) >= 3
        assert len(matcher._alice_exact_cache) >= 2

        # Evaluate candidate pair with short-circuiting enabled
        scores = matcher.evaluate_pair(rows_a[0], rows_b[0], standard_mappings, overall_threshold=0.75)
        assert scores is not None
        # Zero additional misses for Alice
        assert matcher.stats["alice_fuzzy_misses"] == 3
        assert matcher.stats["alice_shingle_evaluations"] > 0
        assert matcher.stats["alice_exact_evaluations"] == 2

