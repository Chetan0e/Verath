import AsyncStorage from '@react-native-async-storage/async-storage';
import { AppState } from 'react-native';

const QUEUE_KEY = 'offline_queue';

/**
 * Offline Queue Service
 * Handles failed requests that need to be retried when network is restored.
 */

export const offlineQueue = {
  /**
   * Add a failed request to the offline queue
   */
  async add(request) {
    try {
      const queue = await this.getQueue();
      queue.push({
        ...request,
        timestamp: Date.now(),
        retryCount: 0,
      });
      await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
      console.log('[OfflineQueue] Added to queue:', request);
      return queue.length;
    } catch (error) {
      console.error('[OfflineQueue] Error adding to queue:', error);
      return 0;
    }
  },

  /**
   * Get all queued requests
   */
  async getQueue() {
    try {
      const queueJson = await AsyncStorage.getItem(QUEUE_KEY);
      return queueJson ? JSON.parse(queueJson) : [];
    } catch (error) {
      console.error('[OfflineQueue] Error getting queue:', error);
      return [];
    }
  },

  /**
   * Get queue size (for badge count)
   */
  async getSize() {
    const queue = await this.getQueue();
    return queue.length;
  },

  /**
   * Clear the queue
   */
  async clear() {
    try {
      await AsyncStorage.removeItem(QUEUE_KEY);
      console.log('[OfflineQueue] Queue cleared');
    } catch (error) {
      console.error('[OfflineQueue] Error clearing queue:', error);
    }
  },

  /**
   * Process and retry all queued requests
   */
  async drainQueue(axiosInstance) {
    const queue = await this.getQueue();
    if (queue.length === 0) {
      console.log('[OfflineQueue] Queue is empty, nothing to drain');
      return { success: 0, failed: 0 };
    }

    console.log(`[OfflineQueue] Draining ${queue.length} items`);
    let successCount = 0;
    let failedCount = 0;

    const remainingQueue = [];

    for (const item of queue) {
      try {
        const response = await axiosInstance({
          method: item.method,
          url: item.url,
          data: item.data,
          headers: item.headers,
        });

        if (response.status >= 200 && response.status < 300) {
          successCount++;
          console.log('[OfflineQueue] Successfully retried:', item.url);
        } else {
          failedCount++;
          item.retryCount = (item.retryCount || 0) + 1;
          if (item.retryCount < 3) {
            remainingQueue.push(item);
          }
          console.warn('[OfflineQueue] Retry failed:', item.url, response.status);
        }
      } catch (error) {
        failedCount++;
        item.retryCount = (item.retryCount || 0) + 1;
        if (item.retryCount < 3) {
          remainingQueue.push(item);
        }
        console.error('[OfflineQueue] Retry error:', item.url, error);
      }
    }

    // Update queue with remaining items
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(remainingQueue));

    console.log(`[OfflineQueue] Drain complete: ${successCount} success, ${failedCount} failed`);
    return { success: successCount, failed: failedCount };
  },
};

/**
 * Hook to automatically drain queue on app foreground or network restore
 */
export const setupOfflineQueueListener = (axiosInstance) => {
  const handleAppStateChange = (nextAppState) => {
    if (nextAppState === 'active') {
      console.log('[OfflineQueue] App came to foreground, draining queue');
      offlineQueue.drainQueue(axiosInstance);
    }
  };

  const subscription = AppState.addEventListener(
    'change',
    handleAppStateChange
  );

  return () => {
    subscription.remove();
  };
};
