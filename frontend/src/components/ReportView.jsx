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

  if (err) {
    return (
      <div className="flex items-center justify-center h-full text-red-400 text-sm">
        {err}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
        loading session...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto space-y-4 p-4">
      <div className="space-y-2">
        {data.tasks.length === 0 && (
          <p className="text-gray-500 text-sm">waiting for tasks...</p>
        )}
        {data.tasks.map((t, i) => (
          <div
            key={i}
            className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3 border border-gray-700"
          >
            <span className="text-gray-200 text-sm font-medium">{fmt(t.name)}</span>
            <span
              className={`text-xs font-semibold px-2 py-1 rounded-full ${
                t.status === "done"
                  ? "bg-green-900 text-green-300"
                  : "bg-yellow-900 text-yellow-300"
              }`}
            >
              {t.status}
            </span>
          </div>
        ))}
      </div>
      {data.report && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-indigo-400 font-semibold text-sm">Final Report</h3>
            <button
              onClick={() => download(data.report.content)}
              className="text-xs text-gray-400 hover:text-white border border-gray-600 hover:border-gray-400 px-3 py-1 rounded-md transition-colors"
            >
              Download Report
            </button>
          </div>
          <div className="prose prose-invert prose-sm max-w-none text-gray-300">
            <ReactMarkdown>{data.report.content}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
