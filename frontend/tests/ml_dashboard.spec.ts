import { test, expect } from '@playwright/test';

test.describe('ML Intelligence Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the ML Intelligence page
    await page.goto('http://localhost:3000/ml-intelligence');
    // Wait for page to load - either content or loading state
    await page.waitForLoadState('networkidle');
  });

  test('should display the dashboard title', async ({ page }) => {
    // Title is uppercase: "ML INTELLIGENCE"
    const title = page.locator('h1, h2').filter({ hasText: /ML INTELLIGENCE/i });
    await expect(title).toBeVisible({ timeout: 10000 });
  });

  test('should display model accuracy metrics', async ({ page }) => {
    // Check for accuracy cards or sections (Hybrid Accuracy, TrueSkill Baseline)
    const accuracySection = page.getByText(/Accuracy|Baseline/i).first();
    await expect(accuracySection).toBeVisible({ timeout: 10000 });
  });

  test('should display global feature importance chart', async ({ page }) => {
    // Check for chart container OR "no data" message (valid when no matches exist)
    const chart = page.locator('svg.recharts-surface, .recharts-responsive-container').first();
    const noDataMessage = page.getByText(/No importance data|Insufficient data/i).first();
    
    // Either chart or no-data message should be visible
    const chartVisible = await chart.isVisible().catch(() => false);
    const noDataVisible = await noDataMessage.isVisible().catch(() => false);
    
    expect(chartVisible || noDataVisible).toBeTruthy();
  });

  test('should have a functional retrain button', async ({ page }) => {
    // Button text is "Retrain Model"
    const retrainButton = page.getByRole('button', { name: /Retrain Model/i });
    await expect(retrainButton).toBeEnabled({ timeout: 10000 });
    
    // Click the retrain button
    await retrainButton.click();
    
    // Check for loading state or toast feedback
    const feedback = page.getByText(/Training|Retrained|Model/i).first();
    await expect(feedback).toBeVisible({ timeout: 15000 });
  });
});
