import React from 'react';
import type { MatchingMode } from '../types/api';

interface ModeSelectorProps {
  currentMode: MatchingMode;
  onSelectMode: (mode: MatchingMode) => void;
  disabled?: boolean;
}

const MODES: { id: MatchingMode; label: string }[] = [
  { id: 'entity_resolution', label: 'Entity Resolution' },
  { id: 'fuzzycrypt', label: 'FuzzyCrypt' },
  { id: 'exact', label: 'Exact PSI' },
  { id: 'comparison', label: 'Benchmark' },
];

export const ModeSelector: React.FC<ModeSelectorProps> = ({
  currentMode,
  onSelectMode,
  disabled = false,
}) => {
  return (
    <div className="flex items-center">
      <nav className="flex items-center bg-slate-900 rounded-lg p-1 gap-0.5" role="tablist">
        {MODES.map((mode) => {
          const isActive = currentMode === mode.id;
          return (
            <button
              key={mode.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => !disabled && onSelectMode(mode.id)}
              disabled={disabled}
              className={`
                px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-150
                ${isActive
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              {mode.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
};
