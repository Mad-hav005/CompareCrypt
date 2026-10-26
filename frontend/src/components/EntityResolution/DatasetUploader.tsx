import React, { useState, useRef, useCallback } from 'react';
import { Upload, FileText, CheckCircle2, X, Eye, EyeOff } from 'lucide-react';
import type { DatasetSchema } from '../../types/api';

interface DatasetUploaderProps {
  party: 'A' | 'B';
  jobId: string;
  schema: DatasetSchema | null;
  isUploading: boolean;
  onUpload: (file: File) => void;
  onClear: () => void;
  disabled?: boolean;
}

const PARTY_COLORS = {
  A: { dot: 'bg-cyan-400', border: 'border-cyan-500/30', text: 'text-cyan-400', bg: 'bg-cyan-500/10', ring: 'ring-cyan-500/30' },
  B: { dot: 'bg-violet-400', border: 'border-violet-500/30', text: 'text-violet-400', bg: 'bg-violet-500/10', ring: 'ring-violet-500/30' },
};

export const DatasetUploader: React.FC<DatasetUploaderProps> = ({
  party,
  schema,
  isUploading,
  onUpload,
  onClear,
  disabled = false,
}) => {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const colors = PARTY_COLORS[party];

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (!file) return;
      const name = file.name.toLowerCase();
      if (!name.endsWith('.csv') && !name.endsWith('.xlsx') && !name.endsWith('.xls') && !name.endsWith('.txt')) {
        return;
      }
      onUpload(file);
    },
    [onUpload]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      handleFile(e.dataTransfer.files[0]);
    },
    [disabled, handleFile]
  );

  return (
    <div className="space-y-3">
      {/* Party header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className={`w-2 h-2 rounded-full ${colors.dot}`} />
          <span className="text-sm font-semibold text-slate-200">Party {party}</span>
          {schema && (
            <span className="text-xs text-slate-500 font-mono">
              {schema.row_count.toLocaleString()} rows · {schema.columns.length} cols
            </span>
          )}
        </div>
        {schema && (
          <div className="flex items-center space-x-1">
            <button
              type="button"
              onClick={() => setShowPreview((v) => !v)}
              className="flex items-center space-x-1 text-xs text-slate-500 hover:text-slate-300 transition-colors px-2 py-1 rounded-md hover:bg-slate-800/60"
            >
              {showPreview ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
              <span>{showPreview ? 'Hide' : 'Preview'}</span>
            </button>
            <button
              type="button"
              onClick={onClear}
              disabled={disabled}
              className="p-1 rounded text-slate-600 hover:text-rose-400 hover:bg-slate-800/60 transition-colors disabled:opacity-40"
              title="Remove dataset"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Upload zone or loaded state */}
      {!schema ? (
        <div
          onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`
            relative border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-200 cursor-pointer
            ${dragOver
              ? `${colors.border} ${colors.bg}`
              : 'border-slate-800 hover:border-slate-700 hover:bg-slate-900/40'
            }
            ${disabled ? 'opacity-40 cursor-not-allowed' : ''}
          `}
          onClick={() => !disabled && fileRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && !disabled && fileRef.current?.click()}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx,.xls,.txt"
            className="hidden"
            disabled={disabled}
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
          {isUploading ? (
            <div className="space-y-2">
              <div className={`w-8 h-8 rounded-full border-2 border-t-transparent ${colors.text.replace('text-', 'border-')} animate-spin mx-auto`} />
              <p className="text-xs text-slate-500">Parsing dataset…</p>
            </div>
          ) : (
            <div className="space-y-2">
              <Upload className={`w-7 h-7 mx-auto ${colors.text} opacity-60`} />
              <div>
                <p className="text-sm text-slate-300 font-medium">Drop CSV or XLSX here</p>
                <p className="text-xs text-slate-600 mt-0.5">or click to browse</p>
              </div>
              <p className="text-xs text-slate-700">.csv · .xlsx · .xls · .txt</p>
            </div>
          )}
        </div>
      ) : (
        <div className={`rounded-2xl border ${colors.border} bg-slate-900/60 p-4 space-y-3`}>
          {/* File info */}
          <div className="flex items-center space-x-3">
            <div className={`w-8 h-8 rounded-xl ${colors.bg} flex items-center justify-center shrink-0`}>
              <FileText className={`w-4 h-4 ${colors.text}`} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-slate-200 truncate">{schema.filename}</p>
              <p className="text-xs text-slate-500">
                {schema.row_count.toLocaleString()} rows · {schema.columns.length} columns
              </p>
            </div>
            <CheckCircle2 className={`w-4 h-4 ${colors.text} shrink-0`} />
          </div>

          {/* Column chips */}
          <div className="flex flex-wrap gap-1.5">
            {schema.columns.map((col) => (
              <span
                key={col.name}
                className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-800 text-xs text-slate-300 border border-slate-700/60"
                title={`${col.non_empty_count} non-empty values`}
              >
                {col.name}
              </span>
            ))}
          </div>

          {/* Preview table */}
          {showPreview && schema.preview_rows.length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-slate-800 mt-2">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-800">
                    {schema.columns.map((col) => (
                      <th key={col.name} className="px-3 py-2 text-left text-slate-500 font-medium whitespace-nowrap">
                        {col.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {schema.preview_rows.slice(0, 5).map((row, i) => (
                    <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                      {schema.columns.map((col) => (
                        <td key={col.name} className="px-3 py-2 text-slate-300 font-mono truncate max-w-[120px]">
                          {row[col.name] || <span className="text-slate-700">—</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
