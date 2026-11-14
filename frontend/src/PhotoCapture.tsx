import { useEffect, useRef, useState } from 'react';
import { Camera, Check, ImagePlus, X } from 'lucide-react';
import { isNativeApp, takeNativePhoto } from './nativeBridge';

type Props = {
  donationId: string;
  photos: string[];
  onChange: (photos: string[]) => void;
  upload: (file: File, donationId: string) => Promise<{filename: string}>;
  onBusy: (busy: boolean) => void;
};

export default function PhotoCapture({donationId, photos, onChange, upload, onBusy}: Props) {
  const [camera, setCamera] = useState(false);
  const [ready, setReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [nativePending,setNativePending]=useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const nativeCamera = useRef<HTMLInputElement>(null);
  const mounted = useRef(true);
  const savingRef = useRef(false);
  const photosRef = useRef(photos);
  photosRef.current = photos;
  useEffect(() => {mounted.current = true; return () => {mounted.current = false;};}, []);
  useEffect(() => {
    if (!camera) return;
    let cancelled = false;
    let stream: MediaStream | null = null;
    setReady(false);
    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1600},height:{ideal:1200}},audio:false}).then(async media => {
      stream = media;
      if(cancelled){media.getTracks().forEach(t=>t.stop());return;}
      if(video.current){video.current.srcObject=media;await video.current.play();}
    }).catch(() => {
      stream?.getTracks().forEach(t=>t.stop());
      if(!cancelled){setError('Live camera unavailable. Use “Device camera” below to take a photo, or allow camera access on HTTPS.');setCamera(false);}
    });
    return () => {cancelled=true;stream?.getTracks().forEach(t=>t.stop());};
  }, [camera]);
  useEffect(() => {if(photos.length>=3)setCamera(false);}, [photos.length]);

  async function save(file: File) {
    if(savingRef.current || photosRef.current.length>=3 || !donationId) return;
    savingRef.current=true;setSaving(true);onBusy(true);setError('');
    try {
      const result=await upload(file,donationId);
      if(mounted.current)onChange([...photosRef.current,result.filename]);
    } catch(err){if(mounted.current)setError((err as Error).message);}
    finally{savingRef.current=false;if(mounted.current){setSaving(false);onBusy(false);}}
  }
  async function snap() {
    const source=video.current;
    if(!source?.videoWidth || savingRef.current)return;
    const canvas=document.createElement('canvas');
    const scale=Math.min(1,1600/source.videoWidth);
    canvas.width=Math.round(source.videoWidth*scale);canvas.height=Math.round(source.videoHeight*scale);
    canvas.getContext('2d')!.drawImage(source,0,0,canvas.width,canvas.height);
    const blob=await new Promise<Blob|null>(resolve=>canvas.toBlob(resolve,'image/jpeg',.88));
    if(blob)await save(new File([blob],`capture-${Date.now()}.jpg`,{type:'image/jpeg'}));
  }
  async function openCamera() {
    setError('');
    if(isNativeApp()){
      if(nativePending)return;
      setNativePending(true);onBusy(true);
      try{const file=await takeNativePhoto();if(mounted.current)await save(file);}
      catch(error){if(mounted.current&&(error as Error).message!=='cancelled')setError((error as Error).message);}
      finally{if(mounted.current){setNativePending(false);onBusy(false);}}
    }else if(typeof navigator.mediaDevices?.getUserMedia==='function')setCamera(true);
    else nativeCamera.current?.click();
  }
  const hasRoom=photos.length<3;
  return <div className="photo-capture">
    <div className="capture-heading"><b>Item photos · {photos.length}/3</b><span>{saving?'Saving to database…':photos.length>0?<><Check size={12}/>Saved to this bag</>:'Take photos without leaving this form'}</span></div>
    {camera&&<div className="live-camera"><video ref={video} playsInline muted onLoadedData={()=>setReady(true)} aria-label="Item camera preview"/><div className="camera-tools"><span>Photo {photos.length+1} of 3</span><button type="button" className="shutter" disabled={!ready||saving} onClick={snap} aria-label="Take and save photo"><Camera size={23}/></button><button type="button" className="icon-button" aria-label="Close camera" onClick={()=>setCamera(false)}><X size={21}/></button></div></div>}
    <div className="upload-grid">{photos.map((p,i)=><div className="upload-preview" key={p}><img src={`/api/photos/${p}`} alt={`Item photo ${i+1}`}/><button type="button" className="icon-button" disabled={saving} aria-label={`Remove photo ${i+1}`} onClick={()=>onChange(photos.filter(x=>x!==p))}><X size={15}/></button></div>)}</div>
    {hasRoom&&<div className="capture-actions"><button type="button" className="button primary" disabled={!donationId||saving||nativePending} onClick={openCamera}><Camera size={17}/>{camera?'Camera open':'Take photos'}</button><label className={`button secondary file-action ${!donationId||saving?'disabled':''}`}><Camera size={15}/>{isNativeApp()?'Choose image':'Device camera'}<input ref={nativeCamera} type="file" accept="image/*" capture="environment" disabled={!donationId||saving||nativePending} onChange={async e=>{const input=e.currentTarget;const file=input.files?.[0];if(file)await save(file);input.value='';}}/></label><label className={`button secondary file-action ${!donationId||saving?'disabled':''}`}><ImagePlus size={15}/>Library<input type="file" accept="image/jpeg,image/png,image/webp" disabled={!donationId||saving||nativePending} onChange={async e=>{const input=e.currentTarget;const file=input.files?.[0];if(file)await save(file);input.value='';}}/></label></div>}
    {!donationId&&<small>Select a donation bag before taking photos.</small>}
    {error&&<p className="form-error" role="alert">{error}</p>}
  </div>;
}
