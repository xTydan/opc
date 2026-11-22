const button = document.getElementById("collect");
const status = document.getElementById("status");

async function waitForJob(jobId) {
  while (true) {
    await new Promise(resolve => setTimeout(resolve, 1500));
    const response = await fetch(`http://127.0.0.1:8765/status?job=${encodeURIComponent(jobId)}`);
    const job = await response.json();
    if (!response.ok) throw new Error(job.error || "Nie udało się sprawdzić postępu.");
    if (job.state === "failed") throw new Error(job.error || "Pobieranie zakończyło się błędem.");
    if (job.state === "completed") {
      status.textContent = `Gotowe.\nLinki: ${job.total}\nPobrane opisy: ${job.successful}\nPlik: data/imports/olx-listings.json`;
      return;
    }
    status.textContent = `Pobieranie ogłoszeń…\nPostęp: ${job.completed || 0}/${job.total}\nNie zamykaj okna, jeśli chcesz obserwować postęp. Zadanie działa również po zamknięciu popupu.`;
  }
}

button.addEventListener("click", async () => {
  button.disabled = true;
  status.textContent = "Odczytuję linki ze strony OLX…";
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    if (!tab?.id || !tab.url?.startsWith("https://www.olx.pl/")) {
      throw new Error("Najpierw otwórz stronę wyników OLX.");
    }
    const collected = await chrome.tabs.sendMessage(tab.id, {action: "COLLECT_LINKS"});
    if (!collected?.urls?.length) throw new Error("Nie znalazłem linków do ogłoszeń na tej stronie.");
    status.textContent = `Znaleziono ${collected.urls.length} linków. Uruchamiam pobieranie…`;
    const response = await fetch("http://127.0.0.1:8765/collect", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({urls: collected.urls})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Lokalny skrypt zwrócił błąd.");
    await waitForJob(result.job_id);
  } catch (error) {
    status.textContent = error.message + (error.message.includes("Failed to fetch") ? "\nUruchom najpierw: py scripts/olx_local_server.py" : "");
  } finally {
    button.disabled = false;
  }
});