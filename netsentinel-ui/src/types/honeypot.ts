import z from "zod";

/**
 * Schema for honeypot service data
 */
export const HoneypotServiceSchema = z.object({
  id: z.number(),
  name: z.string(),
  port: z.number(),
  protocol: z.string(),
  is_active: z.number().int(),
  connection_count: z.number(),
  last_connection_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Type for honeypot service data inferred from schema
 */
export type HoneypotServiceType = z.infer<typeof HoneypotServiceSchema>;
