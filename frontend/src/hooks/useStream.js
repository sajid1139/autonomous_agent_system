import { useEffect, useState } from "react";

export default function useStream(goalId, active) {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    if (!goalId || !active) return;
    setLogs([]);
    const ws = new WebSocket(`ws://localhost:8000/ws/${goalId}`);
    ws.onmessage = (e) => setLogs((prev) => [...prev, e.data]);
    return () => ws.close();
  }, [goalId, active]);

  return logs;
}
