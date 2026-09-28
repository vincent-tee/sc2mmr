import type { ResultSource } from '../types/api';

export const isRatedResult = (source: ResultSource | null | undefined): boolean =>
  source !== 'unknown' && source !== 'not_rateable';
