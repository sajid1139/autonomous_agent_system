import { useEffect, useState, useRef } from "react";
import { get } from "../utils/api";
import ReactMarkdown from "react-markdown";

function fmt(name) {
  return name.replace(/([A-Z])/g, " $1").trim();
}

function download(content) {
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "report.txt";
  a.click();
  URL.revokeObjectURL(url);
}

export default function ReportView({ goalId }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [imgs, setImgs] = useState([]);
  const timer = useRef(null);

  async function load() {
    try {
      const [session, goal] = await Promise.all([
        get(`/sessions/${goalId}`),
        get(`/goals/${goalId}`),
      ]);
      setData(session);
      if (goal.status === "done" || goal.status === "failed") {
        clearInterval(timer.current);
        try {
          const ir = await get(`/goals/${goalId}/images`);
          setImgs(ir.images || []);
        } catch {}
      }
    } catch {
      setErr("failed to load session");
      clearInterval(timer.current);
    }
  }

  useEffect(() => {
    if (!goalId) return;
    load();
    timer.current = setInterval(load, 3000);
    return () => clearInterval(timer.current);
  }, [goalId]);

  function dotColor(s) {
    if (s === "done") return "#10b981";
    if (s === "running") return "#9333ea";
    if (s === "failed") return "#ef4444";
    return "#444";
  }

  const mdComponents = {
    h1: ({ children }) => <h1 style={{ color: "#ffffff", fontWeight: 700, fontSize: "16px", margin: "12px 0 6px" }}>{children}</h1>,
    h2: ({ children }) => <h2 style={{ color: "#9333ea", fontWeight: 700, fontSize: "14px", margin: "10px 0 4px" }}>{children}</h2>,
    h3: ({ children }) => <h3 style={{ color: "#ffffff", fontWeight: 700, fontSize: "13px", margin: "8px 0 4px" }}>{children}</h3>,
    p: ({ children }) => <p style={{ color: "#e2e8f0", fontSize: "13px", lineHeight: 1.7, margin: "4px 0" }}>{children}</p>,
    li: ({ children }) => <li style={{ color: "#e2e8f0", fontSize: "13px" }}>{children}</li>,
    ul: ({ children }) => <ul style={{ paddingLeft: "20px", color: "#e2e8f0" }}>{children}</ul>,
    ol: ({ children }) => <ol style={{ paddingLeft: "20px", color: "#e2e8f0" }}>{children}</ol>,
    strong: ({ children }) => <strong style={{ color: "#ffffff", fontWeight: 700 }}>{children}</strong>,
    hr: () => <hr style={{ borderColor: "rgba(255,255,255,0.1)", borderStyle: "solid", borderWidth: "1px 0 0 0", margin: "12px 0" }} />,
    a: ({ children, href }) => <a href={href} style={{ color: "#9333ea" }} target="_blank" rel="noreferrer">{children}</a>,
    code: ({ children }) => <code className="mono" style={{ background: "#1a1a1a", color: "#10b981", padding: "2px 6px", borderRadius: "4px" }}>{children}</code>,
  };

  if (err) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", background: "#050505", borderRadius: "8px" }}>
        <span className="mono" style={{ color: "#ef4444", fontSize: "12px" }}>❯ {err}</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", background: "#050505", borderRadius: "8px" }}>
        <span className="mono" style={{ color: "var(--text-muted)", fontSize: "12px" }}>❯ Loading session...</span>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#050505", borderRadius: "8px", overflow: "hidden" }}>
      <div style={{
        background: "#0d0d0d",
        borderBottom: "1px solid var(--border)",
        padding: "10px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0,
      }}>
        <span className="mono" style={{ color: "var(--accent)", fontSize: "12px" }}>Report</span>
        {data.report && (
          <button
            onClick={() => download(data.report.content)}
            style={{
              background: "transparent",
              border: "1px solid var(--accent)",
              color: "var(--accent)",
              borderRadius: "6px",
              padding: "4px 12px",
              fontSize: "11px",
              cursor: "pointer",
              transition: "background 0.15s, color 0.15s",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "var(--accent)"; e.currentTarget.style.color = "#fff"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--accent)"; }}
          >
            Download
          </button>
        )}
      </div>

      {data.tasks.length > 0 && (
        <div style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          flexWrap: "wrap",
          gap: "8px",
          flexShrink: 0,
        }}>
          {data.tasks.map((t, i) => (
            <div key={i} className="mono" style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              background: "#0d0d0d",
              border: "1px solid var(--border)",
              borderRadius: "20px",
              padding: "4px 12px",
              fontSize: "11px",
            }}>
              <div style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: dotColor(t.status),
                flexShrink: 0,
              }} />
              <span style={{ color: "var(--text)" }}>{fmt(t.name)}</span>
              <span style={{ color: "var(--text-muted)" }}>{t.status}</span>
            </div>
          ))}
        </div>
      )}

      <style>{`@keyframes gradientMove { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }`}</style>

      <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
        {!data.report ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
            <span className="mono" style={{ color: "var(--text-muted)", fontSize: "12px" }}>❯ Report will appear here...</span>
          </div>
        ) : (
          <div style={{
            position: "relative",
            padding: "1px",
            borderRadius: "8px",
            background: "linear-gradient(90deg, rgba(255,255,255,0.3), #ffffff, rgba(255,255,255,0.3))",
            backgroundSize: "200% 200%",
            animation: "gradientMove 3s ease infinite",
          }}>
            <div style={{
              background: "#050505",
              borderRadius: "7px",
              padding: "16px",
            }}>
              <ReactMarkdown components={mdComponents}>{data.report.content}</ReactMarkdown>
            </div>
          </div>
        )}

        {imgs.length > 0 && (
          <div style={{ marginTop: "16px" }}>
            {imgs.filter(s => s.includes("/static/screenshots/") && !s.includes("_img_")).slice(0, 1).map((src, i) => (
              <div key={"ss" + i} style={{ marginBottom: "16px" }}>
                <span className="mono" style={{ color: "#9333ea", fontSize: "12px", display: "block", marginBottom: "6px" }}>Page Screenshot</span>
                <img
                  src={src}
                  style={{ width: "100%", borderRadius: "6px", border: "1px solid var(--border)", display: "block" }}
                  onError={(e) => { e.target.style.display = "none"; }}
                />
              </div>
            ))}
            {imgs.filter(s => s.includes("_img_")).length > 0 && (
              <>
                <span className="mono" style={{ color: "#9333ea", fontSize: "12px", display: "block", marginBottom: "8px" }}>Captured Images</span>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px" }}>
                  {imgs.filter(s => s.includes("_img_")).map((src, i) => (
                    <img
                      key={i}
                      src={src}
                      style={{ width: "100%", borderRadius: "6px", objectFit: "cover", height: "120px", border: "1px solid var(--border)" }}
                      onError={(e) => { e.target.style.display = "none"; }}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
