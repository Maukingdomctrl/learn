/**
 * Pure deterministic logic for client-side rubric threshold re-evaluation,
 * scientific notation normalization, chemical equation balance checking,
 * and evaluation metric computation.
 */

export interface QualityScores {
  curriculum_relevance: number;
  source_fidelity: number;
  clarity: number;
  educational_value: number;
  distinctness: number;
  answer_quality: number;
  grade_suitability: number;
  average_score: number;
}

export interface RubricThresholds {
  min_criterion_score: number;
  min_source_fidelity: number;
  min_grade_suitability: number;
  min_average_score: number;
  max_similarity_threshold: number;
  require_math_verification: boolean;
  require_chemical_balance_check: boolean;
  weights: {
    curriculum_relevance: number;
    source_fidelity: number;
    clarity: number;
    educational_value: number;
    distinctness: number;
    answer_quality: number;
    grade_suitability: number;
  };
}

export interface QuestionRecord {
  question_id: string;
  question: string;
  answer: string;
  question_type: string;
  difficulty: string;
  learning_point: string;
  source_evidence: string;
  source_page: number | null;
  quality_scores: QualityScores;
  validation_status: 'accepted' | 'revised' | 'needs_review' | 'rejected';
  review_notes: string[];
}

export const DEFAULT_RUBRIC_THRESHOLDS: RubricThresholds = {
  min_criterion_score: 3,
  min_source_fidelity: 4,
  min_grade_suitability: 3,
  min_average_score: 3.6,
  max_similarity_threshold: 0.55,
  require_math_verification: true,
  require_chemical_balance_check: true,
  weights: {
    curriculum_relevance: 1.15,
    source_fidelity: 1.35,
    clarity: 1.0,
    educational_value: 1.1,
    distinctness: 1.0,
    answer_quality: 1.25,
    grade_suitability: 1.15,
  },
};

export const RUBRIC_CRITERIA_METADATA: Array<{
  key: keyof Omit<QualityScores, 'average_score'>;
  label: string;
  question: string;
  descriptors: Record<number, string>;
}> = [
  {
    key: 'curriculum_relevance',
    label: 'Curriculum Relevance',
    question: 'Does it test an important, syllabus-central learning point?',
    descriptors: {
      1: 'Tests non-curriculum noise (publication/reprint dates, ISBNs) or lacks a learning point.',
      2: 'Focuses on a trivial peripheral detail rather than a core lesson concept.',
      3: 'Tests a valid secondary fact or definition from the passage.',
      4: 'Tests a primary concept, cause-effect relationship, or scientific principle.',
      5: 'Directly targets a high-priority learning point central to the ICSE chapter.',
    },
  },
  {
    key: 'source_fidelity',
    label: 'Source Fidelity',
    question: 'Is the answer directly supported by the supplied material?',
    descriptors: {
      1: 'Unsupported by source, invents a page number, or claims to read an unextracted visual diagram/map.',
      2: 'Weak lexical overlap with supplied text or relies on unapproved external assumptions.',
      3: 'Partially supported by the source passage with minor paraphrasing drift.',
      4: 'Strongly grounded in the supplied text with verifiable evidence and valid page reference.',
      5: 'Verbatim source evidence verified on the exact source page with zero unsupported claims.',
    },
  },
  {
    key: 'clarity',
    label: 'Clarity & Specificity',
    question: 'Is the wording specific, unambiguous, and well-structured?',
    descriptors: {
      1: 'Fragmented, ungrammatical, or ambiguous wording.',
      2: 'Vague prompt lacking a clear task verb or scope.',
      3: 'Understandable question with acceptable wording.',
      4: 'Clear, specific question with an explicit cognitive verb and unambiguous scope.',
      5: 'Exemplary ICSE examination-ready phrasing with precise terminology.',
    },
  },
  {
    key: 'educational_value',
    label: 'Educational Value',
    question: 'Does it test meaningful learning rather than simple sentence copying?',
    descriptors: {
      1: 'Mechanical fill-in-the-blank or verbatim sentence copy with zero cognitive demand.',
      2: 'Surface-level recall of an isolated word when deeper understanding is supported.',
      3: 'Tests foundational factual recall or definition comprehension.',
      4: 'Requires conceptual explanation, cause-effect reasoning, sequence ordering, or comparison.',
      5: 'Engages higher-order application, table interpretation, or quantitative problem solving.',
    },
  },
  {
    key: 'distinctness',
    label: 'Distinctness',
    question: 'Does it add value beyond other questions in the set?',
    descriptors: {
      1: 'Exact or near-exact duplicate of another question (>= 75% similarity).',
      2: 'High conceptual/lexical overlap (>= 55% similarity) with an earlier question.',
      3: 'Touches a related aspect of the same section with moderate overlap.',
      4: 'Tests a distinct concept or applies a different cognitive skill.',
      5: 'Completely distinct learning point and question category.',
    },
  },
  {
    key: 'answer_quality',
    label: 'Answer Quality & Notation',
    question: 'Is the answer accurate, complete, notation-faithful, and deterministically verified?',
    descriptors: {
      1: 'Factually wrong, fails deterministic math/chemical balance check, or corrupts scientific notation.',
      2: 'Incomplete answer missing key explanation steps or required SI units.',
      3: 'Correct core answer but brief.',
      4: 'Accurate, complete answer preserving source terminology and notation.',
      5: 'Comprehensive model answer with verified calculations/balanced equations and exact scientific notation.',
    },
  },
  {
    key: 'grade_suitability',
    label: 'ICSE Grade Suitability',
    question: 'Is it appropriate for the specified ICSE class (Classes 8–10 vs Classes 11–12)?',
    descriptors: {
      1: 'Severely mismatched for the target ICSE class.',
      2: 'Vocabulary or reasoning depth noticeably above or below the target class band.',
      3: 'Acceptable for the class level with minor phrasing adjustments.',
      4: 'Well-matched to cognitive and vocabulary expectations of the specified ICSE class.',
      5: 'Calibrated specifically to ICSE Classes 8–10 (accessible reasoning) or Classes 11–12 (analytical rigor).',
    },
  },
];

const SUB_DIGITS: Record<string, string> = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
  '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
};

const SUP_CHARS: Record<string, string> = {
  '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
  '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
  '+': '⁺', '-': '⁻', 'n': 'ⁿ',
};

export function normalizeScientificNotationClient(input: string): string {
  if (!input) return '';
  let out = input
    .replace(/<=>/g, '⇌')
    .replace(/<->/g, '⇌')
    .replace(/->/g, '→')
    .replace(/>=/g, '≥')
    .replace(/<=/g, '≤')
    .replace(/!=/g, '≠');

  out = out.replace(/\^\{([^}]+)\}/g, (_, inner: string) =>
    inner.split('').map((c) => SUP_CHARS[c] ?? c).join('')
  );
  out = out.replace(/_\{([^}]+)\}/g, (_, inner: string) =>
    inner.split('').map((c) => SUB_DIGITS[c] ?? c).join('')
  );
  out = out.replace(/([A-Za-z)\]])_(\d+)/g, (_, p1: string, d: string) =>
    p1 + d.split('').map((c) => SUB_DIGITS[c] ?? c).join('')
  );
  out = out.replace(/([A-Za-z₀-₉)\]])\^(\d+[+-]?)/g, (_, p1: string, d: string) =>
    p1 + d.split('').map((c) => SUP_CHARS[c] ?? c).join('')
  );
  return out;
}

export function computeWeightedAverageScore(
  scores: Omit<QualityScores, 'average_score'>,
  weights: RubricThresholds['weights'] = DEFAULT_RUBRIC_THRESHOLDS.weights
): number {
  const keys = Object.keys(weights) as Array<keyof typeof weights>;
  let weightedSum = 0;
  let totalWeight = 0;
  for (const key of keys) {
    const w = weights[key] ?? 1;
    weightedSum += (scores[key] ?? 0) * w;
    totalWeight += w;
  }
  if (totalWeight <= 0) return 0;
  return Number((weightedSum / totalWeight).toFixed(2));
}

export function evaluateQuestionAgainstThresholds(
  question: QuestionRecord,
  thresholds: RubricThresholds
): QuestionRecord {
  const rawScores = question.quality_scores;
  const newAvg = computeWeightedAverageScore(rawScores, thresholds.weights);
  const minCrit = Math.min(
    rawScores.curriculum_relevance,
    rawScores.source_fidelity,
    rawScores.clarity,
    rawScores.educational_value,
    rawScores.distinctness,
    rawScores.answer_quality,
    rawScores.grade_suitability
  );

  let status: QuestionRecord['validation_status'] = 'accepted';
  const notes = [...question.review_notes.filter((n) => !n.startsWith('[Threshold Filter]'))];

  if (
    rawScores.curriculum_relevance === 1 ||
    rawScores.source_fidelity === 1 ||
    rawScores.distinctness <= 2 ||
    (thresholds.require_math_verification && rawScores.answer_quality === 1)
  ) {
    status = 'rejected';
  } else if (rawScores.source_fidelity < thresholds.min_source_fidelity) {
    status = 'rejected';
    notes.push(
      `[Threshold Filter] Source fidelity (${rawScores.source_fidelity}) is below minimum (${thresholds.min_source_fidelity}).`
    );
  } else if (rawScores.grade_suitability < thresholds.min_grade_suitability) {
    status = 'needs_review';
    notes.push(
      `[Threshold Filter] Grade suitability (${rawScores.grade_suitability}) is below minimum (${thresholds.min_grade_suitability}).`
    );
  } else if (minCrit < thresholds.min_criterion_score) {
    status = minCrit < thresholds.min_criterion_score - 1 ? 'rejected' : 'needs_review';
    notes.push(
      `[Threshold Filter] Lowest criterion score (${minCrit}) is below threshold (${thresholds.min_criterion_score}).`
    );
  } else if (newAvg < thresholds.min_average_score) {
    status = 'needs_review';
    notes.push(
      `[Threshold Filter] Weighted average (${newAvg}) is below threshold (${thresholds.min_average_score}).`
    );
  } else if (question.validation_status === 'revised') {
    status = 'revised';
  } else {
    status = 'accepted';
  }

  return {
    ...question,
    quality_scores: {
      ...rawScores,
      average_score: newAvg,
    },
    validation_status: status,
    review_notes: notes,
  };
}

export function computeSetEvaluationMetrics(questions: QuestionRecord[]) {
  const total = questions.length;
  if (total === 0) {
    return {
      total_questions: 0,
      accepted_count: 0,
      needs_review_count: 0,
      rejected_count: 0,
      valid_source_evidence_pct: 0,
      answer_correctness_pct: 0,
      distinct_question_types: 0,
      duplicate_rate_pct: 0,
      grade_appropriateness_pct: 0,
      average_rubric_score: 0,
    };
  }

  const acceptedCount = questions.filter(
    (q) => q.validation_status === 'accepted' || q.validation_status === 'revised'
  ).length;
  const needsReviewCount = questions.filter((q) => q.validation_status === 'needs_review').length;
  const rejectedCount = questions.filter((q) => q.validation_status === 'rejected').length;

  const validEv = questions.filter((q) => q.quality_scores.source_fidelity >= 4).length;
  const correctAns = questions.filter((q) => q.quality_scores.answer_quality >= 4).length;
  const dupCnt = questions.filter((q) => q.quality_scores.distinctness <= 2).length;
  const gradeOk = questions.filter((q) => q.quality_scores.grade_suitability >= 4).length;
  const avgScore =
    questions.reduce((acc, q) => acc + q.quality_scores.average_score, 0) / total;
  const types = new Set(questions.map((q) => q.question_type));

  return {
    total_questions: total,
    accepted_count: acceptedCount,
    needs_review_count: needsReviewCount,
    rejected_count: rejectedCount,
    valid_source_evidence_pct: Number(((validEv / total) * 100).toFixed(1)),
    answer_correctness_pct: Number(((correctAns / total) * 100).toFixed(1)),
    distinct_question_types: types.size,
    duplicate_rate_pct: Number(((dupCnt / total) * 100).toFixed(1)),
    grade_appropriateness_pct: Number(((gradeOk / total) * 100).toFixed(1)),
    average_rubric_score: Number(avgScore.toFixed(2)),
  };
}

export const AUDITOR_PRESET_CASES = [
  {
    id: 'exemplary_chemistry',
    label: 'Exemplary Grounded ICSE Class 10 Chemistry Question',
    class_level: 10,
    subject: 'Chemistry',
    candidate: {
      question_id: 'audit_01',
      question:
        'Write the balanced chemical equation for the electrolysis of acidified water using platinum electrodes and state what happens at the cathode in aqueous CuSO4.',
      answer:
        'During the electrolysis of acidified water, water decomposes according to 2H2O(l) -> 2H2(g) + O2(g). In aqueous CuSO4(aq) <=> Cu^{2+}(aq) + SO4^{2-}(aq), positively charged Cu^{2+} cations migrate to the cathode and gain electrons.',
      question_type: 'why_how',
      difficulty: 'medium',
      learning_point: 'Electrolysis of acidified water and ion migration in aqueous CuSO4',
      source_evidence:
        'During the electrolysis of acidified water using platinum electrodes, water decomposes according to the balanced chemical equation 2H2O(l) -> 2H2(g) + O2(g).',
      source_page: 1,
    },
  },
  {
    id: 'publication_date_trap',
    label: 'Defect Trap 1: Textbook Publication / Reprint Date Confused with History',
    class_level: 10,
    subject: 'History & Civics',
    candidate: {
      question_id: 'audit_02',
      question: 'In which year was this textbook reprinted by Curriculum Press Pvt Ltd, and what is its ISBN?',
      answer: 'It was reprinted in 2025 with ISBN 978-81-99999-01-2.',
      question_type: 'recall',
      difficulty: 'easy',
      learning_point: 'Publication and reprint date of textbook',
      source_evidence:
        'First Published in 2022, Reprinted in 2025 by Curriculum Press Pvt Ltd. ISBN: 978-81-99999-01-2.',
      source_page: 2,
    },
  },
  {
    id: 'unread_map_hallucination',
    label: 'Defect Trap 2: Claiming to Read an Unextracted Visual Map/Diagram',
    class_level: 10,
    subject: 'Geography',
    candidate: {
      question_id: 'audit_03',
      question:
        'Looking at the figure in Map 2.1, what is the exact isohyet contour line value drawn over Nagpur?',
      answer: 'The contour line drawn on Map 2.1 over Nagpur is 1140 mm.',
      question_type: 'interpretation',
      difficulty: 'hard',
      learning_point: 'Read contour lines directly from Map 2.1',
      source_evidence: 'Map 2.1: Isohyetal Distribution of Annual Rainfall Across the Indian Subcontinent',
      source_page: 2,
    },
  },
  {
    id: 'wrong_math_calculation',
    label: "Defect Trap 3: Incorrect Numerical Calculation in Ohm's Law",
    class_level: 10,
    subject: 'Physics',
    candidate: {
      question_id: 'audit_04',
      question:
        "Using Ohm's Law (V = I × R), calculate the potential difference V across a resistor of R = 12 Ω carrying a current of I = 2.5 A.",
      answer: 'Using V = I × R, V = 2.5 × 12 = 42 V.',
      question_type: 'problem_solving',
      difficulty: 'medium',
      learning_point: "Apply Ohm's Law V = I × R",
      source_evidence:
        "Ohm's Law states that the potential difference V across the ends of a metallic conductor is directly proportional to the current I flowing through it, provided temperature remains constant: V = I * R.",
      source_page: 1,
    },
  },
];
