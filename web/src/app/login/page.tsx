"use client";

import { motion } from "framer-motion";
import { ArrowRight, Loader2, Lock, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { endpoints } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/errors";
import { getSession, setSession } from "@/lib/auth/session";
import { API_BASE_URL } from "@/lib/api/config";
import { Button } from "@/components/ui/button";
import { FieldLabel, Input } from "@/components/ui/field";
import { VaynexMark } from "@/components/shell/logo";
import { Dot } from "@/components/ui/badge";
import { useQuery } from "@tanstack/react-query";

/** Development-only seed accounts from the backend README (scripts/seed_demo.py). */
const DEMO_ACCOUNTS = [
  { role: "OPERATOR", email: "operator@vaynex.local", password: "VaynexOperator!2026" },
  { role: "ADMIN", email: "admin@vaynex.local", password: "VaynexAdmin!2026" },
  { role: "VIEWER", email: "viewer@vaynex.local", password: "VaynexViewer!2026" },
];

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginScreen />
    </Suspense>
  );
}

function LoginScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const expired = params.get("expired") === "1";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ title: string; message: string } | null>(
    expired ? { title: "AUTHENTICATION EXPIRED", message: "Your session has ended. Sign in again." } : null,
  );

  const health = useQuery({ queryKey: ["health", "login"], queryFn: endpoints.health, retry: 0, refetchInterval: 10_000 });

  useEffect(() => {
    if (getSession()) router.replace("/command");
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const tok = await endpoints.login({ email: email.trim(), password });
      setSession({ token: tok.access_token, expiresAt: Date.now() + tok.expires_in * 1000, user: tok.user });
      // Confirm the JWT with GET /auth/me before entering.
      const me = await endpoints.me();
      setSession({ token: tok.access_token, expiresAt: Date.now() + tok.expires_in * 1000, user: me });
      router.replace("/command");
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : null;
      if (apiErr?.kind === "network") {
        setError({ title: "BACKEND UNAVAILABLE", message: `Cannot reach the Vaynex API at ${API_BASE_URL}.` });
      } else if (apiErr?.status === 401) {
        setError({ title: "ACCESS DENIED", message: "Invalid email or password." });
      } else if (apiErr?.kind === "validation") {
        setError({ title: "INVALID INPUT", message: apiErr.humanMessage });
      } else {
        setError({ title: "SIGN-IN FAILED", message: apiErr?.humanMessage ?? "Unexpected error." });
      }
      setLoading(false);
    }
  }

  const online = health.isSuccess;

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-bg bg-grid px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(34,211,238,0.08),transparent_60%)]" />
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-[420px] border border-line bg-panel/95"
      >
        <span className="absolute -left-px -top-px h-3 w-3 border-l border-t border-cyan" />
        <span className="absolute -bottom-px -right-px h-3 w-3 border-b border-r border-cyan" />
        <div className="border-b border-line px-6 pb-5 pt-7 text-center">
          <VaynexMark className="mx-auto h-11 w-11" />
          <h1 className="mt-4 font-mono text-xl font-semibold tracking-[0.42em] text-ink">VAYNEX</h1>
          <p className="mt-1.5 font-mono text-2xs tracking-[0.3em] text-cyan/80">AI RESILIENCE OS</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4 px-6 py-6">
          <div className="flex items-center justify-between">
            <span className="label flex items-center gap-2 text-ink/80">
              <Lock className="h-3 w-3 text-cyan" /> OPERATOR ACCESS
            </span>
            <span className="flex items-center gap-1.5 font-mono text-2xs text-muted">
              <Dot tone={health.isLoading ? "neutral" : online ? "ok" : "crit"} pulse={!online && !health.isLoading} />
              {health.isLoading ? "CHECKING API" : online ? "API ONLINE" : "API OFFLINE"}
            </span>
          </div>
          <div>
            <FieldLabel htmlFor="email">EMAIL</FieldLabel>
            <Input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="operator@vaynex.local"
            />
          </div>
          <div>
            <FieldLabel htmlFor="password">PASSWORD</FieldLabel>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
            />
          </div>
          {error && (
            <div role="alert" className="border border-red/40 bg-red-soft/40 px-3 py-2">
              <p className="font-mono text-2xs tracking-widest text-red">{error.title}</p>
              <p className="mt-0.5 text-xs text-ink/80">{error.message}</p>
            </div>
          )}
          <Button type="submit" variant="solid" size="lg" className="w-full" disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> AUTHENTICATING
              </>
            ) : (
              <>
                SIGN IN <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
          {process.env.NODE_ENV === "development" && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="label mr-1 text-[9px]">DEV SEED</span>
              {DEMO_ACCOUNTS.map((a) => (
                <button
                  key={a.role}
                  type="button"
                  onClick={() => {
                    setEmail(a.email);
                    setPassword(a.password);
                  }}
                  className="border border-line px-1.5 py-0.5 font-mono text-2xs text-muted hover:border-cyan/50 hover:text-cyan"
                >
                  {a.role}
                </button>
              ))}
            </div>
          )}
          <p className="flex items-start gap-2 text-2xs leading-relaxed text-dim">
            <ShieldCheck className="mt-0.5 h-3 w-3 shrink-0 text-cyan/60" />
            Advisory decision-support system. Vaynex never controls physical infrastructure; every action requires an
            authorized human operator and is audited.
          </p>
        </form>
      </motion.div>
    </main>
  );
}
