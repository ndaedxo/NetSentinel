import z from "zod";

/**
 * Schema for alert data
 */
export const AlertSchema = z.object({
  id: z.number(),
  title: z.string(),
  severity: z.enum(["low", "medium", "high", "critical"]),
  status: z.enum(["new", "acknowledged", "resolved"]),
  description: z.string().nullable(),
  threat_id: z.number().nullable(),
  is_acknowledged: z.number().int(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Type for alert data inferred from schema
 */
export type AlertType = z.infer<typeof AlertSchema>;
