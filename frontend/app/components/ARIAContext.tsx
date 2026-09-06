"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

export interface ARIAContextValue {
  mode: "portfolio" | "project";
  projectId: string | null;
  projectName: string | null;
  setProjectContext: (id: string, name: string) => void;
  clearProjectContext: () => void;
}

const ARIACtx = createContext<ARIAContextValue>({
  mode: "portfolio",
  projectId: null,
  projectName: null,
  setProjectContext: () => {},
  clearProjectContext: () => {},
});

export function ARIAProvider({ children }: { children: ReactNode }) {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState<string | null>(null);

  const setProjectContext = useCallback((id: string, name: string) => {
    setProjectId(id);
    setProjectName(name);
  }, []);

  const clearProjectContext = useCallback(() => {
    setProjectId(null);
    setProjectName(null);
  }, []);

  return (
    <ARIACtx.Provider
      value={{
        mode: projectId ? "project" : "portfolio",
        projectId,
        projectName,
        setProjectContext,
        clearProjectContext,
      }}
    >
      {children}
    </ARIACtx.Provider>
  );
}

export function useARIA() {
  return useContext(ARIACtx);
}
