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

  function msgColor(msg) {
    const m = msg.toLowerCase();
    if (m.includes("done") || m.includes("complete")) return "#10b981";
    if (m.includes("failed") || m.includes("error")) return "#ef4444";
    return "#9333ea";
  }

  const active = logs.length > 0;

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      height: "100%",
      background: "#050505",
      borderRadius: "8px",
      overflow: "hidden",
    }}>
      <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>

      <div style={{
        background: "#0d0d0d",
        borderBottom: "1px solid var(--border)",
        padding: "10px 16px",
        display: "flex",
        alignItems: "center",
        gap: "8px",
        flexShrink: 0,
      }}>
        <div style={{
          width: "8px",
          height: "8px",
          borderRadius: "50%",
          background: active ? "#9333ea" : "#444",
          animation: active ? "blink 1s infinite" : "none",
          flexShrink: 0,
        }} />
        <span className="mono" style={{ color: "#9333ea", fontSize: "12px" }}>
          Agent Log
        </span>
      </div>

      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: "12px 16px",
        display: "flex",
        flexWrap: "wrap",
        alignItems: "flex-start",
        alignContent: "flex-start",
      }}>
        {logs.length === 0 && (
          <span className="mono" style={{ color: "var(--text-muted)", fontSize: "12px" }}>
            ❯ Waiting for agent activity...
          </span>
        )}
        {logs.map((msg, i) => (
          <div key={i} className="mono" style={{
            display: "inline-flex",
            alignItems: "center",
            background: "#0d0d0d",
            border: "1px solid var(--border)",
            borderRadius: "20px",
            padding: "4px 12px",
            fontSize: "11px",
            margin: "4px",
            color: msgColor(msg),
          }}>
            ❯ {msg}
          </div>
        ))}
        <div ref={bottom} />
      </div>
    </div>
  );
}
