import z from "zod";

/**
 * Schema for incident data
 */
export const IncidentSchema = z.object({
  id: z.number(),
  title: z.string(),
  severity: z.enum(["low", "medium", "high", "critical"]),
  status: z.enum(["open", "investigating", "contained", "resolved", "closed"]),
  category: z.string(),
  description: z.string().nullable(),
  affected_systems: z.string().nullable(),
  assigned_to: z.string().nullable(),
  response_plan: z.string().nullable(),
  containment_actions: z.string().nullable(),
  recovery_actions: z.string().nullable(),
  lessons_learned: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Type for incident data inferred from schema
 */
export type IncidentType = z.infer<typeof IncidentSchema>;

/**
 * Schema for incident timeline data
 */
export const IncidentTimelineSchema = z.object({
  id: z.number(),
  incident_id: z.number(),
  action_type: z.string(),
  description: z.string(),
  performed_by: z.string().nullable(),
  created_at: z.string(),
});

/**
 * Type for incident timeline data inferred from schema
 */
export type IncidentTimelineType = z.infer<typeof IncidentTimelineSchema>;
