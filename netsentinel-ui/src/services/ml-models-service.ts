import type { MLModel } from '@/types';
import { mockConfig } from '@/test/__mocks__/mock-config';
import { generateMLModels, mockMLModels } from '@/mock/ml-models-mock';

/**
 * Get all ML models using dynamic mocking
 */
export async function getMLModels(): Promise<MLModel[]> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay if enabled
  await store.getGenerator('threats').delay(delayRange.min, delayRange.max);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('network');
  }

  // Generate dynamic ML models
  return process.env.NODE_ENV === 'test' ? generateMLModels(6) : mockMLModels;
}

/**
 * Get ML model performance metrics
 */
export async function getMLModelMetrics(): Promise<{
  activeModels: number;
  avgAccuracy: number;
  totalDetections: number;
  avgLatency: number;
}> {
  const models = await getMLModels();

  const activeModels = models.filter(m => m.status === 'active').length;
  const avgAccuracy = activeModels > 0
    ? models.filter(m => m.status === 'active').reduce((sum, m) => sum + m.accuracy, 0) / activeModels
    : 0;
  const totalDetections = models.reduce((sum, m) => sum + m.detections, 0);
  const avgLatency = models.length > 0
    ? models.reduce((sum, m) => sum + m.latency, 0) / models.length
    : 0;

  return {
    activeModels,
    avgAccuracy: Math.round(avgAccuracy * 10) / 10,
    totalDetections,
    avgLatency: Math.round(avgLatency)
  };
}

/**
 * Update ML model status
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function updateMLModelStatus(_modelId: string, _status: "active" | "training" | "inactive"): Promise<{ success: boolean }> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay if enabled
  await store.getGenerator('threats').delay(delayRange.min, delayRange.max);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('server');
  }

  // In a real implementation, this would update the model status
  return { success: true };
}

/**
 * Retrain ML model
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function retrainMLModel(_modelId: string): Promise<{ success: boolean; estimatedTime?: number }> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay if enabled (longer for retraining)
  await store.getGenerator('threats').delay(delayRange.min * 3, delayRange.max * 4);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('server');
  }

  // Return estimated completion time
  return {
    success: true,
    estimatedTime: Math.floor(Math.random() * 3600) + 1800 // 30 minutes to 1.5 hours
  };
}
