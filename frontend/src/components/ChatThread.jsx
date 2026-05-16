import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import axios from "axios";

function fmtName(n) {
  return (n || "").replace(/([A-Z])/g, " $1").trim();
}

function pillColor(s) {
  const m = (s || "").toLowerCase();
  if (m.includes("done") || m.includes("complete")) return "#10b981";
  if (m.includes("failed") || m.includes("error")) return "#ef4444";
  return "#FF781A";
}

function dotColor(s) {
  if (s === "done") return "#10b981";
  if (s === "running") return "#FF781A";
  if (s === "failed") return "#ef4444";
  return "#444";
}

const mdComp = {
  p: ({ children }) => <p style={{ margin: "0 0 6px", lineHeight: 1.6 }}>{children}</p>,
  h1: ({ children }) => <h1 style={{ fontSize: "15px", fontWeight: 600, margin: "10px 0 4px", color: "var(--text)" }}>{children}</h1>,
  h2: ({ children }) => <h2 style={{ fontSize: "13px", fontWeight: 600, margin: "8px 0 4px", color: "var(--text)" }}>{children}</h2>,
  h3: ({ children }) => <h3 style={{ fontSize: "12px", fontWeight: 600, margin: "6px 0 4px", color: "var(--text)" }}>{children}</h3>,
  li: ({ children }) => <li style={{ lineHeight: 1.6, color: "var(--text-muted)" }}>{children}</li>,
  strong: ({ children }) => <strong style={{ color: "var(--accent)" }}>{children}</strong>,
  code: ({ children }) => <code style={{ background: "rgba(0,0,0,0.4)", color: "#10b981", padding: "1px 5px", borderRadius: "3px", fontSize: "12px" }}>{children}</code>,
};

export default function ChatThread({ goalId, extraMsgs = [], loading = false }) {
  const [msgs, setMsgs] = useState([]);
  const [report, setReport] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [fetching, setFetching] = useState(false);
  const bottom = useRef(null);
  const fetchedFor = useRef(null);

  useEffect(() => {
    if (!goalId || goalId === fetchedFor.current) return;
    fetchedFor.current = goalId;
    let aborted = false;
    setFetching(true);
    Promise.all([
      axios.get("http://localhost:8000/goals/" + goalId + "/messages"),
      axios.get("http://localhost:8000/sessions/" + goalId),
    ])
      .then(([msgRes, sesRes]) => {
        if (aborted) return;
        setMsgs(msgRes.data);
        setReport(sesRes.data?.report || null);
        setTasks(sesRes.data?.tasks || []);
      })
      .catch((e) => { if (!aborted) console.log("fetch error:", e.message); })
      .finally(() => { if (!aborted) setFetching(false); });
    return () => { aborted = true; };
  }, [goalId]);

  const allMsgs = [...msgs, ...extraMsgs];
  const prevLen = useRef(0);

  useEffect(() => {
    const cur = allMsgs.length;
    if (cur > prevLen.current) {
      bottom.current?.scrollIntoView({ behavior: "smooth" });
    }
    prevLen.current = cur;
  }, [allMsgs.length]);

  useEffect(() => {
    if (loading) bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [loading]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#050505", borderRadius: "8px", overflow: "hidden" }}>
      <style>{`@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}`}</style>

      {tasks.length > 0 && (
        <div style={{
          display: "flex",
          gap: "0",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}>
          <div style={{
            flex: 1,
            padding: "10px 14px",
            borderRight: "1px solid var(--border)",
            minWidth: 0,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
              <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: "#10b981", display: "inline-block", flexShrink: 0 }} />
              <span className="mono" style={{ color: "var(--accent)", fontSize: "11px", fontWeight: 600 }}>Agent Log</span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
              {tasks.map((t, i) => (
                <div key={i} className="mono" style={{
                  display: "inline-flex", alignItems: "center", gap: "5px",
                  background: "#111", border: "1px solid var(--border)",
                  borderRadius: "20px", padding: "3px 10px", fontSize: "11px",
                  color: pillColor(t.status),
                }}>
                  ❯ {fmtName(t.name)} {t.status}
                </div>
              ))}
            </div>
          </div>

          <div style={{ flex: 1, padding: "10px 14px", minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
              <span className="mono" style={{ color: "var(--accent)", fontSize: "11px", fontWeight: 600 }}>Report</span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
              {tasks.map((t, i) => (
                <div key={i} className="mono" style={{
                  display: "inline-flex", alignItems: "center", gap: "5px",
                  background: "#1a1a1a", border: "1px solid var(--border)",
                  borderRadius: "20px", padding: "3px 10px", fontSize: "11px",
                }}>
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: dotColor(t.status), flexShrink: 0 }} />
                  <span style={{ color: "var(--text)" }}>{fmtName(t.name)}</span>
                  <span style={{ color: "var(--text-muted)" }}>{t.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        minHeight: 0,
      }}>
        {fetching && (
          <span className="mono" style={{ color: "var(--text-muted)", fontSize: "12px", alignSelf: "center" }}>
            Loading...
          </span>
        )}

        {!fetching && report?.content && (
          <div style={{
            alignSelf: "flex-start",
            background: "#1a1a1a",
            color: "var(--text)",
            borderRadius: "12px 12px 12px 2px",
            padding: "12px 16px",
            maxWidth: "85%",
            fontSize: "13px",
            lineHeight: 1.6,
            border: "1px solid rgba(255,120,26,0.2)",
          }}>
            <ReactMarkdown components={mdComp}>{report.content}</ReactMarkdown>
          </div>
        )}

        {!fetching && !report?.content && allMsgs.length === 0 && (
          <span className="mono" style={{ color: "var(--text-muted)", fontSize: "12px", alignSelf: "center" }}>
            ❯ No messages yet
          </span>
        )}

        {allMsgs.map((m) => {
          const hasImgs = m.role === "assistant" && m.images && m.images.length > 0;
          const pageImgs = hasImgs ? m.images.filter(s => !s.includes("_img_")) : [];
          const capImgs = hasImgs ? m.images.filter(s => s.includes("_img_")) : [];
          const imgFirst = m.images_first === true;

          const textBubble = (
            <div style={{
              background: m.role === "user" ? "var(--accent)" : "#1a1a1a",
              color: m.role === "user" ? "#fff" : "var(--text)",
              borderRadius: m.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
              padding: "10px 14px",
              fontSize: "13px",
              lineHeight: 1.6,
            }}>
              {m.role === "user"
                ? m.content
                : <ReactMarkdown components={mdComp}>{m.content}</ReactMarkdown>}
            </div>
          );

          const imgBlocks = (
            <>
              {pageImgs.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <span className="mono" style={{ fontSize: "11px", color: "var(--text-muted)" }}>Page Screenshot</span>
                  {pageImgs.map((src, i) => (
                    <img key={i} src={"http://localhost:8000/static/screenshots/" + src.split("/").pop()} alt="page" style={{ width: "100%", borderRadius: "8px", border: "1px solid var(--border)" }} />
                  ))}
                </div>
              )}
              {capImgs.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <span className="mono" style={{ fontSize: "11px", color: "var(--text-muted)" }}>Captured Images</span>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "6px" }}>
                    {capImgs.map((src, i) => (
                      <img key={i} src={"http://localhost:8000/static/screenshots/" + src.split("/").pop()} alt={"img " + i} style={{ width: "100%", borderRadius: "6px", border: "1px solid var(--border)" }} />
                    ))}
                  </div>
                </div>
              )}
            </>
          );

          return (
            <div key={m.id} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "85%", display: "flex", flexDirection: "column", gap: "8px" }}>
              {imgFirst ? <>{imgBlocks}{textBubble}</> : <>{textBubble}{imgBlocks}</>}
            </div>
          );
        })}

        {loading && (
          <div style={{
            alignSelf: "flex-start", background: "#1a1a1a",
            borderRadius: "12px 12px 12px 2px", padding: "10px 14px",
            fontSize: "13px", color: "var(--text-muted)",
          }}>
            <span style={{ animation: "blink 1s infinite" }}>thinking...</span>
          </div>
        )}

        <div ref={bottom} />
      </div>
    </div>
  );
}
