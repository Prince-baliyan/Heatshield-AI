import { useEffect, useState, type FormEvent } from "react";
import { ApiError, register } from "../services/api";
import { useAuth } from "./AuthContext";
import { Button, Card } from "../components/ui";

function errorText(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return error instanceof Error
      ? error.message
      : "The request could not be completed.";
  }
  if (error.details && typeof error.details === "object") {
    const details = Object.values(error.details as Record<string, unknown>)
      .flatMap((value) => (Array.isArray(value) ? value : [value]))
      .filter((value): value is string => typeof value === "string");
    if (details.length > 0) return details.join(" ");
  }
  return error.message;
}

function destinationAfterLogin() {
  const next = new URLSearchParams(window.location.search).get("next");
  return next &&
    (next === "/app" || next.startsWith("/app/")) &&
    !next.startsWith("//")
    ? next
    : "/app";
}

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { login, state } = useAuth();
  const isRegistration = mode === "register";
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (mode === "login" && state.status === "ready" && state.user) {
      window.location.replace("/app");
    }
  }, [mode, state]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      if (isRegistration) {
        await register(username.trim(), email.trim(), password, confirmPassword);
        setSuccess("Account created. Sign in with your new account to continue.");
        setPassword("");
        setConfirmPassword("");
      } else {
        await login(username.trim(), password);
        window.location.replace(destinationAfterLogin());
      }
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="hs-page py-16 sm:py-24">
      <div className="mx-auto max-w-lg">
        <p className="hs-eyebrow">{isRegistration ? "Create account" : "Account access"}</p>
        <h1 className="hs-display mt-3 text-3xl font-bold text-slate-50 sm:text-4xl">
          {isRegistration ? "Get started with HeatShield-AI" : "Sign in"}
        </h1>
        <p className="mt-4 leading-7 text-slate-400">
          Sign-in uses a Django session cookie. Your password is submitted only
          to the backend and is never saved in browser storage.
        </p>
        <Card className="mt-8 p-6 sm:p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <label className="block text-sm font-medium text-slate-300">
              Username
              <input
                autoComplete="username"
                required
                maxLength={150}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"
              />
            </label>
            {isRegistration && (
              <label className="block text-sm font-medium text-slate-300">
                Email
                <input
                  type="email"
                  autoComplete="email"
                  required
                  maxLength={254}
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"
                />
              </label>
            )}
            <label className="block text-sm font-medium text-slate-300">
              Password
              <input
                type="password"
                autoComplete={isRegistration ? "new-password" : "current-password"}
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"
              />
            </label>
            {isRegistration && (
              <label className="block text-sm font-medium text-slate-300">
                Confirm password
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"
                />
              </label>
            )}
            {error && (
              <p role="alert" className="text-sm leading-6 text-red-200">
                {error}
              </p>
            )}
            {success && (
              <p role="status" className="text-sm leading-6 text-emerald-200">
                {success}
              </p>
            )}
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting
                ? isRegistration
                  ? "Creating account…"
                  : "Signing in…"
                : isRegistration
                  ? "Create account"
                  : "Sign in"}
            </Button>
          </form>
          <p className="mt-6 text-sm text-slate-400">
            {isRegistration ? "Already registered?" : "Need an account?"}{" "}
            <a
              href={isRegistration ? "/login" : "/register"}
              className="font-semibold text-cyan-200 hover:text-white"
            >
              {isRegistration ? "Sign in" : "Create one"}
            </a>
          </p>
        </Card>
      </div>
    </section>
  );
}
