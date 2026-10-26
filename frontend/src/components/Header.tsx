import React from 'react';
import { Shield, ShieldAlert, ShieldCheck, Activity } from 'lucide-react';
import type { HealthResponse } from '../types/api';

interface HeaderProps {
  health: HealthResponse | null;
  healthLoading: boolean;
  onRefreshHealth: () => void;
}

export const Header: React.FC<HeaderProps> = ({ health, healthLoading, onRefreshHealth }) => {
  return (
    <header className="border-b border-slate-800/60 bg-slate-950/90 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-6 h-13 flex items-center justify-between" style={{ height: '52px' }}>
        {/* Brand */}
        <div className="flex items-center space-x-2.5">
          <Shield className="w-5 h-5 text-indigo-400" strokeWidth={2} />
          <div>
            <span className="text-sm font-semibold text-white tracking-tight">FuzzyCrypt</span>
            <span className="hidden sm:inline text-sm text-slate-500 ml-2">
              Privacy-Preserving Similarity Matching
            </span>
          </div>
        </div>

        {/* Backend status */}
        <button
          onClick={onRefreshHealth}
          title="Click to refresh backend status"
          className="flex items-center space-x-1.5 text-xs transition-colors hover:text-slate-300"
        >
          {healthLoading ? (
            <>
              <Activity className="w-3 h-3 text-slate-500 animate-pulse" />
              <span className="text-slate-500">Connecting…</span>
            </>
          ) : health?.status === 'healthy' ? (
            <>
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
              </span>
              <ShieldCheck className="w-3 h-3 text-emerald-500" />
              <span className="text-emerald-500 font-medium">Connected</span>
            </>
          ) : (
            <>
              <ShieldAlert className="w-3 h-3 text-rose-400" />
              <span className="text-rose-400">Backend Offline</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
};
