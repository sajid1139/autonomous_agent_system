import { useState } from "react";
import Sidebar from "./components/Sidebar";
import MainArea from "./components/MainArea";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [goalId, setGoalId] = useState(null);
  const [activeGoalId, setActiveGoalId] = useState(null);

  return (
    <div style={{ background: "var(--bg)" }} className="flex h-screen w-screen overflow-hidden">
      <div
        style={{
          width: sidebarOpen ? "240px" : "60px",
          transition: "width 0.3s ease",
          flexShrink: 0,
        }}
        className="h-full overflow-hidden"
      >
        <Sidebar
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          goalId={goalId}
          setGoalId={setGoalId}
          activeGoalId={activeGoalId}
          setActiveGoalId={setActiveGoalId}
        />
      </div>
      <div className="flex-1 h-full overflow-hidden">
        <MainArea
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          goalId={goalId}
          setGoalId={setGoalId}
          activeGoalId={activeGoalId}
          setActiveGoalId={setActiveGoalId}
        />
      </div>
    </div>
  );
}
