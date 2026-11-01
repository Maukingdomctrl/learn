import fs from 'node:fs';
import path from 'node:path';
import EngineWorkbench from '@/components/EngineWorkbench';
import { SheetEvaluation, ReferenceFact, Round2SheetResult } from '@/lib/engine-types';

function loadJsonFile<T>(relPath: string): T {
  const fullPath = path.join(process.cwd(), relPath);
  return JSON.parse(fs.readFileSync(fullPath, 'utf-8')) as T;
}

export default function HomePage() {
  const finalEvals = loadJsonFile<Record<string, SheetEvaluation>>('data/final_eval.json');
  const prototypeEvals = loadJsonFile<Record<string, SheetEvaluation>>(
    'data/prototype_v1_eval.json'
  );
  const round2Baseline = loadJsonFile<Round2SheetResult[]>('data/round2_baseline.json');
  const round2Final = loadJsonFile<Round2SheetResult[]>('data/round2_final.json');

  const referenceFactsBySlug: Record<string, ReferenceFact[]> = {
    'mumbai-personalities-flat': loadJsonFile<{ facts: ReferenceFact[] }>(
      'data/mumbai-personalities-flat.reference_facts.json'
    ).facts,
    'uk-cities-comparative-table': loadJsonFile<{ facts: ReferenceFact[] }>(
      'data/uk-cities-comparative-table.reference_facts.json'
    ).facts,
    'full-physics-forces': loadJsonFile<{ facts: ReferenceFact[] }>(
      'data/full-physics-forces.reference_facts.json'
    ).facts,
  };

  const readerJsonBySlug: Record<string, Record<string, unknown>> = {
    'mumbai-personalities-flat': loadJsonFile<Record<string, unknown>>(
      'data/mumbai-personalities-flat.reader.json'
    ),
    'uk-cities-comparative-table': loadJsonFile<Record<string, unknown>>(
      'data/uk-cities-comparative-table.reader.json'
    ),
    'full-physics-forces': loadJsonFile<Record<string, unknown>>(
      'data/full-physics-forces.reader.json'
    ),
    'civics-sheet': loadJsonFile<Record<string, unknown>>(
      'data/round2/civics-sheet.reader.json'
    ),
    equations: loadJsonFile<Record<string, unknown>>(
      'data/round2/equations.reader.json'
    ),
    'full-finance-lost-rupee': loadJsonFile<Record<string, unknown>>(
      'data/round2/full-finance-lost-rupee.reader.json'
    ),
    'history-sheet': loadJsonFile<Record<string, unknown>>(
      'data/round2/history-sheet.reader.json'
    ),
    'processes-sheet': loadJsonFile<Record<string, unknown>>(
      'data/round2/processes-sheet.reader.json'
    ),
  };

  return (
    <EngineWorkbench
      finalEvals={finalEvals}
      prototypeEvals={prototypeEvals}
      round2Baseline={round2Baseline}
      round2Final={round2Final}
      referenceFactsBySlug={referenceFactsBySlug}
      readerJsonBySlug={readerJsonBySlug}
    />
  );
}
