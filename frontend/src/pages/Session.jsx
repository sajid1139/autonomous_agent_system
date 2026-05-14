import { useState } from "react";
import AgentLog from "../components/AgentLog";
import ReportView from "../components/ReportView";

export default function Session({ goalId, setGoalId }) {
  const [done, setDone] = useState(false);

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {!done && (
        <div className="fixed inset-0 bg-gray-950 bg-opacity-80 z-50 flex flex-col items-center justify-center gap-6">
          <div className="w-16 h-16 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin" />
          <p className="text-white text-sm font-medium tracking-wide">
            Agents are working...
          </p>
        </div>
      )}
      <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
        <span className="text-gray-400 text-sm font-mono truncate max-w-lg">
          goal: {goalId}
        </span>
        <button
          onClick={() => setGoalId(null)}
          className="text-sm text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 px-4 py-1.5 rounded-lg transition-colors ml-4 shrink-0"
        >
          New Goal
        </button>
      </div>
      <div className="flex flex-1 gap-4 p-6 overflow-hidden">
        <div className="flex-1 flex flex-col min-h-0">
          <AgentLog goalId={goalId} onDone={() => setDone(true)} />
        </div>
        <div className="flex-1 flex flex-col min-h-0 bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
          <div className="px-4 py-2 bg-gray-900 text-gray-400 text-sm font-mono border-b border-gray-700">
            session report
          </div>
          <ReportView goalId={goalId} />
        </div>
      </div>
    </div>
  );
}
