# Technical Design & Critical Review: Phase 3 — Fuzzy Matching & Cryptographic Private Set Intersection

**Project:** Secure Private Matching of Similar Data (FuzzyCrypt)  
**Document Purpose:** Architectural Investigation, Mathematical Analysis, and Security Critique of Phase 3  
**Status:** Revised Technical Assessment (Pre-Implementation Review)  

---

## 1. Context & Architectural Boundary

In Phase 1 and Phase 2, the following modules were established and verified:
1. **Exact 2Hash-DH OPRF-PSI**: A cryptographically sound Private Set Intersection protocol operating over the RFC 3526 2048-bit MODP safe-prime group ($QR_p$) under the Decisional Diffie-Hellman (DDH) assumption.
2. **Deterministic Fuzzy Matching Baseline**: A pairwise string comparison baseline using normalized Levenshtein distance:
   $$\text{sim}_{\text{Lev}}(a, b) = 1.0 - \frac{\text{levenshtein}(a, b)}{\max(\text{len}(a), \text{len}(b))}$$
   governed by `ThresholdPolicy` ($\tau \in [0.0, 1.0]$).

### The Essential Clarification:
The Phase 2 fuzzy matching baseline was developed as an isolated functional prototype simulating two parties in memory. **It does NOT provide cryptographic privacy across a distributed boundary.** If Alice and Bob resided on separate machines, calculating pairwise Levenshtein distance would require either:
- Exposing plaintext records to one another, or
- Running generic secure two-party computation (2PC) / Garbled Circuits over the dynamic programming edit distance matrix.

The objective of this document is to critically assess how fuzzy matching can interface with cryptographic PSI, identify what is realistically achievable in this project, and correct prior mathematical and privacy claims.

---

## 2. Distinction: "Cryptographic Fuzzy-PSI" vs. "LSH-Based Candidate Generation + Exact PSI"

A rigorous academic distinction must be drawn between two fundamentally different concepts:

```
+-------------------------------------------------------------------------------------------------------+
| True Cryptographic Fuzzy-PSI (Threshold PSI)                                                          |
| - Mathematical distance metric dist(x, y) <= tau is computed ENTIRELY inside the cryptographic domain |
| - Cryptographic primitives (e.g., Fuzzy Vaults, Additive Homomorphic Vectors, Functional Encryption)   |
| - Zero structural leakage: Neither party learns intermediate sub-tokens or frequency distributions    |
+-------------------------------------------------------------------------------------------------------+
                                                  vs.
+-------------------------------------------------------------------------------------------------------+
| Hybrid Pipeline: LSH / Shingle Projection + Exact OPRF-PSI (PPRL Approach)                            |
| - Deterministic feature decomposition (q-grams, MinHash, Bloom filter sketches) in plaintext domain   |
| - Cryptographic exact PSI is executed merely over the resulting deterministic tokens / band hashes    |
| - Approximate matching occurs via hash collisions, NOT ciphertext-level distance arithmetic           |
+-------------------------------------------------------------------------------------------------------+
```

Any construction using Locality-Sensitive Hashing (LSH) or $q$-gram shingling evaluated over 2Hash-DH OPRF is **not** a novel "cryptographic fuzzy PSI primitive." It is an established **Privacy-Preserving Record Linkage (PPRL) candidate filtering pipeline** that uses exact cryptographic PSI as a sub-routine. 

We must not claim this construction evaluates fuzzy distances cryptographically.

---

## 3. Mathematical Correction of LSH Collision Probabilities

The standard collision probability for MinHash Locality-Sensitive Hashing with $B$ bands and $R$ rows per band ($K = B \times R$ total hash functions) over Jaccard similarity $s \in [0, 1]$ is:
$$P(\text{collision}) = 1 - (1 - s^R)^B$$

### Error in the Initial Claim:
The initial proposal stated that $B = 16, R = 2$ yields $>90\%$ collision for $s \ge 0.85$ and $<5\%$ collision for $s < 0.50$. **This claim is mathematically false.**

At $s = 0.50$:
$$s^R = 0.50^2 = 0.25$$
$$1 - s^R = 0.75$$
$$(1 - s^R)^B = 0.75^{16} \approx 0.01002$$
$$P(\text{collision}) = 1 - 0.01002 \approx 0.98998 \quad (\mathbf{99.0\%})$$

Even at low similarity $s = 0.20$:
$$P(\text{collision}) = 1 - (1 - 0.20^2)^{16} = 1 - (0.96)^{16} \approx 1 - 0.5204 \approx \mathbf{48.0\%}$$

With $B=16, R=2$, the filter exhibits catastrophic false positives, causing almost every record to collide regardless of similarity.

### Rigorous Parameter Analysis:
The inflection threshold $t$ (where $P = 0.50$) is approximately:
$$t \approx \left(\frac{1}{B}\right)^{1/R}$$

To achieve true discrimination (e.g., $P \le 5\%$ at $s = 0.50$ and $P \ge 90\%$ at $s = 0.85$), $R$ must be substantially larger:

| Configuration ($B, R$) | Inflection $t$ | $P(\text{collision})$ at $s = 0.20$ | $P(\text{collision})$ at $s = 0.50$ | $P(\text{collision})$ at $s = 0.85$ | Total Hashes $K = B \cdot R$ |
|---|---|---|---|---|---|
| $B = 16, R = 2$ *(Rejected)* | $0.25$ | $48.0\%$ | **$99.0\%$** *(Severe FP)* | $99.9\%$ | 32 |
| $B = 10, R = 5$ | $0.63$ | $0.3\%$ | $27.3\%$ | $99.1\%$ | 50 |
| $B = 15, R = 6$ | $0.64$ | $0.1\%$ | $21.0\%$ | $99.8\%$ | 90 |
| $B = 20, R = 8$ | $0.69$ | $< 0.01\%$ | **$7.5\%$** | **$99.8\%$** | 160 |
| $B = 25, R = 10$ | $0.72$ | $< 0.001\%$ | **$2.4\%$** | **$99.1\%$** | 250 |

To achieve $< 5\%$ collision at $s=0.50$, the system would require at least $B=25, R=10$ ($K = 250$ permutations), generating $25$ band tokens per record that must each be exponentiated in the 2048-bit group.

---

## 4. Metric Mismatch: Jaccard vs. Normalized Levenshtein

MinHash LSH is mathematically bound to the **Jaccard similarity of sets**:
$$J(A, B) = \frac{|A \cap B|}{|A \cup B|}$$

However, the project target metric is **Normalized Levenshtein (edit) distance**. These two metrics diverge significantly:

1. **Short String Sensitivity**:
   For short strings like names (e.g., `"John"` $\rightarrow$ bigrams `{"_J", "Jo", "oh", "hn", "n_"}`: 5 bigrams total), a single character substitution changes or destroys up to 3 bigrams. 
   The Jaccard similarity drops from $1.0$ down to $2 / 8 = 0.25$, whereas normalized Levenshtein similarity is $1.0 - 1/4 = 0.75$. MinHash on bigrams would miss this match completely (False Negative).
2. **Anagram / Transposition Invariance**:
   Strings with identical character bags in different orders (e.g., `"tar"` vs `"rat"`, or inverted first/last names) have identical or high $q$-gram Jaccard overlap, but high Levenshtein edit distance (False Positive).
3. **Conclusion**: MinHash on $q$-grams cannot faithfully enforce a precise Levenshtein distance threshold. It operates strictly as a surrogate heuristic.

---

## 5. Critical Privacy & Information Leakage Analysis

If a hybrid LSH-banded OPRF-PSI scheme were deployed, it would exhibit several critical information leaks:

### 1. Token Frequency & Syllable Distribution Leakage
- Deterministic $q$-grams and LSH band tokens have low entropy compared to full records.
- In English names, common prefixes/suffixes (e.g., `"John"`, `"Smith"`, `"Kumar"`) produce identical band tokens across multiple individuals.
- When Bob evaluates and returns PRF digests $\{Z_{j, b}\}$, Alice observes which tokens repeat and their exact frequency distribution in Bob's dataset.
- In an untrusted setting, this enables frequency-analysis and reconstruction attacks against Bob's private dataset.

### 2. Multi-Band Collisions Reveal Approximate Distance
- If Alice generates $B = 20$ band tokens for a record $x_i$, and tests them against Bob's evaluated digests, she counts how many bands collided ($c \in [0, B]$).
- A single exact match collides in all $B$ bands ($c = B$).
- An approximate match collides in some subset of bands ($1 \le c < B$).
- Alice directly learns an estimate of Bob's similarity score for non-exact records, rather than a strictly oblivious binary decision.

### 3. Client Dataset Size & Volume Leakage
- If Alice sends $N \cdot B$ blinded tokens, Bob learns the exact token volume.
- If Alice deduplicates band tokens before blinding, Bob learns the uniqueness ratio of Alice's dataset, leaking structural properties about her population.

### 4. Offline Dictionary / Precomputation Attacks on Low-Entropy Tokens
- Full strings (e.g., `"Madhav Kumar, SSN: 1234, DOB: 1990"`) have high entropy.
- Sub-tokens (e.g., 2-character shingles like `"Ma"`, `"ad"`, `"dh"`) have extremely small domains ($26^2 = 676$ possible combinations).
- If individual shingles were ever passed to the OPRF, the client or server could easily build an offline dictionary of all 676 evaluations and invert the inputs.
- While band hashes combine $R$ rows ($T_b = H(\text{shingle}_1 \parallel \dots \parallel \text{shingle}_R)$), for short strings the effective entropy of the band remains low enough to be vulnerable to targeted precomputation if the domain is known.

---

## 6. Evaluation of Cryptographic Alternatives

| Alternative | Mechanism | Cryptographic Privacy | Feasibility in Python / Final-Year Scope | Limitations |
|---|---|---|---|---|
| **1. Hybrid LSH + 2Hash-DH OPRF-PSI** | MinHash band tokens evaluated via exact OPRF-PSI | **Partial / Heuristic** (Leaks collision frequencies, token counts, and Jaccard approximations) | **High** (Reuses existing OPRF implementation; low lines of code) | Metric mismatch with Levenshtein; high False Positives unless $K \ge 150$; not a true Fuzzy-PSI primitive. |
| **2. Additive Homomorphic Encryption (Paillier AHE)** | Encode strings as character frequency vectors; compute encrypted inner product $\text{Enc}(\langle u, v \rangle)$ | **High** (Cryptographically hides vectors; only reveals threshold decision via blinded decryption) | **Moderate** (Can use `phe` library in Python; clean math) | Pairwise comparison scales as $O(N \cdot M)$ encryptions; slow for $N > 100$ in pure Python; requires introducing Paillier alongside OPRF. |
| **3. Garbled Circuits (2PC Edit Distance)** | Evaluate standard Wagner-Fischer dynamic programming matrix inside Yao's Garbled Circuit | **Highest** (Exact Levenshtein distance computed with zero leakage beyond match decision) | **Very Low** (Requires C++ frameworks like ABY/EMP; extremely complex to build safely from scratch) | Out of scope for a pure Python lightweight architecture. |
| **4. Cryptographic Shingle Threshold PSI (Bost et al. / Hazay-Nissim)** | Decompose strings into $q$-grams; evaluate set intersection cardinality $|S_A \cap S_B| \ge T$ using homomorphic polynomials or garbled Bloom filters | **High** (Established cryptographic formulation of Fuzzy-PSI) | **Moderate to High** | Complex polynomial interpolation over finite fields; computationally intensive. |

---

## 7. Explicit Recommendations for Next Steps

1. **Do NOT claim LSH-PSI is a true "Cryptographic Fuzzy-PSI" primitive.**
   If an LSH-based approach is implemented, it must be accurately documented as:
   *"A Privacy-Preserving Record Linkage (PPRL) candidate filtering baseline using MinHash band tokens over exact OPRF-PSI."*
2. **Acknowledge the Tradeoffs Transparently in Academic Documentation:**
   - Jaccard approximation vs. true edit distance.
   - Frequency leakage of repeating band tokens.
   - Probabilistic false positive / false negative curve based on corrected $(B, R)$ parameters.
3. **Preserve the Architectural Baseline:**
   The exact 2Hash-DH OPRF-PSI implementation remains our gold-standard exact cryptographic baseline. Any fuzzy matching extension must be kept modularly distinct so its performance and leakage profile can be explicitly benchmarked against the exact baseline.
