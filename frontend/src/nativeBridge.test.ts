import {afterEach, expect, test, vi} from 'vitest';
import {isNativeApp, printNativeLabels, scanNativeQr, takeNativePhoto, shareNativeFile} from './nativeBridge';

afterEach(() => {vi.unstubAllGlobals(); vi.restoreAllMocks(); vi.useRealTimers();});

test('browser printing falls back without claiming native support', () => {
  expect(isNativeApp()).toBe(false);
  expect(printNativeLabels(['bag-1'])).toBe(false);
  expect(shareNativeFile('draft.json', '{}')).toBe(false);
});

test('iOS shares the exact JSON export while older native apps retain browser fallback', () => {
  vi.stubGlobal('GivingFlowAndroid', {takePhoto: vi.fn(), scanQr: vi.fn(), printLabels: vi.fn()});
  expect(shareNativeFile('draft.json', '{}')).toBe(false);
  const shareFile = vi.fn();
  vi.stubGlobal('GivingFlowIOS', {takePhoto: vi.fn(), scanQr: vi.fn(), printLabels: vi.fn(), shareFile});
  expect(shareNativeFile('ITM-DEMO-shopify-draft.json', '{"currency":"AED"}')).toBe(true);
  expect(shareFile).toHaveBeenCalledWith('ITM-DEMO-shopify-draft.json', '{"currency":"AED"}');
});

test.each(['GivingFlowAndroid', 'GivingFlowIOS'])('%s forwards the exact label IDs to the platform', platform => {
  const printLabels = vi.fn();
  vi.stubGlobal(platform, {takePhoto: vi.fn(), scanQr: vi.fn(), printLabels});
  expect(isNativeApp()).toBe(true);
  expect(printNativeLabels(['first-id', 'second-id'])).toBe(true);
  expect(printLabels).toHaveBeenCalledWith('first-id,second-id');
});

test('iOS scan ignores an unrelated callback before accepting its own result', async () => {
  vi.stubGlobal('GivingFlowIOS', {
    takePhoto: vi.fn(), printLabels: vi.fn(),
    scanQr: (requestId: string) => queueMicrotask(() => {
      window.dispatchEvent(new CustomEvent('givingflow:qr', {detail: {requestId: 'other-operation', value: 'WRONG'}}));
      window.dispatchEvent(new CustomEvent('givingflow:qr', {detail: {requestId, value: 'BAG-CORRECT'}}));
    })
  });
  expect(await scanNativeQr()).toBe('BAG-CORRECT');
});

test('iOS camera cancellation rejects and removes its callback listener', async () => {
  const remove = vi.spyOn(window, 'removeEventListener');
  vi.stubGlobal('GivingFlowIOS', {
    scanQr: vi.fn(), printLabels: vi.fn(),
    takePhoto: (requestId: string) => queueMicrotask(() =>
      window.dispatchEvent(new CustomEvent('givingflow:photo', {detail: {requestId, error: 'cancelled'}})))
  });
  await expect(takeNativePhoto()).rejects.toThrow('cancelled');
  expect(remove).toHaveBeenCalledWith('givingflow:photo', expect.any(Function));
});

test('missing and empty native responses produce useful errors', async () => {
  await expect(scanNativeQr()).rejects.toThrow('Native camera is unavailable');
  vi.stubGlobal('GivingFlowIOS', {
    takePhoto: vi.fn(), printLabels: vi.fn(),
    scanQr: (requestId: string) => queueMicrotask(() =>
      window.dispatchEvent(new CustomEvent('givingflow:qr', {detail: {requestId}})))
  });
  await expect(scanNativeQr()).rejects.toThrow('No QR code returned');
});

test('a native operation that never responds times out and removes its listener', async () => {
  vi.useFakeTimers();
  const remove = vi.spyOn(window, 'removeEventListener');
  vi.stubGlobal('GivingFlowIOS', {takePhoto: vi.fn(), scanQr: vi.fn(), printLabels: vi.fn()});
  const pending = expect(scanNativeQr()).rejects.toThrow('Camera timed out');
  await vi.advanceTimersByTimeAsync(180000);
  await pending;
  expect(remove).toHaveBeenCalledWith('givingflow:qr', expect.any(Function));
});
