import React, { useCallback, useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";

const NAV_ITEMS = [
  { id: "overview", label: "Overview" },
  { id: "resources", label: "Resources" },
  { id: "dependencies", label: "Dependencies" },
  { id: "timeline", label: "Timeline" },
  { id: "alerts", label: "Alerts" },
  { id: "logs", label: "Activity Logs" },
  { id: "analytics", label: "Analytics" },
  { id: "settings", label: "Settings" },
];

const STATUS_STYLE = {
  expired: { bg: "rgba(239,68,68,0.14)", border: "#EF4444", color: "#FCA5A5", label: "Expired" },
  critical: { bg: "rgba(239,68,68,0.14)", border: "#EF4444", color: "#FCA5A5", label: "Critical" },
  warning: { bg: "rgba(245,158,11,0.14)", border: "#F59E0B", color: "#FCD34D", label: "Warning" },
  error: { bg: "rgba(239,68,68,0.14)", border: "#EF4444", color: "#FCA5A5", label: "Error" },
  ok: { bg: "rgba(34,197,94,0.14)", border: "#22C55E", color: "#86EFAC", label: "Healthy" },
};

function isActionableStatus(status) {
  return status === "expired" || status === "critical" || status === "warning" || status === "error";
}

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [windowDays, setWindowDays] = useState(14);
  const [offline, setOffline] = useState(true);
  const [report, setReport] = useState(null);
  const [historyItems, setHistoryItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastCheckedAt, setLastCheckedAt] = useState(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [kindFilter, setKindFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedServiceName, setSelectedServiceName] = useState(null);

  const fetchData = useCallback(async (signal) => {
    setLoading(true);
    setError("");
    try {
      const [statusRes, histRes] = await Promise.all([
        fetch(`${API_BASE}/api/status?window=${windowDays}&offline=${offline}`, { signal }),
        fetch(`${API_BASE}/api/history?limit=25`, { signal }),
      ]);
      if (!statusRes.ok) {
        throw new Error(`Status endpoint returned ${statusRes.status}`);
      }
      const statusData = await statusRes.json();
      setReport(statusData);
      setLastCheckedAt(new Date());

      if (histRes.ok) {
        const histData = await histRes.json();
        setHistoryItems(histData.items || []);
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message || "Failed to reach backend");
      }
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, [windowDays, offline]);

  useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();
  }, [fetchData]);

  const impacts = report?.impacts || [];

  const counts = useMemo(() => {
    let healthy = 0;
    let attention = 0;
    let expired = 0;
    const services = new Set();

    for (const item of impacts) {
      if (item.status === "expired") expired += 1;
      else if (isActionableStatus(item.status)) attention += 1;
      else healthy += 1;

      for (const s of item.affected_services || []) {
        services.add(s.service_name);
      }
    }
    return { total: impacts.length, servicesCount: services.size, healthy, attention, expired };
  }, [impacts]);

  const filteredResources = useMemo(() => {
    return impacts.filter((item) => {
      const matchesQuery =
        !searchQuery.trim() ||
        item.resource_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.owner.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.renewal_hint || "").toLowerCase().includes(searchQuery.toLowerCase());
      const matchesKind = kindFilter === "all" || item.kind === kindFilter;
      const matchesStatus = statusFilter === "all" || item.status === statusFilter;
      return matchesQuery && matchesKind && matchesStatus;
    });
  }, [impacts, searchQuery, kindFilter, statusFilter]);

  const serviceGraph = useMemo(() => {
    const map = new Map();
    for (const item of impacts) {
      for (const svc of item.affected_services || []) {
        if (!map.has(svc.service_name)) {
          map.set(svc.service_name, { name: svc.service_name, criticality: svc.criticality, deps: [] });
        }
        map.get(svc.service_name).deps.push({
          resource_id: item.resource_id,
          kind: item.kind,
          status: item.status,
          severity: item.severity,
          days_remaining: item.days_remaining,
          impact: svc.impact,
        });
      }
    }
    return Array.from(map.values());
  }, [impacts]);

  const exportJsonReport = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `deadline-map-${report.as_of || "report"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const score = report?.health_score ?? 100;
  const scoreColor = score >= 80 ? "#22C55E" : score >= 55 ? "#F59E0B" : "#EF4444";

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#090B10", color: "#E5E7EB", fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif" }}>
      <aside
        style={{
          width: sidebarOpen ? 240 : 72,
          background: "#11151D",
          borderRight: "1px solid #252B36",
          padding: "18px 12px",
          display: "flex",
          flexDirection: "column",
          transition: "width 0.18s ease",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 6px 18px", borderBottom: "1px solid #252B36" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, overflow: "hidden" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#668BFF", flexShrink: 0 }} />
            {sidebarOpen && (
              <div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>deadline-map</div>
                <div style={{ fontSize: 11, color: "#8993A4", marginTop: 2 }}>Deadline Intelligence</div>
              </div>
            )}
          </div>
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            style={{ background: "transparent", color: "#8993A4", border: "1px solid #252B36", borderRadius: 6, padding: "4px 8px", cursor: "pointer", fontSize: 12 }}
          >
            {sidebarOpen ? "←" : "→"}
          </button>
        </div>

        <nav style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 14 }}>
          {NAV_ITEMS.map((item) => {
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "9px 10px",
                  borderRadius: 7,
                  border: active ? "1px solid rgba(102,139,255,0.4)" : "1px solid transparent",
                  background: active ? "rgba(102,139,255,0.14)" : "transparent",
                  color: active ? "#E5E7EB" : "#8993A4",
                  cursor: "pointer",
                  textAlign: "left",
                  fontSize: 13,
                  fontWeight: active ? 600 : 400,
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: 2, background: active ? "#668BFF" : "#3B4354", flexShrink: 0 }} />
                {sidebarOpen && <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.label}</span>}
              </button>
            );
          })}
        </nav>
      </aside>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <header
          style={{
            height: 64,
            background: "#11151D",
            borderBottom: "1px solid #252B36",
            padding: "0 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{NAV_ITEMS.find((n) => n.id === activeTab)?.label}</div>
            <div style={{ fontSize: 12, color: "#8993A4" }}>
              {lastCheckedAt ? `Checked ${lastCheckedAt.toLocaleTimeString()}` : "Awaiting check"} · As of {report?.as_of || "-"} · {offline ? "Offline" : "Live"}
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <select
              value={windowDays}
              onChange={(e) => setWindowDays(Number(e.target.value))}
              style={{ background: "#090B10", color: "#E5E7EB", border: "1px solid #252B36", borderRadius: 6, padding: "6px 10px", fontSize: 12 }}
            >
              <option value={7}>7d window</option>
              <option value={14}>14d window</option>
              <option value={30}>30d window</option>
              <option value={90}>90d window</option>
            </select>
            <button
              onClick={() => fetchData()}
              style={{ background: "#668BFF", color: "#090B10", border: "none", borderRadius: 6, padding: "6px 12px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
            >
              Run Checks
            </button>
            <button
              onClick={exportJsonReport}
              disabled={!report}
              style={{ background: "#090B10", color: "#E5E7EB", border: "1px solid #252B36", borderRadius: 6, padding: "6px 12px", fontSize: 12, cursor: "pointer" }}
            >
              Export JSON
            </button>
          </div>
        </header>

        <main style={{ padding: 24, maxWidth: 1240, width: "100%", margin: "0 auto", boxSizing: "border-box" }}>
          {error && (
            <div style={{ marginBottom: 18, padding: 14, background: "rgba(239,68,68,0.12)", border: "1px solid #EF4444", borderRadius: 8, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 13, color: "#FCA5A5" }}>Connection error: {error} ({API_BASE})</span>
              <button onClick={() => fetchData()} style={{ background: "#EF4444", color: "#fff", border: "none", borderRadius: 6, padding: "5px 10px", fontSize: 12, cursor: "pointer" }}>
                Retry
              </button>
            </div>
          )}

          {loading && !report && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 14 }}>
              {[1, 2, 3, 4, 5].map((n) => (
                <div key={n} style={{ height: 96, background: "#11151D", border: "1px solid #252B36", borderRadius: 8 }} />
              ))}
            </div>
          )}

          {report && activeTab === "overview" && (
            <>
              <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14 }}>
                <KpiCard label="DEADLINE HEALTH" value={`${score}/100`} sub="Deadline readiness index" accent={scoreColor} />
                <KpiCard label="TOTAL RESOURCES" value={counts.total} sub={`Across ${counts.servicesCount} services`} accent="#668BFF" />
                <KpiCard label="SERVICES AT RISK" value={report.services_at_risk_count} sub={`${report.deadlines_in_window_count} in ${report.window_days}d`} accent="#F59E0B" />
                <KpiCard label="HEALTHY" value={counts.healthy} sub="Within threshold" accent="#22C55E" />
                <KpiCard label="NEEDS ATTENTION" value={counts.attention + counts.expired} sub={`${counts.expired} expired · ${counts.attention} active`} accent="#EF4444" />
              </section>

              <section style={{ marginTop: 18, background: "#11151D", border: "1px solid #252B36", borderRadius: 8, padding: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
                  <strong style={{ fontSize: 14 }}>Category Health &amp; Scoring Basis</strong>
                  <span style={{ fontSize: 11, color: "#8993A4" }}>{report.health_formula}</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 10 }}>
                  {(report.health_breakdown || []).map((cat) => (
                    <div key={cat.category} style={{ background: "#090B10", border: "1px solid #252B36", borderRadius: 6, padding: 12 }}>
                      <div style={{ fontSize: 12, color: "#8993A4" }}>{cat.label}</div>
                      <div style={{ fontSize: 15, fontWeight: 600, marginTop: 4 }}>{cat.state}</div>
                      <div style={{ fontSize: 11, color: "#8993A4", marginTop: 2 }}>
                        {cat.issues} issue(s) of {cat.total} checked
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section style={{ marginTop: 18, background: "#11151D", border: "1px solid #252B36", borderRadius: 8, padding: 18 }}>
                <h2 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 600 }}>Priority Deadlines, Impact &amp; Renewal Actions</h2>
                <div style={{ display: "grid", gap: 10 }}>
                  {impacts.map((item) => {
                    const badge = STATUS_STYLE[item.status] || STATUS_STYLE.ok;
                    return (
                      <div
                        key={item.resource_id}
                        style={{
                          background: "#090B10",
                          border: "1px solid #252B36",
                          borderRadius: 7,
                          padding: "12px 14px",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: 12,
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ minWidth: 260, flex: 1 }}>
                          <div style={{ fontWeight: 600, fontSize: 14 }}>
                            {item.resource_id}{" "}
                            <span style={{ color: "#8993A4", fontWeight: 400, fontSize: 12 }}>
                              · {item.kind} · severity: {item.severity} · owner: {item.owner}
                            </span>
                          </div>
                          <div style={{ fontSize: 12, color: "#8993A4", marginTop: 4 }}>
                            Breaks:{" "}
                            <span style={{ color: "#E5E7EB" }}>
                              {item.affected_services.length > 0
                                ? item.affected_services.map((s) => `${s.service_name} (${s.impact})`).join(", ")
                                : "None"}
                            </span>
                          </div>
                          <div style={{ fontSize: 12, color: "#668BFF", marginTop: 4 }}>
                            Action: {item.renewal_hint}
                          </div>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                          <span style={{ fontSize: 12, color: "#8993A4" }}>Priority {item.priority_score}</span>
                          <span
                            style={{
                              padding: "3px 9px",
                              borderRadius: 999,
                              fontSize: 11,
                              fontWeight: 600,
                              background: badge.bg,
                              border: `1px solid ${badge.border}`,
                              color: badge.color,
                            }}
                          >
                            {badge.label} {item.days_remaining !== null ? `· ${item.days_remaining}d` : ""}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            </>
          )}

          {report && activeTab === "resources" && (
            <section style={{ background: "#11151D", border: "1px solid #252B36", borderRadius: 8, padding: 18 }}>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
                <input
                  type="text"
                  placeholder="Search resource, owner, or action..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ background: "#090B10", color: "#E5E7EB", border: "1px solid #252B36", borderRadius: 6, padding: "7px 11px", fontSize: 13, minWidth: 230 }}
                />
                <select value={kindFilter} onChange={(e) => setKindFilter(e.target.value)} style={{ background: "#090B10", color: "#E5E7EB", border: "1px solid #252B36", borderRadius: 6, padding: "7px 10px", fontSize: 12 }}>
                  <option value="all">All types</option>
                  <option value="tls_cert">tls_cert</option>
                  <option value="domain">domain</option>
                  <option value="runtime">runtime</option>
                  <option value="token">token</option>
                  <option value="trial">trial</option>
                </select>
                <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ background: "#090B10", color: "#E5E7EB", border: "1px solid #252B36", borderRadius: 6, padding: "7px 10px", fontSize: 12 }}>
                  <option value="all">All statuses</option>
                  <option value="expired">expired</option>
                  <option value="critical">critical</option>
                  <option value="warning">warning</option>
                  <option value="ok">ok</option>
                  <option value="error">error</option>
                </select>
              </div>

              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid #252B36", color: "#8993A4", textAlign: "left" }}>
                      <th style={{ padding: "10px 8px" }}>Resource</th>
                      <th style={{ padding: "10px 8px" }}>Type</th>
                      <th style={{ padding: "10px 8px" }}>Severity</th>
                      <th style={{ padding: "10px 8px" }}>Remaining</th>
                      <th style={{ padding: "10px 8px" }}>Status</th>
                      <th style={{ padding: "10px 8px" }}>Affected Services</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredResources.map((item) => {
                      const badge = STATUS_STYLE[item.status] || STATUS_STYLE.ok;
                      return (
                        <tr key={item.resource_id} style={{ borderBottom: "1px solid #1B202B" }}>
                          <td style={{ padding: "10px 8px", fontWeight: 600 }}>{item.resource_id}</td>
                          <td style={{ padding: "10px 8px", color: "#8993A4" }}>{item.kind}</td>
                          <td style={{ padding: "10px 8px", textTransform: "uppercase", fontSize: 11 }}>{item.severity}</td>
                          <td style={{ padding: "10px 8px" }}>{item.days_remaining !== null ? `${item.days_remaining}d` : "n/a"}</td>
                          <td style={{ padding: "10px 8px" }}>
                            <span style={{ padding: "2px 8px", borderRadius: 999, fontSize: 11, background: badge.bg, border: `1px solid ${badge.border}`, color: badge.color }}>
                              {badge.label}
                            </span>
                          </td>
                          <td style={{ padding: "10px 8px", color: "#8993A4" }}>
                            {item.affected_services.map((s) => s.service_name).join(", ") || "-"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {report && activeTab === "dependencies" && (
            <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(290px, 1fr))", gap: 16 }}>
              {serviceGraph.map((svc) => {
                const isSelected = selectedServiceName === svc.name;
                return (
                  <div
                    key={svc.name}
                    onClick={() => setSelectedServiceName(isSelected ? null : svc.name)}
                    style={{
                      background: "#11151D",
                      border: isSelected ? "1px solid #668BFF" : "1px solid #252B36",
                      borderRadius: 8,
                      padding: 16,
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ fontSize: 15 }}>{svc.name}</strong>
                      <span style={{ fontSize: 11, color: "#668BFF", textTransform: "uppercase" }}>{svc.criticality}</span>
                    </div>
                    <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
                      {svc.deps.map((d) => {
                        const badge = STATUS_STYLE[d.status] || STATUS_STYLE.ok;
                        return (
                          <div key={d.resource_id} style={{ background: "#090B10", border: "1px solid #252B36", borderRadius: 6, padding: 10 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                              <span style={{ fontWeight: 600 }}>{d.resource_id}</span>
                              <span style={{ color: badge.color }}>{badge.label}</span>
                            </div>
                            <div style={{ fontSize: 12, color: "#8993A4", marginTop: 4 }}>{d.impact}</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </section>
          )}

          {report && activeTab === "timeline" && (
            <section style={{ background: "#11151D", border: "1px solid #252B36", borderRadius: 8, padding: 18 }}>
              <h2 style={{ margin: "0 0 12px", fontSize: 15 }}>Upcoming Expiry &amp; Rotation Timeline</h2>
              <div style={{ display: "grid", gap: 10 }}>
                {impacts.map((item) => (
                  <div key={item.resource_id} style={{ display: "flex", justifyContent: "space-between", background: "#090B10", border: "1px solid #252B36", borderRadius: 6, padding: 12, fontSize: 13 }}>
                    <span><strong>{item.expires_on || "Pending probe"}</strong> — {item.resource_id} ({item.kind})</span>
                    <span style={{ color: "#8993A4" }}>{item.days_remaining !== null ? `${item.days_remaining} days` : "Offline"}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {report && activeTab === "alerts" && (
            <section style={{ background: "#11151D", border: "1px solid #252B36", borderRadius: 8, padding: 18 }}>
              <h2 style={{ margin: "0 0 8px", fontSize: 15 }}>Alert Cadence &amp; Supported Channels</h2>
              <p style={{ margin: "0 0 14px", fontSize: 13, color: "#8993A4" }}>
                Triggers at 30, 14, 7, and 1 day(s) remaining or when expired. Backend notifier supports Slack, Microsoft Teams, Telegram, Discord, and SMTP Email.
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
                {["Slack Webhook", "Microsoft Teams", "Telegram Bot", "Discord Webhook", "SMTP Email"].map((ch) => (
                  <div key={ch} style={{ background: "#090B10", border: "1px solid #252B36", borderRadius: 6, padding: 12, fontSize: 13 }}>
                    <strong>{ch}</strong>
                  </div>
                ))}
              </div>
            </section>
          )}

          {report && activeTab === "logs" && (
            <section style={{ background: "#11151D", border: "1px solid #252B36", borderRadius: 8, padding: 18 }}>
              <h2 style={{ margin: "0 0 12px", fontSize: 15 }}>DuckDB Snapshot History</h2>
              {historyItems.length === 0 ? (
                <p style={{ margin: 0, fontSize: 13, color: "#8993A4" }}>
                  No snapshots recorded yet. Run <code>deadline-map status --db snapshots.duckdb</code> and pass <code>--db</code> to <code>serve</code> to populate history.
                </p>
              ) : (
                <div style={{ display: "grid", gap: 8, fontSize: 12 }}>
                  {historyItems.map((row, idx) => (
                    <div key={idx} style={{ background: "#090B10", border: "1px solid #252B36", borderRadius: 6, padding: 10 }}>
                      <strong>{row.resource_id}</strong> · {row.status} · {row.days_remaining ?? "n/a"}d · score {row.priority_score}
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {report && activeTab === "analytics" && (
            <section style={{ background: "#11151D", border: "1px solid #252B36", borderRadius: 8, padding: 18 }}>
              <h2 style={{ margin: "0 0 12px", fontSize: 15 }}>Priority Score &amp; Blast-Radius Distribution</h2>
              <div style={{ display: "grid", gap: 10 }}>
                {impacts.map((item) => (
                  <div key={item.resource_id}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                      <span>{item.resource_id} ({item.affected_services.length} services)</span>
                      <span style={{ color: "#668BFF" }}>{item.priority_score}</span>
                    </div>
                    <div style={{ height: 8, background: "#090B10", borderRadius: 999, overflow: "hidden", border: "1px solid #252B36" }}>
                      <div style={{ width: `${Math.min(100, item.priority_score)}%`, height: "100%", background: "#668BFF" }} />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {report && activeTab === "settings" && (
            <section style={{ background: "#11151D", border: "1px solid #252B36", borderRadius: 8, padding: 18, display: "grid", gap: 14 }}>
              <h2 style={{ margin: "0 0 4px", fontSize: 15 }}>Runtime &amp; Probe Settings</h2>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                <input type="checkbox" checked={offline} onChange={(e) => setOffline(e.target.checked)} />
                Offline mode (skip live TLS / RDAP / EOL external lookups)
              </label>
              <div style={{ fontSize: 12, color: "#8993A4" }}>
                API Base URL: <code style={{ color: "#E5E7EB" }}>{API_BASE}</code>
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

function KpiCard({ label, value, sub, accent }) {
  return (
    <div style={{ background: "#11151D", border: "1px solid #252B36", borderRadius: 8, padding: 16 }}>
      <div style={{ fontSize: 11, color: "#8993A4", letterSpacing: "0.04em" }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: accent, marginTop: 6 }}>{value}</div>
      <div style={{ fontSize: 12, color: "#8993A4", marginTop: 4 }}>{sub}</div>
    </div>
  );
}
