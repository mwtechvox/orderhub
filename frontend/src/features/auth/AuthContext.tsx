import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, resetApiSession } from "@/lib/api-client";
import type { Me } from "@/types/api";
import { getMe, login, logout } from "./api";

type AuthValue = {
  user: Me | null;
  checking: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  setUser: React.Dispatch<React.SetStateAction<Me | null>>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [checking, setChecking] = useState(true);
  useEffect(() => {
    getMe()
      .then(setUser)
      .catch((error) => {
        if (error instanceof ApiError && [401, 403].includes(error.status)) setUser(null);
      })
      .finally(() => setChecking(false));
  }, []);
  const value = useMemo<AuthValue>(
    () => ({
      user,
      checking,
      setUser,
      signIn: async (username, password) => {
        await login(username, password);
        setUser(await getMe());
      },
      signOut: async () => {
        await logout().catch(() => null);
        resetApiSession();
        setUser(null);
      },
    }),
    [user, checking],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
