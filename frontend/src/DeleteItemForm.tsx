import { useState } from 'react';
import { Field, Modal } from './FormUI';

type Item = {id:string;reference:string;title:string;version:number};
type DeleteValues = {password:string;reference:string;version:number;reason:string};

export default function DeleteItemForm({item,hasSale,busy,close,save}: {
  item:Item;hasSale:boolean;busy:boolean;close:()=>void;save:(values:DeleteValues)=>Promise<unknown>;
}) {
  const [password,setPassword]=useState('');
  const [reference,setReference]=useState('');
  const [reason,setReason]=useState('');
  const [confirmed,setConfirmed]=useState(false);
  const ready=password.length>0&&reference.trim()===item.reference&&reason.trim().length>0&&confirmed;
  return <Modal title="Delete inventory item" subtitle="Admin approval required for every deletion." close={()=>{if(!busy)close();}}>
    <form onSubmit={async event=>{
      event.preventDefault();
      if(!ready||busy)return;
      const values={password,reference:reference.trim(),version:item.version,reason:reason.trim()};
      setPassword('');
      await save(values);
    }}>
      <div className="form-content">
        <p className="delete-warning">Permanently delete <b>{item.title}</b> ({item.reference}) and its attached photos. {hasSale?'Its recorded sale will also be removed and sales totals will change. ':''}The donation bag and donor will remain. An audit entry will be kept. This cannot be undone in the app.</p>
        <Field label="Reason for deletion *"><input required maxLength={300} value={reason} onChange={event=>setReason(event.target.value)} placeholder="For example, a dummy record or created in error"/></Field>
        <Field label={`Type ${item.reference} to confirm *`}><input required autoComplete="off" spellCheck={false} value={reference} onChange={event=>setReference(event.target.value)}/></Field>
        <Field label="Admin deletion password *"><input type="password" required maxLength={256} autoComplete="off" value={password} onChange={event=>setPassword(event.target.value)}/></Field>
        <label className="delete-acknowledgement"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/><span>I understand that this permanently deletes this inventory record{hasSale?' and its recorded sale':''}.</span></label>
      </div>
      <div className="form-footer"><button type="button" className="button secondary" disabled={busy} onClick={close}>Cancel</button><button className="button danger" disabled={!ready||busy}>{busy?'Deleting…':'Permanently delete item'}</button></div>
    </form>
  </Modal>;
}
