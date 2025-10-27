import { useState, useEffect } from "react";
import * as services from "@/services";

/**
 * Generic hook for fetching data - supports both service functions and legacy endpoint strings
 */
export function useApi<T>(
  endpointOrService?: string | (() => Promise<T>),
  refreshInterval?: number
) {
  const [data, setData] = useState<T | null>(null);
  const [loading] = useState(!!endpointOrService);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async <U = T>(overrideEndpoint?: string): Promise<U> => {
    const targetEndpoint = overrideEndpoint || (typeof endpointOrService === 'string' ? endpointOrService : null);

    if (!targetEndpoint && typeof endpointOrService !== 'function') return undefined as U;

    try {
      let result: U;

      if (typeof targetEndpoint === 'string') {
        // Legacy endpoint string - map to service functions
        result = await mapEndpointToService<U>(targetEndpoint);
      } else if (endpointOrService && typeof endpointOrService === 'function') {
        // Service function
        result = await endpointOrService() as U;
      } else {
        return undefined as U;
      }

      if (!overrideEndpoint) {
        setData(result as unknown as T);
      }

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      if (!overrideEndpoint) {
        setError(errorMessage);
      }
      throw err;
    }
  };

  useEffect(() => {
    if (endpointOrService) {
      fetchData();

      if (refreshInterval) {
        const interval = setInterval(() => fetchData(), refreshInterval);
        return () => clearInterval(interval);
      }
    }
  }, [endpointOrService, refreshInterval]);

  const postData = async (endpoint: string, body?: any) => {
    // For backward compatibility - just return mock success
    console.log(`Mock POST to ${endpoint}`, body);
    await new Promise(resolve => setTimeout(resolve, 300));
    return { success: true };
  };

  return { data, loading, error, refetch: fetchData, fetchData, postData };
}

/**
 * Map legacy endpoint strings to service functions
 */
function mapEndpointToService<T>(endpoint: string): Promise<T> {
  switch (endpoint) {
    case "/api/metrics":
      return services.getDashboardMetrics() as Promise<T>;
    case "/api/threats/recent":
      return services.getRecentThreats() as Promise<T>;
    case "/api/threats/all":
      return services.getAllThreats() as Promise<T>;
    case "/api/threats/timeline":
      return services.getThreatTimeline() as Promise<T>;
    case "/api/health":
      return services.getSystemHealth() as Promise<T>;
    case "/api/alerts/active":
      return services.getActiveAlerts() as Promise<T>;
    case "/api/alerts/all":
      return services.getAllAlerts() as Promise<T>;
    case "/api/network/topology":
      return services.getNetworkTopology() as Promise<T>;
    case "/api/incidents":
      return services.getIncidents() as Promise<T>;
    case "/api/reports":
      return services.getReports() as Promise<T>;
    case "/api/honeypots":
      return services.getHoneypots() as Promise<T>;
    default:
      throw new Error(`Unknown endpoint: ${endpoint}`);
  }
}
