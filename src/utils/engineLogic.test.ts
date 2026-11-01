import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_RUBRIC_THRESHOLDS,
  computeSetEvaluationMetrics,
  computeWeightedAverageScore,
  evaluateQuestionAgainstThresholds,
  normalizeScientificNotationClient,
  type QuestionRecord,
} from './engineLogic';

test('normalizeScientificNotationClient converts subscripts, superscripts, and reaction arrows', () => {
  const raw = '2H_2O(l) -> 2H_2(g) + O_2(g) and Cu^{2+}(aq) <=> Cu(s) at >= 10^{-3} mol';
  const norm = normalizeScientificNotationClient(raw);
  assert.equal(norm.includes('2H₂O(l) → 2H₂(g) + O₂(g)'), true);
  assert.equal(norm.includes('Cu²⁺(aq) ⇌ Cu(s)'), true);
  assert.equal(norm.includes('≥ 10⁻³'), true);
});

test('computeWeightedAverageScore computes accurate weighted mean on 1-5 scale', () => {
  const perfect = computeWeightedAverageScore({
    curriculum_relevance: 5,
    source_fidelity: 5,
    clarity: 5,
    educational_value: 5,
    distinctness: 5,
    answer_quality: 5,
    grade_suitability: 5,
  });
  assert.equal(perfect, 5);
});

test('evaluateQuestionAgainstThresholds enforces source_fidelity and min_average_score thresholds', () => {
  const sampleQuestion: QuestionRecord = {
    question_id: 'q_01',
    question: 'What is electrolysis?',
    answer: 'Decomposition of an ionic compound by electric current.',
    question_type: 'understanding',
    difficulty: 'easy',
    learning_point: 'Define electrolysis',
    source_evidence: 'Electrolysis is defined as the chemical decomposition of an ionic compound.',
    source_page: 1,
    quality_scores: {
      curriculum_relevance: 4,
      source_fidelity: 4,
      clarity: 4,
      educational_value: 4,
      distinctness: 5,
      answer_quality: 4,
      grade_suitability: 4,
      average_score: 4.13,
    },
    validation_status: 'accepted',
    review_notes: [],
  };

  // Passing under default thresholds
  const resDefault = evaluateQuestionAgainstThresholds(sampleQuestion, DEFAULT_RUBRIC_THRESHOLDS);
  assert.equal(resDefault.validation_status, 'accepted');

  // Raising min_average_score to 4.5 moves status to needs_review
  const resStrictAvg = evaluateQuestionAgainstThresholds(sampleQuestion, {
    ...DEFAULT_RUBRIC_THRESHOLDS,
    min_average_score: 4.5,
  });
  assert.equal(resStrictAvg.validation_status, 'needs_review');

  // Raising min_source_fidelity to 5 rejects a fidelity=4 question
  const resStrictFidelity = evaluateQuestionAgainstThresholds(sampleQuestion, {
    ...DEFAULT_RUBRIC_THRESHOLDS,
    min_source_fidelity: 5,
  });
  assert.equal(resStrictFidelity.validation_status, 'rejected');
});

test('computeSetEvaluationMetrics calculates percentages and counts accurately', () => {
  const questions: QuestionRecord[] = [
    {
      question_id: 'q_01',
      question: 'Q1?',
      answer: 'A1',
      question_type: 'why_how',
      difficulty: 'medium',
      learning_point: 'LP1',
      source_evidence: 'Ev1',
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
      validation_status: 'accepted',
      review_notes: [],
    },
    {
      question_id: 'q_02',
      question: 'Q2?',
      answer: 'A2',
      question_type: 'problem_solving',
      difficulty: 'hard',
      learning_point: 'LP2',
      source_evidence: 'Ev2',
      source_page: 2,
      quality_scores: {
        curriculum_relevance: 4,
        source_fidelity: 4,
        clarity: 4,
        educational_value: 5,
        distinctness: 2,
        answer_quality: 4,
        grade_suitability: 4,
        average_score: 3.9,
      },
      validation_status: 'rejected',
      review_notes: ['Near duplicate'],
    },
  ];

  const metrics = computeSetEvaluationMetrics(questions);
  assert.equal(metrics.total_questions, 2);
  assert.equal(metrics.accepted_count, 1);
  assert.equal(metrics.rejected_count, 1);
  assert.equal(metrics.valid_source_evidence_pct, 100);
  assert.equal(metrics.duplicate_rate_pct, 50);
  assert.equal(metrics.distinct_question_types, 2);
});
