/**
 * charts.js — VIEW layer JavaScript
 * Renders mini sparklines and full price charts using Chart.js CDN.
 * Completely decoupled: reads data from data-* attributes on DOM elements.
 */

// ── Colour helpers ─────────────────────────────────────────────────────────
const SIGNAL_COLORS = {
  "STRONG BUY":  "#48bb78",
  "BUY":         "#68d391",
  "HOLD":        "#f6e05e",
  "SELL":        "#fc8181",
  "STRONG SELL": "#e53e3e",
};

function signalColor(signal) {
  return SIGNAL_COLORS[signal] || "#94a3b8";
}

function trendColor(prices) {
  if (!prices || prices.length < 2) return "#63b3ed";
  return prices[prices.length - 1] >= prices[0] ? "#48bb78" : "#fc8181";
}

// ── Mini sparkline (card charts) ──────────────────────────────────────────
function renderSparkline(canvasId, prices) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const color = trendColor(prices);

  new Chart(ctx, {
    type: "line",
    data: {
      labels: prices.map(() => ""),
      datasets: [{
        data: prices,
        borderColor: color,
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.4,
        fill: true,
        backgroundColor: color + "22",
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        x: { display: false },
        y: { display: false },
      },
      animation: { duration: 600 }
    }
  });
}

// ── Full price chart (detail page) ────────────────────────────────────────
function renderDetailChart(canvasId, prices, dates, signal) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const color = signalColor(signal);
  const gradient = ctx.getContext("2d").createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0, color + "40");
  gradient.addColorStop(1, color + "00");

  new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [{
        label: "Price (USD)",
        data: prices,
        borderColor: color,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 5,
        tension: 0.35,
        fill: true,
        backgroundColor: gradient,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0f1528ee",
          borderColor: "rgba(255,255,255,0.1)",
          borderWidth: 1,
          titleColor: "#94a3b8",
          bodyColor: "#e2e8f0",
          padding: 12,
          callbacks: {
            label: ctx => ` $${ctx.parsed.y.toFixed(2)}`
          }
        }
      },
      scales: {
        x: {
          ticks: { color: "#4a5568", maxTicksLimit: 8, font: { size: 11 } },
          grid: { color: "rgba(255,255,255,0.04)" }
        },
        y: {
          position: "right",
          ticks: { color: "#4a5568", font: { size: 11 }, callback: v => "$" + v.toFixed(0) },
          grid: { color: "rgba(255,255,255,0.04)" }
        }
      },
      animation: { duration: 900, easing: "easeInOutQuart" }
    }
  });
}

// ── Auto-init on DOMContentLoaded ─────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {

  // Sparklines on cards
  document.querySelectorAll("[data-sparkline]").forEach(el => {
    try {
      const prices = JSON.parse(el.dataset.sparkline);
      renderSparkline(el.id, prices);
    } catch (e) { /* ignore bad data */ }
  });

  // Full chart on detail page
  const fullChart = document.getElementById("fullChart");
  if (fullChart) {
    try {
      const prices = JSON.parse(fullChart.dataset.prices);
      const dates  = JSON.parse(fullChart.dataset.dates);
      const signal = fullChart.dataset.signal;
      renderDetailChart("fullChart", prices, dates, signal);
    } catch (e) { console.warn("Chart render error", e); }
  }

  // Animate score bars
  document.querySelectorAll(".score-bar-fill").forEach(bar => {
    const target = bar.dataset.score || 0;
    setTimeout(() => { bar.style.width = target + "%"; }, 100);
  });
});
