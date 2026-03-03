import { useEffect, useState } from "react";
import { Button } from "../components";
import { useAuth } from "../contexts";
import { getMyScans, type ScanItem } from "../api";

export function DashboardPage() {
  const { user } = useAuth();
  const [scans, setScans] = useState<ScanItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyScans()
      .then(setScans)
      .catch(() => setScans([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="page dashboard-page">
        <p className="text-muted">Chargement…</p>
      </div>
    );
  }

  const hasScans = scans.length > 0;

  return (
    <div className="page dashboard-page">
      <h1>Tableau de bord</h1>
      <p className="text-muted">
        Bienvenue, {user?.full_name || user?.email}.
      </p>

      {hasScans ? (
        <section className="dashboard-scans">
          <h2>Vos analyses</h2>
          <ul className="scan-list">
            {scans.map((s) => (
              <li key={s.id} className="scan-item">
                <span className="scan-status">{s.status}</span>
                <span className="scan-date">
                  {new Date(s.created_at).toLocaleDateString("fr-FR")}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <section className="dashboard-empty">
          <p>Aucun test de sécurité n’a encore été réalisé.</p>
          <div className="dashboard-cta">
            <Button>Faire mon test</Button>
          </div>
        </section>
      )}
    </div>
  );
}
