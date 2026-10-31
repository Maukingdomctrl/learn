import React, { useState } from 'react';
import {
  AUDITOR_PRESET_CASES,
  DEFAULT_RUBRIC_THRESHOLDS,
  RUBRIC_CRITERIA_METADATA,
  type RubricThresholds,
} from '../utils/engineLogic';

interface RubricAuditorProps {
  thresholds: RubricThresholds;
  onChangeThresholds: (next: RubricThresholds) => void;
  onScoreCandidate: (payload: {
    candidate: any;
    classLevel: number;
    subject: string;
    rubricConfig: RubricThresholds;
  }) => Promise<any>;
}

export const RubricAuditorView: React.FC<RubricAuditorProps> = ({
  thresholds,
  onChangeThresholds,
  onScoreCandidate,
}) => {
  const [selectedPresetId, setSelectedPresetId] = useState<string>(AUDITOR_PRESET_CASES[0].id);
  const [auditClassLevel, setAuditClassLevel] = useState<number>(AUDITOR_PRESET_CASES[0].class_level);
  const [auditSubject, setAuditSubject] = useState<string>(AUDITOR_PRESET_CASES[0].subject);
  const [candidateForm, setCandidateForm] = useState<any>(AUDITOR_PRESET_CASES[0].candidate);
  const [auditResult, setAuditResult] = useState<any | null>({
    question_id: 'audit_01',
    validation_status: 'accepted',
    source_page: 1,
    quality_scores: {
      curriculum_relevance: 5,
      source_fidelity: 5,
      clarity: 5,
      educational_value: 5,
      distinctness: 5,
      answer_quality: 5,
      grade_suitability: 5,
      average_score: 5.0,
    },
    review_notes: [
      "Balanced stoichiometry verified: {'H': 4, 'O': 2}",
      "Balanced stoichiometry verified: {'Cu': 1, 'S': 1, 'O': 4}",
      'Passed all 7 rubric criteria and source grounding checks.',
    ],
  });
  const [isScoring, setIsScoring] = useState<boolean>(false);

  const handleLoadPreset = async (presetId: string) => {
    const found = AUDITOR_PRESET_CASES.find((p) => p.id === presetId);
    if (!found) return;
    setSelectedPresetId(found.id);
    setAuditClassLevel(found.class_level);
    setAuditSubject(found.subject);
    setCandidateForm(found.candidate);
    setIsScoring(true);
    try {
      const res = await onScoreCandidate({
        candidate: found.candidate,
        classLevel: found.class_level,
        subject: found.subject,
        rubricConfig: thresholds,
      });
      setAuditResult(res);
    } finally {
      setIsScoring(false);
    }
  };

  const handleRunAudit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsScoring(true);
    try {
      const res = await onScoreCandidate({
        candidate: candidateForm,
        classLevel: auditClassLevel,
        subject: auditSubject,
        rubricConfig: thresholds,
      });
      setAuditResult(res);
    } finally {
      setIsScoring(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Split Layout: Left Configurable Rubric Thresholds & Scale Matrix (55%) | Right Live Candidate Auditor (45%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Configurable Rubric Thresholds & Documented 1–5 Scale */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  03. Configurable 7-Criterion Question-Quality Rubric
                </h2>
                <p className="text-sm text-slate-600 mt-1">
                  Adjust minimum pass thresholds and criterion weights. Changes apply immediately to question validation.
                </p>
              </div>
              <button
                type="button"
                onClick={() => onChangeThresholds(DEFAULT_RUBRIC_THRESHOLDS)}
                className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                Reset to Documented Defaults
              </button>
            </div>

            {/* Labeled Threshold Sliders */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div>
                <label
                  htmlFor="slider-min-avg"
                  className="block text-xs font-semibold text-slate-800 mb-1.5"
                >
                  Minimum Weighted Average Score:{' '}
                  <span className="font-mono tabular-nums">
                    {thresholds.min_average_score.toFixed(1)} / 5.0
                  </span>{' '}
                  <span className="text-slate-500 font-normal">(Default: 3.6)</span>
                </label>
                <input
                  id="slider-min-avg"
                  type="range"
                  min={2.5}
                  max={4.8}
                  step={0.1}
                  value={thresholds.min_average_score}
                  onChange={(e) =>
                    onChangeThresholds({
                      ...thresholds,
                      min_average_score: Number(e.target.value),
                    })
                  }
                  className="w-full accent-sky-700"
                />
              </div>

              <div>
                <label
                  htmlFor="slider-min-fidelity"
                  className="block text-xs font-semibold text-slate-800 mb-1.5"
                >
                  Minimum Source Fidelity Score:{' '}
                  <span className="font-mono tabular-nums">
                    {thresholds.min_source_fidelity} / 5
                  </span>{' '}
                  <span className="text-slate-500 font-normal">(Default: 4)</span>
                </label>
                <input
                  id="slider-min-fidelity"
                  type="range"
                  min={1}
                  max={5}
                  step={1}
                  value={thresholds.min_source_fidelity}
                  onChange={(e) =>
                    onChangeThresholds({
                      ...thresholds,
                      min_source_fidelity: Number(e.target.value),
                    })
                  }
                  className="w-full accent-sky-700"
                />
              </div>

              <div>
                <label
                  htmlFor="slider-min-criterion"
                  className="block text-xs font-semibold text-slate-800 mb-1.5"
                >
                  Minimum Any-Criterion Floor:{' '}
                  <span className="font-mono tabular-nums">
                    {thresholds.min_criterion_score} / 5
                  </span>{' '}
                  <span className="text-slate-500 font-normal">(Default: 3)</span>
                </label>
                <input
                  id="slider-min-criterion"
                  type="range"
                  min={1}
                  max={5}
                  step={1}
                  value={thresholds.min_criterion_score}
                  onChange={(e) =>
                    onChangeThresholds({
                      ...thresholds,
                      min_criterion_score: Number(e.target.value),
                    })
                  }
                  className="w-full accent-sky-700"
                />
              </div>

              <div>
                <label
                  htmlFor="slider-max-sim"
                  className="block text-xs font-semibold text-slate-800 mb-1.5"
                >
                  Near-Duplicate Similarity Ceiling:{' '}
                  <span className="font-mono tabular-nums">
                    {Math.round(thresholds.max_similarity_threshold * 100)}%
                  </span>{' '}
                  <span className="text-slate-500 font-normal">(Default: 55%)</span>
                </label>
                <input
                  id="slider-max-sim"
                  type="range"
                  min={0.35}
                  max={0.85}
                  step={0.05}
                  value={thresholds.max_similarity_threshold}
                  onChange={(e) =>
                    onChangeThresholds({
                      ...thresholds,
                      max_similarity_threshold: Number(e.target.value),
                    })
                  }
                  className="w-full accent-sky-700"
                />
              </div>
            </div>
          </div>

          {/* Documented 1–5 Rubric Scale Matrix */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
            <h3 className="text-base font-semibold text-slate-900">
              Documented 1–5 Scoring Scale Descriptors
            </h3>
            <div className="divide-y divide-slate-100">
              {RUBRIC_CRITERIA_METADATA.map((crit) => (
                <div key={crit.key} className="py-3.5 space-y-2 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-slate-900">
                      {crit.label} — <span className="font-normal text-slate-600">{crit.question}</span>
                    </span>
                    <span className="font-mono text-slate-500 tabular-nums">
                      Weight: {thresholds.weights[crit.key].toFixed(2)}×
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px]">
                    <div className="bg-slate-50 border border-slate-200/80 rounded p-2 text-slate-700">
                      <span className="font-mono font-semibold text-red-700">Score 1: </span>
                      {crit.descriptors[1]}
                    </div>
                    <div className="bg-slate-50 border border-slate-200/80 rounded p-2 text-slate-700">
                      <span className="font-mono font-semibold text-amber-700">Score 3: </span>
                      {crit.descriptors[3]}
                    </div>
                    <div className="bg-slate-50 border border-slate-200/80 rounded p-2 text-slate-700">
                      <span className="font-mono font-semibold text-emerald-700">Score 5: </span>
                      {crit.descriptors[5]}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Interactive Candidate Question Auditor (Live Python Rubric + Deterministic Verifier) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-6 space-y-5">
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              Interactive Candidate Question &amp; Trap Auditor
            </h3>
            <p className="text-xs text-slate-600 mt-1">
              Test how `QuestionQualityRubric` and `DeterministicVerifier` score candidate questions and catch publication-date traps, unread diagram hallucinations, or calculation errors.
            </p>
          </div>

          {/* Preset Selector */}
          <div className="space-y-1.5">
            <label htmlFor="audit-preset-select" className="block text-xs font-semibold text-slate-700">
              Load Verification Preset Scenario
            </label>
            <select
              id="audit-preset-select"
              value={selectedPresetId}
              onChange={(e) => handleLoadPreset(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-600"
            >
              {AUDITOR_PRESET_CASES.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <form onSubmit={handleRunAudit} className="space-y-3 text-xs">
            <div>
              <label htmlFor="audit-question-input" className="block font-semibold text-slate-700 mb-1">
                Candidate Question
              </label>
              <textarea
                id="audit-question-input"
                rows={2}
                value={candidateForm.question}
                onChange={(e) => setCandidateForm({ ...candidateForm, question: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900"
              />
            </div>

            <div>
              <label htmlFor="audit-answer-input" className="block font-semibold text-slate-700 mb-1">
                Candidate Answer (Checked for Math &amp; Chemical Balance)
              </label>
              <textarea
                id="audit-answer-input"
                rows={2}
                value={candidateForm.answer}
                onChange={(e) => setCandidateForm({ ...candidateForm, answer: e.target.value })}
                className="w-full font-mono bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900"
              />
            </div>

            <div>
              <label htmlFor="audit-evidence-input" className="block font-semibold text-slate-700 mb-1">
                Claimed Source Evidence
              </label>
              <textarea
                id="audit-evidence-input"
                rows={2}
                value={candidateForm.source_evidence}
                onChange={(e) =>
                  setCandidateForm({ ...candidateForm, source_evidence: e.target.value })
                }
                className="w-full font-mono bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900"
              />
            </div>

            <button
              type="submit"
              disabled={isScoring}
              className="w-full px-4 py-2 text-xs font-semibold text-white bg-sky-700 hover:bg-sky-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              {isScoring ? 'Running Python Rubric Audit...' : 'Audit Candidate with Python Rubric'}
            </button>
          </form>

          {/* Audit Result Output */}
          {auditResult && (
            <div className="border border-slate-200 rounded-lg p-4 bg-slate-50 space-y-3 text-xs">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2 font-mono tabular-nums">
                <span
                  className={`font-semibold ${
                    auditResult.validation_status === 'accepted'
                      ? 'text-emerald-700'
                      : auditResult.validation_status === 'rejected'
                      ? 'text-red-700'
                      : 'text-amber-700'
                  }`}
                >
                  {auditResult.validation_status === 'accepted'
                    ? '● STATUS: ACCEPTED'
                    : auditResult.validation_status === 'rejected'
                    ? '✕ STATUS: REJECTED'
                    : '▲ STATUS: NEEDS REVIEW'}
                </span>
                <span className="font-bold text-slate-900">
                  Avg Score: {auditResult.quality_scores?.average_score?.toFixed(2)} / 5.00
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 font-mono tabular-nums">
                <div>Relevance: {auditResult.quality_scores?.curriculum_relevance}/5</div>
                <div>Source Fidelity: {auditResult.quality_scores?.source_fidelity}/5</div>
                <div>Clarity: {auditResult.quality_scores?.clarity}/5</div>
                <div>Educational Value: {auditResult.quality_scores?.educational_value}/5</div>
                <div>Distinctness: {auditResult.quality_scores?.distinctness}/5</div>
                <div>Answer Quality: {auditResult.quality_scores?.answer_quality}/5</div>
                <div>Grade Suitability: {auditResult.quality_scores?.grade_suitability}/5</div>
                <div>Verified Page: {auditResult.source_page ?? 'null'}</div>
              </div>

              {auditResult.review_notes?.length > 0 && (
                <div className="space-y-1 pt-2 border-t border-slate-200">
                  <div className="font-semibold text-slate-800">Diagnostic Review Notes:</div>
                  <ul className="list-disc pl-4 space-y-1 text-slate-700 font-mono text-[11px]">
                    {auditResult.review_notes.map((n: string, i: number) => (
                      <li key={i}>{n}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
