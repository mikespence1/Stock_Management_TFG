/** Keep chart widths finite and inside their track, including empty data sets. */
export function boundedPercentage(value: number, total: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(total) || total <= 0) return 0;
  return Math.max(0, Math.min(100, value / total * 100));
}
