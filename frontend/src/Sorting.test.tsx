import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { App } from './main';

afterEach(()=>{cleanup();vi.unstubAllGlobals();});
function setup(){
 const data={staff:{name:'Test Staff',email:'staff@example.com'},database:'postgresql',donors:[{id:'donor-1',name:'Original Donor'}],customers:[],items:[] as any[],sales:[] as any[],causes:[{id:'cause-1',name:'Community Fund'}],events:[],donations:[{id:'bag-1',reference:'BAG-ORIGINAL',donor_id:'donor-1',status:'sorting',created_at:'2026-11-14T00:00:00Z',location:'Warehouse'},{id:'bag-2',reference:'BAG-SECOND',donor_id:'donor-1',status:'in_transit',created_at:'2026-11-14T01:00:00Z',location:'Van'}]};
 const fetchMock=vi.fn(async(input:any,options:any)=>{
   const url=String(input);let body:any=data;
   if(url.startsWith('/api/resolve'))body={kind:'donation',id:url.includes('WRONG')?'bag-1':'bag-2'};
   if(url==='/api/donations/bag-2/action'){expect(JSON.parse(options.body).action).toBe('receive');data.donations[1].status='sorting';body=data.donations[1];}
   return {ok:true,json:async()=>structuredClone(body)};
 });
 vi.stubGlobal('fetch',fetchMock);return {data,fetchMock};
}

test('the top sorting cards open bags and sorting defaults to clothes with the original bag locked',async()=>{
 setup();render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:/Being sorted/}));
 const picker=await screen.findByRole('dialog',{name:'Choose a donation bag'});
 expect(within(picker).getByText('BAG-ORIGINAL')).toBeTruthy();
 fireEvent.click(within(picker).getByRole('button',{name:/Open manually/}));
 fireEvent.click(within(await screen.findByRole('dialog',{name:'BAG-ORIGINAL'})).getByRole('button',{name:'Sort an item'}));
 const form=await screen.findByRole('dialog',{name:'Sort an item'});
 const bag=within(form).getByLabelText('Original donation bag *') as HTMLSelectElement;
 expect(bag.value).toBe('bag-1');expect(bag.disabled).toBe(true);
 const type=within(form).getByLabelText('Item type *') as HTMLSelectElement;
 expect(type.value).toBe('clothing');
 for(const name of ['Clothes','Books','Jewellery','Ornaments'])expect(within(type).getByRole('option',{name})).toBeTruthy();
 for(const name of ['Toys','Shoes','Hats','Other'])expect(within(type).queryByRole('option',{name})).toBeNull();
 expect(within(form).getByText(/Original Donor/)).toBeTruthy();
 expect(within(form).getByRole('button',{name:'Take photos'})).toBeTruthy();
 fireEvent.click(within(form).getByRole('button',{name:'Donate'}));
 expect(within(type).getByRole('option',{name:'Toys'})).toBeTruthy();
 fireEvent.change(type,{target:{value:'toy'}});
 fireEvent.click(within(form).getByRole('button',{name:'Re-sale'}));
 expect(type.value).toBe('clothing');
});

test('scanning the selected incoming bag receives it and selects its sorting workspace',async()=>{
 const {fetchMock}=setup();render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:/On the way/}));
 fireEvent.click(within(await screen.findByRole('dialog',{name:'Choose a donation bag'})).getByRole('button',{name:'Scan this bag'}));
 const scanner=await screen.findByRole('dialog',{name:'Scan a bag or item'});
 fireEvent.change(within(scanner).getByLabelText('Bag / item reference or QR link'),{target:{value:'BAG-SECOND'}});
 fireEvent.click(within(scanner).getByRole('button',{name:'Find record'}));
 await screen.findByText('Processing BAG-SECOND');
 expect(fetchMock.mock.calls.some(([url])=>url==='/api/donations/bag-2/action')).toBe(true);
 expect(screen.getByRole('button',{name:'Sort next item'})).toBeTruthy();
});

test('scanning the wrong bag is rejected before any processing transition',async()=>{
 const {fetchMock}=setup();render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:/On the way/}));
 fireEvent.click(within(await screen.findByRole('dialog',{name:'Choose a donation bag'})).getByRole('button',{name:'Scan this bag'}));
 const scanner=await screen.findByRole('dialog',{name:'Scan a bag or item'});
 fireEvent.change(within(scanner).getByLabelText('Bag / item reference or QR link'),{target:{value:'WRONG'}});
 fireEvent.click(within(scanner).getByRole('button',{name:'Find record'}));
 await screen.findByText(/That label is not the selected donation bag/);
 expect(fetchMock.mock.calls.some(([url])=>url==='/api/donations/bag-2/action')).toBe(false);
});

test('Android native QR scanning selects the bag and native printing uses its exact ID',async()=>{
 setup();
 const printLabels=vi.fn();
 const scanQr=vi.fn((requestId:string)=>queueMicrotask(()=>window.dispatchEvent(new CustomEvent('givingflow:qr',{detail:{requestId,value:'BAG-SECOND'}}))));
 vi.stubGlobal('GivingFlowAndroid',{scanQr,takePhoto:vi.fn(),printLabels});
 render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:/On the way/}));
 fireEvent.click(within(await screen.findByRole('dialog',{name:'Choose a donation bag'})).getByRole('button',{name:'Scan this bag'}));
 fireEvent.click(within(await screen.findByRole('dialog',{name:'Scan a bag or item'})).getByRole('button',{name:/Open camera scanner/}));
 const bag=await screen.findByRole('dialog',{name:'BAG-SECOND'});
 expect(scanQr).toHaveBeenCalled();
 fireEvent.click(within(bag).getByRole('button',{name:'Print QR label'}));
 expect(printLabels).toHaveBeenCalledWith('bag-2');
});

test('active inventory hides completed records and the view controls can show them again',async()=>{
 const {data}=setup();
 for(const [status,title] of [['available','Available shirt'],['sold','Sold shirt'],['donated','Donated shirt'],['disposed','Disposed shirt']])data.items.push({id:status,reference:'ITM-'+status,title,status,category:'Re-sale',item_type:'clothing',donation_id:'bag-1',details:{condition:'good'},location:'Shelf 1',created_at:'2026-11-14T00:00:00Z'});
 render(<App/>);
 await screen.findByRole('button',{name:/Being sorted/});
 fireEvent.click(screen.getAllByRole('button',{name:'Inventory'})[0]);
 expect(screen.getByText('Available shirt')).toBeTruthy();
 for(const title of ['Sold shirt','Donated shirt','Disposed shirt'])expect(screen.queryByText(title)).toBeNull();
 const views=screen.getByRole('group',{name:'Item visibility'});
 fireEvent.click(within(views).getByRole('button',{name:'All items'}));
 expect(screen.getByText('Sold shirt')).toBeTruthy();expect(screen.getByText('Disposed shirt')).toBeTruthy();
 fireEvent.click(within(views).getByRole('button',{name:'Sold items'}));
 expect(screen.getByText('Sold shirt')).toBeTruthy();expect(screen.queryByText('Available shirt')).toBeNull();
 fireEvent.change(screen.getByRole('combobox',{name:'Status'}),{target:{value:'completed'}});
 expect(screen.getByText('Donated shirt')).toBeTruthy();expect(screen.queryByText('Available shirt')).toBeNull();
});

test('sale entry is AED only and the submitted amount uses fils',async()=>{
 const {data,fetchMock}=setup();
 data.items.push({id:'available',version:1,reference:'ITM-AVAILABLE',title:'Available shirt',status:'available',category:'Re-sale',item_type:'clothing',donation_id:'bag-1',details:{condition:'good'},location:'Shelf 1',created_at:'2026-11-14T00:00:00Z'});
 render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:/Available shirt/}));
 fireEvent.click(within(screen.getByRole('dialog',{name:'Available shirt'})).getByRole('button',{name:'Record sale'}));
 const sale=await screen.findByRole('dialog',{name:'Record a sale'});
 expect(within(sale).queryByRole('combobox',{name:'Currency'})).toBeNull();
 fireEvent.change(within(sale).getByLabelText('Sale price (AED) *'),{target:{value:'17.25'}});
 fireEvent.click(within(sale).getByRole('button',{name:'Confirm sale'}));
 await waitFor(()=>expect(fetchMock.mock.calls.some(([url])=>url==='/api/items/available/sale')).toBe(true));
 const call=fetchMock.mock.calls.find(([url])=>url==='/api/items/available/sale')!;
 expect(JSON.parse(call[1].body)).toMatchObject({currency:'AED',amount_minor:1725});
});
