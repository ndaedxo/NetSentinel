import z from "zod";

/**
 * Schema for report data
 */
export const ReportSchema = z.object({
  id: z.number(),
  title: z.string(),
  report_type: z.string(),
  status: z.enum(["generating", "completed", "failed", "scheduled"]),
  parameters: z.string().nullable(),
  file_path: z.string().nullable(),
  generated_by: z.string().nullable(),
  scheduled_for: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Type for report data inferred from schema
 */
export type ReportType = z.infer<typeof ReportSchema>;
