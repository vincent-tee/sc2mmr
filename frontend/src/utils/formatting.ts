/**
 * Formatting Utilities
 * Helper functions for displaying data to users
 */
import type { TeamSuggestion, TeamPlayer } from '@/types/api';
import type { ApiClientError } from '@/api/client';

// =============================================================================
// MMR Formatting
// =============================================================================

/**
 * Format MMR value with proper rounding
 */
export const formatMMR = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return 'N/A';
  return Math.round(value).toLocaleString();
};

// =============================================================================
// Date/Time Formatting (AEST)
// =============================================================================

/**
 * The API returns naive timestamps with no timezone suffix (backend stores
 * everything as datetime.utcnow(), and FastAPI/Pydantic can't mark a naive
 * datetime as UTC on the way out). `new Date(isoString)` treats a
 * timezone-less string as browser-local time, which silently produces the
 * wrong instant for any viewer whose OS timezone isn't UTC - exactly the
 * GMT+10 offset bug. Force UTC interpretation before parsing so the
 * `timeZone: 'Australia/Sydney'` conversions below land on the real time.
 */
const parseUTC = (isoString: string): Date => {
  const hasTimezone = /Z$|[+-]\d{2}:?\d{2}$/.test(isoString);
  return new Date(hasTimezone ? isoString : `${isoString}Z`);
};

/**
 * Format date/time for user display in AEST (Australian Eastern Standard Time)
 */
export const formatDate = (isoString: string | null | undefined): string => {
  if (!isoString) return 'Never';

  const date = parseUTC(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  // Show relative time for recent dates
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;

  // Show full date for older entries in AEST
  return date.toLocaleDateString('en-AU', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'Australia/Sydney'
  });
};

/**
 * Format date and time in AEST (Australian Eastern Standard Time)
 */
export const formatDateTime = (isoString: string | null | undefined): string => {
  if (!isoString) return 'Never';

  const date = parseUTC(isoString);
  return date.toLocaleString('en-AU', {
    timeZone: 'Australia/Sydney',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
};

/**
 * Format date only in AEST (Australian Eastern Standard Time)
 */
export const formatDateOnly = (isoString: string | null | undefined): string => {
  if (!isoString) return 'Never';

  const date = parseUTC(isoString);
  return date.toLocaleDateString('en-AU', {
    timeZone: 'Australia/Sydney',
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

/**
 * Format date + time without the year, in AEST. For recent-match feeds
 * (e.g. "last N matches" widgets) where every entry is close enough that
 * the year is always redundant, but same-day matches still need the time
 * to tell them apart.
 */
export const formatDateTimeShort = (isoString: string | null | undefined): string => {
  if (!isoString) return 'Never';

  const date = parseUTC(isoString);
  const datePart = date.toLocaleDateString('en-AU', {
    timeZone: 'Australia/Sydney',
    month: 'short',
    day: 'numeric',
  });
  return `${datePart}, ${formatTimeOnly(isoString)}`;
};

/**
 * Format time only in AEST (Australian Eastern Standard Time)
 */
export const formatTimeOnly = (isoString: string | null | undefined): string => {
  if (!isoString) return '';

  const date = parseUTC(isoString);
  return date.toLocaleTimeString('en-AU', {
    timeZone: 'Australia/Sydney',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
};

// =============================================================================
// Win Rate / Probability Formatting
// =============================================================================

/**
 * Format win rate as percentage
 */
export const formatWinRate = (rate: number | null | undefined): string => {
  if (rate === null || rate === undefined) return 'N/A';
  return `${(rate * 100).toFixed(1)}%`;
};

/**
 * Format win probability as percentage (alias for formatWinRate)
 */
export const formatWinProbability = (probability: number | null | undefined): string => {
  return formatWinRate(probability);
};

// =============================================================================
// Match Result Helpers
// =============================================================================

/**
 * Check if a match was an upset based on win probability
 * Returns true if the underdog (< 40% predicted chance) won
 */
export const isUpset = (
  teamWon: number,
  team1WinProb: number | null | undefined,
  team2WinProb: number | null | undefined
): boolean => {
  if (!team1WinProb || !team2WinProb) return false;

  if (teamWon === 1) {
    return team1WinProb < 0.4;
  } else if (teamWon === 2) {
    return team2WinProb < 0.4;
  }
  return false;
};

/**
 * Get upset indicator emoji/text
 */
export const getUpsetIndicator = (
  teamWon: number,
  team1WinProb: number | null | undefined,
  team2WinProb: number | null | undefined
): string | null => {
  if (isUpset(teamWon, team1WinProb, team2WinProb)) {
    const winProb = teamWon === 1 ? team1WinProb : team2WinProb;
    if (winProb && winProb < 0.25) return 'MAJOR UPSET';
    if (winProb && winProb < 0.35) return 'UPSET';
    return 'UNDERDOG WIN';
  }
  return null;
};

/**
 * Format game duration
 */
export const formatDuration = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
};

// =============================================================================
// Race Helpers
// =============================================================================

type RaceName = 'Terran' | 'Protoss' | 'Zerg' | 'Random';

/**
 * Get race emoji/icon
 */
export const getRaceEmoji = (race: string | null | undefined): string => {
  const raceMap: Record<RaceName, string> = {
    Terran: 'T',
    Protoss: 'P',
    Zerg: 'Z',
    Random: 'R'
  };
  return raceMap[race as RaceName] || '?';
};

/**
 * Get race color for styling
 */
export const getRaceColor = (race: string | null | undefined): string => {
  const colorMap: Record<RaceName, string> = {
    Terran: 'terran',
    Protoss: 'protoss',
    Zerg: 'zerg',
    Random: 'gray'
  };
  return colorMap[race as RaceName] || 'gray';
};

// =============================================================================
// Player Helpers
// =============================================================================

interface RaceInfo {
  name: RaceName;
  games: number;
  emoji: string;
}

// Interface for players with race game counts
interface PlayerWithRaceGames {
  terran_games?: number;
  protoss_games?: number;
  zerg_games?: number;
  random_games?: number;
}

/**
 * Get all races a player has played
 * Returns array of race objects with game counts
 */
export const getPlayerRaces = (player: PlayerWithRaceGames): RaceInfo[] => {
  const races: RaceInfo[] = [];
  if (player.terran_games && player.terran_games > 0) {
    races.push({ name: 'Terran', games: player.terran_games, emoji: 'T' });
  }
  if (player.protoss_games && player.protoss_games > 0) {
    races.push({ name: 'Protoss', games: player.protoss_games, emoji: 'P' });
  }
  if (player.zerg_games && player.zerg_games > 0) {
    races.push({ name: 'Zerg', games: player.zerg_games, emoji: 'Z' });
  }
  if (player.random_games && player.random_games > 0) {
    races.push({ name: 'Random', games: player.random_games, emoji: 'R' });
  }

  // Sort by most played
  races.sort((a, b) => b.games - a.games);

  return races;
};

/**
 * Get MMR badge color based on value
 */
export const getMMRBadgeColor = (mmr: number): string => {
  if (mmr >= 1300) return 'green';
  if (mmr >= 1200) return 'blue';
  if (mmr >= 1100) return 'yellow';
  return 'orange';
};

/**
 * Get fairness rating color
 */
export const getFairnessColor = (rating: string): string => {
  const colorMap: Record<string, string> = {
    'Excellent': 'green',
    'Good': 'blue',
    'Fair': 'yellow',
    'Poor': 'orange',
    'Very Poor': 'red'
  };
  return colorMap[rating] || 'gray';
};

/**
 * Get dynamic mascot URL for a player using DiceBear API
 * Returns a unique SVG mascot based on name and race
 */
export const getPlayerAvatarUrl = (name: string, race?: string, isAi?: boolean): string => {
  const seed = encodeURIComponent(name.trim());
  const raceLower = race?.toLowerCase();
  
  // Pick a "mascot style" based on race/status
  let style = 'bottts'; // Default: Mechanical/Tech (fits Terran/SC2)
  
  if (isAi) {
    style = 'bottts-neutral'; // Simplified robots for AI
  } else if (raceLower === 'zerg') {
    style = 'big-ears'; // Organic, slightly "monster" like
  } else if (raceLower === 'protoss') {
    style = 'adventurer'; // Noble, humanoid explorers
  } else if (raceLower === 'random' || !raceLower) {
    style = 'pixel-art'; // Classic gaming mascots
  }

  // Use a high-quality version of the API
  return `https://api.dicebear.com/7.x/${style}/svg?seed=${seed}&backgroundColor=transparent`;
};

/**
 * Get player initials for avatar (Fallback)
 */
export const getInitials = (name: string | null | undefined): string => {
  if (!name) return '?';
  const parts = name.trim().split(' ');
  if (parts.length === 1) {
    return parts[0].substring(0, 2).toUpperCase();
  }
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};

// =============================================================================
// Team Text Generation
// =============================================================================

export const generateTeamText = (teamSuggestion: TeamSuggestion): string => {
  const { team_1, team_2, win_probability_team_1, win_probability_team_2, match_quality } = teamSuggestion;

  let text = 'SC2 Match Info\n';
  text += `Match Quality: ${Math.round(match_quality)}%\n\n`;

  text += `T1 (${Math.round(win_probability_team_1)}%): `;
  text += team_1.players.map(p => `${p.name} (${formatMMR(p.mmr)})`).join(', ');

  text += `\n\nT2 (${Math.round(win_probability_team_2)}%): `;
  text += team_2.players.map(p => `${p.name} (${formatMMR(p.mmr)})`).join(', ');

  return text;
};

export const generateAllTeamsText = (suggestions: TeamSuggestion[]): string => {
  let text = 'Match Configs\n\n';

  suggestions.forEach((s, index) => {
    const label = index === 0 ? 'Optimal' : index === 1 ? 'Tactical' : `Alt ${index - 1}`;
    
    text += `[${label}]\n`;
    text += `T1 (${Math.round(s.win_probability_team_1)}%): ${s.team_1.players.map(p => p.name).join(', ')}\n`;
    text += `T2 (${Math.round(s.win_probability_team_2)}%): ${s.team_2.players.map(p => p.name).join(', ')}\n\n`;
  });

  return text;
};


// =============================================================================
// Clipboard
// =============================================================================

/**
 * Copy text to clipboard
 */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    } else {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.select();
      const success = document.execCommand('copy');
      document.body.removeChild(textArea);
      return success;
    }
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    return false;
  }
};

// =============================================================================
// Error Parsing
// =============================================================================

interface ErrorWithResponse {
  userMessage?: string;
  response?: {
    data?: {
      detail?: string;
    };
  };
}

/**
 * Parse API error message
 */
export const parseErrorMessage = (error: ErrorWithResponse | ApiClientError): string => {
  if ('userMessage' in error && error.userMessage) {
    return error.userMessage;
  }

  // Type guard for response data with detail property
  const responseData = error.response?.data as { detail?: string } | undefined;
  if (responseData?.detail) {
    const detail = responseData.detail;

    // Check for Winner Determination errors FIRST (before Parse error check)
    // Backend sends: "Winner determination failed: {message}"
    if (detail.startsWith('Winner determination failed:')) {
      // Return the full message from backend - it contains detailed diagnostics
      return detail.replace('Winner determination failed: ', 'Winner determination failed: ');
    }

    // Then check for Parse errors
    // Backend sends: "Parse error: {message}"
    if (detail.startsWith('Parse error:')) {
      return detail; // Return full backend message
    }

    // Translate other common backend errors to friendly messages
    if (detail.includes('Validation failed')) {
      return detail.replace('Validation failed: ', '');
    }
    if (detail.includes('Invalid game mode') || detail.includes('Invalid number of players')) {
      return "This game mode isn't supported (only 2v2, 3v3, 4v4, 5v5)";
    }
    if (detail.includes('Game too short') || detail.includes('duration')) {
      return 'This game was too short to analyze (under 3 minutes)';
    }
    if (detail.includes('Missing players')) {
      return "Couldn't identify all players in this match";
    }

    return detail;
  }

  return 'An unexpected error occurred';
};
