"""
Multi-attribute matcher.

Orchestrates per-attribute cryptographic matching over a set of candidate pairs
using the existing OPRF/PSI building blocks with session-scoped memoization.

Key design decisions
--------------------
- FUZZY attributes use CryptographicThresholdPSI (shingle OPRF).
- EXACT attributes use OPRFExactPSI.
- IGNORE attributes are skipped; their score is None / not counted in weighting.
- Alice-side OPRF evaluations are memoized at both the individual shingle level
  and the full protected value level within a single ER job session.
  This guarantees that Alice's blinding, Bob's server evaluation, and Alice's
  unblinding are computed ONCE per unique value/shingle and reused across all
  candidate-pair comparisons.
- Bob-side OPRF evaluations are memoized via _OPRFEvaluator._cache.
- The OPRF key is fresh per job instance (no cross-job linkage or leakage).
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from app.crypto.oprf import OPRFClient, OPRFServer, default_group
from app.crypto.hashing import finalize_oprf_hash
from app.matching.shingle import generate_unique_shingles
from app.models.er_schemas import AttributeMapping, AttributeScore, MatchStrategy
from app.utils.normalization import normalize_string


# ---------------------------------------------------------------------------
# Internal memoized OPRF evaluator for a single OPRF key
# ---------------------------------------------------------------------------

class _OPRFEvaluator:
    """
    Wraps a single OPRFServer key and memoizes evaluate_direct() results.

    By memoizing evaluate_direct(shingle) we avoid redundant 2048-bit exponentiations
    when the same shingle appears in many records across many candidate pairs.
    """

    def __init__(self) -> None:
        self._server = OPRFServer(default_group)
        self._cache: Dict[str, bytes] = {}

    def digest(self, shingle: str) -> bytes:
        if shingle not in self._cache:
            self._cache[shingle] = self._server.evaluate_direct(shingle)
        return self._cache[shingle]

    def evaluate_blinded(self, blinded: int) -> int:
        return self._server.evaluate(blinded)

    @property
    def server(self) -> OPRFServer:
        return self._server


def _oprf_dice_similarity(
    value_a: str,
    value_b: str,
    evaluator: _OPRFEvaluator,
    client: OPRFClient,
) -> Tuple[float, int]:
    """
    Compute OPRF-based Sørensen-Dice similarity between two strings.
    Standalone helper preserving original interface.
    """
    shingles_a = generate_unique_shingles(value_a)
    shingles_b = generate_unique_shingles(value_b)

    if not shingles_a or not shingles_b:
        return 0.0, 0

    # Alice side: blind, evaluate via Bob's server, unblind
    alice_prf_set: Set[bytes] = set()
    for shingle in shingles_a:
        blinded, r = client.blind(shingle)
        evaluated = evaluator.evaluate_blinded(blinded)
        r_inv = default_group.inverse_scalar(r)
        unblinded = default_group.exponentiate(evaluated, r_inv)
        elem_bytes = default_group.serialize_element(unblinded)
        prf = finalize_oprf_hash(shingle, elem_bytes)
        alice_prf_set.add(prf)

    # Bob side: direct evaluation (memoized)
    bob_prf_set: Set[bytes] = {evaluator.digest(s) for s in shingles_b}

    intersection = len(alice_prf_set & bob_prf_set)
    total = len(shingles_a) + len(shingles_b)
    dice = round((2.0 * intersection) / total, 5) if total > 0 else 0.0
    return dice, intersection


def _exact_oprf_match(value_a: str, value_b: str, evaluator: _OPRFEvaluator, client: OPRFClient) -> float:
    """
    Returns 1.0 if OPRF(value_a) == OPRF(value_b), else 0.0.
    Standalone helper preserving original interface.
    """
    if not value_a or not value_b:
        return 0.0

    # Alice side
    blinded, r = client.blind(value_a)
    evaluated = evaluator.evaluate_blinded(blinded)
    r_inv = default_group.inverse_scalar(r)
    unblinded = default_group.exponentiate(evaluated, r_inv)
    elem_bytes = default_group.serialize_element(unblinded)
    alice_prf = finalize_oprf_hash(value_a, elem_bytes)

    # Bob side (memoized)
    bob_prf = evaluator.digest(value_b)

    return 1.0 if alice_prf == bob_prf else 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class MultiAttributeMatcher:
    """
    Evaluates attribute-level similarity for a set of candidate row pairs.

    One instance per ER job. Shares a single OPRF key per job.
    Caches Alice's and Bob's protected representations within this instance session.
    """

    def __init__(self, normalize: bool = True) -> None:
        self._normalize = normalize
        self._evaluator = _OPRFEvaluator()
        self._client = OPRFClient(default_group)
        # Memoize normalized values to avoid redundant normalization
        self._norm_cache: Dict[str, str] = {}

        # Alice-side OPRF caches (scoped strictly to this matcher session)
        self._alice_shingle_cache: Dict[str, bytes] = {}
        self._alice_fuzzy_cache: Dict[str, Tuple[FrozenSet[bytes], int]] = {}
        self._alice_exact_cache: Dict[str, bytes] = {}

        # Bob-side fuzzy digest-set cache (scoped strictly to this matcher session)
        self._bob_fuzzy_cache: Dict[str, Tuple[Set[bytes], int]] = {}

        # Performance instrumentation counters
        self.stats = {
            "candidate_pairs_evaluated": 0,
            "pairs_fully_evaluated": 0,
            "pairs_short_circuited": 0,
            "attributes_skipped": 0,
            "alice_shingle_evaluations": 0,
            "alice_shingle_hits": 0,
            "alice_fuzzy_hits": 0,
            "alice_fuzzy_misses": 0,
            "alice_exact_evaluations": 0,
            "alice_exact_hits": 0,
            "alice_exact_misses": 0,
            "bob_fuzzy_hits": 0,
            "bob_fuzzy_misses": 0,
        }
        self.last_pair_short_circuited: bool = False

    def _norm(self, value: str) -> str:
        if not self._normalize:
            return value
        if value not in self._norm_cache:
            self._norm_cache[value] = normalize_string(value)
        return self._norm_cache[value]

    def _evaluate_alice_shingle(self, shingle: str) -> bytes:
        """
        Evaluate a single shingle using 2Hash-DH OPRF from Alice's side:
        blind -> evaluate via Bob -> unblind -> finalize hash.
        Memoized within this matcher instance.
        """
        if shingle in self._alice_shingle_cache:
            self.stats["alice_shingle_hits"] += 1
            return self._alice_shingle_cache[shingle]

        self.stats["alice_shingle_evaluations"] += 1
        blinded, r = self._client.blind(shingle)
        evaluated = self._evaluator.evaluate_blinded(blinded)
        r_inv = default_group.inverse_scalar(r)
        unblinded = default_group.exponentiate(evaluated, r_inv)
        elem_bytes = default_group.serialize_element(unblinded)
        prf = finalize_oprf_hash(shingle, elem_bytes)

        self._alice_shingle_cache[shingle] = prf
        return prf

    def get_alice_fuzzy_digests(self, value_a: str) -> Tuple[FrozenSet[bytes], int]:
        """
        Compute or retrieve Alice's protected OPRF representation for a fuzzy attribute string.
        Returns (frozenset_of_prf_digests, shingle_count).
        Memoized per normalized string.
        """
        if value_a in self._alice_fuzzy_cache:
            self.stats["alice_fuzzy_hits"] += 1
            return self._alice_fuzzy_cache[value_a]

        self.stats["alice_fuzzy_misses"] += 1
        shingles = generate_unique_shingles(value_a)
        if not shingles:
            result = (frozenset(), 0)
        else:
            prf_set = frozenset(self._evaluate_alice_shingle(s) for s in shingles)
            result = (prf_set, len(shingles))

        self._alice_fuzzy_cache[value_a] = result
        return result

    def get_bob_fuzzy_digests(self, value_b: str) -> Tuple[Set[bytes], int]:
        """
        Compute or retrieve Bob's protected OPRF representation for a fuzzy attribute string.
        Returns (set_of_prf_digests, shingle_count).
        Memoized per normalized string.
        """
        if value_b in self._bob_fuzzy_cache:
            self.stats["bob_fuzzy_hits"] += 1
            return self._bob_fuzzy_cache[value_b]

        self.stats["bob_fuzzy_misses"] += 1
        shingles = generate_unique_shingles(value_b)
        if not shingles:
            result = (set(), 0)
        else:
            # evaluator.digest() memoizes each shingle in evaluator._cache
            result = ({self._evaluator.digest(s) for s in shingles}, len(shingles))

        self._bob_fuzzy_cache[value_b] = result
        return result

    def get_alice_exact_digest(self, value_a: str) -> bytes:
        """
        Compute or retrieve Alice's protected 2Hash-DH OPRF digest for an exact attribute string.
        Memoized per normalized string.
        """
        if value_a in self._alice_exact_cache:
            self.stats["alice_exact_hits"] += 1
            return self._alice_exact_cache[value_a]

        self.stats["alice_exact_misses"] += 1
        self.stats["alice_exact_evaluations"] += 1

        blinded, r = self._client.blind(value_a)
        evaluated = self._evaluator.evaluate_blinded(blinded)
        r_inv = default_group.inverse_scalar(r)
        unblinded = default_group.exponentiate(evaluated, r_inv)
        elem_bytes = default_group.serialize_element(unblinded)
        prf = finalize_oprf_hash(value_a, elem_bytes)

        self._alice_exact_cache[value_a] = prf
        return prf

    def get_bob_exact_digest(self, value_b: str) -> bytes:
        """
        Compute or retrieve Bob's direct OPRF digest for an exact attribute string.
        Memoized via evaluator._cache.
        """
        return self._evaluator.digest(value_b)

    def precompute_alice(
        self,
        rows_a: List[Dict[str, str]],
        mappings: List[AttributeMapping],
    ) -> None:
        """
        Precompute Alice's protected OPRF representation for all unique values
        across dataset A for the mapped attributes.
        """
        for mapping in mappings:
            if mapping.strategy == MatchStrategy.IGNORE:
                continue
            col_a = mapping.column_a
            for row in rows_a:
                val = self._norm(row.get(col_a, ""))
                if not val:
                    continue
                if mapping.strategy == MatchStrategy.EXACT:
                    self.get_alice_exact_digest(val)
                elif mapping.strategy == MatchStrategy.FUZZY:
                    self.get_alice_fuzzy_digests(val)

    def evaluate_pair(
        self,
        row_a: Dict[str, str],
        row_b: Dict[str, str],
        mappings: List[AttributeMapping],
        overall_threshold: Optional[float] = None,
    ) -> Optional[List[AttributeScore]]:
        """
        Evaluate mapped attributes for a single row pair with mathematically
        safe short-circuit evaluation.

        If overall_threshold is provided (and > 0.0):
        - Calculates the maximum possible weighted score achievable by this candidate pair
          given the attributes evaluated so far plus the theoretical maximum (1.0)
          from all remaining present attributes.
        - Attributes with both values missing are excluded from the denominator.
        - Attributes with one value missing contribute 0.0 to the numerator and their weight
          to the denominator.
        - If the maximum possible score drops strictly below overall_threshold, evaluation
          halts immediately without evaluating remaining attributes, returning None.
        - When all necessary attributes are evaluated, returns the list of AttributeScore
          objects in original mapping order.

        If overall_threshold is None or <= 0.0:
        - Evaluates all attributes without short-circuiting, returning List[AttributeScore].
        """
        self.stats["candidate_pairs_evaluated"] += 1
        self.last_pair_short_circuited = False

        # If overall_threshold is not specified or non-positive, evaluate all attributes fully
        if overall_threshold is None or overall_threshold <= 0.0:
            scores: List[AttributeScore] = []
            for mapping in mappings:
                if mapping.strategy == MatchStrategy.IGNORE:
                    scores.append(AttributeScore(
                        column_a=mapping.column_a,
                        column_b=mapping.column_b,
                        strategy=mapping.strategy,
                        score=None,
                        weight=mapping.weight,
                    ))
                    continue

                val_a = self._norm(row_a.get(mapping.column_a, ""))
                val_b = self._norm(row_b.get(mapping.column_b, ""))

                if not val_a and not val_b:
                    score = None
                elif not val_a or not val_b:
                    score = 0.0
                else:
                    if mapping.strategy == MatchStrategy.EXACT:
                        alice_prf = self.get_alice_exact_digest(val_a)
                        bob_prf = self.get_bob_exact_digest(val_b)
                        score = 1.0 if alice_prf == bob_prf else 0.0
                    elif mapping.strategy == MatchStrategy.FUZZY:
                        alice_prfs, count_a = self.get_alice_fuzzy_digests(val_a)
                        bob_prfs, count_b = self.get_bob_fuzzy_digests(val_b)
                        total = count_a + count_b
                        if total > 0:
                            intersection = len(alice_prfs & bob_prfs)
                            dice = round((2.0 * intersection) / total, 5)
                        else:
                            dice = 0.0
                        score = dice if dice >= mapping.fuzzy_threshold else 0.0
                    else:
                        score = None

                scores.append(AttributeScore(
                    column_a=mapping.column_a,
                    column_b=mapping.column_b,
                    strategy=mapping.strategy,
                    score=score,
                    weight=mapping.weight,
                ))

            self.stats["pairs_fully_evaluated"] += 1
            return scores

        # ── Mathematically safe short-circuit evaluation ──
        # 1. Categorize attributes based on value presence
        # For each mapping, determine if both are missing, one is missing, or both present.
        # This requires zero cryptographic operations.
        attr_eval_plan: List[Tuple[int, AttributeMapping, str, str]] = []
        computed_scores: Dict[int, Optional[float]] = {}
        total_weight: float = 0.0

        for idx, mapping in enumerate(mappings):
            if mapping.strategy == MatchStrategy.IGNORE:
                computed_scores[idx] = None
                continue

            val_a = self._norm(row_a.get(mapping.column_a, ""))
            val_b = self._norm(row_b.get(mapping.column_b, ""))

            if not val_a and not val_b:
                # Both missing: score = None, excluded from denominator
                computed_scores[idx] = None
            elif not val_a or not val_b:
                # One missing: score = 0.0, counts in denominator
                computed_scores[idx] = 0.0
                total_weight += mapping.weight
            else:
                # Both present: requires evaluation, counts in denominator
                total_weight += mapping.weight
                attr_eval_plan.append((idx, mapping, val_a, val_b))

        # If total_weight == 0.0, no attributes have values; score is None; cannot meet threshold
        if total_weight == 0.0:
            self.stats["pairs_short_circuited"] += 1
            self.last_pair_short_circuited = True
            return None

        # 2. Check initial theoretical upper bound before any crypto
        remaining_weight = sum(m.weight for _, m, _, _ in attr_eval_plan)
        accumulated_weighted_sum = 0.0  # missing attributes scored 0.0 contribute 0.0

        max_possible_score = round((accumulated_weighted_sum + remaining_weight) / total_weight, 5)
        if max_possible_score < overall_threshold:
            self.stats["pairs_short_circuited"] += 1
            self.stats["attributes_skipped"] += len(attr_eval_plan)
            self.last_pair_short_circuited = True
            return None

        # 3. Order active present attributes for evaluation
        # Prioritize inexpensive, highly-discriminative attributes:
        # EXACT strategies first (O(1) hash equality), sorted by weight descending;
        # then FUZZY strategies, sorted by weight descending.
        attr_eval_plan.sort(
            key=lambda item: (
                0 if item[1].strategy == MatchStrategy.EXACT else 1,
                -item[1].weight,
                item[0],
            )
        )

        # 4. Evaluate attributes sequentially, checking upper bound after each
        for plan_step, (idx, mapping, val_a, val_b) in enumerate(attr_eval_plan):
            if mapping.strategy == MatchStrategy.EXACT:
                alice_prf = self.get_alice_exact_digest(val_a)
                bob_prf = self.get_bob_exact_digest(val_b)
                score = 1.0 if alice_prf == bob_prf else 0.0
            elif mapping.strategy == MatchStrategy.FUZZY:
                alice_prfs, count_a = self.get_alice_fuzzy_digests(val_a)
                bob_prfs, count_b = self.get_bob_fuzzy_digests(val_b)
                total = count_a + count_b
                if total > 0:
                    intersection = len(alice_prfs & bob_prfs)
                    dice = round((2.0 * intersection) / total, 5)
                else:
                    dice = 0.0
                score = dice if dice >= mapping.fuzzy_threshold else 0.0
            else:
                score = None

            computed_scores[idx] = score
            accumulated_weighted_sum += mapping.weight * (score if score is not None else 0.0)
            remaining_weight -= mapping.weight

            # Check if remaining attributes could possibly bring score to threshold
            max_possible_score = round((accumulated_weighted_sum + remaining_weight) / total_weight, 5)
            if max_possible_score < overall_threshold:
                remaining_skipped = len(attr_eval_plan) - (plan_step + 1)
                self.stats["pairs_short_circuited"] += 1
                self.stats["attributes_skipped"] += remaining_skipped
                self.last_pair_short_circuited = True
                return None

        # 5. All required attributes evaluated without short-circuiting
        self.stats["pairs_fully_evaluated"] += 1

        # Build final scores in original mapping order
        scores = [
            AttributeScore(
                column_a=m.column_a,
                column_b=m.column_b,
                strategy=m.strategy,
                score=computed_scores.get(i),
                weight=m.weight,
            )
            for i, m in enumerate(mappings)
        ]
        return scores
