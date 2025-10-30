import z from "zod";

/**
 * Schema for ML model data
 */
export const MLModelSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.enum(["active", "training", "inactive"]),
  accuracy: z.number().min(0).max(100),
  latency: z.number().positive(),
  detections: z.number().int().min(0),
  falsePositiveRate: z.number().min(0).max(100),
  lastTrained: z.string().optional(),
  modelType: z.string(),
  description: z.string(),
});

/**
 * Type for ML model data inferred from schema
 */
export type MLModel = z.infer<typeof MLModelSchema>;
