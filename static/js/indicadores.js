(() => {
  "use strict";

  const t = (texto, valores = {}) =>
    ((window.TEXTOS || {})[texto] ?? texto).replace(/\{(\w+)\}/g, (m, k) => (k in valores ? valores[k] : m));
  const g = window.GRAFICA_INDICADOR;
  const linea = (valor, color, etiqueta, guiones) => ({
    label: etiqueta, data: g.dias.map(() => valor), borderColor: color, borderWidth: 1.5,
    borderDash: guiones, pointRadius: 0, fill: false,
  });

  const series = [
    { label: g.nombre, data: g.valores, borderColor: "#9EB8FF", borderWidth: 2.5, pointRadius: 0, tension: 0.2, spanGaps: true },
    linea(g.rango[0], "#7C84AD", t("Rango habitual"), [5, 5]),
    linea(g.rango[1], "#7C84AD", t("Rango habitual"), [5, 5]),
  ];
  if (g.base != null) series.push(linea(g.base, "#4FC48D", t("Tu línea base"), [2, 4]));

  Chart.defaults.color = "#7C84AD";
  Chart.defaults.font.family = '"Barlow SC", sans-serif';
  new Chart(document.getElementById("grafica-indicador"), {
    type: "line",
    data: { labels: g.dias, datasets: series },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      scales: { y: { grid: { color: "#343D72" } }, x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } } },
      plugins: {
        legend: { labels: { boxWidth: 18, boxHeight: 2, filter: (x) => x.datasetIndex !== 2 } },
        tooltip: { callbacks: { title: (i) => t("Día {dia}", { dia: i[0].label }) } },
      },
    },
  });
})();
