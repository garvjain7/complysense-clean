// Use: Super Admin — Audit Trail Explorer. Filterable, paginated, and CSV-downloadable log of all platform actions.

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../lib/api";
import { PageShell } from "../../components/shared/PageShell";
import { Download, Search } from "lucide-react";

interface AuditLog {
  audit_log_id: string;
  institution_name: string | null;
  user_name: string | null;
  user_email: string | null;
  role_at_time: string | null;
  action_type: string;
  entity_type: string | null;
  entity_id: string | null;
  ip_address: string | null;
  created_at: string;
}

interface Institution {
  institution_id: string;
  institution_name: string;
}

const ACTION_TYPES = [
  "login", "logout", "failed_login", "user_blocked", "register",
  "user_created", "user_invited", "user_updated", "user_role_changed", "user_status_toggled",
  "user_unlocked", "admin_password_reset", "change_password", "department_created",
  "department_updated", "department_status_toggled", "reviewer_assigned",
  "policy_created", "policy_updated", "policy_approved", "policy_rejected", "policy_content_saved",
  "evidence_uploaded", "evidence_approved", "evidence_rejected",
  "control_created", "control_assigned", "control_status_updated", "control_note_added",
  "assessment_created", "assessment_response_saved", "assessment_submitted",
  "incident_created", "incident_updated", "incident_checklist_updated",
  "vendor_created", "vendor_updated", "vendor_risk_assessment_created", "vendor_risk_assessment_updated",
  "event_created", "event_updated", "event_deleted",
  "institution_created", "institution_updated", "institution_status_toggled",
];

const ACTION_LABELS: Record<string, string> = {
  login: "Logged In",
  logout: "Logged Out",
  failed_login: "Failed Login",
  user_blocked: "Account Blocked",
  register: "Account Registered",
  user_created: "Created User",
  user_invited: "Invited User",
  user_updated: "Updated User",
  user_role_changed: "Changed User Role",
  user_role_updated: "Updated User Role",
  user_status_toggled: "Toggled User Status",
  user_unlocked: "Unlocked User Account",
  admin_password_reset: "Reset User Password",
  change_password: "Changed Password",
  institution_created: "Created Institution",
  institution_updated: "Updated Institution",
  institution_deleted: "Deleted Institution",
  institution_status_toggled: "Toggled Institution Status",
  department_created: "Created Department",
  department_updated: "Updated Department",
  department_status_toggled: "Toggled Department Status",
  department_deleted: "Deleted Department",
  reviewer_assigned: "Assigned Reviewer",
  event_created: "Created Calendar Event",
  event_updated: "Updated Calendar Event",
  event_deleted: "Deleted Calendar Event",
  policy_created: "Created Policy",
  policy_updated: "Updated Policy",
  policy_approved: "Approved Policy",
  policy_rejected: "Rejected Policy",
  policy_content_saved: "Saved Policy Content",
  evidence_uploaded: "Uploaded Evidence",
  evidence_submitted: "Submitted Evidence",
  evidence_approved: "Approved Evidence",
  evidence_rejected: "Rejected Evidence",
  control_created: "Created Control",
  control_assigned: "Assigned Control",
  control_status_updated: "Updated Control Status",
  control_note_added: "Added Control Note",
  assessment_created: "Created Assessment",
  assessment_response_saved: "Saved Assessment Response",
  assessment_submitted: "Submitted Assessment",
  incident_created: "Created Incident",
  incident_updated: "Updated Incident",
  incident_checklist_updated: "Updated Incident Checklist",
  vendor_created: "Added Vendor",
  vendor_updated: "Updated Vendor",
  vendor_risk_assessment_created: "Created Vendor Risk Assessment",
  vendor_risk_assessment_updated: "Updated Vendor Risk Assessment",
  observation_added: "Added Audit Observation",
};

export default function AuditTrail() {
  const [searchParams] = useSearchParams();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [jumpPage, setJumpPage] = useState("1");
  const LIMIT = 50;

  // Filters
  const [institutionId, setInstitutionId] = useState(searchParams.get("institution_id") ?? "");
  const [actionType, setActionType] = useState(searchParams.get("action_type") ?? "");
  const [userSearch, setUserSearch] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    const params: Record<string, string | number> = { page, limit: LIMIT };
    if (institutionId) params.institution_id = institutionId;
    if (actionType) params.action_type = actionType;
    if (userSearch) params.user_search = userSearch;
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;

    try {
      const res = await api.get("/api/v1/audit/logs", { params });
      setLogs(res.data.logs ?? []);
      setTotal(res.data.total ?? 0);
    } catch { setLogs([]); }
    setLoading(false);
  }, [page, institutionId, actionType, userSearch, fromDate, toDate]);

  useEffect(() => {
    api.get("/api/v1/institutions").then((r) => setInstitutions(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    fetchLogs();
    setJumpPage(String(page));
  }, [fetchLogs, page]);

  async function handleCSVExport() {
    const params: Record<string, string> = { format: "csv" };
    if (institutionId) params.institution_id = institutionId;
    if (actionType) params.action_type = actionType;
    if (userSearch) params.user_search = userSearch;
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;

    try {
      const res = await api.get("/api/v1/audit/logs", { params, responseType: "blob" });
      const url = window.URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "audit_trail_export.csv";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch { alert("CSV export failed."); }
  }

  const totalPages = Math.max(1, Math.ceil(total / LIMIT));

  function handleJumpSubmit() {
    const p = parseInt(jumpPage, 10);
    if (!isNaN(p) && p >= 1 && p <= totalPages) {
      setPage(p);
    } else {
      setJumpPage(String(page));
    }
  }

  return (
    <PageShell
      title="Audit Trail"
      subtitle="Immutable, searchable log of every action across the platform"
      actions={
        <button className="btn btn-ghost" onClick={handleCSVExport} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Download size={14} /> Export CSV
        </button>
      }
    >
      {/* Filter Bar */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: "1 1 150px" }}>
            <label className="form-label" style={{ fontSize: 11 }}>From Date</label>
            <input type="date" className="form-input" value={fromDate} onChange={(e) => setFromDate(e.target.value)} style={{ fontSize: 13 }} />
          </div>
          <div style={{ flex: "1 1 150px" }}>
            <label className="form-label" style={{ fontSize: 11 }}>To Date</label>
            <input type="date" className="form-input" value={toDate} onChange={(e) => setToDate(e.target.value)} style={{ fontSize: 13 }} />
          </div>
          <div style={{ flex: "1 1 180px" }}>
            <label className="form-label" style={{ fontSize: 11 }}>Institution</label>
            <select className="form-input" value={institutionId} onChange={(e) => setInstitutionId(e.target.value)} style={{ fontSize: 13 }}>
              <option value="">All Institutions</option>
              {institutions.map((i) => <option key={i.institution_id} value={i.institution_id}>{i.institution_name}</option>)}
            </select>
          </div>
          <div style={{ flex: "1 1 180px" }}>
            <label className="form-label" style={{ fontSize: 11 }}>Action Type</label>
            <select className="form-input" value={actionType} onChange={(e) => setActionType(e.target.value)} style={{ fontSize: 13 }}>
              <option value="">All Actions</option>
              {ACTION_TYPES.map((a) => <option key={a} value={a}>{ACTION_LABELS[a] ?? a}</option>)}
            </select>
          </div>
          <div style={{ flex: "1 1 200px" }}>
            <label className="form-label" style={{ fontSize: 11 }}>Search User</label>
            <div style={{ position: "relative" }}>
              <Search size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
              <input
                className="form-input"
                placeholder="Name or email..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                style={{ fontSize: 13, paddingLeft: 30 }}
              />
            </div>
          </div>
          {(institutionId || actionType || userSearch || fromDate || toDate) && (
            <button className="btn btn-ghost" style={{ fontSize: 12, alignSelf: "flex-end" }}
              onClick={() => { setInstitutionId(""); setActionType(""); setUserSearch(""); setFromDate(""); setToDate(""); setPage(1); }}>
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Logs Table */}
      <div className="card">
        <div style={{ marginBottom: 12, fontSize: 13, color: "var(--text-muted)" }}>
          Showing {logs.length} of {total} entries (50 per page)
        </div>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Institution</th>
                <th>User</th>
                <th>Role</th>
                <th>Action</th>
                <th>Resource Type</th>
                <th>IP Address</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i}>{Array.from({ length: 7 }).map((_, j) => <td key={j}><div className="skeleton" style={{ height: 16, borderRadius: 4 }} /></td>)}</tr>
                ))
              ) : logs.length === 0 ? (
                <tr><td colSpan={7} style={{ textAlign: "center", color: "var(--text-muted)", padding: 40 }}>No audit logs match your filters.</td></tr>
              ) : logs.map((log) => (
                <tr key={log.audit_log_id}>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: 11, whiteSpace: "nowrap", color: "var(--text-muted)" }}>
                    {new Date(log.created_at).toLocaleString("en-IN")}
                  </td>
                  <td style={{ fontSize: 13 }}>{log.institution_name ?? "System"}</td>
                  <td>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{log.user_name ?? "System"}</div>
                    {log.user_email && <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{log.user_email}</div>}
                  </td>
                  <td style={{ fontSize: 12 }}>{log.role_at_time ? <span className="badge badge-draft">{log.role_at_time}</span> : "—"}</td>
                  <td><span className="badge badge-in_progress">{ACTION_LABELS[log.action_type] ?? log.action_type}</span></td>
                  <td style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "capitalize" }}>{log.entity_type ? log.entity_type.replace(/_/g, " ") : "—"}</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }}>{log.ip_address ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Enhanced Pagination with Direct Jump Input */}
        {totalPages > 1 && (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 12, marginTop: 20 }}>
            <button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))} style={{ fontSize: 12 }}>
              ← Prev
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-secondary)" }}>
              <span>Page</span>
              <input
                type="number"
                min={1}
                max={totalPages}
                value={jumpPage}
                onChange={(e) => setJumpPage(e.target.value)}
                onBlur={handleJumpSubmit}
                onKeyDown={(e) => { if (e.key === "Enter") handleJumpSubmit(); }}
                style={{
                  width: 56,
                  padding: "4px 6px",
                  textAlign: "center",
                  borderRadius: 4,
                  border: "1px solid var(--border)",
                  fontSize: 13,
                  fontFamily: "var(--font-mono)",
                  background: "var(--surface)",
                  color: "var(--text-primary)",
                }}
              />
              <span>of {totalPages}</span>
            </div>
            <button className="btn btn-ghost" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))} style={{ fontSize: 12 }}>
              Next →
            </button>
          </div>
        )}
      </div>
    </PageShell>
  );
}
