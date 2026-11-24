import { useEffect, type ReactNode } from "react";
import { AuthPage } from "./auth/AuthPage";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { AppShell } from "./app/AppShell";
import { AssessmentCreatePage } from "./app/AssessmentCreatePage";
import {
  AreaComparisonPage,
  AssessmentDetailPage,
  AssessmentHistoryPage,
  DataSourcesPage,
  DatasetsPage,
  DashboardOverview,
  LocationsPage,
  ObservationsPage,
  ProfilePage,
  RecommendationsPage,
} from "./app/AppPages";
import { ErrorPanel, LoadingPanel } from "./app/AppUI";
import { PlatformShell } from "./components/layout";
import {
  AboutSection,
  CapabilitiesSection,
  HeroSection,
  HowItWorksSection,
  MethodologySection,
} from "./components/sections";

function normalizedPath() {
  return window.location.pathname.replace(/\/+$/, "") || "/";
}

function PublicLandingPage() {
  return (
    <PlatformShell>
      <HeroSection />
      <AboutSection />
      <CapabilitiesSection />
      <HowItWorksSection />
      <MethodologySection />
    </PlatformShell>
  );
}

function ProtectedApplication({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  const path = `${normalizedPath()}${window.location.search}`;

  useEffect(() => {
    if (state.status === "ready" && !state.user) {
      window.location.replace(`/login?next=${encodeURIComponent(path)}`);
    }
  }, [path, state]);

  if (state.status === "loading") {
    return <LoadingPanel label="Restoring your secure session…" />;
  }
  if (state.status === "error") {
    return (
      <main className="mx-auto max-w-2xl px-5 py-16">
        <h1 className="mb-5 text-2xl font-bold text-white">Session unavailable</h1>
        <ErrorPanel error={state.message} />
        <p className="mt-4 text-sm text-slate-400">
          Check the backend connection, then reload to restore your session.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-4 rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-200"
        >
          Reload
        </button>
      </main>
    );
  }
  if (!state.user) {
    return <LoadingPanel label="Redirecting to sign in…" />;
  }
  return <>{children}</>;
}

function ApplicationRoutes({ path }: { path: string }) {
  const detailMatch = path.match(/^\/app\/assessments\/([^/]+)$/);
  let page: ReactNode;

  if (path === "/app" || path === "/app/") {
    page = <DashboardOverview />;
  } else if (path === "/app/assessments/new") {
    page = <AssessmentCreatePage />;
  } else if (path === "/app/assessments") {
    page = <AssessmentHistoryPage />;
  } else if (detailMatch) {
    page = <AssessmentDetailPage id={detailMatch[1]} />;
  } else if (path === "/app/recommendations") {
    page = <RecommendationsPage />;
  } else if (path === "/app/locations") {
    page = <LocationsPage />;
  } else if (path === "/app/compare") {
    page = <AreaComparisonPage />;
  } else if (path === "/app/data-sources") {
    page = <DataSourcesPage />;
  } else if (path === "/app/datasets") {
    page = <DatasetsPage />;
  } else if (path === "/app/observations") {
    page = <ObservationsPage />;
  } else if (path === "/app/profile") {
    page = <ProfilePage />;
  } else {
    page = (
      <div className="rounded-2xl border border-white/10 p-8 text-center">
        <h2 className="text-xl font-semibold text-white">Page not found</h2>
        <p className="mt-2 text-sm text-slate-400">This application route does not exist.</p>
        <a href="/app" className="mt-5 inline-block text-sm text-cyan-200 hover:text-white">Return to overview</a>
      </div>
    );
  }

  return (
    <ProtectedApplication>
      <AppShell path={path}>{page}</AppShell>
    </ProtectedApplication>
  );
}

function AppContent() {
  const path = normalizedPath();
  if (path === "/app" || path.startsWith("/app/")) {
    return <ApplicationRoutes path={path} />;
  }
  if (path === "/login" || path === "/register") {
    return (
      <PlatformShell>
        <AuthPage mode={path === "/register" ? "register" : "login"} />
      </PlatformShell>
    );
  }
  if (path === "/") {
    return <PublicLandingPage />;
  }
  return (
    <main className="mx-auto max-w-2xl px-5 py-16 text-center">
      <h1 className="text-2xl font-bold text-white">Page not found</h1>
      <a href="/" className="mt-4 inline-block text-cyan-200 hover:text-white">Return to HeatShield-AI</a>
    </main>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
