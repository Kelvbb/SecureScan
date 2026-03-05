/**
 * Frontend\src\views\ScanFixesPage.tsx
 * Page de validation et d'application des corrections SecureScan.
 * Workflow : chargement des fixes → sélection utilisateur → apply + push Git.
 */

import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "../components";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FixProposal {
  suggested_fix_id: string;
  vuln_id: string;
  file_path: string;
  line_number: number;
  original_line: string;
  fixed_line: string;
  patch_diff: string;
  description: string;
  owasp_category: string;
  fix_type: string;
  auto_applicable: boolean;
}

interface FixesListResponse {
  scan_id: string;
  proposals: FixProposal[];
  total: number;
}

interface ApplyFixesResponse {
  scan_id: string;
  applied_fix_ids: string[];
  skipped_fix_ids: string[];
  errors: Record<string, string>;
  git_branch: string | null;
  git_commit: string | null;
  git_pushed: boolean;
}

// ---------------------------------------------------------------------------
// API calls (inline pour ne pas modifier api/scans.ts si non souhaité)
// ---------------------------------------------------------------------------

async function getFixProposals(scanId: string): Promise<FixesListResponse> {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`/api/scans/${scanId}/fixes`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok)
    throw new Error(`Erreur ${res.status} lors du chargement des corrections`);
  return res.json();
}

async function applyFixes(
  scanId: string,
  fixIds: string[],
): Promise<ApplyFixesResponse> {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`/api/scans/${scanId}/fixes/apply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ fix_ids: fixIds }),
  });
  if (!res.ok)
    throw new Error(
      `Erreur ${res.status} lors de l'application des corrections`,
    );
  return res.json();
}

// ---------------------------------------------------------------------------
// Helpers UI
// ---------------------------------------------------------------------------

const OWASP_COLORS: Record<string, string> = {
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

function getOwaspColor(category: string): string {
  const key = category.slice(0, 3);
  return OWASP_COLORS[key] ?? "var(--accent)";
}

function OwaspBadge({ category }: { category: string }) {
  const color = getOwaspColor(category);
  return (
    <span
      style={{
        padding: "0.2rem 0.6rem",
        borderRadius: "10px",
        fontSize: "0.75rem",
        fontWeight: 600,
        background: `${color}20`,
        color,
        whiteSpace: "nowrap",
      }}
    >
      {category}
    </span>
  );
}

/** Affiche un diff unified ligne par ligne avec coloration +/- */
function DiffView({
  patch_diff,
  original_line,
  fixed_line,
}: Pick<FixProposal, "patch_diff" | "original_line" | "fixed_line">) {
  const [showDiff, setShowDiff] = useState(false);

  return (
    <div style={{ marginTop: "1rem" }}>
      {/* Côte-à-côte : original vs corrigé */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "0.5rem",
          marginBottom: "0.5rem",
        }}
      >
        <div>
          <div
            style={{
              fontSize: "0.75rem",
              color: "#ef5350",
              marginBottom: "0.25rem",
              fontWeight: 600,
            }}
          >
            − Original
          </div>
          <pre
            style={{
              margin: 0,
              padding: "0.75rem",
              background: "#1a0a0a",
              border: "1px solid #ef535040",
              borderRadius: "6px",
              fontSize: "0.8rem",
              color: "#ef9a9a",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
              lineHeight: 1.6,
              minHeight: "2.5rem",
            }}
          >
            {original_line || "(ligne vide)"}
          </pre>
        </div>
        <div>
          <div
            style={{
              fontSize: "0.75rem",
              color: "#66bb6a",
              marginBottom: "0.25rem",
              fontWeight: 600,
            }}
          >
            + Corrigé
          </div>
          <pre
            style={{
              margin: 0,
              padding: "0.75rem",
              background: "#091a09",
              border: "1px solid #66bb6a40",
              borderRadius: "6px",
              fontSize: "0.8rem",
              color: "#a5d6a7",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
              lineHeight: 1.6,
              minHeight: "2.5rem",
            }}
          >
            {fixed_line || "(ligne vide)"}
          </pre>
        </div>
      </div>

      {/* Diff unified (optionnel) */}
      {patch_diff && (
        <>
          <button
            onClick={() => setShowDiff((v) => !v)}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              fontSize: "0.8rem",
              cursor: "pointer",
              padding: "0.25rem 0",
              textDecoration: "underline",
            }}
          >
            {showDiff ? "Masquer" : "Afficher"} le diff unifié
          </button>
          {showDiff && (
            <pre
              style={{
                margin: "0.5rem 0 0",
                padding: "0.75rem",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                fontSize: "0.78rem",
                lineHeight: 1.7,
                whiteSpace: "pre-wrap",
                wordBreak: "break-all",
                color: "var(--text-muted)",
              }}
            >
              {patch_diff.split("\n").map((line, i) => (
                <span
                  key={i}
                  style={{
                    display: "block",
                    color:
                      line.startsWith("+") && !line.startsWith("+++")
                        ? "#a5d6a7"
                        : line.startsWith("-") && !line.startsWith("---")
                          ? "#ef9a9a"
                          : line.startsWith("@@")
                            ? "#80cbc4"
                            : "var(--text-muted)",
                  }}
                >
                  {line}
                </span>
              ))}
            </pre>
          )}
        </>
      )}
    </div>
  );
}

/** Résultat du push Git */
function GitResult({ result }: { result: ApplyFixesResponse }) {
  return (
    <div
      style={{
        marginTop: "2rem",
        padding: "1.5rem",
        background: result.git_pushed ? "#091a09" : "#1a0a0a",
        border: `1px solid ${result.git_pushed ? "#66bb6a60" : "#ef535060"}`,
        borderRadius: "12px",
      }}
    >
      <h3
        style={{
          marginTop: 0,
          marginBottom: "1rem",
          color: result.git_pushed ? "#66bb6a" : "#ef5350",
          fontSize: "1rem",
        }}
      >
        {result.git_pushed
          ? "✓ Push Git réussi"
          : "⚠ Push Git échoué — fichiers corrigés sur disque"}
      </h3>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "0.6rem",
          fontSize: "0.9rem",
        }}
      >
        {result.git_branch && (
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <span style={{ color: "var(--text-muted)", minWidth: "100px" }}>
              Branche
            </span>
            <code
              style={{
                padding: "0.15rem 0.5rem",
                background: "var(--bg-elevated)",
                borderRadius: "4px",
                color: "var(--accent)",
              }}
            >
              {result.git_branch}
            </code>
          </div>
        )}
        {result.git_commit && (
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <span style={{ color: "var(--text-muted)", minWidth: "100px" }}>
              Commit
            </span>
            <code
              style={{
                padding: "0.15rem 0.5rem",
                background: "var(--bg-elevated)",
                borderRadius: "4px",
                color: "var(--text)",
                fontFamily: "monospace",
              }}
            >
              {result.git_commit.slice(0, 10)}
            </code>
          </div>
        )}
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <span style={{ color: "var(--text-muted)", minWidth: "100px" }}>
            Appliqués
          </span>
          <span style={{ color: "#66bb6a", fontWeight: 600 }}>
            {result.applied_fix_ids.length} fix
            {result.applied_fix_ids.length > 1 ? "s" : ""}
          </span>
        </div>
        {result.skipped_fix_ids.length > 0 && (
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <span style={{ color: "var(--text-muted)", minWidth: "100px" }}>
              Ignorés
            </span>
            <span style={{ color: "#ffa726" }}>
              {result.skipped_fix_ids.length} fix
              {result.skipped_fix_ids.length > 1 ? "s" : ""}
            </span>
          </div>
        )}
        {Object.keys(result.errors).length > 0 && (
          <div style={{ marginTop: "0.5rem" }}>
            <span style={{ color: "#ef5350", fontWeight: 600 }}>Erreurs :</span>
            {Object.entries(result.errors).map(([id, msg]) => (
              <div
                key={id}
                style={{
                  fontSize: "0.8rem",
                  color: "#ef9a9a",
                  marginTop: "0.25rem",
                  paddingLeft: "1rem",
                }}
              >
                {msg}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page principale
// ---------------------------------------------------------------------------

export function ScanFixesPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();

  const [proposals, setProposals] = useState<FixProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // IDs cochés par l'utilisateur
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // État du push
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<ApplyFixesResponse | null>(
    null,
  );
  const [applyError, setApplyError] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) {
      setError("ID de scan manquant");
      setLoading(false);
      return;
    }
    getFixProposals(scanId)
      .then((data) => {
        setProposals(data.proposals);
        // Pré-cocher tous les auto_applicable
        const autoIds = new Set(
          data.proposals
            .filter((p) => p.auto_applicable)
            .map((p) => p.suggested_fix_id),
        );
        setSelectedIds(autoIds);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [scanId]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () =>
    setSelectedIds(new Set(proposals.map((p) => p.suggested_fix_id)));
  const deselectAll = () => setSelectedIds(new Set());

  const handleApply = async () => {
    if (!scanId || selectedIds.size === 0) return;
    setApplying(true);
    setApplyError(null);
    setApplyResult(null);
    try {
      const result = await applyFixes(scanId, Array.from(selectedIds));
      setApplyResult(result);
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setApplying(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Rendu
  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <div className="page">
        <p className="text-muted">Chargement des corrections…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <p className="auth-error">{error}</p>
        <Button onClick={() => navigate(`/scans/${scanId}`)}>Retour</Button>
      </div>
    );
  }

  return (
    <div className="page">
      {/* En-tête */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "2rem",
        }}
      >
        <div>
          <h1>Corrections automatisées</h1>
          <p className="text-muted">
            {proposals.length} correction{proposals.length > 1 ? "s" : ""}{" "}
            proposée{proposals.length > 1 ? "s" : ""}
            {" — "}
            <span style={{ color: "var(--accent)" }}>
              {selectedIds.size} sélectionnée{selectedIds.size > 1 ? "s" : ""}
            </span>
          </p>
        </div>
        <Button
          className="btn-secondary"
          onClick={() => navigate(`/scans/${scanId}`)}
        >
          Retour
        </Button>
      </div>

      {/* Aucune correction disponible */}
      {proposals.length === 0 && (
        <section
          style={{
            padding: "3rem",
            textAlign: "center",
            background: "var(--bg-card)",
            borderRadius: "12px",
            border: "1px solid var(--border)",
          }}
        >
          <p className="text-muted" style={{ fontSize: "1.1rem" }}>
            Aucune correction automatique disponible pour ce scan.
          </p>
          <p
            className="text-muted"
            style={{ fontSize: "0.9rem", marginTop: "0.5rem" }}
          >
            Seules les vulnérabilités de type SQL injection, XSS, secret exposé
            et mot de passe en clair sont corrigées automatiquement.
          </p>
        </section>
      )}

      {proposals.length > 0 && (
        <>
          {/* Barre d'actions globales */}
          <section
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "1rem 1.5rem",
              background: "var(--bg-card)",
              borderRadius: "12px",
              border: "1px solid var(--border)",
              marginBottom: "1.5rem",
              flexWrap: "wrap",
              gap: "1rem",
            }}
          >
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button
                onClick={selectAll}
                style={{
                  background: "none",
                  border: "1px solid var(--border)",
                  borderRadius: "6px",
                  color: "var(--text-muted)",
                  fontSize: "0.85rem",
                  cursor: "pointer",
                  padding: "0.4rem 0.9rem",
                }}
              >
                Tout sélectionner
              </button>
              <button
                onClick={deselectAll}
                style={{
                  background: "none",
                  border: "1px solid var(--border)",
                  borderRadius: "6px",
                  color: "var(--text-muted)",
                  fontSize: "0.85rem",
                  cursor: "pointer",
                  padding: "0.4rem 0.9rem",
                }}
              >
                Tout désélectionner
              </button>
            </div>
            <Button
              onClick={handleApply}
              disabled={
                applying ||
                selectedIds.size === 0 ||
                applyResult?.git_pushed === true
              }
            >
              {applying
                ? "Application en cours…"
                : applyResult?.git_pushed
                  ? "✓ Push effectué"
                  : `Appliquer et pusher (${selectedIds.size})`}
            </Button>
          </section>

          {/* Liste des fixes */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "1rem",
              marginBottom: "2rem",
            }}
          >
            {proposals.map((proposal) => {
              const isSelected = selectedIds.has(proposal.suggested_fix_id);
              const wasApplied = applyResult?.applied_fix_ids.includes(
                proposal.suggested_fix_id,
              );
              const wasSkipped = applyResult?.skipped_fix_ids.includes(
                proposal.suggested_fix_id,
              );
              const hasError = applyResult?.errors[proposal.suggested_fix_id];

              return (
                <div
                  key={proposal.suggested_fix_id}
                  style={{
                    padding: "1.5rem",
                    background: "var(--bg-card)",
                    borderRadius: "12px",
                    border: `1px solid ${
                      wasApplied
                        ? "#66bb6a60"
                        : wasSkipped || hasError
                          ? "#ef535060"
                          : isSelected
                            ? "var(--accent)"
                            : "var(--border)"
                    }`,
                    opacity: applyResult && !wasApplied ? 0.6 : 1,
                    transition: "border-color 0.2s, opacity 0.2s",
                  }}
                >
                  {/* Header du fix */}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: "1rem",
                      flexWrap: "wrap",
                    }}
                  >
                    {/* Checkbox + titre */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "1rem",
                        flex: 1,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(proposal.suggested_fix_id)}
                        disabled={!!applyResult}
                        style={{
                          marginTop: "3px",
                          width: "18px",
                          height: "18px",
                          cursor: applyResult ? "default" : "pointer",
                          accentColor: "var(--accent)",
                          flexShrink: 0,
                        }}
                      />
                      <div style={{ flex: 1 }}>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "0.75rem",
                            flexWrap: "wrap",
                            marginBottom: "0.4rem",
                          }}
                        >
                          <code
                            style={{
                              fontSize: "0.85rem",
                              padding: "0.15rem 0.5rem",
                              background: "var(--bg-elevated)",
                              borderRadius: "4px",
                              color: "var(--accent)",
                            }}
                          >
                            {proposal.fix_type}
                          </code>
                          <OwaspBadge category={proposal.owasp_category} />
                          {wasApplied && (
                            <span
                              style={{
                                fontSize: "0.8rem",
                                color: "#66bb6a",
                                fontWeight: 600,
                              }}
                            >
                              ✓ Appliqué
                            </span>
                          )}
                          {wasSkipped && (
                            <span
                              style={{
                                fontSize: "0.8rem",
                                color: "#ffa726",
                                fontWeight: 600,
                              }}
                            >
                              ⚠ Ignoré
                            </span>
                          )}
                          {hasError && (
                            <span
                              style={{
                                fontSize: "0.8rem",
                                color: "#ef5350",
                                fontWeight: 600,
                              }}
                            >
                              ✗ Erreur
                            </span>
                          )}
                        </div>

                        {/* Localisation */}
                        <div
                          style={{
                            display: "flex",
                            gap: "1.5rem",
                            fontSize: "0.82rem",
                            color: "var(--text-muted)",
                            flexWrap: "wrap",
                          }}
                        >
                          <span>
                            <strong>Fichier :</strong>{" "}
                            <code
                              style={{
                                padding: "0.1rem 0.4rem",
                                background: "var(--bg-elevated)",
                                borderRadius: "3px",
                                color: "var(--text)",
                              }}
                            >
                              {proposal.file_path}
                            </code>
                          </span>
                          <span>
                            <strong>Ligne :</strong>{" "}
                            <code
                              style={{
                                padding: "0.1rem 0.4rem",
                                background: "var(--bg-elevated)",
                                borderRadius: "3px",
                                color: "var(--accent)",
                                fontWeight: 600,
                              }}
                            >
                              {proposal.line_number}
                            </code>
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  {proposal.description && (
                    <p
                      style={{
                        margin: "1rem 0 0",
                        paddingLeft: "2rem",
                        fontSize: "0.88rem",
                        color: "var(--text-muted)",
                        lineHeight: 1.6,
                      }}
                    >
                      {proposal.description}
                    </p>
                  )}

                  {/* Erreur détaillée */}
                  {hasError && (
                    <p
                      style={{
                        margin: "0.5rem 0 0",
                        paddingLeft: "2rem",
                        fontSize: "0.82rem",
                        color: "#ef9a9a",
                      }}
                    >
                      {hasError}
                    </p>
                  )}

                  {/* Diff côte-à-côte */}
                  <div style={{ paddingLeft: "2rem" }}>
                    <DiffView
                      patch_diff={proposal.patch_diff}
                      original_line={proposal.original_line}
                      fixed_line={proposal.fixed_line}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Erreur globale apply */}
          {applyError && (
            <div
              style={{
                padding: "1rem 1.5rem",
                background: "#1a0a0a",
                border: "1px solid #ef535060",
                borderRadius: "8px",
                color: "#ef9a9a",
                marginBottom: "1rem",
              }}
            >
              {applyError}
            </div>
          )}

          {/* Résultat Git */}
          {applyResult && <GitResult result={applyResult} />}
        </>
      )}

      {/* Actions bas de page */}
      <section style={{ display: "flex", gap: "1rem", marginTop: "2rem" }}>
        <Button
          className="btn-secondary"
          onClick={() => navigate(`/scans/${scanId}/results`)}
        >
          Voir les vulnérabilités
        </Button>
        <Button
          className="btn-secondary"
          onClick={() => navigate(`/scans/${scanId}`)}
        >
          Retour aux détails
        </Button>
      </section>
    </div>
  );
}
