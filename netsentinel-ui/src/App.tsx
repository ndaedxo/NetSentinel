import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router";
import { Suspense, lazy } from "react";
import { AuthProvider, useAuth } from "@/hooks";
import { ToastProvider } from "@/hooks/useToast";
import { ErrorBoundary, LoadingSpinner } from "@/components";
import OnboardingTour from "@/components/OnboardingTour";

// Lazy load page components for code splitting
const LoginPage = lazy(() => import("@/pages/Login"));
const AuthCallbackPage = lazy(() => import("@/pages/AuthCallback"));
const DashboardPage = lazy(() => import("@/pages/Dashboard"));
const ThreatIntelligencePage = lazy(() => import("@/pages/ThreatIntelligence"));
const HoneypotManagementPage = lazy(() => import("@/pages/HoneypotManagement"));
const MLMonitoringPage = lazy(() => import("@/pages/MLMonitoring"));
const AlertManagementPage = lazy(() => import("@/pages/AlertManagement"));
const NetworkAnalysisPage = lazy(() => import("@/pages/NetworkAnalysis"));
const IncidentResponsePage = lazy(() => import("@/pages/IncidentResponse"));
const ReportsPage = lazy(() => import("@/pages/Reports"));
const ProfilePage = lazy(() => import("@/pages/Profile"));
const NotificationsPage = lazy(() => import("@/pages/Notifications"));
const NotificationSettingsPage = lazy(() => import("@/pages/NotificationSettings"));
const ApiKeysPage = lazy(() => import("@/pages/ApiKeys"));
const CorrelationPage = lazy(() => import("@/pages/Correlation"));
const LogViewerPage = lazy(() => import("@/pages/LogViewer"));

// Loading component for Suspense fallback
function PageLoader() {
  return <LoadingSpinner message="Loading page..." />;
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isPending } = useAuth();

  if (isPending) {
    return <LoadingSpinner message="Authenticating..." />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/threats" element={<ProtectedRoute><ThreatIntelligencePage /></ProtectedRoute>} />
      <Route path="/honeypots" element={<ProtectedRoute><HoneypotManagementPage /></ProtectedRoute>} />
      <Route path="/ml-models" element={<ProtectedRoute><MLMonitoringPage /></ProtectedRoute>} />
      <Route path="/alerts" element={<ProtectedRoute><AlertManagementPage /></ProtectedRoute>} />
      <Route path="/network" element={<ProtectedRoute><NetworkAnalysisPage /></ProtectedRoute>} />
      <Route path="/incidents" element={<ProtectedRoute><IncidentResponsePage /></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
      <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
      <Route path="/notifications" element={<ProtectedRoute><NotificationsPage /></ProtectedRoute>} />
      <Route path="/settings/notifications" element={<ProtectedRoute><NotificationSettingsPage /></ProtectedRoute>} />
      <Route path="/settings/api-keys" element={<ProtectedRoute><ApiKeysPage /></ProtectedRoute>} />
      <Route path="/correlation" element={<ProtectedRoute><CorrelationPage /></ProtectedRoute>} />
      <Route path="/logs" element={<ProtectedRoute><LogViewerPage /></ProtectedRoute>} />
    </Routes>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <Router>
            <Suspense fallback={<PageLoader />}>
              <AppRoutes />
              <OnboardingTour />
            </Suspense>
          </Router>
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}
