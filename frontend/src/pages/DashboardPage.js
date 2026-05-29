import { useEffect, useMemo, useState } from "react";
import { getRecords, getTenants, normalizeList } from "../api";

function StatCard({ label, value }) {
  return (
    <div className="card stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function DashboardPage() {
  const [records, setRecords] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [filters, setFilters] = useState({
    tenant_id: "",
    source_type: "",
  });
  const [error, setError] = useState("");

  function loadTenants() {
    getTenants()
      .then((data) => setTenants(normalizeList(data)))
      .catch((err) => setError(err.message));
  }

  function loadRecords(currentFilters = filters) {
    setError("");

    getRecords(currentFilters)
      .then((data) => setRecords(normalizeList(data)))
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    loadTenants();
    loadRecords();
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
    loadRecords();
  }

  function clearFilters() {
    const emptyFilters = {
      tenant_id: "",
      source_type: "",
    };

    setFilters(emptyFilters);
    loadRecords(emptyFilters);
  }

  const stats = useMemo(() => {
    return {
      total: records.length,
      invalid: records.filter((row) => row.status === "invalid").length,
      suspicious: records.filter((row) => row.status === "suspicious").length,
      pending: records.filter((row) =>
        ["valid", "suspicious", "invalid"].includes(row.status)
      ).length,
      approved: records.filter((row) => row.status === "approved").length,
      rejected: records.filter((row) => row.status === "rejected").length,
      scope1: records.filter((row) => row.scope === "scope_1").length,
      scope2: records.filter((row) => row.scope === "scope_2").length,
      scope3: records.filter((row) => row.scope === "scope_3").length,
    };
  }, [records]);

  return (
    <section>
      <div className="page-header">
        <h2>Dashboard Overview</h2>
        <p>
          View uploaded activity rows across companies, sources, validation
          states, and approval decisions.
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
              <option value="">All companies</option>

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

          <div className="button-row">
            <button type="submit">Apply Filters</button>
            <button
              type="button"
              className="secondary-button"
              onClick={clearFilters}
            >
              Clear
            </button>
          </div>
        </form>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="stats-grid">
        <StatCard label="Total Rows" value={stats.total} />
        <StatCard label="Failed / Invalid Rows" value={stats.invalid} />
        <StatCard label="Suspicious Rows" value={stats.suspicious} />
        <StatCard label="Pending Review" value={stats.pending} />
        <StatCard label="Approved Rows" value={stats.approved} />
        <StatCard label="Rejected Rows" value={stats.rejected} />
        <StatCard label="Scope 1 Rows" value={stats.scope1} />
        <StatCard label="Scope 2 Rows" value={stats.scope2} />
        <StatCard label="Scope 3 Rows" value={stats.scope3} />
      </div>
    </section>
  );
}