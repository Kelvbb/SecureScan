import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "../components";
import { getScanScore, getScanOwaspSummary, type ScanScore, type ScanOwaspSummary } from "../api";

export function ScanScorePage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [score, setScore] = useState<ScanScore | null>(null);
  const [owaspSummary, setOwaspSummary] = useState<ScanOwaspSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) {
      setError("ID de scan manquant");
      setLoading(false);
      return;
    }

    const loadData = async () => {
      try {
        const [scoreData, summaryData] = await Promise.all([
          getScanScore(scanId),
          getScanOwaspSummary(scanId).catch(() => null),
        ]);
        setScore(scoreData);
        setOwaspSummary(summaryData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur lors du chargement");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [scanId]);

  if (loading) {
    return (
      <div className="page">
        <p className="text-muted">Chargement…</p>
      </div>
    );
  }

  if (error || !score) {
    return (
      <div className="page">
        <p className="auth-error">{error || "Score introuvable"}</p>
        <Button onClick={() => navigate(`/scans/${scanId}`)}>Retour</Button>
      </div>
    );
  }

  const getGradeColor = (grade: string) => {
    switch (grade.toUpperCase()) {
      case "A":
        return "#00e676";
      case "B":
        return "#66bb6a";
      case "C":
        return "#ffa726";
      case "D":
        return "#ff7043";
      case "F":
        return "#ef5350";
      default:
        return "#a1a1aa";
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return "#ef5350";
      case "high":
        return "#ff7043";
      case "medium":
        return "#ffa726";
      case "low":
        return "#66bb6a";
      default:
        return "#a1a1aa";
    }
  };

  const total = score.total_vulnerabilities;
  const criticalPercent = total > 0 ? (score.critical_count / total) * 100 : 0;
  const highPercent = total > 0 ? (score.high_count / total) * 100 : 0;
  const mediumPercent = total > 0 ? (score.medium_count / total) * 100 : 0;
  const lowPercent = total > 0 ? (score.low_count / total) * 100 : 0;

  return (
    <div className="page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem" }}>
        <h1>Score de sécurité</h1>
        <Button className="btn-secondary" onClick={() => navigate(`/scans/${scanId}`)}>
          Retour
        </Button>
      </div>

      {/* Score principal */}
      <section style={{ marginBottom: "3rem", padding: "2rem", background: "var(--bg-card)", borderRadius: "12px", border: "1px solid var(--border)", textAlign: "center" }}>
        <div style={{ fontSize: "4rem", fontWeight: 700, color: getGradeColor(score.grade), marginBottom: "0.5rem" }}>
          {score.grade}
        </div>
        <div style={{ fontSize: "2rem", fontWeight: 600, color: "var(--text)", marginBottom: "0.25rem" }}>
          {score.score.toFixed(1)} / 100
        </div>
        <p className="text-muted" style={{ marginTop: "0.5rem" }}>
          {total === 0 ? "Aucune vulnérabilité détectée" : `${total} vulnérabilité${total > 1 ? "s" : ""} détectée${total > 1 ? "s" : ""}`}
        </p>
      </section>

      {/* Répartition par sévérité */}
      <section style={{ marginBottom: "3rem", padding: "1.5rem", background: "var(--bg-card)", borderRadius: "12px", border: "1px solid var(--border)" }}>
        <h2 style={{ marginTop: 0, marginBottom: "1.5rem" }}>Répartition par sévérité</h2>
        
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
          <div style={{ padding: "1rem", background: "var(--bg-elevated)", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: getSeverityColor("critical"), marginBottom: "0.25rem" }}>
              {score.critical_count}
            </div>
            <div className="text-muted" style={{ fontSize: "0.9rem" }}>Critique</div>
          </div>
          <div style={{ padding: "1rem", background: "var(--bg-elevated)", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: getSeverityColor("high"), marginBottom: "0.25rem" }}>
              {score.high_count}
            </div>
            <div className="text-muted" style={{ fontSize: "0.9rem" }}>Élevé</div>
          </div>
          <div style={{ padding: "1rem", background: "var(--bg-elevated)", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: getSeverityColor("medium"), marginBottom: "0.25rem" }}>
              {score.medium_count}
            </div>
            <div className="text-muted" style={{ fontSize: "0.9rem" }}>Moyen</div>
          </div>
          <div style={{ padding: "1rem", background: "var(--bg-elevated)", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: getSeverityColor("low"), marginBottom: "0.25rem" }}>
              {score.low_count}
            </div>
            <div className="text-muted" style={{ fontSize: "0.9rem" }}>Faible</div>
          </div>
        </div>

        {/* Graphique en barres */}
        {total > 0 && (
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "flex-end", height: "200px" }}>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div
                style={{
                  width: "100%",
                  height: `${criticalPercent}%`,
                  background: getSeverityColor("critical"),
                  borderRadius: "4px 4px 0 0",
                  minHeight: score.critical_count > 0 ? "20px" : "0",
                  transition: "height 0.3s ease",
                }}
              />
              <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>Critique</div>
            </div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div
                style={{
                  width: "100%",
                  height: `${highPercent}%`,
                  background: getSeverityColor("high"),
                  borderRadius: "4px 4px 0 0",
                  minHeight: score.high_count > 0 ? "20px" : "0",
                  transition: "height 0.3s ease",
                }}
              />
              <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>Élevé</div>
            </div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div
                style={{
                  width: "100%",
                  height: `${mediumPercent}%`,
                  background: getSeverityColor("medium"),
                  borderRadius: "4px 4px 0 0",
                  minHeight: score.medium_count > 0 ? "20px" : "0",
                  transition: "height 0.3s ease",
                }}
              />
              <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>Moyen</div>
            </div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div
                style={{
                  width: "100%",
                  height: `${lowPercent}%`,
                  background: getSeverityColor("low"),
                  borderRadius: "4px 4px 0 0",
                  minHeight: score.low_count > 0 ? "20px" : "0",
                  transition: "height 0.3s ease",
                }}
              />
              <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>Faible</div>
            </div>
          </div>
        )}
      </section>

      {/* Répartition OWASP */}
      {owaspSummary && owaspSummary.items.length > 0 && (
        <section style={{ marginBottom: "2rem", padding: "1.5rem", background: "var(--bg-card)", borderRadius: "12px", border: "1px solid var(--border)" }}>
          <h2 style={{ marginTop: 0, marginBottom: "1.5rem" }}>Répartition par catégorie OWASP Top 10</h2>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {owaspSummary.items
              .sort((a, b) => b.count - a.count)
              .map((item) => {
                const percent = total > 0 ? (item.count / total) * 100 : 0;
                return (
                  <div key={item.owasp_category_id} style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                    <div style={{ minWidth: "60px", fontSize: "0.9rem", fontWeight: 600, color: "var(--accent)" }}>
                      {item.owasp_category_id}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
                        <span style={{ fontSize: "0.9rem" }}>{item.owasp_category_name}</span>
                        <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: 600 }}>
                          {item.count} ({percent.toFixed(1)}%)
                        </span>
                      </div>
                      <div
                        style={{
                          width: "100%",
                          height: "8px",
                          background: "var(--bg-elevated)",
                          borderRadius: "4px",
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            width: `${percent}%`,
                            height: "100%",
                            background: "var(--accent)",
                            transition: "width 0.3s ease",
                          }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        </section>
      )}

      {/* Actions */}
      <section style={{ display: "flex", gap: "1rem", marginTop: "2rem" }}>
        <Button onClick={() => navigate(`/scans/${scanId}/results`)}>
          Voir toutes les vulnérabilités
        </Button>
        <Button className="btn-secondary" onClick={() => navigate(`/scans/${scanId}`)}>
          Retour aux détails
        </Button>
      </section>
    </div>
  );
}
