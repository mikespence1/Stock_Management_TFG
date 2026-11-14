import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import PhotoCapture from './PhotoCapture';

afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();});

test('takes a live camera photo and saves it immediately against the selected bag',async()=>{
 const stop=vi.fn();
 const getUserMedia=vi.fn().mockResolvedValue({getTracks:()=>[{stop}]});
 vi.stubGlobal('navigator',{mediaDevices:{getUserMedia}});
 vi.spyOn(HTMLMediaElement.prototype,'play').mockResolvedValue();
 vi.spyOn(HTMLCanvasElement.prototype,'getContext').mockReturnValue({drawImage:vi.fn()} as any);
 vi.spyOn(HTMLCanvasElement.prototype,'toBlob').mockImplementation(callback=>callback(new Blob(['jpeg'],{type:'image/jpeg'})));
 const upload=vi.fn().mockResolvedValue({filename:'captured.jpg'}),onBusy=vi.fn();
 function Harness(){const [photos,setPhotos]=useState<string[]>([]);return <PhotoCapture donationId="original-bag" photos={photos} onChange={setPhotos} upload={upload} onBusy={onBusy}/>;}
 const view=render(<Harness/>);
 fireEvent.click(screen.getByRole('button',{name:'Take photos'}));
 await waitFor(()=>expect(getUserMedia).toHaveBeenCalled());
 const video=screen.getByLabelText('Item camera preview');
 Object.defineProperties(video,{videoWidth:{value:1280},videoHeight:{value:960}});
 fireEvent.loadedData(video);
 fireEvent.click(screen.getByRole('button',{name:'Take and save photo'}));
 await waitFor(()=>expect(upload).toHaveBeenCalledWith(expect.any(File),'original-bag'));
 await screen.findByAltText('Item photo 1');
 expect(screen.getByText('Saved to this bag')).toBeTruthy();
 expect(onBusy).toHaveBeenLastCalledWith(false);
 view.unmount();expect(stop).toHaveBeenCalled();
});

test('provides direct native device camera capture and blocks capture without a bag',()=>{
 const {container}=render(<PhotoCapture donationId="" photos={[]} onChange={vi.fn()} upload={vi.fn()} onBusy={vi.fn()}/>);
 const input=container.querySelector('input[capture="environment"]') as HTMLInputElement;
 expect(input).toBeTruthy();expect(input.disabled).toBe(true);
 expect((screen.getByRole('button',{name:'Take photos'}) as HTMLButtonElement).disabled).toBe(true);
});

test('a capture failure shows an error and does not add a photo',async()=>{
 const onChange=vi.fn(),upload=vi.fn().mockRejectedValue(new Error('Connection lost'));
 const {container}=render(<PhotoCapture donationId="bag-1" photos={[]} onChange={onChange} upload={upload} onBusy={vi.fn()}/>);
 const input=container.querySelector('input[capture="environment"]')!;
 fireEvent.change(input,{target:{files:[new File(['image'],'test.jpg',{type:'image/jpeg'})]}});
 await screen.findByText('Connection lost');
 expect(onChange).not.toHaveBeenCalled();
});

test.each(['GivingFlowAndroid','GivingFlowIOS'])('%s camera saves immediately against the original bag',async(platform)=>{
 const takePhoto=vi.fn((requestId:string)=>queueMicrotask(()=>window.dispatchEvent(new CustomEvent('givingflow:photo',{detail:{requestId,base64:btoa('test-jpeg')}}))));
 vi.stubGlobal(platform,{takePhoto,scanQr:vi.fn(),printLabels:vi.fn()});
 const upload=vi.fn().mockResolvedValue({filename:'android-capture.jpg'}),onChange=vi.fn();
 render(<PhotoCapture donationId="android-bag" photos={[]} onChange={onChange} upload={upload} onBusy={vi.fn()}/>);
 fireEvent.click(screen.getByRole('button',{name:'Take photos'}));
 await waitFor(()=>expect(upload).toHaveBeenCalledWith(expect.any(File),'android-bag'));
 expect(takePhoto).toHaveBeenCalled();
 expect(onChange).toHaveBeenCalledWith(['android-capture.jpg']);
});
