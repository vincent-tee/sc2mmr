/**
 * Type definitions for MatchDetail components
 */

// Commentary types - flexible to handle different response formats
export interface MvpAnalysis {
  player_name: string;
  team: number;
  impact_score: number | null;
  reasoning: string;
}

export interface SHAPImpact {
  feature: string;
  impact: number;
  magnitude: number;
}

export interface MatchCommentary {
  error?: string;
  commentary?: string; // Simple format
  overview?: string;
  key_moments?: string[];
  mvp_analysis?: MvpAnalysis;
  player_performances?: Record<string, string>;
  team_analysis?: {
    team_1: string;
    team_2: string;
  };
  match_summary?: string;
  shap_impacts?: SHAPImpact[];
}

// Player metrics response type - flexible to handle API response
export interface PlayerMetricsResponse {
  match_id?: number;
  player_name: string;
  team_number: number;
  race: string;
  won: boolean;
  minerals_collected: number;
  vespene_collected: number;
  total_resources_collected: number;
  resources_spent: number;
  spending_efficiency: number;
  workers_created: number;
  units_trained: number;
  units_lost: number;
  units_killed: number;
  army_value_built: number;
  army_value_killed: number;
  army_value_lost: number;
  damage_dealt: number;
  damage_taken: number;
  damage_ratio: number;
  first_expansion_timing: number | null;
  bases_created: number;
  apm: number;
  economic_score: number;
  combat_score: number;
  efficiency_score: number;
  overall_impact: number;
  team_fight_participation: number;
  team_fight_damage: number;
  team_fight_damage_ratio: number;
  first_damage_timing: number | null;
  early_game_damage: number;
  mid_game_damage: number;
  late_game_damage: number;
  player_archetype: string | null;
  aggression_score: number;
  damage_timeline: Record<string, number> | null;
}

// Damage timeline type
export interface DamageDistribution {
  early_game?: number;
  mid_game?: number;
  late_game?: number;
  early?: number;
  mid?: number;
  late?: number;
}

export interface TimelineData {
  damage_distribution?: DamageDistribution;
  damage_timeline?: Record<string, number>;
  [key: string]: unknown;
}

export interface PlayerTimeline {
  player_id: number;
  player_name: string;
  team_number: number;
  timeline: TimelineData;
}
