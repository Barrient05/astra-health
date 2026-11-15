(() => {
  "use strict";

  const t = (texto, valores = {}) =>
    ((window.TEXTOS || {})[texto] ?? texto).replace(/\{(\w+)\}/g, (m, k) => (k in valores ? valores[k] : m));
  const $ = (s) => document.querySelector(s);
  const form = document.querySelector(".formulario-registro");

  const LAPSO_MS = 355, SIN_RESPUESTA_MS = 3000;
  const pvt = { activo: false, fin: 0, inicio: 0, espera: null, raf: null, tiempos: [], errores: 0, mostrando: false };
  const area = $("#pvt-area"), numero = $("#pvt-numero"), estado = $("#pvt-estado"), boton = $("#btn-pvt");

  function siguiente() {
    clearTimeout(pvt.espera);
    pvt.mostrando = false;
    numero.textContent = "";
    if (performance.now() >= pvt.fin) { terminar(); return; }
    estado.textContent = t("Espera el contador…");
    pvt.espera = setTimeout(() => {
      pvt.mostrando = true;
      pvt.inicio = performance.now();
      estado.textContent = "";
      area.classList.add("pvt-estimulo");
      const contar = () => {
        if (!pvt.mostrando) return;
        const ms = performance.now() - pvt.inicio;
        numero.textContent = Math.round(ms);
        if (ms >= SIN_RESPUESTA_MS) { responder(SIN_RESPUESTA_MS); return; }
        pvt.raf = requestAnimationFrame(contar);
      };
      pvt.raf = requestAnimationFrame(contar);
    }, 1000 + Math.random() * 3000);
  }

  function responder(ms) {
    pvt.mostrando = false;
    cancelAnimationFrame(pvt.raf);
    area.classList.remove("pvt-estimulo");
    if (ms < 100) { pvt.errores += 1; estado.textContent = t("Demasiado pronto."); }
    else {
      pvt.tiempos.push(ms);
      numero.textContent = Math.round(ms);
      estado.textContent = ms >= LAPSO_MS ? t("Lento: cuenta como lapso.") : t("Bien.");
    }
    pvt.espera = setTimeout(siguiente, 700);
  }

  function pulsar(e) {
    if (!pvt.activo) return;
    e.preventDefault();
    if (pvt.mostrando) { responder(performance.now() - pvt.inicio); return; }
    pvt.errores += 1;
    estado.textContent = t("Te adelantaste. Espera el contador.");
    siguiente();
  }

  function terminar() {
    pvt.activo = false;
    clearTimeout(pvt.espera);
    cancelAnimationFrame(pvt.raf);
    area.classList.remove("pvt-activa", "pvt-estimulo");
    boton.textContent = t("Repetir prueba");
    if (!pvt.tiempos.length) { estado.textContent = t("No hubo respuestas. Intenta de nuevo."); numero.textContent = ""; return; }
    const prom = Math.round(pvt.tiempos.reduce((a, b) => a + b, 0) / pvt.tiempos.length);
    const lapsos = pvt.tiempos.filter((x) => x >= LAPSO_MS).length;
    $("#campo-reaccion").value = prom;
    $("#campo-lapsos").value = lapsos;
    numero.textContent = `${prom} ms`;
    estado.textContent = t("{n} respuestas, {lapsos} lapsos y {errores} errores. Se guardará con tu registro.",
      { n: pvt.tiempos.length, lapsos, errores: pvt.errores });
  }

  boton.addEventListener("click", () => {
    if (pvt.activo) { pvt.fin = 0; terminar(); return; }
    Object.assign(pvt, { activo: true, tiempos: [], errores: 0, fin: performance.now() + 1000 * Number($("#pvt-duracion").value) });
    boton.textContent = t("Terminar antes");
    area.classList.add("pvt-activa");
    area.focus();
    siguiente();
  });
  area.addEventListener("pointerdown", pulsar);
  document.addEventListener("keydown", (e) => { if (pvt.activo && (e.code === "Space" || e.key === " ")) pulsar(e); });

  const texto = $("#dictado"), aviso = $("#dictado-estado"), btnDictar = $("#btn-dictar");
  const Reconocimiento = window.SpeechRecognition || window.webkitSpeechRecognition;
  const IDIOMA_VOZ = { es: "es-MX", en: "en-US", pt: "pt-BR", fr: "fr-FR" };
  let reconocedor = null, escuchando = false;

  if (!Reconocimiento) {
    btnDictar.hidden = true;
    aviso.textContent = t("Este navegador no permite dictar: escribe el texto.");
  } else {
    reconocedor = new Reconocimiento();
    reconocedor.lang = IDIOMA_VOZ[document.documentElement.lang] || "es-MX";
    reconocedor.continuous = true;
    reconocedor.interimResults = true;
    let base = "";
    reconocedor.onstart = () => { base = texto.value ? texto.value.trimEnd() + " " : ""; };
    reconocedor.onresult = (e) => {
      let final = "", parcial = "";
      for (const r of e.results) (r.isFinal ? (x) => (final += x) : (x) => (parcial += x))(r[0].transcript);
      texto.value = base + final + parcial;
    };
    reconocedor.onerror = (e) => {
      aviso.textContent = e.error === "not-allowed" ? t("Permite el uso del micrófono para dictar.")
        : e.error === "network" ? t("El dictado por voz necesita internet. Escribe el texto: el resto funciona sin conexión.")
        : t("No se pudo escuchar. Intenta de nuevo o escribe el texto.");
    };
    reconocedor.onend = () => {
      escuchando = false;
      btnDictar.textContent = t("Dictar");
      btnDictar.setAttribute("aria-pressed", "false");
    };
    btnDictar.addEventListener("click", () => {
      if (escuchando) { reconocedor.stop(); return; }
      aviso.textContent = t("Escuchando… habla con naturalidad. Pulsa Detener al terminar.");
      escuchando = true;
      btnDictar.textContent = t("Detener");
      btnDictar.setAttribute("aria-pressed", "true");
      reconocedor.start();
    });
  }

  $("#btn-interpretar").addEventListener("click", async () => {
    const dicho = texto.value.trim();
    const caja = $("#dictado-resultado");
    if (!dicho) { aviso.textContent = t("Primero dicta o escribe cómo te sientes."); texto.focus(); return; }
    if (escuchando) reconocedor.stop();
    const r = await fetch("/dictado", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ texto: dicho }) });
    const d = await r.json();
    form.querySelectorAll(".llenado-dictado").forEach((n) => n.classList.remove("llenado-dictado"));
    for (const [campo, valor] of Object.entries(d.valores)) {
      const input = $(`#campo-${campo}`);
      if (input) { input.value = valor; input.classList.add("llenado-dictado"); }
    }
    form.querySelectorAll("input[name=sintomas]").forEach((cb) => {
      if (d.sintomas.includes(cb.value)) { cb.checked = true; cb.parentElement.classList.add("llenado-dictado"); }
      if (d.descartados.includes(cb.value)) cb.checked = false;
    });
    if (d.eco) { form.eco.value = d.eco; form.eco.classList.add("llenado-dictado"); }
    if (!form.nota.value.trim()) form.nota.value = dicho.slice(0, 500);

    const nombre = (clave) => (window.SINTOMAS || {})[clave] || clave;
    const bloques = [];
    const agregar = (titulo, items) => {
      if (!items.length) return;
      const p = document.createElement("p");
      p.append(Object.assign(document.createElement("strong"), { textContent: titulo + ": " }), items.join("; ") + ".");
      bloques.push(p);
    };
    agregar(t("Mediciones"), d.reconocido);
    agregar(t("Síntomas marcados"), d.sintomas.map(nombre));
    agregar(t("Descartaste"), d.descartados.map(nombre));
    agregar(t("No reconocí"), d.sin_reconocer.map((f) => `«${f}»`));
    const n = d.reconocido.length + d.sintomas.length + (d.eco ? 1 : 0);
    aviso.textContent = n ? t("Llené {n} datos. Revisa los campos resaltados y guarda.", { n })
      : t("No encontré mediciones ni síntomas. Prueba con frases como «pulso 70» o «me duele la cabeza».");
    caja.replaceChildren(...bloques);
    caja.hidden = !bloques.length;
  });

  let reloj = null;
  $("#btn-pulso").addEventListener("click", (e) => {
    const cuenta = $("#cuenta-pulso");
    clearInterval(reloj);
    let restante = 15;
    cuenta.textContent = restante;
    e.currentTarget.textContent = t("Reiniciar");
    $("#campo-latidos").hidden = true;
    $("#btn-usar-pulso").hidden = true;
    reloj = setInterval(() => {
      cuenta.textContent = --restante;
      if (restante <= 0) {
        clearInterval(reloj);
        cuenta.textContent = t("Listo");
        $("#campo-latidos").hidden = false;
        $("#btn-usar-pulso").hidden = false;
        $("#latidos").focus();
      }
    }, 1000);
  });
  $("#btn-usar-pulso").addEventListener("click", () => {
    const n = Number($("#latidos").value);
    if (!Number.isFinite(n) || n < 5 || n > 60) { $("#cuenta-pulso").textContent = t("Escribe cuántos latidos contaste."); return; }
    $("#campo-fc").value = Math.round(n * 4);
    $("#campo-fc").classList.add("llenado-dictado");
    $("#cuenta-pulso").textContent = `${Math.round(n * 4)} ${t("lpm")}`;
  });
})();
