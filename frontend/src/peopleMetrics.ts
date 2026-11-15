type Row = Record<string, any>;
export const canContact = (donor:Row) => Boolean(donor.marketing_consent && (donor.contact_preference==='email'&&donor.email?.trim() || donor.contact_preference==='phone'&&donor.phone?.trim()));
export function peopleMetrics(donors:Row[],donations:Row[],items:Row[]) {
  const rows:(Row & {donations:number,items:number,contactable:boolean})[]=donors.map(d=>{const bags=donations.filter(b=>!b.anonymous&&b.donor_id===d.id);const ids=new Set(bags.map(b=>b.id));return {...d,donations:bags.length,items:items.filter(i=>ids.has(i.donation_id)).length,contactable:canContact(d)};});
  const anonymous=donations.filter(b=>b.anonymous||!b.donor_id).length;
  const optedIn=donations.filter(b=>!b.anonymous&&rows.some(d=>d.id===b.donor_id&&d.contactable)).length;
  const nationalities=Object.entries(rows.reduce<Record<string,number>>((acc,d)=>{const key=d.nationality?.trim()||'Not provided';acc[key]=(acc[key]||0)+1;return acc;},{})).sort((a,b)=>b[1]-a[1]);
  return {rows,anonymous,optedIn,knownNoConsent:donations.length-anonymous-optedIn,nationalities,contactable:rows.filter(d=>d.contactable).length};
}
