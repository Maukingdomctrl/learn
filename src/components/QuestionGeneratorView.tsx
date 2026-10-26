import React, { useState } from 'react';
import {
  RUBRIC_CRITERIA_METADATA,
  computeSetEvaluationMetrics,
  evaluateQuestionAgainstThresholds,
  type QuestionRecord,
  type RubricThresholds,
} from '../utils/engineLogic';
import { ScientificText } from './ScientificText';

interface QuestionGeneratorProps {
  questions: QuestionRecord[];
  analysisSummary: any;
  metadata: any;
  thresholds: RubricThresholds;
  onGenerate: (params: {
    classLevel: number;
    subject: string;
    questionCount: number;
    provider: string;
    sourceMode: 'pdf' | 'text';
    pdfFixturePath?: string;
    extractedText?: string;
  }) => Promise<void>;
  isGenerating: boolean;
}

const ICSE_SUBJECTS = [
  'History & Civics',
  'Chemistry & Physics',
  'Chemistry',
  'Physics',
  'Mathematics',
  'Biology',
  'Geography',
];

export const QuestionGeneratorView: React.FC<QuestionGeneratorProps> = ({
  questions,
  analysisSummary,
  metadata,
  thresholds,
  onGenerate,
  isGenerating,
}) => {
  const [pdfFixturePath, setPdfFixturePath] = useState<string>(
    'public/assets/aistudio/indian_constitution_history_lesson_0b1adbb9.pdf'
  );
  const [classLevel, setClassLevel] = useState<number>(metadata?.class_level || 8);
  const [subject, setSubject] = useState<string>(metadata?.subject || 'History & Civics');
  const [questionCount, setQuestionCount] = useState<number>(metadata?.requested_question_count || 7);
  const [provider, setProvider] = useState<string>('auto');
  const [statusFilter, setStatusFilter] = useState<'all' | 'accepted' | 'needs_review' | 'rejected'>('all');
  const [showLearningPoints, setShowLearningPoints] = useState<boolean>(false);

  // Re-evaluate questions live against current configurable rubric thresholds
  const evaluatedQuestions = questions.map((q) => evaluateQuestionAgainstThresholds(q, thresholds));
  const liveMetrics = computeSetEvaluationMetrics(evaluatedQuestions);

  const filteredQuestions = evaluatedQuestions.filter((q) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'accepted') {
      return q.validation_status === 'accepted' || q.validation_status === 'revised';
    }
    return q.validation_status === statusFilter;
  });

  const handlePdfPresetChange = (newPath: string) => {
    setPdfFixturePath(newPath);
    if (newPath.includes('indian_constitution')) {
      setClassLevel(8);
      setSubject('History & Civics');
      setQuestionCount(7);
    } else {
      setClassLevel(10);
      setSubject('Chemistry & Physics');
      setQuestionCount(6);
    }
  };

  const handleRunGeneration = async (e: React.FormEvent) => {
    e.preventDefault();
    await onGenerate({
      classLevel,
      subject,
      questionCount,
      provider,
      sourceMode: 'pdf',
      pdfFixturePath,
    });
  };

  return (
    <div className="space-y-8">
      {/* Generation Control Deck */}
      <form
        onSubmit={handleRunGeneration}
        className="bg-white border border-slate-200 rounded-xl p-6 space-y-5"
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              02. Curriculum-Grounded Question Generation Studio (ICSE Classes 8–12)
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              Adapts cognitive complexity, vocabulary, and analytical rigor to the selected ICSE class while verifying source evidence and calculations.
            </p>
          </div>
          <div className="text-xs text-slate-500 font-mono tabular-nums shrink-0">
            Active Band: {classLevel <= 10 ? 'ICSE Classes 8–10 (Foundational & Reasoning)' : 'ICSE Classes 11–12 (Advanced Analytical & Multi-Step)'}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4 items-end">
          {/* Source PDF Selector */}
          <div className="lg:col-span-2">
            <label htmlFor="icse-pdf-select" className="block text-xs font-semibold text-slate-700 mb-1.5">
              Curriculum PDF Document
            </label>
            <select
              id="icse-pdf-select"
              value={pdfFixturePath}
              onChange={(e) => handlePdfPresetChange(e.target.value)}
              className="w-full text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-600"
            >
              <option value="public/assets/aistudio/indian_constitution_history_lesson_0b1adbb9.pdf">
                The Making of the Indian Constitution (Standard 8 PDF)
              </option>
              <option value="fixtures/icse_sample_science_history.pdf">
                ICSE Multi-Page Science, History &amp; Calculus PDF
              </option>
            </select>
          </div>

          {/* ICSE Class Level Selector */}
          <div>
            <label htmlFor="icse-class-select" className="block text-xs font-semibold text-slate-700 mb-1.5">
              ICSE Class Level
            </label>
            <select
              id="icse-class-select"
              value={classLevel}
              onChange={(e) => setClassLevel(Number(e.target.value))}
              className="w-full text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-600"
            >
              {[8, 9, 10, 11, 12].map((cls) => (
                <option key={cls} value={cls}>
                  Class {cls} (ICSE/ISC)
                </option>
              ))}
            </select>
          </div>

          {/* Subject Selector */}
          <div>
            <label htmlFor="icse-subject-select" className="block text-xs font-semibold text-slate-700 mb-1.5">
              Subject
            </label>
            <select
              id="icse-subject-select"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-600"
            >
              {ICSE_SUBJECTS.map((subj) => (
                <option key={subj} value={subj}>
                  {subj}
                </option>
              ))}
            </select>
          </div>

          {/* Question Count */}
          <div>
            <label htmlFor="question-count-input" className="block text-xs font-semibold text-slate-700 mb-1.5">
              Desired Question Count: <span className="font-mono tabular-nums">{questionCount}</span>
            </label>
            <input
              id="question-count-input"
              type="range"
              min={2}
              max={8}
              value={questionCount}
              onChange={(e) => setQuestionCount(Number(e.target.value))}
              className="w-full accent-sky-700"
            />
          </div>

          {/* AI Provider Adapter */}
          <div>
            <label htmlFor="provider-select" className="block text-xs font-semibold text-slate-700 mb-1.5">
              AI Provider Adapter
            </label>
            <select
              id="provider-select"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-600"
            >
              <option value="auto">Auto (Gemini 3.8 Flash / Deterministic)</option>
              <option value="gemini">Gemini 3.8 Flash Adapter</option>
              <option value="deterministic">Deterministic Pedagogical Synthesizer</option>
            </select>
          </div>

          {/* Submit */}
          <div>
            <button
              type="submit"
              disabled={isGenerating}
              className="w-full px-4 py-2 text-xs font-semibold text-white bg-sky-700 hover:bg-sky-800 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              {isGenerating ? 'Generating & Validating...' : 'Generate Questions'}
            </button>
          </div>
        </div>
      </form>

      {/* Evaluation Metrics Strip (Full-Width 4-Column Row) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-1">
          <div className="text-xs text-slate-500">Source Evidence Grounding</div>
          <div className="text-2xl font-bold text-slate-900 font-mono tabular-nums">
            {liveMetrics.valid_source_evidence_pct}%
          </div>
          <div className="text-xs text-slate-600">
            <span>● Verified verbatim or high-overlap evidence</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-1">
          <div className="text-xs text-slate-500">Weighted Average Rubric Score</div>
          <div className="text-2xl font-bold text-slate-900 font-mono tabular-nums">
            {liveMetrics.average_rubric_score.toFixed(2)} <span className="text-sm font-normal text-slate-500">/ 5.00</span>
          </div>
          <div className="text-xs text-slate-600 tabular-nums">
            Threshold: ≥ {thresholds.min_average_score.toFixed(2)}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-1">
          <div className="text-xs text-slate-500">Question-Type Variety</div>
          <div className="text-2xl font-bold text-slate-900 font-mono tabular-nums">
            {liveMetrics.distinct_question_types} <span className="text-sm font-normal text-slate-500">categories</span>
          </div>
          <div className="text-xs text-slate-600 tabular-nums">
            Duplicate rate: {liveMetrics.duplicate_rate_pct}%
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-1">
          <div className="text-xs text-slate-500">Rubric Validation Breakdown</div>
          <div className="text-2xl font-bold text-slate-900 font-mono tabular-nums">
            {liveMetrics.accepted_count} <span className="text-sm font-normal text-slate-500">/ {liveMetrics.total_questions} Accepted</span>
          </div>
          <div className="text-xs text-slate-600 tabular-nums">
            {liveMetrics.needs_review_count} Needs Review · {liveMetrics.rejected_count} Rejected
          </div>
        </div>
      </div>

      {/* Filter Bar & Prioritized Learning Points Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-1 p-1 bg-slate-200/70 rounded-lg">
          <button
            type="button"
            onClick={() => setStatusFilter('all')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 tabular-nums ${
              statusFilter === 'all' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            All Questions ({evaluatedQuestions.length})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter('accepted')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 tabular-nums ${
              statusFilter === 'accepted' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            ● Accepted ({liveMetrics.accepted_count})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter('needs_review')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 tabular-nums ${
              statusFilter === 'needs_review' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            ▲ Needs Review ({liveMetrics.needs_review_count})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter('rejected')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 tabular-nums ${
              statusFilter === 'rejected' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            ✕ Rejected ({liveMetrics.rejected_count})
          </button>
        </div>

        <button
          type="button"
          onClick={() => setShowLearningPoints(!showLearningPoints)}
          className="px-3.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0"
        >
          {showLearningPoints
            ? 'Hide Source Learning Points'
            : `Inspect Prioritized Learning Points (${analysisSummary?.total_learning_points || 0})`}
        </button>
      </div>

      {/* Collapsible Source Analysis & Learning Points Drawer */}
      {showLearningPoints && analysisSummary?.learning_points && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">
              Step 2 &amp; 3: Prioritized Source Learning Points (Pre-Generation Analysis)
            </h3>
            <span className="text-xs text-slate-500 font-mono tabular-nums">
              Chunks: {analysisSummary.chunk_count || 1} · Total Learning Points: {analysisSummary.total_learning_points}
            </span>
          </div>
          <div className="divide-y divide-slate-100 max-h-72 overflow-y-auto">
            {analysisSummary.learning_points.map((lp: any) => (
              <div key={lp.id} className="py-3 space-y-1 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold text-slate-900">{lp.summary}</span>
                  <div className="text-slate-500 font-mono tabular-nums">
                    <span>Category: {lp.category}</span>
                    <span aria-hidden="true"> · </span>
                    <span>Priority: {lp.importance_score}</span>
                    <span aria-hidden="true"> · </span>
                    <span>Page {lp.source_page ?? 'null'}</span>
                  </div>
                </div>
                <p className="text-slate-600 font-mono text-[11px]">{lp.source_evidence}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Question Cards List */}
      <div className="space-y-4">
        {filteredQuestions.map((q) => {
          const statusLabel =
            q.validation_status === 'accepted'
              ? '● ACCEPTED'
              : q.validation_status === 'revised'
              ? '◆ REVISED & ACCEPTED'
              : q.validation_status === 'needs_review'
              ? '▲ NEEDS EDUCATOR REVIEW'
              : '✕ REJECTED BY RUBRIC';

          const statusColor =
            q.validation_status === 'accepted' || q.validation_status === 'revised'
              ? 'text-emerald-700'
              : q.validation_status === 'needs_review'
              ? 'text-amber-700'
              : 'text-red-700';

          return (
            <article
              key={q.question_id}
              className="bg-white border border-slate-200 rounded-xl p-6 space-y-5"
            >
              {/* Unboxed Metadata Kicker Line (Zero-Pill Compliance) */}
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs border-b border-slate-100 pb-3">
                <div className="flex flex-wrap items-center gap-2 text-slate-600 font-mono tabular-nums">
                  <span className="font-semibold text-slate-900">{q.question_id.toUpperCase()}</span>
                  <span aria-hidden="true">·</span>
                  <span>Type: {q.question_type.replace('_', '/')}</span>
                  <span aria-hidden="true">·</span>
                  <span>Difficulty: {q.difficulty}</span>
                  <span aria-hidden="true">·</span>
                  <span>
                    Source Page: {q.source_page !== null ? `Page ${q.source_page}` : 'null (unpaginated)'}
                  </span>
                </div>

                <div className="flex items-center gap-3 font-mono text-xs tabular-nums">
                  <span className={`font-semibold ${statusColor}`}>{statusLabel}</span>
                  <span aria-hidden="true">·</span>
                  <span className="font-semibold text-slate-900">
                    Rubric Avg: {q.quality_scores.average_score.toFixed(2)} / 5.00
                  </span>
                </div>
              </div>

              {/* Question & Model Answer */}
              <div className="space-y-3">
                <h3 className="text-base font-semibold text-slate-900 leading-snug">
                  <ScientificText text={q.question} />
                </h3>
                <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-4 space-y-1.5">
                  <div className="text-xs font-semibold text-slate-700">
                    Model Answer (Curriculum-Grounded)
                  </div>
                  <p className="text-sm text-slate-800 leading-relaxed font-mono">
                    <ScientificText text={q.answer} />
                  </p>
                </div>
              </div>

              {/* Learning Point & Verbatim Source Evidence */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 text-xs">
                <div className="bg-slate-50/60 border border-slate-200/70 rounded-lg p-3.5 space-y-1">
                  <div className="font-semibold text-slate-700">Target Learning Point</div>
                  <p className="text-slate-800">
                    <ScientificText text={q.learning_point} />
                  </p>
                </div>
                <div className="bg-slate-50/60 border border-slate-200/70 rounded-lg p-3.5 space-y-1">
                  <div className="font-semibold text-slate-700">
                    Supporting Source Evidence (Page {q.source_page ?? 'null'})
                  </div>
                  <p className="text-slate-700 font-mono text-[11px] leading-relaxed">
                    &ldquo;<ScientificText text={q.source_evidence} />&rdquo;
                  </p>
                </div>
              </div>

              {/* 7-Criterion Quality Rubric Breakdown */}
              <div className="pt-2 border-t border-slate-100 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="font-semibold text-slate-700">
                    7-Criterion Quality Rubric Scores (1–5 Scale)
                  </span>
                  {q.review_notes?.length > 0 && (
                    <span className="text-slate-600 font-mono">
                      Review Note: {q.review_notes[0]}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
                  {RUBRIC_CRITERIA_METADATA.map((crit) => {
                    const val = q.quality_scores[crit.key];
                    return (
                      <div
                        key={crit.key}
                        className="bg-slate-50 border border-slate-200/80 rounded-lg p-2.5 space-y-1"
                      >
                        <div className="text-[11px] text-slate-600 truncate" title={crit.label}>
                          {crit.label}
                        </div>
                        <div className="flex items-baseline justify-between font-mono tabular-nums">
                          <span className="text-sm font-bold text-slate-900">{val} / 5</span>
                          <span className="text-[10px] text-slate-500">
                            {val >= 4 ? '● Pass' : val === 3 ? '◆ Min' : '✕ Low'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
};
