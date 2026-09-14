import { afterEach, expect, it, vi } from 'vitest';
import { readPhotoLocally } from '../src/localOcr';

class TestWorker {
  static latest: TestWorker;
  onmessage?: (event: { data: object }) => void;
  onerror?: () => void;
  terminate = vi.fn();
  postMessage = vi.fn();
  constructor() { TestWorker.latest = this; }
}
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

it('returns text from the worker and releases it', async () => {
  vi.stubGlobal('Worker', TestWorker);
  const result = readPhotoLocally('pixels', new AbortController().signal, vi.fn());
  const worker = TestWorker.latest;
  expect(worker.postMessage).toHaveBeenCalledWith({ image: 'pixels', assets: expect.stringContaining('/ocr/v7/') });
  worker.onmessage?.({ data: { text: 'MANGO' } });
  expect(await result).toBe('MANGO');
  expect(worker.terminate).toHaveBeenCalledOnce();
});
it('cancels initialization before any OCR response', async () => {
  vi.stubGlobal('Worker', TestWorker);
  const controller = new AbortController();
  const result = readPhotoLocally('pixels', controller.signal, vi.fn());
  controller.abort();
  await expect(result).rejects.toThrow('отменено');
  expect(TestWorker.latest.terminate).toHaveBeenCalledOnce();
});
it('bounds time even when the OCR worker never initializes', async () => {
  vi.useFakeTimers(); vi.stubGlobal('Worker', TestWorker);
  const result = readPhotoLocally('pixels', new AbortController().signal, vi.fn());
  const rejected = expect(result).rejects.toThrow('не успело');
  await vi.advanceTimersByTimeAsync(90000);
  await rejected;
  expect(TestWorker.latest.terminate).toHaveBeenCalledOnce();
});
