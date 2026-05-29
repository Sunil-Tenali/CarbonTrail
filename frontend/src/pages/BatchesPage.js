import { useEffect, useState } from "react";
import { getBatches, getTenants, normalizeList } from "../api";

export default function BatchesPage() {
  const [batches, setBatches] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [filters, setFilters] = useState({
    tenant_id: "",
    source_type: "",
    status: "",
  });
  const [error, setError] = useState("");

  function loadBatches(currentFilters = filters) {
    setError("");

    getBatches(currentFilters)
      .then((data) => setBatches(normalizeList(data)))
      .catch((err) => setError(err.message));
  }

  function loadTenants() {
    getTenants()
      .then((data) => setTenants(normalizeList(data)))
      .catch(() => {});
  }

  useEffect(() => {
    loadTenants();
    loadBatches();
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
    loadBatches();
  }

  function clearFilters() {
    const emptyFilters = {
      tenant_id: "",
      source_type: "",
      status: "",
    };

    setFilters(emptyFilters);
    loadBatches(emptyFilters);
  }

  return (
    <section>
      <div className="page-header">
        <h2>Import Batches</h2>
        <p>
          Each batch represents one uploaded CSV file and its import result.
        </p>
      </div>

      <div className="card">
        <form className="filters-grid" onSubmit={applyFilters}>
          <label>
            Company
            <select
              value={filters.tenant_id}
              onChange={(event) => updateFilter("tenant_id", event.target.value)}
            >
              <option value="">All Companies</option>

              {tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Source
            <select
              value={filters.source_type}
              onChange={(event) =>
                updateFilter("source_type", event.target.value)
              }
            >
              <option value="">All sources</option>
              <option value="sap">SAP</option>
              <option value="utility">Utility</option>
              <option value="travel">Travel</option>
            </select>
          </label>

          <label>
            Status
            <select
              value={filters.status}
              onChange={(event) => updateFilter("status", event.target.value)}
            >
              <option value="">All statuses</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </select>
          </label>

          <div className="button-row">
            <button type="submit">Apply Filters</button>
            <button type="button" className="secondary-button" onClick={clearFilters}>
              Clear
            </button>
          </div>
        </form>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="card table-card">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Company</th>
              <th>Source</th>
              <th>Filename</th>
              <th>Status</th>
              <th>Total</th>
              <th>Valid</th>
              <th>Invalid</th>
              <th>Suspicious</th>
              <th>Approved</th>
              <th>Uploaded</th>
            </tr>
          </thead>

          <tbody>
            {batches.map((batch) => (
              <tr key={batch.id}>
                <td>{batch.id}</td>
                <td>{batch.tenant_name || batch.tenant || "-"}</td>
                <td>{batch.source_type || batch.source_system_name || "-"}</td>
                <td>{batch.original_filename || "-"}</td>
                <td>
                  <span className={`badge badge-${batch.status}`}>
                    {batch.status}
                  </span>
                </td>
                <td>{batch.total_rows ?? 0}</td>
                <td>{batch.valid_rows ?? 0}</td>
                <td>{batch.invalid_rows ?? 0}</td>
                <td>{batch.suspicious_rows ?? 0}</td>
                <td>{batch.approved_rows ?? 0}</td>
                <td>{formatDate(batch.created_at || batch.uploaded_at)}</td>
              </tr>
            ))}

            {batches.length === 0 && (
              <tr>
                <td colSpan="11" className="empty-cell">
                  No import batches found.
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