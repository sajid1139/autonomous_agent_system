import { useEffect, useState } from "react";

export default function Sidebar({ sidebarOpen, setSidebarOpen, goalId, setGoalId, activeGoalId, setActiveGoalId }) {
  const [goals, setGoals] = useState([]);

  useEffect(() => {
    console.log("useEffect fired");
    fetch("http://localhost:8000/goals").then(r => r.json()).then(data => {
      console.log("goals loaded:", data.length);
      setGoals([...data].sort((a, b) => new Date(b.created) - new Date(a.created)));
    }).catch(e => console.log("error:", e.message));
  }, [goalId]);

  function fmt(d) {
    return new Date(d).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  function trunc(t) {
    const words = (t || "").trim().split(/\s+/);
    return words.length <= 5 ? t : words.slice(0, 5).join(" ") + "...";
  }

  console.log("rendering goals:", goals.length);

  return (
    <div style={{
      background: "#161616",
      borderRight: "1px solid rgba(255,255,255,0.08)",
      width: "100%",
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    }}>

      <div style={{
        padding: "16px 12px",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: sidebarOpen ? "space-between" : "center",
        }}>
          {sidebarOpen && (
            <span className="mono" style={{
              color: "var(--accent)",
              fontWeight: 800,
              fontSize: "20px",
              whiteSpace: "nowrap",
            }}>
              <span style={{ fontSize: "22px", marginRight: "6px" }}>◈</span>AMAR
            </span>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            style={{
              width: "28px",
              height: "28px",
              background: "var(--accent)",
              border: "none",
              borderRadius: "6px",
              color: "#fff",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "11px",
              flexShrink: 0,
              transition: "background 0.15s",
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = "var(--accent-hover)"}
            onMouseLeave={(e) => e.currentTarget.style.background = "var(--accent)"}
          >
            {sidebarOpen ? "◀" : "▶"}
          </button>
        </div>

        <button
          onClick={() => { setGoalId(null); setActiveGoalId(null); }}
          style={{
            background: "var(--accent)",
            border: "none",
            cursor: "pointer",
            color: "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: sidebarOpen ? "flex-start" : "center",
            gap: "6px",
            padding: "10px",
            borderRadius: "8px",
            fontWeight: 600,
            fontSize: "13px",
            width: "100%",
            marginTop: "12px",
            whiteSpace: "nowrap",
            overflow: "hidden",
            transition: "background 0.15s",
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = "var(--accent-hover)"}
          onMouseLeave={(e) => e.currentTarget.style.background = "var(--accent)"}
        >
          <span style={{ fontSize: "15px", lineHeight: 1, flexShrink: 0 }}>＋</span>
          {sidebarOpen && <span>New Goal</span>}
        </button>
      </div>

      <div className="sidebar-scroll" style={{ flex: 1, overflowY: "auto", overflowX: "hidden" }}>
        {sidebarOpen && (
          <div style={{
            position: "sticky",
            top: 0,
            background: "#161616",
            zIndex: 1,
            color: "var(--text-muted)",
            fontSize: "10px",
            padding: "12px 12px 8px",
            textTransform: "uppercase",
            letterSpacing: "1.5px",
            marginBottom: "15px",
          }}>
            All Goals
          </div>
        )}
        <div style={{ padding: "0 8px" }}>
          {goals.length === 0 && sidebarOpen && (
            <div style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              padding: "24px 12px",
            }}>
              <span style={{ fontSize: "24px", color: "var(--border)" }}>◈</span>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px" }}>No goals yet</span>
            </div>
          )}
          {goals.map((g) => (
            <button
              key={g.id}
              onClick={() => setActiveGoalId(g.id)}
              style={{
                width: "100%",
                background: activeGoalId === g.id ? "rgba(147,51,234,0.15)" : "transparent",
                border: "none",
                borderLeft: activeGoalId === g.id ? "2px solid #9333ea" : "2px solid transparent",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "6px 10px",
                justifyContent: sidebarOpen ? "flex-start" : "center",
                borderRadius: "8px",
                marginBottom: "2px",
                transition: "background 0.15s",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(147,51,234,0.1)"; e.currentTarget.style.borderLeft = "2px solid #9333ea"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = activeGoalId === g.id ? "rgba(147,51,234,0.15)" : "transparent"; e.currentTarget.style.borderLeft = activeGoalId === g.id ? "2px solid #9333ea" : "2px solid transparent"; }}
            >
              <span style={{ fontSize: "14px", color: "#9333ea", flexShrink: 0 }}>◎</span>
              {sidebarOpen && (
                <div style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "flex-start",
                  overflow: "hidden",
                  flex: 1,
                }}>
                  <span style={{
                    fontSize: "12px",
                    color: "var(--text)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    width: "100%",
                    textAlign: "left",
                  }}>
                    {trunc(g.text)}
                  </span>
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      <div style={{
        borderTop: "1px solid var(--border)",
        padding: "0 0 8px",
        marginTop: "auto",
        flexShrink: 0,
      }}>
        <button
          style={{
            background: "#1a1a1a",
            border: "1px solid var(--border)",
            borderRadius: "10px",
            padding: "10px 12px",
            margin: "8px",
            width: "calc(100% - 16px)",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            justifyContent: sidebarOpen ? "flex-start" : "center",
            cursor: "pointer",
            color: "var(--text-muted)",
            transition: "background 0.15s, color 0.15s",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = "#222"; e.currentTarget.style.color = "var(--accent)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "#1a1a1a"; e.currentTarget.style.color = "var(--text-muted)"; }}
          title="Settings"
        >
          <span style={{ fontSize: "16px", lineHeight: 1, flexShrink: 0 }}>⚙</span>
          {sidebarOpen && <span style={{ fontSize: "12px" }}>Settings</span>}
        </button>
      </div>
    </div>
  );
}
