import { useState } from "react";
import { post } from "../utils/api";

const url_re = /https?:\/\/\S+/;

export default function GoalForm({ setGoalId, onSuccess, onError }) {
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
        if (hasUrl) {
          const match = text.match(url_re);
          if (match) {
            try {
              const domain = new URL(match[0]).hostname;
              localStorage.setItem("ctx_url", match[0]);
              localStorage.setItem("ctx_domain", domain);
            } catch {}
          }
        }
        onSuccess && onSuccess();
        setGoalId(res.goal_id);
      } else {
        onSuccess && onSuccess();
      }
    } catch {
      onError && onError();
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4 w-full max-w-2xl">
      <textarea
        className="w-full h-36 bg-gray-800 text-gray-100 border border-gray-600 rounded-lg p-4 resize-none focus:outline-none focus:border-indigo-500 placeholder-gray-500"
        placeholder="Enter a goal, paste a URL, or type a URL + question..."
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        type="submit"
        disabled={loading}
        className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold py-3 rounded-lg transition-colors"
      >
        {loading ? "Working..." : "Run"}
      </button>
    </form>
  );
}
