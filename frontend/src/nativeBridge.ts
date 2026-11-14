type NativeResult = {requestId: string; error?: string; base64?: string; value?: string};
type NativeBridge = {
  takePhoto: (requestId: string) => void;
  scanQr: (requestId: string) => void;
  printLabels: (ids: string) => void;
};

declare global {
  interface Window {
    GivingFlowAndroid?: NativeBridge;
    GivingFlowIOS?: NativeBridge;
  }
}

const bridge = () => window.GivingFlowIOS || window.GivingFlowAndroid;
export function isNativeApp() { return Boolean(bridge()); }

function request(eventName: string, launch: (native: NativeBridge, id: string) => void): Promise<NativeResult> {
  const native = bridge();
  if (!native) return Promise.reject(new Error('Native camera is unavailable. Please reopen the app.'));
  const id = globalThis.crypto?.randomUUID?.() || `native-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return new Promise((resolve, reject) => {
    const cleanup = () => { window.removeEventListener(eventName, receive); clearTimeout(timer); };
    const receive = (event: Event) => {
      const detail = (event as CustomEvent<NativeResult>).detail;
      if (detail?.requestId !== id) return;
      cleanup();
      if (detail.error) reject(new Error(detail.error)); else resolve(detail);
    };
    const timer = setTimeout(() => { cleanup(); reject(new Error('Camera timed out. Please try again.')); }, 180000);
    window.addEventListener(eventName, receive);
    try { launch(native, id); } catch (error) { cleanup(); reject(error); }
  });
}

export async function takeNativePhoto(): Promise<File> {
  const result = await request('givingflow:photo', (native, id) => native.takePhoto(id));
  if (!result.base64) throw new Error('No photo returned. Please retake it.');
  const raw = atob(result.base64), bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return new File([bytes], `capture-${Date.now()}.jpg`, {type: 'image/jpeg'});
}

export async function scanNativeQr(): Promise<string> {
  const result = await request('givingflow:qr', (native, id) => native.scanQr(id));
  if (!result.value) throw new Error('No QR code returned.');
  return result.value;
}

export function printNativeLabels(ids: string[]): boolean {
  const native = bridge();
  if (!native) return false;
  native.printLabels(ids.join(','));
  return true;
}
