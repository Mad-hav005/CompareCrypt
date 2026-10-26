import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Play, Loader2, AlertOctagon, Database, Settings2, BarChart3, Info } from 'lucide-react';
import { DatasetUploader } from './DatasetUploader';
import { AttributeMapper } from './AttributeMapper';
import { JobProgress } from './JobProgress';
import { ResultsPanel } from './ResultsPanel';
import { apiService } from '../../services/api';
import type {
  DatasetSchema,
  AttributeMapping,
  ERJobStatus,
  ERJobResults,
  MatchStrategy,
} from '../../types/api';

// ─── Demo data ────────────────────────────────────────────────────────────────

const DEMO_CSV_A = `Name,Address,Phone,Email,City
Alice Johnson,123 Main St,555-0101,alice@example.com,New York
Bob Smythe,456 Oak Ave,555-0102,bob.smythe@example.com,Chicago
Charlie Browne,789 Elm Dr,555-0103,charlie@example.com,Houston
Diana Prince,321 Park Blvd,555-0104,diana@example.com,Phoenix
Edward Norton,654 Pine St,555-0105,edward@example.com,Philadelphia`;

const DEMO_CSV_B = `Full Name,Residential Address,Mobile,Email ID,Location
Alice Johnsun,123 Main Street,555-0101,alice@example.com,New York
Robert Smith,456 Oak Avenue,555-0199,rob.smith@example.com,Chicago
Charlie Brown,789 Elm Drive,555-0103,charlie@example.com,Houston
Diana Prynce,321 Park Boulevard,555-0104,diana@example.com,Phoenix
Frank Castle,987 River Rd,555-0106,frank@example.com,San Antonio`;

type Step = 'upload' | 'map' | 'run' | 'results';

function makeDefaultMappings(schemaA: DatasetSchema | null, schemaB: DatasetSchema | null): AttributeMapping[] {
  if (!schemaA || !schemaB) return [];
  const colsA = schemaA.columns;
  const colsB = schemaB.columns;
  const count = Math.min(colsA.length, colsB.length);
  return Array.from({ length: count }, (_, i) => ({
    column_a: colsA[i].name,
    column_b: colsB[i].name,
    strategy: 'fuzzy' as MatchStrategy,
    weight: 1.0,
    fuzzy_threshold: 0.80,
  }));
}

function csvStringToFile(csvString: string, filename: string): File {
  const blob = new Blob([csvString], { type: 'text/csv' });
  return new File([blob], filename, { type: 'text/csv' });
}

// ─── Main Component ───────────────────────────────────────────────────────────

export const EntityResolutionPage: React.FC = () => {
  const [step, setStep] = useState<Step>('upload');

  // Job state
  const [jobId, setJobId] = useState<string | null>(null);
  const [schemaA, setSchemaA] = useState<DatasetSchema | null>(null);
  const [schemaB, setSchemaB] = useState<DatasetSchema | null>(null);
  const [uploadingA, setUploadingA] = useState(false);
  const [uploadingB, setUploadingB] = useState(false);

  // Mappings & config
  const [mappings, setMappings] = useState<AttributeMapping[]>([]);
  const [overallThreshold, setOverallThreshold] = useState(0.70);
  const [normalize, setNormalize] = useState(true);

  // Job lifecycle
  const [jobStatus, setJobStatus] = useState<ERJobStatus | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Results
  const [erResults, setErResults] = useState<ERJobResults | null>(null);
  const [sortBy, setSortBy] = useState('overall_score');
  const [sortDesc, setSortDesc] = useState(true);
  const [minScore, setMinScore] = useState<number | undefined>(undefined);

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Ensure a job ID exists
  const ensureJobId = useCallback(async (): Promise<string> => {
    if (jobId) return jobId;
    const { job_id } = await apiService.createERJob();
    setJobId(job_id);
    return job_id;
  }, [jobId]);

  // Upload handler
  const handleUpload = useCallback(
    async (party: 'A' | 'B', file: File) => {
      if (party === 'A') setUploadingA(true);
      else setUploadingB(true);
      setError(null);
      try {
        const jid = await ensureJobId();
        const resp = await apiService.uploadERDataset(jid, party, file);
        if (party === 'A') {
          setSchemaA(resp.dataset_schema);
        } else {
          setSchemaB(resp.dataset_schema);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (party === 'A') setUploadingA(false);
        else setUploadingB(false);
      }
    },
    [ensureJobId]
  );

  // Auto-populate default mappings when both schemas load
  useEffect(() => {
    if (schemaA && schemaB && mappings.length === 0) {
      setMappings(makeDefaultMappings(schemaA, schemaB));
    }
  }, [schemaA, schemaB, mappings.length]);

  // Mapping handlers
  const handleAddMapping = () => {
    const firstA = schemaA?.columns[0]?.name ?? '';
    const firstB = schemaB?.columns[0]?.name ?? '';
    setMappings((prev) => [
      ...prev,
      { column_a: firstA, column_b: firstB, strategy: 'fuzzy', weight: 1.0, fuzzy_threshold: 0.80 },
    ]);
  };

  const handleUpdateMapping = (index: number, update: Partial<AttributeMapping>) => {
    setMappings((prev) => prev.map((m, i) => (i === index ? { ...m, ...update } : m)));
  };

  const handleRemoveMapping = (index: number) => {
    setMappings((prev) => prev.filter((_, i) => i !== index));
  };

  // Polling
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (jid: string) => {
      stopPolling();
      pollIntervalRef.current = setInterval(async () => {
        try {
          const status = await apiService.getERStatus(jid);
          setJobStatus(status);
          if (status.phase === 'complete' || status.phase === 'error') {
            stopPolling();
            if (status.phase === 'complete') {
              // Fetch first page of results
              const res = await apiService.getERResults(jid, 1, 50, 'overall_score', true, minScore);
              setErResults(res);
              setStep('results');
              setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);
            }
          }
        } catch {
          stopPolling();
        }
      }, 600);
    },
    [stopPolling, minScore]
  );

  useEffect(() => () => stopPolling(), [stopPolling]);

  // Start job
  const handleStart = async () => {
    if (!jobId || !schemaA || !schemaB) return;
    const activeMappings = mappings.filter((m) => m.strategy !== 'ignore');
    if (activeMappings.length === 0) {
      setError('At least one non-ignored attribute mapping is required.');
      return;
    }
    setError(null);
    setIsStarting(true);
    setJobStatus(null);
    setErResults(null);
    setStep('run');
    try {
      await apiService.startERJob({ job_id: jobId, mappings, overall_threshold: overallThreshold, normalize });
      startPolling(jobId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setStep('map');
    } finally {
      setIsStarting(false);
    }
  };

  // Results fetch (for page/sort/filter changes)
  const fetchResults = useCallback(
    async (page: number, by: string, desc: boolean, min: number | undefined) => {
      if (!jobId) return;
      try {
        const res = await apiService.getERResults(jobId, page, 50, by, desc, min);
        setErResults(res);
      } catch { /* ignore */ }
    },
    [jobId]
  );

  // Demo loader
  const handleLoadDemo = async () => {
    // Reset
    setSchemaA(null);
    setSchemaB(null);
    setMappings([]);
    setJobStatus(null);
    setErResults(null);
    setError(null);
    setStep('upload');
    const { job_id } = await apiService.createERJob();
    setJobId(job_id);
    const fileA = csvStringToFile(DEMO_CSV_A, 'party_a_demo.csv');
    const fileB = csvStringToFile(DEMO_CSV_B, 'party_b_demo.csv');
    setUploadingA(true);
    setUploadingB(true);
    try {
      const [respA, respB] = await Promise.all([
        apiService.uploadERDataset(job_id, 'A', fileA),
        apiService.uploadERDataset(job_id, 'B', fileB),
      ]);
      setSchemaA(respA.dataset_schema);
      setSchemaB(respB.dataset_schema);
      // Set smart default mappings for the demo
      setMappings([
        { column_a: 'Name', column_b: 'Full Name', strategy: 'fuzzy', weight: 2.0, fuzzy_threshold: 0.75 },
        { column_a: 'Address', column_b: 'Residential Address', strategy: 'fuzzy', weight: 1.0, fuzzy_threshold: 0.70 },
        { column_a: 'Phone', column_b: 'Mobile', strategy: 'exact', weight: 2.0, fuzzy_threshold: 0.80 },
        { column_a: 'Email', column_b: 'Email ID', strategy: 'exact', weight: 3.0, fuzzy_threshold: 0.80 },
        { column_a: 'City', column_b: 'Location', strategy: 'fuzzy', weight: 1.0, fuzzy_threshold: 0.80 },
      ]);
      setStep('map');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploadingA(false);
      setUploadingB(false);
    }
  };

  const canProceedToMap = schemaA && schemaB;
  const canRun = canProceedToMap && mappings.length > 0 && mappings.some((m) => m.strategy !== 'ignore');
  const isRunning = jobStatus?.phase !== undefined && !['complete', 'error', 'queued'].includes(jobStatus.phase);

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-white flex items-center space-x-2">
            <Database className="w-5 h-5 text-indigo-400" />
            <span>Entity Resolution</span>
          </h2>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Upload two datasets with different schemas, map corresponding attributes, and find matching records
            using privacy-preserving OPRF-based matching.
          </p>
        </div>
        <button
          type="button"
          onClick={handleLoadDemo}
          disabled={uploadingA || uploadingB || isRunning}
          className="flex items-center space-x-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors disabled:opacity-40 shrink-0 mt-1"
        >
          <span>✦</span>
          <span>Load demo data</span>
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-start space-x-3 p-3.5 rounded-xl bg-rose-950/30 border border-rose-500/20 text-rose-300 text-xs">
          <AlertOctagon className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Step tabs */}
      <div className="flex items-center space-x-1 bg-slate-900 rounded-xl p-1 w-fit">
        {[
          { key: 'upload', icon: <Database className="w-3.5 h-3.5" />, label: 'Upload' },
          { key: 'map', icon: <Settings2 className="w-3.5 h-3.5" />, label: 'Map & Configure' },
          { key: 'run', icon: <Play className="w-3.5 h-3.5" />, label: 'Running' },
          { key: 'results', icon: <BarChart3 className="w-3.5 h-3.5" />, label: 'Results' },
        ].map(({ key, icon, label }) => {
          const isActive = step === key;
          const isDisabled = (key === 'map' && !canProceedToMap) || (key === 'run' && !isRunning && step !== 'run') || (key === 'results' && !erResults);
          return (
            <button
              key={key}
              type="button"
              onClick={() => {
                if (!isDisabled) setStep(key as Step);
              }}
              disabled={isDisabled}
              className={`
                flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all
                ${isActive
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
                }
              `}
            >
              {icon}
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      {/* ── Step: Upload ── */}
      {step === 'upload' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <DatasetUploader
              party="A"
              jobId={jobId ?? ''}
              schema={schemaA}
              isUploading={uploadingA}
              onUpload={(f) => handleUpload('A', f)}
              onClear={() => setSchemaA(null)}
              disabled={uploadingA || uploadingB}
            />
            <DatasetUploader
              party="B"
              jobId={jobId ?? ''}
              schema={schemaB}
              isUploading={uploadingB}
              onUpload={(f) => handleUpload('B', f)}
              onClear={() => setSchemaB(null)}
              disabled={uploadingA || uploadingB}
            />
          </div>
          {canProceedToMap && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setStep('map')}
                className="px-6 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-900/30 transition-all"
              >
                Configure mapping →
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Step: Map & Configure ── */}
      {step === 'map' && (
        <div className="space-y-6">
          <AttributeMapper
            schemaA={schemaA}
            schemaB={schemaB}
            mappings={mappings}
            onAddMapping={handleAddMapping}
            onUpdateMapping={handleUpdateMapping}
            onRemoveMapping={handleRemoveMapping}
            disabled={isRunning}
          />

          {/* Overall threshold + options */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-4">
            <h3 className="text-sm font-semibold text-slate-200">Match configuration</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-xs text-slate-400 font-medium">Overall match threshold</label>
                <div className="flex items-center space-x-3">
                  <input
                    type="range"
                    min={0}
                    max={100}
                    step={5}
                    value={Math.round(overallThreshold * 100)}
                    onChange={(e) => setOverallThreshold(parseInt(e.target.value) / 100)}
                    className="flex-1 accent-indigo-500"
                  />
                  <span className="text-sm font-bold font-mono text-indigo-400 w-12 text-right">
                    {Math.round(overallThreshold * 100)}%
                  </span>
                </div>
                <p className="text-xs text-slate-600">
                  Weighted average attribute similarity must reach this to be reported as a match.
                </p>
              </div>
              <div className="space-y-2">
                <label className="text-xs text-slate-400 font-medium">Options</label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={normalize}
                    onChange={(e) => setNormalize(e.target.checked)}
                    className="accent-indigo-500 w-3.5 h-3.5"
                  />
                  <span className="text-xs text-slate-300">Normalize strings (case-fold, strip whitespace)</span>
                </label>
              </div>
            </div>
          </div>

          {/* Privacy note */}
          <div className="flex items-start space-x-2 p-3 rounded-xl bg-slate-900/40 border border-slate-800/60 text-xs text-slate-600">
            <Info className="w-3.5 h-3.5 shrink-0 mt-0.5 text-indigo-800" />
            <span>
              <strong className="text-slate-500">Privacy model:</strong>{' '}
              Fuzzy attributes use 2Hash-DH OPRF (RFC 3526 2048-bit MODP, semi-honest). Exact attributes use OPRF-PSI.
              For large datasets, blocking pre-filters candidates using plaintext shingle-prefix similarity —
              this leaks coarse structural similarity of the blocking column. All matching is done server-side (simulated two-party).
              Non-matching records are not included in results.
            </span>
          </div>

          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => setStep('upload')}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              ← Back to upload
            </button>
            <button
              type="button"
              id="run-entity-resolution-btn"
              onClick={handleStart}
              disabled={!canRun || isStarting}
              className="flex items-center space-x-2.5 px-7 py-3 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-900/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isStarting ? (
                <><Loader2 className="w-4 h-4 animate-spin" /><span>Starting…</span></>
              ) : (
                <><Play className="w-4 h-4 fill-white" /><span>Run Entity Resolution</span></>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ── Step: Running ── */}
      {step === 'run' && (
        <div className="space-y-4">
          <JobProgress status={jobStatus} />
        </div>
      )}

      {/* ── Step: Results ── */}
      {step === 'results' && erResults && (
        <div ref={resultsRef} className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-slate-200">Entity Resolution Results</h3>
            <button
              type="button"
              onClick={() => { setStep('map'); setJobStatus(null); }}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              ← Modify configuration
            </button>
          </div>

          {/* Progress stats while viewing results */}
          {jobStatus && (
            <div className="flex items-center space-x-4 text-xs text-slate-500">
              <span>Elapsed: <span className="font-mono text-slate-300">{(jobStatus.elapsed_ms / 1000).toFixed(2)}s</span></span>
              <span>·</span>
              <span>Threshold: <span className="font-mono text-slate-300">{(overallThreshold * 100).toFixed(0)}%</span></span>
              <span>·</span>
              <span>Protocol: <span className="text-indigo-400">2Hash-DH OPRF</span></span>
            </div>
          )}

          <ResultsPanel
            results={erResults}
            jobId={jobId ?? ''}
            exportUrl={apiService.getERExportUrl(jobId ?? '')}
            onPageChange={(page) => {
              fetchResults(page, sortBy, sortDesc, minScore);
            }}
            onSortChange={(by, desc) => {
              setSortBy(by);
              setSortDesc(desc);
              fetchResults(1, by, desc, minScore);
            }}
            onFilterChange={(min) => {
              setMinScore(min);
              fetchResults(1, sortBy, sortDesc, min);
            }}
            currentSort={{ by: sortBy, desc: sortDesc }}
            currentMinScore={minScore}
          />
        </div>
      )}
    </div>
  );
};
