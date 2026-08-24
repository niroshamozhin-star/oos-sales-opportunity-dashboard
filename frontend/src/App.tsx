import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Overview from "./pages/Overview";
import Opportunities from "./pages/Opportunities";
import SalesTeam from "./pages/SalesTeam";
import Outreach from "./pages/Outreach";
import AiAssistant from "./pages/AiAssistant";

function App() {
  return (
    <div className="min-h-screen flex">
      <Sidebar />
      <main className="flex-1 p-8 min-w-0">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/opportunities" element={<Opportunities />} />
          <Route path="/sales-team" element={<SalesTeam />} />
          <Route path="/outreach" element={<Outreach />} />
          <Route path="/assistant" element={<AiAssistant />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
