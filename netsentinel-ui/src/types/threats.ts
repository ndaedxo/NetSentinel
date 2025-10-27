import z from "zod";

/**
 * Schema for threat data
 */
export const ThreatSchema = z.object({
  id: z.number(),
  ip_address: z.string(),
  country_code: z.string().nullable(),
  threat_score: z.number(),
  severity: z.enum(["low", "medium", "high", "critical"]),
  threat_type: z.string(),
  description: z.string().nullable(),
  honeypot_service: z.string().nullable(),
  is_blocked: z.number().int(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Type for threat data inferred from schema
 */
export type ThreatType = z.infer<typeof ThreatSchema>;
