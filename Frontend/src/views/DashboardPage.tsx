import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "../components";
import { useAuth } from "../contexts";
import { getMyScans, type ScanItem } from "../api";

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <h1>Tableau de bord</h1>
          <p className="text-muted">
            Bienvenue, {user?.full_name || user?.email}.
          </p>
        </div>
        <Button onClick={() => navigate("/scans/new")}>
          Nouveau scan
        </Button>
      </div>

      {hasScans ? (
        <section className="dashboard-scans">
          <h2>Vos analyses</h2>
          <ul className="scan-list">
            {scans.map((s) => (
              <li key={s.id} className="scan-item">
                <div style={{ display: "flex", alignItems: "center", gap: "1rem", flex: 1 }}>
                  <span className="scan-status" style={{
                    padding: "0.25rem 0.75rem",
                    borderRadius: "4px",
                    fontSize: "0.85rem",
                    fontWeight: 500,
                    backgroundColor: 
                      s.status === "completed" ? "rgba(0, 230, 118, 0.2)" :
                      s.status === "running" ? "rgba(255, 193, 7, 0.2)" :
                      s.status === "error" ? "rgba(244, 67, 54, 0.2)" :
                      "rgba(158, 158, 158, 0.2)",
                    color:
                      s.status === "completed" ? "#00e676" :
                      s.status === "running" ? "#ffc107" :
                      s.status === "error" ? "#f44336" :
                      "#9e9e9e",
                  }}>
                    {s.status === "completed" ? "Terminé" :
                     s.status === "running" ? "En cours" :
                     s.status === "error" ? "Erreur" :
                     s.status === "pending" ? "En attente" : s.status}
                  </span>
                  <span className="scan-date" style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                    {new Date(s.created_at).toLocaleDateString("fr-FR", {
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <Link 
                  to={`/scans/${s.id}`}
                  style={{
                    color: "var(--accent)",
                    textDecoration: "none",
                    fontSize: "0.9rem",
                    fontWeight: 500,
                    padding: "0.5rem 1rem",
                    borderRadius: "6px",
                    border: "1px solid var(--accent)",
                    transition: "all 0.2s",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = "var(--accent)";
                    e.currentTarget.style.color = "#000";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "transparent";
                    e.currentTarget.style.color = "var(--accent)";
                  }}
                >
                  Voir détails →
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <section className="dashboard-empty">
          <p>Aucun test de sécurité n'a encore été réalisé.</p>
          <div className="dashboard-cta">
            <Button onClick={() => navigate("/scans/new")}>Faire mon test</Button>
          </div>
        </section>
      )}
    </div>
  );
}
