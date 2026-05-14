import { createContext, useContext, useState } from "react";

const Ctx = createContext(null);

export function AppProvider({ children }) {
  const [goalId, setGoalId] = useState(null);
  return <Ctx.Provider value={{ goalId, setGoalId }}>{children}</Ctx.Provider>;
}

export function useApp() {
  return useContext(Ctx);
}

export default function AppCtx() {}
