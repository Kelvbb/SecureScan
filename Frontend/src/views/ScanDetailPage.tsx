import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Button } from "../components";
import {
  getScan,
  getScanProgress,
  runScan,
  getScanFiles,
  type ScanDetail,
  type ScanProgress,
  type ScanFiles,
} from "../api";

export function ScanDetailPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [progress, setProgress] = useState<ScanProgress | null>(null);
  const [files, setFiles] = useState<ScanFiles | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingScan, setStartingScan] = useState(false);

  useEffect(() => {
    if (!scanId) {
      setError("ID de scan manquant");
      setLoading(false);
      return;
    }

    const loadData = async () => {
      try {
        const [scanData, progressData, filesData] = await Promise.all([
          getScan(scanId),
          getScanProgress(scanId).catch(() => null), // Peut échouer si le scan n'existe pas
          getScanFiles(scanId).catch(() => null), // Peut échouer si le scan n'existe pas
        ]);
        setScan(scanData);
        setProgress(progressData);
        setFiles(filesData);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Erreur lors du chargement",
        );
      } finally {
        setLoading(false);
      }
    };

    loadData();

    // Si le scan est en cours, rafraîchir la progression et les fichiers toutes les 2 secondes
    // Si le scan est terminé, rafraîchir aussi les fichiers une fois pour s'assurer qu'ils sont chargés
    const interval = setInterval(() => {
      if (scanId) {
        if (scan?.status === "running") {
          Promise.all([
            getScanProgress(scanId)
              .then(setProgress)
              .catch(() => {}),
            getScanFiles(scanId)
              .then(setFiles)
              .catch(() => {}),
            getScan(scanId)
              .then(setScan)
              .catch(() => {}),
          ]);
        } else if (scan?.status === "completed" && !files) {
          // Charger les fichiers une fois si le scan est terminé et qu'on ne les a pas encore
          getScanFiles(scanId)
            .then(setFiles)
            .catch(() => {});
        }
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [scanId, scan?.status]);

  const handleRunScan = async () => {
    if (!scanId) return;

    // Empêcher les doubles clics si le scan est déjà en cours
    if (scan?.status === "running" || startingScan) {
      return;
    }

    setStartingScan(true);
    setError(null);

    // Mettre à jour le statut localement immédiatement pour un feedback instantané
    if (scan) {
      setScan({ ...scan, status: "running" });
    }

    try {
      await runScan(scanId);
      // Rafraîchir les données immédiatement
      const [scanData, progressData] = await Promise.all([
        getScan(scanId),
        getScanProgress(scanId).catch(() => null),
      ]);
      setScan(scanData);
      setProgress(progressData);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Erreur lors du lancement du scan";
      setError(errorMessage);
      // Si l'erreur indique que le scan est déjà en cours, rafraîchir les données
      if (
        errorMessage.includes("déjà en cours") ||
        errorMessage.includes("already running")
      ) {
        const scanData = await getScan(scanId).catch(() => null);
        if (scanData) {
          setScan(scanData);
        }
      }
    } finally {
      setStartingScan(false);
    }
  };

  if (loading) {
    return (
      <div className="page">
        <p className="text-muted">Chargement…</p>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="page">
        <p className="auth-error">{error || "Scan introuvable"}</p>
        <Button onClick={() => navigate("/dashboard")}>
          Retour au dashboard
        </Button>
      </div>
    );
  }

  const isCompleted = scan?.status === "completed";
  const isRunning = scan?.status === "running";
  const isPending = scan?.status === "pending";

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "#00e676";
      case "running":
        return "#ffa726";
      case "failed":
      case "error":
        return "#ef5350";
      default:
        return "#a1a1aa";
    }
  };

  const getTaskStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "#00e676";
      case "running":
        return "#ffa726";
      case "error":
        return "#ef5350";
      default:
        return "#a1a1aa";
    }
  };

  return (
    <div className="page">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "2rem",
        }}
      >
        <div>
          <h1>Détails du scan</h1>
          <p className="text-muted">
            Statut :{" "}
            <span
              style={{
                color: getStatusColor(scan?.status || "pending"),
                fontWeight: 500,
                textTransform: "capitalize",
              }}
            >
              {scan?.status || "pending"}
            </span>
          </p>
        </div>
        <Button
          className="btn-secondary"
          onClick={() => navigate("/dashboard")}
        >
          Retour
        </Button>
      </div>

      {/* Informations du scan */}
      {scan && (
        <section
          style={{
            marginBottom: "2rem",
            padding: "1.5rem",
            background: "var(--bg-card)",
            borderRadius: "12px",
            border: "1px solid var(--border)",
          }}
        >
          <h2 style={{ marginTop: 0, marginBottom: "1rem" }}>Informations</h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
              gap: "1rem",
            }}
          >
            <div>
              <strong
                className="text-muted"
                style={{ display: "block", marginBottom: "0.25rem" }}
              >
                Créé le
              </strong>
              <span>{new Date(scan.created_at).toLocaleString("fr-FR")}</span>
            </div>
            {scan.started_at && (
              <div>
                <strong
                  className="text-muted"
                  style={{ display: "block", marginBottom: "0.25rem" }}
                >
                  Démarré le
                </strong>
                <span>{new Date(scan.started_at).toLocaleString("fr-FR")}</span>
              </div>
            )}
            {scan.finished_at && (
              <div>
                <strong
                  className="text-muted"
                  style={{ display: "block", marginBottom: "0.25rem" }}
                >
                  Terminé le
                </strong>
                <span>
                  {new Date(scan.finished_at).toLocaleString("fr-FR")}
                </span>
              </div>
            )}
            {scan.repository_url && (
              <div>
                <strong
                  className="text-muted"
                  style={{ display: "block", marginBottom: "0.25rem" }}
                >
                  Dépôt Git
                </strong>
                <span style={{ wordBreak: "break-all" }}>
                  {scan.repository_url}
                </span>
              </div>
            )}
            {scan.upload_path && (
              <div>
                <strong
                  className="text-muted"
                  style={{ display: "block", marginBottom: "0.25rem" }}
                >
                  Fichier téléversé
                </strong>
                <span style={{ wordBreak: "break-all" }}>
                  ✓ Fichier décompressé
                </span>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Progression des tâches (si scan non terminé) */}
      {!isCompleted && progress && scan && (
        <section
          style={{
            marginBottom: "2rem",
            padding: "1.5rem",
            background: "var(--bg-card)",
            borderRadius: "12px",
            border: "1px solid var(--border)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1.5rem",
            }}
          >
            <h2 style={{ margin: 0 }}>Progression de l'analyse</h2>
            <span
              style={{
                fontSize: "1.25rem",
                fontWeight: 600,
                color: getStatusColor(scan?.status || "running"),
              }}
            >
              {progress.overall_progress}%
            </span>
          </div>

          {/* Barre de progression globale */}
          <div style={{ marginBottom: "2rem" }}>
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
                  width: `${progress.overall_progress}%`,
                  height: "100%",
                  background: getStatusColor(scan?.status || "running"),
                  transition: "width 0.3s ease",
                }}
              />
            </div>
          </div>

          {/* Liste des tâches */}
          <div
            style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
          >
            {progress.tasks.map((task) => (
              <div
                key={task.tool_name}
                style={{
                  padding: "1rem",
                  background: "var(--bg-elevated)",
                  borderRadius: "8px",
                  border: "1px solid var(--border)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "0.75rem",
                  }}
                >
                  <div>
                    <strong
                      style={{ display: "block", marginBottom: "0.25rem" }}
                    >
                      {task.display_name}
                    </strong>
                    <span
                      style={{
                        fontSize: "0.85rem",
                        color: getTaskStatusColor(task.status),
                        textTransform: "capitalize",
                      }}
                    >
                      {task.status === "pending"
                        ? "En attente"
                        : task.status === "running"
                          ? "En cours"
                          : task.status === "completed"
                            ? "Terminé"
                            : "Erreur"}
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: "1.1rem",
                      fontWeight: 600,
                      color: getTaskStatusColor(task.status),
                    }}
                  >
                    {task.progress}%
                  </span>
                </div>
                <div
                  style={{
                    width: "100%",
                    height: "6px",
                    background: "var(--bg)",
                    borderRadius: "3px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${task.progress}%`,
                      height: "100%",
                      background: getTaskStatusColor(task.status),
                      transition: "width 0.3s ease",
                    }}
                  />
                </div>
                {task.started_at && (
                  <small
                    className="text-muted"
                    style={{ display: "block", marginTop: "0.5rem" }}
                  >
                    Démarré :{" "}
                    {new Date(task.started_at).toLocaleString("fr-FR")}
                  </small>
                )}
                {task.finished_at && (
                  <small
                    className="text-muted"
                    style={{ display: "block", marginTop: "0.25rem" }}
                  >
                    Terminé :{" "}
                    {new Date(task.finished_at).toLocaleString("fr-FR")}
                  </small>
                )}

                {/* Afficher les fichiers analysés pour cet outil */}
                {files && files.files_by_tool[task.tool_name] && (
                  <div
                    style={{
                      marginTop: "1rem",
                      paddingTop: "1rem",
                      borderTop: "1px solid var(--border)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "0.5rem",
                      }}
                    >
                      <strong style={{ fontSize: "0.9rem" }}>
                        Fichiers analysés :
                      </strong>
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        {files.files_by_tool[task.tool_name].count} fichier
                        {files.files_by_tool[task.tool_name].count > 1
                          ? "s"
                          : ""}
                      </span>
                    </div>
                    <div
                      style={{
                        maxHeight: "150px",
                        overflowY: "auto",
                        background: "var(--bg)",
                        borderRadius: "4px",
                        padding: "0.5rem",
                        fontSize: "0.85rem",
                        fontFamily: "monospace",
                      }}
                    >
                      {files.files_by_tool[task.tool_name].files
                        .slice(0, 20)
                        .map((file: string, idx: number) => (
                          <div
                            key={idx}
                            style={{
                              padding: "0.25rem 0",
                              color: "var(--text-muted)",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                          >
                            📄 {file}
                          </div>
                        ))}
                      {files.files_by_tool[task.tool_name].files.length >
                        20 && (
                        <div
                          style={{
                            color: "var(--text-muted)",
                            fontStyle: "italic",
                            marginTop: "0.5rem",
                          }}
                        >
                          ... et{" "}
                          {files.files_by_tool[task.tool_name].files.length -
                            20}{" "}
                          autre(s) fichier(s)
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Section fichiers analysés globale */}
          {files && files.total_files > 0 && (
            <div
              style={{
                marginTop: "2rem",
                padding: "1.5rem",
                background: "var(--bg-elevated)",
                borderRadius: "8px",
                border: "1px solid var(--border)",
              }}
            >
              <h3 style={{ marginBottom: "1rem", fontSize: "1.1rem" }}>
                📁 Fichiers analysés
              </h3>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "1rem",
                }}
              >
                <span style={{ color: "var(--text-muted)" }}>
                  Total :{" "}
                  <strong style={{ color: "var(--text)" }}>
                    {files.total_files}
                  </strong>{" "}
                  fichier{files.total_files > 1 ? "s" : ""}
                </span>
              </div>
              <div
                style={{
                  maxHeight: "300px",
                  overflowY: "auto",
                  background: "var(--bg)",
                  borderRadius: "4px",
                  padding: "0.75rem",
                  fontSize: "0.85rem",
                  fontFamily: "monospace",
                }}
              >
                {files.all_files.map((file: string, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      padding: "0.25rem 0",
                      color: "var(--text-muted)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    📄 {file}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Section fichiers analysés (toujours visible si des fichiers sont disponibles) */}
      {files && files.total_files > 0 ? (
        <section
          style={{
            marginBottom: "2rem",
            padding: "1.5rem",
            background: "var(--bg-card)",
            borderRadius: "12px",
            border: "1px solid var(--border)",
          }}
        >
          <h2 style={{ marginTop: 0, marginBottom: "1.5rem" }}>
            📁 Fichiers analysés
          </h2>

          {/* Statistiques globales */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1.5rem",
              padding: "1rem",
              background: "var(--bg-elevated)",
              borderRadius: "8px",
            }}
          >
            <div>
              <strong
                style={{
                  fontSize: "1.1rem",
                  display: "block",
                  marginBottom: "0.25rem",
                }}
              >
                {files.total_files} fichier{files.total_files > 1 ? "s" : ""}{" "}
                analysé{files.total_files > 1 ? "s" : ""}
              </strong>
              <span style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                Répartis sur {Object.keys(files.files_by_tool).length} outil
                {Object.keys(files.files_by_tool).length > 1 ? "s" : ""}
              </span>
            </div>
          </div>

          {/* Fichiers par outil */}
          {Object.keys(files.files_by_tool).length > 0 && (
            <div style={{ marginBottom: "2rem" }}>
              <h3
                style={{
                  fontSize: "1rem",
                  marginBottom: "1rem",
                  color: "var(--text-muted)",
                }}
              >
                Par outil d'analyse
              </h3>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "1rem",
                }}
              >
                {Object.entries(files.files_by_tool).map(
                  ([toolName, toolData]) => (
                    <div
                      key={toolName}
                      style={{
                        padding: "1rem",
                        background: "var(--bg-elevated)",
                        borderRadius: "8px",
                        border: "1px solid var(--border)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          marginBottom: "0.75rem",
                        }}
                      >
                        <strong style={{ textTransform: "capitalize" }}>
                          {toolName}
                        </strong>
                        <span
                          style={{
                            fontSize: "0.9rem",
                            color: "var(--text-muted)",
                          }}
                        >
                          {toolData.count} fichier
                          {toolData.count > 1 ? "s" : ""}
                        </span>
                      </div>
                      <div
                        style={{
                          maxHeight: "200px",
                          overflowY: "auto",
                          background: "var(--bg)",
                          borderRadius: "4px",
                          padding: "0.75rem",
                          fontSize: "0.85rem",
                          fontFamily: "monospace",
                        }}
                      >
                        {toolData.files.map((file: string, idx: number) => (
                          <div
                            key={idx}
                            style={{
                              padding: "0.35rem 0",
                              color: "var(--text)",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              borderBottom:
                                idx < toolData.files.length - 1
                                  ? "1px solid var(--border)"
                                  : "none",
                            }}
                          >
                            📄 {file}
                          </div>
                        ))}
                      </div>
                    </div>
                  ),
                )}
              </div>
            </div>
          )}

          {/* Liste complète de tous les fichiers */}
          <div>
            <h3
              style={{
                fontSize: "1rem",
                marginBottom: "1rem",
                color: "var(--text-muted)",
              }}
            >
              Liste complète
            </h3>
            <div
              style={{
                maxHeight: "400px",
                overflowY: "auto",
                background: "var(--bg-elevated)",
                borderRadius: "8px",
                padding: "1rem",
                fontSize: "0.85rem",
                fontFamily: "monospace",
                border: "1px solid var(--border)",
              }}
            >
              {files.all_files.map((file: string, idx: number) => (
                <div
                  key={idx}
                  style={{
                    padding: "0.4rem 0",
                    color: "var(--text)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    borderBottom:
                      idx < files.all_files.length - 1
                        ? "1px solid var(--border)"
                        : "none",
                  }}
                >
                  📄 {file}
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : (
        // Message si aucun fichier n'est trouvé
        scan &&
        (scan.status === "completed" || scan.status === "running") && (
          <section
            style={{
              marginBottom: "2rem",
              padding: "1.5rem",
              background: "var(--bg-card)",
              borderRadius: "12px",
              border: "1px solid var(--border)",
            }}
          >
            <h2 style={{ marginTop: 0, marginBottom: "1rem" }}>
              📁 Fichiers analysés
            </h2>
            <p style={{ color: "var(--text-muted)" }}>
              {scan.status === "running"
                ? "Les fichiers analysés seront affichés une fois l'analyse terminée..."
                : "Aucun fichier analysé trouvé. L'analyse peut être en cours de traitement."}
            </p>
          </section>
        )
      )}

      {/* Actions */}
      <section style={{ display: "flex", gap: "1rem", marginTop: "2rem" }}>
        {isPending && (
          <Button
            onClick={handleRunScan}
            disabled={startingScan || scan?.status === "running"}
          >
            {startingScan
              ? "Démarrage…"
              : scan?.status === "running"
                ? "Analyse en cours…"
                : "Lancer l'analyse"}
          </Button>
        )}
        {isRunning && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              color: "var(--text-muted)",
            }}
          >
            <span>Analyse en cours…</span>
          </div>
        )}
        {isCompleted && (
          <>
            <Link to={`/scans/${scanId}/results`}>
              <Button>Voir les résultats</Button>
            </Link>
            <Link to={`/scans/${scanId}/score`}>
              <Button className="btn-secondary">Voir le score</Button>
            </Link>
            <Link to={`/scans/${scanId}/fixes`}>
              <Button className="btn-secondary">Auto-corrections</Button>
            </Link>
          </>
        )}
      </section>
    </div>
  );
}
