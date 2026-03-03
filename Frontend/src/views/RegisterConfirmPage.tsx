import { Link } from "react-router-dom";
import { Button } from "../components";

export function RegisterConfirmPage() {
  return (
    <div className="page auth-page">
      <div className="auth-card confirm-card">
        <h1>Inscription confirmée</h1>
        <p className="text-muted">
          Votre compte a été créé. Veuillez vous connecter pour accéder à votre
          espace.
        </p>
        <Link to="/login">
          <Button className="full-width">Se connecter</Button>
        </Link>
      </div>
    </div>
  );
}
