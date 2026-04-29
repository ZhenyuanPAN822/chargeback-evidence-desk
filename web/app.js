let disputes = [];

const $ = (id) => document.getElementById(id);

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    $("tab-" + button.dataset.tab).classList.add("active");
  });
});

async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || "Request failed");
  return data;
}

$("sampleBtn").addEventListener("click", async () => {
  const response = await fetch("/api/sample");
  const data = await response.json();
  disputes = data.disputes;
  $("metadata").textContent = `Loaded realistic sample: ${data.metadata.row_count} disputes from ${data.metadata.source_system_hint}.`;
  renderReview();
});

$("parseCsvBtn").addEventListener("click", async () => {
  try {
    const data = await api("/api/parse-csv", { csv: $("csvInput").value });
    disputes = data.disputes;
    $("metadata").textContent = `Mapped ${data.metadata.row_count} rows. Source hint: ${data.metadata.source_system_hint}. ${data.metadata.warning || ""}`;
    renderReview();
  } catch (err) {
    $("metadata").textContent = err.message;
  }
});

$("parseTextBtn").addEventListener("click", async () => {
  try {
    const data = await api("/api/parse-text", { text: $("textInput").value });
    disputes.push(data.dispute);
    $("metadata").textContent = "Extracted one pasted-text dispute. Review fields before analysis.";
    renderReview();
  } catch (err) {
    $("metadata").textContent = err.message;
  }
});

$("addManualBtn").addEventListener("click", () => {
  const dispute = {
    dispute_id: $("m_dispute_id").value || `MANUAL-${Date.now()}`,
    processor: $("m_processor").value,
    reason: $("m_reason").value,
    amount: Number($("m_amount").value || 0),
    currency: $("m_currency").value || "USD",
    due_date: $("m_due_date").value,
    order_id: $("m_order_id").value,
    customer_email: $("m_customer_email").value,
    tracking_number: $("m_tracking_number").value,
    delivery_status: $("m_delivery_status").value,
    shipping_address_match: $("m_shipping_address_match").value,
    refund_status: $("m_refund_status").value,
    notes: $("m_notes").value,
    product_type: "physical",
    extraction_source: "manual",
    confidence: 0.85,
    needs_review: false,
    missing_fields: [],
  };
  disputes.push(dispute);
  renderReview();
});

$("analyzeBtn").addEventListener("click", async () => {
  try {
    const data = await api("/api/analyze", {
      disputes,
      scenario: { deadline_buffer_days: Number($("deadlineBuffer").value || 1) },
    });
    renderReport(data);
  } catch (err) {
    $("metadata").textContent = err.message;
  }
});

function renderReview() {
  const tbody = $("reviewTable").querySelector("tbody");
  tbody.innerHTML = "";
  disputes.forEach((item, index) => {
    const row = document.createElement("tr");
    const evidence = [];
    if (item.tracking_number) evidence.push("tracking");
    if (String(item.delivery_status || "").includes("delivered")) evidence.push("delivery");
    if (item.customer_messages) evidence.push("messages");
    if (item.refund_status) evidence.push("refund");
    row.innerHTML = `
      <td contenteditable onblur="edit(${index}, 'dispute_id', this.textContent)">${item.dispute_id || ""}</td>
      <td contenteditable onblur="edit(${index}, 'processor', this.textContent)">${item.processor || ""}</td>
      <td contenteditable onblur="edit(${index}, 'reason', this.textContent)">${item.reason || ""}</td>
      <td contenteditable onblur="edit(${index}, 'amount', this.textContent)">${item.amount || 0} ${item.currency || ""}</td>
      <td contenteditable onblur="edit(${index}, 'due_date', this.textContent)">${item.due_date || ""}</td>
      <td>${evidence.map(e => `<span class="pill good">${e}</span>`).join("") || '<span class="pill bad">evidence gap</span>'}</td>
      <td>${item.needs_review ? '<span class="pill bad">needs review</span>' : '<span class="pill good">ok</span>'}</td>
    `;
    tbody.appendChild(row);
  });
}

window.edit = function (index, field, value) {
  if (field === "amount") {
    disputes[index][field] = Number(String(value).replace(/[^0-9.]/g, "") || 0);
  } else {
    disputes[index][field] = value.trim();
  }
};

function renderReport(data) {
  $("mCount").textContent = data.summary.dispute_count;
  $("mAmount").textContent = "$" + Number(data.summary.total_amount).toLocaleString();
  $("mCritical").textContent = data.summary.critical_count;
  $("mReview").textContent = data.summary.needs_review_count;
  $("reportOutput").value = data.markdown_report;
  $("savedPaths").textContent = `Saved Markdown and JSON reports locally: ${data.saved_outputs.markdown}`;

  $("processorBoard").innerHTML = Object.entries(data.processor_summary).map(([processor, item]) => `
    <div class="case">
      <h3>${processor}</h3>
      <span class="pill">${item.count} disputes</span>
      <span class="pill">$${Number(item.amount).toLocaleString()}</span>
      <span class="pill bad">${item.critical} critical</span>
    </div>
  `).join("");

  $("whatIf").innerHTML = Object.entries(data.what_if || {}).map(([key, value]) => `
    <p><strong>${key.replaceAll("_", " ")}:</strong> ${value}</p>
  `).join("");

  $("queue").innerHTML = data.queue.map((item) => {
    const d = item.dispute;
    return `
      <div class="case ${item.urgency}">
        <h3>${d.dispute_id} · ${d.processor} · ${d.amount} ${d.currency}</h3>
        <span class="pill ${item.urgency === "critical" || item.urgency === "expired" ? "bad" : ""}">${item.urgency}</span>
        <span class="pill">evidence ${item.evidence_score}/100</span>
        <span class="pill">${item.confidence} confidence</span>
        <p><strong>Missing:</strong> ${item.missing_evidence.length ? item.missing_evidence.join(", ") : "none"}</p>
        <p><strong>Next action:</strong> ${item.recommended_action}</p>
        <p><strong>Packet:</strong> ${item.suggested_packet_sections.join(" · ")}</p>
      </div>
    `;
  }).join("");
}

