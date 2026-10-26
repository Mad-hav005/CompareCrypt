import React from 'react';
import { ArrowRight, Plus, Trash2, ChevronDown } from 'lucide-react';
import type { AttributeMapping, DatasetSchema, MatchStrategy } from '../../types/api';

interface AttributeMapperProps {
  schemaA: DatasetSchema | null;
  schemaB: DatasetSchema | null;
  mappings: AttributeMapping[];
  onAddMapping: () => void;
  onUpdateMapping: (index: number, update: Partial<AttributeMapping>) => void;
  onRemoveMapping: (index: number) => void;
  disabled?: boolean;
}

const STRATEGY_OPTIONS: { value: MatchStrategy; label: string; desc: string; color: string }[] = [
  { value: 'fuzzy', label: 'Fuzzy', desc: 'OPRF shingle similarity', color: 'text-indigo-400' },
  { value: 'exact', label: 'Exact', desc: 'OPRF exact PSI', color: 'text-cyan-400' },
  { value: 'ignore', label: 'Ignore', desc: 'Skip this attribute', color: 'text-slate-500' },
];

export const AttributeMapper: React.FC<AttributeMapperProps> = ({
  schemaA,
  schemaB,
  mappings,
  onAddMapping,
  onUpdateMapping,
  onRemoveMapping,
  disabled = false,
}) => {
  const colsA = schemaA?.columns.map((c) => c.name) ?? [];
  const colsB = schemaB?.columns.map((c) => c.name) ?? [];

  if (!schemaA || !schemaB) {
    return (
      <div className="rounded-2xl border border-slate-800 p-6 text-center text-sm text-slate-600">
        Upload datasets for both parties to configure attribute mapping.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Attribute Mapping</h3>
        <button
          type="button"
          onClick={onAddMapping}
          disabled={disabled || colsA.length === 0 || colsB.length === 0}
          className="flex items-center space-x-1.5 text-xs text-indigo-400 hover:text-indigo-300 disabled:opacity-40 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add mapping</span>
        </button>
      </div>

      {mappings.length === 0 ? (
        <div className="text-center py-6 text-xs text-slate-600 border border-dashed border-slate-800 rounded-2xl">
          No attribute mappings configured. Add at least one.
        </div>
      ) : (
        <div className="space-y-2">
          {/* Header row */}
          <div className="grid grid-cols-[1fr_auto_1fr_auto_auto_auto] gap-2 px-3 text-xs text-slate-600 font-medium">
            <span>Party A column</span>
            <span />
            <span>Party B column</span>
            <span>Strategy</span>
            <span>Weight</span>
            <span />
          </div>

          {mappings.map((mapping, idx) => (
            <div
              key={idx}
              className={`
                grid grid-cols-[1fr_auto_1fr_auto_auto_auto] gap-2 items-center
                bg-slate-900/60 rounded-xl px-3 py-2.5 border
                ${mapping.strategy === 'ignore'
                  ? 'border-slate-800/40 opacity-60'
                  : 'border-slate-800/80'
                }
              `}
            >
              {/* Column A */}
              <div className="relative">
                <select
                  value={mapping.column_a}
                  onChange={(e) => onUpdateMapping(idx, { column_a: e.target.value })}
                  disabled={disabled}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 appearance-none pr-6 disabled:opacity-50 focus:ring-1 focus:ring-indigo-500/50 transition-all"
                >
                  {colsA.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-600 pointer-events-none" />
              </div>

              {/* Arrow */}
              <ArrowRight className="w-3.5 h-3.5 text-slate-700 shrink-0" />

              {/* Column B */}
              <div className="relative">
                <select
                  value={mapping.column_b}
                  onChange={(e) => onUpdateMapping(idx, { column_b: e.target.value })}
                  disabled={disabled}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 appearance-none pr-6 disabled:opacity-50 focus:ring-1 focus:ring-indigo-500/50 transition-all"
                >
                  {colsB.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-600 pointer-events-none" />
              </div>

              {/* Strategy */}
              <div className="relative">
                <select
                  value={mapping.strategy}
                  onChange={(e) => onUpdateMapping(idx, { strategy: e.target.value as MatchStrategy })}
                  disabled={disabled}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 appearance-none pr-6 disabled:opacity-50 focus:ring-1 focus:ring-indigo-500/50 transition-all"
                >
                  {STRATEGY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-600 pointer-events-none" />
              </div>

              {/* Weight */}
              <div className="flex items-center space-x-1.5 w-24">
                <input
                  type="number"
                  value={mapping.weight}
                  min={0}
                  max={10}
                  step={0.5}
                  onChange={(e) => onUpdateMapping(idx, { weight: parseFloat(e.target.value) || 1 })}
                  disabled={disabled || mapping.strategy === 'ignore'}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-200 text-center font-mono disabled:opacity-40 focus:ring-1 focus:ring-indigo-500/50 transition-all"
                />
              </div>

              {/* Remove */}
              <button
                type="button"
                onClick={() => onRemoveMapping(idx)}
                disabled={disabled}
                className="p-1 rounded text-slate-700 hover:text-rose-400 hover:bg-slate-800/60 transition-colors disabled:opacity-40"
                title="Remove mapping"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Per-fuzzy-attribute threshold controls */}
      {mappings.some((m) => m.strategy === 'fuzzy') && (
        <div className="rounded-xl border border-slate-800/60 p-3 space-y-2 mt-1">
          <p className="text-xs text-slate-500 font-medium">Fuzzy attribute thresholds</p>
          {mappings.map((mapping, idx) =>
            mapping.strategy === 'fuzzy' ? (
              <div key={idx} className="flex items-center space-x-3">
                <span className="text-xs text-slate-400 w-32 truncate shrink-0">{mapping.column_a}</span>
                <input
                  type="range"
                  min={0.1}
                  max={1.0}
                  step={0.05}
                  value={mapping.fuzzy_threshold}
                  onChange={(e) => onUpdateMapping(idx, { fuzzy_threshold: parseFloat(e.target.value) })}
                  disabled={disabled}
                  className="flex-1 accent-indigo-500 disabled:opacity-40"
                />
                <span className="text-xs font-mono text-indigo-400 w-10 text-right shrink-0">
                  {(mapping.fuzzy_threshold * 100).toFixed(0)}%
                </span>
              </div>
            ) : null
          )}
        </div>
      )}
    </div>
  );
};
