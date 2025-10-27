import React, { useState } from 'react';
import { HelpCircle, Book, MessageCircle, ExternalLink, X, ChevronRight } from 'lucide-react';
import { useOnboardingTour } from './OnboardingTour';

interface HelpGuideProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function HelpGuide({ isOpen, onClose }: HelpGuideProps) {
  const { startTour, resetTour } = useOnboardingTour();
  const [activeSection, setActiveSection] = useState<'getting-started' | 'features' | 'troubleshooting'>('getting-started');

  if (!isOpen) return null;

  const handleRestartTour = () => {
    resetTour();
    startTour();
    onClose();
  };

  const sections = {
    'getting-started': {
      title: 'Getting Started',
      content: (
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold text-slate-200 mb-2">Welcome to Netsentinel</h4>
            <p className="text-slate-400 text-sm mb-3">
              Netsentinel is your comprehensive security operations center for monitoring and responding to network threats.
            </p>
          </div>

          <div>
            <h5 className="font-medium text-slate-300 mb-2">Quick Start Guide</h5>
            <ol className="list-decimal list-inside space-y-1 text-sm text-slate-400">
              <li>Log in using any email/password combination</li>
              <li>Explore the dashboard for security metrics</li>
              <li>Check active threats and alerts</li>
              <li>Monitor system health and network activity</li>
            </ol>
          </div>

          <div>
            <h5 className="font-medium text-slate-300 mb-2">Navigation</h5>
            <ul className="space-y-1 text-sm text-slate-400">
              <li><strong>Dashboard:</strong> Overview of security metrics and alerts</li>
              <li><strong>Threats:</strong> Detailed threat intelligence and analysis</li>
              <li><strong>Alerts:</strong> Active security alerts and management</li>
              <li><strong>Network:</strong> Network topology and analysis</li>
              <li><strong>Incidents:</strong> Incident response and tracking</li>
            </ul>
          </div>
        </div>
      ),
    },
    'features': {
      title: 'Features & Capabilities',
      content: (
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold text-slate-200 mb-2">Core Features</h4>
            <div className="grid gap-3">
              <div className="p-3 bg-slate-800/50 rounded-lg">
                <h5 className="font-medium text-slate-300 text-sm">Real-time Threat Monitoring</h5>
                <p className="text-slate-500 text-xs mt-1">Continuous monitoring of network traffic and security events</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-lg">
                <h5 className="font-medium text-slate-300 text-sm">Alert Management</h5>
                <p className="text-slate-500 text-xs mt-1">Comprehensive alert system with filtering and escalation</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-lg">
                <h5 className="font-medium text-slate-300 text-sm">Network Analysis</h5>
                <p className="text-slate-500 text-xs mt-1">Deep packet inspection and network topology visualization</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-lg">
                <h5 className="font-medium text-slate-300 text-sm">Incident Response</h5>
                <p className="text-slate-500 text-xs mt-1">Structured incident response workflows and tracking</p>
              </div>
            </div>
          </div>
        </div>
      ),
    },
    'troubleshooting': {
      title: 'Troubleshooting',
      content: (
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold text-slate-200 mb-2">Common Issues</h4>
            <div className="space-y-3">
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <h5 className="font-medium text-red-300 text-sm">Login Issues</h5>
                <p className="text-slate-400 text-xs mt-1">
                  Try any email/password combination. This is a demo application.
                </p>
              </div>
              <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <h5 className="font-medium text-yellow-300 text-sm">Slow Loading</h5>
                <p className="text-slate-400 text-xs mt-1">
                  Check your internet connection. Data is simulated and may take a moment to load.
                </p>
              </div>
              <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <h5 className="font-medium text-blue-300 text-sm">Missing Features</h5>
                <p className="text-slate-400 text-xs mt-1">
                  This is a demo application. Some features may be simulated or limited.
                </p>
              </div>
            </div>
          </div>

          <div>
            <h5 className="font-medium text-slate-300 mb-2">Support</h5>
            <p className="text-slate-400 text-sm">
              For technical support or questions, please contact the development team.
            </p>
          </div>
        </div>
      ),
    },
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div className="flex h-full">
          {/* Sidebar */}
          <div className="w-64 bg-slate-800/50 border-r border-slate-700 p-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-slate-200">Help & Guide</h2>
              <button
                onClick={onClose}
                className="p-1 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <nav className="space-y-2">
              {Object.entries(sections).map(([key, section]) => (
                <button
                  key={key}
                  onClick={() => setActiveSection(key as keyof typeof sections)}
                  className={`w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center space-x-2 ${
                    activeSection === key
                      ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                      : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700/50'
                  }`}
                >
                  <ChevronRight className={`w-4 h-4 transition-transform ${activeSection === key ? 'rotate-90' : ''}`} />
                  <span className="text-sm">{section.title}</span>
                </button>
              ))}
            </nav>

            <div className="mt-6 pt-4 border-t border-slate-700">
              <button
                onClick={handleRestartTour}
                className="w-full flex items-center space-x-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors text-sm"
              >
                <Book className="w-4 h-4" />
                <span>Take Tour Again</span>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 p-6 overflow-y-auto">
            <div className="max-w-2xl">
              {sections[activeSection].content}

              <div className="mt-8 pt-6 border-t border-slate-700">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2 text-slate-400">
                    <MessageCircle className="w-4 h-4" />
                    <span className="text-sm">Need more help?</span>
                  </div>
                  <a
                    href="mailto:support@netsentinel.com"
                    className="flex items-center space-x-1 text-blue-400 hover:text-blue-300 text-sm"
                  >
                    <span>Contact Support</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Help button component for the header
export function HelpButton() {
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setIsHelpOpen(true)}
        className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
        title="Help & Documentation"
      >
        <HelpCircle className="w-5 h-5 text-slate-400" />
      </button>

      <HelpGuide
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
      />
    </>
  );
}
