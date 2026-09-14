import { mkdir, readdir, copyFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const dest = path.join(root, 'public/ocr/v7');
await mkdir(dest, { recursive: true });
await copyFile(path.join(root, 'node_modules/tesseract.js/dist/worker.min.js'), path.join(dest, 'worker.min.js'));
const core = path.join(root, 'node_modules/tesseract.js-core');
for (const file of await readdir(core)) {
  if (file.endsWith('.wasm.js')) await copyFile(path.join(core, file), path.join(dest, file));
}
for (const lang of ['eng', 'rus']) {
  await copyFile(path.join(root, `node_modules/@tesseract.js-data/${lang}/4.0.0_best_int/${lang}.traineddata.gz`), path.join(dest, `${lang}.traineddata.gz`));
}
await copyFile(path.join(core, 'LICENSE'), path.join(dest, 'LICENSE.txt'));
console.log('Local OCR assets prepared (English + Russian, no external CDN).');
