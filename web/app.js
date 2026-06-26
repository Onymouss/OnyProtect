const TAB_META = {
  dashboard: {
    title: "Dashboard",
    subtitle: "System security posture and hardening status",
    loader: loadDashboard,
    search: false,
  },
  profiles: {
    title: "Profiles",
    subtitle: "One-click hardening bundles for field deployment",
    loader: loadProfiles,
    search: false,
  },
  registry: {
    title: "Registry",
    subtitle: "Core authentication, LSA, and system hardening keys",
    loader: () => loadRegistry("security", "registry-grid"),
  },
  network: {
    title: "Network",
    subtitle: "SMB, NTLM, LLMNR, WPAD, and network attack surface",
    loader: () => loadRegistry("network", "network-grid"),
  },
  firewall: {
    title: "Firewall",
    subtitle: "Windows Firewall policies, logging, and inbound blocking",
    loader: () => loadRegistry("firewall", "firewall-grid"),
  },
  dns: {
    title: "DNS",
    subtitle: "DNS over HTTPS, leak prevention, and secure resolution",
    loader: () => loadRegistry("dns", "dns-grid"),
  },
  privacy: {
    title: "Privacy",
    subtitle: "Telemetry, tracking, app permissions, and data collection",
    loader: () => loadRegistry("privacy", "privacy-grid"),
  },
  audit: {
    title: "Audit",
    subtitle: "Event logging, process creation, and forensic readiness",
    loader: () => loadRegistry("audit", "audit-grid"),
  },
  accounts: {
    title: "Accounts",
    subtitle: "Lockout policy, password rules, and logon hardening",
    loader: () => loadRegistry("accounts", "accounts-grid"),
  },
  explorer: {
    title: "Explorer",
    subtitle: "File visibility, autoplay, history, and Explorer behavior",
    loader: () => loadRegistry("explorer", "explorer-grid"),
  },
  services: {
    title: "Services",
    subtitle: "Toggle on to disable background services",
    loader: loadServices,
  },
  startup: {
    title: "Startup",
    subtitle: "Programs that run at boot — toggle off to disable",
    loader: loadStartup,
  },
  restore: {
    title: "Restore Point",
    subtitle: "Create a Windows rollback point before hardening",
    loader: loadRestorePoint,
    search: false,
  },
  recovery: {
    title: "Recovery",
    subtitle: "Restore original registry and service states saved by OnyProtect",
    loader: loadRecovery,
  },
  download: {
    title: "Download",
    subtitle: "Privacy, security, dev, and utility apps",
    loader: loadDownloads,
  },
};

document.addEventListener("DOMContentLoaded", init);

function init() {
  setupNavigation();
  setupSearch();
  TAB_META.dashboard.loader();
  fetchVersion();
}

function setupNavigation() {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

function switchTab(tab) {
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
  document.querySelector(`.nav-item[data-tab="${tab}"]`)?.classList.add("active");

  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
  document.getElementById(`tab-${tab}`)?.classList.add("active");

  const meta = TAB_META[tab];
  if (meta) {
    document.getElementById("page-title").textContent = meta.title;
    document.getElementById("page-subtitle").textContent = meta.subtitle;
    document.getElementById("search-wrap").style.display = meta.search === false ? "none" : "";
    meta.loader?.();
  }

  document.getElementById("search").value = "";
  filterCards("");
}

function setupSearch() {
  document.getElementById("search").addEventListener("input", (e) => {
    filterCards(e.target.value.trim().toLowerCase());
  });
}

function filterCards(query) {
  const panel = document.querySelector(".tab-panel.active");
  if (!panel) return;

  panel.querySelectorAll(".tweak-card, .download-card, .profile-card, .recovery-card").forEach((card) => {
    const text = card.textContent.toLowerCase();
    card.classList.toggle("hidden", query.length > 0 && !text.includes(query));
  });
}

function loadingRow(text = "Loading...") {
  return `<div class="tweak-card"><div class="tweak-info"><span class="tweak-name">${text}</span></div></div>`;
}

async function loadDashboard() {
  const el = document.getElementById("dashboard-content");
  el.innerHTML = loadingRow("Scanning system...");

  try {
    const info = await window.pywebview.api.get_system_info();
    const fmt = (v) => (v === null || v === undefined ? "Unknown" : v ? "Yes" : "No");

    el.innerHTML = `
      <div class="stat-grid">
        <div class="stat-card highlight">
          <span class="stat-label">Hardening Score</span>
          <span class="stat-value">${info.hardening_score}%</span>
          <span class="stat-detail">${info.tweaks_enabled} / ${info.tweaks_total} tweaks active</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Administrator</span>
          <span class="stat-value ${info.admin ? "ok" : "warn"}">${fmt(info.admin)}</span>
          <span class="stat-detail">${info.admin ? "Full hardening available" : "Run as admin for HKLM"}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Defender RT</span>
          <span class="stat-value">${fmt(info.defender)}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Firewall</span>
          <span class="stat-value">${fmt(info.firewall)}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Secure Boot</span>
          <span class="stat-value">${fmt(info.secure_boot)}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">UAC</span>
          <span class="stat-value">${info.uac === 1 ? "On" : info.uac ?? "?"}</span>
        </div>
      </div>
      <div class="info-panel">
        <div class="info-row"><span>OS</span><span>${escapeHtml(info.os)}</span></div>
        <div class="info-row"><span>Architecture</span><span>${escapeHtml(info.arch)}</span></div>
      </div>
      <p class="dashboard-note">Use <strong>Profiles</strong> for one-click deployment, or configure individual tabs for granular control.</p>`;

    setStatus(`Hardening score: ${info.hardening_score}%`);
  } catch (err) {
    el.innerHTML = loadingRow("Failed to load dashboard");
    setStatus(`Error: ${err}`);
  }
}

async function loadProfiles() {
  const grid = document.getElementById("profiles-grid");
  grid.innerHTML = loadingRow();

  try {
    const profiles = await window.pywebview.api.get_profiles();
    grid.innerHTML = profiles.map(profileCard).join("");
    attachProfileListeners(grid);
    setStatus(`${profiles.length} profiles available`);
  } catch (err) {
    grid.innerHTML = loadingRow("Failed to load");
    setStatus(`Error: ${err}`);
  }
}

async function loadRegistry(category, gridId) {
  const grid = document.getElementById(gridId);
  grid.innerHTML = loadingRow();

  try {
    const tweaks = await window.pywebview.api.get_registry_tweaks(category);
    grid.innerHTML = tweaks.length ? tweaks.map(tweakCard).join("") : loadingRow("No tweaks");
    attachRegistryListeners(grid);
    setStatus(`${tweaks.length} tweaks`);
  } catch (err) {
    grid.innerHTML = loadingRow("Failed to load");
    setStatus(`Error: ${err}`);
  }
}

async function loadServices() {
  const grid = document.getElementById("services-grid");
  grid.innerHTML = loadingRow();

  try {
    const services = await window.pywebview.api.get_services();
    grid.innerHTML = services.map(serviceCard).join("");
    attachServiceListeners(grid);
    setStatus(`${services.length} services`);
  } catch (err) {
    grid.innerHTML = loadingRow("Failed to load");
    setStatus(`Error: ${err}`);
  }
}

async function loadStartup() {
  const grid = document.getElementById("startup-grid");
  grid.innerHTML = loadingRow();

  try {
    const items = await window.pywebview.api.get_startup_items();
    grid.innerHTML = items.length
      ? items.map(startupCard).join("")
      : loadingRow("No startup entries found");
    attachStartupListeners(grid);
    setStatus(`${items.length} startup entries`);
  } catch (err) {
    grid.innerHTML = loadingRow("Failed to load");
    setStatus(`Error: ${err}`);
  }
}

async function loadDownloads() {
  const grid = document.getElementById("download-grid");
  grid.innerHTML = loadingRow();

  try {
    const items = await window.pywebview.api.get_downloads();
    grid.innerHTML = items.map(downloadCard).join("");
    attachDownloadListeners(grid);
    setStatus(`${items.length} apps`);
  } catch (err) {
    grid.innerHTML = loadingRow("Failed to load");
    setStatus(`Error: ${err}`);
  }
}

async function loadRecovery() {
  const grid = document.getElementById("recovery-grid");
  grid.innerHTML = loadingRow();

  try {
    const items = await window.pywebview.api.get_recovery_items();
    grid.innerHTML = items.length
      ? items.map(recoveryCard).join("")
      : loadingRow("No saved changes yet");
    attachRecoveryListeners(grid);
    setStatus(`${items.length} recovery items`);
  } catch (err) {
    grid.innerHTML = loadingRow("Failed to load recovery items");
    setStatus(`Error: ${err}`);
  }
}

function loadRestorePoint() {
  const btn = document.getElementById("create-restore-point");
  const input = document.getElementById("restore-name");
  const note = document.getElementById("restore-note");

  if (!btn || btn.dataset.bound === "true") return;
  btn.dataset.bound = "true";

  btn.addEventListener("click", async () => {
    const description = input.value.trim() || "OnyProtect restore point";
    btn.disabled = true;
    btn.textContent = "Creating...";
    note.textContent = "Creating restore point. This can take a moment.";
    setStatus("Creating restore point...");

    try {
      const result = await window.pywebview.api.create_restore_point(description);
      note.textContent = result.message;
      setStatus(result.message);
      btn.textContent = result.success ? "Created" : "Retry";
    } catch (err) {
      const message = `Failed: ${err}`;
      note.textContent = message;
      setStatus(message);
      btn.textContent = "Retry";
    } finally {
      btn.disabled = false;
    }
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function tweakCard(item) {
  const checked = item.enabled ? "checked" : "";
  return `
    <div class="tweak-card" data-id="${item.id}" data-type="registry">
      <div class="tweak-info">
        <span class="tweak-name">${escapeHtml(item.name)}</span>
        <span class="help-tip" tabindex="0">?<span class="tip-text">${escapeHtml(item.info)}</span></span>
      </div>
      <label class="toggle"><input type="checkbox" ${checked}><span class="toggle-track"></span></label>
    </div>`;
}

function serviceCard(item) {
  const checked = item.enabled ? "checked" : "";
  const unavailable = item.available === false ? " unavailable" : "";
  return `
    <div class="tweak-card${unavailable}" data-id="${item.id}" data-type="service">
      <div class="tweak-info">
        <span class="tweak-name">${escapeHtml(item.name)}</span>
        <span class="help-tip" tabindex="0">?<span class="tip-text">${escapeHtml(item.info)}</span></span>
      </div>
      <label class="toggle"><input type="checkbox" ${checked} ${item.available === false ? "disabled" : ""}><span class="toggle-track"></span></label>
    </div>`;
}

function startupCard(item) {
  const checked = item.enabled ? "checked" : "";
  return `
    <div class="tweak-card" data-id="${escapeHtml(item.id)}" data-type="startup">
      <div class="tweak-info">
        <span class="tweak-name">${escapeHtml(item.name)}</span>
        <span class="help-tip" tabindex="0">?<span class="tip-text">${escapeHtml(item.info)}</span></span>
      </div>
      <label class="toggle"><input type="checkbox" ${checked}><span class="toggle-track"></span></label>
    </div>`;
}

function recoveryCard(item) {
  return `
    <div class="tweak-card recovery-card" data-id="${escapeHtml(item.id)}" data-type="${escapeHtml(item.type)}">
      <div class="download-card-body">
        <span class="dl-cat">${escapeHtml(item.type)}</span>
        <h3>${escapeHtml(item.name)}</h3>
        <p>${escapeHtml(item.detail)}</p>
      </div>
      <button class="btn-download btn-restore-item">Restore</button>
    </div>`;
}

function profileCard(item) {
  const levelClass = `level-${item.level}`;
  return `
    <div class="profile-card ${levelClass}" data-id="${item.id}" data-level="${escapeHtml(item.level)}">
      <div class="profile-header">
        <h3>${escapeHtml(item.name)}</h3>
        <span class="profile-level">${item.level}</span>
      </div>
      <p>${escapeHtml(item.info)}</p>
      <div class="profile-meta">${item.registry_count} registry · ${item.services_count} services</div>
      <button class="btn-apply">Apply Profile</button>
    </div>`;
}

function downloadCard(item) {
  return `
    <div class="download-card" data-id="${item.id}">
      <div class="download-card-body">
        <span class="dl-cat">${escapeHtml(item.category)}</span>
        <h3>${escapeHtml(item.name)}</h3>
        <p>${escapeHtml(item.desc)}</p>
      </div>
      <button class="btn-download">Get</button>
    </div>`;
}

function attachRegistryListeners(container) {
  container.querySelectorAll('[data-type="registry"]').forEach((card) => {
    const input = card.querySelector(".toggle input");
    input.addEventListener("change", async () => {
      const enable = input.checked;
      input.disabled = true;
      setStatus(`Applying...`);
      try {
        const result = await window.pywebview.api.set_registry_tweak(card.dataset.id, enable);
        if (!result.success) input.checked = !enable;
        setStatus(result.message);
      } catch (err) {
        input.checked = !enable;
        setStatus(`Failed: ${err}`);
      } finally {
        input.disabled = false;
      }
    });
  });
}

function attachServiceListeners(container) {
  container.querySelectorAll('[data-type="service"]').forEach((card) => {
    const input = card.querySelector(".toggle input");
    if (input.disabled) return;
    input.addEventListener("change", async () => {
      const harden = input.checked;
      input.disabled = true;
      try {
        const result = await window.pywebview.api.set_service(card.dataset.id, harden);
        if (!result.success) input.checked = !harden;
        setStatus(result.message);
      } catch (err) {
        input.checked = !harden;
        setStatus(`Failed: ${err}`);
      } finally {
        input.disabled = false;
      }
    });
  });
}

function attachStartupListeners(container) {
  container.querySelectorAll('[data-type="startup"]').forEach((card) => {
    const input = card.querySelector(".toggle input");
    input.addEventListener("change", async () => {
      const keepEnabled = input.checked;
      input.disabled = true;
      try {
        const result = await window.pywebview.api.set_startup_item(card.dataset.id, !keepEnabled);
        if (!result.success) input.checked = !keepEnabled;
        setStatus(result.message);
      } catch (err) {
        input.checked = !keepEnabled;
        setStatus(`Failed: ${err}`);
      } finally {
        input.disabled = false;
      }
    });
  });
}

function attachProfileListeners(container) {
  container.querySelectorAll(".profile-card").forEach((card) => {
    card.querySelector(".btn-apply")?.addEventListener("click", async () => {
      const name = card.querySelector("h3")?.textContent;
      const level = card.dataset.level;
      const btn = card.querySelector(".btn-apply");

      if (level === "medium" || level === "high") {
        const proceed = window.confirm(`${name} is a ${level} risk profile and may change security, networking, privacy, or service behavior. Continue?`);
        if (!proceed) return;

        const wantsRestorePoint = window.confirm("Create a Windows restore point before applying this profile?");
        if (wantsRestorePoint) {
          btn.disabled = true;
          btn.textContent = "Creating restore point...";
          setStatus("Creating restore point...");
          const restoreResult = await window.pywebview.api.create_restore_point(`OnyProtect before ${name}`);
          setStatus(restoreResult.message);
          if (!restoreResult.success) {
            const continueAnyway = window.confirm(`${restoreResult.message}\n\nApply the profile anyway?`);
            if (!continueAnyway) {
              btn.disabled = false;
              btn.textContent = "Apply Profile";
              return;
            }
          }
        }
      }

      btn.disabled = true;
      btn.textContent = "Applying...";
      setStatus(`Applying ${name}...`);
      try {
        const result = await window.pywebview.api.apply_profile(card.dataset.id);
        setStatus(result.message);
        btn.textContent = result.success ? "Applied" : "Retry";
      } catch (err) {
        setStatus(`Failed: ${err}`);
        btn.textContent = "Retry";
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function attachDownloadListeners(container) {
  container.querySelectorAll(".download-card").forEach((card) => {
    card.querySelector(".btn-download")?.addEventListener("click", async () => {
      try {
        const result = await window.pywebview.api.open_download(card.dataset.id);
        setStatus(result.message);
      } catch (err) {
        setStatus(`Failed: ${err}`);
      }
    });
  });
}

function attachRecoveryListeners(container) {
  container.querySelectorAll(".recovery-card").forEach((card) => {
    card.querySelector(".btn-restore-item")?.addEventListener("click", async () => {
      const btn = card.querySelector(".btn-restore-item");
      btn.disabled = true;
      btn.textContent = "Restoring...";
      setStatus("Restoring original state...");
      try {
        const result = await window.pywebview.api.restore_recovery_item(card.dataset.type, card.dataset.id);
        setStatus(result.message);
        if (result.success) {
          card.remove();
          if (!container.querySelector(".recovery-card")) {
            container.innerHTML = loadingRow("No saved changes yet");
          }
        } else {
          btn.textContent = "Retry";
        }
      } catch (err) {
        setStatus(`Failed: ${err}`);
        btn.textContent = "Retry";
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function setStatus(msg) {
  const el = document.getElementById("status-text");
  if (el) el.textContent = msg;
}

async function fetchVersion() {
  try {
    if (window.pywebview?.api?.get_version) {
      const version = await window.pywebview.api.get_version();
      document.getElementById("version").textContent = `v${version}`;
    }
  } catch { /* preview */ }
}
