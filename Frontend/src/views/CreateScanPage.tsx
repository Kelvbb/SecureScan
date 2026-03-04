import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components";
import { createScan, uploadScan } from "../api";

type UploadMode = "git" | "file";

export function CreateScanPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<UploadMode>("git");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGitSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!repositoryUrl.trim()) {
      setError("Veuillez saisir une URL de dépôt Git.");
      return;
    }

    setLoading(true);
    try {
      const scan = await createScan({
        repository_url: repositoryUrl.trim(),
      });
      // Rediriger vers la page de prévisualisation
      navigate(`/scans/${scan.id}/preview`, { replace: true });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Impossible de créer le scan."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleFileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!selectedFile) {
      setError("Veuillez sélectionner un fichier ZIP.");
      return;
    }

    if (!selectedFile.name.endsWith(".zip")) {
      setError("Le fichier doit être une archive ZIP (.zip)");
      return;
    }

    setLoading(true);
    try {
      await uploadScan(selectedFile);
      navigate(`/dashboard`, { replace: true });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Impossible de téléverser le fichier."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h1>Nouveau scan</h1>
      <p className="text-muted">
        Analysez un dépôt Git ou téléversez votre code pour détecter les vulnérabilités de sécurité
      </p>

      {error && <p className="auth-error">{error}</p>}

      {/* Onglets */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem", borderBottom: "1px solid var(--border)" }}>
        <button
          type="button"
          onClick={() => setMode("git")}
          style={{
            padding: "0.75rem 1.5rem",
            background: "transparent",
            border: "none",
            borderBottom: mode === "git" ? "2px solid var(--accent)" : "2px solid transparent",
            color: mode === "git" ? "var(--accent)" : "var(--text-muted)",
            cursor: "pointer",
            fontWeight: mode === "git" ? 500 : 400,
          }}
          disabled={loading}
        >
          Dépôt Git
        </button>
        <button
          type="button"
          onClick={() => setMode("file")}
          style={{
            padding: "0.75rem 1.5rem",
            background: "transparent",
            border: "none",
            borderBottom: mode === "file" ? "2px solid var(--accent)" : "2px solid transparent",
            color: mode === "file" ? "var(--accent)" : "var(--text-muted)",
            cursor: "pointer",
            fontWeight: mode === "file" ? 500 : 400,
          }}
          disabled={loading}
        >
          Téléverser un fichier
        </button>
      </div>

      {/* Formulaire Git */}
      {mode === "git" && (
        <form onSubmit={handleGitSubmit} className="auth-form" style={{ maxWidth: "600px" }}>
          <label>
            <span>URL du dépôt Git</span>
            <input
              type="url"
              value={repositoryUrl}
              onChange={(e) => setRepositoryUrl(e.target.value)}
              placeholder="https://github.com/user/repo.git"
              required
              disabled={loading}
            />
            <small className="text-muted" style={{ marginTop: "0.25rem", display: "block" }}>
              Exemples : https://github.com/user/repo.git ou https://gitlab.com/user/repo.git
            </small>
          </label>

          <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
            <Button type="submit" disabled={loading}>
              {loading ? "Création…" : "Créer le scan"}
            </Button>
            <Button
              type="button"
              className="btn-secondary"
              onClick={() => navigate("/dashboard")}
              disabled={loading}
            >
              Annuler
            </Button>
          </div>
        </form>
      )}

      {/* Formulaire Fichier */}
      {mode === "file" && (
        <form onSubmit={handleFileSubmit} className="auth-form" style={{ maxWidth: "600px" }}>
          <label>
            <span>Archive ZIP du code source</span>
            <input
              type="file"
              accept=".zip"
              onChange={(e) => {
                const file = e.target.files?.[0] || null;
                setSelectedFile(file);
                setError(null);
              }}
              required
              disabled={loading}
              style={{
                padding: "0.5rem",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                color: "var(--text)",
                cursor: loading ? "not-allowed" : "pointer",
              }}
            />
            {selectedFile && (
              <small className="text-muted" style={{ marginTop: "0.25rem", display: "block" }}>
                Fichier sélectionné : {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
              </small>
            )}
            <small className="text-muted" style={{ marginTop: "0.25rem", display: "block" }}>
              Compressez votre code source dans une archive ZIP (.zip) avant de le téléverser
            </small>
          </label>

          <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
            <Button type="submit" disabled={loading || !selectedFile}>
              {loading ? "Téléversement…" : "Téléverser et créer le scan"}
            </Button>
            <Button
              type="button"
              className="btn-secondary"
              onClick={() => navigate("/dashboard")}
              disabled={loading}
            >
              Annuler
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
