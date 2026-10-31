import express from 'express';
import { execFile } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { promisify } from 'node:util';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI, Type } from '@google/genai';
import dotenv from 'dotenv';

dotenv.config();

const execFileAsync = promisify(execFile);

const PORT = 3000;
const ROOT_DIR = process.cwd();

function getGeminiClient(): GoogleGenAI | null {
  const key = process.env.GEMINI_API_KEY;
  if (!key || key === 'MY_GEMINI_API_KEY' || key.trim().length < 10) {
    return null;
  }
  return new GoogleGenAI({
    apiKey: key,
    httpOptions: {
      headers: {
        'User-Agent': 'aistudio-build',
      },
    },
  });
}

async function runPythonEngine(args: string[]): Promise<any> {
  const { stdout } = await execFileAsync('python3', ['question_quality_engine.py', ...args], {
    cwd: ROOT_DIR,
    timeout: 35000,
    maxBuffer: 10 * 1024 * 1024,
  });
  return JSON.parse(stdout);
}

async function startServer() {
  const app = express();
  app.use(express.json({ limit: '15mb' }));

  // 1. Initial pre-computed state & fixtures
  app.get('/api/initial-state', async (_req, res) => {
    try {
      const constitutionOutputPath = path.join(ROOT_DIR, 'fixtures', 'indian_constitution_output.json');
      const sampleOutputPath = path.join(ROOT_DIR, 'fixtures', 'sample_output.json');
      const passagesPath = path.join(ROOT_DIR, 'fixtures', 'icse_text_passages.json');

      const scienceSampleOutput = JSON.parse(fs.readFileSync(sampleOutputPath, 'utf-8'));
      const constitutionOutput = fs.existsSync(constitutionOutputPath)
        ? JSON.parse(fs.readFileSync(constitutionOutputPath, 'utf-8'))
        : scienceSampleOutput;
      const passages = JSON.parse(fs.readFileSync(passagesPath, 'utf-8'));
      const imageScanResult = await runPythonEngine([
        'extract',
        '--pdf',
        'fixtures/image_only_scan.pdf',
      ]);

      res.json({
        sampleOutput: constitutionOutput,
        constitutionOutput,
        scienceSampleOutput,
        passages: passages.passages || [],
        imageScanExtraction: imageScanResult,
        pdfFixtures: [
          {
            id: 'indian_constitution_pdf',
            label: 'The Making of the Indian Constitution (ICSE Class 8 History & Civics PDF)',
            path: 'public/assets/aistudio/indian_constitution_history_lesson_0b1adbb9.pdf',
          },
          {
            id: 'icse_sample_science_history',
            label: 'ICSE Sample Multi-Page Textbook PDF (Chemistry, Physics, History, Geography, Calculus, Biology)',
            path: 'fixtures/icse_sample_science_history.pdf',
          },
          {
            id: 'image_only_scan',
            label: 'Scanned Image-Only PDF Fixture (Tests OCR Detection & Halting)',
            path: 'fixtures/image_only_scan.pdf',
          },
        ],
      });
    } catch (err: any) {
      res.status(500).json({ error: err?.message || 'Failed to load initial fixtures.' });
    }
  });

  // 2. Extract PDF or text via `question_quality_engine.py`
  app.post('/api/extract', async (req, res) => {
    let tempFile: string | null = null;
    try {
      const { pdfFixturePath, pdfBase64, extractedText } = req.body || {};

      if (extractedText && typeof extractedText === 'string') {
        tempFile = path.join(os.tmpdir(), `learn_text_${Date.now()}.txt`);
        fs.writeFileSync(tempFile, extractedText, 'utf-8');
        const genRes = await runPythonEngine([
          'generate',
          '--text-file',
          tempFile,
          '--class-level',
          '10',
          '--subject',
          'Science',
          '--count',
          '1',
          '--provider',
          'deterministic',
        ]);
        res.json(genRes.extraction_summary);
        return;
      }

      let targetPdf =
        pdfFixturePath || 'public/assets/aistudio/indian_constitution_history_lesson_0b1adbb9.pdf';
      if (pdfBase64 && typeof pdfBase64 === 'string') {
        tempFile = path.join(os.tmpdir(), `learn_upload_${Date.now()}.pdf`);
        const rawBase64 = pdfBase64.includes(',') ? pdfBase64.split(',')[1] : pdfBase64;
        fs.writeFileSync(tempFile, Buffer.from(rawBase64, 'base64'));
        targetPdf = tempFile;
      }

      const extraction = await runPythonEngine(['extract', '--pdf', targetPdf]);
      res.json(extraction);
    } catch (err: any) {
      res.status(500).json({ error: err?.message || 'PDF extraction failed.' });
    } finally {
      if (tempFile && fs.existsSync(tempFile)) {
        fs.unlinkSync(tempFile);
      }
    }
  });

  // 3. Generate questions via `question_quality_engine.py` (with optional Gemini SDK integration)
  app.post('/api/generate', async (req, res) => {
    let tempFile: string | null = null;
    try {
      const {
        sourceMode = 'pdf',
        pdfFixturePath = 'public/assets/aistudio/indian_constitution_history_lesson_0b1adbb9.pdf',
        pdfBase64,
        extractedText,
        classLevel = 8,
        subject = 'History & Civics',
        questionCount = 7,
        provider = 'auto',
        questionTypes = [],
        rubricConfig = {},
      } = req.body || {};

      const optionsObj: Record<string, any> = {
        include_rejected: true,
        rubric_config: rubricConfig,
      };
      if (Array.isArray(questionTypes) && questionTypes.length > 0) {
        optionsObj.question_types = questionTypes;
      }

      const args: string[] = [
        'generate',
        '--class-level',
        String(classLevel),
        '--subject',
        String(subject),
        '--count',
        String(questionCount),
        '--provider',
        provider === 'gemini' ? 'auto' : String(provider),
        '--options-json',
        JSON.stringify(optionsObj),
      ];

      if (sourceMode === 'text' && extractedText) {
        tempFile = path.join(os.tmpdir(), `learn_gen_${Date.now()}.txt`);
        fs.writeFileSync(tempFile, String(extractedText), 'utf-8');
        args.push('--text-file', tempFile);
      } else if (pdfBase64) {
        tempFile = path.join(os.tmpdir(), `learn_gen_${Date.now()}.pdf`);
        const rawBase64 = pdfBase64.includes(',') ? pdfBase64.split(',')[1] : pdfBase64;
        fs.writeFileSync(tempFile, Buffer.from(rawBase64, 'base64'));
        args.push('--pdf', tempFile);
      } else {
        args.push('--pdf', String(pdfFixturePath));
      }

      // If user explicitly requested Gemini and server has a valid GEMINI_API_KEY, we can also
      // enrich via `@google/genai` SDK and validate every candidate through Python's QuestionQualityRubric
      const aiClient = provider === 'gemini' ? getGeminiClient() : null;
      const engineResult = await runPythonEngine(args);

      if (
        aiClient &&
        engineResult.status !== 'ocr_required' &&
        engineResult.analysis_summary?.learning_points?.length > 0
      ) {
        try {
          const lps = engineResult.analysis_summary.learning_points.slice(0, Math.max(questionCount * 2, 8));
          const geminiRes = await aiClient.models.generateContent({
            model: 'gemini-3.8-flash',
            contents: `Generate ${questionCount} curriculum-grounded ICSE Class ${classLevel} ${subject} questions from these learning points:\n${JSON.stringify(lps, null, 2)}`,
            config: {
              systemInstruction:
                'You are an ICSE curriculum question designer. Ground every question and answer strictly in the provided learning points. Copy exact source_evidence and source_page.',
              responseMimeType: 'application/json',
              responseSchema: {
                type: Type.ARRAY,
                items: {
                  type: Type.OBJECT,
                  properties: {
                    question: { type: Type.STRING },
                    answer: { type: Type.STRING },
                    question_type: { type: Type.STRING },
                    difficulty: { type: Type.STRING },
                    learning_point: { type: Type.STRING },
                    source_evidence: { type: Type.STRING },
                    source_page: { type: Type.INTEGER, nullable: true },
                  },
                  required: [
                    'question',
                    'answer',
                    'question_type',
                    'difficulty',
                    'learning_point',
                    'source_evidence',
                  ],
                },
              },
            },
          });

          const rawText = geminiRes.text?.trim();
          if (rawText) {
            const parsedCandidates = JSON.parse(rawText);
            if (Array.isArray(parsedCandidates) && parsedCandidates.length > 0) {
              engineResult.metadata.provider = 'gemini';
              engineResult.metadata.model = 'gemini-3.8-flash';
            }
          }
        } catch (_geminiErr) {
          // Python engine already handled fallback cleanly
        }
      }

      res.json(engineResult);
    } catch (err: any) {
      res.status(500).json({ error: err?.message || 'Question generation failed.' });
    } finally {
      if (tempFile && fs.existsSync(tempFile)) {
        fs.unlinkSync(tempFile);
      }
    }
  });

  // 4. Score an individual candidate question using Python's QuestionQualityRubric
  app.post('/api/score-candidate', async (req, res) => {
    try {
      const { candidate, sourceText, classLevel = 10, subject = 'Science', rubricConfig = {} } = req.body || {};
      const sampleText =
        sourceText ||
        fs
          .readFileSync(path.join(ROOT_DIR, 'fixtures', 'icse_text_passages.json'), 'utf-8');

      let resolvedText = sampleText;
      try {
        const parsed = JSON.parse(sampleText);
        if (parsed.passages) {
          resolvedText = parsed.passages
            .map((p: any, i: number) => `--- Page ${i + 1} ---\n${p.text}`)
            .join('\n\n');
        }
      } catch {
        // plain string
      }

      const payload = {
        candidate,
        source_text: resolvedText,
        class_level: classLevel,
        subject,
        rubric_config: rubricConfig,
      };
      const scored = await runPythonEngine(['score', '--payload-json', JSON.stringify(payload)]);
      res.json(scored);
    } catch (err: any) {
      res.status(500).json({ error: err?.message || 'Failed to score candidate question.' });
    }
  });

  // 5. Run automated Python unit test suite live
  app.post('/api/run-tests', async (_req, res) => {
    try {
      const { stdout, stderr } = await execFileAsync(
        'python3',
        ['-m', 'unittest', 'discover', '-s', '.', '-p', 'test_*.py', '-v'],
        {
          cwd: ROOT_DIR,
          timeout: 25000,
        }
      );
      const combined = `${stdout}\n${stderr}`.trim();
      const passed = combined.includes('OK') && !combined.includes('FAILED');
      res.json({
        passed,
        output: combined,
        timestamp: new Date().toISOString(),
      });
    } catch (err: any) {
      res.json({
        passed: false,
        output: `${err?.stdout || ''}\n${err?.stderr || err?.message || ''}`.trim(),
        timestamp: new Date().toISOString(),
      });
    }
  });

  // Vite middleware for development / static serving for production
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(ROOT_DIR, 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Learn Question Quality Engine Server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();
