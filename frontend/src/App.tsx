import { useEffect, useState, useSyncExternalStore } from "react";
import { logout, type AuthResult } from "./api";
import { useRoute } from "./lib/route";
import { WorkspaceProvider } from "./lib/store";
import { clearSession, loadSession, saveSession } from "./session";
import ForgotPassword from "./ForgotPassword";
import Landing from "./Landing";
import Legal, { readLegalPage, type LegalPage } from "./Legal";
import Login from "./Login";
import ResetPassword from "./ResetPassword";
import SignUp from "./SignUp";
import Dashboard, { Applications, Jobs, MyCVs, Settings } from "./pages/Dashboard";
import Tailor from "./pages/Tailor";
import AppShell from "./ui/AppShell";

type Mode = "landing" | "login" | "signup" | "forgot";

// The emailed link is <site>/?reset_token=... (read-only here: StrictMode runs initialisers twice).
const readResetToken = () => new URLSearchParams(window.location.search).get("reset_token");

function clearResetTokenFromUrl() {
  const url = new URL(window.location.href);
  url.searchParams.delete("reset_token");
  window.history.replaceState(null, "", url.pathname + url.search + url.hash);
}

function Workspace({ session, onSignOut }: { session: AuthResult; onSignOut: () => void }) {
  const route = useRoute();
  const email = session.user.email;
  return (
    <WorkspaceProvider userId={session.user.id}>
      <AppShell route={route} email={email} onSignOut={onSignOut}>
        {route === "dashboard" && <Dashboard email={email} />}
        {route === "tailor" && <Tailor />}
        {route === "applications" && <Applications />}
        {route === "cvs" && <MyCVs />}
        {route === "jobs" && <Jobs />}
        {route === "settings" && <Settings email={email} onSignOut={onSignOut} />}
      </AppShell>
    </WorkspaceProvider>
  );
}

const subscribeHash = (cb: () => void) => {
  window.addEventListener("hashchange", cb);
  return () => window.removeEventListener("hashchange", cb);
};

export default function App() {
  const legal: LegalPage | null = useSyncExternalStore(subscribeHash, readLegalPage);
  const [session, setSession] = useState<AuthResult | null>(loadSession);
  const [mode, setMode] = useState<Mode>("landing");
  const [resetToken, setResetToken] = useState<string | null>(readResetToken);

  // Keep the token out of the address bar and browser history once it's in memory.
  useEffect(() => { if (resetToken) clearResetTokenFromUrl(); }, [resetToken]);

  const start = (r: AuthResult) => { saveSession(r); setSession(r); };

  if (legal) return <Legal page={legal} />;

  if (resetToken) {
    return <ResetPassword token={resetToken} onDone={() => { setResetToken(null); setMode("login"); }} />;
  }

  if (!session) {
    if (mode === "landing") return <Landing onLogin={() => setMode("login")} onSignUp={() => setMode("signup")} />;
    if (mode === "signup") return <SignUp onDone={start} onSwitch={() => setMode("login")} />;
    if (mode === "forgot") return <ForgotPassword onBack={() => setMode("login")} />;
    return <Login onDone={start} onSwitch={() => setMode("signup")} onForgot={() => setMode("forgot")} />;
  }

  const signOut = () => {
    // Revoke the refresh token on the server; sign out locally even if that call fails.
    logout(session.refresh_token).catch(() => {});
    clearSession();
    setSession(null);
    setMode("landing");
  };

  return <Workspace session={session} onSignOut={signOut} />;
}
