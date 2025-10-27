import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Shield, CheckCircle } from "lucide-react";
import { useAuth } from "@/hooks";

export default function AuthCallback() {
  const { exchangeCodeForSessionToken } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const code = searchParams.get('code');
  const error = searchParams.get('error');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        if (error) {
          console.error("OAuth error:", error);
          navigate("/login?error=oauth_failed");
          return;
        }

        if (code) {
          await exchangeCodeForSessionToken(code);
          navigate("/");
        } else {
          // Mock OAuth flow - simulate success
          await exchangeCodeForSessionToken("mock-auth-code");
          navigate("/");
        }
      } catch (err) {
        console.error("Auth callback error:", err);
        navigate("/login?error=auth_failed");
      }
    };

    handleCallback();
  }, [code, error, exchangeCodeForSessionToken, navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="flex flex-col items-center space-y-6">
        <div className="relative">
          <div className="absolute inset-0 bg-blue-500 blur-xl opacity-50 animate-pulse"></div>
          <Shield className="relative w-16 h-16 text-blue-400" strokeWidth={1.5} />
        </div>

        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-gradient">Netsentinel</h1>
          <p className="text-slate-400">Completing authentication...</p>
        </div>

        <div className="flex flex-col items-center space-y-4">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <div className="text-center space-y-2">
            <p className="text-sm text-slate-300">Verifying credentials</p>
            <p className="text-xs text-slate-500">This may take a few moments</p>
          </div>
        </div>

        <div className="card-dark p-6 max-w-sm">
          <div className="flex items-center space-x-3">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <div>
              <p className="text-sm font-medium text-slate-300">Secure Connection</p>
              <p className="text-xs text-slate-500">OAuth 2.0 flow in progress</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
