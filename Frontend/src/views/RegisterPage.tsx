import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../components";
import { register as apiRegister } from "../api";

export function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiRegister({
        email,
        password,
        full_name: fullName.trim() || undefined,
      });
      navigate("/register/confirm", { replace: true });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Inscription impossible."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page auth-page">
      <div className="auth-card">
        <h1>Inscription</h1>
        <p className="text-muted">Créez votre compte SecureScan</p>
        {error && <p className="auth-error">{error}</p>}
        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              disabled={loading}
            />
          </label>
          <label>
            <span>Nom (optionnel)</span>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              autoComplete="name"
              disabled={loading}
            />
          </label>
          <label>
            <span>Mot de passe</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              disabled={loading}
            />
          </label>
          <Button type="submit" className="full-width" disabled={loading}>
            {loading ? "Inscription…" : "S'inscrire"}
          </Button>
        </form>
        <p className="auth-footer">
          Déjà un compte ? <Link to="/login">Se connecter</Link>
        </p>
      </div>
    </div>
  );
}
