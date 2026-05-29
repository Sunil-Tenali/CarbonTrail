import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getRecords, getTenants, normalizeList } from "../api";

export default function RecordsPage() {
  const [records, setRecords] = useState([]);
  const [tenants, setTenants] = useState([]);

  const [filters, setFilters] = useState({
    tenant_id: "",
    source_type: "",
    scope: "",
    status: "",
    validation_state: "",
  });

  const [error, setError] = useState("");

  function loadRecords(currentFilters = filters) {
    setError("");

    getRecords(currentFilters)
      .then((data) => setRecords(normalizeList(data)))
      .catch((err) => setError(err.message));
  }

  function loadTenants() {
    getTenants()
      .then((data) => setTenants(normalizeList(data)))
      .catch(() => {});
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
      scope: "",
      status: "",
      validation_state: "",
    };

    setFilters(emptyFilters);
    loadRecords(emptyFilters);
  }

  return (
    <section>
      <div className="page-header">
        <h2>Activity Review</h2>
        <p>
          Review normalized records, validation issues, status, and scope before
          analyst sign-off.
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
              <option value="">All</option>
              <option value="sap">SAP</option>
              <option value="utility">Utility</option>
              <option value="travel">Travel</option>
            </select>
          </label>

          <label>
            Scope
            <select
              value={filters.scope}
              onChange={(event) => updateFilter("scope", event.target.value)}
            >
              <option value="">All</option>
              <option value="scope_1">Scope 1</option>
              <option value="scope_2">Scope 2</option>
              <option value="scope_3">Scope 3</option>
            </select>
          </label>

          <label>
            Status
            <select
              value={filters.status}
              onChange={(event) => updateFilter("status", event.target.value)}
            >
              <option value="">All</option>
              <option value="valid">Valid</option>
              <option value="suspicious">Suspicious</option>
              <option value="invalid">Invalid</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>

          <label>
            Issues
            <select
              value={filters.validation_state}
              onChange={(event) =>
                updateFilter("validation_state", event.target.value)
              }
            >
              <option value="">All</option>
              <option value="has_issues">Has issues</option>
              <option value="no_issues">No issues</option>
              <option value="errors">Errors</option>
              <option value="warnings">Warnings</option>
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

      <div className="card table-card">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Company</th>
              <th>Source</th>
              <th>Type</th>
              <th>Scope</th>
              <th>Original</th>
              <th>Normalized</th>
              <th>Status</th>
              <th>Review</th>
              <th>Issues</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            {records.map((record) => (
              <tr key={record.id}>
                <td>{record.id}</td>

                <td>{record.tenant_name || record.tenant || "-"}</td>

                <td>{record.source_type}</td>

                <td>{record.activity_type}</td>

                <td>{record.scope}</td>

                <td>
                  {record.quantity_original ?? "-"} {record.unit_original}
                </td>

                <td>
                  {record.quantity_normalized ?? "-"}{" "}
                  {record.unit_normalized}
                </td>

                <td>
                  <span className={`badge badge-${record.status}`}>
                    {record.status}
                  </span>
                </td>

                <td>
                  <span
                    className={
                      record.status === "approved" ||
                      record.status === "rejected"
                        ? "review-pill reviewed"
                        : "review-pill pending-review"
                    }
                  >
                    {getReviewLabel(record)}
                  </span>
                </td>

                <td>{record.issue_count ?? record.issues?.length ?? 0}</td>

                <td>{formatDate(record.created_at)}</td>

                <td>
                  <Link className="text-link" to={`/records/${record.id}`}>
                    Review
                  </Link>
                </td>
              </tr>
            ))}

            {records.length === 0 && (
              <tr>
                <td colSpan="12" className="empty-cell">
                  No records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function getReviewLabel(record) {
  if (record.status === "approved" || record.status === "rejected") {
    return "Already reviewed";
  }

  if (record.status === "invalid") {
    return "Needs decision";
  }

  if (record.status === "valid" || record.status === "suspicious") {
    return "Needs review";
  }

  return "-";
}

function formatDate(value) {
  if (!value) {
    return "-";
  }

  return new Date(value).toLocaleString();
}