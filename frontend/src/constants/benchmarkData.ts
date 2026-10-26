/**
 * Historical empirical benchmark metrics from project documentation.
 * Verified on Windows 11 with RFC 3526 2048-bit MODP Group.
 */

export interface ParadigmMetrics {
  name: string;
  shortName: string;
  runtimeSec: number;
  perRecordMs: number;
  commKb: number;
  peakMemoryKb: number;
  matches: number;
  precision: number;
  recall: number;
  color: string;
  description: string;
}

export interface BenchmarkDataSet {
  n: number;
  label: string;
  metrics: {
    plaintextFuzzy: ParadigmMetrics;
    exactPsi: ParadigmMetrics;
    fuzzyCrypt: ParadigmMetrics;
  };
}

export const EMPIRICAL_BENCHMARK_DATA: Record<10 | 50, BenchmarkDataSet> = {
  10: {
    n: 10,
    label: "N = 10 Records per party",
    metrics: {
      plaintextFuzzy: {
        name: "Plaintext Fuzzy (Normalized Levenshtein)",
        shortName: "Plaintext Fuzzy",
        runtimeSec: 0.0290,
        perRecordMs: 2.90,
        commKb: 0.00,
        peakMemoryKb: 7.34,
        matches: 4,
        precision: 1.0000,
        recall: 1.0000,
        color: "#64748b", // slate
        description: "In-memory string edit distance with zero cryptographic privacy.",
      },
      exactPsi: {
        name: "Exact 2Hash-DH OPRF-PSI",
        shortName: "Exact PSI",
        runtimeSec: 1.2158,
        perRecordMs: 121.58,
        commKb: 5.31,
        peakMemoryKb: 19.33,
        matches: 2,
        precision: 1.0000,
        recall: 1.0000,
        color: "#3b82f6", // blue
        description: "Cryptographic exact intersection hiding non-matching elements.",
      },
      fuzzyCrypt: {
        name: "FuzzyCrypt (Shingle Threshold-PSI)",
        shortName: "FuzzyCrypt",
        runtimeSec: 17.6375,
        perRecordMs: 1763.75,
        commKb: 89.19,
        peakMemoryKb: 249.88,
        matches: 4,
        precision: 1.0000,
        recall: 1.0000,
        color: "#6366f1", // indigo
        description: "Privacy-preserving similarity matching via OPRF-evaluated shingle sets.",
      },
    },
  },
  50: {
    n: 50,
    label: "N = 50 Records per party",
    metrics: {
      plaintextFuzzy: {
        name: "Plaintext Fuzzy (Normalized Levenshtein)",
        shortName: "Plaintext Fuzzy",
        runtimeSec: 0.6845,
        perRecordMs: 13.69,
        commKb: 0.00,
        peakMemoryKb: 13.11,
        matches: 20,
        precision: 1.0000,
        recall: 1.0000,
        color: "#64748b",
        description: "In-memory string edit distance with zero cryptographic privacy.",
      },
      exactPsi: {
        name: "Exact 2Hash-DH OPRF-PSI",
        shortName: "Exact PSI",
        runtimeSec: 5.7585,
        perRecordMs: 115.17,
        commKb: 26.56,
        peakMemoryKb: 60.53,
        matches: 10,
        precision: 1.0000,
        recall: 1.0000,
        color: "#3b82f6",
        description: "Cryptographic exact intersection hiding non-matching elements.",
      },
      fuzzyCrypt: {
        name: "FuzzyCrypt (Shingle Threshold-PSI)",
        shortName: "FuzzyCrypt",
        runtimeSec: 86.3936,
        perRecordMs: 1727.87,
        commKb: 470.26,
        peakMemoryKb: 1298.94,
        matches: 20,
        precision: 1.0000,
        recall: 1.0000,
        color: "#6366f1",
        description: "Privacy-preserving similarity matching via OPRF-evaluated shingle sets.",
      },
    },
  },
};
