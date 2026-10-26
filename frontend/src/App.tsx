import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Header } from './components/Header';
import { ModeSelector } from './components/ModeSelector';
import { PartyInput } from './components/PartyInput';
import { ThresholdControl } from './components/ThresholdControl';
import { ProtocolProgress } from './components/ProtocolProgress';
import { ResultsDashboard } from './components/ResultsDashboard';
import { SecurityInfo } from './components/SecurityInfo';
import { ComparisonDashboard } from './components/ComparisonDashboard';
import { EntityResolutionPage } from './components/EntityResolution/EntityResolutionPage';
import { apiService } from './services/api';
import type {
  MatchingMode,
  HealthResponse,
  UnifiedMatchResult,
  ProtocolStage,
} from './types/api';
import { Play, AlertOctagon, Loader2 } from 'lucide-react';

const PROTOCOL_STAGES: ProtocolStage[] = [
  { id: 'shingle_extraction', label: 'Shingle Extraction', party: 'Alice & Bob', description: 'Generates boundary-padded unique bigrams', status: 'pending' },
  { id: 'alice_blinding', label: 'Alice Blinding', party: 'Alice', description: 'Blinds shingle group elements with secret scalars', status: 'pending' },
  { id: 'bob_evaluation', label: 'Bob OPRF Evaluation', party: 'Bob', description: 'Exponentiates Alice shingles with private key k', status: 'pending' },
  { id: 'bob_digest', label: 'Bob Digest Generation', party: 'Bob', description: 'Generates direct PRF digests for Bob shingles', status: 'pending' },
  { id: 'alice_unblinding', label: 'Alice Unblinding', party: 'Alice', description: 'Unblinds evaluated points into Alice PRF digests', status: 'pending' },
  { id: 'similarity_calc', label: 'Similarity Calculation', party: 'Alice', description: 'Counts intersection cardinality per record pair', status: 'pending' },
  { id: 'threshold_eval', label: 'Threshold Evaluation', party: 'Alice', description: 'Applies Sørensen-Dice threshold condition', status: 'pending' },
  { id: 'complete', label: 'Matching Complete', party: 'Alice', description: 'Outputs permitted match records to Alice', status: 'pending' },
];

const DEMO_ALICE = `Madhav Kumar\nJohn Smith\nAlice Johnson\nRobert Brown`;
const DEMO_BOB = `Madhav Kumer\nJohn Smith\nAlice Johnson\nRobert Browne`;

export const App: React.FC = () => {
  const [mode, setMode] = useState<MatchingMode>('entity_resolution');
  const [aliceInput, setAliceInput] = useState<string>(DEMO_ALICE);
  const [bobInput, setBobInput] = useState<string>(DEMO_BOB);
  const [threshold, setThreshold] = useState<number>(0.80);
  const [normalize, setNormalize] = useState<boolean>(true);

  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [currentStageIdx, setCurrentStageIdx] = useState<number>(-1);
  const [stages] = useState<ProtocolStage[]>(PROTOCOL_STAGES);

  const [result, setResult] = useState<UnifiedMatchResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);

  const resultsRef = useRef<HTMLDivElement>(null);

  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const res = await apiService.checkHealth();
      setHealth(res);
      setErrorMessage(null);
    } catch {
      setHealth(null);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const handleLoadDemoData = () => {
    setAliceInput(DEMO_ALICE);
    setBobInput(DEMO_BOB);
    setThreshold(0.80);
    setErrorMessage(null);
  };

  const handleRunMatching = async () => {
    const aliceRecords = aliceInput.split('\n').map((l) => l.trim()).filter((l) => l.length > 0);
    const bobRecords = bobInput.split('\n').map((l) => l.trim()).filter((l) => l.length > 0);

    if (aliceRecords.length === 0 || bobRecords.length === 0) {
      setErrorMessage('Both Party A and Party B must contain at least one valid record.');
      return;
    }

    setErrorMessage(null);
    setResult(null);
    setIsExecuting(true);

    const startTime = performance.now();

    let progressTimer: ReturnType<typeof setInterval> | null = null;
    let simulatedStage = 0;
    setCurrentStageIdx(0);

    if (mode === 'comparecrypt') {
      progressTimer = setInterval(() => {
        simulatedStage++;
        if (simulatedStage < PROTOCOL_STAGES.length - 1) {
          setCurrentStageIdx(simulatedStage);
        }
      }, 500);
    }

    try {
      if (mode === 'comparecrypt') {
        const response = await apiService.runThresholdCrypto(aliceRecords, bobRecords, threshold);
        const elapsed = performance.now() - startTime;

        const avgShingles = 15;
        const totalAliceShingles = aliceRecords.length * avgShingles;
        const totalBobShingles = bobRecords.length * avgShingles;
        const commBytes = totalAliceShingles * 260 + totalAliceShingles * 260 + totalBobShingles * 32;

        setResult({
          mode: 'comparecrypt',
          protocolName: response.protocol_name,
          aliceSize: response.alice_dataset_size,
          bobSize: response.bob_dataset_size,
          matchCount: response.match_count,
          threshold: response.threshold,
          executionTimeMs: elapsed,
          estimatedPayloadKb: commBytes / 1024.0,
          matches: response.matches.map((m) => ({
            aliceRecord: m.alice_record,
            bobRecord: m.bob_record,
            similarity: m.dice_similarity,
            isMatch: m.match_decision,
            intersectionCount: m.intersection_count,
          })),
        });
      } else if (mode === 'exact') {
        const response = await apiService.runExactPSI(aliceRecords, bobRecords, normalize);
        const elapsed = performance.now() - startTime;

        setResult({
          mode: 'exact',
          protocolName: response.protocol_name,
          aliceSize: response.alice_dataset_size,
          bobSize: response.bob_dataset_size,
          matchCount: response.match_count,
          threshold: 1.0,
          executionTimeMs: elapsed,
          matches: response.matches.map((m) => ({
            aliceRecord: m,
            bobRecord: m,
            similarity: 1.0,
            isMatch: true,
          })),
        });
      }

      setCurrentStageIdx(PROTOCOL_STAGES.length - 1);

      // Scroll to results after a short delay
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 200);

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(msg);
      setCurrentStageIdx(-1);
    } finally {
      if (progressTimer) clearInterval(progressTimer);
      setIsExecuting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header health={health} healthLoading={healthLoading} onRefreshHealth={checkHealth} />

      <main className="flex-1">
        {/* Top nav bar */}
        <div className="border-b border-slate-800/60">
          <div className={`mx-auto px-6 py-3 ${mode === 'comparison' ? 'max-w-5xl' : 'max-w-4xl'}`}>
            <ModeSelector
              currentMode={mode}
              onSelectMode={(newMode) => {
                setMode(newMode);
                setResult(null);
                setErrorMessage(null);
                setCurrentStageIdx(-1);
              }}
              disabled={isExecuting}
            />
          </div>
        </div>

        {/* Error alerts */}
        {(!healthLoading && !health) || errorMessage ? (
          <div className={`mx-auto px-6 pt-4 ${mode === 'comparison' ? 'max-w-5xl' : 'max-w-4xl'}`}>
            {!healthLoading && !health && (
              <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/20 flex items-start space-x-3 text-rose-300 mb-3">
                <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <p className="font-semibold text-rose-200">Backend is offline</p>
                  <p>
                    Cannot reach{' '}
                    <code className="bg-rose-900/30 px-1 rounded font-mono">
                      {import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}
                    </code>
                  </p>
                  <p className="text-rose-400/70">
                    Start:{' '}
                    <code className="bg-slate-900 px-1.5 py-0.5 rounded text-indigo-300 font-mono">
                      $env:PYTHONPATH="backend"; uvicorn app.main:app --port 8000
                    </code>
                  </p>
                </div>
              </div>
            )}
            {errorMessage && (
              <div className="p-3.5 rounded-xl bg-rose-950/30 border border-rose-500/20 flex items-center space-x-3 text-rose-300 text-xs">
                <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}
          </div>
        ) : null}

        {/* Page content */}
        <div className={`mx-auto px-6 py-12 ${mode === 'comparison' ? 'max-w-5xl' : 'max-w-4xl'}`}>
          {mode === 'comparison' ? (
            <ComparisonDashboard />
          ) : mode === 'entity_resolution' ? (
            <EntityResolutionPage />
          ) : (
            <div className="space-y-12">
              {/* ── Party Data ── */}
              <PartyInput
                aliceInput={aliceInput}
                bobInput={bobInput}
                onChangeAlice={setAliceInput}
                onChangeBob={setBobInput}
                onLoadDemoData={handleLoadDemoData}
                disabled={isExecuting}
              />

              {/* ── Threshold ── */}
              <div className="max-w-lg">
                <ThresholdControl
                  mode={mode}
                  threshold={threshold}
                  onChangeThreshold={setThreshold}
                  normalize={normalize}
                  onChangeNormalize={setNormalize}
                  disabled={isExecuting}
                />
              </div>

              {/* ── Run Button ── */}
              <div className="flex justify-start">
                <button
                  type="button"
                  id="run-private-matching-btn"
                  onClick={handleRunMatching}
                  disabled={isExecuting}
                  className={`
                    flex items-center space-x-2.5 px-8 py-3 rounded-xl text-sm font-semibold
                    transition-all duration-150
                    ${isExecuting
                      ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                      : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-900/30'
                    }
                  `}
                >
                  {isExecuting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Matching in progress…</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-white" />
                      <span>Run Private Matching</span>
                    </>
                  )}
                </button>
              </div>

              {/* ── Results (scroll target) ── */}
              <div ref={resultsRef}>
                {result && (
                  <div className="border-t border-slate-800/60 pt-10">
                    <ResultsDashboard result={result} />
                  </div>
                )}
              </div>

              {/* ── Protocol stages (collapsible) ── */}
              {mode === 'comparecrypt' && (
                <ProtocolProgress
                  stages={stages}
                  currentStageIndex={currentStageIdx}
                  isExecuting={isExecuting}
                />
              )}

              {/* ── Security & protocol details (collapsible) ── */}
              <SecurityInfo />
            </div>
          )}
        </div>
      </main>

      <footer className="border-t border-slate-800/40 py-6 text-center">
        <p className="text-xs text-slate-700">
          CompareCrypt &mdash; Secure Private Matching of Similar Data &mdash; Academic Research Prototype
        </p>
      </footer>
    </div>
  );
};

export default App;
