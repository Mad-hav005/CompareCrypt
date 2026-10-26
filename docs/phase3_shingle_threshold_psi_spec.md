# Implementation Specification: CompareCrypt — Privacy-Preserving Shingle Similarity Matching (Phase 3)

**Project:** Secure Private Matching of Similar Data (CompareCrypt)  
**Stage:** Phase 3 Design Specification  
**Construction Name:** CompareCrypt — Privacy-Preserving Shingle Similarity Matching  
**Status:** Pre-Implementation Specification (Revised Under Review)  

---

## 1. Scope and Security Boundary

Before describing the construction, we establish the explicit security boundaries and scope of this implementation:
- **Semi-Honest Model**: Both parties (Alice and Bob) are assumed to be semi-honest (honest-but-curious). They follow the protocol steps faithfully as specified, but may analyze received messages to deduce information.
- **Two-Party Setting**: Designed specifically for two independent parties.
- **No Malicious-Security Guarantee**: This construction does not defend against active malicious attacks (e.g., input tampering, invalid public values, or selective aborts).
- **No Formal Proof Provided**: This is an academic student implementation and engineering prototype; no formal simulation-based security proof is supplied.
- **Controlled Information Leakage**: The protocol intentionally leaks record-level shingle cardinalities ($|S(x_i)|$, $|S(y_j)|$) and individual shingle-overlap information to Alice. It does not provide ideal zero-leakage black-box threshold evaluation.
- **No Claim of State-of-the-Art Fuzzy PSI**: This design does not claim to be a state-of-the-art cryptographic fuzzy PSI primitive. It is an engineering construction bridging exact 2Hash-DH OPRF evaluation with deterministic shingle-overlap thresholding.

---

## 2. Theoretical Foundation & Relationship to Literature

To maintain scientific accuracy, we explicitly clarify our relationship to the academic literature:

- **Literature Foundation for Private Fuzzy/Threshold Matching**:
  - Benny Freedman, Kobbi Nissim, and Benny Pinkas (*"Efficient Private Matching and Set Intersection"*, EUROCRYPT 2004, LNCS 3027, Section 5: *"Fuzzy Matching and Threshold Set Intersection"*) established the theoretical foundation for evaluating set intersections under threshold constraints.
- **OPRF-Based Private Set Operations**:
  - Carmit Hazay and Kobbi Nissim (*"Efficient, Semi-Honest and Malicious Two-Party Computation of Set Intersection and Set Similarity"*, EUROCRYPT 2010 / *Journal of Cryptology* 25(3), 2012) established relevant OPRF-based techniques for private set operations over small and structured domains.
- **The CompareCrypt Construction**:
  - **CompareCrypt implements a simplified semi-honest construction using 2Hash-DH OPRF + cryptographic shingles + overlap-based Dice thresholding.**
  - We do **NOT** claim this is the exact Freedman-Nissim-Pinkas or Hazay-Nissim protocol. Those theoretical constructions use different cryptographic mechanisms, including homomorphic-encryption-based techniques. CompareCrypt instead uses a 2Hash-DH OPRF pipeline for its engineering prototype.


---

## 3. Cryptographic Primitives Used

1. **Prime-Order Cyclic Subgroup ($QR_p$)**:
   - Standardized IETF RFC 3526 2048-bit MODP Group (Group 14).
   - Safe prime $p = 2q + 1$ (2048 bits), where $q$ is also prime.
   - Prime-order subgroup: Quadratic residues $QR_p = \{x^2 \bmod p : x \in \mathbb{Z}_p^*\}$ of prime order $q$.
2. **2Hash-DH Oblivious Pseudorandom Function (OPRF)**:
   - PRF family: $F(k, x) = H_2(x, H_G(x)^k \bmod p)$.
   - Key: Secret scalar $k \in_R [2, q-1]$.
   - Blinding: Secret random scalar $r \in_R [2, q-1]$.
3. **Domain-Separated Cryptographic Hash Functions**:
   - $H_G: \{0, 1\}^* \rightarrow QR_p \setminus \{1\}$: Deterministic hash-and-square mapping arbitrary shingle strings into $QR_p$.
   - $H_2: \{0, 1\}^* \rightarrow \{0, 1\}^{256}$: SHA-256 random oracle with domain separation tags.
4. **CSPRNG**:
   - Python `secrets` module (operating-system entropy via `BCryptGenRandom` on Windows).

*(No LSH, no MinHash, and no Machine Learning are used).*

---

## 4. Metric Distinction: Normalized Levenshtein vs. Sørensen-Dice

We explicitly distinguish the similarity metrics across project phases:
- **Phase 2 Baseline**: Uses **Normalized Levenshtein similarity**, which measures the minimum number of single-character edits (insertions, deletions, substitutions) normalized by maximum string length.
- **Phase 3 Construction**: Uses **$q$-gram Sørensen-Dice similarity**, which measures the normalized overlap cardinality between two sets of unique character bigrams.
- **Non-Equivalence**: These two metrics are **not mathematically equivalent**. While both capture typographical proximity (e.g., both yield high similarity for small substitution typos), they handle token transpositions, word reordering, and repeated characters differently.

---

## 5. Mathematical Definition of the Threshold Matching Condition

### 5.1 String Decomposition into a Set of Unique Shingles
Let $\Sigma$ be the character alphabet. A string $x$ is padded with boundary markers `^` and `$`. It is deterministically decomposed into a **set of unique character $q$-grams (shingles)** of size $q = 2$ (bigrams):
$$S(x) = \{ g : g \text{ is a unique bigram in } \text{"^" } \parallel x \parallel \text{"\$"} \}$$
$S(x)$ is strictly defined as a **set of unique shingles** (duplicates within the same string are deduplicated). Let $|S(x)|$ denote the number of unique shingles in $x$.

### 5.2 Shingle Overlap & Intersection Cardinality
For two strings $x$ (Alice) and $y$ (Bob):
$$\text{Overlap Cardinality: } C(x, y) = |S(x) \cap S(y)|$$

### 5.3 The Sørensen–Dice Matching Condition
Two strings $x$ and $y$ match under a configurable similarity threshold $\tau \in (0.0, 1.0]$ if and only if their unique shingle overlap satisfies:
$$\text{sim}_{\text{Dice}}(x, y) = \frac{2 \cdot |S(x) \cap S(y)|}{|S(x)| + |S(y)|} \ge \tau$$
Equivalently, the absolute shingle intersection threshold is:
$$|S(x) \cap S(y)| \ge \left\lceil \frac{\tau}{2} \cdot (|S(x)| + |S(y)|) \right\rceil$$

### 5.4 Validated Benchmark Example (`"Madhav Kumar"` vs. `"Madhav Kumer"`):
- String $x$: `"Madhav Kumar"` $\implies$ Padded: `"^Madhav Kumar$"`  
  Unique shingles: `{'^M', 'Ma', 'ad', 'dh', 'ha', 'av', 'v ', ' K', 'Ku', 'um', 'ma', 'ar', 'r$'}` $\implies |S(x)| = 13$.
- String $y$: `"Madhav Kumer"` $\implies$ Padded: `"^Madhav Kumer$"`  
  Unique shingles: `{'^M', 'Ma', 'ad', 'dh', 'ha', 'av', 'v ', ' K', 'Ku', 'um', 'me', 'er', 'r$'}` $\implies |S(y)| = 13$.
- Unique Shingle Intersection: $S(x) \cap S(y) = 11$ unique shingles.  
  (Divergent shingles: `{'ar', 'ma'}` vs. `{'er', 'me'}`).
- Intersection cardinality: $|S(x) \cap S(y)| = 11$.
- Sørensen-Dice similarity:
  $$\text{sim}_{\text{Dice}} = \frac{2 \times 11}{13 + 13} = \frac{22}{26} \approx 0.84615\dots$$
- **Threshold Evaluation**:
  - At threshold $\tau = 0.80$: Required overlap $\lceil 0.40 \times 26 \rceil = 11 \implies 11 \ge 11 \implies \mathbf{MATCH}$.
  - At threshold $\tau = 0.90$: Required overlap $\lceil 0.45 \times 26 \rceil = 12 \implies 11 < 12 \implies \mathbf{NO\ MATCH}$.

---

## 6. Exact Protocol Steps Between Alice and Bob

```
Alice (Client)                                                  Bob (Server)
Private Dataset: X = {x_1, ..., x_n}                           Private Dataset: Y = {y_1, ..., y_m}
------------------------------------------------------------------------------------------------------
[Phase 1: Shingling & Blinding]
For each record x_i in X:
  Compute unique shingle set S(x_i)
  For each unique shingle g in S(x_i):
    Pick random scalar r_{i, g} in [2, q-1]
    Blinded point: A_{i, g} = H_G(g)^{r_{i, g}} mod p
  
  Alice sends { (record_id=i, A_{i, g}) } to Bob ------------>
                                                                [Phase 2: OPRF Evaluation & Own Set PRF]
                                                                Bob holds secret key k in [2, q-1]
                                                                
                                                                For each blinded point (i, A_{i, g}):
                                                                  B_{i, g} = (A_{i, g})^k mod p
                                                                  
                                                                For each record y_j in Y:
                                                                  Compute unique shingle set S(y_j)
                                                                  For each unique shingle h in S(y_j):
                                                                    Direct PRF: Z_{j, h} = H_2(h, H_G(h)^k mod p)
                                                                    
                                                                For each y_j, Bob builds digest set:
                                                                  DigestSet(y_j) = { Z_{j, h} : h in S(y_j) }
                                                                  
  <---------------------- Bob sends { (i, B_{i, g}) }
                          and { (record_id=j, |S(y_j)|, DigestSet(y_j)) }

[Phase 3: Unblinding & Shingle Overlap Thresholding (Alice)]
For each record x_i in X:
  For each shingle g in S(x_i):
    Unblind: P_{i, g} = (B_{i, g})^{(r_{i, g})^{-1} mod q} mod p = H_G(g)^k mod p
    Finalize PRF: PRF_Alice(i, g) = H_2(g, P_{i, g})
  Alice PRF Set for record i: PRF_Set(x_i) = { PRF_Alice(i, g) : g in S(x_i) }

  For each Bob record j:
    Compute shingle overlap count:
      Overlap(x_i, y_j) = | PRF_Set(x_i) cap DigestSet(y_j) |
    Compute required threshold:
      T_{i, j} = ceil( (tau / 2) * ( |S(x_i)| + |S(y_j)| ) )
      
    If Overlap(x_i, y_j) >= T_{i, j}:
      Record Match: (x_i, bob_record_id=j, similarity = 2 * Overlap / (|S(x_i)| + |S(y_j)|))
```

---

## 7. What Alice and Bob Send

### 7.1 What Alice Sends to Bob:
- A list of tuples: `(record_id: int, blinded_point: int)`.
- Each point is a 2048-bit integer in $QR_p$ (256 bytes).
- Contains no plaintext strings or raw characters.

### 7.2 What Bob Sends to Alice:
- Evaluated points: `(record_id: int, evaluated_point: int)` (256 bytes per point).
- Grouped record digest sets: `(bob_record_id: int, shingle_count: int, digests: Set[bytes])` (32 bytes per PRF digest).
- Contains no plaintext strings from Bob's records.

---

## 8. What Each Party Learns & Intentional Protocol Leakage

We explicitly document what each party learns, including intentional leakages of this semi-honest prototype:

### What Alice Learns:
- **Matching Records & Scores**: Alice learns which of her records match Bob's records, the corresponding Bob record ID, and the exact Sørensen-Dice similarity score.
- **Controlled Leakage — Individual Shingle-Overlap Information**: Because Bob returns his PRF digests grouped by record $j$, Alice can observe:
  1. The exact number of shared shingles between $x_i$ and $y_j$, even if it falls below threshold $\tau$.
  2. Which of her specific shingles matched a shingle in Bob's record $j$.
- **What Alice Does NOT Learn**:
  - The plaintext string of any record of Bob.
  - The plaintext content of Bob's non-shared shingles.
  - Bob's secret key $k$.

### What Bob Learns:
- The number of records in Alice's dataset ($n$) and the unique shingle count $|S(x_i)|$ for each of Alice's records.
- **What Bob Does NOT Learn**:
  - Any plaintext record of Alice.
  - Which of Alice's records matched.
  - The content of any shingle owned by Alice.

---

## 9. Security Assumptions & Cryptographic Privacy Analysis

### 9.1 Security Assumptions:
1. **Decisional Diffie-Hellman (DDH)**: Assumes DDH is computationally hard in the prime-order subgroup $QR_p$ of the RFC 3526 2048-bit group. Under DDH, Bob's PRF outputs $Z_{j, h}$ are computationally indistinguishable from random strings to any party that does not possess $k$.
2. **Random Oracle Model (ROM)**: SHA-256 with distinct domain separation tags (`COMPARECRYPT_DOMAIN_...`) behaves as a cryptographic random oracle.
3. **Semi-Honest Behavior**: Both parties follow protocol execution faithfully.
4. **CSPRNG**: System entropy source via Python's `secrets` module.

### 9.2 Computational Privacy Analysis:
- **Computational Unlinkability of Blinded Elements**: Blinding scalars $r_{i, g} \in_R [2, q-1]$ provide computational unlinkability and privacy under the discrete logarithm and DDH assumptions in $QR_p$. Without knowledge of $r_{i, g}$, Bob cannot determine which group points correspond to identical shingles across different records or deduce the underlying shingle.
- **Dictionary Resistance Constraints**:
  - An external eavesdropper observing the transcript cannot invert Bob's digests $Z_{j, h} = H_2(h, H_G(h)^k \bmod p)$ without knowledge of Bob's secret key $k$.
  - However, because the domain of character bigrams is small ($\approx 26^2 = 676$ for lowercase English), Bob's key $k$ is the sole cryptographic barrier preventing an offline dictionary attack.
  - Alice, having obtained evaluated group points $H_G(g)^k \bmod p$ for all shingles $g \in S(X)$, possesses the PRF evaluations for her own shingles. She can test if Bob has any shingle that is also in her vocabulary, but cannot test for shingles she does not own without querying Bob.

---

## 10. Required Dependencies & Implementation Feasibility

- **Required Libraries**:
  - Python Standard Library only: `secrets`, `hashlib`, `math`, `typing`, `dataclasses`.
  - Existing framework dependencies: `fastapi`, `pydantic`, `pytest`.
  - Zero external C++ packages, zero custom encryption primitives, zero ML libraries.
- **Implementation Feasibility**:
  - **High implementation feasibility** on standard Windows 11 and Python 3.12.
  - Cryptographic operations use standard modular exponentiation (`pow(base, exp, mod)`) natively supported by Python.

---

## 11. Computational Complexity Analysis

Let $n = |X|$ (Alice dataset size), $m = |Y|$ (Bob dataset size), and let $L$ denote the **average number of unique shingles per record** ($L \approx 12\text{--}18$ for names/emails):

1. **Modular Exponentiations**:
   - Alice: $n \cdot L$ blinding exponentiations $+ n \cdot L$ unblinding exponentiations $= 2 n L$.
   - Bob: $n \cdot L$ evaluations $+ m \cdot L$ direct evaluations $= (n + m) L$.
   - Total group operations: $(3n + m) L$ modular exponentiations over the 2048-bit group.
   - Strictly linear in the number of unique shingles ($O(N \cdot L)$).
2. **Communication Payload**:
   - Alice $\rightarrow$ Bob: $n \cdot L \times 256$ bytes.
   - Bob $\rightarrow$ Alice: $(n \cdot L \times 256) + (m \cdot L \times 32)$ bytes.
3. **Runtime Note**:
   - Specific runtime and throughput figures will be established empirically via actual benchmarks once implemented, rather than using theoretical estimates.

---

## 12. Integration with Existing Baseline Architecture

The construction cleanly integrates into the existing codebase without modifying the exact PSI implementation:

```
backend/app/
├── crypto/
│   ├── crypto_interface.py       # (Unchanged) BaseGroup, BaseOPRFClient, BaseOPRFServer
│   ├── hashing.py                # (Unchanged) Domain-separated SHA-256
│   ├── oprf.py                   # (Unchanged) RFC3526Group14, OPRFClient, OPRFServer
│   ├── psi.py                    # (Unchanged) Exact 2Hash-DH OPRF-PSI baseline
│   └── threshold_psi.py          # [Phase 3] AliceThresholdParty, BobThresholdParty, CryptographicThresholdPSI
├── matching/
│   ├── shingle.py                # [Phase 3] Deterministic unique bigram tokenizer & Dice threshold math
│   ├── exact_match.py            # (Unchanged) Exact PSI matcher
│   └── fuzzy_match.py            # (Unchanged) Plaintext Levenshtein baseline
├── models/
│   └── schemas.py                # Adds ThresholdMatchRequest and ThresholdMatchResponse
└── api/
    └── routes.py                 # Adds POST /api/matching/threshold-crypto
```

---

## 13. Minimal Implementation Plan

When approved for coding, implementation will proceed in three testable steps:
1. **Module 1 (`matching/shingle.py`)**:
   - String normalization, boundary padding (`^`, `$`), and unique bigram extraction.
   - Sørensen-Dice similarity and absolute threshold calculation functions.
2. **Module 2 (`crypto/threshold_psi.py`)**:
   - `AliceThresholdParty`: Generates unique shingle sets, blinds each shingle, and computes unblinded PRF digests.
   - `BobThresholdParty`: Evaluates Alice's blinded shingles and computes direct PRF digests for Bob's unique shingles.
   - `CryptographicThresholdPSI`: Coordinates the two-party exchange and evaluates the shingle threshold condition.
3. **Module 3 (API & Service Layer)**:
   - Extend `private_matching_service.py` with `perform_threshold_matching`.
   - Add endpoint `POST /api/matching/threshold-crypto`.

---

## 14. Test Plan (`tests/test_threshold_psi.py`)

1. **`test_shingle_generation`**: Verify boundary markers and deduplication of repeated bigrams into a set.
2. **`test_dice_similarity_exact_and_typo`**: Verify exact match yields $1.0$; `"Madhav Kumar"` vs. `"Madhav Kumer"` yields $11/13 \approx 0.84615$.
3. **`test_threshold_psi_identical_records`**: Verifies exact matching produces similarity $1.0$.
4. **`test_threshold_psi_name_typo_match`**: Verifies `"Madhav Kumar"` and `"Madhav Kumer"` match at $\tau = 0.80$.
5. **`test_threshold_psi_threshold_boundary`**: Verifies `"Madhav Kumar"` and `"Madhav Kumer"` reject at $\tau = 0.90$.
6. **`test_threshold_psi_dissimilar_records`**: Verifies `"Rahul Sharma"` vs. `"Alice Brown"` produce zero matches.
7. **`test_threshold_psi_privacy_boundaries`**: Verifies transmitted payloads contain only 2048-bit integers and 32-byte hashes (no raw strings).
8. **`test_threshold_psi_empty_datasets`**: Verifies graceful handling of empty inputs.

---

## 15. Benchmark Plan (`benchmarks/benchmark_tri_layer.py`)

Direct 3-way comparative benchmark evaluating across dataset sizes $N = 10, 50$:

| Dimension | 1. Plaintext Fuzzy Baseline | 2. Exact OPRF-PSI Baseline | 3. Cryptographic Threshold-PSI |
|---|---|---|---|
| **Cryptographic Guarantee** | None (Plaintext simulation) | Computational privacy under DDH assumption (semi-honest) | Computational privacy under stated assumptions (semi-honest) with controlled shingle-count and overlap leakage |
| **Matching Metric** | Normalized Levenshtein | Exact String Equality | Unique Bigram Sørensen-Dice |
| **Runtime (seconds)** | Empirical measurement | Empirical measurement | Empirical measurement |
| **Communication (KB)** | 0 KB (Local) | Empirical measurement | Empirical measurement |
| **Peak Memory (KB)** | Empirical measurement | Empirical measurement | Empirical measurement |
| **Precision & Recall** | Evaluated on typo dataset | Evaluated on typo dataset | Evaluated on typo dataset |


---

## 16. Summary of Corrections Applied

1. **Attribution & Relationship to Literature**: Clarified that Freedman et al. (2004) and Hazay & Nissim (2010) provide theoretical foundations; CompareCrypt implements a simplified semi-honest construction using 2Hash-DH OPRF + cryptographic shingles + Dice thresholding.
2. **Set vs. Multiset**: $S(x)$ is strictly defined as a set of unique $q$-grams.
3. **Validated Example Maintained**: Kept `"Madhav Kumar"` vs. `"Madhav Kumer"` ($|S(x)|=13, |S(y)|=13$, intersection $= 11$, $\text{Dice} \approx 0.84615$, match at $0.80$, non-match at $0.90$).
4. **Controlled Information Leakage Stated**: Explicitly documented that Alice receives grouped PRF digests and observes individual shingle-overlap counts.
5. **Privacy Qualification**: Replaced "information-theoretic secrecy" with computational unlinkability based on group and OPRF assumptions.
6. **Dictionary Resistance Qualification**: Stated precisely what an external observer can and cannot invert given Bob's secret key $k$.
7. **Feasibility Qualification**: Replaced "100% Guaranteed" with "High implementation feasibility".
8. **Runtime Claims Removed**: Eliminated unbenchmarked runtime estimates.
9. **Parameter $L$ Redefined**: Defined $L$ as the average number of unique shingles per record.
10. **Metric Non-Equivalence Stated**: Clarified that Phase 2 Normalized Levenshtein and Phase 3 Sørensen-Dice are distinct metrics.
11. **Scope and Security Boundary Added**: Added Section 1 detailing semi-honest model, absence of malicious guarantees, and student prototype status.
12. **Construction Renamed**: Renamed throughout to *"CompareCrypt — Privacy-Preserving Shingle Similarity Matching"*.
