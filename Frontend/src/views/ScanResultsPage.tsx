import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "../components";
import {
  getScanResults,
  getScanOwaspSummary,
  type ScanResults,
  type VulnerabilityItem,
  type ScanOwaspSummary,
} from "../api";

export function ScanResultsPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [results, setResults] = useState<ScanResults | null>(null);
  const [owaspSummary, setOwaspSummary] = useState<ScanOwaspSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filtres
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [owaspFilter, setOwaspFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (!scanId) {
      setError("ID de scan manquant");
      setLoading(false);
      return;
    }

    const loadData = async () => {
      try {
        const [resultsData, summaryData] = await Promise.all([
          getScanResults(scanId),
          getScanOwaspSummary(scanId).catch(() => null),
        ]);
        setResults(resultsData);
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

  if (error || !results) {
    return (
      <div className="page">
        <p className="auth-error">{error || "Résultats introuvables"}</p>
        <Button onClick={() => navigate(`/scans/${scanId}`)}>Retour</Button>
      </div>
    );
  }

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

  const getOwaspColor = (categoryId: string) => {
    const colors: Record<string, string> = {
      A01: "#ef5350",
      A02: "#ff7043",
      A03: "#ffa726",
      A04: "#ffb74d",
      A05: "#ef5350",
      A06: "#ffa726",
      A07: "#ff7043",
      A08: "#ffb74d",
      A09: "#66bb6a",
      A10: "#ffa726",
    };
    return colors[categoryId] || "var(--accent)";
  };

  // Filtrer les vulnérabilités
  const filteredVulns = results.items.filter((vuln) => {
    // Filtre par sévérité
    if (severityFilter !== "all") {
      if (vuln.severity.toLowerCase() !== severityFilter.toLowerCase()) {
        return false;
      }
    }

    // Filtre par OWASP
    if (owaspFilter !== "all") {
      if (vuln.owasp_category_id !== owaspFilter) {
        return false;
      }
    }

    // Recherche textuelle
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesTitle = vuln.title.toLowerCase().includes(query);
      const matchesDescription = vuln.description?.toLowerCase().includes(query) || false;
      const matchesFile = vuln.file_path?.toLowerCase().includes(query) || false;
      if (!matchesTitle && !matchesDescription && !matchesFile) {
        return false;
      }
    }

    return true;
  });

  return (
    <div className="page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem" }}>
        <div>
          <h1>Vulnérabilités détectées</h1>
          <p className="text-muted">
            {results.total} vulnérabilité{results.total > 1 ? "s" : ""} au total
            {filteredVulns.length !== results.total && ` (${filteredVulns.length} affichée${filteredVulns.length > 1 ? "s" : ""})`}
          </p>
        </div>
        <Button className="btn-secondary" onClick={() => navigate(`/scans/${scanId}`)}>
          Retour
        </Button>
      </div>

      {/* Filtres */}
      <section style={{ marginBottom: "2rem", padding: "1.5rem", background: "var(--bg-card)", borderRadius: "12px", border: "1px solid var(--border)" }}>
        <h2 style={{ marginTop: 0, marginBottom: "1rem", fontSize: "1.1rem" }}>Filtres</h2>
        
        <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", marginBottom: "1rem" }}>
          {/* Recherche */}
          <div style={{ flex: "1 1 300px", minWidth: "200px" }}>
            <input
              type="text"
              placeholder="Rechercher dans le titre, description, fichier..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "0.65rem 0.9rem",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                color: "var(--text)",
                fontFamily: "var(--font-body)",
              }}
            />
          </div>

          {/* Filtre sévérité */}
          <div style={{ minWidth: "150px" }}>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              style={{
                width: "100%",
                padding: "0.65rem 0.9rem",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                color: "var(--text)",
                fontFamily: "var(--font-body)",
                cursor: "pointer",
              }}
            >
              <option value="all">Toutes les sévérités</option>
              <option value="critical">Critique</option>
              <option value="high">Élevé</option>
              <option value="medium">Moyen</option>
              <option value="low">Faible</option>
            </select>
          </div>

          {/* Filtre OWASP */}
          <div style={{ minWidth: "200px" }}>
            <select
              value={owaspFilter}
              onChange={(e) => setOwaspFilter(e.target.value)}
              style={{
                width: "100%",
                padding: "0.65rem 0.9rem",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                color: "var(--text)",
                fontFamily: "var(--font-body)",
                cursor: "pointer",
              }}
            >
              <option value="all">Toutes les catégories OWASP</option>
              {owaspSummary?.items
                .sort((a, b) => a.owasp_category_id.localeCompare(b.owasp_category_id))
                .map((item) => (
                  <option key={item.owasp_category_id} value={item.owasp_category_id}>
                    {item.owasp_category_id} - {item.owasp_category_name} ({item.count})
                  </option>
                ))}
            </select>
          </div>
        </div>

        {/* Boutons de réinitialisation */}
        {(severityFilter !== "all" || owaspFilter !== "all" || searchQuery) && (
          <Button
            className="btn-secondary"
            onClick={() => {
              setSeverityFilter("all");
              setOwaspFilter("all");
              setSearchQuery("");
            }}
            style={{ fontSize: "0.9rem", padding: "0.5rem 1rem" }}
          >
            Réinitialiser les filtres
          </Button>
        )}
      </section>

      {/* Liste des vulnérabilités */}
      {filteredVulns.length === 0 ? (
        <section style={{ padding: "3rem", textAlign: "center", background: "var(--bg-card)", borderRadius: "12px", border: "1px solid var(--border)" }}>
          <p className="text-muted" style={{ fontSize: "1.1rem" }}>
            {results.total === 0
              ? "Aucune vulnérabilité détectée"
              : "Aucune vulnérabilité ne correspond aux filtres sélectionnés"}
          </p>
        </section>
      ) : (
        <section>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {filteredVulns.map((vuln) => (
              <div
                key={vuln.id}
                style={{
                  padding: "1.5rem",
                  background: "var(--bg-card)",
                  borderRadius: "12px",
                  border: "1px solid var(--border)",
                  borderLeft: `4px solid ${getSeverityColor(vuln.severity)}`,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "0.5rem", flexWrap: "wrap" }}>
                      <h3 style={{ margin: 0, fontSize: "1.1rem" }}>{vuln.title}</h3>
                      <span
                        style={{
                          padding: "0.25rem 0.75rem",
                          borderRadius: "12px",
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          background: `${getSeverityColor(vuln.severity)}20`,
                          color: getSeverityColor(vuln.severity),
                          textTransform: "capitalize",
                        }}
                      >
                        {vuln.severity}
                      </span>
                      {vuln.owasp_category_id && (
                        <span
                          style={{
                            padding: "0.25rem 0.75rem",
                            borderRadius: "12px",
                            fontSize: "0.8rem",
                            fontWeight: 600,
                            background: `${getOwaspColor(vuln.owasp_category_id)}20`,
                            color: getOwaspColor(vuln.owasp_category_id),
                          }}
                        >
                          {vuln.owasp_category_id} - {vuln.owasp_category_name}
                        </span>
                      )}
                    </div>

                    {vuln.description && (
                      <p style={{ margin: "0.5rem 0", color: "var(--text-muted)", fontSize: "0.9rem", lineHeight: 1.6 }}>
                        {vuln.description}
                      </p>
                    )}

                    {/* Informations de localisation */}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "1.5rem", marginTop: "1rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                      {vuln.file_path && (
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <strong>Fichier :</strong>
                          <code
                            style={{
                              padding: "0.2rem 0.5rem",
                              background: "var(--bg-elevated)",
                              borderRadius: "4px",
                              fontFamily: "var(--font-body)",
                              color: "var(--text)",
                            }}
                          >
                            {vuln.file_path}
                          </code>
                        </div>
                      )}
                      {(vuln.line_start !== null || vuln.line_end !== null) && (
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <strong>Ligne{((vuln.line_start !== null && vuln.line_end !== null && vuln.line_start !== vuln.line_end) || (vuln.line_start === null && vuln.line_end !== null)) ? "s" : ""} :</strong>
                          <code
                            style={{
                              padding: "0.2rem 0.5rem",
                              background: "var(--bg-elevated)",
                              borderRadius: "4px",
                              fontFamily: "var(--font-body)",
                              color: "var(--accent)",
                              fontWeight: 600,
                            }}
                          >
                            {vuln.line_start !== null && vuln.line_end !== null
                              ? vuln.line_start === vuln.line_end
                                ? vuln.line_start
                                : `${vuln.line_start}-${vuln.line_end}`
                              : vuln.line_start !== null
                              ? vuln.line_start
                              : vuln.line_end !== null
                              ? vuln.line_end
                              : "N/A"}
                          </code>
                        </div>
                      )}
                      {vuln.cve_id && (
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <strong>CVE :</strong>
                          <code
                            style={{
                              padding: "0.2rem 0.5rem",
                              background: "var(--bg-elevated)",
                              borderRadius: "4px",
                              fontFamily: "var(--font-body)",
                              color: "var(--text)",
                            }}
                          >
                            {vuln.cve_id}
                          </code>
                        </div>
                      )}
                      {vuln.cwe_id && (
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <strong>CWE :</strong>
                          <code
                            style={{
                              padding: "0.2rem 0.5rem",
                              background: "var(--bg-elevated)",
                              borderRadius: "4px",
                              fontFamily: "var(--font-body)",
                              color: "var(--text)",
                            }}
                          >
                            {vuln.cwe_id}
                          </code>
                        </div>
                      )}
                      {vuln.confidence && (
                        <div>
                          <strong>Confiance :</strong> {vuln.confidence}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Actions */}
      <section style={{ display: "flex", gap: "1rem", marginTop: "2rem" }}>
        <Button onClick={() => navigate(`/scans/${scanId}/score`)}>
          Voir le score
        </Button>
        <Button className="btn-secondary" onClick={() => navigate(`/scans/${scanId}`)}>
          Retour aux détails
        </Button>
      </section>
    </div>
  );
}
