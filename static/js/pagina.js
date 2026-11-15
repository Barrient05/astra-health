(() => {
  "use strict";

  const t = (texto, valores = {}) =>
    ((window.TEXTOS || {})[texto] ?? texto).replace(/\{(\w+)\}/g, (m, k) => (k in valores ? valores[k] : m));
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);
  const g = window.GRAFICA;
  let diaVisto = window.DIA;
  let sistema = window.SISTEMA;

  const relleno = (n) => Array(n).fill(null);

  function datosGrafica(d) {
    const ultimo = d.historial[d.historial.length - 1];
    const series = [
      { label: t("Historial"), data: [...d.historial, ...relleno(d.futuro.length)], borderColor: "#ECEEF7", borderWidth: 2, pointRadius: 0, tension: 0.25 },
      { label: t("Pronóstico sin plan"), data: [...relleno(d.dias.length - 1), ultimo, ...d.sin_plan], borderColor: "#A9B0D3", borderDash: [6, 5], borderWidth: 2, pointRadius: 0 },
    ];
    if (d.hay_planes) {
      series.push({ label: t("Con tus planes"), data: [...relleno(d.dias.length - 1), ultimo, ...d.con_plan], borderColor: "#4FC48D", borderWidth: 2.5, pointRadius: 0 });
    }
    return { labels: [...d.dias, ...d.futuro], datasets: series };
  }

  Chart.defaults.color = "#7C84AD";
  Chart.defaults.font.family = '"Barlow SC", sans-serif';
  const grafica = new Chart($("#grafica"), {
    type: "line",
    data: datosGrafica(g),
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        y: { min: 0, max: 100, grid: { color: "#343D72" } },
        x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } },
      },
      plugins: { legend: { labels: { boxWidth: 18, boxHeight: 2 } }, tooltip: { callbacks: { title: (i) => t("Día {dia}", { dia: i[0].label }) } } },
    },
  });

  const irA = (clave) => verDia(diaVisto, clave).catch(() => {});

  const resaltar = (clave, activo) =>
    $$(`[data-sistema="${clave}"]`).forEach((n) => n.classList.toggle("resaltada", activo));

  $$("[data-chip]").forEach((boton) => {
    boton.addEventListener("click", () => irA(boton.dataset.chip));
    boton.addEventListener("mouseenter", () => resaltar(boton.dataset.chip, true));
    boton.addEventListener("mouseleave", () => resaltar(boton.dataset.chip, false));
  });

  $$("[data-sistema]").forEach((n) => {
    n.addEventListener("mouseenter", () => resaltar(n.dataset.sistema, true));
    n.addEventListener("mouseleave", () => resaltar(n.dataset.sistema, false));
    n.addEventListener("focus", () => resaltar(n.dataset.sistema, true));
    n.addEventListener("blur", () => resaltar(n.dataset.sistema, false));

    n.addEventListener("click", (e) => { e.preventDefault(); irA(n.dataset.sistema); });
    n.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); irA(n.dataset.sistema); } });
  });

  const zonas = new Map([...$$(".zona")].map((z) => [z.dataset.sistema, z]));
  const NIVELES = ["nivel-normal", "nivel-vigilar", "nivel-atencion", "nivel-critico"];

  function pintarDia(d) {
    diaVisto = d.dia;
    sistema = d.elegido;
    $("#mision-dia").textContent = d.titulo_dia;

    for (const [clave, z] of zonas) {
      const info = d.zonas[clave];
      if (!info) continue;
      z.setAttribute("style", info.estilo);
      z.classList.remove(...NIVELES);
      z.classList.add("nivel-" + info.nivel);
    }
    const capa = $("#mapa-etiquetas");
    if (capa) {
      capa.replaceChildren();
      const ns = "http://www.w3.org/2000/svg";
      const svg = (tag, atributos, texto) => {
        const n = document.createElementNS(ns, tag);
        for (const [k, v] of Object.entries(atributos)) n.setAttribute(k, v);
        if (texto !== undefined) n.textContent = texto;
        return n;
      };
      for (const e of d.etiquetas) {
        const grupo = svg("g", { class: "etiqueta", "data-sistema": e.clave });
        grupo.append(
          svg("polyline", { class: "etiqueta-linea", points: `${e.ancla[0]},${e.ancla[1]} ${e.fin_linea[0]},${e.fin_linea[1]}`, stroke: e.color }),
          svg("circle", { class: "etiqueta-punto", cx: e.ancla[0], cy: e.ancla[1], r: 3.2, fill: e.color }),
          svg("text", { class: "etiqueta-valor", x: e.texto[0], y: e.texto[1], "text-anchor": e.lado, fill: e.color }, e.puntaje),
          svg("text", { class: "etiqueta-nombre", x: e.texto[0], y: e.texto[1] + 15, "text-anchor": e.lado }, e.corto),
        );
        grupo.addEventListener("click", () => irA(e.clave));
        grupo.addEventListener("mouseenter", () => resaltar(e.clave, true));
        grupo.addEventListener("mouseleave", () => resaltar(e.clave, false));
        capa.append(grupo);
      }
    }

    $("#anillo-avance").setAttribute("stroke-dasharray", `${d.anillo.avance} ${d.anillo.total}`);
    $("#anillo-hoy").setAttribute("cx", d.anillo.hoy[0]);
    $("#anillo-hoy").setAttribute("cy", d.anillo.hoy[1]);

    $$("[data-signo]").forEach((caja, i) => {
      const s = d.signos[i];
      if (!s) return;
      caja.className = `signo signo-${s.nivel}`;
      caja.querySelector(".signo-valor b").textContent = s.valor;
      caja.querySelector(".signo-sub").textContent = s.referencia;
    });

    const numero = $("#estado-numero");
    numero.textContent = d.general;
    numero.style.color = d.nivel_general.color;
    $("#estado-texto").textContent = t("Estado general: {nivel}", { nivel: d.nivel_general.nombre.toLowerCase() });
    $$(".lista-sistemas .sistema").forEach((fila) => {
      const s = d.sistemas.find((x) => x.clave === fila.dataset.sistema);
      if (!s) return;
      fila.querySelector(".sistema-barra i").style.width = `${s.puntaje}%`;
      fila.querySelector(".sistema-barra i").style.setProperty("--color", s.nivel.color);
      const p = fila.querySelector(".sistema-puntaje");
      p.textContent = s.puntaje; p.style.color = s.nivel.color;
    });

    $("#dosis-numero").textContent = d.radiacion.acumulada;
    $("#dosis-barra").style.width = Math.min(100, d.radiacion.porcentaje) + "%";

    $("#t-pronostico").textContent = d.titulo_tendencia;
    $("#pronostico-resumen").textContent = d.resumen;
    const caja = $("#pronostico-riesgos");
    caja.hidden = !d.riesgos.length;
    caja.querySelector("span").replaceChildren(...d.riesgos.flatMap((r, i) => {
      const a = document.createElement("a");
      a.href = r.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = r.nombre;
      return i ? [document.createTextNode("; "), a] : [a];
    }));
    $$("[data-chip]").forEach((c) => {
      c.setAttribute("aria-pressed", String(c.dataset.chip === d.elegido));
      const s = d.sistemas.find((x) => x.clave === c.dataset.chip);
      if (s) c.querySelector(".punto").className = `punto ${s.nivel.clave}`;
    });
    $$(".lista-sistemas .sistema").forEach((fila) => {
      fila.toggleAttribute("aria-current", fila.dataset.sistema === d.elegido);
      if (fila.dataset.sistema === d.elegido) fila.setAttribute("aria-current", "true");
    });

    const url = new URL(location.href);
    url.searchParams.set("astronauta", window.ASTRONAUTA);
    url.searchParams.set("sistema", d.elegido);
    url.searchParams.set("dia", d.dia);
    history.replaceState(null, "", url);
    grafica.data = datosGrafica(d.grafica);
    grafica.update("none");
  }

  let pidiendo = null;
  async function verDia(dia, nuevoSistema = sistema) {
    if (pidiendo) pidiendo.abort();
    pidiendo = new AbortController();
    const r = await fetch(`/api/dia/${dia}?sistema=${nuevoSistema}`, { signal: pidiendo.signal });
    pidiendo = null;
    pintarDia(await r.json());
  }

  const slider = $("#slider-dia");
  let espera = null;
  slider.addEventListener("input", (e) => {
    const dia = Number(e.target.value);
    $("#mision-dia").textContent = t("Día {dia} de {total}", { dia, total: window.DIAS_TOTALES });
    clearTimeout(espera);
    espera = setTimeout(() => verDia(dia).catch(() => {}), 90);
  });

  const btn = $("#btn-reproducir");
  let reproduciendo = false;
  btn.addEventListener("click", async () => {
    if (reproduciendo) { reproduciendo = false; return; }
    reproduciendo = true;
    btn.textContent = btn.dataset.pausar;
    btn.classList.add("reproduciendo");
    const fin = Number(slider.max);
    for (let dia = 1; dia <= fin && reproduciendo; dia = Math.min(fin, dia + 2)) {
      const t0 = performance.now();
      slider.value = dia;
      try { await verDia(dia); } catch {  }
      if (dia === fin) break;
      await new Promise((r) => setTimeout(r, Math.max(0, 130 - (performance.now() - t0))));
    }
    reproduciendo = false;
    btn.textContent = btn.dataset.reproducir;
    btn.classList.remove("reproduciendo");
  });
})();
