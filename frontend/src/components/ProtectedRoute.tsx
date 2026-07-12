import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { business, loading } = useAuth();

  if (loading) return <div className="loading">Loading...</div>;
  if (!business) return <Navigate to="/login" replace />;

  return <>{children}</>;
}
