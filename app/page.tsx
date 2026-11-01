import fs from 'node:fs';
import path from 'node:path';
import EngineWorkbench from '@/components/EngineWorkbench';
import { SheetEvaluation, ReferenceFact } from '@/lib/engine-types';

function loadJsonFile<T>(relPath: string): T {
  const fullPath = path.join(process.cwd(), relPath);
  return JSON.parse(fs.readFileSync(fullPath, 'utf-8')) as T;
}

export default function HomePage() {
  const finalEvals = loadJsonFile<Record<string, SheetEvaluation>>('data/final_eval.json');
  const prototypeEvals = loadJsonFile<Record<string, SheetEvaluation>>(
    'data/prototype_v1_eval.json'
  );

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
  };

  return (
    <EngineWorkbench
      finalEvals={finalEvals}
      prototypeEvals={prototypeEvals}
      referenceFactsBySlug={referenceFactsBySlug}
      readerJsonBySlug={readerJsonBySlug}
    />
  );
}
