import { useEffect, useState } from "react";
import { getAuditLogs, getTenants, normalizeList } from "../api";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [filters, setFilters] = useState({
    tenant_id: "",
    action: "",
    entity_type: "",
  });
  const [error, setError] = useState("");

  function loadLogs() {
    setError("");

    // Fetch audit logs filtered by tenant, action, and entity type
    getAuditLogs(filters)
      .then((data) => setLogs(normalizeList(data)))
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    getTenants()
      .then((data) => setTenants(normalizeList(data)))
      .catch(() => {});
    loadLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function updateFilter(name, value) {
    setFilters((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function applyFilters(event) {
    event.preventDefault();
    loadLogs();
  }

  return (
    <section>
      <div className="page-header">
        <h2>Audit Logs</h2>
        <p>
          Shows import events and analyst actions like approval and rejection.
        </p>
      </div>

      <div className="card">
        <form className="filters-grid" onSubmit={applyFilters}>
          <label>
            Tenant
            <select
              value={filters.tenant_id}
              onChange={(event) => updateFilter("tenant_id", event.target.value)}
            >
              <option value="">All tenants</option>
              {tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Action
            <select
              value={filters.action}
              onChange={(event) => updateFilter("action", event.target.value)}
            >
              <option value="">All actions</option>
              <option value="imported">Imported</option>
              <option value="import_failed">Import failed</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>

          <label>
            Entity Type
            <select
              value={filters.entity_type}
              onChange={(event) =>
                updateFilter("entity_type", event.target.value)
              }
            >
              <option value="">All entities</option>
              <option value="ImportBatch">ImportBatch</option>
              <option value="ActivityRecord">ActivityRecord</option>
            </select>
          </label>

          <button type="submit">Apply Filters</button>
        </form>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="card table-card">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Tenant</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Message</th>
              <th>Created</th>
            </tr>
          </thead>

          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>{log.id}</td>
                <td>{log.tenant_name || log.tenant || "-"}</td>
                <td>{log.action}</td>
                <td>
                  {log.entity_type} #{log.entity_id}
                </td>
                <td>{log.message || "-"}</td>
                <td>{formatDate(log.created_at)}</td>
              </tr>
            ))}

            {logs.length === 0 && (
              <tr>
                <td colSpan="6" className="empty-cell">
                  No audit logs found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatDate(value) {
  if (!value) {
    return "-";
  }

  return new Date(value).toLocaleString();
}