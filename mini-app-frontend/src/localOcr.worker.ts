import { createWorker, PSM } from 'tesseract.js';

// This outer worker lets the UI terminate initialization as well as recognition.
self.onmessage = async (event: MessageEvent<{ image: string; assets: string }>) => {
  let worker: Awaited<ReturnType<typeof createWorker>> | undefined;
  try {
    const { image, assets } = event.data;
    worker = await createWorker('eng+rus', 1, {
      workerPath: assets + 'worker.min.js', workerBlobURL: false,
      corePath: assets, langPath: assets.slice(0, -1), cachePath: 'hookah-ocr-v7',
      logger: message => {
        if (message.status === 'recognizing text') self.postMessage({ progress: Math.round(message.progress * 100) });
      },
      errorHandler: () => self.postMessage({ error: true }),
    });
    await worker.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT });
    const result = await worker.recognize('data:image/jpeg;base64,' + image);
    self.postMessage({ text: result.data.text.slice(0, 10000) });
  } catch {
    self.postMessage({ error: true });
  } finally {
    if (worker) await worker.terminate();
  }
};
