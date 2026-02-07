/**
 * Chart.js helpers for tokentap dashboard.
 */
let usageChart = null;

function createUsageChart(canvasId, data) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  if (usageChart) {
    usageChart.destroy();
  }

  const labels = data.map(d => formatBucket(d.bucket));
  const inputData = data.map(d => d.input_tokens);
  const outputData = data.map(d => d.output_tokens);

  usageChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Input Tokens',
          data: inputData,
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99, 102, 241, 0.1)',
          fill: true,
          tension: 0.3,
        },
        {
          label: 'Output Tokens',
          data: outputData,
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          fill: true,
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { position: 'top', labels: { color: '#94a3b8' } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${ctx.raw.toLocaleString()} tokens`,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: '#94a3b8', maxTicksLimit: 12 },
          grid: { color: 'rgba(148, 163, 184, 0.1)' },
        },
        y: {
          ticks: {
            color: '#94a3b8',
            callback: (v) => v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v,
          },
          grid: { color: 'rgba(148, 163, 184, 0.1)' },
        },
      },
    },
  });
}

function formatBucket(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const month = (d.getMonth() + 1).toString().padStart(2, '0');
  const day = d.getDate().toString().padStart(2, '0');
  const hour = d.getHours().toString().padStart(2, '0');
  return `${month}/${day} ${hour}:00`;
}
