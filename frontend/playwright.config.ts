import { defineConfig, devices } from '@playwright/test';

/**
 * Cấu hình kiểm thử đầu cuối (E2E) Playwright cho Frontend
 * Tuân thủ quy định tại AGENTS.md và thiết kế hệ thống
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  outputDir: './e2e/test-results',
  // Model cục bộ (Ollama) trên GPU 8 GB có thể mất 10-30s nạp lần đầu, đặt thời gian chờ mỗi kịch bản 120 giây
  timeout: 120_000,
  expect: {
    timeout: 30_000,
  },
  // Chạy tuần tự 1 worker để tránh tranh chấp hàng đợi xử lý mô hình và CSDL thực tế
  fullyParallel: false,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  use: {
    baseURL: 'http://localhost:8080',
    trace: 'on-first-retry',
    video: 'off',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
