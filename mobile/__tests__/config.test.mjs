import { test } from 'node:test';
import assert from 'node:assert';

test('Mobile config fallback without env', async () => {
  delete process.env.EXPO_PUBLIC_API_URL;
  const mod = await import(`../config.js?t=${Date.now()}`);
  assert.strictEqual(mod.API_BASE_URL, 'http://localhost:8000');
});

test('Mobile config with EXPO_PUBLIC_API_URL set', async () => {
  process.env.EXPO_PUBLIC_API_URL = 'https://api.verath.app';
  const mod = await import(`../config.js?t=${Date.now() + 1}`);
  assert.strictEqual(mod.API_BASE_URL, 'https://api.verath.app');
});
