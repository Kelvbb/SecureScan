"""
Générateurs de corrections template-based pour SecureScan.
Chaque fonction reçoit la ligne vulnérable et retourne un FixResult
avec la ligne corrigée et une explication destinée au développeur.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class VulnerabilityType(str, Enum):
    SQL_INJECTION = "sql_injection"
    XSS            = "xss"
    EXPOSED_SECRET = "exposed_secret"
    PLAINTEXT_PWD  = "plaintext_password"


@dataclass(frozen=True)
class FixResult:
    original_line: str
    fixed_line: str
    explanation: str
    owasp_category: str


def _fix_sql_injection(line: str) -> FixResult:
    """
    Réécrit les appels cursor.execute() qui concatènent des variables
    directement dans la requête (f-string, %, .format) en requêtes paramétrées.
    Si le pattern n'est pas reconnu, un commentaire TODO est injecté.
    """
    stripped = line.rstrip()

    fstring_pattern = re.compile(r'(cursor\.execute\()(f["\'])(.*?)(["\'])\)', re.DOTALL)
    percent_pattern = re.compile(r'(cursor\.execute\()(["\'])(.*?)["\'](\s*%\s*)(\w+)\)', re.DOTALL)
    format_pattern  = re.compile(r'(cursor\.execute\()(["\'])(.*?)["\']\.format\(([^)]+)\)\)', re.DOTALL)

    if m := fstring_pattern.search(stripped):
        variables    = re.findall(r'\{(\w+)\}', m.group(3))
        placeholders = re.sub(r'\{(\w+)\}', '%s', m.group(3))
        params       = ", ".join(variables)
        indent       = len(line) - len(line.lstrip())
        fixed        = f"{' ' * indent}cursor.execute(\"{placeholders}\", ({params},))"
        explanation  = (
            "L'interpolation directe dans la requête SQL ouvre une faille d'injection. "
            "Les valeurs sont maintenant transmises séparément et jamais interprétées comme du SQL."
        )

    elif m := percent_pattern.search(stripped):
        placeholders = re.sub(r'%[sd]', '%s', m.group(3))
        param        = m.group(5).strip()
        indent       = len(line) - len(line.lstrip())
        fixed        = f"{' ' * indent}cursor.execute(\"{placeholders}\", ({param},))"
        explanation  = "Formatage % remplacé par un tuple de paramètres liés. [OWASP A05]"

    elif m := format_pattern.search(stripped):
        placeholders = re.sub(r'\{\w*\}', '%s', m.group(3))
        params_raw   = m.group(4)
        indent       = len(line) - len(line.lstrip())
        fixed        = f"{' ' * indent}cursor.execute(\"{placeholders}\", ({params_raw},))"
        explanation  = ".format() dans execute() remplacé par des paramètres liés. [OWASP A05]"

    else:
        # Pattern non reconnu : on annote la ligne pour review manuelle
        indent      = len(line) - len(line.lstrip())
        fixed       = (
            f"{' ' * indent}# TODO [SecureScan]: Utiliser des requêtes paramétrées\n"
            f"{stripped}  # VULNERABLE – voir OWASP A05"
        )
        explanation = (
            "Injection SQL probable, mais le pattern n'a pas pu être corrigé automatiquement. "
            "Remplacer la concaténation par cursor.execute(query, params)."
        )

    return FixResult(original_line=line, fixed_line=fixed,
                     explanation=explanation, owasp_category="A05 – Injection")


def _fix_xss(line: str) -> FixResult:
    """
    Entoure les sorties HTML non échappées avec la fonction appropriée selon le langage :
    - PHP    : htmlspecialchars($var, ENT_QUOTES, 'UTF-8')
    - JS     : DOMPurify.sanitize(value)
    - Python : commentaire markupsafe (correction manuelle requise)
    """
    stripped = line.rstrip()
    indent   = len(line) - len(line.lstrip())

    php_echo = re.compile(r'(echo\s+)(\$\w+)(;?)')
    if m := php_echo.search(stripped):
        var   = m.group(2)
        fixed = stripped.replace(
            m.group(0),
            f"echo htmlspecialchars({var}, ENT_QUOTES, 'UTF-8'){m.group(3)}",
        )
        return FixResult(
            original_line  = line,
            fixed_line     = " " * indent + fixed.lstrip(),
            explanation    = (
                f"{var} est affiché sans échappement. htmlspecialchars() neutralise "
                "les caractères HTML spéciaux (<, >, &, \", '). [OWASP A05]"
            ),
            owasp_category = "A05 – Injection",
        )

    # Sortie Python via f-string ou print() : correction automatique risquée,
    # on guide le développeur vers la bonne approche pour son contexte.
    py_fstring_html = re.compile(r'(return\s+|print\()f?["\'].*\{(\w+)\}.*["\']')
    if py_fstring_html.search(stripped):
        return FixResult(
            original_line  = line,
            fixed_line     = (
                f"{' ' * indent}# TODO [SecureScan]: échapper avec markupsafe.escape() "
                "ou activer autoescape=True dans Jinja2\n"
                f"{stripped}"
            ),
            explanation    = (
                "Sortie HTML potentiellement non échappée. Utiliser markupsafe.escape(var) "
                "ou l'auto-escaping Jinja2. [OWASP A05]"
            ),
            owasp_category = "A05 – Injection",
        )

    js_inner = re.compile(r'(\w+)\.innerHTML\s*=\s*(.+);')
    if m := js_inner.search(stripped):
        element, value = m.group(1), m.group(2).strip()
        fixed = stripped.replace(m.group(0), f"{element}.innerHTML = DOMPurify.sanitize({value});")
        return FixResult(
            original_line  = line,
            fixed_line     = " " * indent + fixed.lstrip(),
            explanation    = (
                "innerHTML accepte du HTML arbitraire. "
                "DOMPurify.sanitize() filtre les vecteurs XSS avant injection dans le DOM. [OWASP A05]"
            ),
            owasp_category = "A05 – Injection",
        )

    return FixResult(
        original_line  = line,
        fixed_line     = (
            f"{' ' * indent}# TODO [SecureScan]: Échapper la sortie – OWASP A05\n"
            f"{stripped}"
        ),
        explanation    = (
            "XSS potentiel détecté. Appliquer htmlspecialchars() (PHP), "
            "markupsafe.escape() (Python) ou DOMPurify (JS) selon le contexte."
        ),
        owasp_category = "A05 – Injection",
    )


def _fix_exposed_secret(line: str) -> FixResult:
    """
    Remplace toute assignation de valeur littérale (clé API, mot de passe, token…)
    par un appel os.getenv(), en dérivant le nom de la variable d'env depuis le nom
    de la variable Python (mise en majuscules).
    """
    stripped = line.rstrip()
    indent   = len(line) - len(line.lstrip())

    # On cible les assignations simples : VAR = "valeur"
    assignment = re.compile(r'^(\s*)([\w_]+)\s*=\s*(["\'])(.+?)\3')
    if m := assignment.match(line):
        var_name    = m.group(2)
        env_key     = var_name.upper()
        fixed       = f"{m.group(1)}{var_name} = os.getenv(\"{env_key}\")"
        explanation = (
            f"'{var_name}' est codé en dur. Stocker la valeur dans la variable "
            f"d'environnement {env_key}, chargée via os.getenv(). "
            "Ajouter cette variable dans .env (et .env dans .gitignore). [OWASP A04]"
        )
        return FixResult(
            original_line  = line,
            fixed_line     = fixed,
            explanation    = explanation,
            owasp_category = "A04 – Cryptographic Failures",
        )

    return FixResult(
        original_line  = line,
        fixed_line     = (
            f"{' ' * indent}# TODO [SecureScan]: Déplacer ce secret en variable d'environnement – OWASP A04\n"
            f"{stripped}"
        ),
        explanation    = "Secret potentiellement exposé. Remplacer par os.getenv('NOM_VAR').",
        owasp_category = "A04 – Cryptographic Failures",
    )


def _fix_plaintext_password(line: str) -> FixResult:
    """
    Injecte un hash Argon2id (argon2-cffi) à la place du stockage en clair.
    Gère deux cas : assignation d'attribut (.password = ...) et clé de dictionnaire.
    Pour la vérification ultérieure : _ph.verify(stored_hash, candidate).
    """
    stripped = line.rstrip()
    indent   = len(line) - len(line.lstrip())

    attr_pattern = re.compile(r'(\w+\.password)\s*=\s*(.+)')
    if m := attr_pattern.search(stripped):
        attr, value = m.group(1), m.group(2).strip().rstrip(';,')
        fixed = (
            f"{' ' * indent}from argon2 import PasswordHasher as _PH\n"
            f"{' ' * indent}_ph = _PH()\n"
            f"{' ' * indent}{attr} = _ph.hash({value})"
        )
        return FixResult(
            original_line  = line,
            fixed_line     = fixed,
            explanation    = (
                f"Mot de passe stocké en clair dans {attr}. "
                "Argon2id (recommandation OWASP 2025) est résistant aux attaques GPU. [OWASP A04]"
            ),
            owasp_category = "A04 – Cryptographic Failures",
        )

    dict_pattern = re.compile(r'(["\']password["\']\s*:\s*)(.+?)([,}])')
    if m := dict_pattern.search(stripped):
        value  = m.group(2).strip()
        prefix = stripped[: m.start()]
        suffix = stripped[m.end() :]
        fixed  = (
            f"{' ' * indent}from argon2 import PasswordHasher as _PH; _ph = _PH()\n"
            f"{' ' * indent}{prefix}'password': _ph.hash({value}){m.group(3)}{suffix}"
        )
        return FixResult(
            original_line  = line,
            fixed_line     = fixed,
            explanation    = "Clé 'password' en clair dans un dictionnaire. Hash Argon2id appliqué. [OWASP A04]",
            owasp_category = "A04 – Cryptographic Failures",
        )

    return FixResult(
        original_line  = line,
        fixed_line     = (
            f"{' ' * indent}# TODO [SecureScan]: Hacher avec argon2-cffi avant stockage – OWASP A04\n"
            f"{stripped}"
        ),
        explanation    = (
            "Mot de passe potentiellement stocké en clair. "
            "Utiliser argon2-cffi : ph = PasswordHasher(); ph.hash(password)."
        ),
        owasp_category = "A04 – Cryptographic Failures",
    )


# Table de dispatch : associe chaque type de vulnérabilité à son générateur.
# Pour ajouter un nouveau type, enregistrer ici + dans VulnerabilityType.
_GENERATORS: dict[VulnerabilityType, Callable[[str], FixResult]] = {
    VulnerabilityType.SQL_INJECTION:  _fix_sql_injection,
    VulnerabilityType.XSS:            _fix_xss,
    VulnerabilityType.EXPOSED_SECRET: _fix_exposed_secret,
    VulnerabilityType.PLAINTEXT_PWD:  _fix_plaintext_password,
}


def generate_fix(vuln_type: VulnerabilityType, line: str) -> FixResult:
    """
    Point d'entrée public : retourne la correction pour une ligne donnée.

    Raises:
        KeyError: si vuln_type n'a pas de générateur enregistré.
    """
    generator = _GENERATORS.get(vuln_type)
    if generator is None:
        raise KeyError(
            f"Aucun générateur pour le type '{vuln_type}'. "
            f"Types supportés : {[t.value for t in _GENERATORS]}"
        )
    return generator(line)
