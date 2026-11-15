(() => {
  "use strict";

  const t = (texto, valores = {}) =>
    ((window.TEXTOS || {})[texto] ?? texto).replace(/\{(\w+)\}/g, (m, k) => (k in valores ? valores[k] : m));
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);
  const g = window.GRAFICA;
  let diaVisto = window.DIA;
  let sistema = window.SISTEMA;
  const diaMax = window.DIA_MAX || window.DIA;
  const quieto = matchMedia("(prefers-reduced-motion: reduce)").matches;

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
      responsive: true, maintainAspectRatio: false,
      animation: quieto ? false : { duration: 700, easing: "easeOutQuart" },
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

    moverMarca(d.dia);
    $("#anillo-avance").setAttribute("stroke-dasharray", `${d.anillo.avance} ${d.anillo.total}`);
    $("#anillo-hoy").setAttribute("cx", d.anillo.hoy[0]);
    $("#anillo-hoy").setAttribute("cy", d.anillo.hoy[1]);

    $$("[data-signo]").forEach((caja, i) => {
      const s = d.signos[i];
      if (!s) return;
      caja.className = `signo signo-${s.nivel}` + (s.medido ? " signo-medido" : "") + (i === 0 ? " signo-pulso" : "");
      caja.querySelector(".signo-valor b").textContent = s.valor;
      caja.querySelector(".signo-sub").textContent = s.medido || s.referencia;
      if (i === 0) latir(s.valor);
    });

    const numero = $("#estado-numero");
    if (!quieto && numero.textContent.trim() !== String(d.general)) {
      numero.classList.remove("numero-cambia");
      void numero.offsetWidth;
      numero.classList.add("numero-cambia");
    }
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

  const linea = $("#linea-mision");
  const marca = linea && linea.querySelector(".hoy");

  function moverMarca(dia) {
    if (!linea) return;
    if (marca) marca.style.left = (100 * (dia - 1)) / window.DIAS_TOTALES + "%";
    linea.setAttribute("aria-valuenow", dia);
    linea.setAttribute("aria-valuetext", t("Día {dia} de {total}", { dia, total: window.DIAS_TOTALES }));
  }

  const acotar = (dia) => Math.min(diaMax, Math.max(1, dia));
  let espera = null;
  let diaObjetivo = diaVisto;

  function pedirDia(dia, demora = 0) {
    dia = acotar(dia);
    diaObjetivo = dia;
    moverMarca(dia);
    $("#mision-dia").textContent = t("Día {dia} de {total}", { dia, total: window.DIAS_TOTALES });
    clearTimeout(espera);
    espera = setTimeout(() => verDia(dia).catch(() => {}), demora);
  }

  if (linea && diaMax > 1) {
    linea.addEventListener("click", (e) => {
      const caja = linea.getBoundingClientRect();
      const parte = (e.clientX - caja.left) / caja.width;
      pedirDia(Math.round(parte * window.DIAS_TOTALES) + 1, 60);
    });
    linea.addEventListener("keydown", (e) => {
      const saltos = { ArrowLeft: -1, ArrowRight: 1, ArrowDown: -1, ArrowUp: 1, PageDown: -7, PageUp: 7 };
      if (e.key in saltos) { e.preventDefault(); pedirDia(diaObjetivo + saltos[e.key], 120); }
      else if (e.key === "Home") { e.preventDefault(); pedirDia(1, 0); }
      else if (e.key === "End") { e.preventDefault(); pedirDia(diaMax, 0); }
    });
  }

  const btn = $("#btn-reproducir");
  let reproduciendo = false;
  btn.addEventListener("click", async () => {
    if (reproduciendo) { reproduciendo = false; return; }
    reproduciendo = true;
    btn.textContent = btn.dataset.pausar;
    btn.classList.add("reproduciendo");
    document.body.classList.add("reproduciendo");
    const salto = Math.max(1, Math.round(diaMax / 55));
    for (let dia = 1; dia <= diaMax && reproduciendo; dia = Math.min(diaMax, dia + salto)) {
      const t0 = performance.now();
      moverMarca(dia);
      try { await verDia(dia); } catch { }
      if (dia === diaMax) break;
      await new Promise((r) => setTimeout(r, Math.max(0, 120 - (performance.now() - t0))));
    }
    reproduciendo = false;
    btn.textContent = btn.dataset.reproducir;
    btn.classList.remove("reproduciendo");
    document.body.classList.remove("reproduciendo");
  });

  function latir(bpm) {
    const caja = $(".signo-pulso");
    if (!caja) return;
    const n = parseFloat(String(bpm).replace(/[^\d.]/g, ""));
    if (!n || n < 30 || n > 220) return;
    caja.dataset.bpm = n;
    caja.style.setProperty("--latido", (60 / n).toFixed(3) + "s");
  }

  function contar(nodo, hasta) {
    const n = parseFloat(String(hasta).replace(/[^\d.-]/g, ""));
    if (quieto || !isFinite(n)) { nodo.textContent = hasta; return; }
    const entero = !String(hasta).includes(".");
    const t0 = performance.now(), dura = 850;
    const paso = (ahora) => {
      const p = Math.min(1, (ahora - t0) / dura);
      const suave = 1 - Math.pow(1 - p, 3);
      nodo.textContent = entero ? Math.round(n * suave) : (n * suave).toFixed(1);
      if (p < 1) requestAnimationFrame(paso); else nodo.textContent = hasta;
    };
    requestAnimationFrame(paso);
  }

  latir($(".signo-pulso") && $(".signo-pulso").dataset.bpm);

  if (!quieto) {
    document.body.classList.add("animar");
    contar($("#estado-numero"), $("#estado-numero").textContent.trim());
    contar($("#dosis-numero"), $("#dosis-numero").textContent.trim());
    setTimeout(() => document.body.classList.remove("animar"), 2200);
  }
})();
