import React, { useState } from 'react';
import { EMPIRICAL_BENCHMARK_DATA } from '../constants/benchmarkData';
import { ChevronDown, ChevronRight, ShieldOff, Shield, Lock } from 'lucide-react';

type DisclosureKey = 'table' | 'timing' | 'methodology';

export const ComparisonDashboard: React.FC = () => {
  const [selectedN, setSelectedN] = useState<10 | 50>(10);
  const [open, setOpen] = useState<Record<DisclosureKey, boolean>>({
    table: false,
    timing: false,
    methodology: false,
  });

  const toggle = (key: DisclosureKey) =>
    setOpen((prev) => ({ ...prev, [key]: !prev[key] }));

  const data = EMPIRICAL_BENCHMARK_DATA[selectedN];
  const { plaintextFuzzy, exactPsi, compareCrypt } = data.metrics;

  const maxRuntime = Math.max(plaintextFuzzy.runtimeSec, exactPsi.runtimeSec, compareCrypt.runtimeSec);
  const maxComm = Math.max(plaintextFuzzy.commKb, exactPsi.commKb, compareCrypt.commKb);
  const maxMem = Math.max(plaintextFuzzy.peakMemoryKb, exactPsi.peakMemoryKb, compareCrypt.peakMemoryKb);

  const paradigms = [
    { ...plaintextFuzzy, privacyLabel: 'No privacy', PrivacyIcon: ShieldOff, privacyColor: 'text-slate-500' },
    { ...exactPsi, privacyLabel: 'Exact matches only', PrivacyIcon: Shield, privacyColor: 'text-blue-400' },
    { ...compareCrypt, privacyLabel: 'Privacy-preserving · fuzzy matches', PrivacyIcon: Lock, privacyColor: 'text-indigo-400' },
  ];

  return (
    <div className="space-y-10">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-white">Benchmark Comparison</h2>
          <p className="text-sm text-slate-500 mt-1">
            Computational and communication cost of three matching approaches.
          </p>
        </div>
        {/* N toggle */}
        <div className="flex items-center bg-slate-900 rounded-lg p-1 gap-0.5 shrink-0">
          {([10, 50] as const).map((n) => (
            <button
              key={n}
              onClick={() => setSelectedN(n)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                selectedN === n
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              N = {n}
            </button>
          ))}
        </div>
      </div>

      {/* Hero: three approach runtimes */}
      <div className="grid grid-cols-3 gap-px bg-slate-800/40 rounded-2xl overflow-hidden">
        {paradigms.map((p) => {
          const { PrivacyIcon } = p;
          return (
            <div key={p.shortName} className="bg-slate-950 px-6 py-6 space-y-3">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{p.shortName}</p>
              <p className="text-3xl font-bold text-slate-100 tabular-nums font-mono">
                {p.runtimeSec < 1
                  ? `${(p.runtimeSec * 1000).toFixed(0)} ms`
                  : `${p.runtimeSec.toFixed(3)} s`}
              </p>
              <div className="flex items-center space-x-1.5">
                <PrivacyIcon className={`w-3 h-3 ${p.privacyColor}`} />
                <p className={`text-xs ${p.privacyColor}`}>{p.privacyLabel}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts */}
      <div className="space-y-8">
        {/* Runtime chart */}
        <div className="space-y-3">
          <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total runtime</h3>
          {paradigms.map((p) => (
            <div key={p.shortName} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 font-medium">{p.shortName}</span>
                <span className="text-slate-300 font-mono tabular-nums">{p.runtimeSec.toFixed(4)} s</span>
              </div>
              <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${Math.max(2, (p.runtimeSec / maxRuntime) * 100)}%`,
                    backgroundColor: p.color,
                  }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Communication chart */}
        <div className="space-y-3">
          <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider">Communication payload</h3>
          {paradigms.map((p) => (
            <div key={p.shortName} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 font-medium">{p.shortName}</span>
                <span className="text-slate-300 font-mono tabular-nums">
                  {p.commKb === 0 ? '0 KB' : `${p.commKb.toFixed(2)} KB`}
                </span>
              </div>
              <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${maxComm > 0 ? Math.max(1, (p.commKb / maxComm) * 100) : 0}%`,
                    backgroundColor: p.color,
                  }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Memory chart */}
        <div className="space-y-3">
          <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider">Peak memory</h3>
          {paradigms.map((p) => (
            <div key={p.shortName} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 font-medium">{p.shortName}</span>
                <span className="text-slate-300 font-mono tabular-nums">{p.peakMemoryKb.toFixed(2)} KB</span>
              </div>
              <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${Math.max(2, (p.peakMemoryKb / maxMem) * 100)}%`,
                    backgroundColor: p.color,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Progressive disclosure panels */}
      <div className="space-y-0 divide-y divide-slate-800/60 border-t border-slate-800/60">

        {/* 1. Detailed metrics table */}
        <div className="py-4">
          <button
            type="button"
            onClick={() => toggle('table')}
            className="w-full flex items-center justify-between text-left group"
          >
            <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors">
              Detailed metrics
            </span>
            {open.table ? (
              <ChevronDown className="w-4 h-4 text-slate-600" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-600" />
            )}
          </button>
          {open.table && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="pb-2 pr-8 text-slate-500 font-medium">Metric</th>
                    <th className="pb-2 pr-8 text-slate-500 font-medium">Plaintext Fuzzy</th>
                    <th className="pb-2 pr-8 text-slate-500 font-medium">Exact PSI</th>
                    <th className="pb-2 text-indigo-400 font-medium">CompareCrypt</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 font-mono">
                  {[
                    ['Matching metric', 'Normalized Levenshtein', 'Exact equality', 'Unique bigram Sørensen-Dice'],
                    ['Cryptographic privacy', 'None', 'Computational (DDH)', 'Computational (DDH)'],
                    ['Runtime', `${plaintextFuzzy.runtimeSec.toFixed(4)} s`, `${exactPsi.runtimeSec.toFixed(4)} s`, `${compareCrypt.runtimeSec.toFixed(4)} s`],
                    ['Per-record', `${plaintextFuzzy.perRecordMs.toFixed(2)} ms`, `${exactPsi.perRecordMs.toFixed(2)} ms`, `${compareCrypt.perRecordMs.toFixed(2)} ms`],
                    ['Payload', `${plaintextFuzzy.commKb.toFixed(2)} KB`, `${exactPsi.commKb.toFixed(2)} KB`, `${compareCrypt.commKb.toFixed(2)} KB`],
                    ['Peak memory', `${plaintextFuzzy.peakMemoryKb.toFixed(2)} KB`, `${exactPsi.peakMemoryKb.toFixed(2)} KB`, `${compareCrypt.peakMemoryKb.toFixed(2)} KB`],
                    ['Matches found', `${plaintextFuzzy.matches}`, `${exactPsi.matches}`, `${compareCrypt.matches}`],
                    ['Precision', `${plaintextFuzzy.precision.toFixed(4)}`, `${exactPsi.precision.toFixed(4)}`, `${compareCrypt.precision.toFixed(4)}`],
                    ['Recall', `${plaintextFuzzy.recall.toFixed(4)}`, `${exactPsi.recall.toFixed(4)}`, `${compareCrypt.recall.toFixed(4)}`],
                  ].map(([metric, pf, ep, fc]) => (
                    <tr key={metric} className="hover:bg-slate-900/30 transition-colors">
                      <td className="py-2 pr-8 text-slate-500 font-sans">{metric}</td>
                      <td className="py-2 pr-8 text-slate-300">{pf}</td>
                      <td className="py-2 pr-8 text-slate-300">{ep}</td>
                      <td className="py-2 text-indigo-300 font-semibold">{fc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* 2. Phase timing */}
        <div className="py-4">
          <button
            type="button"
            onClick={() => toggle('timing')}
            className="w-full flex items-center justify-between text-left group"
          >
            <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors">
              Why is CompareCrypt slower?
            </span>
            {open.timing ? (
              <ChevronDown className="w-4 h-4 text-slate-600" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-600" />
            )}
          </button>
          {open.timing && (
            <div className="mt-4 space-y-4 text-sm text-slate-400">
              <p>
                CompareCrypt performs 2048-bit modular exponentiations per shingle (character bigram).
                Each exponentiation is the dominant cost. Three protocol phases:
              </p>
              <div className="space-y-3">
                {[
                  { phase: 'Phase 1 — Alice Blinding', pct: '~26.5%', detail: 'Alice exponentiates each unique shingle with a secret ephemeral scalar' },
                  { phase: 'Phase 2 — Bob Evaluation (bottleneck)', pct: '~47–50%', detail: "Bob evaluates Alice's blinded shingles and generates PRF digests for Bob's own shingles" },
                  { phase: 'Phase 3 — Alice Unblinding', pct: '~26.6%', detail: 'Alice removes the blinding factor, computes Dice similarity, applies threshold' },
                ].map(({ phase, pct, detail }) => (
                  <div key={phase} className="space-y-0.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-300 font-medium">{phase}</span>
                      <span className="text-indigo-400 font-mono font-semibold">{pct}</span>
                    </div>
                    <p className="text-xs text-slate-600">{detail}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 3. Benchmark methodology */}
        <div className="py-4">
          <button
            type="button"
            onClick={() => toggle('methodology')}
            className="w-full flex items-center justify-between text-left group"
          >
            <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors">
              Benchmark methodology
            </span>
            {open.methodology ? (
              <ChevronDown className="w-4 h-4 text-slate-600" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-600" />
            )}
          </button>
          {open.methodology && (
            <div className="mt-4 space-y-2 text-xs text-slate-500 leading-relaxed">
              <p>
                <span className="text-slate-300 font-medium">Environment:</span>{' '}
                Windows 11 · Python 3.12 · RFC 3526 2048-bit MODP Group 14
              </p>
              <p>
                <span className="text-slate-300 font-medium">Memory profiling:</span>{' '}
                Runtimes include concurrent{' '}
                <code className="text-slate-400 bg-slate-900 px-1 rounded">tracemalloc</code>{' '}
                overhead (calibrated separately at approximately +23% to +30% CPU overhead on
                modular exponentiations and heap allocations). This overhead is reported separately
                and not post-hoc corrected in the raw timings.
              </p>
              <p>
                <span className="text-slate-300 font-medium">Dataset sizes tested:</span>{' '}
                N = 10 and N = 50 records per party. N = 100 and N = 200 were not benchmarked.
              </p>
              <p>
                These are empirical benchmark results. All values are labeled as such.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
