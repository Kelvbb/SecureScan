import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts";

export function GuestOnlyRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="page auth-page">
        <p className="text-muted">Chargement…</p>
      </div>
    );
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}
