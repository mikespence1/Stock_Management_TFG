import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { DonationIntake, DonorEditor } from './RecordForms';
afterEach(cleanup);
const data={causes:[],donors:[{id:'donor',version:3,name:'Repeat Donor',contact_preference:'email',email:'repeat@example.com',marketing_consent:false,cause_ids:[]}]};
test('consent is optional and unchecked, requires a contact channel, and is absent for anonymous donations',()=>{
 const save=vi.fn();render(<DonationIntake data={data} busy={false} close={()=>{}} save={save}/>);
 const checkbox=screen.getByRole('checkbox',{name:/I agree to receive marketing/}) as HTMLInputElement;
 expect(checkbox.checked).toBe(false);expect(checkbox.disabled).toBe(true);
 fireEvent.change(screen.getByLabelText('Contact preference'),{target:{value:'email'}});
 expect(checkbox.disabled).toBe(false);fireEvent.click(checkbox);expect(checkbox.checked).toBe(true);
 fireEvent.change(screen.getByLabelText('Contact preference'),{target:{value:'none'}});expect(checkbox.checked).toBe(false);
 fireEvent.click(screen.getByRole('switch'));
 expect(screen.queryByRole('checkbox',{name:/I agree to receive marketing/})).toBeNull();
 fireEvent.submit(screen.getByRole('button',{name:'Save & create bag label'}).closest('form')!);
 expect(save).toHaveBeenCalledWith(expect.objectContaining({anonymous:true,donor:null,donor_id:null}));
});
test('repeat donors can give consent at intake without creating a second identity',()=>{
 const save=vi.fn();render(<DonationIntake data={data} busy={false} close={()=>{}} save={save}/>);
 fireEvent.change(screen.getByLabelText('Donor'),{target:{value:'donor'}});
 expect((screen.getByLabelText('Donor name *') as HTMLInputElement).value).toBe('Repeat Donor');
 fireEvent.click(screen.getByRole('checkbox',{name:/I agree to receive marketing/}));
 fireEvent.submit(screen.getByRole('button',{name:'Save & create bag label'}).closest('form')!);
 expect(save).toHaveBeenCalledWith(expect.objectContaining({donor_id:'donor',donor_version:3,donor:expect.objectContaining({marketing_consent:true,email:'repeat@example.com'})}));
});
test('donor editing supports withdrawing previously recorded consent',()=>{
 const save=vi.fn();render(<DonorEditor donor={{...data.donors[0],marketing_consent:true}} causes={[]} busy={false} close={()=>{}} save={save}/>);
 fireEvent.click(screen.getByRole('checkbox',{name:/I agree to receive marketing/}));
 fireEvent.submit(screen.getByRole('button',{name:'Save changes'}).closest('form')!);
 expect(save).toHaveBeenCalledWith(expect.objectContaining({marketing_consent:false}));
});
