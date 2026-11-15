import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { App } from './main';

afterEach(()=>{cleanup();vi.unstubAllGlobals();});

test.each(['web','GivingFlowAndroid','GivingFlowIOS'])('%s inventory deletion submits admin approval and removes the selected record',async(platform)=>{
 const {data,fetchMock}=setup();
 const enabledData=data as typeof data & {admin_delete_enabled:boolean};
 enabledData.admin_delete_enabled=true;
 const item={id:'dummy-item',reference:'ITM-DUMMY',title:'Dummy record',version:2,status:'available',category:'Re-sale',item_type:'clothing',donation_id:'bag-1',details:{condition:'good'},location:'Shelf 1',created_at:'2026-11-14T00:00:00Z'};
 data.items.push(item);
 if(platform!=='web')vi.stubGlobal(platform,{takePhoto:vi.fn(),scanQr:vi.fn(),printLabels:vi.fn()});
 fetchMock.mockImplementation(async(input:any,options:any)=>{
   if(options?.method==='DELETE'){
    expect(String(input)).toBe('/api/items/dummy-item');
    expect(JSON.parse(options.body)).toEqual({password:'test-secret',reference:'ITM-DUMMY',version:2,reason:'Test record'});
    data.items=[];
    return {ok:true,json:async()=>({deleted:true,id:item.id,reference:item.reference})};
   }
   return {ok:true,json:async()=>structuredClone(data)};
 });
 render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:/Dummy record/}));
 fireEvent.click(screen.getByRole('button',{name:'Delete item (admin)'}));
 const form=screen.getByRole('dialog',{name:'Delete inventory item'});
 fireEvent.change(within(form).getByLabelText('Reason for deletion *'),{target:{value:'Test record'}});
 fireEvent.change(within(form).getByLabelText('Type ITM-DUMMY to confirm *'),{target:{value:'ITM-DUMMY'}});
 fireEvent.change(within(form).getByLabelText('Admin deletion password *'),{target:{value:'test-secret'}});
 fireEvent.click(within(form).getByRole('checkbox'));
 fireEvent.click(within(form).getByRole('button',{name:'Permanently delete item'}));
 await screen.findByRole('status');
 expect(screen.queryByRole('dialog',{name:'Delete inventory item'})).toBeNull();
 expect(screen.queryByText('Dummy record')).toBeNull();
 expect(data.donations).toHaveLength(2);
});
function setup(){
 const data={staff:{name:'Test Staff',email:'staff@example.com'},database:'postgresql',donors:[{id:'donor-1',version:1,name:'Original Donor',contact_preference:'none',marketing_consent:false,cause_ids:[]}],customers:[],items:[] as any[],sales:[] as any[],causes:[{id:'cause-1',name:'Community Fund'}],events:[],donations:[{id:'bag-1',reference:'BAG-ORIGINAL',donor_id:'donor-1',status:'sorting',created_at:'2026-11-14T00:00:00Z',location:'Warehouse'},{id:'bag-2',reference:'BAG-SECOND',donor_id:'donor-1',status:'sorting',created_at:'2026-11-14T01:00:00Z',location:'Warehouse'}]};
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
 fireEvent.click(within(picker).getAllByRole('button',{name:/Open manually/})[0]);
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

test('arrived bags are ready for sorting and scanning selects the workspace without a transit step',async()=>{
 const {fetchMock}=setup();render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:/Being sorted/}));
 expect(screen.queryByRole('button',{name:/On the way/})).toBeNull();
 fireEvent.click(within(await screen.findByRole('dialog',{name:'Choose a donation bag'})).getAllByRole('button',{name:'Scan this bag'})[1]);
 const scanner=await screen.findByRole('dialog',{name:'Scan a bag or item'});
 fireEvent.change(within(scanner).getByLabelText('Bag / item reference or QR link'),{target:{value:'BAG-SECOND'}});
 fireEvent.click(within(scanner).getByRole('button',{name:'Find record'}));
 await screen.findByText('Processing BAG-SECOND');
 expect(fetchMock.mock.calls.some(([url])=>url==='/api/donations/bag-2/action')).toBe(false);
 expect(screen.getByRole('button',{name:'Sort next item'})).toBeTruthy();
});

test('scanning the wrong bag is rejected before any processing transition',async()=>{
 const {fetchMock}=setup();render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:/Being sorted/}));
 fireEvent.click(within(await screen.findByRole('dialog',{name:'Choose a donation bag'})).getAllByRole('button',{name:'Scan this bag'})[1]);
 const scanner=await screen.findByRole('dialog',{name:'Scan a bag or item'});
 fireEvent.change(within(scanner).getByLabelText('Bag / item reference or QR link'),{target:{value:'WRONG'}});
 fireEvent.click(within(scanner).getByRole('button',{name:'Find record'}));
 await screen.findByText(/That label is not the selected donation bag/);
 expect(fetchMock.mock.calls.some(([url])=>url==='/api/donations/bag-2/action')).toBe(false);
});

test.each(['GivingFlowAndroid','GivingFlowIOS'])('%s QR scanning selects the bag and native printing uses its exact ID',async(platform)=>{
 setup();
 const printLabels=vi.fn();
 const scanQr=vi.fn((requestId:string)=>queueMicrotask(()=>window.dispatchEvent(new CustomEvent('givingflow:qr',{detail:{requestId,value:'BAG-SECOND'}}))));
 vi.stubGlobal(platform,{scanQr,takePhoto:vi.fn(),printLabels});
 render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:/Being sorted/}));
 fireEvent.click(within(await screen.findByRole('dialog',{name:'Choose a donation bag'})).getAllByRole('button',{name:'Scan this bag'})[1]);
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
 data.items.push({id:'available',version:1,reference:'ITM-AVAILABLE',title:'Available shirt',status:'available',category:'Re-sale',item_type:'clothing',donation_id:'bag-1',details:{condition:'good',photos:['1.jpg','2.jpg','3.jpg']},location:'Shelf 1',created_at:'2026-11-14T00:00:00Z'});
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

test.each(['GivingFlowAndroid','GivingFlowIOS'])('%s can correct an existing item and replace a photo while retaining its original bag',async(platform)=>{
 const {data,fetchMock}=setup();
 vi.stubGlobal(platform,{scanQr:vi.fn(),takePhoto:(requestId:string)=>queueMicrotask(()=>window.dispatchEvent(new CustomEvent('givingflow:photo',{detail:{requestId,base64:btoa('replacement')}}))),printLabels:vi.fn()});
 data.items.push({id:'existing',version:4,reference:'ITM-EXISTING',title:'Book typo',status:'available',category:'Re-sale',item_type:'book',donation_id:'bag-1',cause_id:'cause-1',details:{author:'Writer',condition:'good',photos:['a.jpg','b.jpg','c.jpg']},location:'Bookshelf',created_at:'2026-11-14T00:00:00Z'});
 fetchMock.mockImplementation(async(input:any,options:any)=>{
   const url=String(input);
   if(url==='/api/uploads'){expect(options.body.get('donation_id')).toBe('bag-1');return {ok:true,json:async()=>({filename:'replacement.jpg'})};}
   if(options?.method==='PUT')return {ok:true,json:async()=>data.items[0]};
   return {ok:true,json:async()=>structuredClone(data)};
 });
 render(<App/>);fireEvent.click(await screen.findByRole('button',{name:/Book typo/}));
 fireEvent.click(within(screen.getByRole('dialog',{name:'Book typo'})).getByRole('button',{name:'Edit item'}));
 const editor=await screen.findByRole('dialog',{name:'Edit item'});
 expect((within(editor).getByLabelText('Storage location *') as HTMLInputElement).value).toBe('Bookshelf');
 expect((within(editor).getByLabelText('Item type *') as HTMLSelectElement).value).toBe('book');
 fireEvent.change(within(editor).getByLabelText('Book title *'),{target:{value:'Correct book title'}});
 fireEvent.click(within(editor).getByRole('button',{name:'Remove photo 1'}));
 fireEvent.submit(within(editor).getByRole('button',{name:'Save changes'}).closest('form')!);
 expect(within(editor).getByText('Take exactly three photos before saving.')).toBeTruthy();
 expect(fetchMock.mock.calls.some(([,opts])=>opts?.method==='PUT')).toBe(false);
 fireEvent.click(within(editor).getByRole('button',{name:'Take photos'}));
 await within(editor).findByAltText('Item photo 3');
 fireEvent.submit(within(editor).getByRole('button',{name:'Save changes'}).closest('form')!);
 await waitFor(()=>expect(fetchMock.mock.calls.some(([url])=>url==='/api/items/existing?version=4')).toBe(true));
 const call=fetchMock.mock.calls.find(([url])=>url==='/api/items/existing?version=4')!;
 expect(call[1].method).toBe('PUT');
 expect(JSON.parse(call[1].body)).toMatchObject({title:'Correct book title',donation_id:'bag-1',category:'Re-sale',photos:['b.jpg','c.jpg','replacement.jpg'],location:'Bookshelf'});
});

test('People opens the interactive impact dashboard and a donor record',async()=>{
 setup();render(<App/>);await screen.findByRole('button',{name:/Being sorted/});
 fireEvent.click(screen.getAllByRole('button',{name:'People'})[0]);
 expect(screen.getByRole('region',{name:'Donor impact dashboard'})).toBeTruthy();
 expect(screen.getByRole('link',{name:'Export People to Excel'}).getAttribute('href')).toBe('/api/people/export.xlsx');
 fireEvent.click(screen.getByRole('button',{name:'Customers'}));
 expect(screen.getByRole('link',{name:'Export People to Excel'}).getAttribute('download')).not.toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Impact dashboard'}));
 expect(screen.getByText('Donation contact permissions')).toBeTruthy();
 expect(screen.getByRole('combobox',{name:'Rank donors by'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Original Donor'}));
 fireEvent.click(within(screen.getByRole('dialog',{name:'Original Donor'})).getByRole('button',{name:'Edit donor'}));
 expect(await screen.findByRole('dialog',{name:'Edit donor'})).toBeTruthy();
});

test.each(['Donate','Mend','Clean','Dispose'])('%s saves without photos while keeping optional capture available',async(category)=>{
 const {fetchMock}=setup();render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:/Being sorted/}));
 fireEvent.click(within(await screen.findByRole('dialog',{name:'Choose a donation bag'})).getAllByRole('button',{name:/Open manually/})[0]);
 fireEvent.click(within(await screen.findByRole('dialog',{name:'BAG-ORIGINAL'})).getByRole('button',{name:'Sort an item'}));
 const form=await screen.findByRole('dialog',{name:'Sort an item'});
 fireEvent.click(within(form).getByRole('button',{name:category}));
 expect(within(form).getByText('Photos (optional, up to three)')).toBeTruthy();
 expect(within(form).getByRole('button',{name:'Take photos'})).toBeTruthy();
 fireEvent.submit(within(form).getByRole('button',{name:'Save item & create label'}).closest('form')!);
 await waitFor(()=>expect(fetchMock.mock.calls.some(([url])=>url==='/api/items')).toBe(true));
 const call=fetchMock.mock.calls.find(([url])=>url==='/api/items')!;
 expect(JSON.parse(call[1].body)).toMatchObject({category,photos:[]});
});


test.each([{categories:[] as string[]}, {categories:['Re-sale']}, {categories:['Re-sale','Re-sale','Re-sale','Donate']}])('overview bars handle empty and dominant categories: $categories',async({categories})=>{
 const {data}=setup();
 categories.forEach((category,index)=>data.items.push({id:`item-${index}`,reference:`ITM-${index}`,title:`Test item ${index}`,status:'available',category,item_type:'clothing',donation_id:'bag-1',details:{condition:'good'},location:'Shelf 1',created_at:'2026-11-14T00:00:00Z'}));
 render(<App/>);
 await screen.findByRole('button',{name:/Being sorted/});
 fireEvent.click(screen.getAllByRole('button',{name:'Overview'})[0]);
 for(const meter of screen.getAllByRole('meter')){
  const label=meter.getAttribute('aria-label')!.replace(' share of items','');
  const count=categories.filter(category=>category===label).length;
  const expected=categories.length?count/categories.length*100:0;
  expect(Number(meter.getAttribute('aria-valuenow'))).toBe(expected);
  expect((meter.firstElementChild as HTMLElement).style.width).toBe(`${expected}%`);
 }
});
