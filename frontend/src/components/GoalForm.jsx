import { useState } from "react";
import { post } from "../utils/api";

const url_re = /https?:\/\/\S+/;

export default function GoalForm({ setGoalId, goalId, isRunning, onSuccess, onError }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (!text.trim()) return;

    const hasUrl = url_re.test(text);
    const ctxUrl = localStorage.getItem("ctx_url");

    if (hasUrl && ctxUrl) {
      const match = text.match(url_re);
      if (match && match[0] !== ctxUrl) {
        onError && onError("Clear current context before submitting a new URL");
        return;
      }
    }

    setLoading(true);
    try {
      let res;

      if (!hasUrl && ctxUrl) {
        res = await post("/query-context", { url: ctxUrl, query: text });
      } else {
        res = await post("/goals", { text });
      }

      if (res.goal_id) {
        onSuccess && onSuccess();
        setGoalId(res.goal_id, res.status === "done");
      } else {
        onSuccess && onSuccess();
      }
    } catch {
      onError && onError();
    } finally {
      setLoading(false);
    }
  }

  const [focused, setFocused] = useState(false);

  const ctxUrl = typeof window !== "undefined" ? localStorage.getItem("ctx_url") : null;
  const ctxDomain = typeof window !== "undefined" ? localStorage.getItem("ctx_domain") : null;

  const inputBox = (
    <div style={{ position: "relative", width: "100%", maxWidth: "700px" }}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .amar-spinner { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
        .amar-input::placeholder { color: #555; }
      `}</style>
      {ctxUrl && ctxDomain && (
        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--accent)",
          borderRadius: "8px",
          color: "var(--accent)",
          padding: "8px 12px",
          fontSize: "12px",
          marginBottom: "10px",
          display: "flex",
          alignItems: "center",
        }}>
          <span>Context: <strong>{ctxDomain}</strong></span>
          <button
            onClick={() => { localStorage.removeItem("ctx_url"); localStorage.removeItem("ctx_domain"); window.location.reload(); }}
            style={{ background: "transparent", border: "1px solid var(--accent)", borderRadius: "4px", color: "var(--accent)", fontSize: "10px", padding: "2px 8px", cursor: "pointer", marginLeft: "8px" }}
          >Clear</button>
        </div>
      )}
      <div style={{
        position: "relative",
        padding: "1px",
        borderRadius: "16px",
        background: focused ? "var(--accent)" : "rgba(255,255,255,0.12)",
        transition: "background 0.2s ease",
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          background: "#0d0d0d",
          borderRadius: "15px",
          position: "relative",
          padding: "6px 6px 6px 8px",
        }}>
          <textarea
            className="amar-input"
            placeholder="Enter a goal, paste a URL, or type a URL + question..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(e); } }}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            rows={1}
            style={{
              background: "transparent",
              border: "none",
              borderRadius: "15px",
              color: "var(--text)",
              padding: "10px 12px",
              width: "100%",
              minHeight: "56px",
              fontFamily: "Inter, sans-serif",
              fontSize: "14px",
              resize: "none",
              outline: "none",
              boxSizing: "border-box",
              lineHeight: "1.5",
              flex: 1,
            }}
          />
          <button
            type="submit"
            disabled={loading || isRunning}
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "50%",
              background: "var(--accent)",
              color: "#fff",
              border: "none",
              cursor: (loading || isRunning) ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "14px",
              transition: "background 0.2s ease",
              flexShrink: 0,
              marginRight: "8px",
            }}
            onMouseEnter={(e) => { if (!loading && !isRunning) e.currentTarget.style.background = "var(--accent-hover)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "var(--accent)"; }}
          >
            {(loading || isRunning) ? <div className="amar-spinner" /> : "➤"}
          </button>
        </div>
      </div>
    </div>
  );

  if (!goalId) {
    return (
      <form
        onSubmit={submit}
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          width: "100%",
          maxWidth: "700px",
        }}
      >
        {inputBox}
      </form>
    );
  }

  return (
    <form
      onSubmit={submit}
      style={{ display: "flex", width: "100%", maxWidth: "700px" }}
    >
      {inputBox}
    </form>
  );
}
