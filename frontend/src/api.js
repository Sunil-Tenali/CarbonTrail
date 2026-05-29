const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:8000/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: "Request failed",
    }));

    throw new Error(error.detail || JSON.stringify(error));
  }

  return response.json();
}

// Handle both paginated responses (with a results array) and simple arrays
export function normalizeList(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.results)) {
    return data.results;
  }

  return [];
}

function buildQuery(params = {}) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.append(key, value);
    }
  });

  const queryString = query.toString();

  return queryString ? `?${queryString}` : "";
}

export function getTenants() {
  return request("/tenants/");
}

export function createTenant(name) {
  return request("/tenants/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  });
}

export function getRecords(params = {}) {
  return request(`/activity-records/${buildQuery(params)}`);
}

export function getRecord(id) {
  return request(`/activity-records/${id}/`);
}

export function getBatches(params = {}) {
  return request(`/import-batches/${buildQuery(params)}`);
}

export function getAuditLogs(params = {}) {
  return request(`/audit-logs/${buildQuery(params)}`);
}

export async function uploadCsv({ tenantId, sourceType, file }) {
  // Use FormData to send file as multipart/form-data instead of JSON
  const formData = new FormData();

  formData.append("tenant_id", tenantId);
  formData.append("source_type", sourceType);
  formData.append("file", file);

  return request("/ingestion/upload/", {
    method: "POST",
    body: formData,
  });
}

export function approveRecord(id) {
  return request(`/activity-records/${id}/approve/`, {
    method: "POST",
  });
}

export function rejectRecord(id, reason) {
  return request(`/activity-records/${id}/reject/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ reason }),
  });
}