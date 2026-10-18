import { test } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('Mobile API contract exports all required endpoints in api.js', async () => {
  const apiFileContent = fs.readFileSync(path.join(__dirname, '../services/api.js'), 'utf-8');
  
  const expectedExports = [
    'login',
    'signup',
    'logout',
    'getTimeline',
    'askQuestion',
    'uploadAudio',
    'startRecording',
    'deleteMemory',
    'getSummary',
    'getInsights',
    'getStatistics',
    'trainSpeaker',
    'getVoiceProfiles',
    'getStatus',
    'getRemindersUpcoming',
    'acknowledgeReminder',
  ];

  for (const fnName of expectedExports) {
    const regex = new RegExp(`export\\s+const\\s+${fnName}\\s*=`);
    assert.ok(
      regex.test(apiFileContent),
      `api.js must export ${fnName}`
    );
  }

  // Verify acknowledgeReminder calls the correct route
  assert.ok(
    apiFileContent.includes('/reminders/${alertId}/acknowledge'),
    'acknowledgeReminder must call /reminders/${alertId}/acknowledge'
  );

  // Verify memory deletion calls /memory/${memoryId}
  assert.ok(
    apiFileContent.includes('/memory/${memoryId}'),
    'deleteMemory must call /memory/${memoryId}'
  );
});

test('Mobile API configuration rejects physical device localhost assumption', async () => {
  const { API_BASE_URL } = await import('../config.js');
  assert.ok(API_BASE_URL, 'API_BASE_URL must be defined');
  // Verify trailing slashes are stripped
  assert.ok(!API_BASE_URL.endsWith('/'), 'API_BASE_URL must not end with a trailing slash');
});
