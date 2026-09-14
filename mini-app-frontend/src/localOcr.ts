/** No API calls: pixels/text stay inside disposable browser workers. */
export function readPhotoLocally(image: string, signal: AbortSignal, progress: (message: string) => void): Promise<string> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) { reject(new Error('Распознавание отменено.')); return; }
    const worker = new Worker(new URL('./localOcr.worker.ts', import.meta.url), { type: 'module' });
    const finish = (error?: string, text = '') => {
      clearTimeout(timer);
      signal.removeEventListener('abort', abort);
      worker.terminate();
      if (error) reject(new Error(error)); else resolve(text);
    };
    const abort = () => finish('Распознавание отменено.');
    const timer = setTimeout(() => finish('Устройство не успело прочитать фото. Снимите одну пачку ближе или введите название вручную.'), 90000);
    signal.addEventListener('abort', abort, { once: true });
    worker.onerror = () => finish('Не удалось запустить распознавание на устройстве. Проверьте интернет или введите название вручную.');
    worker.onmessage = ({ data }) => {
      if (data.error) finish('Не удалось прочитать фото. Проверьте интернет или введите название вручную.');
      else if (typeof data.text === 'string') finish(undefined, data.text.slice(0, 10000));
      else if (typeof data.progress === 'number') progress(`Читаем этикетку: ${data.progress}%`);
    };
    progress('Готовим распознавание…');
    const assets = new URL(`${import.meta.env.BASE_URL}ocr/v7/`, window.location.origin).href;
    worker.postMessage({ image, assets });
  });
}
