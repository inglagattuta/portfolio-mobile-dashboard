const euro = new Intl.NumberFormat("it-IT", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

const pct = new Intl.NumberFormat("it-IT", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const number = new Intl.NumberFormat("it-IT", {
  maximumFractionDigits: 0,
});

const colors = {
  ink: "#f3f7f4",
  muted: "#9fb0aa",
  line: "rgba(255,255,255,.16)",
  green: "#69d39a",
  amber: "#f1c76b",
  red: "#ef7e74",
  blue: "#78a8ff",
};

function setText(id, text) {
  document.getElementById(id).textContent = text;
}

function formatDate(value) {
  const date = new Date(value);
  return date.toLocaleDateString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function drawLineChart(canvas, points, valueKey, options = {}) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const pad = { left: 42, right: 16, top: 18, bottom: 34 };

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "rgba(255,255,255,.03)";
  ctx.fillRect(0, 0, width, height);

  if (!points.length) return;

  const values = points.map((point) => point[valueKey]);
  const min = Math.min(...values, options.min ?? Infinity);
  const max = Math.max(...values, options.max ?? -Infinity);
  const span = max - min || 1;

  const xFor = (idx) => pad.left + (idx / Math.max(points.length - 1, 1)) * (width - pad.left - pad.right);
  const yFor = (value) => height - pad.bottom - ((value - min) / span) * (height - pad.top - pad.bottom);

  ctx.strokeStyle = colors.line;
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i < 4; i += 1) {
    const y = pad.top + (i / 3) * (height - pad.top - pad.bottom);
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
  }
  ctx.stroke();

  ctx.strokeStyle = options.color || colors.green;
  ctx.lineWidth = 4;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.beginPath();
  points.forEach((point, idx) => {
    const x = xFor(idx);
    const y = yFor(point[valueKey]);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = colors.muted;
  ctx.font = "22px system-ui, sans-serif";
  ctx.fillText(options.labelMin ? options.labelMin(min) : min.toFixed(0), 8, yFor(min));
  ctx.fillText(options.labelMax ? options.labelMax(max) : max.toFixed(0), 8, yFor(max) + 8);

  const first = points[0];
  const last = points[points.length - 1];
  ctx.fillText(formatDate(first.date), pad.left, height - 8);
  const endLabel = formatDate(last.date);
  const labelWidth = ctx.measureText(endLabel).width;
  ctx.fillText(endLabel, width - pad.right - labelWidth, height - 8);
}

function drawBars(canvas, months) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const pad = { left: 34, right: 14, top: 18, bottom: 42 };
  const max = Math.max(...months.map((item) => item.amount), 1);
  const slot = (width - pad.left - pad.right) / months.length;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "rgba(255,255,255,.03)";
  ctx.fillRect(0, 0, width, height);

  months.forEach((item, index) => {
    const barHeight = (item.amount / max) * (height - pad.top - pad.bottom);
    const x = pad.left + index * slot + slot * 0.16;
    const y = height - pad.bottom - barHeight;
    const barWidth = slot * 0.68;
    ctx.fillStyle = index % 2 ? colors.blue : colors.green;
    ctx.fillRect(x, y, barWidth, barHeight);

    ctx.fillStyle = colors.muted;
    ctx.font = "20px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(item.month, x + barWidth / 2, height - 12);
  });

  ctx.textAlign = "left";
}

function renderBlocks(blocks) {
  const list = document.getElementById("blockList");
  list.innerHTML = "";

  blocks.forEach((block) => {
    const row = document.createElement("article");
    row.className = "block-row";
    const fill = Math.min(Math.max(block.weight / 0.3, 0), 1) * 100;
    const target = Math.min(Math.max(block.target / 0.3, 0), 1) * 100;
    row.innerHTML = `
      <div class="block-top">
        <div class="block-title">
          <strong>${block.block} - ${block.role}</strong>
          <span class="block-meta">${block.state}</span>
        </div>
        <strong class="tone-${block.tone}">${pct.format(block.weight)}</strong>
      </div>
      <div class="bar" aria-hidden="true">
        <span style="width:${fill}%"></span>
        <i style="left:${target}%"></i>
      </div>
      <div class="block-meta">Target ${pct.format(block.target)} | Delta ${pct.format(block.delta)}</div>
    `;
    list.appendChild(row);
  });
}

function renderAlerts(alerts) {
  const list = document.getElementById("alertList");
  list.innerHTML = "";
  setText("alertCount", `${alerts.length} alert`);

  if (!alerts.length) {
    list.innerHTML = '<div class="alert-row"><span>Nessun alert fuori banda</span><strong class="tone-watch">OK</strong></div>';
    return;
  }

  alerts.forEach((alert) => {
    const row = document.createElement("article");
    row.className = "alert-row";
    row.innerHTML = `
      <span>${alert.block} - ${alert.state}</span>
      <strong class="tone-${alert.tone}">${pct.format(alert.delta)}</strong>
    `;
    list.appendChild(row);
  });
}

function wireTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
      document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(button.dataset.view).classList.add("active");
    });
  });
}

async function main() {
  wireTabs();
  const data = await loadSnapshot();

  setText("scoreValue", data.summary.portfolio_score);
  setText("totalValue", euro.format(data.summary.total_value));
  setText("totalPnl", euro.format(data.summary.total_pnl));
  setText("totalPnlPct", pct.format(data.summary.total_pnl_pct));
  setText("monthlyIncome", euro.format(data.dividends.monthly_estimate));
  setText("incomeDetail", `${data.dividends.year || ""} in corso`);
  setText("annualIncome", `${euro.format(data.dividends.annual)} ${data.dividends.year || ""}`);
  setText("actualYtd", `Reale YTD ${euro.format(data.dividends.actual_ytd || 0)}`);
  setText("futureIncome", `Stimato futuro ${euro.format(data.dividends.forecast_future || 0)}`);
  setText("yieldValue", `${pct.format(data.summary.yield_on_value)} yield`);
  setText("positionsCount", number.format(data.summary.positions_count));
  setText("lastUpdate", `Aggiornato ${formatDate(data.meta.source_mtime)}`);
  setText("returnLabel", pct.format(data.performance.total_return));
  setText("drawdownLabel", pct.format(data.performance.max_drawdown));

  drawLineChart(document.getElementById("performanceChart"), data.performance.series, "index", {
    min: 80,
    color: colors.green,
  });
  drawLineChart(document.getElementById("drawdownChart"), data.performance.series, "drawdown", {
    max: 0,
    color: colors.red,
    labelMin: (value) => pct.format(value),
    labelMax: (value) => pct.format(value),
  });
  drawBars(document.getElementById("incomeChart"), data.dividends.monthly);
  renderBlocks(data.blocks);
  renderAlerts(data.alerts);
}

async function loadSnapshot() {
  const encrypted = await loadEncryptedSnapshot();
  if (encrypted) return unlockEncryptedSnapshot(encrypted);

  try {
    const response = await fetch("portfolio_snapshot.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    document.body.classList.remove("locked");
    return data;
  } catch (error) {
    if (window.PORTFOLIO_SNAPSHOT) {
      document.body.classList.remove("locked");
      return window.PORTFOLIO_SNAPSHOT;
    }
    throw error;
  }
}

async function loadEncryptedSnapshot() {
  if (window.ENCRYPTED_PORTFOLIO_SNAPSHOT) return window.ENCRYPTED_PORTFOLIO_SNAPSHOT;

  try {
    const response = await fetch("encrypted_snapshot.json", { cache: "no-store" });
    if (!response.ok) return null;
    return await response.json();
  } catch (_error) {
    return null;
  }
}

function unlockEncryptedSnapshot(payload) {
  return new Promise((resolve) => {
    const form = document.getElementById("unlockForm");
    const input = document.getElementById("unlockCode");
    const error = document.getElementById("unlockError");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      error.textContent = "";

      try {
        const snapshot = await decryptSnapshot(payload, input.value);
        input.value = "";
        document.body.classList.remove("locked");
        resolve(snapshot);
      } catch (_error) {
        error.textContent = "Codice non valido";
        input.select();
      }
    });

    input.focus();
  });
}

async function decryptSnapshot(payload, passcode) {
  const salt = base64ToBytes(payload.salt);
  const iv = base64ToBytes(payload.iv);
  const tag = base64ToBytes(payload.tag);
  const ciphertext = base64ToBytes(payload.ciphertext);
  const cipherWithTag = concatBytes(ciphertext, tag);
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(passcode),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  const key = await crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt,
      iterations: payload.iterations,
      hash: "SHA-256",
    },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["decrypt"],
  );
  const plainBuffer = await crypto.subtle.decrypt(
    {
      name: "AES-GCM",
      iv,
      tagLength: 128,
    },
    key,
    cipherWithTag,
  );
  return JSON.parse(new TextDecoder().decode(plainBuffer));
}

function base64ToBytes(value) {
  return Uint8Array.from(atob(value), (char) => char.charCodeAt(0));
}

function concatBytes(left, right) {
  const out = new Uint8Array(left.length + right.length);
  out.set(left, 0);
  out.set(right, left.length);
  return out;
}

main().catch((error) => {
  document.body.innerHTML = `<main class="app-shell"><div class="panel">Errore caricamento snapshot: ${error.message}</div></main>`;
});
