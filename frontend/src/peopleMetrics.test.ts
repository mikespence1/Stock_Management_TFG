import { expect, test } from 'vitest';
import { peopleMetrics } from './peopleMetrics';

test('repeat donations and all original items count once, with anonymity and consent kept separate',()=>{
 const donors=[{id:'a',name:'A',nationality:'Emirati',email:'a@example.com',contact_preference:'email',marketing_consent:true},{id:'b',name:'B',nationality:'',phone:'123',contact_preference:'phone',marketing_consent:false},{id:'c',name:'C',nationality:'Emirati',contact_preference:'email',marketing_consent:true}];
 const donations=[{id:'1',donor_id:'a'},{id:'2',donor_id:'a'},{id:'3',donor_id:'b'},{id:'4',anonymous:true,donor_id:null}];
 const items=[{donation_id:'1',status:'sold'},{donation_id:'1',status:'available'},{donation_id:'2',status:'disposed'},{donation_id:'4',status:'donated'}];
 const m=peopleMetrics(donors,donations,items);
 expect(m.rows[0]).toMatchObject({donations:2,items:3,contactable:true});
 expect(m.rows[1].contactable).toBe(false);expect(m.rows[2].contactable).toBe(false);
 expect(m.contactable).toBe(1);expect(m.optedIn).toBe(2);expect(m.anonymous).toBe(1);expect(m.knownNoConsent).toBe(1);
 expect(m.nationalities).toEqual([['Emirati',2],['Not provided',1]]);
});
test('empty dashboards have zero counts',()=>{
 const m=peopleMetrics([],[],[]);expect(m.rows).toEqual([]);expect(m.contactable+m.anonymous+m.optedIn).toBe(0);
});
