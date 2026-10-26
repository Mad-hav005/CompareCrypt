import React from 'react';
import type { UnifiedMatchResult } from '../types/api';
import { ResultsTable } from './ResultsTable';
import { CheckCircle } from 'lucide-react';

interface ResultsDashboardProps {
  result: UnifiedMatchResult;
}

export const ResultsDashboard: React.FC<ResultsDashboardProps> = ({ result }) => {
  const timeSec = (result.executionTimeMs / 1000).toFixed(2);
  const thresholdPct = (result.threshold * 100).toFixed(0);

  return (
    <div className="space-y-6">
      {/* Completion banner */}
      <div className="flex items-start justify-between gap-4 pt-2">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <CheckCircle className="w-4 h-4 text-emerald-500" />
            <h3 className="text-base font-semibold text-white">Matching complete</h3>
          </div>
          <p className="text-sm text-slate-500">
            <span className="text-slate-200 font-medium">{result.matchCount}</span>{' '}
            {result.matchCount === 1 ? 'match' : 'matches'} found
            <span className="text-slate-700 mx-2">·</span>
            <span className="text-slate-400">{thresholdPct}% threshold</span>
            <span className="text-slate-700 mx-2">·</span>
            <span className="text-slate-400">{timeSec}s</span>
            <span className="text-slate-700 mx-2">·</span>
            <span className="text-slate-600 text-xs">
              A: {result.aliceSize} records &nbsp;B: {result.bobSize} records
            </span>
          </p>
        </div>
        {result.mode === 'fuzzycrypt' && result.estimatedPayloadKb && (
          <div className="text-right shrink-0">
            <p className="text-[11px] text-slate-600">Est. payload</p>
            <p className="text-xs font-mono text-slate-400">
              {result.estimatedPayloadKb.toFixed(1)} KB
            </p>
          </div>
        )}
      </div>

      {/* Match pair list */}
      <ResultsTable matches={result.matches} threshold={result.threshold} />
    </div>
  );
};
