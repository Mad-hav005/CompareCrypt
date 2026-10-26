import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { MatchingMode } from '../types/api';

interface ThresholdControlProps {
  mode: MatchingMode;
  threshold: number;
  onChangeThreshold: (val: number) => void;
  normalize: boolean;
  onChangeNormalize: (val: boolean) => void;
  disabled?: boolean;
}

export const ThresholdControl: React.FC<ThresholdControlProps> = ({
  mode,
  threshold,
  onChangeThreshold,
  normalize,
  onChangeNormalize,
  disabled = false,
}) => {
  const [detailsOpen, setDetailsOpen] = useState(false);

  if (mode === 'comparison') return null;

  if (mode === 'exact') {
    return (
      <div className="flex items-center space-x-3">
        <input
          id="normalize-checkbox"
          type="checkbox"
          checked={normalize}
          onChange={(e) => onChangeNormalize(e.target.checked)}
          disabled={disabled}
          className="w-4 h-4 rounded text-indigo-600 bg-slate-800 border-slate-700 focus:ring-indigo-500 focus:ring-offset-slate-950"
        />
        <label htmlFor="normalize-checkbox" className="text-sm text-slate-400 cursor-pointer">
          Normalize records before matching{' '}
          <span className="text-slate-600 text-xs">(case folding, whitespace trimming)</span>
        </label>
      </div>
    );
  }

  // FuzzyCrypt threshold
  return (
    <div className="space-y-3">
      {/* Label + value */}
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-slate-400">Similarity threshold</label>
        <span className="text-2xl font-bold text-slate-100 font-mono tabular-nums">
          {(threshold * 100).toFixed(0)}%
        </span>
      </div>

      {/* Slider */}
      <input
        type="range"
        min="0.50"
        max="1.00"
        step="0.05"
        value={threshold}
        onChange={(e) => onChangeThreshold(parseFloat(e.target.value))}
        disabled={disabled}
        className="w-full cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
      />

      {/* Range labels */}
      <div className="flex justify-between text-xs text-slate-600">
        <span>More permissive</span>
        <span>Stricter</span>
      </div>

      {/* How it works disclosure */}
      <div>
        <button
          type="button"
          onClick={() => setDetailsOpen((v) => !v)}
          className="flex items-center space-x-1 text-xs text-slate-600 hover:text-slate-400 transition-colors"
        >
          {detailsOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          <span>How FuzzyCrypt protects the data</span>
        </button>

        {detailsOpen && (
          <div className="mt-3 space-y-2 pl-4 border-l border-slate-800">
            {[
              ['Cryptographic construction', '2Hash-DH OPRF · RFC 3526 Group 14'],
              ['Similarity representation', 'Unique boundary-padded character bigrams'],
              ['Similarity metric', 'Sørensen-Dice coefficient'],
              ['Security model', 'Semi-honest two-party setting'],
            ].map(([key, val]) => (
              <div key={key} className="flex items-start gap-4">
                <span className="text-xs text-slate-500 w-48 shrink-0">{key}</span>
                <span className="text-xs text-slate-300 font-mono">{val}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
