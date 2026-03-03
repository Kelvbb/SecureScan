import { Link } from "react-router-dom";

export function VisitorHeader() {
  return (
    <header className="header">
      <div className="header-inner">
        <Link to="/" className="logo">
          SecureScan
        </Link>
        <nav className="nav">
          <Link to="/login">Connexion</Link>
          <Link to="/register" className="btn-nav">
            S'inscrire
          </Link>
        </nav>
      </div>
    </header>
  );
}
