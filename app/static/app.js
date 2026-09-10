const el = (id) => document.getElementById(id);

const state = { scenarios: [], current: null };

const pretty = (obj) => JSON.stringify(obj, null, 2);
const pct = (value) => `${Math.round(Number(value) * 100)}%`;

function setBar(id, value) {
  el(id).style.width = `${Math.max(0, Math.min(100, Math.round(Number(value) * 100)))}%`;
}

function chipList(id, values) {
  const root = el(id);
  root.replaceChildren();
  if (!values || values.length === 0) {
    const empty = document.createElement("span");
    empty.className = "muted";
    empty.textContent = "none";
    root.appendChild(empty);
    return;
  }
  values.forEach((value) => {
    const span = document.createElement("span");
    span.className = "chip";
    span.textContent = String(value);
    root.appendChild(span);
  });
}

function showEditorError(message = "") {
  const root = el("editorError");
  root.textContent = message;
  root.classList.toggle("hidden", !message);
}

function loadScenario() {
  const id = el("scenarioSelect").value;
  state.current = state.scenarios.find((scenario) => scenario.id === id);
  if (!state.current) return;
  el("requestEditor").value = pretty(state.current.request);
  el("domainTag").textContent = state.current.request.action.domain;
  el("scenarioNote").textContent = state.current.description;
  showEditorError();
}

function renderDecision(result) {
  const badge = el("decisionBadge");
  badge.className = `decision ${result.decision}`;
  badge.textContent = result.decision.toUpperCase();
  el("decisionRationale").textContent = result.rationale;
  el("nextStep").textContent = result.next_step;
  el("policyVersion").textContent = result.policy_version;

  el("confidence").textContent = pct(result.confidence);
  el("risk").textContent = pct(result.risk_score);
  el("evidenceStrength").textContent = pct(result.evidence_strength);
  el("reversibility").textContent = `${result.reversibility.label} · ${pct(result.reversibility.score)}`;
  el("costOfError").textContent = result.cost_of_error;

  setBar("confidenceBar", result.confidence);
  setBar("riskBar", result.risk_score);
  setBar("evidenceBar", result.evidence_strength);
  chipList("evidenceUsed", result.evidence_used);
  chipList("evidenceRejected", result.evidence_rejected);
  chipList("evidenceConflicts", result.evidence_conflicts);
  chipList("missingInfo", result.missing_information);
  chipList("riskFactors", result.risk_factors);
  chipList("reasonCodes", result.reason_codes);
  el("resolvedFacts").textContent = pretty(result.resolved_facts);
}

function summarizePayload(stage, payload) {
  if (stage === "input_received") {
    const req = payload.request;
    return `${req.action.type} on ${req.action.target} · actor ${req.context.actor}`;
  }
  if (stage === "evidence_analyzed") {
    const conflict = payload.conflicts.length ? ` · conflicts: ${payload.conflicts.join(", ")}` : "";
    const rejected = payload.rejected_ids.length ? ` · rejected: ${payload.rejected_ids.length}` : "";
    return `strength ${pct(payload.strength)} · used ${payload.used_ids.length}${rejected}${conflict}`;
  }
  if (stage === "domain_assessed") {
    return `base risk ${pct(payload.base_risk)} · reversibility ${pct(payload.reversibility_score)} · cost ${payload.cost_of_error}`;
  }
  if (stage === "signals_computed") {
    return `confidence ${pct(payload.confidence)} · risk ${pct(payload.risk_score)} · missing ${payload.missing_information.length}`;
  }
  if (stage === "decision_emitted") {
    return `${payload.decision.toUpperCase()} · ${payload.reason_codes.join(", ")}`;
  }
  return pretty(payload);
}

function renderAudit(audit) {
  const integrity = el("auditIntegrity");
  integrity.textContent = audit.chain_valid ? "hash chain verified" : "audit integrity failure";
  integrity.className = `integrity ${audit.chain_valid ? "ok" : "bad"}`;

  const timeline = el("auditTimeline");
  timeline.replaceChildren();
  audit.events.forEach((event) => {
    const row = document.createElement("div");
    row.className = "event";

    const seq = document.createElement("div");
    seq.className = "event-seq";
    seq.textContent = `#${event.sequence}`;

    const stage = document.createElement("div");
    stage.className = "event-stage";
    stage.textContent = event.stage;

    const summary = document.createElement("div");
    summary.className = "event-summary";
    summary.textContent = summarizePayload(event.stage, event.payload);

    const hash = document.createElement("span");
    hash.className = "hash";
    hash.textContent = `sha256 ${event.event_hash.slice(0, 24)}…`;
    summary.appendChild(hash);

    const disclosure = document.createElement("details");
    disclosure.className = "audit-details";
    const disclosureLabel = document.createElement("summary");
    disclosureLabel.textContent = "view event payload";
    const payload = document.createElement("pre");
    payload.textContent = pretty(event.payload);
    disclosure.append(disclosureLabel, payload);
    summary.appendChild(disclosure);

    row.append(seq, stage, summary);
    timeline.appendChild(row);
  });
}

async function runDecision() {
  showEditorError();
  let payload;
  try {
    payload = JSON.parse(el("requestEditor").value);
  } catch (error) {
    showEditorError(`Invalid JSON: ${error.message}`);
    return;
  }

  const runBtn = el("runBtn");
  runBtn.disabled = true;
  runBtn.textContent = "Evaluating…";

  try {
    const response = await fetch("/api/decisions/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail ? pretty(result.detail) : `Request failed (${response.status})`);
    }
    renderDecision(result);

    const auditResponse = await fetch(`/api/decisions/${result.decision_id}/audit`);
    if (!auditResponse.ok) throw new Error("Decision succeeded but the audit trail could not be loaded.");
    renderAudit(await auditResponse.json());
  } catch (error) {
    showEditorError(error.message || String(error));
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = "Run decision";
  }
}

async function boot() {
  const response = await fetch("/api/scenarios");
  if (!response.ok) throw new Error("Could not load demo scenarios.");
  state.scenarios = await response.json();

  const select = el("scenarioSelect");
  state.scenarios.forEach((scenario) => {
    const option = document.createElement("option");
    option.value = scenario.id;
    option.textContent = scenario.title;
    select.appendChild(option);
  });
  loadScenario();
}

el("loadBtn").addEventListener("click", loadScenario);
el("scenarioSelect").addEventListener("change", loadScenario);
el("runBtn").addEventListener("click", runDecision);

boot().catch((error) => showEditorError(error.message || String(error)));
