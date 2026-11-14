export const completedStatuses = ['sold','donated','disposed'];
export function matchesItemStatus(item: Record<string, unknown>, filter: string): boolean {
  const status = typeof item.status === 'string' ? item.status : '';
  if(filter==='all')return true;
  if(filter==='active')return status!==''&&!completedStatuses.includes(status);
  if(filter==='completed')return completedStatuses.includes(status);
  return status===filter;
}
export function formatAED(amountMinor: number): string {
  return `AED ${(amountMinor/100).toLocaleString('en-AE',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
}
