type NativeResult = {requestId: string; error?: string; base64?: string; value?: string};
declare global {
  interface Window {
    GivingFlowAndroid?: {
      takePhoto: (requestId: string) => void;
      scanQr: (requestId: string) => void;
      printLabels: (ids: string) => void;
    };
  }
}

export function isAndroidApp() {return Boolean(window.GivingFlowAndroid);}

function request(eventName: string, launch: (id: string) => void): Promise<NativeResult> {
  const id=crypto.randomUUID?.()||`native-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return new Promise((resolve,reject)=>{
    const cleanup=()=>{window.removeEventListener(eventName,receive);clearTimeout(timer);};
    const receive=(event: Event)=>{
      const detail=(event as CustomEvent<NativeResult>).detail;
      if(detail?.requestId!==id)return;
      cleanup();
      if(detail.error)reject(new Error(detail.error));else resolve(detail);
    };
    const timer=setTimeout(()=>{cleanup();reject(new Error('Camera timed out. Please try again.'));},180000);
    window.addEventListener(eventName,receive);
    try{launch(id);}catch(error){cleanup();reject(error);}
  });
}

export async function takeAndroidPhoto(): Promise<File> {
  const result=await request('givingflow:photo',id=>window.GivingFlowAndroid!.takePhoto(id));
  if(!result.base64)throw new Error('No photo returned. Please retake it.');
  const raw=atob(result.base64),bytes=new Uint8Array(raw.length);
  for(let i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);
  return new File([bytes],`android-${Date.now()}.jpg`,{type:'image/jpeg'});
}

export async function scanAndroidQr(): Promise<string> {
  const result=await request('givingflow:qr',id=>window.GivingFlowAndroid!.scanQr(id));
  if(!result.value)throw new Error('No QR code returned.');
  return result.value;
}
