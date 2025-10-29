import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { Shield, AlertTriangle, Mail, Key, LogIn } from "lucide-react";
import { useAuth } from "@/hooks";

export default function Login() {
  const { user, login, redirectToLogin, isPending } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (user) {
      navigate("/");
    }
  }, [user, navigate]);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      console.error('Login error:', err);
      setError("Invalid credentials. Try any email/password combination.");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.1),transparent_50%)]"></div>

      <div className="relative z-10 w-full max-w-md">
        <div className="card-dark p-8 space-y-8 shadow-2xl">
          <div className="text-center space-y-4">
            <div className="flex justify-center">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-500 blur-xl opacity-50 animate-pulse"></div>
                <Shield className="relative w-16 h-16 text-blue-400" strokeWidth={1.5} />
              </div>
            </div>

            <div>
              <h1 className="text-3xl font-bold text-gradient">Netsentinel</h1>
              <p className="text-slate-400 mt-2">Enterprise Network Security Platform</p>
            </div>
          </div>

          <form onSubmit={handleEmailLogin} className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center space-x-3 p-4 bg-slate-900/50 rounded-lg border border-slate-700/50">
                <Mail className="w-5 h-5 text-blue-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email address"
                  className="flex-1 bg-transparent text-slate-300 placeholder-slate-500 focus:outline-none"
                  required
                />
              </div>

              <div className="flex items-center space-x-3 p-4 bg-slate-900/50 rounded-lg border border-slate-700/50">
                <Key className="w-5 h-5 text-blue-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  className="flex-1 bg-transparent text-slate-300 placeholder-slate-500 focus:outline-none"
                  required
                />
              </div>

              {error && (
                <div className="text-red-400 text-sm text-center">
                  {error}
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={isPending}
              className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-200 transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-blue-500/50 flex items-center justify-center space-x-2"
            >
              <LogIn className="w-4 h-4" />
              <span>{isPending ? "Signing in..." : "Sign In"}</span>
            </button>
          </form>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-slate-900 text-slate-400">or</span>
            </div>
          </div>

          <button
            onClick={redirectToLogin}
            disabled={isPending}
            className="w-full bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-semibold py-3 px-6 rounded-lg transition-all duration-200 border border-slate-600 hover:border-slate-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Continue with Google OAuth
          </button>

          <div className="flex items-start space-x-3 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-amber-200 font-medium">Demo Mode</p>
              <p className="text-xs text-amber-300/80 mt-1">
                This is a demo application. Use any email/password combination to sign in, or try OAuth for the full experience.
              </p>
            </div>
          </div>

          <div className="text-center text-xs text-slate-500">
            <p>Netsentinel v1.0 | © 2025</p>
          </div>
        </div>
      </div>
    </div>
  );
}
