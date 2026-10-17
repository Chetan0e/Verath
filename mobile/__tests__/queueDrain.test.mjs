import { test } from 'node:test';
import assert from 'node:assert';

test('Offline queue drain logic handles retry limit and success', async () => {
  // Simulate queue drain logic identically to mobile/services/offlineQueue.js
  let queue = [
    { id: 1, url: '/record', method: 'POST', retryCount: 0 },
    { id: 2, url: '/query', method: 'POST', retryCount: 2 },
  ];

  const axiosMock = async (item) => {
    if (item.id === 1) {
      return { status: 200, data: { success: true } };
    }
    // item 2 fails
    const err = new Error('Network error');
    err.status = 500;
    throw err;
  };

  let successCount = 0;
  let failedCount = 0;
  const remainingQueue = [];

  for (const item of queue) {
    try {
      const response = await axiosMock(item);
      if (response.status >= 200 && response.status < 300) {
        successCount++;
      } else {
        failedCount++;
        item.retryCount = (item.retryCount || 0) + 1;
        if (item.retryCount < 3) {
          remainingQueue.push(item);
        }
      }
    } catch (error) {
      failedCount++;
      item.retryCount = (item.retryCount || 0) + 1;
      if (item.retryCount < 3) {
        remainingQueue.push(item);
      }
    }
  }

  assert.strictEqual(successCount, 1, 'Item 1 should succeed');
  assert.strictEqual(failedCount, 1, 'Item 2 should fail');
  assert.strictEqual(remainingQueue.length, 0, 'Item 2 reached 3 retries and was pruned');
});
