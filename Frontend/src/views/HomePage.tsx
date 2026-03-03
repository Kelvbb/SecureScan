import { Link } from "react-router-dom";
import { Button } from "../components";

export function HomePage() {
  return (
    <div className="page home-page">
      <section className="hero">
        <h1>Analysez la sécurité de votre code</h1>
        <p className="lead">
          SecureScan orchestre les outils de sécurité open source, mappe les
          vulnérabilités sur l&apos;OWASP Top 10 et vous aide à corriger.
        </p>
        <div className="hero-actions">
          <Link to="/register">
            <Button>Commencer</Button>
          </Link>
          <Link to="/login">
            <Button variant="secondary">Connexion</Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
