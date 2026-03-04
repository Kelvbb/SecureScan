import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "../components";
import { getScanPreview, runScan, type ScanPreview } from "../api";

const TECH_LABELS: { [key: string]: string } = {
  python: "Python",
  javascript: "JavaScript",
  typescript: "TypeScript",
  php: "PHP",
  java: "Java",
  go: "Go",
  ruby: "Ruby",
  rust: "Rust",
  csharp: "C#",
};

const TOOL_LABELS: { [key: string]: string } = {
  semgrep: "Semgrep (SAST)",
  bandit: "Bandit (Python SAST)",
  eslint: "ESLint (JS/TS SAST)",
  "pip-audit": "pip-audit (Dépendances Python)",
  "npm-audit": "npm-audit (Dépendances Node.js)",
  truffleHog: "TruffleHog (Détection de secrets)",
};

export function ScanPreviewPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [preview, setPreview] = useState<ScanPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingScan, setStartingScan] = useState(false);

  useEffect(() => {
    if (!scanId) return;

    const fetchPreview = async () => {
      try {
        setLoading(true);
        const data = await getScanPreview(scanId);
        setPreview(data);
        
        // Si le projet n'est pas prêt, réessayer après 2 secondes
        if (data.status === "not_ready") {
          setTimeout(fetchPreview, 2000);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur lors du chargement de la prévisualisation");
      } finally {
        setLoading(false);
      }
    };

    fetchPreview();
  }, [scanId]);

  const handleStartScan = async () => {
    if (!scanId) return;

    setStartingScan(true);
    try {
      await runScan(scanId);
      navigate(`/scans/${scanId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du lancement de l'analyse");
    } finally {
      setStartingScan(false);
    }
  };

  if (loading && !preview) {
    return (
      <div className="page">
        <h1>Analyse de votre projet...</h1>
        <p className="text-muted">Détection des technologies et préparation de l'analyse...</p>
      </div>
    );
  }

  if (error && !preview) {
    return (
      <div className="page">
        <h1>Erreur</h1>
        <p className="auth-error">{error}</p>
        <Button onClick={() => navigate("/scans/new")}>Retour</Button>
      </div>
    );
  }

  if (!preview) {
    return null;
  }

  const detectedTechnologies = Object.entries(preview.technologies)
    .filter(([_, detected]) => detected)
    .map(([tech, _]) => tech);

  return (
    <div className="page">
      <h1>Prévisualisation du projet</h1>
      <p className="text-muted">
        Voici les technologies détectées et les fichiers qui seront analysés
      </p>

      {preview.status === "not_ready" && (
        <div style={{
          padding: "1rem",
          background: "var(--warning-bg, #fff3cd)",
          border: "1px solid var(--warning-border, #ffc107)",
          borderRadius: "8px",
          marginBottom: "2rem",
        }}>
          <p style={{ margin: 0, color: "var(--warning-text, #856404)" }}>
            {preview.message || "Le projet est en cours de préparation..."}
          </p>
        </div>
      )}

      {error && <p className="auth-error">{error}</p>}

      {/* Technologies détectées */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Technologies détectées</h2>
        {detectedTechnologies.length > 0 ? (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {detectedTechnologies.map((tech) => (
              <span
                key={tech}
                style={{
                  padding: "0.5rem 1rem",
                  background: "var(--accent)",
                  color: "white",
                  borderRadius: "20px",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                }}
              >
                {TECH_LABELS[tech] || tech}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-muted">Aucune technologie détectée</p>
        )}
      </section>

      {/* Outils qui seront utilisés */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Outils d'analyse</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {preview.tools.map((tool) => (
            <div
              key={tool}
              style={{
                padding: "0.75rem 1rem",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <span style={{ color: "var(--accent)" }}>✓</span>
              <span>{TOOL_LABELS[tool] || tool}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Fichiers à analyser */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>
          Fichiers à analyser ({preview.total_files} fichiers)
        </h2>
        <div style={{
          maxHeight: "400px",
          overflowY: "auto",
          background: "var(--bg-elevated)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "1rem",
        }}>
          {Object.entries(preview.files_by_type).map(([type, files]) => (
            <div key={type} style={{ marginBottom: "1.5rem" }}>
              <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem", color: "var(--accent)" }}>
                {TECH_LABELS[type] || type} ({files.length} fichiers)
              </h3>
              <ul style={{ margin: 0, paddingLeft: "1.5rem", listStyle: "none" }}>
                {files.slice(0, 20).map((file, idx) => (
                  <li key={idx} style={{ marginBottom: "0.25rem", fontSize: "0.875rem", color: "var(--text-muted)" }}>
                    <code style={{ background: "transparent", padding: 0 }}>{file}</code>
                  </li>
                ))}
                {files.length > 20 && (
                  <li style={{ marginTop: "0.5rem", fontSize: "0.875rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                    ... et {files.length - 20} autres fichiers
                  </li>
                )}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Actions */}
      <div style={{ display: "flex", gap: "1rem", marginTop: "2rem" }}>
        <Button
          onClick={handleStartScan}
          disabled={preview.status !== "ready" || startingScan}
          style={{ flex: 1 }}
        >
          {startingScan ? "Lancement..." : "Lancer l'analyse"}
        </Button>
        <Button
          className="btn-secondary"
          onClick={() => navigate("/dashboard")}
          disabled={startingScan}
        >
          Annuler
        </Button>
      </div>
    </div>
  );
}
