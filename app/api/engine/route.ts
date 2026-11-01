import { NextRequest, NextResponse } from 'next/server';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const readerJson = body.reader_json;
    if (!readerJson || typeof readerJson !== 'object' || !Array.isArray(readerJson.items)) {
      return NextResponse.json(
        { error: 'Invalid input: reader_json must be an object containing an "items" array.' },
        { status: 400 }
      );
    }

    const script = `
import json, sys
import engine
data = json.loads(sys.stdin.read())
out = engine.run(data)
print(json.dumps(out, ensure_ascii=False))
`;
    const stdout = execFileSync('python3', ['-c', script], {
      cwd: process.cwd(),
      input: JSON.stringify(readerJson),
      encoding: 'utf-8',
      timeout: 5000,
    });

    const result = JSON.parse(stdout);
    return NextResponse.json(result);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to execute Python Key Facts engine';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
