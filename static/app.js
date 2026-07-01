const TERMINAL_STATUSES = ["COMPLETED", "FAILED"];

function statusBadgeHtml(status) {
  return `<span class="badge badge-${status}">${status}</span>`;
}

function pollDocumentStatus(documentId, onUpdate, intervalMs = 2000) {
  const tick = async () => {
    const res = await fetch(`/documents/${documentId}/status`);
    if (!res.ok) return;
    const data = await res.json();
    onUpdate(data);
    if (!TERMINAL_STATUSES.includes(data.status)) {
      setTimeout(tick, intervalMs);
    }
  };
  tick();
}

function highlightMatches(container, query) {
  if (!query) return;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`(${escaped})`, "gi");
  container.innerHTML = container.textContent.replace(regex, "<mark>$1</mark>");
}
