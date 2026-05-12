import { useEffect } from 'react';
import { getTaskStatus } from '../services/api';

export const usePolling = (taskId, onComplete, onError, interval = 2000) => {
  useEffect(() => {
    let pollInterval;

    if (taskId) {
      pollInterval = setInterval(async () => {
        try {
          const { data } = await getTaskStatus(taskId);
          if (data.status === 'SUCCESS') {
            onComplete(data.result);
            clearInterval(pollInterval);
          } else if (data.status === 'FAILURE') {
            onError(data.error || 'Task failed', data.code);
            clearInterval(pollInterval);
          }
        } catch {
          onError('Connection lost during status check');
          clearInterval(pollInterval);
        }
      }, interval);
    }

    return () => clearInterval(pollInterval);
  }, [taskId, onComplete, onError, interval]);
};
