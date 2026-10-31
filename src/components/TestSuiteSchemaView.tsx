import React, { useState } from 'react';

interface TestSuiteSchemaProps {
  fullEngineOutput: any;
  onRunTests: () => Promise<any>;
}

export const TestSuiteSchemaView: React.FC<TestSuiteSchemaProps> = ({
  fullEngineOutput,
  onRunTests,
}) => {
  const [testRunResult, setTestRunResult] = useState<{
    passed: boolean;
    output: string;
    timestamp: string;
  } | null>(null);
  const [isRunningTests, setIsRunningTests] = useState<boolean>(false);

  const handleTriggerTests = async () => {
    setIsRunningTests(true);
    try {
      const res = await onRunTests();
      setTestRunResult(res);
    } finally {
      setIsRunningTests(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Automated Python Unit Test Runner & Learn Integration Boundary */}
        <div className="lg:col-span-6 space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  04. Automated Validation &amp; Unit Test Suite
                </h2>
                <p className="text-xs text-slate-600 mt-1">
                  Execute `test_question_quality_engine.py` covering PDF extraction, OCR warnings, notation, schema validation, duplicates, and deterministic math/chemical verification.
                </p>
              </div>
              <button
                type="button"
                disabled={isRunningTests}
                onClick={handleTriggerTests}
                className="px-4 py-2 text-xs font-semibold text-white bg-sky-700 hover:bg-sky-800 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                {isRunningTests ? 'Running Python Tests...' : 'Run Python Test Suite'}
              </button>
            </div>

            {testRunResult ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono tabular-nums">
                  <span
                    className={`font-semibold ${
                      testRunResult.passed ? 'text-emerald-700' : 'text-red-700'
                    }`}
                  >
                    {testRunResult.passed
                      ? '● ALL PYTHON AUTOMATED TESTS PASSED (11 / 11)'
                      : '✕ TEST SUITE REPORTED FAILURES'}
                  </span>
                  <span className="text-slate-500">{testRunResult.timestamp}</span>
                </div>
                <pre className="text-[11px] font-mono bg-slate-900 text-slate-100 p-4 rounded-lg overflow-x-auto max-h-80">
                  {testRunResult.output}
                </pre>
              </div>
            ) : (
              <div className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg p-4">
                Click &ldquo;Run Python Test Suite&rdquo; above to execute `python3 -m unittest discover -s . -p &quot;test_*.py&quot; -v` and inspect live assertions.
              </div>
            )}
          </div>

          {/* Standalone Python API & Future Learn Integration Contract */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
            <h3 className="text-base font-semibold text-slate-900">
              Standalone Python Calling Interface &amp; Learn Integration Boundary
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              `question_quality_engine.py` is completely decoupled from Learn&apos;s internal codebase. It accepts either a local PDF path (`pdf_path`) or pre-extracted text (`extracted_text`) and returns validated JSON-serializable question records.
            </p>
            <pre className="text-[11px] font-mono bg-slate-900 text-slate-100 p-4 rounded-lg overflow-x-auto">
{`from question_quality_engine import (
    generate_questions,
    extract_pdf_content,
    QuestionQualityRubric,
    RubricConfig,
)

# 1. Generate from PDF or pre-extracted text
result = generate_questions(
    pdf_path="fixtures/icse_sample_science_history.pdf",
    class_level=10,
    subject="Chemistry",
    question_count=5,
    options={
        "provider": "auto",
        "rubric_config": {"min_average_score": 3.6, "min_source_fidelity": 4},
    },
)`}
            </pre>
          </div>
        </div>

        {/* Right: Validated Output JSON Schema Inspector */}
        <div className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                Validated Structured Output Schema (`questions` JSON)
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Every record is validated by `validate_output_schema()` and guaranteed JSON-serializable.
              </p>
            </div>
            <span className="text-xs font-mono text-slate-500 tabular-nums">
              Records: {fullEngineOutput?.questions?.length || 0}
            </span>
          </div>

          <pre className="text-[11px] font-mono bg-slate-900 text-slate-100 p-4 rounded-lg overflow-x-auto max-h-[540px]">
            {JSON.stringify(fullEngineOutput?.questions || [], null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
};
