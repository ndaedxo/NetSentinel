import { useRef } from 'react';

/**
 * Hook for performance monitoring functionality
 */
export function usePerformanceMonitor() {
  const renderTimeRef = useRef<number[]>([]);
  const renderCountRef = useRef(0);

  const recordRenderTime = (startTime: number) => {
    const renderTime = performance.now() - startTime;
    if (renderTimeRef.current) {
      renderTimeRef.current.push(renderTime);

      if (renderTimeRef.current.length > 100) {
        renderTimeRef.current = renderTimeRef.current.slice(-100);
      }

      if (renderCountRef.current !== undefined) {
        renderCountRef.current++;
      }
    }
  };

  const getAverageRenderTime = () => {
    const renderTimes = renderTimeRef.current || [];
    if (renderTimes.length === 0) return 0;
    return renderTimes.reduce((sum: number, time: number) => sum + time, 0) / renderTimes.length;
  };

  const getRenderCount = () => renderCountRef.current;

  return {
    recordRenderTime,
    getAverageRenderTime,
    getRenderCount
  };
}
