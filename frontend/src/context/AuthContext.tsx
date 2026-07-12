import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { type Business, fetchMe, login as loginRequest, logoutRequest } from "../api/auth";

interface AuthContextValue {
  business: Business | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then(setBusiness)
      .catch(() => localStorage.removeItem("access_token"))
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const token = await loginRequest(email, password);
    localStorage.setItem("access_token", token);
    setBusiness(await fetchMe());
  }

  async function logout() {
    try {
      await logoutRequest();
    } catch {
      // Best-effort server-side revocation; always clear local session regardless.
    }
    localStorage.removeItem("access_token");
    setBusiness(null);
  }

  return (
    <AuthContext.Provider value={{ business, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
