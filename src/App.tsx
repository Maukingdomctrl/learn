/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { ExtractionInspectorView } from './components/ExtractionInspectorView';
import { QuestionGeneratorView } from './components/QuestionGeneratorView';
import { RubricAuditorView } from './components/RubricAuditorView';
import { TestSuiteSchemaView } from './components/TestSuiteSchemaView';
import {
  DEFAULT_RUBRIC_THRESHOLDS,
  type RubricThresholds,
} from './utils/engineLogic';

type ActiveTab = 'extraction' | 'generator' | 'rubric' | 'tests';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('generator');
  const [engineOutput, setEngineOutput] = useState<any | null>(null);
  const [extractionData, setExtractionData] = useState<any | null>(null);
  const [imageScanExtraction, setImageScanExtraction] = useState<any | null>(null);
  const [passages, setPassages] = useState<any[]>([]);
  const [thresholds, setThresholds] = useState<RubricThresholds>(DEFAULT_RUBRIC_THRESHOLDS);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;
    async function loadInitialState() {
      try {
        const res = await fetch('/api/initial-state');
        if (!res.ok) throw new Error('Failed to load initial fixtures');
        const data = await res.json();
        if (!mounted) return;
        setEngineOutput(data.sampleOutput);
        setExtractionData(data.sampleOutput?.extraction_summary || null);
        setImageScanExtraction(data.imageScanExtraction || null);
        setPassages(data.passages || []);
      } catch (err: any) {
        if (mounted) setErrorMsg(err?.message || 'Error loading engine state.');
      } finally {
        if (mounted) setIsLoading(false);
      }
    }
    loadInitialState();
    return () => {
      mounted = false;
    };
  }, []);

  const handleRunExtraction = async (payload: {
    pdfFixturePath?: string;
    pdfBase64?: string;
    extractedText?: string;
  }) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Extraction request failed');
      setExtractionData(data);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Extraction failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateQuestions = async (params: {
    classLevel: number;
    subject: string;
    questionCount: number;
    provider: string;
    sourceMode: 'pdf' | 'text';
    pdfFixturePath?: string;
    extractedText?: string;
  }) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...params,
          rubricConfig: thresholds,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Generation request failed');
      setEngineOutput(data);
      if (data.extraction_summary) {
        setExtractionData(data.extraction_summary);
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Question generation failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleScoreCandidate = async (payload: {
    candidate: any;
    classLevel: number;
    subject: string;
    rubricConfig: RubricThresholds;
  }) => {
    const res = await fetch('/api/score-candidate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Candidate audit failed');
    return data;
  };

  const handleRunTests = async () => {
    const res = await fetch('/api/run-tests', { method: 'POST' });
    return await res.json();
  };

  const handleExportJson = () => {
    if (!engineOutput) return;
    const jsonString = JSON.stringify(engineOutput.questions || [], null, 2);
    navigator.clipboard?.writeText(jsonString).catch(() => {});
    setCopyFeedback(true);
    setTimeout(() => setCopyFeedback(false), 1800);
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 flex flex-col">
      {/* Strict 3-Zone Top Bar Contract */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-8">
          {/* Zone 1: Single text element wordmark */}
          <a
            href="#top"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('extraction');
            }}
            className="text-lg font-bold tracking-tight text-slate-900 whitespace-nowrap shrink-0"
          >
            Learn Question Engine
          </a>

          {/* Zone 2: 4 concise single-line text navigation links */}
          <nav className="flex items-center gap-6 text-sm font-medium text-slate-600 overflow-x-auto">
            <button
              type="button"
              onClick={() => setActiveTab('extraction')}
              className={`py-1 transition-colors whitespace-nowrap shrink-0 border-b-2 ${
                activeTab === 'extraction'
                  ? 'border-sky-700 text-slate-900 font-semibold'
                  : 'border-transparent hover:text-slate-900'
              }`}
            >
              Extraction &amp; Notation
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('generator')}
              className={`py-1 transition-colors whitespace-nowrap shrink-0 border-b-2 ${
                activeTab === 'generator'
                  ? 'border-sky-700 text-slate-900 font-semibold'
                  : 'border-transparent hover:text-slate-900'
              }`}
            >
              Question Studio
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('rubric')}
              className={`py-1 transition-colors whitespace-nowrap shrink-0 border-b-2 ${
                activeTab === 'rubric'
                  ? 'border-sky-700 text-slate-900 font-semibold'
                  : 'border-transparent hover:text-slate-900'
              }`}
            >
              Quality Rubric
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('tests')}
              className={`py-1 transition-colors whitespace-nowrap shrink-0 border-b-2 ${
                activeTab === 'tests'
                  ? 'border-sky-700 text-slate-900 font-semibold'
                  : 'border-transparent hover:text-slate-900'
              }`}
            >
              Tests &amp; Schema
            </button>
          </nav>

          {/* Zone 3: 1 primary action */}
          <div className="shrink-0">
            <button
              type="button"
              onClick={handleExportJson}
              className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              {copyFeedback ? 'Copied JSON Schema' : 'Copy Questions JSON'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 space-y-6">
        {/* Compact Context Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 pb-5">
          <div className="space-y-1 max-w-3xl">
            <div className="text-xs text-slate-500 font-mono">
              Standalone Python Module (`question_quality_engine.py`) · ICSE Classes 8, 9, 10, 11 &amp; 12
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight text-balance">
              Curriculum-Grounded AI Question Generation &amp; PDF Extraction Engine
            </h1>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-600 font-mono tabular-nums shrink-0">
            <span>Pages Read: {extractionData?.page_count ?? 3}</span>
            <span aria-hidden="true">·</span>
            <span>Tables: {extractionData?.tables?.length ?? 2}</span>
            <span aria-hidden="true">·</span>
            <span>Questions Validated: {engineOutput?.questions?.length ?? 0}</span>
          </div>
        </div>

        {errorMsg && (
          <div
            role="alert"
            className="bg-red-50 border border-red-200 text-red-900 rounded-xl p-4 text-xs font-medium flex items-center justify-between"
          >
            <span>✕ Error: {errorMsg}</span>
            <button
              type="button"
              onClick={() => setErrorMsg(null)}
              className="text-red-700 underline ml-4 whitespace-nowrap shrink-0"
            >
              Dismiss
            </button>
          </div>
        )}

        {activeTab === 'extraction' && (
          <ExtractionInspectorView
            extraction={extractionData}
            imageScanExtraction={imageScanExtraction}
            passages={passages}
            onRunExtraction={handleRunExtraction}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'generator' && (
          <QuestionGeneratorView
            questions={engineOutput?.questions || []}
            analysisSummary={engineOutput?.analysis_summary}
            metadata={engineOutput?.metadata}
            thresholds={thresholds}
            onGenerate={handleGenerateQuestions}
            isGenerating={isLoading}
          />
        )}

        {activeTab === 'rubric' && (
          <RubricAuditorView
            thresholds={thresholds}
            onChangeThresholds={setThresholds}
            onScoreCandidate={handleScoreCandidate}
          />
        )}

        {activeTab === 'tests' && (
          <TestSuiteSchemaView
            fullEngineOutput={engineOutput}
            onRunTests={handleRunTests}
          />
        )}
      </main>

      {/* Quiet Footer */}
      <footer className="bg-white border-t border-slate-200 px-6 py-4 mt-12">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
          <span>
            Standalone Python Question-Generation Engine (`question_quality_engine.py` &amp; `provider_adapters.py`)
          </span>
          <span>
            Designed for future integration into Learn · ICSE Classes 8–12 Curriculum Grounded
          </span>
        </div>
      </footer>
    </div>
  );
}
