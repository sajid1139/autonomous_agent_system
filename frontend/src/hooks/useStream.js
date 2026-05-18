import { useEffect, useState } from "react";

export default function useStream(goalId) {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    if (!goalId) return;
    setLogs([]);
    const ws = new WebSocket(`ws://localhost:8000/ws/${goalId}`);
    ws.onmessage = (e) => setLogs((prev) => [...prev, e.data]);
    return () => ws.close();
  }, [goalId]);

  return logs;
}
