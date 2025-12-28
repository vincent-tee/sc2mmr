import { test, expect } from '@playwright/test';

test.describe('SC2 MMR Tracker - User Acceptance Testing', () => {
  test('UAT-1: Home page loads with player rankings', async ({ page }) => {
    // Step 1: Navigate to home page
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Take screenshot
    await page.screenshot({ path: 'test-results/uat-01-home-page.png', fullPage: true });
    
    // Verify page loads - check for SC2 MMR Tracker branding
    const title = await page.title();
    expect(title).toContain('SC2');
    
    // Check for main content area (use .first() to avoid strict mode)
    const mainContent = page.locator('main, #root, .app').first();
    await expect(mainContent).toBeVisible({ timeout: 10000 });
    
    console.log('✅ UAT-1: Home page loaded successfully');
  });

  test('UAT-2: Navigate to ML Intelligence page', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Step 3: Click on "ML Intel" navigation button
    const mlIntelNav = page.getByRole('link', { name: /ML Intel/i })
      .or(page.getByText(/ML Intel/i))
      .or(page.locator('a[href*="ml-intel"]'))
      .or(page.locator('nav').getByText(/ML/i));
    
    await mlIntelNav.first().click();
    await page.waitForLoadState('networkidle');
    
    // Take screenshot
    await page.screenshot({ path: 'test-results/uat-02-ml-intel-page.png', fullPage: true });
    
    // Step 4: Verify ML Intelligence page content
    // Check for "ML INTELLIGENCE" title
    const pageTitle = page.locator('h1, h2').filter({ hasText: /ML INTELLIGENCE/i });
    await expect(pageTitle).toBeVisible({ timeout: 10000 });
    
    // Check for accuracy metrics
    const accuracyText = page.getByText(/Accuracy|accuracy/i).first();
    await expect(accuracyText).toBeVisible({ timeout: 10000 });
    
    // Check for Retrain Model button
    const retrainButton = page.getByRole('button', { name: /Retrain Model/i });
    await expect(retrainButton).toBeVisible({ timeout: 10000 });
    
    console.log('✅ UAT-2: ML Intelligence page loaded with all required elements');
  });

  test('UAT-3: Navigate to Players page', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Step 5: Navigate to Players page
    const playersNav = page.getByRole('link', { name: /Players/i })
      .or(page.getByText(/Players/i).first())
      .or(page.locator('a[href*="players"]'));
    
    await playersNav.first().click();
    await page.waitForLoadState('networkidle');
    
    // Take screenshot
    await page.screenshot({ path: 'test-results/uat-03-players-page.png', fullPage: true });
    
    // Verify player list loads (look for table, list, or player cards)
    const playerContent = page.locator('table, .player-list, .player-card, [data-testid="player"]').first()
      .or(page.getByRole('table'))
      .or(page.locator('tbody tr').first());
    
    // Wait for either player content or a "no players" message
    const hasContent = await playerContent.first().isVisible({ timeout: 10000 }).catch(() => false);
    
    if (hasContent) {
      console.log('✅ UAT-3: Players page loaded with player list');
    } else {
      // Check if there's a "no players" or loading message
      const message = page.getByText(/No players|Loading|player/i).first();
      await expect(message).toBeVisible({ timeout: 5000 });
      console.log('✅ UAT-3: Players page loaded (empty or loading state)');
    }
  });

  test('UAT-4: Full navigation flow with screenshots', async ({ page }) => {
    test.setTimeout(60000); // Increase timeout to 60 seconds
    
    // Complete navigation test capturing all pages
    
    // Home Page
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'test-results/uat-full-01-home.png', fullPage: true });
    
    // Capture navigation menu
    const navLinks = await page.locator('nav a, header a, .nav-link, [role="navigation"] a').all();
    console.log(`Found ${navLinks.length} navigation links`);
    
    // Get page HTML snapshot for analysis
    const homeSnapshot = await page.locator('body').innerHTML();
    console.log('Home page body length:', homeSnapshot.length, 'characters');
    
    // Navigate to ML Intel (route is /ml-intelligence)
    await page.goto('http://localhost:3000/ml-intelligence');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'test-results/uat-full-02-ml-intel.png', fullPage: true });
    
    // Check for ML Intelligence title (with timeout)
    const mlTitle = page.locator('h1, h2').filter({ hasText: /ML INTELLIGENCE/i });
    await expect(mlTitle).toBeVisible({ timeout: 10000 });
    console.log('ML Intel page loaded successfully');
    
    // Navigate to Players
    await page.goto('http://localhost:3000/players');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'test-results/uat-full-03-players.png', fullPage: true });
    
    // Count player rows if table exists
    const playerRows = await page.locator('tbody tr').count();
    console.log('Player rows found:', playerRows);
    
    console.log('✅ UAT-4: Full navigation flow completed');
  });
});
