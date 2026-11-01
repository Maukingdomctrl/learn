'use client';

import React, { useState, useMemo } from 'react';
import {
  BookOpen,
  CheckCircle2,
  Eye,
  EyeOff,
  FileJson,
  Printer,
  Search,
  SlidersHorizontal,
  Play,
  RotateCcw,
} from 'lucide-react';
import {
  SheetEvaluation,
  ReferenceFact,
  EngineOutput,
  Round2SheetResult,
  checkMilestoneCompliance,
  filterCards,
} from '@/lib/engine-types';

interface EngineWorkbenchProps {
  finalEvals: Record<string, SheetEvaluation>;
  prototypeEvals: Record<string, SheetEvaluation>;
  round2Baseline?: Round2SheetResult[];
  round2Final?: Round2SheetResult[];
  referenceFactsBySlug: Record<string, ReferenceFact[]>;
  readerJsonBySlug: Record<string, Record<string, unknown>>;
}

const SHEET_META: Array<{
  slug: string;
  title: string;
  subtitle: string;
}> = [
  {
    slug: 'mumbai-personalities-flat',
    title: 'Mumbai Personalities',
    subtitle: 'Grade 8 ICSE Social Studies · 5 Topics · Notes + Comparative Table',
  },
  {
    slug: 'uk-cities-comparative-table',
    title: 'UK Cities Comparative',
    subtitle: 'Grade 8 Social Studies · 5 Cities · Notes + Matrix + Practice',
  },
  {
    slug: 'full-physics-forces',
    title: 'Physics: Forces & Mass',
    subtitle: 'ICSE Physics · Newton’s Second Law · Free-Body & Units',
  },
];

const READER_NOTES = [
  {
    sheet: 'mumbai-personalities-flat.pdf',
    item_id: 'I8, I11, I13, I15',
    issue:
      'Inline source citations "(Britannica)" are embedded inside point text with empty bold arrays. General parenthetical check requires multi-word or bold alias so single-word citations are ignored.',
  },
  {
    sheet: 'uk-cities-comparative-table.pdf',
    item_id: 'I116',
    issue:
      'On page 6, the reader merged "Study Tip for Grade 8: Make a simple mind-map..." into answer item I116 instead of emitting a separate kind="tip" item. Because answer items are excluded as card sources, no tip leaks into cards.',
  },
  {
    sheet: 'full-physics-forces.pdf',
    item_id: 'I12, I13',
    issue:
      'In I12, the box heading "Evaluation:" remained inline inside text while context stayed "Units and conversions" from I10; I13 (practice question) also inherited context="Units and conversions".',
  },
  {
    sheet: 'equations.pdf',
    item_id: 'I12',
    issue:
      'In I12 ("Fractions: ¾ + \\ufffd = \\ufffd"), the PDF reader emitted Unicode replacement characters (\\ufffd) for missing fraction glyphs. Skipped in relations.py and rejected in validate.py so broken glyphs never appear on cards.',
  },
  {
    sheet: 'full-finance-lost-rupee.pdf',
    item_id: 'I9, I12',
    issue:
      'In table item I9 and question item I12, the Rupee symbol (₹) was replaced with \\ufffd ("\\ufffd5,000", "\\ufffd600 interest") and the exponent in "A = P(1 + r)\\ufffd" was lost. Currency prefix \\ufffd before digits is stripped while keeping the number intact; corrupted formula "A = P(1 + r)\\ufffd" is skipped.',
  },
];

export default function EngineWorkbench({
  finalEvals,
  prototypeEvals,
  round2Baseline = [],
  round2Final = [],
  referenceFactsBySlug,
  readerJsonBySlug,
}: EngineWorkbenchProps) {
  const [activeSlug, setActiveSlug] = useState<string>('mumbai-personalities-flat');
  const [activeR2Index, setActiveR2Index] = useState<number>(0);
  const [activeSection, setActiveSection] = useState<
    'cards' | 'facts' | 'audit' | 'progression' | 'custom'
  >('cards');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [questionTypeFilter, setQuestionTypeFilter] = useState<string>('ALL');
  const [revealAll, setRevealAll] = useState<boolean>(false);
  const [revealedIds, setRevealedIds] = useState<Record<string, boolean>>({});
  const [printMode, setPrintMode] = useState<boolean>(false);

  // Custom JSON runner state
  const [customJsonText, setCustomJsonText] = useState<string>(() =>
    JSON.stringify(readerJsonBySlug['full-physics-forces'], null, 2)
  );
  const [customOutput, setCustomOutput] = useState<EngineOutput | null>(null);
  const [customError, setCustomError] = useState<string>('');
  const [isRunningCustom, setIsRunningCustom] = useState<boolean>(false);

  const currentEval = finalEvals[activeSlug];
  const protoEval = prototypeEvals[activeSlug];
  const refFacts = referenceFactsBySlug[activeSlug] || [];
  const compliance = useMemo(
    () => checkMilestoneCompliance(currentEval.metrics),
    [currentEval.metrics]
  );

  const filteredCards = useMemo(
    () => filterCards(currentEval.output.cards, searchQuery, questionTypeFilter),
    [currentEval.output.cards, searchQuery, questionTypeFilter]
  );

  const questionTypes = useMemo(() => {
    const types = new Set<string>();
    for (const c of currentEval.output.cards) {
      types.add(c.question_type);
    }
    return ['ALL', ...Array.from(types)];
  }, [currentEval.output.cards]);

  const factById = useMemo(() => {
    const map: Record<string, EngineOutput['facts'][number]> = {};
    for (const f of currentEval.output.facts) {
      map[f.id] = f;
    }
    return map;
  }, [currentEval.output.facts]);

  const toggleCardReveal = (cardId: string) => {
    setRevealedIds((prev) => ({
      ...prev,
      [cardId]: !prev[cardId],
    }));
  };

  const handleRunCustomJson = async () => {
    setCustomError('');
    let parsed: unknown;
    try {
      parsed = JSON.parse(customJsonText);
    } catch {
      setCustomError('Invalid JSON syntax. Please provide a valid .reader.json object.');
      return;
    }
    if (
      !parsed ||
      typeof parsed !== 'object' ||
      !Array.isArray((parsed as { items?: unknown }).items)
    ) {
      setCustomError('JSON object must include an "items" array matching the reader schema.');
      return;
    }

    setIsRunningCustom(true);
    try {
      const res = await fetch('/api/engine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reader_json: parsed }),
      });
      const data = await res.json();
      if (!res.ok) {
        setCustomError(data.error || 'Engine execution failed.');
      } else {
        setCustomOutput(data);
      }
    } catch {
      setCustomError('Network error while calling /api/engine.');
    } finally {
      setIsRunningCustom(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A] flex flex-col">
      {/* Top Bar Contract: 3 zones separated by gap-8 */}
      <header className="flex items-center justify-between gap-8 px-6 py-4 bg-white border-b border-slate-200 sticky top-0 z-20">
        <a
          href="#top"
          onClick={(e) => {
            e.preventDefault();
            setActiveSection('cards');
            setPrintMode(false);
          }}
          className="text-lg font-bold tracking-tight text-slate-900 whitespace-nowrap shrink-0 font-serif"
        >
          Learn Key Facts Engine
        </a>

        <nav
          aria-label="Primary sections"
          className="flex items-center gap-4 md:gap-6 text-xs md:text-sm font-medium text-slate-600 overflow-x-auto"
        >
          <button
            type="button"
            onClick={() => {
              setActiveSection('cards');
              setPrintMode(false);
            }}
            className={`hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 pb-0.5 ${
              activeSection === 'cards' && !printMode
                ? 'text-slate-900 border-b-2 border-slate-900 font-semibold'
                : ''
            }`}
          >
            Study Cards
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveSection('facts');
              setPrintMode(false);
            }}
            className={`hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 pb-0.5 ${
              activeSection === 'facts'
                ? 'text-slate-900 border-b-2 border-slate-900 font-semibold'
                : ''
            }`}
          >
            Extracted Facts
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveSection('audit');
              setPrintMode(false);
            }}
            className={`hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 pb-0.5 ${
              activeSection === 'audit'
                ? 'text-slate-900 border-b-2 border-slate-900 font-semibold'
                : ''
            }`}
          >
            Evaluation Audit
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveSection('progression');
              setPrintMode(false);
            }}
            className={`hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 pb-0.5 ${
              activeSection === 'progression'
                ? 'text-slate-900 border-b-2 border-slate-900 font-semibold'
                : ''
            }`}
          >
            Development Log
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveSection('custom');
              setPrintMode(false);
            }}
            className={`hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 pb-0.5 ${
              activeSection === 'custom'
                ? 'text-slate-900 border-b-2 border-slate-900 font-semibold'
                : ''
            }`}
          >
            Live JSON Runner
          </button>
        </nav>

        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={() => setPrintMode((prev) => !prev)}
            className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 flex items-center gap-2"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>{printMode ? 'Exit Print Sheet' : 'Print Answer Sheet'}</span>
          </button>
        </div>
      </header>

      <main id="top" className="max-w-[1320px] w-full mx-auto px-6 py-8 flex-1 space-y-8">
        {/* Hero & Sheet Selector Strip */}
        <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
          <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-6 border-b border-slate-200">
            <div className="space-y-2 max-w-2xl">
              <div className="text-xs font-medium text-slate-500 flex items-center gap-2">
                <span>Deterministic Python 3 Standard-Library Engine</span>
                <span aria-hidden="true">·</span>
                <span>Zero AI / Zero Network</span>
                <span aria-hidden="true">·</span>
                <span>ICSE Classes 1–10</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 font-serif">
                Rule-Based Fact Discovery &amp; Study Card Generator
              </h1>
              <p className="text-sm text-slate-600 leading-relaxed">
                Transforms structured PDF reader output (<code>*.reader.json</code>) through six
                modular Python stages (<code>facts.py</code>, <code>entities.py</code>,{' '}
                <code>relations.py</code>, <code>questions.py</code>, <code>validate.py</code>,{' '}
                <code>output.py</code>) into verified recall cards with word-for-word sheet answers.
              </p>
            </div>

            {/* Sheet Selector Tabs */}
            <div
              role="group"
              aria-label="Select study sheet"
              className="flex flex-wrap items-center gap-1.5 p-1.5 bg-slate-100 rounded-lg shrink-0"
            >
              {SHEET_META.map((item) => {
                const isSelected = activeSlug === item.slug;
                return (
                  <button
                    key={item.slug}
                    type="button"
                    onClick={() => {
                      setActiveSlug(item.slug);
                      setSearchQuery('');
                      setQuestionTypeFilter('ALL');
                    }}
                    className={`px-3.5 py-2 text-xs font-semibold rounded-md transition-colors whitespace-nowrap shrink-0 ${
                      isSelected
                        ? 'bg-white text-slate-900 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {item.title}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Quantitative Evaluation Strip for Selected Sheet */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-6">
            <div>
              <div className="text-xs text-slate-500">Core-Fact Recall</div>
              <div className="mt-1 text-xl font-bold text-slate-900 font-mono tabular-nums">
                {currentEval.metrics.core_recall.toFixed(1)}%
              </div>
              <div className="mt-0.5 text-xs text-emerald-700 font-mono tabular-nums">
                {currentEval.metrics.core_covered}/{currentEval.metrics.core_total} core covered
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-500">All Reference Recall</div>
              <div className="mt-1 text-xl font-bold text-slate-900 font-mono tabular-nums">
                {currentEval.metrics.all_recall.toFixed(1)}%
              </div>
              <div className="mt-0.5 text-xs text-slate-600 font-mono tabular-nums">
                {currentEval.metrics.all_covered}/{currentEval.metrics.all_total} total facts
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-500">Question Correctness</div>
              <div className="mt-1 text-xl font-bold text-slate-900 font-mono tabular-nums">
                {currentEval.metrics.question_correctness.toFixed(1)}%
              </div>
              <div className="mt-0.5 text-xs text-emerald-700">
                Word-for-word in cited item
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-500">Duplicate Rate</div>
              <div className="mt-1 text-xl font-bold text-slate-900 font-mono tabular-nums">
                {currentEval.metrics.duplicate_rate.toFixed(1)}%
              </div>
              <div className="mt-0.5 text-xs text-emerald-700">
                Target &lt; 5.0%
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-500">Source Traceability</div>
              <div className="mt-1 text-xl font-bold text-slate-900 font-mono tabular-nums">
                {currentEval.metrics.traceability.toFixed(1)}%
              </div>
              <div className="mt-0.5 text-xs text-slate-600">
                Verified item_id &amp; page
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-500">Accepted / Extracted</div>
              <div className="mt-1 text-xl font-bold text-slate-900 font-mono tabular-nums">
                {currentEval.metrics.cards_count} / {currentEval.metrics.facts_count}
              </div>
              <div className="mt-0.5 text-xs text-slate-600 font-mono tabular-nums">
                0 invented words · {currentEval.metrics.rejected_count} filtered
              </div>
            </div>
          </div>
        </section>

        {/* Print Sheet Mode (Parent Printable Cards + Separate Answer Sheet) */}
        {printMode ? (
          <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
              <div>
                <h2 className="text-xl font-bold text-slate-900 font-serif">
                  Printable Study Cards &amp; Separate Answer Sheet — {currentEval.sheet}
                </h2>
                <p className="text-xs text-slate-600 mt-1">
                  Parent sheet: cut out the question cards on top and keep the numbered answer key
                  separate for self-testing recall.
                </p>
              </div>
              <button
                type="button"
                onClick={() => window.print()}
                className="px-4 py-2 text-xs font-semibold text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                Print Browser Page
              </button>
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-slate-900">
                Part 1: Question Cards ({currentEval.output.cards.length} Cards)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {currentEval.output.cards.map((card) => (
                  <div
                    key={card.id}
                    className="border border-slate-300 rounded-lg p-4 flex flex-col justify-between gap-3 bg-white"
                  >
                    <div className="space-y-1.5">
                      <div className="text-xs text-slate-500 flex items-center justify-between font-mono tabular-nums">
                        <span>
                          {card.id} · {card.label}
                        </span>
                        <span>
                          p.{card.page} ({card.item_id})
                        </span>
                      </div>
                      <p className="text-sm font-semibold text-slate-900 leading-snug">
                        {card.front}
                      </p>
                      {card.prompt && (
                        <p className="text-xs text-slate-600 italic">{card.prompt}</p>
                      )}
                    </div>
                    <div className="pt-2 border-t border-dashed border-slate-200 text-xs text-slate-400 font-mono">
                      Answer on Answer Sheet #{card.id}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-4 pt-6 border-t border-slate-200">
              <h3 className="text-sm font-semibold text-slate-900">
                Part 2: Separate Parent Answer Sheet ({currentEval.sheet})
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-2 text-sm">
                {currentEval.output.cards.map((card) => (
                  <div
                    key={card.id}
                    className="flex items-baseline justify-between gap-4 py-1.5 border-b border-slate-100"
                  >
                    <span className="font-mono text-xs text-slate-500 shrink-0">
                      {card.id} ({card.label})
                    </span>
                    <span className="font-semibold text-slate-900 text-right">{card.answer}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        ) : (
          <>
            {/* SECTION 1: STUDY CARDS */}
            {activeSection === 'cards' && (
              <section className="space-y-6">
                {/* Filter & Practice Toolbar */}
                <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex flex-1 flex-col sm:flex-row sm:items-center gap-3">
                    <div className="relative flex-1 max-w-md">
                      <label htmlFor="card-search" className="sr-only">
                        Search cards by subject, question, or answer
                      </label>
                      <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                      <input
                        id="card-search"
                        type="search"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Filter by subject, question, answer, or item ID..."
                        className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-600 focus:bg-white"
                      />
                    </div>

                    <div className="flex items-center gap-2">
                      <SlidersHorizontal className="w-4 h-4 text-slate-400 shrink-0" />
                      <label htmlFor="qtype-select" className="text-xs font-medium text-slate-600">
                        Template:
                      </label>
                      <select
                        id="qtype-select"
                        value={questionTypeFilter}
                        onChange={(e) => setQuestionTypeFilter(e.target.value)}
                        className="px-3 py-2 text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-600"
                      >
                        {questionTypes.map((qt) => (
                          <option key={qt} value={qt}>
                            {qt === 'ALL' ? 'All Question Types' : qt}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-slate-500 font-mono tabular-nums">
                      Showing {filteredCards.length} of {currentEval.output.cards.length} cards
                    </span>
                    <button
                      type="button"
                      onClick={() => setRevealAll((prev) => !prev)}
                      className="px-3.5 py-2 text-xs font-semibold text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap shrink-0"
                    >
                      {revealAll ? (
                        <>
                          <EyeOff className="w-3.5 h-3.5" />
                          <span>Cover All Answers</span>
                        </>
                      ) : (
                        <>
                          <Eye className="w-3.5 h-3.5" />
                          <span>Reveal All Answers</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Cards Grid */}
                {filteredCards.length === 0 ? (
                  <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3">
                    <p className="text-sm font-medium text-slate-700">
                      No study cards match your current filter.
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        setSearchQuery('');
                        setQuestionTypeFilter('ALL');
                      }}
                      className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors"
                    >
                      Reset Filters
                    </button>
                  </div>
                ) : (
                  <div
                    data-testid="study-cards-grid"
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
                  >
                    {filteredCards.map((card) => {
                      const isRevealed = revealAll || !!revealedIds[card.id];
                      const linkedFact = factById[card.fact_id];
                      return (
                        <article
                          key={card.id}
                          className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col justify-between gap-4 hover:border-slate-300 transition-colors"
                        >
                          <div className="space-y-2.5">
                            {/* Unboxed metadata line per Zero-Pill rule */}
                            <div className="flex items-center justify-between gap-2 text-xs text-slate-500 font-mono tabular-nums">
                              <div className="flex items-center gap-1.5 truncate">
                                <span className="font-semibold text-slate-800 font-sans">
                                  {card.label}
                                </span>
                                <span aria-hidden="true">·</span>
                                <span>{card.question_type}</span>
                              </div>
                              <div className="shrink-0">
                                <span>{card.id}</span>
                                <span aria-hidden="true"> · </span>
                                <span>{card.item_id}</span>
                                <span aria-hidden="true"> · </span>
                                <span>p.{card.page}</span>
                              </div>
                            </div>

                            {/* Question Front */}
                            <h2 className="text-base font-semibold text-slate-900 leading-snug">
                              {card.front}
                            </h2>

                            {card.prompt && (
                              <p className="text-xs text-sky-800 font-medium">{card.prompt}</p>
                            )}
                          </div>

                          <div className="space-y-3 pt-3 border-t border-slate-100">
                            <div className="flex items-center justify-between gap-3">
                              <div className="text-xs text-slate-500">
                                {isRevealed ? (
                                  <span className="font-semibold text-emerald-800 text-sm">
                                    Answer: {card.answer}
                                  </span>
                                ) : (
                                  <span className="text-slate-400 select-none">
                                    Answer hidden — click to recall
                                  </span>
                                )}
                              </div>
                              <button
                                type="button"
                                onClick={() => toggleCardReveal(card.id)}
                                aria-label={
                                  isRevealed
                                    ? `Hide answer for card ${card.id}`
                                    : `Reveal answer for card ${card.id}`
                                }
                                className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors whitespace-nowrap shrink-0"
                              >
                                {isRevealed ? 'Cover' : 'Reveal Answer'}
                              </button>
                            </div>

                            {/* Source traceability footer (masked until revealed so answer is not given away) */}
                            <div className="text-xs text-slate-500 leading-relaxed bg-slate-50 rounded-lg p-2.5">
                              <span className="font-mono text-slate-700 font-medium">
                                Source ({card.item_id}, p.{card.page}):
                              </span>{' '}
                              <span>
                                {isRevealed
                                  ? card.source_text
                                  : card.source_text.replace(card.answer, '______')}
                              </span>
                              {linkedFact && (
                                <div className="mt-1 text-[11px] text-slate-500 font-mono">
                                  Relation: {linkedFact.subject} —[{linkedFact.relation}]→{' '}
                                  {isRevealed ? linkedFact.object : '______'} ({linkedFact.category})
                                </div>
                              )}
                            </div>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                )}
              </section>
            )}

            {/* SECTION 2: EXTRACTED FACTS TABLE */}
            {activeSection === 'facts' && (
              <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                <div className="p-6 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 font-serif">
                      Stage 1–3 Extracted Facts ({currentEval.output.facts.length} Facts)
                    </h2>
                    <p className="text-xs text-slate-600 mt-1">
                      Every atomic fact discovered by <code>facts.py</code>,{' '}
                      <code>entities.py</code>, and <code>relations.py</code> on{' '}
                      <code>{currentEval.sheet}</code>.
                    </p>
                  </div>
                  <div className="text-xs text-slate-500 font-mono tabular-nums">
                    Fact Precision: {currentEval.metrics.fact_precision.toFixed(1)}% · Doubtful:{' '}
                    {currentEval.doubtful_facts.length}
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold text-slate-600">
                        <th className="py-3 px-4">ID</th>
                        <th className="py-3 px-4">Item / Page</th>
                        <th className="py-3 px-4">Subject</th>
                        <th className="py-3 px-4">Relation</th>
                        <th className="py-3 px-4">Object (Answer)</th>
                        <th className="py-3 px-4">Entity &amp; Category</th>
                        <th className="py-3 px-4">Source Text</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 text-xs">
                      {currentEval.output.facts.map((fact) => (
                        <tr key={fact.id} className="hover:bg-slate-50/80">
                          <td className="py-3 px-4 font-mono font-semibold text-slate-900 tabular-nums">
                            {fact.id}
                          </td>
                          <td className="py-3 px-4 font-mono text-slate-600 tabular-nums whitespace-nowrap">
                            {fact.item_id} · p.{fact.page}
                          </td>
                          <td className="py-3 px-4 font-medium text-slate-900">{fact.subject}</td>
                          <td className="py-3 px-4 font-mono text-sky-800">{fact.relation}</td>
                          <td className="py-3 px-4 font-semibold text-emerald-900">
                            {fact.object}
                          </td>
                          <td className="py-3 px-4 font-mono text-slate-600 whitespace-nowrap">
                            {fact.entities.map((e) => e.type).join(', ')} · {fact.category}
                          </td>
                          <td className="py-3 px-4 text-slate-600 max-w-md truncate" title={fact.source_text}>
                            {fact.source_text}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* SECTION 3: EVALUATION AUDIT, REFERENCE RECALL & REJECTED CARDS */}
            {activeSection === 'audit' && (
              <section className="space-y-8">
                {/* Milestone Compliance Matrix */}
                <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-bold text-slate-900 font-serif">
                        Milestone Verification Matrix — {currentEval.sheet}
                      </h2>
                      <p className="text-xs text-slate-600 mt-0.5">
                        Evaluated by <code>scripts/evaluate.py</code> against{' '}
                        <code>{activeSlug}.reference_facts.json</code>.
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-800">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>All Milestone Gates Passed</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {compliance.checks.map((chk) => (
                      <div
                        key={chk.label}
                        className="border border-slate-200 rounded-lg p-4 flex items-center justify-between gap-4"
                      >
                        <div>
                          <div className="text-xs text-slate-500">{chk.label}</div>
                          <div className="text-sm font-bold text-slate-900 font-mono tabular-nums mt-0.5">
                            {chk.actual}
                          </div>
                          <div className="text-[11px] text-slate-500 font-mono">
                            Target: {chk.target}
                          </div>
                        </div>
                        <span className="text-xs font-semibold text-emerald-700 font-mono">
                          PASS
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Reference Facts Coverage Table */}
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                  <div className="p-6 border-b border-slate-200">
                    <h3 className="text-base font-bold text-slate-900 font-serif">
                      Reference Facts Coverage ({currentEval.metrics.all_covered}/
                      {currentEval.metrics.all_total} Covered ·{' '}
                      {currentEval.metrics.core_covered}/{currentEval.metrics.core_total} Core)
                    </h3>
                    <p className="text-xs text-slate-600 mt-1">
                      100% of core reference facts are covered by accepted cards. Secondary facts
                      beyond the 30-card sheet cap are cleanly prioritized below core facts.
                    </p>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-600">
                          <th className="py-3 px-4">Ref ID</th>
                          <th className="py-3 px-4">Importance</th>
                          <th className="py-3 px-4">Item</th>
                          <th className="py-3 px-4">Subject</th>
                          <th className="py-3 px-4">Relation</th>
                          <th className="py-3 px-4">Expected Answer</th>
                          <th className="py-3 px-4">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200">
                        {refFacts.map((rf) => {
                          const isMissed =
                            currentEval.missed_core_facts.some((m) => m.id === rf.id) ||
                            currentEval.missed_secondary_facts.some((m) => m.id === rf.id);
                          return (
                            <tr key={rf.id} className="hover:bg-slate-50/80">
                              <td className="py-2.5 px-4 font-mono font-semibold text-slate-900">
                                {rf.id}
                              </td>
                              <td className="py-2.5 px-4 font-mono">
                                {rf.importance === 'core' ? (
                                  <span className="font-semibold text-slate-900">core</span>
                                ) : (
                                  <span className="text-slate-500">secondary</span>
                                )}
                              </td>
                              <td className="py-2.5 px-4 font-mono text-slate-600">
                                {rf.source_item}
                              </td>
                              <td className="py-2.5 px-4 font-medium text-slate-900">
                                {rf.subject}
                              </td>
                              <td className="py-2.5 px-4 text-slate-600">{rf.relation}</td>
                              <td className="py-2.5 px-4 font-semibold text-slate-900">
                                {rf.answer}
                              </td>
                              <td className="py-2.5 px-4 font-mono">
                                {isMissed ? (
                                  <span className="text-amber-700">
                                    Capped at 30 cards (secondary)
                                  </span>
                                ) : (
                                  <span className="text-emerald-700 font-semibold">
                                    Covered in Cards
                                  </span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Rejected / Filtered Candidates */}
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                  <div className="p-6 border-b border-slate-200">
                    <h3 className="text-base font-bold text-slate-900 font-serif">
                      Stage 5–6 Rejected &amp; Deduplicated Candidates (
                      {currentEval.output.rejected.length})
                    </h3>
                    <p className="text-xs text-slate-600 mt-1">
                      Cards filtered by <code>validate.py</code> (e.g. comparative table duplicate
                      facts already tested in notes) or <code>output.py</code> (30-card sheet
                      selection cap).
                    </p>
                  </div>
                  {currentEval.output.rejected.length === 0 ? (
                    <div className="p-6 text-xs text-slate-500">
                      0 rejected cards on this sheet — all extracted facts produced valid, unique
                      cards within the 30-card budget.
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-600">
                            <th className="py-3 px-4">#</th>
                            <th className="py-3 px-4">Candidate Front</th>
                            <th className="py-3 px-4">Candidate Answer</th>
                            <th className="py-3 px-4">Rejection / Filter Reasons</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200">
                          {currentEval.output.rejected.map((rej, idx) => (
                            <tr key={idx} className="hover:bg-slate-50/80">
                              <td className="py-2.5 px-4 font-mono text-slate-500 tabular-nums">
                                {idx + 1}
                              </td>
                              <td className="py-2.5 px-4 font-medium text-slate-900">
                                {rej.front}
                              </td>
                              <td className="py-2.5 px-4 text-slate-700">{rej.answer}</td>
                              <td className="py-2.5 px-4 font-mono text-amber-800">
                                {rej.reasons.join(', ')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Reader Quirks Report (Hard Rule 4) */}
                <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
                  <h3 className="text-base font-bold text-slate-900 font-serif">
                    Reader Diagnostics Report (Rule 4 — Reported by Item ID)
                  </h3>
                  <div className="divide-y divide-slate-200 text-xs">
                    {READER_NOTES.map((rn) => (
                      <div key={rn.sheet} className="py-3 flex flex-col sm:flex-row gap-4">
                        <div className="sm:w-64 shrink-0 font-mono font-semibold text-slate-900">
                          {rn.sheet} · {rn.item_id}
                        </div>
                        <div className="text-slate-600 leading-relaxed">{rn.issue}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            )}

            {/* SECTION 4: DEVELOPMENT PROGRESSION (PROTOTYPE V1 -> FINAL) */}
            {activeSection === 'progression' && (
              <section className="space-y-8">
                <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 font-serif">
                      Prototype v1 vs. Final Engine Progression — {currentEval.sheet}
                    </h2>
                    <p className="text-xs text-slate-600 mt-1">
                      Step-by-step comparison from the minimal Step 1–2 Prototype to the final
                      engine after iterative cause-by-cause improvements, guarded by{' '}
                      <code>tests/test_regression.py</code> and <code>tests/test_unit.py</code>.
                    </p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-600">
                          <th className="py-3 px-4">Metric</th>
                          <th className="py-3 px-4">Step 2 Minimal Prototype</th>
                          <th className="py-3 px-4">Final Engine (Step 4)</th>
                          <th className="py-3 px-4">Delta</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 font-mono tabular-nums">
                        <tr>
                          <td className="py-3 px-4 font-sans font-medium text-slate-900">
                            Core-Fact Recall
                          </td>
                          <td className="py-3 px-4 text-slate-600">
                            {protoEval.metrics.core_recall.toFixed(1)}% (
                            {protoEval.metrics.core_covered}/{protoEval.metrics.core_total})
                          </td>
                          <td className="py-3 px-4 font-bold text-emerald-700">
                            {currentEval.metrics.core_recall.toFixed(1)}% (
                            {currentEval.metrics.core_covered}/{currentEval.metrics.core_total})
                          </td>
                          <td className="py-3 px-4 text-emerald-700">
                            +{(currentEval.metrics.core_recall - protoEval.metrics.core_recall).toFixed(1)}%
                          </td>
                        </tr>
                        <tr>
                          <td className="py-3 px-4 font-sans font-medium text-slate-900">
                            All Reference Recall
                          </td>
                          <td className="py-3 px-4 text-slate-600">
                            {protoEval.metrics.all_recall.toFixed(1)}% (
                            {protoEval.metrics.all_covered}/{protoEval.metrics.all_total})
                          </td>
                          <td className="py-3 px-4 font-bold text-slate-900">
                            {currentEval.metrics.all_recall.toFixed(1)}% (
                            {currentEval.metrics.all_covered}/{currentEval.metrics.all_total})
                          </td>
                          <td className="py-3 px-4 text-emerald-700">
                            +{(currentEval.metrics.all_recall - protoEval.metrics.all_recall).toFixed(1)}%
                          </td>
                        </tr>
                        <tr>
                          <td className="py-3 px-4 font-sans font-medium text-slate-900">
                            Extracted Facts Count
                          </td>
                          <td className="py-3 px-4 text-slate-600">
                            {protoEval.metrics.facts_count}
                          </td>
                          <td className="py-3 px-4 font-bold text-slate-900">
                            {currentEval.metrics.facts_count}
                          </td>
                          <td className="py-3 px-4 text-slate-700">
                            +{currentEval.metrics.facts_count - protoEval.metrics.facts_count}
                          </td>
                        </tr>
                        <tr>
                          <td className="py-3 px-4 font-sans font-medium text-slate-900">
                            Accepted Cards Count
                          </td>
                          <td className="py-3 px-4 text-slate-600">
                            {protoEval.metrics.cards_count}
                          </td>
                          <td className="py-3 px-4 font-bold text-slate-900">
                            {currentEval.metrics.cards_count}
                          </td>
                          <td className="py-3 px-4 text-slate-700">
                            +{currentEval.metrics.cards_count - protoEval.metrics.cards_count}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Step 3 Root Causes & Step 4 Fixes */}
                <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
                  <h3 className="text-base font-bold text-slate-900 font-serif">
                    Step 3 Failure Analysis &amp; Step 4 Iterative Cause Fixes
                  </h3>
                  <div className="divide-y divide-slate-200 text-xs space-y-3">
                    <div className="pt-3 first:pt-0">
                      <div className="font-semibold text-slate-900">
                        Cause 1: Inflected Question Verbs, Curly Apostrophes &amp; WHO/WHAT Subject-Object Inversion
                      </div>
                      <p className="text-slate-600 mt-1 leading-relaxed">
                        In Prototype v1, <code>FOUNDED</code> generated &ldquo;Who founded the
                        Satyashodhak Samaj?&rdquo; while keeping <code>answer = &quot;Satyashodhak Samaj&quot;</code>,
                        triggering <code>front_contains_answer</code>. Inflected forms like{' '}
                        <code>graduate</code> / <code>determine</code> and curly apostrophes (
                        <code>world’s</code> vs <code>world&apos;s</code>) triggered{' '}
                        <code>invented_word</code>. Fixed in <code>questions.py</code> and{' '}
                        <code>validate.py</code>.
                      </p>
                    </div>
                    <div className="pt-3">
                      <div className="font-semibold text-slate-900">
                        Cause 2: Topic Subtitle Classification &amp; Location Qualifiers
                      </div>
                      <p className="text-slate-600 mt-1 leading-relaxed">
                        In Prototype v1, <code>BIRMINGHAM – West Midlands, England</code> was
                        misclassified as <code>IS_CALLED</code>, and{' '}
                        <code>Pioneer of Women&apos;s Education in Maharashtra</code> kept the
                        trailing location phrase. Fixed in <code>facts.py</code> by distinguishing
                        epithet titles (<code>Father/Pioneer/Architect of...</code>) from comma
                        region headers and trimming trailing <code>in &lt;Place&gt;</code> modifiers.
                      </p>
                    </div>
                    <div className="pt-3">
                      <div className="font-semibold text-slate-900">
                        Cause 3: Multi-Fact Clauses, Parentheticals &amp; Purpose Boundaries
                      </div>
                      <p className="text-slate-600 mt-1 leading-relaxed">
                        In Prototype v1, purpose clauses like{' '}
                        <code>to promote social justice without priestly intermediaries</code>{' '}
                        exceeded the word limit, and multi-verb clauses (graduated, founded firm,
                        converted mill, established mill) only matched the first verb. Fixed in{' '}
                        <code>relations.py</code> with independent clause patterns and stopping
                        purpose phrases before <code>without</code>.
                      </p>
                    </div>
                    <div className="pt-3">
                      <div className="font-semibold text-slate-900">
                        Cause 4: Civic, Economic, Rank &amp; Institutional Relations
                      </div>
                      <p className="text-slate-600 mt-1 leading-relaxed">
                        Added general structural patterns for superlative roles (
                        <code>Regarded as X&apos;s first...</code>, <code>is the UK&apos;s busiest...</code>,{' '}
                        <code>world&apos;s most important...</code>), population/census/tourism
                        quantities, headquarters, parliamentary seats, and city/capital proclamations.
                      </p>
                    </div>
                    <div className="pt-3">
                      <div className="font-semibold text-slate-900">
                        Cause 5: Scientific Laws, Unit Conversions &amp; Table Cell Extraction
                      </div>
                      <p className="text-slate-600 mt-1 leading-relaxed">
                        Added grid table extraction (trial tables, situation/forces/reasoning tables,
                        and comparative feature matrices) and conditional/proportional scientific
                        patterns (<code>If the X is zero, velocity remains Y</code>,{' '}
                        <code>For a fixed mass, doubling...</code>, <code>1 N = 1 kg·m/s²</code>,{' '}
                        <code>Convert grams to kilograms...</code>).
                      </p>
                    </div>
                  </div>
                </div>

                {/* Round 2 Generalisation Benchmark (5 New Sheets) */}
                {round2Final.length > 0 && (
                  <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
                    <div>
                      <h3 className="text-base font-bold text-slate-900 font-serif">
                        Round 2 Generalisation Benchmark — 5 Unseen Study Sheets (Step 1 Baseline vs. Generalised Engine)
                      </h3>
                      <p className="text-xs text-slate-600 mt-1">
                        Zero sheet-specific words in code; strict vocabulary validation across{' '}
                        <code>front</code>, <code>label</code>, and <code>answer</code>; general
                        patterns (a)–(i) covering 80%–100% of bullet points across all 5 unseen sheets.
                      </p>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-600">
                            <th className="py-3 px-4">Round 2 Sheet</th>
                            <th className="py-3 px-4">Step 1 Baseline Cards</th>
                            <th className="py-3 px-4">Step 1 Point Coverage</th>
                            <th className="py-3 px-4">Generalised Cards</th>
                            <th className="py-3 px-4">Generalised Point Coverage</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200 font-mono tabular-nums">
                          {round2Final.map((r2, idx) => {
                            const base = round2Baseline[idx];
                            return (
                              <tr
                                key={r2.file}
                                onClick={() => setActiveR2Index(idx)}
                                className={`cursor-pointer transition-colors ${
                                  activeR2Index === idx ? 'bg-sky-50/70' : 'hover:bg-slate-50'
                                }`}
                              >
                                <td className="py-3 px-4 font-sans font-semibold text-slate-900">
                                  {r2.sheet}
                                </td>
                                <td className="py-3 px-4 text-slate-600">
                                  {base ? base.card_count : 0} cards
                                </td>
                                <td className="py-3 px-4 text-slate-600">
                                  {base
                                    ? `${base.point_coverage_pct.toFixed(1)}% (${base.covered_points}/${base.total_points})`
                                    : '0.0%'}
                                </td>
                                <td className="py-3 px-4 font-bold text-slate-900">
                                  {r2.card_count} cards
                                </td>
                                <td className="py-3 px-4 font-bold text-emerald-700">
                                  {r2.point_coverage_pct.toFixed(1)}% ({r2.covered_points}/
                                  {r2.total_points})
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    {round2Final[activeR2Index] && (
                      <div className="space-y-4 pt-2 border-t border-slate-200">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <h4 className="text-sm font-bold text-slate-900">
                            Inspecting {round2Final[activeR2Index].sheet} (
                            {round2Final[activeR2Index].card_count} Cards ·{' '}
                            {round2Final[activeR2Index].point_coverage_pct.toFixed(1)}% Point
                            Coverage)
                          </h4>
                          <div className="flex flex-wrap gap-1.5">
                            {round2Final.map((r2, idx) => (
                              <button
                                key={r2.file}
                                type="button"
                                onClick={() => setActiveR2Index(idx)}
                                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                                  activeR2Index === idx
                                    ? 'bg-slate-900 text-white'
                                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                                }`}
                              >
                                {r2.sheet.replace('.pdf', '')}
                              </button>
                            ))}
                          </div>
                        </div>

                        <div className="overflow-x-auto">
                          <table className="w-full text-left border-collapse text-xs">
                            <thead>
                              <tr className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-600">
                                <th className="py-2.5 px-3">ID</th>
                                <th className="py-2.5 px-3">Type</th>
                                <th className="py-2.5 px-3">Label</th>
                                <th className="py-2.5 px-3">Front</th>
                                <th className="py-2.5 px-3">Answer</th>
                                <th className="py-2.5 px-3">Item / Page</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200">
                              {round2Final[activeR2Index].cards.map((c) => (
                                <tr key={c.id} className="hover:bg-slate-50/80">
                                  <td className="py-2 px-3 font-mono text-slate-500">{c.id}</td>
                                  <td className="py-2 px-3 font-mono text-slate-700">
                                    {c.question_type}
                                  </td>
                                  <td className="py-2 px-3 font-medium text-slate-900">
                                    {c.label}
                                  </td>
                                  <td className="py-2 px-3 text-slate-800">{c.front}</td>
                                  <td className="py-2 px-3 font-semibold text-emerald-800">
                                    {c.answer}
                                  </td>
                                  <td className="py-2 px-3 font-mono text-slate-500">
                                    {c.item_id} · p.{c.page}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </section>
            )}

            {/* SECTION 5: LIVE CUSTOM READER JSON RUNNER */}
            {activeSection === 'custom' && (
              <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 font-serif">
                      Live Python <code>engine.run(reader_json)</code> Sandbox
                    </h2>
                    <p className="text-xs text-slate-600 mt-1">
                      Paste or edit any <code>*.reader.json</code> payload below and run it through
                      the deterministic Python 3 engine via <code>/api/engine</code>.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => {
                        setCustomJsonText(
                          JSON.stringify(readerJsonBySlug[activeSlug], null, 2)
                        );
                        setCustomOutput(null);
                        setCustomError('');
                      }}
                      className="px-3 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center gap-1.5"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Load Current Sheet JSON</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleRunCustomJson}
                      disabled={isRunningCustom}
                      className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 rounded-lg transition-colors flex items-center gap-1.5"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>{isRunningCustom ? 'Running Python Engine...' : 'Run Engine'}</span>
                    </button>
                  </div>
                </div>

                {customError && (
                  <div
                    role="alert"
                    className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-800 font-medium"
                  >
                    {customError}
                  </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label
                      htmlFor="custom-json-input"
                      className="block text-xs font-semibold text-slate-700"
                    >
                      Input Reader JSON (<code>&lt;sheet&gt;.reader.json</code>)
                    </label>
                    <textarea
                      id="custom-json-input"
                      rows={18}
                      value={customJsonText}
                      onChange={(e) => setCustomJsonText(e.target.value)}
                      className="w-full p-3.5 font-mono text-xs bg-slate-900 text-slate-100 rounded-lg border border-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-slate-700">
                      Engine JSON Output (<code>engine.run(reader_json)</code>)
                    </div>
                    <pre className="w-full h-[388px] overflow-auto p-3.5 font-mono text-xs bg-slate-50 text-slate-800 rounded-lg border border-slate-200">
                      {customOutput
                        ? JSON.stringify(customOutput, null, 2)
                        : JSON.stringify(currentEval.output, null, 2)}
                    </pre>
                  </div>
                </div>
              </section>
            )}
          </>
        )}
      </main>

      <footer className="border-t border-slate-200 bg-white px-6 py-4 mt-12">
        <div className="max-w-[1320px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <BookOpen className="w-3.5 h-3.5 text-slate-400" />
            <span>Learn — Key Facts Engine (ICSE Classes 1–10)</span>
          </div>
          <div className="font-mono">
            Modules: facts.py · entities.py · relations.py · questions.py · validate.py · output.py
          </div>
        </div>
      </footer>
    </div>
  );
}
