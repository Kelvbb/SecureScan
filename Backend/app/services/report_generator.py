"""Service de génération de rapports de sécurité (HTML et PDF)."""

import io
import logging
from datetime import datetime
from uuid import UUID

from jinja2 import Template
from weasyprint import HTML, CSS
from sqlalchemy.orm import Session, joinedload

from app.models.scan import Scan
from app.models.vulnerability import Vulnerability
from app.models.tool_execution import ToolExecution

logger = logging.getLogger(__name__)

# Template HTML pour les rapports
REPORT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport de Sécurité - SecureScan</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #2c3e50; line-height: 1.6; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 40px; }
        .header { text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 30px; margin-bottom: 30px; }
        .header h1 { font-size: 32px; color: #2c3e50; margin-bottom: 10px; }
        .header .subtitle { font-size: 14px; color: #7f8c8d; }
        .security-score { text-align: center; margin: 30px 0; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; color: white; }
        .score-number { font-size: 48px; font-weight: bold; }
        .statistics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }
        .stat-box { padding: 20px; background: #f8f9fa; border-radius: 8px; text-align: center; border-left: 4px solid #3498db; }
        .stat-box.critical { border-left-color: #c0392b; }
        .stat-box.critical .stat-number { color: #c0392b; }
        .stat-box.high { border-left-color: #e74c3c; }
        .stat-box.high .stat-number { color: #e74c3c; }
        .stat-box.medium { border-left-color: #f39c12; }
        .stat-box.medium .stat-number { color: #f39c12; }
        .stat-box.low { border-left-color: #27ae60; }
        .stat-box.low .stat-number { color: #27ae60; }
        .stat-number { font-size: 28px; font-weight: bold; margin-bottom: 5px; }
        .stat-label { font-size: 14px; color: #7f8c8d; text-transform: uppercase; }
        h2 { font-size: 24px; color: #2c3e50; margin-top: 40px; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #e74c3c; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        table th { background: #3498db; color: white; padding: 12px; text-align: left; font-weight: 600; }
        table td { padding: 12px; border-bottom: 1px solid #ecf0f1; }
        table tr:nth-child(even) { background: #f8f9fa; }
        .vulnerability-item { padding: 20px; margin: 15px 0; background: #f8f9fa; border-left: 4px solid #e74c3c; border-radius: 4px; }
        .vulnerability-item.critical { border-left-color: #c0392b; background: #fadbd8; }
        .vulnerability-item.high { border-left-color: #e74c3c; background: #fadbd8; }
        .vulnerability-item.medium { border-left-color: #f39c12; background: #fef5e7; }
        .vulnerability-item.low { border-left-color: #27ae60; background: #eafaf1; }
        .vuln-title { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
        .severity-badge { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase; }
        .severity-badge.critical { background: #c0392b; color: white; }
        .severity-badge.high { background: #e74c3c; color: white; }
        .severity-badge.medium { background: #f39c12; color: white; }
        .severity-badge.low { background: #27ae60; color: white; }
        .remediation-box { background: #d5f4e6; border-left: 4px solid #27ae60; padding: 15px; margin-top: 15px; border-radius: 4px; }
        .remediation-title { color: #27ae60; font-weight: 600; margin-bottom: 8px; }
        .empty-state { text-align: center; padding: 40px; color: #27ae60; }
        .footer { margin-top: 50px; padding-top: 20px; border-top: 1px solid #ecf0f1; text-align: center; color: #7f8c8d; font-size: 12px; }
        .scan-info { background: #ecf0f1; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .info-item { margin: 10px 0; }
        .info-label { color: #7f8c8d; font-weight: 600; text-transform: uppercase; font-size: 12px; }
        .info-value { color: #2c3e50; font-size: 14px; }
        @media print { body { background: white; } .container { max-width: 100%; padding: 0; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 Rapport de Sécurité</h1>
            <p class="subtitle">SecureScan - Analyse de Sécurité du Code Source</p>
            <p class="subtitle">Généré le {{ generated_at }}</p>
        </div>

        <div class="security-score">
            <div class="score-number">{{ statistics.security_score }}/100</div>
            <div>Score de Sécurité Global</div>
        </div>

        <div class="statistics">
            <div class="stat-box critical">
                <div class="stat-number">{{ statistics.critical }}</div>
                <div class="stat-label">Critique</div>
            </div>
            <div class="stat-box high">
                <div class="stat-number">{{ statistics.high }}</div>
                <div class="stat-label">Élevé</div>
            </div>
            <div class="stat-box medium">
                <div class="stat-number">{{ statistics.medium }}</div>
                <div class="stat-label">Moyen</div>
            </div>
            <div class="stat-box low">
                <div class="stat-number">{{ statistics.low }}</div>
                <div class="stat-label">Faible</div>
            </div>
        </div>

        <h2>📋 Résumé du Scan</h2>
        <div class="scan-info">
            <div class="info-item">
                <span class="info-label">ID Scan</span>
                <span class="info-value">{{ scan.id }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Dépôt</span>
                <span class="info-value">{{ scan.repository_url or 'N/A' }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Statut</span>
                <span class="info-value">{{ scan.status }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Créé le</span>
                <span class="info-value">{{ scan.created_at }}</span>
            </div>
        </div>

        {% if statistics.by_tool %}
        <h2>🛠️ Résultats par Outil</h2>
        <table>
            <thead>
                <tr>
                    <th>Outil</th>
                    <th>Vulnérabilités</th>
                    <th>Statut</th>
                </tr>
            </thead>
            <tbody>
                {% for tool_exec in tool_executions %}
                <tr>
                    <td>{{ tool_exec.tool_name }}</td>
                    <td>{{ statistics.by_tool.get(tool_exec.tool_name, 0) }}</td>
                    <td>{% if tool_exec.status == 'success' %}<span style="color: #27ae60;">✓ Réussi</span>{% elif tool_exec.status == 'error' %}<span style="color: #e74c3c;">✗ Erreur</span>{% else %}<span style="color: #f39c12;">⊙ {{ tool_exec.status }}</span>{% endif %}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        <h2>🔍 Détail des Vulnérabilités</h2>
        {% if vulnerabilities %}
            {% for vuln in vulnerabilities %}
            <div class="vulnerability-item {{ vuln.severity|lower }}">
                <div class="vuln-title">{{ vuln.title }}</div>
                <p><strong>Sévérité:</strong> <span class="severity-badge {{ vuln.severity|lower }}">{{ vuln.severity }}</span></p>
                <p><strong>Outil:</strong> {{ vuln.tool_name }}</p>
                {% if vuln.file %}<p><strong>Fichier:</strong> {{ vuln.file }}{% if vuln.line %} (ligne {{ vuln.line }}){% endif %}</p>{% endif %}
                {% if vuln.owasp_category %}<p><strong>OWASP:</strong> {{ vuln.owasp_category }}</p>{% endif %}
                {% if vuln.description %}<p><strong>Description:</strong> {{ vuln.description }}</p>{% endif %}
                {% if vuln.remediation %}
                <div class="remediation-box">
                    <div class="remediation-title">💡 Correction Recommandée</div>
                    <div>{{ vuln.remediation }}</div>
                </div>
                {% endif %}
            </div>
            {% endfor %}
        {% else %}
        <div class="empty-state">
            <h3>✓ Aucune vulnérabilité détectée!</h3>
            <p>Votre code a réussi les contrôles de sécurité.</p>
        </div>
        {% endif %}

        <div class="footer">
            <p>SecureScan © 2026 - Plateforme d'Analyse de Sécurité du Code Source</p>
            <p>Ce rapport est confidentiel et destiné exclusivement à l'organisation propriétaire du code.</p>
        </div>
    </div>
</body>
</html>"""


class ReportGenerator:
    """Générateur de rapports de sécurité en HTML et PDF."""

    def generate_html_report(self, db: Session, scan_id: UUID) -> str:
        """Génère un rapport HTML pour un scan."""
        # Récupérer les données
        scan = db.get(Scan, scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        vulnerabilities = (
            db.query(Vulnerability)
            .filter(Vulnerability.scan_id == scan_id)
            .options(
                joinedload(Vulnerability.tool_execution),
                joinedload(Vulnerability.owasp_category),
            )
            .all()
        )

        tool_executions = (
            db.query(ToolExecution).filter(ToolExecution.scan_id == scan_id).all()
        )

        # Calculer les statistiques
        stats = self._calculate_statistics(vulnerabilities, tool_executions)

        # Préparer le contexte
        context = {
            "scan": {
                "id": str(scan.id),
                "repository_url": scan.repository_url,
                "status": scan.status,
                "created_at": (
                    scan.created_at.strftime("%d/%m/%Y %H:%M")
                    if scan.created_at
                    else ""
                ),
            },
            "vulnerabilities": [
                {
                    "title": v.title,
                    "description": v.description,
                    "severity": v.severity,
                    "file": v.file_path,
                    "line": (
                        f"{v.line_start}-{v.line_end}"
                        if (v.line_start and v.line_end and v.line_start != v.line_end)
                        else (v.line_start or v.line_end or None)
                    ),
                    "owasp_category": (
                        v.owasp_category.name if v.owasp_category else None
                    ),
                    "tool_name": (
                        v.tool_execution.raw_output.get("tool", "unknown")
                        if (
                            v.tool_execution
                            and v.tool_execution.raw_output
                            and isinstance(v.tool_execution.raw_output, dict)
                        )
                        else "unknown"
                    ),
                    "remediation": None,  # Pas de champ dans le modèle
                }
                for v in vulnerabilities
            ],
            "tool_executions": [
                {
                    "tool_name": (
                        t.raw_output.get("tool", "unknown")
                        if t.raw_output and isinstance(t.raw_output, dict)
                        else "unknown"
                    ),
                    "status": t.status,
                }
                for t in tool_executions
            ],
            "statistics": stats,
            "generated_at": datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
        }

        # Rendre le template
        template = Template(REPORT_HTML_TEMPLATE)
        html_content = template.render(**context)

        return html_content

    def generate_pdf_report(self, db: Session, scan_id: UUID) -> bytes:
        """Génère un rapport PDF pour un scan."""
        html_content = self.generate_html_report(db, scan_id)

        try:
            html_obj = HTML(string=html_content)

            css_styles = CSS(string="""
                @page { size: A4; margin: 2cm; }
                body { font-family: 'Segoe UI', sans-serif; color: #333; }
                h2 { page-break-after: avoid; }
            """)

            pdf_bytes = html_obj.write_pdf(stylesheets=[css_styles])
            return pdf_bytes

        except Exception as e:
            logger.error(f"Erreur lors de la génération du PDF: {e}")
            raise

    def _calculate_statistics(
        self, vulnerabilities: list, tool_executions: list
    ) -> dict:
        """Calcule les statistiques des vulnérabilités."""
        stats = {
            "total": len(vulnerabilities),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "by_tool": {},
        }

        for vuln in vulnerabilities:
            severity = vuln.severity.lower()
            if severity == "critical":
                stats["critical"] += 1
            elif severity == "high":
                stats["high"] += 1
            elif severity == "medium":
                stats["medium"] += 1
            else:
                stats["low"] += 1

            tool = "unknown"
            if (
                vuln.tool_execution
                and vuln.tool_execution.raw_output
                and isinstance(vuln.tool_execution.raw_output, dict)
            ):
                tool = vuln.tool_execution.raw_output.get("tool", "unknown")
            stats["by_tool"][tool] = stats["by_tool"].get(tool, 0) + 1

        # Calcul du score
        score = 100
        score -= stats["critical"] * 25
        score -= stats["high"] * 10
        score -= stats["medium"] * 5
        score -= stats["low"] * 2
        stats["security_score"] = max(0, score)

        return stats
