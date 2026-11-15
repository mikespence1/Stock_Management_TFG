import { useState } from 'react';
import { Field, Modal } from './FormUI';
type Row = Record<string, any>;

export function DonorFields({donor,causes}: {donor?:Row,causes:Row[]}) {
  const [contact,setContact]=useState(donor?.contact_preference||'none');
  const [consent,setConsent]=useState(Boolean(donor?.marketing_consent));
  return <>
    <div className="form-grid">
      <Field label="Donor name *"><input name="name" required maxLength={120} defaultValue={donor?.name||''} autoComplete="name"/></Field>
      <Field label="Nationality (optional)"><input name="nationality" maxLength={100} defaultValue={donor?.nationality||''}/></Field>
      <Field label={`Email address ${contact==='email'?'*':'(optional)'}`}><input type="email" name="email" required={contact==='email'} defaultValue={donor?.email||''}/></Field>
      <Field label={`Phone number ${contact==='phone'?'*':'(optional)'}`}><input type="tel" name="phone" required={contact==='phone'} maxLength={40} defaultValue={donor?.phone||''}/></Field>
      <Field label="Contact preference"><select name="contact_preference" value={contact} onChange={e=>{setContact(e.target.value);if(e.target.value==='none')setConsent(false);}}><option value="none">No contact</option><option value="email">Email</option><option value="phone">Phone</option></select></Field>
    </div>
    <label className="consent-card"><input type="checkbox" name="marketing_consent" checked={consent} disabled={contact==='none'} onChange={e=>setConsent(e.target.checked)}/><span><b>I agree to receive marketing and updates from Thrift for Good</b><small>Including the causes my donations support and rewards for my support, using my chosen contact method. This is optional and I can withdraw consent at any time. Choose email or phone above to opt in.</small></span></label>
    <Field label="Favoured causes (optional)"><div className="cause-choices">{causes.map(c=><label key={c.id}><input type="checkbox" name="cause_ids" value={c.id} defaultChecked={donor?.cause_ids?.includes(c.id)}/>{c.name}</label>)}</div></Field>
  </>;
}
function donorValues(form:FormData) {
  return {name:form.get('name'),email:form.get('email')||null,phone:form.get('phone')||'',nationality:form.get('nationality')||'',contact_preference:form.get('contact_preference'),marketing_consent:form.get('marketing_consent')==='on',cause_ids:form.getAll('cause_ids')};
}
export function DonationIntake({data,busy,close,save}:Row) {
  const [anonymous,setAnonymous]=useState(false),[donorId,setDonorId]=useState('');
  const donor=data.donors.find((d:Row)=>d.id===donorId);
  return <Modal title="Receive a donation" subtitle="Record bags only once they have arrived. They are ready to sort immediately." close={close} wide><form onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);save({anonymous,location:f.get('location'),notes:f.get('notes'),donor_id:!anonymous&&donorId?donorId:null,donor_version:!anonymous&&donor?donor.version:null,donor:anonymous?null:donorValues(f)});}}><div className="form-content">
    <label className="toggle-card"><div><b>Anonymous donation</b><small>No identity or contact permission will be stored for this donation.</small></div><input type="checkbox" role="switch" checked={anonymous} onChange={e=>setAnonymous(e.target.checked)}/></label>
    {!anonymous&&<><Field label="Donor"><select value={donorId} onChange={e=>setDonorId(e.target.value)}><option value="">New donor</option>{data.donors.map((d:Row)=><option value={d.id} key={d.id}>{d.name}{d.email?` · ${d.email}`:''}</option>)}</select></Field>{donor&&<p className="muted">Review this existing donor’s details and consent. Changes apply to their donor record.</p>}<DonorFields key={donorId} donor={donor} causes={data.causes}/></>}
    <div className="form-grid"><Field label="Received at *"><input name="location" defaultValue="Warehouse" required maxLength={120}/></Field><Field label="Bag note (optional)"><input name="notes" maxLength={1000}/></Field></div>
  </div><FormFooter close={close} busy={busy} label="Save & create bag label"/></form></Modal>;
}
export function DonorEditor({donor,causes,busy,close,save}:Row) {
  return <Modal title="Edit donor" subtitle="Updates apply to every donation linked to this donor." close={close} wide><form onSubmit={e=>{e.preventDefault();save(donorValues(new FormData(e.currentTarget)));}}><div className="form-content"><DonorFields donor={donor} causes={causes}/></div><FormFooter close={close} busy={busy}/></form></Modal>;
}
export function FormFooter({close,busy,label='Save changes'}:Row) {
  return <div className="form-footer"><button type="button" className="button secondary" onClick={close} disabled={busy}>Cancel</button><button className="button primary" disabled={busy}>{busy?'Saving…':label}</button></div>;
}
export function SaleEditor({sale,customers,causes,busy,close,save}:Row) {
  return <Modal title="Edit sale" subtitle="The original item, sale date and sold status are retained." close={close}><form onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);save({amount_minor:Math.round(Number(f.get('amount'))*100),customer_id:f.get('customer_id')||null,cause_id:f.get('cause_id')||null});}}><div className="form-content"><Field label="Sale price (AED) *"><input name="amount" type="number" min="0.01" max="1000000" step="0.01" required defaultValue={(sale.amount_minor/100).toFixed(2)}/></Field><Field label="Customer"><select name="customer_id" defaultValue={sale.customer_id||''}><option value="">Anonymous customer</option>{customers.map((c:Row)=><option key={c.id} value={c.id}>{c.name}</option>)}</select></Field><Field label="Supporting cause"><select name="cause_id" defaultValue={sale.cause_id||''}><option value="">Unassigned</option>{causes.map((c:Row)=><option key={c.id} value={c.id}>{c.name}</option>)}</select></Field></div><FormFooter close={close} busy={busy}/></form></Modal>;
}
