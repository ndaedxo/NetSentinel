const TOUR_STORAGE_KEY = 'netsentinel-onboarding-completed';

// Hook for manually triggering the tour
export function useOnboardingTour() {
  const startTour = () => {
    localStorage.removeItem(TOUR_STORAGE_KEY);
    // Tour will automatically start on next page load
    window.location.reload();
  };

  const resetTour = () => {
    localStorage.removeItem(TOUR_STORAGE_KEY);
  };

  return { startTour, resetTour };
}

export { TOUR_STORAGE_KEY };
