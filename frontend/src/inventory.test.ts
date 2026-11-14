import { expect, test } from 'vitest';
import { formatAED, matchesItemStatus } from './inventory';

test('active view excludes completed items but keeps service work and stock',()=>{
 for(const status of ['sold','donated','disposed'])expect(matchesItemStatus({status},'active')).toBe(false);
 for(const status of ['available','in_service','awaiting_sort'])expect(matchesItemStatus({status},'active')).toBe(true);
 expect(matchesItemStatus({status:'sold'},'all')).toBe(true);
 expect(matchesItemStatus({status:'sold'},'sold')).toBe(true);
 expect(matchesItemStatus({status:'available'},'sold')).toBe(false);
});

test('prices are explicitly displayed in AED and fils',()=>{
 expect(formatAED(1250)).toBe('AED 12.50');
 expect(formatAED(100000)).toBe('AED 1,000.00');
});
