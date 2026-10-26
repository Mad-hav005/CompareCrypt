import React, { useState } from 'react';
import {
  Download, Filter, SortAsc, SortDesc, ChevronDown,
  ChevronLeft, ChevronRight as ChevronRightIcon
} from 'lucide-react';
import type { ERJobResults, EntityMatchResult, AttributeScore } from '../../types/api';

interface ResultsPanelProps {
  results: ERJobResults;
  jobId: string;
  exportUrl: string;
  onPageChange: (page: number) => void;
  onSortChange: (sortBy: string, sortDesc: boolean) => void;
  onFilterChange: (minScore: number | undefined) => void;
  currentSort: { by: string; desc: boolean };
  currentMinScore: number | undefined;
}

const STRATEGY_COLORS: Record<string, string> = {
  fuzzy: 'text-indigo-400 bg-indigo-500/10',
  exact: 'text-cyan-400 bg-cyan-500/10',
  ignore: 'text-slate-600 bg-slate-800/40',
};

function scoreColor(score: number): string {
  if (score >= 0.9) return 'text-emerald-400';
  if (score >= 0.75) return 'text-yellow-400';
  if (score >= 0.5) return 'text-orange-400';
  return 'text-rose-400';
}

function scoreBar(score: number): string {
  if (score >= 0.9) return 'bg-emerald-500';
  if (score >= 0.75) return 'bg-yellow-500';
  if (score >= 0.5) return 'bg-orange-500';
  return 'bg-rose-500';
}

const AttributeScoreRow: React.FC<{ attr: AttributeScore }> = ({ attr }) => {
  if (attr.strategy === 'ignore') return null;
  const score = attr.score ?? 0;
  return (
    <div className="flex items-center space-x-2 text-xs">
      <span className="text-slate-500 w-28 truncate shrink-0">{attr.column_a}</span>
      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${STRATEGY_COLORS[attr.strategy]}`}>
        {attr.strategy}
      </span>
      <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${scoreBar(score)}`}
          style={{ width: `${score * 100}%` }}
        />
      </div>
      <span className={`font-mono w-10 text-right shrink-0 ${scoreColor(score)}`}>
        {(score * 100).toFixed(0)}%
      </span>
      <span className="text-slate-700 text-xs">×{attr.weight}</span>
    </div>
  );
};

const MatchCard: React.FC<{ match: EntityMatchResult; index: number }> = ({ match, index }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-slate-800/80 rounded-xl overflow-hidden hover:border-slate-700/80 transition-colors">
      {/* Summary row */}
      <div
        className="flex items-center space-x-4 px-4 py-3 cursor-pointer hover:bg-slate-800/30 transition-colors"
        onClick={() => setExpanded((v) => !v)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && setExpanded((v) => !v)}
      >
        <span className="text-xs text-slate-600 font-mono w-6 text-right shrink-0">#{index + 1}</span>

        {/* Score circle */}
        <div className="relative w-10 h-10 shrink-0">
          <svg className="w-10 h-10 -rotate-90" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="15" fill="none" stroke="#1e293b" strokeWidth="3" />
            <circle
              cx="18" cy="18" r="15" fill="none"
              stroke={match.overall_score >= 0.9 ? '#10b981' : match.overall_score >= 0.75 ? '#eab308' : '#f97316'}
              strokeWidth="3"
              strokeDasharray={`${match.overall_score * 94.25} 94.25`}
            />
          </svg>
          <span className={`absolute inset-0 flex items-center justify-center text-xs font-bold font-mono ${scoreColor(match.overall_score)}`}>
            {(match.overall_score * 100).toFixed(0)}
          </span>
        </div>

        {/* Previews */}
        <div className="flex-1 min-w-0 grid grid-cols-2 gap-4">
          <div className="min-w-0">
            <p className="text-xs text-slate-500 mb-0.5">Row {match.row_index_a} · Party A</p>
            <div className="flex flex-wrap gap-1">
              {Object.entries(match.row_a_preview).slice(0, 3).map(([k, v]) => (
                <span key={k} className="text-xs text-slate-300 font-mono truncate max-w-[140px]" title={`${k}: ${v}`}>
                  {v || <span className="text-slate-700">—</span>}
                </span>
              ))}
            </div>
          </div>
          <div className="min-w-0">
            <p className="text-xs text-slate-500 mb-0.5">Row {match.row_index_b} · Party B</p>
            <div className="flex flex-wrap gap-1">
              {Object.entries(match.row_b_preview).slice(0, 3).map(([k, v]) => (
                <span key={k} className="text-xs text-slate-300 font-mono truncate max-w-[140px]" title={`${k}: ${v}`}>
                  {v || <span className="text-slate-700">—</span>}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Expand */}
        <div className="shrink-0 text-slate-600">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRightIcon className="w-4 h-4" />}
        </div>
      </div>

      {/* Expanded attribute breakdown */}
      {expanded && (
        <div className="border-t border-slate-800/60 px-4 py-3 space-y-2 bg-slate-900/40">
          <p className="text-xs text-slate-500 font-medium">Attribute breakdown</p>
          {match.attribute_scores.map((attr, i) => (
            <AttributeScoreRow key={i} attr={attr} />
          ))}
          {/* Full row previews */}
          <div className="grid grid-cols-2 gap-4 mt-3 pt-3 border-t border-slate-800/60">
            {[{ label: 'Party A', data: match.row_a_preview }, { label: 'Party B', data: match.row_b_preview }].map(({ label, data }) => (
              <div key={label}>
                <p className="text-xs text-slate-500 mb-1.5">{label} (matched fields)</p>
                <div className="space-y-1">
                  {Object.entries(data).map(([k, v]) => (
                    <div key={k} className="flex items-baseline space-x-2">
                      <span className="text-xs text-slate-600 w-24 shrink-0 truncate">{k}</span>
                      <span className="text-xs text-slate-300 font-mono truncate">{v || '—'}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export const ResultsPanel: React.FC<ResultsPanelProps> = ({
  results,
  jobId,
  exportUrl,
  onPageChange,
  onSortChange,
  onFilterChange,
  currentSort,
  currentMinScore,
}) => {
  const [filterInput, setFilterInput] = useState(
    currentMinScore !== undefined ? String(Math.round(currentMinScore * 100)) : ''
  );

  const handleFilterApply = () => {
    const val = parseFloat(filterInput);
    if (!isNaN(val) && val >= 0 && val <= 100) {
      onFilterChange(val / 100);
    } else if (filterInput === '') {
      onFilterChange(undefined);
    }
  };

  return (
    <div className="space-y-4">
      {/* Summary banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Matched pairs', value: results.total_matches.toLocaleString(), color: 'text-emerald-400' },
          { label: 'Unmatched A', value: results.total_unmatched_a.toLocaleString(), color: 'text-slate-400' },
          { label: 'Unmatched B', value: results.total_unmatched_b.toLocaleString(), color: 'text-slate-400' },
          { label: 'Candidates evaluated', value: results.candidate_pairs_evaluated.toLocaleString(), color: 'text-indigo-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-slate-900/60 rounded-xl p-3 border border-slate-800/80">
            <p className={`text-xl font-bold font-mono tabular-nums ${color}`}>{value}</p>
            <p className="text-xs text-slate-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Controls row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Sort controls */}
        <div className="flex items-center space-x-2">
          <span className="text-xs text-slate-500">Sort by</span>
          {[
            { key: 'overall_score', label: 'Score' },
            { key: 'row_index_a', label: 'Row A' },
            { key: 'row_index_b', label: 'Row B' },
          ].map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => onSortChange(key, currentSort.by === key ? !currentSort.desc : true)}
              className={`
                flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all
                ${currentSort.by === key
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-transparent'
                }
              `}
            >
              <span>{label}</span>
              {currentSort.by === key && (
                currentSort.desc ? <SortDesc className="w-3 h-3" /> : <SortAsc className="w-3 h-3" />
              )}
            </button>
          ))}
        </div>

        {/* Filter */}
        <div className="flex items-center space-x-1.5 ml-auto">
          <Filter className="w-3.5 h-3.5 text-slate-600" />
          <span className="text-xs text-slate-500">Min score</span>
          <input
            type="number"
            value={filterInput}
            onChange={(e) => setFilterInput(e.target.value)}
            onBlur={handleFilterApply}
            onKeyDown={(e) => e.key === 'Enter' && handleFilterApply()}
            min={0}
            max={100}
            placeholder="0–100"
            className="w-16 bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-200 font-mono text-center focus:ring-1 focus:ring-indigo-500/50 transition-all"
          />
          <span className="text-xs text-slate-600">%</span>
        </div>

        {/* Export */}
        <a
          href={exportUrl}
          download={`er_results_${jobId}.csv`}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 border border-slate-700 transition-all"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export CSV</span>
        </a>
      </div>

      {/* Results list */}
      {results.results.length === 0 ? (
        <div className="text-center py-10 text-sm text-slate-600 border border-dashed border-slate-800 rounded-2xl">
          No matches found for the current filter.
        </div>
      ) : (
        <div className="space-y-2">
          {results.results.map((match, i) => (
            <MatchCard
              key={`${match.row_index_a}-${match.row_index_b}`}
              match={match}
              index={(results.page - 1) * results.page_size + i}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {results.total_pages > 1 && (
        <div className="flex items-center justify-center space-x-2 pt-2">
          <button
            type="button"
            onClick={() => onPageChange(results.page - 1)}
            disabled={results.page <= 1}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 disabled:opacity-40 transition-all"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs text-slate-500 font-mono">
            Page {results.page} / {results.total_pages}
          </span>
          <button
            type="button"
            onClick={() => onPageChange(results.page + 1)}
            disabled={results.page >= results.total_pages}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 disabled:opacity-40 transition-all"
          >
            <ChevronRightIcon className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Protocol notes */}
      <details className="text-xs text-slate-600">
        <summary className="cursor-pointer hover:text-slate-500 transition-colors">Protocol & privacy notes</summary>
        <p className="mt-2 leading-relaxed max-w-3xl">{results.protocol_notes}</p>
      </details>
    </div>
  );
};
