import { describe, it, expect } from '@jest/globals';
import { renderHook } from '@testing-library/react';
import { useThreatData, useAlertData, useSystemHealthData } from '../useWidgetData';

describe('useWidgetData', () => {
  describe('useThreatData', () => {
    it('returns mock threat data', () => {
      const { result } = renderHook(() => useThreatData());

      expect(Array.isArray(result.current)).toBe(true);
      expect(result.current.length).toBeGreaterThan(0);

      const threat = result.current[0];
      expect(threat).toHaveProperty('id');
      expect(threat).toHaveProperty('ip_address');
      expect(threat).toHaveProperty('threat_score');
      expect(threat).toHaveProperty('severity');
      expect(threat).toHaveProperty('threat_type');
      expect(threat).toHaveProperty('created_at');
    });

    it('returns the same data on multiple calls (memoized)', () => {
      const { result: result1 } = renderHook(() => useThreatData());
      const { result: result2 } = renderHook(() => useThreatData());

      expect(result1.current).toEqual(result2.current);
    });
  });

  describe('useAlertData', () => {
    it('returns mock alert data', () => {
      const { result } = renderHook(() => useAlertData());

      expect(Array.isArray(result.current)).toBe(true);
      expect(result.current.length).toBeGreaterThan(0);

      const alert = result.current[0];
      expect(alert).toHaveProperty('id');
      expect(alert).toHaveProperty('title');
      expect(alert).toHaveProperty('severity');
      expect(alert).toHaveProperty('status');
      expect(alert).toHaveProperty('created_at');
    });
  });

  describe('useSystemHealthData', () => {
    it('returns mock system health data', () => {
      const { result } = renderHook(() => useSystemHealthData());

      expect(result.current).toHaveProperty('services');
      expect(Array.isArray(result.current.services)).toBe(true);
      expect(result.current.services.length).toBeGreaterThan(0);

      const service = result.current.services[0];
      expect(service).toHaveProperty('id');
      expect(service).toHaveProperty('name');
      expect(service).toHaveProperty('status');
      expect(service).toHaveProperty('uptime');
      expect(service).toHaveProperty('response_time');
    });
  });
});
