import z from "zod";

/**
 * Schema for network device data
 */
export const NetworkDeviceSchema = z.object({
  id: z.number(),
  hostname: z.string(),
  ip_address: z.string(),
  device_type: z.string(),
  os_info: z.string().nullable(),
  mac_address: z.string().nullable(),
  vendor: z.string().nullable(),
  location: z.string().nullable(),
  is_online: z.number().int(),
  last_seen_at: z.string().nullable(),
  vulnerability_score: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Type for network device data inferred from schema
 */
export type NetworkDeviceType = z.infer<typeof NetworkDeviceSchema>;

/**
 * Schema for network connection data
 */
export const NetworkConnectionSchema = z.object({
  id: z.number(),
  source_device_id: z.number(),
  destination_device_id: z.number(),
  source_port: z.number().nullable(),
  destination_port: z.number().nullable(),
  protocol: z.string(),
  connection_state: z.string(),
  bandwidth_usage: z.number(),
  packet_count: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Type for network connection data inferred from schema
 */
export type NetworkConnectionType = z.infer<typeof NetworkConnectionSchema>;

/**
 * Interface for network topology data
 */
export interface NetworkTopology {
  devices: NetworkDeviceType[];
  connections: NetworkConnectionType[];
}
