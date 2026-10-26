import React, { useRef, useState } from 'react';
import { Upload, X, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';

interface PartyInputProps {
  aliceInput: string;
  bobInput: string;
  onChangeAlice: (value: string) => void;
  onChangeBob: (value: string) => void;
  onLoadDemoData: () => void;
  disabled?: boolean;
}

export const PartyInput: React.FC<PartyInputProps> = ({
  aliceInput,
  bobInput,
  onChangeAlice,
  onChangeBob,
  onLoadDemoData,
  disabled = false,
}) => {
  const aliceFileRef = useRef<HTMLInputElement>(null);
  const bobFileRef = useRef<HTMLInputElement>(null);
  const [privacyExpanded, setPrivacyExpanded] = useState(false);

  const countRecords = (text: string) =>
    text.split('\n').map((l) => l.trim()).filter((l) => l.length > 0).length;

  const handleFileUpload = (
    e: React.ChangeEvent<HTMLInputElement>,
    setter: (val: string) => void
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const content = ev.target?.result as string;
      if (content) {
        const lines = content
          .split(/\r?\n/)
          .map((l) => l.trim())
          .filter((l) => l.length > 0);
        setter(lines.join('\n'));
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const aliceCount = countRecords(aliceInput);
  const bobCount = countRecords(bobInput);

  return (
    <div className="space-y-4">
      {/* Top row: section label + demo link */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-slate-400">Party data</h2>
        <button
          type="button"
          onClick={onLoadDemoData}
          disabled={disabled}
          className="flex items-center space-x-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors disabled:opacity-40"
        >
          <Sparkles className="w-3 h-3" />
          <span>Load demo data</span>
        </button>
      </div>

      {/* Two-column party inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ── Party A ── */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span className="text-sm font-medium text-slate-200">Party A</span>
              <span className="text-xs text-slate-600 font-mono">
                {aliceCount} {aliceCount === 1 ? 'record' : 'records'}
              </span>
            </div>
            <div className="flex items-center space-x-1">
              <input
                ref={aliceFileRef}
                type="file"
                accept=".txt,.csv"
                className="hidden"
                onChange={(e) => handleFileUpload(e, onChangeAlice)}
                disabled={disabled}
              />
              <button
                type="button"
                onClick={() => aliceFileRef.current?.click()}
                disabled={disabled}
                title="Import from TXT or CSV"
                className="p-1 rounded text-slate-500 hover:text-slate-300 hover:bg-slate-800/60 transition-colors disabled:opacity-40"
              >
                <Upload className="w-3.5 h-3.5" />
              </button>
              {aliceInput && (
                <button
                  type="button"
                  onClick={() => onChangeAlice('')}
                  disabled={disabled}
                  title="Clear"
                  className="p-1 rounded text-slate-600 hover:text-rose-400 hover:bg-slate-800/60 transition-colors disabled:opacity-40"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
          <textarea
            rows={7}
            value={aliceInput}
            onChange={(e) => onChangeAlice(e.target.value)}
            disabled={disabled}
            placeholder={`One record per line\nMadhav Kumar\nJohn Smith\nAlice Johnson`}
            className="w-full bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 text-sm font-mono text-slate-200 placeholder:text-slate-700 focus:ring-1 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all resize-y leading-relaxed disabled:opacity-50"
          />
        </div>

        {/* ── Party B ── */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
              <span className="text-sm font-medium text-slate-200">Party B</span>
              <span className="text-xs text-slate-600 font-mono">
                {bobCount} {bobCount === 1 ? 'record' : 'records'}
              </span>
            </div>
            <div className="flex items-center space-x-1">
              <input
                ref={bobFileRef}
                type="file"
                accept=".txt,.csv"
                className="hidden"
                onChange={(e) => handleFileUpload(e, onChangeBob)}
                disabled={disabled}
              />
              <button
                type="button"
                onClick={() => bobFileRef.current?.click()}
                disabled={disabled}
                title="Import from TXT or CSV"
                className="p-1 rounded text-slate-500 hover:text-slate-300 hover:bg-slate-800/60 transition-colors disabled:opacity-40"
              >
                <Upload className="w-3.5 h-3.5" />
              </button>
              {bobInput && (
                <button
                  type="button"
                  onClick={() => onChangeBob('')}
                  disabled={disabled}
                  title="Clear"
                  className="p-1 rounded text-slate-600 hover:text-rose-400 hover:bg-slate-800/60 transition-colors disabled:opacity-40"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
          <textarea
            rows={7}
            value={bobInput}
            onChange={(e) => onChangeBob(e.target.value)}
            disabled={disabled}
            placeholder={`One record per line\nMadhav Kumer\nJohn Smith\nBob Wilson`}
            className="w-full bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 text-sm font-mono text-slate-200 placeholder:text-slate-700 focus:ring-1 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all resize-y leading-relaxed disabled:opacity-50"
          />
        </div>
      </div>

      {/* Privacy notice — compact, collapsible */}
      <div className="text-xs text-slate-600">
        Records are processed for private matching and are not exposed in the matching results.{' '}
        <button
          type="button"
          onClick={() => setPrivacyExpanded((v) => !v)}
          className="inline-flex items-center space-x-0.5 text-slate-500 hover:text-slate-400 transition-colors underline underline-offset-2"
        >
          <span>Privacy details</span>
          {privacyExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
        {privacyExpanded && (
          <p className="mt-2 text-slate-600 leading-relaxed max-w-2xl">
            This protocol does not transmit raw plaintext records between parties. Alice and Bob
            independently interact with the backend. Non-matching records are never revealed to
            the other party. Matching is performed under the semi-honest adversary model using
            cryptographic OPRF constructions.
          </p>
        )}
      </div>
    </div>
  );
};
