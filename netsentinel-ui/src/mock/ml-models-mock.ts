import { faker } from '@faker-js/faker';

/**
 * ML Model interface
 */
export interface MLModel {
  id: string;
  name: string;
  status: "active" | "training" | "inactive";
  accuracy: number;
  latency: number;
  detections: number;
  falsePositiveRate: number;
  lastTrained?: string;
  modelType: string;
  description: string;
}

/**
 * Generate dynamic ML model data
 */
export const generateMLModels = (count: number = 5): MLModel[] => {
  const modelNames = [
    'FastFlow', 'EfficientAD', 'PaDiM', 'PatchCore', 'ReverseDistillation',
    'CFA', 'RD++', 'DRAEM', 'CutPaste', 'AnomalyTransformer'
  ];

  const modelTypes = [
    'Deep Learning Anomaly Detection',
    'One-Class Classification',
    'Autoencoder Network',
    'Generative Adversarial Network',
    'Transformer-based Detection'
  ];

  const statuses: Array<"active" | "training" | "inactive"> = ['active', 'training', 'inactive'];

  return Array.from({ length: count }, (_, index) => {
    const status = faker.helpers.arrayElement(statuses);
    const baseAccuracy = faker.number.float({ min: 85, max: 98 });
    const accuracy = status === 'training' ? baseAccuracy * 0.9 : baseAccuracy;

    return {
      id: faker.string.uuid(),
      name: modelNames[index % modelNames.length] || faker.company.buzzNoun(),
      status,
      accuracy: Math.round(accuracy * 10) / 10,
      latency: faker.number.int({ min: 8, max: 35 }),
      detections: faker.number.int({ min: 500, max: 5000 }),
      falsePositiveRate: Math.round(faker.number.float({ min: 0.5, max: 5 }) * 10) / 10,
      lastTrained: faker.date.recent({ days: 30 }).toISOString(),
      modelType: faker.helpers.arrayElement(modelTypes),
      description: faker.lorem.sentence({ min: 8, max: 15 })
    };
  });
};

/**
 * Mock ML models data - dynamically generated
 */
export const mockMLModels: MLModel[] = generateMLModels(6);

/**
 * Generate models by status
 */
export const generateModelsByStatus = (status: "active" | "training" | "inactive", count: number = 3): MLModel[] => {
  return Array.from({ length: count }, () => ({
    id: faker.string.uuid(),
    name: faker.company.buzzNoun(),
    status,
    accuracy: faker.number.float({ min: 85, max: 98 }),
    latency: faker.number.int({ min: 8, max: 35 }),
    detections: faker.number.int({ min: 500, max: 5000 }),
    falsePositiveRate: faker.number.float({ min: 0.5, max: 5 }),
    lastTrained: faker.date.recent({ days: 30 }).toISOString(),
    modelType: faker.helpers.arrayElement([
      'Deep Learning Anomaly Detection',
      'One-Class Classification',
      'Autoencoder Network'
    ]),
    description: faker.lorem.sentence()
  }));
};

/**
 * Get model performance metrics
 */
export const getModelPerformanceMetrics = (models: MLModel[]) => {
  const activeModels = models.filter(m => m.status === 'active');
  const avgAccuracy = activeModels.length > 0
    ? activeModels.reduce((sum, m) => sum + m.accuracy, 0) / activeModels.length
    : 0;
  const totalDetections = models.reduce((sum, m) => sum + m.detections, 0);
  const avgLatency = models.length > 0
    ? models.reduce((sum, m) => sum + m.latency, 0) / models.length
    : 0;

  return {
    activeModels: activeModels.length,
    avgAccuracy: Math.round(avgAccuracy * 10) / 10,
    totalDetections,
    avgLatency: Math.round(avgLatency)
  };
};
