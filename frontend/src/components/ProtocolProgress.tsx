import React, { useState, useEffect } from 'react';
import { CheckCircle2, Loader2, Circle, ChevronDown, ChevronRight } from 'lucide-react';
import type { ProtocolStage } from '../types/api';

interface ProtocolProgressProps {
  stages: ProtocolStage[];
  currentStageIndex: number;
  isExecuting: boolean;
}

export const ProtocolProgress: React.FC<ProtocolProgressProps> = ({
  stages,
  currentStageIndex,
  isExecuting,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  // Auto-expand when execution starts
  useEffect(() => {
    if (isExecuting) setIsOpen(true);
  }, [isExecuting]);

  // Don't render before first run
  if (!isExecuting && currentStageIndex === -1) return null;

  const isComplete = !isExecuting && currentStageIndex === stages.length - 1;

  return (
    <div className="border-t border-slate-800/60 pt-4">
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="w-full flex items-center justify-between text-left group"
      >
        <div className="flex items-center space-x-2">
          {isExecuting ? (
            <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
          ) : isComplete ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          ) : (
            <Circle className="w-3.5 h-3.5 text-slate-600" />
          )}
          <span className="text-xs font-medium text-slate-500 group-hover:text-slate-400 transition-colors">
            {isExecuting
              ? 'Protocol executing…'
              : isComplete
              ? 'Protocol execution complete'
              : 'Protocol execution'}
          </span>
          {!isExecuting && currentStageIndex !== -1 && (
            <span className="text-[10px] text-slate-700 font-mono">
              {stages.length}/{stages.length} stages
            </span>
          )}
        </div>
        {isOpen ? (
          <ChevronDown className="w-3.5 h-3.5 text-slate-600" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
        )}
      </button>

      {/* Expanded stage list */}
      {isOpen && (
        <div className="mt-4 space-y-1">
          {stages.map((stage, idx) => {
            const isCompleted =
              idx < currentStageIndex ||
              (!isExecuting && currentStageIndex === stages.length - 1);
            const isActive = idx === currentStageIndex && isExecuting;

            return (
              <div
                key={stage.id}
                className={`flex items-center space-x-3 py-1.5 px-3 rounded-lg text-xs transition-colors ${
                  isActive
                    ? 'bg-indigo-950/40 text-indigo-300'
                    : isCompleted
                    ? 'text-slate-400'
                    : 'text-slate-700'
                }`}
              >
                <span className="shrink-0 w-4 flex justify-center">
                  {isCompleted ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  ) : isActive ? (
                    <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
                  ) : (
                    <Circle className="w-3.5 h-3.5 text-slate-700" />
                  )}
                </span>
                <span className={`font-medium ${isActive ? 'text-indigo-200' : ''}`}>
                  {idx + 1}. {stage.label}
                </span>
                <span className="text-slate-700 font-mono text-[10px] ml-auto">{stage.party}</span>
              </div>
            );
          })}

          <p className="text-[10px] text-slate-700 px-3 pt-2">
            UI visualization only — the cryptographic pipeline runs in the backend.
          </p>
        </div>
      )}
    </div>
  );
};
