import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Logo from "./Logo";
import ThemeToggle from "./ThemeToggle";

export default function Layout() {
  const { business, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="dashboard-header">
        <div>
          <Logo to="/dashboard" className="app-logo" />
          <p>{business?.name}</p>
        </div>
        <div className="header-actions">
          <ThemeToggle />
          <button onClick={logout}>Log out</button>
        </div>
      </header>

      <nav className="app-nav">
        <NavLink to="/dashboard" end>
          Dashboard
        </NavLink>
        <NavLink to="/contacts">Contacts</NavLink>
        <NavLink to="/appointments">Appointments</NavLink>
        <NavLink to="/reminders">Reminders</NavLink>
      </nav>

      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
