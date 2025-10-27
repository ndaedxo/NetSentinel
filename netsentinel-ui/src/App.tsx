import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router";
import { Suspense, lazy } from "react";
import { AuthProvider, useAuth } from "@/hooks";
import { ErrorBoundary } from "@/components/ErrorBoundary";
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

// Loading component for Suspense fallback
function PageLoader() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
      <div className="flex flex-col items-center space-y-4">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-slate-400">Loading...</p>
      </div>
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isPending } = useAuth();

  if (isPending) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-400">Loading...</p>
        </div>
      </div>
    );
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
    </Routes>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
          <Suspense fallback={<PageLoader />}>
            <AppRoutes />
            <OnboardingTour />
          </Suspense>
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}
