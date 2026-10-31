import React, { useState } from 'react';
import { normalizeScientificNotationClient } from '../utils/engineLogic';
import { ScientificText } from './ScientificText';

interface ExtractionInspectorProps {
  extraction: any;
  imageScanExtraction: any;
  passages: any[];
  onRunExtraction: (payload: {
    pdfFixturePath?: string;
    pdfBase64?: string;
    extractedText?: string;
  }) => Promise<void>;
  isLoading: boolean;
}

export const ExtractionInspectorView: React.FC<ExtractionInspectorProps> = ({
  extraction,
  imageScanExtraction,
  passages,
  onRunExtraction,
  isLoading,
}) => {
  const [activeFixture, setActiveFixture] = useState<'constitution_pdf' | 'sample_pdf' | 'image_scan' | 'custom_text'>('constitution_pdf');
  const [selectedPageIdx, setSelectedPageIdx] = useState<number>(0);
  const [customText, setCustomText] = useState<string>(
    passages[0]?.text ||
      '--- Page 1 ---\nCHAPTER 1: ELECTROLYSIS\nDuring the electrolysis of acidified water, 2H2O(l) -> 2H2(g) + O2(g).\nIn aqueous CuSO4(aq) <=> Cu^{2+}(aq) + SO4^{2-}(aq).'
  );
  const [liveNotationInput, setLiveNotationInput] = useState<string>(
    '2H_2O(l) -> 2H_2(g) + O_2(g) | CuSO_4(aq) <=> Cu^{2+}(aq) + SO_4^{2-}(aq) | E = mc^2 | g = 9.8 m/s^2'
  );

  const displayedExtraction =
    activeFixture === 'image_scan' && imageScanExtraction ? imageScanExtraction : extraction;

  const pages: any[] = displayedExtraction?.pages || [];
  const currentPage = pages[selectedPageIdx] || pages[0] || null;
  const allTables: any[] = displayedExtraction?.tables || [];
  const allFigures: any[] = displayedExtraction?.figures || [];
  const allNotation: any[] = displayedExtraction?.notation_items || [];

  const handleSelectFixture = async (mode: 'constitution_pdf' | 'sample_pdf' | 'image_scan' | 'custom_text') => {
    setActiveFixture(mode);
    setSelectedPageIdx(0);
    if (mode === 'constitution_pdf') {
      await onRunExtraction({ pdfFixturePath: 'public/assets/aistudio/indian_constitution_history_lesson_0b1adbb9.pdf' });
    } else if (mode === 'sample_pdf') {
      await onRunExtraction({ pdfFixturePath: 'fixtures/icse_sample_science_history.pdf' });
    } else if (mode === 'image_scan') {
      await onRunExtraction({ pdfFixturePath: 'fixtures/image_only_scan.pdf' });
    }
  };

  const handleUploadPdf = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      if (typeof reader.result === 'string') {
        setActiveFixture('constitution_pdf');
        setSelectedPageIdx(0);
        await onRunExtraction({ pdfBase64: reader.result });
      }
    };
    reader.readAsDataURL(file);
  };

  return (
    <div className="space-y-8">
      {/* Top Control & Diagnostic Strip */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-100 pb-5">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              01. PDF &amp; Scientific Notation Extraction Component
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              Decoupled extraction engine preserving headings, structured tables, figure metadata, page associations, and coordinate-offset subscripts/superscripts.
            </p>
          </div>

          {/* Interactive Source Selector */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
              <button
                type="button"
                onClick={() => handleSelectFixture('constitution_pdf')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  activeFixture === 'constitution_pdf'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Indian Constitution PDF (Class 8)
              </button>
              <button
                type="button"
                onClick={() => handleSelectFixture('sample_pdf')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  activeFixture === 'sample_pdf'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                ICSE 3-Page Textbook PDF
              </button>
              <button
                type="button"
                onClick={() => handleSelectFixture('image_scan')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  activeFixture === 'image_scan'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Image-Only Scan PDF (OCR Test)
              </button>
              <button
                type="button"
                onClick={() => setActiveFixture('custom_text')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  activeFixture === 'custom_text'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Extracted-Text Input Mode
              </button>
            </div>

            <label className="px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors whitespace-nowrap shrink-0">
              Upload Custom PDF
              <input
                type="file"
                accept="application/pdf"
                onChange={handleUploadPdf}
                className="sr-only"
                aria-label="Upload Custom PDF"
              />
            </label>
          </div>
        </div>

        {/* Alternative Extracted-Text Input Box */}
        {activeFixture === 'custom_text' && (
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <label htmlFor="custom-extracted-text" className="text-xs font-semibold text-slate-800">
                Alternative Pre-Extracted Text Input (Learn Integration Bypass Mode)
              </label>
              <div className="flex items-center gap-2">
                {passages.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setCustomText(`--- Page 1 ---\n${p.text}`)}
                    className="px-2.5 py-1 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded hover:bg-slate-100 transition-colors whitespace-nowrap shrink-0"
                  >
                    Load {p.subject} (Class {p.class_level})
                  </button>
                ))}
              </div>
            </div>
            <textarea
              id="custom-extracted-text"
              rows={5}
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              className="w-full font-mono text-xs bg-white border border-slate-200 rounded-lg p-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-600"
            />
            <div className="flex justify-end">
              <button
                type="button"
                disabled={isLoading}
                onClick={() => onRunExtraction({ extractedText: customText })}
                className="px-4 py-2 text-xs font-medium text-white bg-sky-700 hover:bg-sky-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                {isLoading ? 'Parsing Text Input...' : 'Parse Extracted Text Input'}
              </button>
            </div>
          </div>
        )}

        {/* OCR & Extraction Status Banner (Dual-coded with explicit text + icon symbol) */}
        {displayedExtraction && (
          <div
            className={`rounded-lg p-4 border ${
              displayedExtraction.ocr_required
                ? 'bg-red-50 border-red-200 text-red-900'
                : 'bg-slate-50 border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
                  <span>
                    {displayedExtraction.ocr_required
                      ? '▲ OCR REQUIRED — IMAGE-ONLY PDF HALTED'
                      : '● DIGITAL TEXT LAYER VERIFIED'}
                  </span>
                  <span aria-hidden="true">·</span>
                  <span className="font-mono">
                    Status: {displayedExtraction.extraction_status}
                  </span>
                  <span aria-hidden="true">·</span>
                  <span className="font-mono">
                    Backend: {displayedExtraction.extractor_backend}
                  </span>
                </div>
                <p className="text-xs leading-relaxed">
                  {displayedExtraction.ocr_recommendation}
                </p>
              </div>

              <div className="flex items-center gap-4 text-xs font-mono tabular-nums shrink-0">
                <span>Pages: {displayedExtraction.page_count}</span>
                <span aria-hidden="true">·</span>
                <span>Tables: {allTables.length}</span>
                <span aria-hidden="true">·</span>
                <span>Figures: {allFigures.length}</span>
                <span aria-hidden="true">·</span>
                <span>Notation Tokens: {allNotation.length}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Split Stage: Left Page & Table/Figure Inspector (60%) | Right Notation & Warnings Deck (40%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Page-Associated Content, Tables, and Figures */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-6 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                Page-Associated Text, Headings &amp; Structured Tables
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Every extracted block retains its exact 1-indexed page reference (or null for unpaginated raw text).
              </p>
            </div>

            {pages.length > 0 && (
              <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
                {pages.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setSelectedPageIdx(idx)}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 tabular-nums ${
                      selectedPageIdx === idx
                        ? 'bg-white text-slate-900 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {p.page_number !== null ? `Page ${p.page_number}` : 'Unpaginated'}
                  </button>
                ))}
              </div>
            )}
          </div>

          {currentPage ? (
            <div className="space-y-5">
              {/* Page Metadata Line */}
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 font-mono tabular-nums">
                <span>
                  Page Reference: {currentPage.page_number !== null ? currentPage.page_number : 'null (unpaginated)'}
                </span>
                <span aria-hidden="true">·</span>
                <span>Characters: {currentPage.character_count}</span>
                <span aria-hidden="true">·</span>
                <span>Headings: {currentPage.headings?.length || 0}</span>
                <span aria-hidden="true">·</span>
                <span>Embedded Images: {currentPage.image_count}</span>
              </div>

              {/* Headings */}
              {currentPage.headings?.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-xs font-semibold text-slate-700">Detected Chapter / Section Headings</div>
                  {currentPage.headings.map((h: string, i: number) => (
                    <div
                      key={i}
                      className="text-sm font-semibold text-slate-900 bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2"
                    >
                      {h}
                    </div>
                  ))}
                </div>
              )}

              {/* Paragraphs */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-700">
                  Extracted Paragraphs (with Reconstructed Subscripts &amp; Superscripts)
                </div>
                {currentPage.paragraphs?.length > 0 ? (
                  <div className="space-y-2.5">
                    {currentPage.paragraphs.map((para: string, i: number) => (
                      <p
                        key={i}
                        className="text-sm text-slate-800 leading-relaxed bg-slate-50/70 border border-slate-200/80 rounded-lg p-3.5"
                      >
                        <ScientificText text={para} />
                      </p>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg p-4">
                    ▲ Zero extractable text paragraphs on this page. Image-only scan detected ({currentPage.image_count} image object).
                  </div>
                )}
              </div>

              {/* Extracted Structured Tables on this page */}
              {currentPage.tables?.length > 0 && (
                <div className="space-y-3 pt-2">
                  <div className="text-xs font-semibold text-slate-700">
                    Preserved Structured Tables (Page {currentPage.page_number ?? 'null'})
                  </div>
                  {currentPage.tables.map((tbl: any) => (
                    <div
                      key={tbl.table_id}
                      className="border border-slate-200 rounded-lg overflow-hidden"
                    >
                      <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex items-center justify-between text-xs">
                        <span className="font-semibold text-slate-800">{tbl.caption}</span>
                        <span className="font-mono text-slate-500">ID: {tbl.table_id}</span>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse text-xs">
                          <thead>
                            <tr className="bg-slate-50/60 border-b border-slate-200 text-slate-700">
                              {tbl.headers.map((h: string, hi: number) => (
                                <th key={hi} className="py-2.5 px-3 font-semibold">
                                  {h}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200">
                            {tbl.rows.map((row: string[], ri: number) => (
                              <tr key={ri} className="hover:bg-slate-50/50">
                                {row.map((cell: string, ci: number) => (
                                  <td key={ci} className="py-2.5 px-3 text-slate-800 font-mono">
                                    <ScientificText text={cell} />
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Figures & Visual-Only Safeguard Records */}
              {currentPage.figures?.length > 0 && (
                <div className="space-y-2 pt-2">
                  <div className="text-xs font-semibold text-slate-700">
                    Detected Figures, Diagrams &amp; Maps
                  </div>
                  {currentPage.figures.map((fig: any) => (
                    <div
                      key={fig.figure_id}
                      className="p-3.5 rounded-lg border border-slate-200 bg-slate-50 space-y-1 text-xs"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-semibold text-slate-900">{fig.caption}</span>
                        <span className="font-mono text-slate-600">
                          {fig.is_visual_only
                            ? '▲ Visual-Only Figure (Unread Diagram Guard Active)'
                            : `● Extracted Labels: ${fig.extracted_labels.join(', ')}`}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-slate-500 py-8 text-center">
              No pages available to display.
            </div>
          )}
        </div>

        {/* Right Column: Scientific & Mathematical Notation Catalog + Live Transpiler */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                Preserved Scientific &amp; Mathematical Notation Catalog
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Chemical equations, stoichiometric formulas, state symbols, physics equations, derivatives, and SI units extracted across the document.
              </p>
            </div>

            {allNotation.length > 0 ? (
              <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto pr-1">
                {allNotation.map((item: any, idx: number) => (
                  <div key={idx} className="py-2.5 flex items-center justify-between gap-3 text-xs">
                    <code className="font-mono text-slate-900 font-medium bg-slate-50 px-2 py-1 rounded border border-slate-200/80">
                      <ScientificText text={item.normalized} />
                    </code>
                    <div className="text-slate-500 font-mono tabular-nums shrink-0">
                      <span>{item.kind.replace('_', ' ')}</span>
                      <span aria-hidden="true"> · </span>
                      <span>p.{item.page_number ?? 'null'}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg p-4">
                No scientific notation tokens found in this document (e.g., image-only scan).
              </div>
            )}
          </div>

          {/* Interactive Scientific Notation Normalizer Sandbox */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                Interactive Notation Preservation Sandbox
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Test how raw textbook ASCII/LaTeX notation (`H_2SO_4`, `Cu^&#123;2+&#125;`, `-&gt;`, `&lt;=&gt;`) is normalized before question generation.
              </p>
            </div>

            <div className="space-y-2">
              <label htmlFor="notation-sandbox-input" className="block text-xs font-medium text-slate-700">
                Raw Extracted String Input
              </label>
              <input
                id="notation-sandbox-input"
                type="text"
                value={liveNotationInput}
                onChange={(e) => setLiveNotationInput(e.target.value)}
                className="w-full font-mono text-xs bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-600"
              />
            </div>

            <div className="space-y-1.5">
              <div className="text-xs font-medium text-slate-700">Normalized Output</div>
              <div
                data-testid="normalized-notation-output"
                className="font-mono text-sm font-medium text-slate-900 bg-slate-50 border border-slate-200 rounded-lg p-3 break-words"
              >
                <ScientificText text={normalizeScientificNotationClient(liveNotationInput)} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
