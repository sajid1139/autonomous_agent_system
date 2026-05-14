import { useState } from "react";
import Home from "./pages/Home";
import Session from "./pages/Session";

export default function App() {
  const [goalId, setGoalId] = useState(null);

  if (goalId) return <Session goalId={goalId} setGoalId={setGoalId} />;
  return <Home setGoalId={setGoalId} />;
}
