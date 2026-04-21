/**
 * render_worker.mjs
 *
 * Node.js render worker using @remotion/renderer API.
 * Called by the Python backend in production instead of the `remotion render` CLI.
 *
 * Advantages over CLI:
 *  - Uses a pre-built static bundle (baked into Docker image at build time)
 *  - Skips esbuild re-compilation on every call (~60-90s saved)
 *  - selectComposition() auto-detects durationInFrames from the input props
 *
 * Usage:
 *   node render_worker.mjs <props.json> <output.mp4>
 *
 * Environment variables:
 *   REMOTION_BUNDLE_DIR      Path to the pre-built bundle (default: ../renderer-bundle)
 *   REMOTION_CHROMIUM_PATH   Path to Chromium binary (default: /usr/bin/chromium)
 *   REMOTION_CONCURRENCY     Number of parallel browser tabs (default: 1)
 */

import { selectComposition, renderMedia } from '@remotion/renderer';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ── Args ─────────────────────────────────────────────────────────────────────
const [, , propsPath, outputPath] = process.argv;

if (!propsPath || !outputPath) {
  process.stderr.write(
    'Usage: node render_worker.mjs <props.json> <output.mp4>\n'
  );
  process.exit(1);
}

// ── Config ───────────────────────────────────────────────────────────────────
const props = JSON.parse(readFileSync(propsPath, 'utf-8'));

const bundleDir =
  process.env.REMOTION_BUNDLE_DIR ??
  resolve(__dirname, '..', 'renderer-bundle');

const browserExecutable =
  process.env.REMOTION_CHROMIUM_PATH ?? '/usr/bin/chromium';

const concurrency = Number(process.env.REMOTION_CONCURRENCY ?? '1');

process.stderr.write(
  `[render_worker] bundle=${bundleDir} concurrency=${concurrency} output=${outputPath}\n`
);

// ── Detect composition (auto-resolves durationInFrames from props) ────────────
const composition = await selectComposition({
  serveUrl: bundleDir,
  id: 'Whiteboard',
  inputProps: props,
  chromiumOptions: { disableSandbox: true },
  browserExecutable,
  timeoutInMilliseconds: 60_000,
});

process.stderr.write(
  `[render_worker] composition ready: ${composition.durationInFrames} frames @ ${composition.fps}fps\n`
);

// ── Render ───────────────────────────────────────────────────────────────────
await renderMedia({
  composition,
  serveUrl: bundleDir,
  codec: 'h264',
  outputLocation: outputPath,
  inputProps: props,
  chromiumOptions: { disableSandbox: true },
  browserExecutable,
  concurrency,
  timeoutInMilliseconds: 900_000,
  onProgress: ({ progress }) => {
    process.stderr.write(`\r[render_worker] ${Math.round(progress * 100)}%  `);
  },
});

process.stderr.write('\n[render_worker] Complete → ' + outputPath + '\n');
