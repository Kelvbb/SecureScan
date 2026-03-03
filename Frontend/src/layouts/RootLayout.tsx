import { Outlet } from "react-router-dom";
import { useAuth } from "../contexts";
import { VisitorHeader, AuthenticatedHeader } from "../components";

export function RootLayout() {
  const { user, loading } = useAuth();

  return (
    <div className="app">
      {!loading && user ? (
        <AuthenticatedHeader />
      ) : (
        <VisitorHeader />
      )}
      <main className="main">
        <Outlet />
      </main>
      <footer className="footer">
        <div className="footer-inner">
          <span>SecureScan</span>
          <span className="text-muted">Analyse de sécurité du code</span>
        </div>
      </footer>
    </div>
  );
}
