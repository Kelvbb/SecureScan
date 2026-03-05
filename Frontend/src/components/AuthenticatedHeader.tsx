import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts";

export function AuthenticatedHeader() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <header className="header">
      <div className="header-inner">
        <Link to="/dashboard" className="logo">
          SecureScan
        </Link>
        <nav className="nav">
          <button
            type="button"
            className="btn-logout"
            onClick={handleLogout}
          >
            Déconnexion
          </button>
        </nav>
      </div>
    </header>
  );
}
