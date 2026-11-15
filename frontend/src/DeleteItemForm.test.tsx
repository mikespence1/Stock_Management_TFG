import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import DeleteItemForm from './DeleteItemForm';

afterEach(cleanup);
const item={id:'item-1',reference:'ITM-EXAMPLE',title:'Dummy item',version:3};

test('deletion needs the exact reference, password, reason and explicit confirmation', async()=>{
  const save=vi.fn().mockResolvedValue(true);
  render(<DeleteItemForm item={item} hasSale busy={false} close={()=>{}} save={save}/>);
  const submit=screen.getByRole('button',{name:'Permanently delete item'}) as HTMLButtonElement;
  expect(submit.disabled).toBe(true);
  expect(screen.getByText(/sales totals will change/)).toBeTruthy();
  const password=screen.getByLabelText('Admin deletion password *') as HTMLInputElement;
  expect(password.type).toBe('password');
  fireEvent.change(password,{target:{value:'example-test-secret'}});
  fireEvent.change(screen.getByLabelText('Reason for deletion *'),{target:{value:'Dummy record'}});
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.change(screen.getByLabelText('Type ITM-EXAMPLE to confirm *'),{target:{value:'ITM-WRONG'}});
  expect(submit.disabled).toBe(true);
  fireEvent.change(screen.getByLabelText('Type ITM-EXAMPLE to confirm *'),{target:{value:'ITM-EXAMPLE'}});
  expect(submit.disabled).toBe(false);
  fireEvent.click(submit);
  expect(save).toHaveBeenCalledExactlyOnceWith({password:'example-test-secret',reference:'ITM-EXAMPLE',version:3,reason:'Dummy record'});
  expect(password.value).toBe('');
  expect(submit.disabled).toBe(true);
});

test('cancel does not submit a deletion and pending deletion cannot be dismissed',()=>{
  const close=vi.fn(),save=vi.fn();
  const {rerender}=render(<DeleteItemForm item={item} hasSale={false} busy={false} close={close} save={save}/>);
  fireEvent.click(screen.getByRole('button',{name:'Cancel'}));
  expect(close).toHaveBeenCalledOnce();
  expect(save).not.toHaveBeenCalled();
  rerender(<DeleteItemForm item={item} hasSale={false} busy close={close} save={save}/>);
  fireEvent.click(screen.getByRole('button',{name:'Close dialog'}));
  expect(close).toHaveBeenCalledOnce();
  expect((screen.getByRole('button',{name:'Deleting…'}) as HTMLButtonElement).disabled).toBe(true);
});
