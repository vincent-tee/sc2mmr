/**
 * usePlayerSelection Custom Hook
 * Manages player selection state and operations for team generation
 *
 * Provides functionality for:
 * - Adding/removing players from selection
 * - Validation (duplicate prevention, max player limits)
 * - Bulk operations (clear, select all)
 * - Query helpers (isSelected, canAddMore)
 */

import { useState, useCallback } from 'react';
import type { Player } from '@/types/api';

interface UsePlayerSelectionOptions {
  maxPlayers?: number;
  minPlayers?: number;
}

interface UsePlayerSelectionReturn {
  selectedPlayers: Player[];
  addPlayer: (player: Player) => void;
  removePlayer: (playerId: number) => void;
  clearPlayers: () => void;
  isSelected: (playerId: number) => boolean;
  canAddMore: boolean;
  playerCount: number;
  togglePlayer: (player: Player) => void;
  setSelectedPlayers: (players: Player[]) => void;
}

const DEFAULT_MIN_PLAYERS = 2;
const DEFAULT_MAX_PLAYERS = 10; // Reasonable limit for team balancing

/**
 * Custom hook for managing player selection state
 *
 * @param options Configuration options for player selection
 * @returns Object with selection state and handler functions
 *
 * @example
 * const { selectedPlayers, addPlayer, removePlayer, canAddMore } = usePlayerSelection({
 *   minPlayers: 2,
 *   maxPlayers: 10
 * });
 */
export const usePlayerSelection = (
  options: UsePlayerSelectionOptions = {},
): UsePlayerSelectionReturn => {
  const { maxPlayers = DEFAULT_MAX_PLAYERS } = options;
  // minPlayers reserved for future validation (e.g., minimum team size)
  const _minPlayers = options.minPlayers ?? DEFAULT_MIN_PLAYERS;
  void _minPlayers; // Explicitly mark as intentionally unused for now

  const [selectedPlayers, setSelectedPlayers] = useState<Player[]>([]);

  /**
   * Add a player to the selection if not already selected and within max limit
   */
  const addPlayer = useCallback(
    (player: Player): void => {
      setSelectedPlayers((prev) => {
        // Check if player is already selected
        if (prev.some((p) => p.id === player.id)) {
          return prev;
        }

        // Check if adding another player would exceed maxPlayers
        if (prev.length >= maxPlayers) {
          return prev;
        }

        return [...prev, player];
      });
    },
    [maxPlayers],
  );

  /**
   * Remove a player from the selection
   */
  const removePlayer = useCallback((playerId: number): void => {
    setSelectedPlayers((prev) => prev.filter((p) => p.id !== playerId));
  }, []);

  /**
   * Toggle a player's selection status (add if not selected, remove if selected)
   */
  const togglePlayer = useCallback(
    (player: Player): void => {
      setSelectedPlayers((prev) => {
        const isSelected = prev.some((p) => p.id === player.id);
        if (isSelected) {
          return prev.filter((p) => p.id !== player.id);
        } else {
          // Check max limit before adding
          if (prev.length >= maxPlayers) {
            return prev;
          }
          return [...prev, player];
        }
      });
    },
    [maxPlayers],
  );

  /**
   * Clear all selected players
   */
  const clearPlayers = useCallback((): void => {
    setSelectedPlayers([]);
  }, []);

  /**
   * Check if a specific player is currently selected
   */
  const isSelected = useCallback(
    (playerId: number): boolean => {
      return selectedPlayers.some((p) => p.id === playerId);
    },
    [selectedPlayers],
  );

  /**
   * Check if more players can be added without exceeding max limit
   */
  const canAddMore = selectedPlayers.length < maxPlayers;

  return {
    selectedPlayers,
    addPlayer,
    removePlayer,
    clearPlayers,
    isSelected,
    canAddMore,
    playerCount: selectedPlayers.length,
    togglePlayer,
    setSelectedPlayers,
  };
};
