# Secure Private Matching of Similar Data (CompareCrypt)

## 1. Project Title
**Secure Private Matching of Similar Data (CompareCrypt)**

---

## 2. Problem Statement
In many data-sharing scenarios, two independent organizations or parties (Alice and Bob) hold sensitive private datasets (e.g., customer registries, patient identity lists, fraud watchlists) and need to identify common or approximately matching records.

A conventional comparison requires centralizing records into a third party or exchanging plaintext data across the network. However, regulatory constraints and privacy concerns strictly forbid disclosing non-matching private records.

The goal of this system is to enable Alice and Bob to determine which records in their private datasets match or are sufficiently similar **without directly revealing their non-matching private records to each other**.

---

## 3. Scope & Security Boundary
- **Adversary Model**: Semi-Honest (honest-but-curious). Both parties follow protocol specifications faithfully but inspect received messages.
- **Two-Party Setting**: Designed specifically for two independent parties (Alice as Client, Bob as Server).
- **No Malicious Guarantees**: Does not protect against active malicious deviations (e.g., input tampering, selective aborts).
- **No Claim of State-of-the-Art Fuzzy PSI**: Implements a simplified semi-honest engineering prototype combining 2Hash-DH OPRF evaluation with deterministic shingle-set Dice thresholding.
- **Controlled Information Leakage**: The threshold protocol intentionally leaks record-level unique shingle counts ($|S(x_i)|$, $|S(y_j)|$) and individual shingle-overlap counts to Alice.

---

## 4. Tri-Layer Architecture & How Matching Works

CompareCrypt is built around three modular layers:

```
+---------------------------------------------------------------------------------------------------------+
|                                   CompareCrypt Tri-Layer Architecture                                   |
+---------------------------------------------------------------------------------------------------------+
| Layer 1: Plaintext Fuzzy Baseline     | Pairwise Normalized Levenshtein string distance                 |
| Layer 2: Exact Cryptographic PSI      | 2Hash-DH OPRF over RFC 3526 2048-bit MODP Group (Group 14)     |
| Layer 3: Privacy-Preserving Fuzzy-PSI | CompareCrypt — Privacy-Preserving Shingle Similarity Matching   |
+---------------------------------------------------------------------------------------------------------+
```

### Layer 1: Plaintext Fuzzy Baseline
Computes deterministic normalized Levenshtein string similarity across simulated party boundaries:
$$\text{sim}_{\text{Lev}}(a, b) = 1.0 - \frac{\text{levenshtein}(a, b)}{\max(\text{len}(a), \text{len}(b))}$$
Matched if $\text{sim}_{\text{Lev}}(a, b) \ge \tau$.

### Layer 2: Exact Cryptographic PSI (2Hash-DH OPRF)
Computes exact set intersection over blinded representations in the RFC 3526 2048-bit MODP safe prime group ($QR_p$):
1. **Alice** blinds each item: $A_i = H_G(x_i)^{r_i} \bmod p$.
2. **Bob** evaluates Alice's points: $B_i = (A_i)^k \bmod p$, and directly evaluates his own items: $Z_j = H_2(y_j, H_G(y_j)^k \bmod p)$.
3. **Alice** unblinds $P_i = (B_i)^{r_i^{-1}} \bmod p = H_G(x_i)^k \bmod p$, finalizes $Y_i = H_2(x_i, P_i)$, and computes the intersection against $\{Z_j\}$.

### Layer 3: CompareCrypt — Privacy-Preserving Shingle Similarity Matching (Phase 3)
1. **Deterministic Unique Bigrams**: Each string is padded (`^`, `$`) and decomposed into a set of unique character 2-grams $S(x)$.
2. **OPRF Shingle Evaluation**:
   - Alice blinds every unique shingle with an ephemeral random scalar $r_{i, g} \in_R [2, q-1]$ and sends tagged group points to Bob.
   - Bob evaluates Alice's points with his secret key $k$, and computes direct PRF digests $Z_{j, h} = H_2(h, H_G(h)^k \bmod p)$ for his own unique shingles.
   - Bob returns the evaluated points and grouped digest sets $\{ (j, |S(y_j)|, \text{DigestSet}(y_j)) \}$ to Alice.
3. **Sørensen-Dice Thresholding**:
   - Alice unblinds her points to derive the matching PRF digests.
   - Alice counts the unique shingle intersection against Bob's digest sets: $C(x_i, y_j) = |S(x_i) \cap S(y_j)|$.
   - Evaluates the Sørensen–Dice threshold condition:
     $$\text{sim}_{\text{Dice}}(x_i, y_j) = \frac{2 \cdot C(x_i, y_j)}{|S(x_i)| + |S(y_j)|} \ge \tau$$
   - Records meeting the threshold are identified with their Dice similarity and intersection count.

---

## 5. Metric Distinction: Levenshtein vs. Sørensen-Dice
- **Phase 2 Baseline**: Uses **Normalized Levenshtein similarity** (character edit operations).
- **Phase 3 Construction**: Uses **$q$-gram Sørensen-Dice similarity** (unique bigram overlap).
- These metrics are mathematically distinct. While both capture typographical proximity (e.g., `"Madhav Kumar"` $\leftrightarrow$ `"Madhav Kumer"`), they handle character transpositions and token ordering differently.

---

## 6. Cryptographic Components
- **Cryptographic Group**: Standardized RFC 3526 2048-bit MODP Group (Group 14).
  - Safe prime $p = 2q + 1$ (2048 bits), prime order $q = (p-1)/2$.
  - Prime-order subgroup: Quadratic Residues $QR_p = \{x^2 \bmod p : x \in \mathbb{Z}_p^*\}$.
- **Group Mapping $H_G$**: Deterministic hash-and-square mapping into $QR_p \setminus \{1, p-1\}$.
- **Randomness Source**: Python `secrets` module (operating-system CSPRNG).
- **Hash Function & Domain Separation**: SHA-256 with explicit domain separation tags (`COMPARECRYPT_DOMAIN_...`).

---

## 7. Project Architecture

```
CompareCrypt/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py                 # FastAPI endpoints (/exact, /fuzzy, /threshold-crypto)
│   │   ├── core/
│   │   │   └── config.py                 # Group & application settings
│   │   ├── crypto/
│   │   │   ├── crypto_interface.py       # ABC interfaces (BaseGroup, BaseOPRFClient, etc.)
│   │   │   ├── hashing.py                # Domain-separated SHA-256
│   │   │   ├── oprf.py                   # RFC 3526 Group 14, OPRFClient, OPRFServer
│   │   │   ├── psi.py                    # Exact 2Hash-DH OPRF-PSI baseline
│   │   │   └── threshold_psi.py          # Phase 3 Privacy-Preserving Shingle Threshold PSI
│   │   ├── matching/
│   │   │   ├── shingle.py                # Unique bigram extraction & Dice math
│   │   │   ├── exact_match.py            # Exact matching orchestrator
│   │   │   ├── fuzzy_match.py            # Plaintext Levenshtein baseline
│   │   │   └── similarity.py             # Levenshtein distance & policy interfaces
│   │   ├── models/
│   │   │   └── schemas.py                # Pydantic schemas for all three layers
│   │   ├── services/
│   │   │   └── private_matching_service.py # Two-party coordination service
│   │   ├── utils/
│   │   │   └── normalization.py          # String canonicalization utilities
│   │   └── main.py                       # FastAPI application entrypoint
│   └── requirements.txt
├── tests/
│   ├── test_api.py                       # FastAPI endpoint test suite (all endpoints)
│   ├── test_crypto.py                    # RFC 3526 group, OPRF roundtrip, and hashing tests
│   ├── test_exact_matching.py            # Overlapping, disjoint, and canonical PSI tests
│   ├── test_fuzzy_matching.py            # Levenshtein matching and threshold tests
│   ├── test_privacy.py                   # Exact PSI cryptographic privacy tests
│   └── test_threshold_psi.py             # Phase 3 Shingle Threshold PSI tests
├── benchmarks/
│   ├── benchmark_exact.py                # Exact PSI benchmark suite
│   ├── benchmark_comparison.py           # Exact PSI vs Plaintext Fuzzy comparison
│   └── benchmark_tri_layer.py            # Direct 3-way comparative benchmark suite
├── docs/
│   ├── phase3_shingle_threshold_psi_spec.md # Technical specification
│   └── technical_design_phase3.md        # Technical review and LSH analysis
├── requirements.txt
└── README.md
```

---

## 8. Installation

```bash
python -m pip install -r requirements.txt
```

---

## 9. Running the Backend

```bash
# On Windows PowerShell
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API documentation: `http://127.0.0.1:8000/docs`

### API Endpoints

#### 1. Exact Private Matching (`POST /api/matching/exact`)
```bash
curl -X POST "http://127.0.0.1:8000/api/matching/exact" \
     -H "Content-Type: application/json" \
     -d '{
       "alice_data": ["alice@example.com", "bob@example.com", "charlie@example.com"],
       "bob_data": ["bob@example.com", "charlie@example.com", "david@example.com"],
       "normalize": true
     }'
```

#### 2. Deterministic Fuzzy Matching Baseline (`POST /api/matching/fuzzy`)
```bash
curl -X POST "http://127.0.0.1:8000/api/matching/fuzzy" \
     -H "Content-Type: application/json" \
     -d '{
       "alice_data": ["Madhav Kumar", "John Smith", "Rahul Sharma"],
       "bob_data": ["Madhav Kumer", "Alice Brown", "John Smith"],
       "threshold": 0.85
     }'
```

#### 3. Cryptographic Shingle Threshold Matching (`POST /api/matching/threshold-crypto`)
```bash
curl -X POST "http://127.0.0.1:8000/api/matching/threshold-crypto" \
     -H "Content-Type: application/json" \
     -d '{
       "alice_data": ["Madhav Kumar", "John Smith", "Rahul Sharma"],
       "bob_data": ["Madhav Kumer", "Alice Brown", "John Smith"],
       "threshold": 0.80
     }'
```

Response:
```json
{
  "matches": [
    {
      "alice_record_id": 0,
      "bob_record_id": 0,
      "alice_record": "Madhav Kumar",
      "bob_record": "Madhav Kumer",
      "intersection_count": 11,
      "dice_similarity": 0.84615,
      "threshold": 0.8,
      "match_decision": true
    },
    {
      "alice_record_id": 1,
      "bob_record_id": 2,
      "alice_record": "John Smith",
      "bob_record": "John Smith",
      "intersection_count": 11,
      "dice_similarity": 1.0,
      "threshold": 0.8,
      "match_decision": true
    }
  ],
  "match_count": 2,
  "alice_dataset_size": 3,
  "bob_dataset_size": 3,
  "threshold": 0.8,
  "protocol_name": "CompareCrypt — Privacy-Preserving Shingle Similarity Matching (2Hash-DH OPRF)"
}
```
*(Notice that at threshold 0.80, both "John Smith" and "Madhav Kumar" match. At threshold 0.90, the typo is rejected. Non-matching records "Rahul Sharma" and "Alice Brown" are strictly excluded).*

---

## 10. Running Tests

Execute the full suite of **44 tests**:

```bash
$env:PYTHONPATH="backend"
python -m pytest tests -v
```

All 44 test cases cover:
- Group mathematics, generator orders, and quadratic residue membership.
- OPRF blinding, unblinding roundtrip consistency, and distinctness under distinct keys/inputs.
- Exact PSI scenarios (overlapping, disjoint, identical, empty sets).
- Plaintext Levenshtein baseline tests and threshold policies.
- Phase 3 unique bigram extraction, deduplication, and Sørensen-Dice calculations.
- Phase 3 typo matching (`Madhav Kumar` vs `Madhav Kumer` matches at 0.80, rejects at 0.90).
- Phase 3 payload privacy boundaries (zero plaintext in transit, ephemeral factor cleanup).
- API integration tests across all three endpoints (including HTTP 422 invalid threshold validation).

---

## 11. Empirical Tri-Layer Comparative Benchmark Results

Generated by running `python benchmarks/benchmark_tri_layer.py` on Windows 11 (Python 3.12, RFC 3526 2048-bit MODP Group).

> **Profiling Note on `tracemalloc` Overhead**:
> Runtime measurements below include `tracemalloc` overhead because peak heap memory consumption is captured concurrently as a required benchmark metric. A separate micro-calibration of the memory profiler measured that active `tracemalloc` tracing introduces approximately **+23% to +30% CPU profiling overhead** on modular exponentiations and heap allocations. This is reported separately as profiling overhead and is not applied as a post-hoc correction factor to raw timings. Modular exponentiation was observed to dominate runtime across all phases.

### Benchmark Results ($N = 10$ and $N = 50$)

| Dataset Size $N$ | Metric | 1. Plaintext Fuzzy Baseline | 2. Exact OPRF-PSI Baseline | 3. Cryptographic Threshold-PSI |
|:---:|:---|:---:|:---:|:---:|
| **10** | Matching Metric | Normalized Levenshtein | Exact Equality | Unique Bigram Sørensen-Dice |
| | Cryptographic Guarantee | None (Plaintext simulation) | Computational (DDH in $QR_p$) | Computational (DDH over Shingle OPRF) |
| | **Runtime (Total)** | **0.0290 s** | **1.2158 s** | **17.6375 s** |
| | **Per-Record Runtime** | 2.90 ms | 121.58 ms | 1763.75 ms |
| | **Discovered Matches** | 4 (exact + typos) | 2 (exact only) | 4 (exact + typos) |
| | **Communication Payload** | 0.00 KB | 5.31 KB | 89.19 KB |
| | **Peak Memory** | 7.34 KB | 19.33 KB | 249.88 KB |
| | **Precision** | 1.0000 | 1.0000 | 1.0000 |
| | **Recall** | 1.0000 | 1.0000 | 1.0000 |
| **50** | Matching Metric | Normalized Levenshtein | Exact Equality | Unique Bigram Sørensen-Dice |
| | Cryptographic Guarantee | None (Plaintext simulation) | Computational (DDH in $QR_p$) | Computational (DDH over Shingle OPRF) |
| | **Runtime (Total)** | **0.6845 s** | **5.7585 s** | **86.3936 s** |
| | **Per-Record Runtime** | 13.69 ms | 115.17 ms | 1727.87 ms |
| | **Discovered Matches** | 20 (exact + typos) | 10 (exact only) | 20 (exact + typos) |
| | **Communication Payload** | 0.00 KB | 26.56 KB | 470.26 KB |
| | **Peak Memory** | 13.11 KB | 60.53 KB | 1298.94 KB |
| | **Precision** | 1.0000 | 1.0000 | 1.0000 |
| | **Recall** | 1.0000 | 1.0000 | 1.0000 |

### Phase Timing Breakdown (Cryptographic Shingle Threshold-PSI)

Modular exponentiation was observed to dominate protocol runtime. Bob's Phase 2 is the primary computational bottleneck because Bob evaluates Alice's blinded shingles and independently derives PRF digests for his own shingles:

* **$N = 10$ ($17.64$s Total):**
  * Phase 1 (Alice Shingle Blinding, 166 shingles): `4.74s` (26.9%)
  * Phase 2 (Bob Evaluation & Digest, 320 exponentiations): `8.85s` (50.2%)
  * Phase 3 (Alice Unblinding & Threshold Intersection): `4.05s` (22.9%)
* **$N = 50$ ($86.39$s Total):**
  * Phase 1 (Alice Shingle Blinding, 875 shingles): `22.87s` (26.5%)
  * Phase 2 (Bob Evaluation & Digest, 1,692 exponentiations): `40.52s` (46.9%)
  * Phase 3 (Alice Unblinding & Threshold Intersection): `23.00s` (26.6%)


---

## 12. Security Assumptions
1. **Semi-Honest Adversary Model**: Both parties execute the agreed protocol steps without deviation.
2. **Decisional Diffie-Hellman (DDH) Assumption**: Holds in the quadratic residue subgroup $QR_p$ of the RFC 3526 2048-bit safe prime MODP group.
3. **Random Oracle Model (ROM)**: SHA-256 with distinct domain separation tags behaves as a cryptographic random oracle for $H_G$ and $H_2$.
4. **CSPRNG**: System entropy source via Python's `secrets` module.

---

## 13. Current Limitations & Research Direction
- **Controlled Leakage**: The shingle threshold construction reveals individual shingle-overlap counts and unique shingle lengths to Alice.
- **Computation**: 2048-bit modular exponentiations on bigram sets scale with the number of unique shingles. Future optimizations could evaluate elliptic curve groups (e.g. Curve25519/Ristretto255) for higher throughput.
- **Future Research Direction**: Investigating dynamic adjustment of similarity thresholds and privacy bounds (Adaptive Privacy-Utility Policies) via the modular matching policy interface.

---

## 14. Multi-Attribute Database Entity Resolution

CompareCrypt includes a full **Privacy-Preserving Multi-Attribute Database Entity Resolution** engine:

- **Heterogeneous Schema Ingestion**: Upload multi-column CSV or Excel files with disparate column names, types, and counts.
- **Configurable Attribute Mapping**: Interactive mapping connecting Party A and Party B attributes with custom match strategies (`fuzzy`, `exact`, `ignore`).
- **Privacy-Preserving Blocking**: Multi-token inverted-index blocking (word tokens + character bigrams) to avoid $O(N \times M)$ pairwise cryptographic computations.
- **Weighted Multi-Attribute Scoring**: $\text{Score} = \frac{\sum w_i \cdot s_i}{\sum w_i}$, supporting individual fuzzy thresholds and composite match filtering.
- **Asynchronous Execution & Streaming Progress**: Non-blocking background job execution with stage-by-stage phase tracking (parsing, blocking, crypto matching, scoring).
- **Interactive UI & CSV Export**: Inspect detailed match breakdowns per attribute and export merged resolved records directly.
