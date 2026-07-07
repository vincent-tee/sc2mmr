import { test, expect } from '@playwright/test';

test.describe('SC2 MMR Tracker - Route Verification UAT', () => {
  const routes = [
    { path: '/', title: /Squad|Welcome/i, name: 'Home' },
    { path: '/balance', title: /Team Generator/i, name: 'Balance' },
    { path: '/predictor', title: /Match Predictor/i, name: 'Predictor' },
    { path: '/history', title: /Match Archive|Match History/i, name: 'History' },
    { path: '/players', title: /Player Roster/i, name: 'Players' },
    { path: '/leaderboard', title: /Leaderboard/i, name: 'Leaderboard' },
    { path: '/achievements', title: /Achievements/i, name: 'Achievements' },
    { path: '/h2h', title: /Head to Head/i, name: 'Head to Head' },
    { path: '/ml-intelligence', title: /Intelligence Center/i, name: 'Intelligence Center' },
    { path: '/rating-system', title: /Rating System/i, name: 'Rating System' },
    { path: '/upload', title: /Upload/i, name: 'Upload' },
    { path: '/failed-uploads', title: /Failed Uploads/i, name: 'Failed Uploads' },
  ];

  for (const route of routes) {
    test(`Verify route: ${route.name} (${route.path})`, async ({ page }) => {
      // Increase timeout for slow transitions
      test.setTimeout(20000);
      
      console.log(`Navigating to ${route.path}...`);
      await page.goto(`http://localhost:3000${route.path}`, { waitUntil: 'domcontentloaded' });
      
      // Wait for content to appear (any heading)
      const heading = page.locator('h1, h2, h3').filter({ hasText: route.title });
      await expect(heading.first()).toBeVisible({ timeout: 12000 });
      
      // Take a screenshot for visual verification
      await page.screenshot({ path: `test-results/route-${route.name.replace(/\s+/g, '-').toLowerCase()}.png` });
      
      console.log(`✅ ${route.name} verified successfully`);
    });
  }
});
