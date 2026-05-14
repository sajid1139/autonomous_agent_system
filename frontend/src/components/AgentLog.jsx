import { useEffect, useRef } from "react";
import useStream from "../hooks/useStream";

export default function AgentLog({ goalId, onDone }) {
  const logs = useStream(goalId);
  const bottom = useRef(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
    const last = logs[logs.length - 1];
    if (last && last.includes("workflow complete") && onDone) {
      onDone();
    }
  }, [logs]);

  return (
    <div className="flex flex-col h-full bg-black rounded-lg border border-gray-700 overflow-hidden">
      <div className="px-4 py-2 bg-gray-900 text-gray-400 text-sm font-mono border-b border-gray-700">
        agent log
      </div>
      <div className="flex-1 overflow-y-auto p-4 font-mono text-sm text-green-400 space-y-1">
        {logs.length === 0 && (
          <span className="text-gray-600">waiting for agent...</span>
        )}
        {logs.map((msg, i) => (
          <div key={i}>&gt; {msg}</div>
        ))}
        <div ref={bottom} />
      </div>
    </div>
  );
}
