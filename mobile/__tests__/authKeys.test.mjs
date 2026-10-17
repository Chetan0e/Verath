import { test } from 'node:test';
import assert from 'node:assert';
import { TOKEN_KEY, REFRESH_KEY, USERNAME_KEY } from '../services/authKeys.js';

test('authKeys defines required storage keys', () => {
  assert.strictEqual(TOKEN_KEY, 'verath_token');
  assert.strictEqual(REFRESH_KEY, 'verath_refresh_token');
  assert.strictEqual(USERNAME_KEY, 'verath_username');
});
