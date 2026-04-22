import { useState } from "react";
import { Zap, Eye, EyeOff, AlertCircle } from "lucide-react";

interface LoginProps {
  onLogin: (name: string) => void;
}

const DEMO_CREDENTIALS = [
  { email: "animesh@pulsesignal.io", password: "demo1234", name: "Animesh" },
  { email: "demo@pulsesignal.io", password: "demo1234", name: "Demo User" },
];

export function Login({ onLogin }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    setTimeout(() => {
      const match = DEMO_CREDENTIALS.find(
        (c) => c.email === email.trim().toLowerCase() && c.password === password
      );
      if (match) {
        onLogin(match.name);
      } else {
        setError("Invalid email or password. Try demo@pulsesignal.io / demo1234");
      }
      setLoading(false);
    }, 700);
  }

  function handleDemoLogin() {
    setEmail("demo@pulsesignal.io");
    setPassword("demo1234");
    setError("");
  }

  return (
    <div className="min-h-screen bg-[#0f1117] flex items-center justify-center p-4">
      {/* Background glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-violet-900/10 blur-3xl pointer-events-none" />

      <div className="w-full max-w-sm relative animate-fade-in">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-9 h-9 rounded-xl bg-violet-600 flex items-center justify-center shadow-lg shadow-violet-900/40">
            <Zap size={18} className="text-white" />
          </div>
          <span className="text-xl font-semibold text-slate-100 tracking-tight">
            PulseSignal
          </span>
        </div>

        <div className="card p-6">
          <div className="mb-6">
            <h1 className="text-lg font-semibold text-slate-100">Sign in</h1>
            <p className="text-sm text-slate-500 mt-1">
              Welcome back. Enter your credentials to continue.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {/* Email */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-400">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30 transition-all"
              />
            </div>

            {/* Password */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-400">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-2.5 pr-10 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-start gap-2 bg-rose-900/20 border border-rose-800/40 rounded-xl px-3 py-2.5 text-xs text-rose-400 animate-fade-in">
                <AlertCircle size={13} className="shrink-0 mt-0.5" />
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary w-full justify-center mt-1 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-3.5 h-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  Signing in…
                </span>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          {/* Demo credentials hint */}
          <div className="mt-5 pt-4 border-t border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-600">
              Don't have an account?
            </span>
            <button
              type="button"
              onClick={handleDemoLogin}
              className="text-xs text-violet-400 hover:text-violet-300 transition-colors font-medium"
            >
              Use demo credentials
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-slate-700 mt-6">
          PulseSignal Feedback Intelligence · Demo environment
        </p>
      </div>
    </div>
  );
}
