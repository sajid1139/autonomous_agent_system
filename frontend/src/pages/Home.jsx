import { useState, useEffect } from "react";
import GoalForm from "../components/GoalForm";

export default function Home({ setGoalId }) {
  const [toast, setToast] = useState(null);
  const [ctx, setCtx] = useState(null);

  useEffect(() => {
    const url = localStorage.getItem("ctx_url");
    const domain = localStorage.getItem("ctx_domain");
    if (url && domain) setCtx({ url, domain });
  }, []);

  function clearCtx() {
    localStorage.removeItem("ctx_url");
    localStorage.removeItem("ctx_domain");
    setCtx(null);
  }

  function showToast(msg, type) {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-4 py-12 relative">
      {toast && (
        <div
          className={`fixed top-6 left-1/2 -translate-x-1/2 px-6 py-3 rounded-lg text-sm font-medium shadow-lg z-50 ${
            toast.type === "success"
              ? "bg-green-800 text-green-100 border border-green-600"
              : "bg-red-800 text-red-100 border border-red-600"
          }`}
        >
          {toast.msg}
        </div>
      )}
      <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">
        Autonomous Agent System
      </h1>
      <p className="text-gray-500 text-sm mb-6">
        Enter a goal, paste a URL, or combine both.
      </p>
      {ctx && (
        <div className="w-full max-w-2xl mb-4 flex items-center justify-between bg-gray-900 border border-indigo-800 rounded-lg px-4 py-2">
          <span className="text-sm text-indigo-300">
            Context: <span className="font-medium">{ctx.domain}</span>
          </span>
          <button
            onClick={clearCtx}
            className="text-xs text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 px-3 py-1 rounded-md transition-colors"
          >
            Clear
          </button>
        </div>
      )}
      <GoalForm
        setGoalId={setGoalId}
        onSuccess={() => showToast("Done! Opening session...", "success")}
        onError={(msg) => showToast(msg || "Something went wrong. Try again.", "error")}
      />
    </div>
  );
}
