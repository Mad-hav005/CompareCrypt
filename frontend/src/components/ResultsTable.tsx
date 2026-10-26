import React from 'react';
import type { UnifiedMatchRecord } from '../types/api';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface ResultsTableProps {
  matches: UnifiedMatchRecord[];
  threshold: number;
}

export const ResultsTable: React.FC<ResultsTableProps> = ({ matches, threshold }) => {
  if (matches.length === 0) {
    return (
      <div className="py-12 text-center space-y-3">
        <AlertCircle className="w-8 h-8 text-slate-700 mx-auto" />
        <p className="text-sm font-medium text-slate-400">No matches found</p>
        <p className="text-xs text-slate-600 max-w-sm mx-auto">
          No records met the {(threshold * 100).toFixed(0)}% threshold.
          Try lowering the threshold or loading the demo dataset.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-0 divide-y divide-slate-800/50">
      {matches.map((item, idx) => {
        const simPct = item.similarity * 100;
        const simStr = simPct.toFixed(1);
        const barWidth = Math.min(100, simPct);
        const isExact = simPct >= 99.9;

        return (
          <div key={idx} className="py-5 group">
            {/* Record pair row */}
            <div className="flex items-start gap-3">
              {/* Left: Alice + Bob stacked */}
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0" />
                  <span className="text-sm font-medium text-slate-100 truncate">
                    {item.aliceRecord}
                  </span>
                </div>
                <div className="flex items-center space-x-2 pl-0.5">
                  <span className="text-slate-700 text-[10px] ml-0.5">↕</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400 shrink-0" />
                  <span className="text-sm font-medium text-slate-100 truncate">
                    {item.bobRecord}
                  </span>
                </div>
              </div>

              {/* Right: Score + badge */}
              <div className="shrink-0 flex items-center space-x-3">
                <span className="text-lg font-bold text-slate-100 font-mono tabular-nums">
                  {simStr}%
                </span>
                <span className="flex items-center space-x-1 text-xs font-semibold text-emerald-400 bg-emerald-950/50 px-2.5 py-1 rounded-full border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>MATCH</span>
                </span>
              </div>
            </div>

            {/* Similarity bar + secondary text */}
            <div className="mt-2.5 space-y-1">
              <div className="h-1 w-full bg-slate-800/60 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    isExact ? 'bg-emerald-500' : 'bg-indigo-500'
                  }`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
              {item.intersectionCount !== undefined && (
                <p className="text-[11px] text-slate-700">
                  {item.intersectionCount} shared character bigrams
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
