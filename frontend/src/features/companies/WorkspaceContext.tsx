import { createContext, useContext, type ReactNode } from "react";
import type { CompanyRole } from "@/types/api";

const WorkspaceContext = createContext<{
  companyId: string;
  role: CompanyRole;
  canManage: boolean;
} | null>(null);

export function WorkspaceProvider({
  companyId,
  role,
  children,
}: {
  companyId: string;
  role: CompanyRole;
  children: ReactNode;
}) {
  return (
    <WorkspaceContext.Provider
      value={{
        companyId,
        role,
        canManage: role === "OWNER" || role === "ADMIN",
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return value;
}
