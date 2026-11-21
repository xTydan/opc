"use strict";

const state = { rows: [], report: null };
const $ = (id) => document.getElementById(id);
const money = (value) => value == null ? "—" : new Intl.NumberFormat("pl-PL", {
  style: "currency", currency: "PLN", maximumFractionDigits: 0
}).format(value);
const number = (value) => value == null ? "—" : new Intl.NumberFormat("pl-PL", {
  maximumFractionDigits: 1
}).format(value);

function safeListingUrl(value) {
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || !(url.hostname === "olx.pl" || url.hostname.endsWith(".olx.pl"))) return null;
    return url.href;
  } catch { return null; }
}
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}
function cardFor(row) {
  const card = el("article", "listing-card");
  const top = el("div", "card-top");
  const heading = el("div");
  heading.append(el("h3", "card-title", row.title || "Oferta bez tytułu"));
  const meta = [row.location, row.date_added ? "Dodano: " + row.date_added : null, row.status ? "Status: " + row.status : null].filter(Boolean).join(" · ");
  heading.append(el("div", "card-meta", meta || "Brak dodatkowych informacji"));
  top.append(heading);

  let tagClass = "tag warn", tagText = "Niekompletne dane";
  if (row.analysis_status === "ready" && row.meets_target) { tagClass = "tag good"; tagText = "Spełnia ustawiony próg"; }
  else if (row.analysis_status === "ready") { tagClass = "tag"; tagText = "Pełna analiza"; }
  top.append(el("span", tagClass, tagText));
  card.append(top);

  const stats = el("div", "card-stats");
  const statItems = [
    ["Cena zakupu", money(row.listing_price)],
    ["Wartość znanych części", money(row.component_value_total ?? row.known_component_value_partial)],
    ["Szacowany zysk", row.estimated_net_profit == null ? "Nie wyliczono" : money(row.estimated_net_profit)],
    ["ROI", row.roi_percent == null ? "—" : number(row.roi_percent) + "%"]
  ];
  for (const item of statItems) {
    const stat = el("div", "stat");
    stat.append(el("span", "", item[0]));
    const positive = item[0] === "Szacowany zysk" && row.estimated_net_profit != null && row.estimated_net_profit > 0;
    stat.append(el("strong", positive ? "profit" : "", item[1]));
    stats.append(stat);
  }
  card.append(stats);

  const actions = el("div", "card-actions");
  const linkUrl = safeListingUrl(row.url);
  if (linkUrl) {
    const link = el("a", "text-link", "Otwórz ogłoszenie ↗");
    link.href = linkUrl; link.target = "_blank"; link.rel = "noopener noreferrer";
    actions.append(link);
  } else actions.append(el("span", "card-meta", "Brak poprawnego linku OLX"));
  actions.append(el("span", "card-meta", row.maximum_purchase_price_for_target_profit != null
    ? "Maks. cena zakupu: " + money(row.maximum_purchase_price_for_target_profit)
    : row.analysis_status === "incomplete_inventory" ? "Najpierw uzupełnij konfigurację" : "Uzupełnij wyceny części"));
  card.append(actions);

  const details = el("details");
  details.append(el("summary", "", "Szczegóły podzespołów (" + (row.components || []).length + ")"));
  const componentList = el("div", "component-list");
  for (const component of row.components || []) {
    const item = el("div", "component");
    item.append(el("strong", "", (component.category || "część") + " · " + (component.model || "Nieznany model")));
    const value = component.estimated_sale_price == null ? "Brak wyceny" : "Wycena: " + money(component.estimated_sale_price);
    const confidence = component.confidence ? "Pewność: " + component.confidence : "Pewność nieokreślona";
    const comps = "Porównywalne oferty: " + (component.comparable_listings ?? "brak danych");
    item.append(el("small", "", value + " · " + confidence + " · " + comps));
    if (component.valuation && component.valuation.median_price != null) {
      const q1 = component.valuation.q1_price == null ? "—" : money(component.valuation.q1_price);
      const median = money(component.valuation.median_price);
      const latest = component.valuation.latest_comparable_at || "brak daty";
      item.append(el("small", "", "OLX: Q1 " + q1 + " · mediana " + median + " · aktualizacja " + latest));
    }
    if (component.valuation && component.valuation.reason) {
      item.append(el("small", "", "Wycena: " + component.valuation.reason));
    }
    const benchmark = (row.benchmark_scores_used || []).find((entry) =>
      entry.category === component.category && entry.model === component.model
    );
    if (benchmark) {
      const sourceLine = "Benchmark: " + benchmark.benchmark + " · wynik " + number(benchmark.score)
        + " · " + (benchmark.source || "źródło nieznane")
        + " · " + (benchmark.license || "licencja nieznana")
        + " · aktualizacja " + (benchmark.dataset_updated_at || "brak daty");
      item.append(el("small", "", sourceLine));
      try {
        const sourceUrl = new URL(benchmark.url);
        if (sourceUrl.protocol === "https:") {
          const sourceLink = el("a", "text-link", "Źródło benchmarku ↗");
          sourceLink.href = sourceUrl.href;
          sourceLink.target = "_blank";
          sourceLink.rel = "noopener noreferrer";
          item.append(sourceLink);
        }
      } catch { /* Invalid source URLs are displayed as provenance text only. */ }
    }
    if (component.attributes && Object.keys(component.attributes).length) {
      const attrs = Object.entries(component.attributes)
        .filter((entry) => entry[1] !== null && entry[1] !== undefined && entry[1] !== false)
        .map((entry) => entry[0] + ": " + entry[1]).join(" · ");
      if (attrs) item.append(el("small", "", attrs));
    }
    if (component.evidence) item.append(el("small", "", "Źródło rozpoznania: " + component.evidence));
    componentList.append(item);
  }
  details.append(componentList);
  const missing = [
    ...(row.missing_required_categories || []).map((x) => "Brak rozpoznania: " + x),
    ...(row.missing_valuations || []).map((x) => "Brak wyceny kluczowej części: " + x),
    ...(row.missing_optional_valuations || []).map((x) => "Pominięta wycena dodatku: " + x)
  ];
  if (missing.length) details.append(el("p", "missing-list", missing.join(" · ")));
  if (row.profit_basis) details.append(el("p", "card-meta", row.profit_basis));
  card.append(details);
  if (row.description) {
    const descriptionDetails = el("details");
    descriptionDetails.append(el("summary", "", "Pełny opis ogłoszenia"));
    descriptionDetails.append(el("p", "description", row.description));
    card.append(descriptionDetails);
  }
  return card;
}
function filteredRows() {
  const query = $("search-input").value.trim().toLocaleLowerCase("pl-PL");
  const filter = $("status-filter").value;
  const sort = $("sort-select").value;
  let rows = state.rows.filter((row) => {
    const text = [row.title, row.location, ...(row.components || []).map((c) => c.model)].join(" ").toLocaleLowerCase("pl-PL");
    if (query && !text.includes(query)) return false;
    if (filter === "ready" && row.analysis_status !== "ready") return false;
    if (filter === "incomplete" && row.analysis_status === "ready") return false;
    if (filter === "target" && !row.meets_target) return false;
    return true;
  });
  rows = [...rows].sort((a, b) => {
    if (sort === "price") return (a.listing_price ?? Infinity) - (b.listing_price ?? Infinity);
    if (sort === "roi") return (b.roi_percent ?? -Infinity) - (a.roi_percent ?? -Infinity);
    if (sort === "newest") return String(b.collected_at || "").localeCompare(String(a.collected_at || ""));
    return (b.estimated_net_profit ?? -Infinity) - (a.estimated_net_profit ?? -Infinity);
  });
  return rows;
}
function render() {
  $("results-list").replaceChildren();
  const rows = filteredRows();
  $("empty-state").hidden = state.rows.length > 0;
  if (state.rows.length > 0 && rows.length === 0) {
    const noMatch = el("div", "empty-state");
    noMatch.append(el("h3", "", "Brak wyników dla wybranych filtrów"));
    noMatch.append(el("p", "", "Zmień tekst wyszukiwania lub filtr statusu."));
    $("results-list").append(noMatch);
  } else for (const row of rows) $("results-list").append(cardFor(row));

  $("metric-total").textContent = state.rows.length;
  $("metric-ready").textContent = state.rows.filter((r) => r.analysis_status === "ready").length;
  $("metric-target").textContent = state.rows.filter((r) => r.meets_target).length;
  $("metric-missing").textContent = state.rows.filter((r) => r.analysis_status !== "ready").length;
}
function validateReport(data) {
  if (!data || typeof data !== "object" || !Array.isArray(data.results)) {
    throw new Error("To nie jest raport z analyze_import.py. Oczekiwano pola results[] w głównym obiekcie.");
  }
  for (const row of data.results) {
    if (!row || typeof row !== "object" || typeof row.listing_price !== "number") {
      throw new Error("Raport zawiera rekord w nieprawidłowym formacie.");
    }
  }
}
async function importFile(file) {
  const status = $("file-status");
  try {
    if (!file || !file.name.toLowerCase().endsWith(".json")) throw new Error("Wybierz plik JSON.");
    const data = JSON.parse(await file.text());
    validateReport(data);
    state.report = data; state.rows = data.results;
    status.textContent = "Wczytano " + file.name + " · " + state.rows.length + " ofert";
    $("report-meta").textContent = data.exported_at ? "Eksport: " + data.exported_at : "Raport zaimportowany";
    for (const id of ["search-input", "status-filter", "sort-select", "clear-button"]) $(id).disabled = false;
    render();
  } catch (error) { status.textContent = error.message || "Nie udało się wczytać pliku."; }
}
$("report-file").addEventListener("change", (event) => importFile(event.target.files?.[0]));
$("search-input").addEventListener("input", render);
$("status-filter").addEventListener("change", render);
$("sort-select").addEventListener("change", render);
$("clear-button").addEventListener("click", () => {
  state.rows = []; state.report = null; $("report-file").value = "";
  $("file-status").textContent = "Nie wczytano jeszcze raportu.";
  $("report-meta").textContent = "Oczekiwanie na plik";
  for (const id of ["search-input", "status-filter", "sort-select", "clear-button"]) $(id).disabled = true;
  $("search-input").value = ""; render();
});
