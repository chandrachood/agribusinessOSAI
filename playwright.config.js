const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: false,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5010',
    headless: true,
    channel: 'chrome',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'venv\\Scripts\\python.exe tests\\e2e\\mock_server.py',
    url: 'http://127.0.0.1:5010/health',
    reuseExistingServer: true,
    timeout: 60000,
  },
});
