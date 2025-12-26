/**
 * Helper functions for MatchDetail components
 */
import type { DamageDistribution, TimelineData } from './types';

// Helper function to transform damage distribution for chart component
export const transformDamageDistribution = (
  dist: DamageDistribution
): { early: number; mid: number; late: number } => ({
  early: dist.early ?? dist.early_game ?? 0,
  mid: dist.mid ?? dist.mid_game ?? 0,
  late: dist.late ?? dist.late_game ?? 0,
});

// Helper function to transform timeline data for chart component
export const transformTimelineData = (
  data: TimelineData
): {
  damage_timeline: string | null;
  total_damage?: number;
  first_damage_time?: string;
  peak_damage_time?: string;
  peak_damage_amount?: number;
} => ({
  damage_timeline: data.damage_timeline
    ? JSON.stringify({ damage_by_second: data.damage_timeline })
    : null,
  total_damage:
    typeof data.total_damage === 'number' ? data.total_damage : undefined,
  first_damage_time:
    typeof data.first_damage_time === 'string'
      ? data.first_damage_time
      : undefined,
  peak_damage_time:
    typeof data.peak_damage_time === 'string'
      ? data.peak_damage_time
      : undefined,
  peak_damage_amount:
    typeof data.peak_damage_amount === 'number'
      ? data.peak_damage_amount
      : undefined,
});
