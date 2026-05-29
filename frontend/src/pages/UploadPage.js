import { useEffect, useState } from "react";
import { createTenant, getTenants, normalizeList, uploadCsv } from "../api";

export default function UploadPage() {
  const [tenants, setTenants] = useState([]);
  const [tenantId, setTenantId] = useState("");
  const [newTenantName, setNewTenantName] = useState("");

  const [sourceType, setSourceType] = useState("utility");
  const [file, setFile] = useState(null);

  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isCreatingTenant, setIsCreatingTenant] = useState(false);

  function loadTenants() {
    getTenants()
      .then((data) => {
        const tenantList = normalizeList(data);

        setTenants(tenantList);

        if (!tenantId && tenantList.length > 0) {
          setTenantId(String(tenantList[0].id));
        }
      })
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    loadTenants();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreateTenant(event) {
    event.preventDefault();

    setError("");
    setResult(null);

    const cleanName = newTenantName.trim();

    if (!cleanName) {
      setError("Please enter a company name.");
      return;
    }

    try {
      setIsCreatingTenant(true);

      const createdTenant = await createTenant(cleanName);

      setNewTenantName("");
      setTenantId(String(createdTenant.id));

      const latestTenants = await getTenants();
      setTenants(normalizeList(latestTenants));
    } catch (err) {
      setError(err.message);
    } finally {
      setIsCreatingTenant(false);
    }
  }

  async function handleUpload(event) {
    event.preventDefault();

    setError("");
    setResult(null);

    if (!tenantId) {
      setError("Please select a company.");
      return;
    }

    if (!sourceType) {
      setError("Please select a source type.");
      return;
    }

    if (!file) {
      setError("Please choose a CSV file.");
      return;
    }

    try {
      setIsUploading(true);

      const data = await uploadCsv({
        tenantId,
        sourceType,
        file,
      });

      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <section>
      <div className="page-header">
        <h2>Upload CSV</h2>
        <p>
          Choose a company and upload SAP, utility electricity, or corporate
          travel CSV data.
        </p>
      </div>

      <div className="card">
        <h3>Add Company</h3>

        <form className="form-grid" onSubmit={handleCreateTenant}>
          <label>
            Company Name
            <input
              value={newTenantName}
              onChange={(event) => setNewTenantName(event.target.value)}
              placeholder="Example: Acme Manufacturing"
            />
          </label>

          <button type="submit" disabled={isCreatingTenant}>
            {isCreatingTenant ? "Adding..." : "Add Company"}
          </button>
        </form>
      </div>

      <div className="card">
        <h3>Upload Source File</h3>

        <form className="form-grid" onSubmit={handleUpload}>
          <label>
            Company
            <select
              value={tenantId}
              onChange={(event) => setTenantId(event.target.value)}
            >
              <option value="">Select company</option>

              {tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Source Type
            <select
              value={sourceType}
              onChange={(event) => setSourceType(event.target.value)}
            >
              <option value="sap">SAP fuel/procurement</option>
              <option value="utility">Utility electricity</option>
              <option value="travel">Corporate travel</option>
            </select>
          </label>

          <label>
            CSV File
            <input
              type="file"
              accept=".csv"
              onChange={(event) => setFile(event.target.files[0])}
            />
          </label>

          <button type="submit" disabled={isUploading}>
            {isUploading ? "Uploading..." : "Upload CSV"}
          </button>
        </form>
      </div>

      {error && <div className="error-box">{error}</div>}

      {result && (
        <div className="card result-card">
          <h3>Import Summary</h3>

          <dl>
            <dt>Batch ID</dt>
            <dd>{result.id}</dd>

            <dt>Company</dt>
            <dd>{result.tenant_name || result.tenant}</dd>

            <dt>Source</dt>
            <dd>{result.source_type}</dd>

            <dt>Status</dt>
            <dd>{result.status}</dd>

            <dt>Total rows</dt>
            <dd>{result.total_rows}</dd>

            <dt>Valid rows</dt>
            <dd>{result.valid_rows}</dd>

            <dt>Invalid rows</dt>
            <dd>{result.invalid_rows}</dd>

            <dt>Suspicious rows</dt>
            <dd>{result.suspicious_rows}</dd>
          </dl>
        </div>
      )}
    </section>
  );
}