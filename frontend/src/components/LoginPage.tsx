import { BriefcaseBusiness, LockKeyhole, Mail, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import type { User } from "../types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function LoginPage({ onLogin }: { onLogin: (token: string, user: User) => void }) {
  const [email, setEmail] = useState("hameed@example.com");
  const [password, setPassword] = useState("jobscout2026");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      if (!response.ok) throw new Error("Invalid email or password");
      const data = await response.json() as { token: string; user: User };
      onLogin(data.token, data.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setLoading(false);
    }
  };

  return <main className="auth-shell"><section className="login-page page-surface"><div className="login-copy"><button className="brand login-brand" type="button"><span><BriefcaseBusiness size={20}/></span>Job<span>Scout</span></button><p className="overline"><Sparkles size={14}/> SMART JOB SEARCH</p><h1>Welcome back to your next <em>move.</em></h1><p>Sign in to manage saved roles, compare your resume, and continue your job search from one focused workspace.</p><div className="login-proof"><ShieldCheck size={18}/><span>Protected session for your local JobScout workspace</span></div></div><form className="login-card" onSubmit={submit}><p className="eyebrow">ACCOUNT ACCESS</p><h2>Sign in</h2><label><span>Email</span><div><Mail size={17}/><input value={email} onChange={event => setEmail(event.target.value)} type="email" autoComplete="email" required/></div></label><label><span>Password</span><div><LockKeyhole size={17}/><input value={password} onChange={event => setPassword(event.target.value)} type="password" autoComplete="current-password" required/></div></label>{error && <p className="form-error">{error}</p>}<button className="primary" disabled={loading}>{loading ? "Signing in..." : "Sign in"}</button><p className="login-hint">Default local credentials can be changed with backend environment variables.</p></form></section></main>;
}