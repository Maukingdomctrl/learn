import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { checkMilestoneCompliance, filterCards, SheetEvaluation } from './engine-types';

test('checkMilestoneCompliance validates milestone thresholds accurately', () => {
  const passingMetrics = {
    core_recall: 100.0,
    core_covered: 20,
    core_total: 20,
    all_recall: 81.1,
    all_covered: 30,
    all_total: 37,
    fact_precision: 100.0,
    question_correctness: 100.0,
    question_clarity: 100.0,
    duplicate_rate: 0.0,
    traceability: 100.0,
    invented_words_count: 0,
    invented_words: [],
    facts_count: 41,
    cards_count: 30,
    rejected_count: 11,
  };
  const res = checkMilestoneCompliance(passingMetrics);
  assert.equal(res.passed, true);

  const failingMetrics = {
    ...passingMetrics,
    core_recall: 50.0,
  };
  assert.equal(checkMilestoneCompliance(failingMetrics).passed, false);
});

test('filterCards filters by search query and question_type', () => {
  const sampleCards = [
    {
      id: 'C1',
      fact_id: 'F1',
      item_id: 'I4',
      page: 1,
      label: 'London',
      front: 'What is London the capital of?',
      prompt: '',
      answer: 'United Kingdom & England',
      question_type: 'WHERE',
      source_text: 'LONDON – Capital of the United Kingdom & England',
      status: 'accepted',
    },
    {
      id: 'C2',
      fact_id: 'F2',
      item_id: 'I9',
      page: 1,
      label: 'Satyashodhak Samaj',
      front: 'In which year was the Satyashodhak Samaj founded?',
      prompt: '',
      answer: '1873',
      question_type: 'WHEN',
      source_text: 'Founded the Satyashodhak Samaj in 1873.',
      status: 'accepted',
    },
  ];

  assert.equal(filterCards(sampleCards, '1873', 'ALL').length, 1);
  assert.equal(filterCards(sampleCards, '', 'WHERE').length, 1);
  assert.equal(filterCards(sampleCards, 'london', 'WHEN').length, 0);
});

test('all 3 real study sheets in final_eval.json meet first milestone targets', () => {
  const evalPath = path.join(process.cwd(), 'data', 'final_eval.json');
  const raw = fs.readFileSync(evalPath, 'utf-8');
  const data = JSON.parse(raw) as Record<string, SheetEvaluation>;

  for (const slug of ['mumbai-personalities-flat', 'uk-cities-comparative-table', 'full-physics-forces']) {
    const sheetEval = data[slug];
    assert.ok(sheetEval, `Missing evaluation for ${slug}`);
    const compliance = checkMilestoneCompliance(sheetEval.metrics);
    assert.equal(
      compliance.passed,
      true,
      `Sheet ${slug} failed milestone compliance: ${JSON.stringify(compliance.checks)}`
    );
  }
});
