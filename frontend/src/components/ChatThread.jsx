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

export default function ChatThread({ goalId, loading = false }) {
  const [msgs, setMsgs] = useState([]);
  const [report, setReport] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [fetching, setFetching] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const bottom = useRef(null);

  useEffect(() => {
    if (!goalId) return;
    console.log("ChatThread fetching for:", goalId);
    let aborted = false;
    setFetching(true);
    Promise.all([
      axios.get("http://localhost:8000/goals/" + goalId + "/messages"),
      axios.get("http://localhost:8000/sessions/" + goalId),
    ])
      .then(([msgRes, sesRes]) => {
        if (aborted) return;
        console.log("ChatThread messages response:", msgRes.data);
        console.log("ChatThread session response:", sesRes.data);
        setMsgs(msgRes.data);
        setReport(sesRes.data?.report || null);
        setTasks(sesRes.data?.tasks || []);
        console.log("ChatThread fetching done");
        setFetching(false);
      })
      .catch((e) => { 
        if (!aborted) {
          console.log("ChatThread fetch error:", e);
          console.log("ChatThread fetching done");
          setFetching(false);
        }
      });
    return () => { aborted = true; };
  }, [goalId]);

  const fetchMessages = async () => {
    if (!goalId) return;
    try {
      const res = await axios.get("http://localhost:8000/goals/" + goalId + "/messages");
      setMsgs(res.data);
    } catch (e) {
      console.log("Message fetch error:", e);
    }
  };

  async function sendChat(e) {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;
    const q = chatInput.trim();
    setChatInput("");
    setChatLoading(true);
    try {
      const ctxUrl = localStorage.getItem("ctx_url");
      const res = await axios.post("http://localhost:8000/goals/" + goalId + "/chat", {
        query: q,
        ctx_url: ctxUrl || null,
      });
      console.log("chat response:", res.data);
      await fetchMessages();
    } catch (e) {
      console.log("Chat error:", e);
    }
    setChatLoading(false);
  }

  const allMsgs = (() => {
    const seen = new Set();
    const deduped = [];
    
    msgs.forEach(m => {
      const key = `${m.role}:${m.content}`;
      if (!seen.has(key)) {
        seen.add(key);
        deduped.push(m);
      }
    });
    
    return deduped.sort((a, b) => {
      const aTime = a.created ? new Date(a.created).getTime() : 0;
      const bTime = b.created ? new Date(b.created).getTime() : 0;
      return aTime - bTime;
    });
  })();
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
      <style>{`@keyframes blink{0%,100%{opacity:1}50%{opacity:0}} @keyframes spin{to{transform:rotate(360deg)}}`}</style>

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

        {!fetching && !loading && !report?.content && allMsgs.length === 0 && (
          <span className="mono" style={{ color: "var(--text-muted)", fontSize: "12px", alignSelf: "center" }}>
            ❯ No messages yet
          </span>
        )}

        {allMsgs.map((m) => {
          console.log("MSG:", m.id, "images:", m.images, "descriptions:", m.descriptions);
          const hasContact = m.role === "assistant" && m.contact;
          const hasSocial = m.role === "assistant" && m.social && m.social.length > 0;
          const hasNav = m.role === "assistant" && m.navigation && m.navigation.length > 0;

          const extraData = (
            <>
              {hasContact && (
                <div style={{ background: "#111", border: "1px solid var(--border)", borderRadius: "8px", padding: "10px", fontSize: "12px" }}>
                  <div style={{ color: "var(--accent)", fontWeight: 600, marginBottom: "6px" }}>Contact Info</div>
                  {m.contact.email && <div style={{ color: "var(--text)" }}>Email: {m.contact.email}</div>}
                  {m.contact.phone && <div style={{ color: "var(--text)" }}>Phone: {m.contact.phone}</div>}
                  {m.contact.address && <div style={{ color: "var(--text)" }}>Address: {m.contact.address}</div>}
                </div>
              )}
              {hasSocial && (
                <div style={{ background: "#111", border: "1px solid var(--border)", borderRadius: "8px", padding: "10px", fontSize: "12px" }}>
                  <div style={{ color: "var(--accent)", fontWeight: 600, marginBottom: "6px" }}>Social Links</div>
                  {m.social.map((link, i) => (
                    <div key={i} style={{ color: "var(--text)", marginBottom: "2px" }}>
                      {link.platform}: <a href={link.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)" }}>{link.url}</a>
                    </div>
                  ))}
                </div>
              )}
              {hasNav && (
                <div style={{ background: "#111", border: "1px solid var(--border)", borderRadius: "8px", padding: "10px", fontSize: "12px" }}>
                  <div style={{ color: "var(--accent)", fontWeight: 600, marginBottom: "6px" }}>Navigation</div>
                  {m.navigation.map((nav, i) => (
                    <div key={i} style={{ color: "var(--text)", marginBottom: "2px" }}>
                      {nav.label}: <a href={nav.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)" }}>{nav.url}</a>
                    </div>
                  ))}
                </div>
              )}
            </>
          );

          return (
            <div key={m.id} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "70%", display: "flex", flexDirection: "column", gap: "8px" }}>
              <div style={{background: m.role==="user" ? "var(--accent)" : "#1a1a1a", borderRadius:"12px", padding:"12px 16px"}}>
                {m.role === "user" ? m.content : <ReactMarkdown components={mdComp}>{m.content}</ReactMarkdown>}
                {m.images && m.images.length > 0 && (
                  <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(220px, 1fr))", gap:"12px", marginTop:"16px"}}>
                    {m.images.map((img, i) => (
                      <div key={i} style={{borderRadius:"8px", overflow:"hidden", boxShadow:"0 2px 6px rgba(0,0,0,0.1)", background:"#fff"}}>
                        <img src={img} alt={`Image ${i+1}`} style={{width:"100%", height:"160px", objectFit:"cover", display:"block"}} />
                        {m.descriptions && m.descriptions[i] && (
                          <div style={{padding:"8px 10px", fontSize:"12px", color:"#444"}}>
                            {m.descriptions[i]}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {extraData}
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

      <div style={{ flexShrink: 0, padding: "12px 16px", display: "flex", justifyContent: "center" }}>
        <form onSubmit={sendChat} style={{ width: "100%", display: "flex", gap: "8px" }}>
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
                width: "100%", background: "#050505", border: "none",
                borderRadius: "15px", color: "var(--text)", padding: "12px 16px",
                fontFamily: "Inter, sans-serif", fontSize: "13px", outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>
          <button type="submit" disabled={chatLoading} style={{
            width: "40px", height: "40px", borderRadius: "50%",
            background: "var(--accent)", border: "none", color: "#fff",
            cursor: chatLoading ? "not-allowed" : "pointer", fontSize: "14px",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            {chatLoading
              ? <div style={{ width: "14px", height: "14px", border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
              : "➤"}
          </button>
        </form>
      </div>
    </div>
  );
}
