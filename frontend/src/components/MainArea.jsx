import { useState, useEffect, useRef } from "react";
import useStream from "../hooks/useStream";
import { get, post } from "../utils/api";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import GoalForm from "./GoalForm";
import ChatThread from "./ChatThread";

function fmt(n) {
  return n.replace(/([A-Z])/g, " $1").trim();
}

function dl(content) {
  const blob = new Blob([content], { type: "text/plain" });
  const u = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = u; a.download = "report.txt"; a.click();
  URL.revokeObjectURL(u);
}

export default function MainArea({ goalId, setGoalId, activeGoalId, setActiveGoalId, sidebarOpen }) {
  const [isRunning, setIsRunning] = useState(false);
  const [data, setData] = useState(null);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMsgs, setChatMsgs] = useState([]);
  const chatBottom = useRef(null);
  const fullText = "Autonomous Multi-Agent AI Research & Execution System";
  const [displayText, setDisplayText] = useState("");
  const [idx, setIdx] = useState(0);
  const [fwd, setFwd] = useState(true);
  const active = activeGoalId || goalId;
  const logs = useStream(active, isRunning);
  const bottom = useRef(null);
  const timer = useRef(null);
  const pauseRef = useRef(false);
  const transitioned = useRef(false);

  useEffect(() => {
    const t = setInterval(() => {
      if (pauseRef.current) return;
      setIdx((i) => {
        if (fwd) {
          const next = i + 1;
          setDisplayText(fullText.slice(0, next));
          if (next >= fullText.length) {
            pauseRef.current = true;
            setTimeout(() => { pauseRef.current = false; setFwd(false); }, 1000);
          }
          return next;
        } else {
          const next = i - 1;
          setDisplayText(fullText.slice(0, next));
          if (next <= 0) setFwd(true);
          return next;
        }
      });
    }, 60);
    return () => clearInterval(t);
  }, [fwd]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
    const last = logs[logs.length - 1];
    if (last && last.includes("workflow complete") && !transitioned.current) {
      transitioned.current = true;
      setIsRunning(false);
      if (active) setActiveGoalId(active);
    }
  }, [logs]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!active) { setData(null); return; }
    async function load() {
      try {
        const [session, goal] = await Promise.all([
          get(`/sessions/${active}`),
          get(`/goals/${active}`),
        ]);
        setData(session);
        console.log("status check:", goal.status);
        if (goal.status === "done" || goal.status === "failed") {
          clearInterval(timer.current);
          if (goal.status === "done" && !transitioned.current) {
            transitioned.current = true;
            setIsRunning(false);
            setActiveGoalId(active);
          }
        }
      } catch { clearInterval(timer.current); }
    }
    load();
    timer.current = setInterval(load, 1000);
    return () => clearInterval(timer.current);
  }, [active]);

  useEffect(() => {
    if (!activeGoalId) { setChatMsgs([]); return; }
    get("/goals/" + activeGoalId + "/messages").then(setChatMsgs).catch(() => {});
  }, [activeGoalId]);

  useEffect(() => {
    if (!activeGoalId) {
      localStorage.removeItem("ctx_url");
      localStorage.removeItem("ctx_domain");
      return;
    }
    get("/goals/" + activeGoalId).then((g) => {
      if (g.url) {
        localStorage.setItem("ctx_url", g.url);
        try {
          localStorage.setItem("ctx_domain", new URL(g.url).hostname);
        } catch {}
      } else {
        localStorage.removeItem("ctx_url");
        localStorage.removeItem("ctx_domain");
      }
    }).catch(() => {
      localStorage.removeItem("ctx_url");
      localStorage.removeItem("ctx_domain");
    });
  }, [activeGoalId]);

  useEffect(() => {
    chatBottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMsgs]);

  async function sendChat(e) {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;
    const q = chatInput.trim();
    setChatInput("");
    setChatLoading(true);
    setChatMsgs((prev) => [...prev, { id: Date.now(), role: "user", content: q }]);
    try {
      const ctxUrl = localStorage.getItem("ctx_url");
      const res = await axios.post("http://localhost:8000/goals/" + activeGoalId + "/chat", {
        query: q,
        ctx_url: ctxUrl || null,
      });
      setChatMsgs((prev) => [...prev, { id: Date.now() + 1, role: "assistant", content: res.data.response, images: res.data.images || [], images_first: res.data.images_first || false }]);
      if (res.data.used_search === true) {
        setGoalId(res.data.goal_id);
        setIsRunning(true);
      }
    } catch {}
    setChatLoading(false);
  }

  function onGoalSubmit(id) {
    transitioned.current = false;
    setGoalId(id);
    setActiveGoalId(null);
    setIsRunning(true);
    setData(null);
  }

  function msgColor(msg) {
    const m = msg.toLowerCase();
    if (m.includes("done") || m.includes("complete")) return "#10b981";
    if (m.includes("failed") || m.includes("error")) return "#ef4444";
    return "var(--accent)";
  }

  function dotColor(s) {
    if (s === "done") return "#10b981";
    if (s === "running") return "#FF781A";
    if (s === "failed") return "#ef4444";
    return "#444";
  }

  const mdComponents = {
    h1: ({ children }) => <h1 style={{ color: "var(--text)", fontWeight: 600, fontSize: "16px", margin: "12px 0 6px" }}>{children}</h1>,
    h2: ({ children }) => <h2 style={{ color: "var(--text)", fontWeight: 600, fontSize: "14px", margin: "10px 0 4px" }}>{children}</h2>,
    h3: ({ children }) => <h3 style={{ color: "var(--text)", fontWeight: 600, fontSize: "13px", margin: "8px 0 4px" }}>{children}</h3>,
    p: ({ children }) => <p style={{ color: "var(--text-muted)", fontSize: "13px", lineHeight: 1.7, margin: "4px 0" }}>{children}</p>,
    li: ({ children }) => <li style={{ color: "var(--text-muted)", fontSize: "13px" }}>{children}</li>,
    strong: ({ children }) => <strong style={{ color: "var(--accent)" }}>{children}</strong>,
    code: ({ children }) => <code className="mono" style={{ background: "#1a1a1a", color: "#10b981", padding: "2px 6px", borderRadius: "4px" }}>{children}</code>,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%" }}>
      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes gradientMove { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
        @keyframes spin { to{transform:rotate(360deg)} }
      `}</style>

      <div style={{
        background: "#0d0d0d",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "12px 24px",
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center" }}>
          <span className="mono" style={{
            fontSize: "15px",
            fontWeight: 400,
            background: "linear-gradient(90deg, #9333ea, #ffffff)",
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            color: "transparent",
            WebkitTextFillColor: "transparent",
          }}>
            {displayText}
          </span>
          <span style={{ color: "#9333ea", animation: "blink 0.8s infinite", fontWeight: 400, fontSize: "15px" }}>|</span>
        </div>
        <div />
      </div>

      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {(isRunning || (activeGoalId && chatMsgs.length === 0 && !data)) ? (
          <div style={{ flex: 1, position: "relative" }}>
            <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", display: "flex", flexDirection: "column", alignItems: "center", gap: "14px" }}>
              <div style={{ width: "32px", height: "32px", border: "3px solid rgba(255,120,26,0.2)", borderTopColor: "var(--accent)", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
              <span className="mono" style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                {isRunning ? "Generating report..." : "Loading..."}
              </span>
            </div>
          </div>
        ) : activeGoalId ? (
          <>
            <div style={{
              flex: 1,
              margin: "8px",
              overflow: "hidden",
              borderRadius: "12px",
              border: "1px solid rgba(255,255,255,0.08)",
            }}>
              <ChatThread goalId={activeGoalId} extraMsgs={chatMsgs} loading={chatLoading} />
            </div>

            <div style={{ flexShrink: 0, padding: "12px 24px 20px", display: "flex", justifyContent: "center" }}>
              <form onSubmit={sendChat} style={{ width: "100%", maxWidth: "800px", display: "flex", gap: "8px" }}>
                <div style={{
                  flex: 1, padding: "1px", borderRadius: "16px",
                  background: chatInput ? "var(--accent)" : "rgba(255,255,255,0.12)",
                  transition: "background 0.2s",
                }}>
                  <input
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask about this report..."
                    style={{
                      width: "100%", background: "#0d0d0d", border: "none",
                      borderRadius: "15px", color: "var(--text)", padding: "14px 16px",
                      fontFamily: "Inter, sans-serif", fontSize: "14px", outline: "none",
                      boxSizing: "border-box",
                    }}
                  />
                </div>
                <button type="submit" disabled={chatLoading} style={{
                  width: "44px", height: "44px", borderRadius: "50%",
                  background: "var(--accent)", border: "none", color: "#fff",
                  cursor: chatLoading ? "not-allowed" : "pointer", fontSize: "16px",
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                }}>
                  {chatLoading
                    ? <div style={{ width: "16px", height: "16px", border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
                    : "➤"}
                </button>
              </form>
            </div>
          </>
        ) : goalId ? (
          <>
            <div style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              background: "#0d0d0d",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "12px",
              margin: "8px",
              overflow: "hidden",
            }}>
              <div style={{ borderBottom: "1px solid var(--border)", padding: "12px 20px", flexShrink: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                  <div style={{
                    width: "8px", height: "8px", borderRadius: "50%",
                    background: logs.length > 0 ? "#10b981" : "#444",
                    animation: logs.length > 0 ? "blink 1s infinite" : "none",
                    flexShrink: 0,
                  }} />
                  <span className="mono" style={{ color: "var(--accent)", fontSize: "13px", fontWeight: 600 }}>Agent Log</span>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {logs.length === 0 && (
                    <span className="mono" style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                      ❯ Waiting for agent activity...
                    </span>
                  )}
                  {logs.map((msg, i) => (
                    <div key={i} className="mono" style={{
                      display: "inline-flex", alignItems: "center",
                      background: "#111", border: "1px solid var(--border)",
                      borderRadius: "20px", padding: "4px 12px",
                      fontSize: "12px", color: msgColor(msg),
                    }}>
                      ❯ {msg}
                    </div>
                  ))}
                  <div ref={bottom} />
                </div>
              </div>

              {data && data.tasks && data.tasks.length > 0 && (
                <div style={{ borderBottom: "1px solid var(--border)", padding: "12px 20px", flexShrink: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                    <span className="mono" style={{ color: "var(--accent)", fontSize: "13px", fontWeight: 600 }}>Report</span>
                    {data.report && (
                      <button
                        onClick={() => dl(data.report.content)}
                        style={{ background: "transparent", border: "1px solid var(--accent)", color: "var(--accent)", borderRadius: "6px", padding: "3px 12px", fontSize: "11px", cursor: "pointer" }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = "var(--accent)"; e.currentTarget.style.color = "#fff"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--accent)"; }}
                      >
                        Download
                      </button>
                    )}
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {data.tasks.map((t, i) => (
                      <div key={i} className="mono" style={{
                        display: "inline-flex", alignItems: "center", gap: "6px",
                        background: "#1a1a1a", border: "1px solid var(--border)",
                        borderRadius: "20px", padding: "5px 14px", fontSize: "12px",
                      }}>
                        <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: dotColor(t.status), flexShrink: 0 }} />
                        <span style={{ color: "var(--text)" }}>{fmt(t.name)}</span>
                        <span style={{ color: "var(--text-muted)" }}>{t.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
                {!data || !data.report ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
                    <span className="mono" style={{ color: "var(--text-muted)", fontSize: "12px" }}>❯ Report will appear here...</span>
                  </div>
                ) : (
                  <div style={{
                    padding: "1px", borderRadius: "8px",
                    background: "linear-gradient(90deg, #9333ea, #9333ea, #fff, #9333ea)",
                    backgroundSize: "200% 200%",
                    animation: "gradientMove 3s ease infinite",
                  }}>
                    <div style={{ background: "#050505", borderRadius: "7px", padding: "16px", minHeight: "200px" }}>
                      <ReactMarkdown components={mdComponents}>{data.report.content}</ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {data && data.report && (
              <div style={{ flexShrink: 0, padding: "12px 24px 20px", display: "flex", justifyContent: "center" }}>
                <form onSubmit={sendChat} style={{ width: "100%", maxWidth: "800px", display: "flex", gap: "8px" }}>
                  <div style={{
                    flex: 1, padding: "1px", borderRadius: "16px",
                    background: chatInput ? "var(--accent)" : "rgba(255,255,255,0.12)",
                    transition: "background 0.2s",
                  }}>
                    <input
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Ask about this report..."
                      style={{
                        width: "100%", background: "#0d0d0d", border: "none",
                        borderRadius: "15px", color: "var(--text)", padding: "14px 16px",
                        fontFamily: "Inter, sans-serif", fontSize: "14px", outline: "none",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>
                  <button type="submit" disabled={chatLoading} style={{
                    width: "44px", height: "44px", borderRadius: "50%",
                    background: "var(--accent)", border: "none", color: "#fff",
                    cursor: chatLoading ? "not-allowed" : "pointer", fontSize: "16px",
                    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                  }}>
                    {chatLoading
                      ? <div style={{ width: "16px", height: "16px", border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
                      : "➤"}
                  </button>
                </form>
              </div>
            )}
          </>
        ) : (
          <div style={{
            flex: 1, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            gap: "16px", padding: "24px",
          }}>
            <span style={{ fontSize: "48px", color: "rgba(147,51,234,0.3)", lineHeight: 1 }}>◈</span>
            <h1 style={{
              background: "linear-gradient(90deg, #9333ea, #ffffff)",
              WebkitBackgroundClip: "text", backgroundClip: "text",
              color: "transparent", WebkitTextFillColor: "transparent",
              fontSize: "2.2rem", fontWeight: 700, textAlign: "center", margin: 0,
            }}>
              What can I do for you?
            </h1>
            <GoalForm
              setGoalId={onGoalSubmit}
              goalId={goalId}
              isRunning={isRunning}
              onSuccess={() => {}}
              onError={() => {}}
            />
            <span className="mono" style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              Autonomous research • Multi-agent execution • Smart reports
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
