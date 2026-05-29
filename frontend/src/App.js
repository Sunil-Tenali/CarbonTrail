import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import AuditLogsPage from "./pages/AuditLogsPage";
import BatchesPage from "./pages/BatchesPage";
import DashboardPage from "./pages/DashboardPage";
import RecordDetailPage from "./pages/RecordDetailPage";
import RecordsPage from "./pages/RecordsPage";
import UploadPage from "./pages/UploadPage";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <aside className="sidebar">
          <h1>CarbonTrail</h1>
          <p>Analyst Review Console</p>

          <nav>
            <Link to="/">Dashboard</Link>
            <Link to="/upload">Upload CSV</Link>
            <Link to="/batches">Import Batches</Link>
            <Link to="/records">Activity Review</Link>
            <Link to="/audit-logs">Audit Logs</Link>
          </nav>
        </aside>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/batches" element={<BatchesPage />} />
            <Route path="/records" element={<RecordsPage />} />
            <Route path="/records/:id" element={<RecordDetailPage />} />
            <Route path="/audit-logs" element={<AuditLogsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}