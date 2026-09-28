import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

// Runs the production bundle with intercepted HTTP: no live database/server.
test('record final teams and restore the locked assessment after navigation', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  const players = ['Alice', 'Bob', 'Carol', 'Dave'].map((name, index) => ({
    id: index + 1, name, mu: 25, sigma: 4, mmr: 2700, unified_mmr: 2700,
    total_games: 20, wins: 10, losses: 10, win_rate: .5, is_ai: false,
    favorite_race: 'Terran', avg_overall_impact: 50, last_played: null,
  }));
  const suggestion = {
    balance_prediction_id: 42, map_name: null,
    team_1: { players: players.slice(0, 2), total_mmr: 5400, avg_mmr: 2700 },
    team_2: { players: players.slice(2), total_mmr: 5400, avg_mmr: 2700 },
    mmr_difference: 0, match_quality: 75, fairness_rating: 'Good',
    win_probability_team_1: 50, win_probability_team_2: 50,
  };
  let saved: Record<string, unknown> | null = null;
  let submitted: Record<string, unknown> | null = null;
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api/, '');
    let response: unknown = {};
    if (path === '/auth/status') response = { authenticated: true, auth_enabled: false, public_read: true };
    else if (path === '/players/' || path === '/players') response = players;
    else if (path === '/teams/balance') response = [suggestion];
    else if (path === '/teams/predict') response = {
      team_1: { win_probability: 52 }, team_2: { win_probability: 48 },
      predicted_winner: 1, confidence: 'Low', match_quality: 0.74, factors: [] };
    else if (path === '/teams/suggest-swaps') response = { current_match_quality: 0.74, current_win_probability: 0.52, suggestions: [] };
    else if (path.includes('ai-difficulties')) response = { difficulties: {} };
    else if (path.startsWith('/replays/matches')) response = { matches: [], total: 0 };
    else if (path === '/judgments' && route.request().method() === 'GET') response = saved ? [saved] : [];
    else if (path === '/judgments' && route.request().method() === 'POST') {
      submitted = route.request().postDataJSON();
      const body = submitted as Record<string, unknown>;
      saved = { ...body, id: 7, selection_id: null, match_id: null, is_locked: false,
        created_at: '2026-09-14T09:00:00', locked_at: null,
        team1_player_ids_key: (body.team1_player_ids as number[]).slice().sort().join(','),
        team2_player_ids_key: (body.team2_player_ids as number[]).slice().sort().join(','),
        team1_context: body.team1_context ?? null, team2_context: body.team2_context ?? null,
        map_name: body.map_name ?? null, model_predicted_team1_win_prob: .5, model_version: 'mmr_v2' };
      response = saved;
    } else if (path === '/judgments/7/lock') {
      saved = { ...saved, is_locked: true, locked_at: '2026-09-14T09:01:00', selection_id: 9 };
      response = saved;
    } else if (url.hostname === 'sc2mmr.test' && !url.pathname.startsWith('/api/')) {
      const asset = url.pathname.startsWith('/assets/') ? url.pathname.slice(1) : 'index.html';
      const body = await readFile(resolve('dist', asset));
      await route.fulfill({ body, contentType: asset.endsWith('.js') ? 'text/javascript' : asset.endsWith('.css') ? 'text/css' : 'text/html' });
      return;
    }
    await route.fulfill({ json: response });
  });
  await page.goto('http://sc2mmr.test/balance');
  for (const player of players) await page.getByText(player.name, { exact: true }).first().click();
  await page.getByRole('button', { name: 'Generate teams' }).click();
  await page.getByRole('button', { name: 'Adjust teams' }).click();
  await page.getByRole('button', { name: 'Pick Alice to swap' }).click();
  await page.getByRole('button', { name: 'Pick Carol to swap' }).click();
  await expect(page.getByText('Adjusted')).toBeVisible();
  await page.getByRole('button', { name: 'Record this game' }).click();
  await page.getByPlaceholder('Organizer name').fill('Organizer');
  await page.getByRole('spinbutton').fill('65');
  await page.getByRole('button', { name: 'Record Judgment' }).click();
  await expect(page.getByRole('button', { name: 'Start game with these teams' })).toBeVisible();
  expect(submitted!['team1_player_ids']).toEqual([3, 2]);
  expect(submitted!['human_win_prob']).toBe(.65);
  await page.getByRole('button', { name: 'Start game with these teams' }).click();
  await expect(page.getByText(/Game #9 recorded/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Pick Bob to swap' })).toBeDisabled();
  await page.reload();
  for (const player of players) await page.getByText(player.name, { exact: true }).first().click();
  await page.getByRole('button', { name: 'Generate teams' }).click();
  await expect(page.getByText(/Game #9 recorded/)).toBeVisible();
  await page.getByRole('button', { name: 'Adjust teams' }).click();
  await expect(page.getByRole('button', { name: 'Pick Bob to swap' })).toBeDisabled();
  expect(errors).toEqual([]);
});
