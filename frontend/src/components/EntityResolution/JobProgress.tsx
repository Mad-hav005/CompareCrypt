import React from 'react';
import { Loader2, CheckCircle2, AlertCircle, Clock, Shield } from 'lucide-react';
import type { ERJobStatus, ERJobPhase } from '../../types/api';

interface JobProgressProps {
  status: ERJobStatus | null;
}

const PHASE_LABELS: Record<ERJobPhase, string> = {
  queued: 'Queued',
  blocking: 'Generating candidates',
  matching: 'Cryptographic matching',
  scoring: 'Computing scores',
  complete: 'Complete',
  error: 'Error',
};

const PHASE_ORDER: ERJobPhase[] = ['queued', 'blocking', 'matching', 'scoring', 'complete'];

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export const JobProgress: React.FC<JobProgressProps> = ({ status }) => {
  if (!status) return null;

  const isError = status.phase === 'error';
  const isComplete = status.phase === 'complete';
  const phaseIdx = PHASE_ORDER.indexOf(status.phase as ERJobPhase);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {isError ? (
            <AlertCircle className="w-4 h-4 text-rose-400" />
          ) : isComplete ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : (
            <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
          )}
          <span className="text-sm font-semibold text-slate-200">
            {isError ? 'Job Failed' : isComplete ? 'Matching Complete' : 'Running…'}
          </span>
        </div>
        <div className="flex items-center space-x-1.5 text-xs text-slate-500">
          <Clock className="w-3 h-3" />
          <span className="font-mono">{formatMs(status.elapsed_ms)}</span>
        </div>
      </div>

      {/* Progress bar */}
      {!isError && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-slate-500">
            <span>{PHASE_LABELS[status.phase as ERJobPhase]}</span>
            <span className="font-mono">{status.progress_pct.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isComplete ? 'bg-emerald-500' : 'bg-indigo-500'
              }`}
              style={{ width: `${status.progress_pct}%` }}
            />
          </div>
        </div>
      )}

      {/* Phase stepper */}
      <div className="flex items-center space-x-1 overflow-x-auto pb-1">
        {PHASE_ORDER.slice(1).map((phase, i) => {
          const idx = i + 1;
          const done = phaseIdx > idx;
          const active = phaseIdx === idx;
          return (
            <React.Fragment key={phase}>
              {i > 0 && (
                <div className={`h-px flex-1 min-w-[16px] ${done ? 'bg-indigo-500' : 'bg-slate-800'} transition-colors`} />
              )}
              <div className={`
                flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold shrink-0 transition-colors
                ${done ? 'bg-indigo-500 text-white'
                  : active ? 'bg-indigo-600/40 text-indigo-300 ring-1 ring-indigo-500'
                  : 'bg-slate-800 text-slate-600'}
              `}>
                {done ? '✓' : idx}
              </div>
            </React.Fragment>
          );
        })}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Candidates', value: status.candidate_pairs.toLocaleString() },
          { label: 'Evaluated', value: status.processed_pairs.toLocaleString() },
          { label: 'Matches', value: status.match_count.toLocaleString() },
        ].map(({ label, value }) => (
          <div key={label} className="bg-slate-800/40 rounded-xl p-2.5 text-center">
            <p className="text-lg font-bold text-slate-100 font-mono tabular-nums">{value}</p>
            <p className="text-xs text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      {/* Error message */}
      {isError && status.error_message && (
        <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/20 text-xs text-rose-300">
          {status.error_message}
        </div>
      )}

      {/* Privacy notice */}
      {(isComplete || (!isError && status.phase !== 'queued')) && (
        <div className="flex items-start space-x-2 text-xs text-slate-600">
          <Shield className="w-3 h-3 shrink-0 mt-0.5 text-indigo-800" />
          <span>
            Fuzzy attributes use 2Hash-DH OPRF (RFC 3526 2048-bit). Exact attributes use OPRF-PSI.
            Non-matching records are excluded from results.
          </span>
        </div>
      )}
    </div>
  );
};
