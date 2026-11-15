import { expect, test } from 'vitest';
import { boundedPercentage } from './progress';

test('category bars show the actual share of inventory', () => {
  expect(boundedPercentage(26, 67)).toBeCloseTo(38.80597);
  expect(boundedPercentage(3, 4)).toBe(75);
});

test.each([
  [0, 0, 0], [3, 0, 0], [3, -1, 0], [-3, 10, 0],
  [12, 10, 100], [10, 10, 100], [Number.NaN, 10, 0],
  [Number.POSITIVE_INFINITY, 10, 0], [10, Number.NaN, 0],
  [10, Number.POSITIVE_INFINITY, 0], [Number.MAX_VALUE, Number.MIN_VALUE, 100],
])('bar width for %s of %s is safely bounded at %s', (value, total, expected) => {
  expect(boundedPercentage(value, total)).toBe(expected);
});
