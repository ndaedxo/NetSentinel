import { useState, useEffect } from 'react';
import Joyride, { CallBackProps, STATUS, EVENTS, Step } from 'react-joyride';
import { useAuth } from '@/hooks';
import { TOUR_STORAGE_KEY } from '@/hooks/useOnboardingTour';

interface OnboardingTourProps {
  run?: boolean;
  onComplete?: () => void;
}


// Helper function to detect test environment
const isTestEnvironment = () => {
  return typeof window !== 'undefined' &&
         (window.navigator.webdriver === true ||
          typeof (window as Window & { __playwright?: unknown }).__playwright !== 'undefined' ||
          process.env.NODE_ENV === 'test' ||
          typeof jest !== 'undefined');
};

export default function OnboardingTour({ run = false, onComplete }: OnboardingTourProps) {
  const { user } = useAuth();
  const [isTourActive, setIsTourActive] = useState(false);
  const [steps] = useState<Step[]>([
    {
      target: 'body',
      content: (
        <div className="text-center">
          <h3 className="text-lg font-semibold text-slate-100 mb-2">Welcome to Netsentinel! 🎉</h3>
          <p className="text-slate-300">
            Let's take a quick tour to help you get familiar with the security operations center.
          </p>
        </div>
      ),
      placement: 'center',
      disableBeacon: true,
    },
    {
      target: '[data-tour="dashboard"]',
      content: (
        <div>
          <h4 className="font-semibold text-slate-100 mb-2">Dashboard Overview</h4>
          <p className="text-slate-300 text-sm">
            This is your main dashboard showing key security metrics, active threats, and system health at a glance.
          </p>
        </div>
      ),
      placement: 'bottom',
    },
    {
      target: '[data-tour="navigation"]',
      content: (
        <div>
          <h4 className="font-semibold text-slate-100 mb-2">Navigation Menu</h4>
          <p className="text-slate-300 text-sm">
            Use this menu to navigate between different sections: Threats, Network, Incidents, Honeypots, ML Models, Alerts, and Reports.
          </p>
        </div>
      ),
      placement: 'right',
    },
    {
      target: '[data-tour="threats"]',
      content: (
        <div>
          <h4 className="font-semibold text-slate-100 mb-2">Threat Intelligence</h4>
          <p className="text-slate-300 text-sm">
            Monitor and analyze security threats with detailed intelligence and timeline views.
          </p>
        </div>
      ),
      placement: 'bottom',
    },
    {
      target: '[data-tour="alerts"]',
      content: (
        <div>
          <h4 className="font-semibold text-slate-100 mb-2">Alert Management</h4>
          <p className="text-slate-300 text-sm">
            Manage and respond to security alerts with filtering, acknowledgment, and escalation features.
          </p>
        </div>
      ),
      placement: 'bottom',
    },
    {
      target: '[data-tour="user-menu"]',
      content: (
        <div>
          <h4 className="font-semibold text-slate-100 mb-2">User Profile</h4>
          <p className="text-slate-300 text-sm">
            Access your profile settings and sign out from here. Your user information and role are displayed for quick reference.
          </p>
        </div>
      ),
      placement: 'bottom-end',
    },
    {
      target: 'body',
      content: (
        <div className="text-center">
          <h3 className="text-lg font-semibold text-slate-100 mb-2">You're all set! 🚀</h3>
          <p className="text-slate-300">
            You can always access help and documentation from the header menu. Happy securing!
          </p>
        </div>
      ),
      placement: 'center',
    },
  ]);

  // Check if user has completed onboarding
  useEffect(() => {
    if (user && !run) {
      const hasCompleted = localStorage.getItem(TOUR_STORAGE_KEY);
      // Don't show tour automatically in test environment or if already completed
      if (!hasCompleted && !isTestEnvironment()) {
        // Show tour for first-time users after a short delay
        const timer = setTimeout(() => {
          setIsTourActive(true);
        }, 2000);
        return () => clearTimeout(timer);
      }
    } else if (run) {
      setIsTourActive(true);
    }
  }, [user, run]);

  const handleJoyrideCallback = (data: CallBackProps) => {
    const { status, type } = data;

    if (type === EVENTS.STEP_AFTER || type === EVENTS.TARGET_NOT_FOUND) {
      // Update step index here if needed
    }

    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      // Mark tour as completed
      localStorage.setItem(TOUR_STORAGE_KEY, 'true');
      setIsTourActive(false);

      if (onComplete) {
        onComplete();
      }
    }
  };

  if (!user || !isTourActive) {
    return null;
  }

  return (
    <Joyride
      steps={steps}
      run={isTourActive}
      continuous
      showSkipButton
      showProgress
      disableOverlayClose
      disableCloseOnEsc
      callback={handleJoyrideCallback}
      styles={{
        options: {
          primaryColor: '#3b82f6', // blue-500
          backgroundColor: '#1e293b', // slate-800
          textColor: '#e2e8f0', // slate-200
          overlayColor: 'rgba(15, 23, 42, 0.8)', // slate-900 with opacity
          spotlightShadow: '0 0 15px rgba(59, 130, 246, 0.5)',
        },
        tooltip: {
          backgroundColor: '#1e293b',
          borderRadius: '8px',
          fontSize: '14px',
        },
        tooltipContent: {
          padding: '16px',
        },
        buttonNext: {
          backgroundColor: '#3b82f6',
          fontSize: '13px',
          fontWeight: '600',
        },
        buttonBack: {
          color: '#64748b',
          fontSize: '13px',
        },
        buttonSkip: {
          color: '#64748b',
          fontSize: '13px',
        },
        buttonClose: {
          display: 'none', // Hide close button to force completion
        },
      }}
      floaterProps={{
        disableAnimation: true,
      }}
    />
  );
}

