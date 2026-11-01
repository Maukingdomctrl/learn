export interface EntitySpan {
  text: string;
  type: string;
}

export interface ExtractedFact {
  id: string;
  item_id: string;
  page: number;
  source_text: string;
  subject: string;
  relation: string;
  object: string;
  entities: EntitySpan[];
  category: string;
}

export interface StudyCard {
  id: string;
  fact_id: string;
  item_id: string;
  page: number;
  label: string;
  front: string;
  prompt: string;
  answer: string;
  question_type: string;
  source_text: string;
  status: string;
}

export interface RejectedCard {
  front: string;
  answer: string;
  reasons: string[];
}

export interface EngineOutput {
  sheet: string;
  facts: ExtractedFact[];
  cards: StudyCard[];
  rejected: RejectedCard[];
}

export interface ReferenceFact {
  id: string;
  source_item: string;
  page: number;
  subject: string;
  relation: string;
  answer: string;
  category: string;
  importance: 'core' | 'secondary';
}

export interface SheetMetrics {
  core_recall: number;
  core_covered: number;
  core_total: number;
  all_recall: number;
  all_covered: number;
  all_total: number;
  fact_precision: number;
  question_correctness: number;
  question_clarity: number;
  duplicate_rate: number;
  traceability: number;
  invented_words_count: number;
  invented_words: string[];
  facts_count: number;
  cards_count: number;
  rejected_count: number;
}

export interface SheetEvaluation {
  slug: string;
  sheet: string;
  metrics: SheetMetrics;
  missed_core_facts: ReferenceFact[];
  missed_secondary_facts: ReferenceFact[];
  doubtful_facts: ExtractedFact[];
  reword_candidates: Array<{ id: string; front: string; reason: string }>;
  output: EngineOutput;
}

export interface Round2UncoveredPoint {
  id: string;
  topic: string;
  text: string;
  reason: string;
}

export interface Round2SheetResult {
  sheet: string;
  file: string;
  card_count: number;
  total_points: number;
  covered_points: number;
  point_coverage_pct: number;
  cards: StudyCard[];
  rejected: RejectedCard[];
  uncovered_points: Round2UncoveredPoint[];
}

export function checkMilestoneCompliance(metrics: SheetMetrics): {
  passed: boolean;
  checks: Array<{ label: string; passed: boolean; actual: string; target: string }>;
} {
  const checks = [
    {
      label: 'Core-Fact Recall',
      passed: metrics.core_recall >= 70.0,
      actual: `${metrics.core_recall.toFixed(1)}% (${metrics.core_covered}/${metrics.core_total})`,
      target: '>= 70.0%',
    },
    {
      label: 'Question Correctness',
      passed: metrics.question_correctness >= 95.0,
      actual: `${metrics.question_correctness.toFixed(1)}%`,
      target: '>= 95.0%',
    },
    {
      label: 'Duplicate Rate',
      passed: metrics.duplicate_rate < 5.0,
      actual: `${metrics.duplicate_rate.toFixed(1)}%`,
      target: '< 5.0%',
    },
    {
      label: 'Source Traceability',
      passed: metrics.traceability === 100.0,
      actual: `${metrics.traceability.toFixed(1)}%`,
      target: '100.0%',
    },
    {
      label: 'Zero Invented Words',
      passed: metrics.invented_words_count === 0,
      actual: `${metrics.invented_words_count} words`,
      target: '0 words',
    },
    {
      label: 'Card Count Cap',
      passed: metrics.cards_count > 0 && metrics.cards_count <= 30,
      actual: `${metrics.cards_count} cards`,
      target: '1–30 cards',
    },
  ];

  return {
    passed: checks.every((c) => c.passed),
    checks,
  };
}

export function filterCards(
  cards: StudyCard[],
  query: string,
  questionType: string
): StudyCard[] {
  const q = query.trim().toLowerCase();
  return cards.filter((card) => {
    if (questionType !== 'ALL' && card.question_type !== questionType) {
      return false;
    }
    if (!q) return true;
    return (
      card.label.toLowerCase().includes(q) ||
      card.front.toLowerCase().includes(q) ||
      card.answer.toLowerCase().includes(q) ||
      card.item_id.toLowerCase().includes(q)
    );
  });
}
