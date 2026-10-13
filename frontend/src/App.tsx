import { BrowserRouter, Routes, Route } from "react-router-dom";
import Shell from "./components/Shell";
import Overview from "./pages/Overview";
import Departments from "./pages/Departments";
import Waiting from "./pages/Waiting";
import Staffing from "./pages/Staffing";
import Flow from "./pages/Flow";
import Simulator from "./pages/Simulator";
import AgentRoom from "./pages/AgentRoom";
import DataSource from "./pages/DataSource";

export default function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/departments" element={<Departments />} />
          <Route path="/waiting" element={<Waiting />} />
          <Route path="/staffing" element={<Staffing />} />
          <Route path="/flow" element={<Flow />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/agent" element={<AgentRoom />} />
          <Route path="/source" element={<DataSource />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  );
}
