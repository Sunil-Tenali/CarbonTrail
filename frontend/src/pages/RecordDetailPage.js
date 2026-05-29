import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  approveRecord,
  getAuditLogs,
  getRecord,
  normalizeList,
  rejectRecord,
} from "../api";

export default function RecordDetailPage() {
  const { id } = useParams();

  const [record, setRecord] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function loadData() {
    setError("");

    return Promise.all([
      getRecord(id),
      getAuditLogs({
        entity_type: "ActivityRecord",
        entity_id: id,
      }),
    ])
      .then(([recordData, logsData]) => {
        setRecord(recordData);
        setAuditLogs(normalizeList(logsData));
      })
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleApprove() {
    setError("");
    setMessage("");

    try {
      setIsSubmitting(true);

      // Approval locks the record to prevent accidental changes after analyst sign-off
      await approveRecord(id);
      await loadData();

      setMessage("Record approved and locked for audit.");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleReject() {
    setError("");
    setMessage("");

    const cleanReason = reason.trim();

    if (!cleanReason) {
      setError("Please enter a rejection reason.");
      return;
    }

    try {
      setIsSubmitting(true);

      // Rejection reason is logged for audit trail
      await rejectRecord(id, cleanReason);
      setReason("");

      await loadData();

      setMessage("Record rejected and audit log created.");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!record) {
    return (
      <section>
        <Link className="text-link" to="/records">
          ← Back to records
        </Link>
        <p>Loading record...</p>
        {error && <div className="error-box">{error}</div>}
      </section>
    );
  }

  // Show review state: records flagged as approved/rejected are no longer editable
  const alreadyReviewed =
    record.status === "approved" || record.status === "rejected";

  const canApprove =
    ["valid", "suspicious"].includes(record.status) &&
    !record.is_locked &&
    !isSubmitting;

  const canReject =
    !record.is_locked &&
    record.status !== "rejected" &&
    record.status !== "approved" &&
    !isSubmitting;

  return (
    <section>
      <Link className="text-link" to="/records">
        ← Back to records
      </Link>

      <div className="page-header detail-header">
        <div>
          <h2>Activity Row #{record.id}</h2>
          <p>
            Inspect normalized data, raw source payload, validation issues, and
            audit history.
          </p>
        </div>

        <div className="header-badges">
          {record.is_locked && <span className="locked-badge">Locked</span>}

          {alreadyReviewed && (
            <span className="review-pill reviewed">Already reviewed</span>
          )}
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <div className="detail-grid">
        <div className="card">
          <h3>Normalized Record</h3>

          <dl>
            <dt>Company</dt>
            <dd>{record.tenant_name || record.tenant || "-"}</dd>

            <dt>Source</dt>
            <dd>{record.source_type}</dd>

            <dt>Activity type</dt>
            <dd>{record.activity_type}</dd>

            <dt>Scope</dt>
            <dd>{record.scope}</dd>

            <dt>Status</dt>
            <dd>
              <span className={`badge badge-${record.status}`}>
                {record.status}
              </span>
            </dd>

            <dt>Review state</dt>
            <dd>
              <span
                className={
                  alreadyReviewed
                    ? "review-pill reviewed"
                    : "review-pill pending-review"
                }
              >
                {alreadyReviewed ? "Already reviewed" : "Needs analyst review"}
              </span>
            </dd>

            <dt>Facility</dt>
            <dd>{record.facility_code || "-"}</dd>

            <dt>Original quantity</dt>
            <dd>
              {record.quantity_original ?? "-"} {record.unit_original}
            </dd>

            <dt>Normalized quantity</dt>
            <dd>
              {record.quantity_normalized ?? "-"} {record.unit_normalized}
            </dd>

            <dt>Reference</dt>
            <dd>{record.source_reference || "-"}</dd>
          </dl>
        </div>

        <div className="card">
          <h3>Analyst Action</h3>

          {alreadyReviewed ? (
            <div className="success-box">
              This row has already been reviewed.
            </div>
          ) : (
            <p>
              Approve rows that are ready for audit, or reject rows that should
              not be used.
            </p>
          )}

          <button disabled={!canApprove} onClick={handleApprove}>
            {isSubmitting ? "Saving..." : "Approve and Lock"}
          </button>

          <div className="reject-box">
            <label>
              Rejection reason
              <textarea
                value={reason}
                disabled={!canReject}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Example: Missing required source evidence."
              />
            </label>

            <button
              type="button"
              className="danger-button"
              disabled={!canReject}
              onClick={handleReject}
            >
              {isSubmitting ? "Saving..." : "Reject"}
            </button>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Validation Issues</h3>

        {record.issues?.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Severity</th>
                <th>Code</th>
                <th>Message</th>
              </tr>
            </thead>

            <tbody>
              {record.issues.map((issue) => (
                <tr key={issue.id}>
                  <td>{issue.severity}</td>
                  <td>{issue.code}</td>
                  <td>{issue.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No validation issues for this row.</p>
        )}
      </div>

      <div className="card">
        <h3>Raw Source Payload</h3>

        <pre>{JSON.stringify(record.raw_payload || {}, null, 2)}</pre>
      </div>

      <div className="card">
        <div className="section-title-row">
          <h3>Audit History</h3>
          <Link className="text-link" to="/audit-logs">
            View all audit logs
          </Link>
        </div>

        {auditLogs.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Action</th>
                <th>Message</th>
                <th>Created</th>
              </tr>
            </thead>

            <tbody>
              {auditLogs.map((log) => (
                <tr key={log.id}>
                  <td>
                    <span className={`badge badge-${log.action}`}>
                      {formatAction(log.action)}
                    </span>
                  </td>
                  <td>{log.message || "-"}</td>
                  <td>{formatDate(log.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No audit logs for this row yet.</p>
        )}
      </div>
    </section>
  );
}

function formatAction(value) {
  if (!value) {
    return "-";
  }

  return value.replace("_", " ");
}

function formatDate(value) {
  if (!value) {
    return "-";
  }

  return new Date(value).toLocaleString();
}