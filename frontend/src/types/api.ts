/**
 * API Type Definitions for SC2 MMR Tracker
 *
 * These types match the backend Pydantic models and ensure
 * type safety across the frontend application.
 */

// =============================================================================
// Player Types
// =============================================================================

export interface Player {
  id: number;
  name: string;
  mu: number;
  sigma: number;
  mmr: number;  // Display MMR — the rating of record (1000 + 100*mu - 200*sigma)
  unified_mmr: number | null;  // Legacy rating, queued for retirement (Phase 6); do not use for display/sort
  hybrid_mmr: number | null;
  avg_pim: number | null;
  recency_weighted_mmr: number | null;
  win_rate: number;
  total_games: number;
  wins: number;
  losses: number;
  terran_games: number;
  protoss_games: number;
  zerg_games: number;
  random_games: number;
  favorite_race: string;
  is_core_player: boolean;
  is_ai: boolean;
  avg_economic_score: number;
  avg_combat_score: number;
  avg_efficiency_score: number;
  avg_overall_impact: number;
  avg_first_damage_timing: number | null;
  primary_archetype: string | null;
  avg_aggression_score: number;
  created_at: string;
  last_played: string | null;
  recent_form: number | null;  // Win rate from last 5 games (0.0-1.0)
}

export interface PlayerCreate {
  name: string;
}

export interface PlayerRanking {
  id: number;
  name: string;
  mmr: number;
  recency_weighted_mmr: number | null;
  win_rate: number;
  total_games: number;
  wins: number;
  losses: number;
  favorite_race: string;
  rank: number;
}

export interface PlayerDetail extends Player {
  recent_matches: RecentMatch[];
}

export interface RecentMatch {
  match_id: number;
  played_at: string;
  game_mode: string;
  map_name: string;
  race: string;
  won: boolean;
  team_number: number;
  mmr_before: number;
  mmr_after: number;
  mmr_change: number;
}

// =============================================================================
// Match Types
// =============================================================================

export interface Match {
  id: number;
  played_at: string;
  game_mode: string;
  map_name: string;
  duration_seconds: number;
  replay_hash: string | null;
  predicted_team1_win_prob: number | null;
  predicted_team2_win_prob: number | null;
}

// Enhanced match types for match history with player summaries
export interface MatchPlayerSummary {
  player_id: number;
  player_name: string;
  team_number: number;
  race: string;
  won: boolean;
  mmr_change: number;
  damage_dealt: number | null;
  damage_ratio: number | null;
  impact_score: number | null;
  units_killed: number | null;
}

export interface MatchWithPlayers {
  id: number;
  played_at: string;
  game_mode: string;
  map_name: string;
  duration_seconds: number;
  replay_hash: string | null;
  predicted_team1_win_prob: number | null;
  predicted_team2_win_prob: number | null;
  winner_team: number;
  players: MatchPlayerSummary[];
  mvp_player_id: number | null;
  mvp_player_name: string | null;
  total_damage: number | null;
}

export interface MatchListWithPlayersResponse {
  matches: MatchWithPlayers[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface MatchListResponse {
  matches: Match[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface MatchPlayer {
  player_id: number;
  player_name: string;
  team_number: number;
  race: string;
  won: boolean;
  mmr_before: number;
  mmr_after: number;
  mmr_change: number;
  /** Computed MMR property for display (uses mmr_before) */
  mmr?: number;
}

export interface MatchDetail {
  match: Match;
  players: MatchPlayer[];
}

export interface MatchPlayerMetrics {
  player_name: string;
  team_number: number;
  race: string;
  won: boolean;
  // Economic metrics
  minerals_collected: number;
  vespene_collected: number;
  total_resources_collected: number;
  resources_spent: number;
  spending_efficiency: number;
  workers_created: number;
  // Army metrics
  units_trained: number;
  units_lost: number;
  units_killed: number;
  army_value_built: number;
  army_value_killed: number;
  army_value_lost: number;
  // Combat metrics
  damage_dealt: number;
  damage_taken: number;
  damage_ratio: number;
  // Timing metrics
  first_expansion_timing: number | null;
  bases_created: number;
  // Mechanics
  apm: number;
  // Impact scores
  economic_score: number;
  combat_score: number;
  efficiency_score: number;
  overall_impact: number;
  // Team game metrics
  team_fight_participation: number;
  team_fight_damage: number;
  team_fight_damage_ratio: number;
  // Timing analysis
  first_damage_timing: number | null;
  early_game_damage: number;
  mid_game_damage: number;
  late_game_damage: number;
  player_archetype: string | null;
  aggression_score: number;
  // Damage timeline (sparse - second: damage)
  damage_timeline: Record<string, number> | null;
}

// =============================================================================
// Team Balance Types
// =============================================================================

export interface TeamInfo {
  players: TeamPlayer[];
  avg_mmr: number;
  avg_impact?: number;
}

export interface TeamPlayer {
  id: number;
  name: string;
  mmr: number;
  unified_mmr: number | null;
  recency_weighted_mmr: number | null;
  win_rate: number;
  total_games: number;
  favorite_race: string;
  is_core_player: boolean;
  is_ai: boolean;
  avg_overall_impact?: number;
}

export interface TeamSuggestion {
  team_1: TeamInfo;
  team_2: TeamInfo;
  win_probability_team_1: number;
  win_probability_team_2: number;
  fairness_rating: string;
  mmr_difference: number;
  match_quality: number;
  impact_balance_score?: number;
  impact_difference?: number;
  total_synergy?: number;
  tactical_forecast?: any;
}

export interface TeamBalanceRequest {
  player_ids: number[];
  num_suggestions?: number;
}

export interface TeamBalanceWithImpactRequest {
  player_ids: number[];
  num_suggestions?: number;
  impact_weight?: number;
}

// =============================================================================
// Impact Types
// =============================================================================

export interface PlayerImpact {
  id: number;
  name: string;
  total_games: number;
  avg_overall_impact: number;
  avg_economic_score: number;
  avg_combat_score: number;
  avg_efficiency_score: number;
  primary_archetype: string | null;
  avg_aggression_score: number;
}

export interface PlayerSynergy {
  player1_id: number;
  player1_name: string;
  player2_id: number;
  player2_name: string;
  games_together: number;
  wins_together: number;
  losses_together: number;
  win_rate_together: number;
  synergy_score: number;
  avg_combined_impact: number;
}

// =============================================================================
// Replay Upload Types
// =============================================================================

export interface ReplayUploadResponse {
  message: string;
  match_id: number;
  players: UploadedMatchPlayer[];
  game_mode: string;
  map_name: string;
  duration_seconds: number;
  played_at: string;
  predicted_win_probability?: {
    team_1: number;
    team_2: number;
  };
}

export interface UploadedMatchPlayer {
  name: string;
  team: number;
  race: string;
  won: boolean;
  mmr_before: number;
  mmr_after: number;
  mmr_change: number;
}

// =============================================================================
// API Error Types
// =============================================================================

export interface ApiError {
  detail: string;
  code?: string;
}

// =============================================================================
// Lineup Prediction Types
// =============================================================================

export interface LineupPrediction {
  team_1: TeamInfo;
  team_2: TeamInfo;
  win_probability_team_1: number;
  win_probability_team_2: number;
  fairness_rating: string;
  mmr_difference: number;
}

// =============================================================================
// Match Prediction Types (Enhanced)
// =============================================================================

export interface PredictionPlayerInfo {
  id: number;
  name: string;
  mmr: number;
  mu: number;
  sigma: number;
}

export interface SynergyInfo {
  player1_name: string;
  player2_name: string;
  games_together: number;
  win_rate: number;
  synergy_score: number;
}

export type TeamChemistry = 'Strong' | 'Average' | 'Weak' | 'Unknown';
export type PredictionConfidence = 'High' | 'Medium' | 'Low';

export interface TeamPredictionInfo {
  players: PredictionPlayerInfo[];
  total_mmr: number;
  avg_mmr: number;
  win_probability: number;
  synergies: SynergyInfo[];
  avg_synergy_score: number;
  team_chemistry: TeamChemistry;
}

export interface MatchPredictionResponse {
  team_1: TeamPredictionInfo;
  team_2: TeamPredictionInfo;
  predicted_winner: 1 | 2;
  confidence: PredictionConfidence;
  upset_potential: boolean;
  match_quality: number;
  factors: string[];
}

// =============================================================================
// Health Check Types
// =============================================================================

export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
}

export interface VersionResponse {
  version: string;
  features: {
    winner_determination_error_handling: boolean;
    uneven_team_support: boolean;
  };
  status: 'up-to-date' | 'outdated';
}

// =============================================================================
// Race and Game Mode Enums
// =============================================================================

export enum Race {
  TERRAN = 'Terran',
  PROTOSS = 'Protoss',
  ZERG = 'Zerg',
  RANDOM = 'Random',
}

export interface TeamSuggestionWithImpact extends TeamSuggestion {
  team_1_avg_impact?: number;
  team_2_avg_impact?: number;
}

export type GameMode =
  | '2v2'
  | '3v3'
  | '4v4'
  | '5v5'
  | '2v1'
  | '3v1'
  | '3v2'
  | '4v1'
  | '4v2'
  | '4v3'
  | '5v1'
  | '5v2'
  | '5v3'
  | '5v4';

export type FairnessRating =
  | 'Perfect'
  | 'Very Good'
  | 'Good'
  | 'Fair'
  | 'Poor';
