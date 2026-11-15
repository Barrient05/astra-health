(() => {
  "use strict";

  const t = (texto, valores = {}) =>
    ((window.TEXTOS || {})[texto] ?? texto).replace(/\{(\w+)\}/g, (m, k) => (k in valores ? valores[k] : m));
  const $ = (s) => document.querySelector(s);
  const caja = $("#pulso-bt");
  if (!caja) return;

  const VENTANA_MS = 60_000;
  const MIN_LECTURAS = 10;
  const estado = { dispositivo: null, caracteristica: null, simulacion: null, lecturas: [], rr: [], nombre: "" };

  const ui = {
    conectar: $("#bt-conectar"), simular: $("#bt-simular"), desconectar: $("#bt-desconectar"),
    usar: $("#bt-usar"), lpm: $("#bt-lpm"), estado: $("#bt-estado"), detalle: $("#bt-detalle"),
    grafica: $("#bt-grafica"), promedio: $("#bt-promedio"),
  };

  function leerMedicion(dv) {
    const banderas = dv.getUint8(0);
    let i = 1;
    const lpm = banderas & 0x01 ? dv.getUint16(i, true) : dv.getUint8(i);
    i += banderas & 0x01 ? 2 : 1;
    const contactoSoportado = (banderas & 0x04) !== 0;
    const contacto = contactoSoportado ? (banderas & 0x02) !== 0 : null;
    if (banderas & 0x08) i += 2;
    const rr = [];
    if (banderas & 0x10) {
      for (; i + 1 < dv.byteLength; i += 2) rr.push((dv.getUint16(i, true) / 1024) * 1000);
    }
    return { lpm, contacto, rr };
  }
  window.leerMedicionPulso = leerMedicion;

  function recibir({ lpm, contacto, rr }) {
    const ahora = Date.now();
    if (contacto === false) {
      ui.estado.textContent = t("El sensor no detecta contacto con la piel: ajusta el reloj en la muñeca.");
      return;
    }
    if (!(lpm >= 25 && lpm <= 230)) return;
    estado.lecturas.push({ t: ahora, lpm });
    rr.forEach((x) => estado.rr.push({ t: ahora, rr: x }));
    estado.lecturas = estado.lecturas.filter((l) => ahora - l.t <= VENTANA_MS);
    estado.rr = estado.rr.filter((l) => ahora - l.t <= VENTANA_MS);
    pintar();
  }

  function rmssd() {
    const v = estado.rr.map((x) => x.rr);
    if (v.length < 10) return null;
    let s = 0;
    for (let k = 1; k < v.length; k++) s += (v[k] - v[k - 1]) ** 2;
    return Math.sqrt(s / (v.length - 1));
  }

  function promedio() {
    const v = estado.lecturas.map((l) => l.lpm);
    return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
  }

  function pintar() {
    const ult = estado.lecturas[estado.lecturas.length - 1];
    ui.lpm.textContent = ult ? ult.lpm : "–";
    const prom = promedio();
    const n = estado.lecturas.length;
    const hrv = rmssd();
    ui.promedio.textContent = prom ? t("Promedio del último minuto: {lpm} lpm ({n} lecturas).", { lpm: Math.round(prom), n })
      + (hrv ? " " + t("Variabilidad (RMSSD): {ms} ms", { ms: Math.round(hrv) }) : "") : "";
    ui.usar.disabled = n < MIN_LECTURAS;
    ui.usar.textContent = n < MIN_LECTURAS ? t("Reuniendo lecturas ({n} de {total})…", { n, total: MIN_LECTURAS })
      : t("Usar {lpm} lpm como pulso en reposo", { lpm: Math.round(prom) });
    caja.classList.toggle("pulso-latido", !!ult);

    const pts = estado.lecturas;
    if (pts.length > 1) {
      const ahora = Date.now();
      const t0 = Math.max(ahora - VENTANA_MS, pts[0].t);
      const tramo = Math.max(1, ahora - t0);
      const vals = pts.map((p) => p.lpm);
      const min = Math.min(...vals) - 3, max = Math.max(...vals) + 3;
      const d = pts.map((p) => `${(((p.t - t0) / tramo) * 300).toFixed(1)},${(60 - ((p.lpm - min) / (max - min)) * 56 - 2).toFixed(1)}`).join(" ");
      ui.grafica.innerHTML = `<polyline points="${d}" />`;
    }
  }

  function enUso(activo, texto) {
    ui.conectar.hidden = activo;
    ui.simular.hidden = activo;
    ui.desconectar.hidden = !activo;
    ui.estado.textContent = texto;
  }

  function reiniciarDatos() {
    estado.lecturas = []; estado.rr = [];
    ui.grafica.innerHTML = ""; ui.lpm.textContent = "–"; ui.promedio.textContent = "";
    ui.usar.disabled = true; ui.usar.textContent = t("Usar como pulso en reposo");
    caja.classList.remove("pulso-latido");
  }

  async function conectar() {
    if (!navigator.bluetooth) {
      ui.estado.textContent = t("Este navegador no permite Bluetooth. Abre la página en Chrome o Edge en la computadora, o prueba la simulación.");
      return;
    }
    reiniciarDatos();
    ui.estado.textContent = t("Elige tu reloj o banda en la ventana del navegador…");
    try {
      const dispositivo = await navigator.bluetooth.requestDevice({
        filters: [{ services: ["heart_rate"] }],
        optionalServices: ["battery_service"],
      });
      estado.dispositivo = dispositivo;
      estado.nombre = dispositivo.name || t("reloj Bluetooth");
      dispositivo.addEventListener("gattserverdisconnected", alDesconectar);
      ui.estado.textContent = t("Conectando con {nombre}…", { nombre: estado.nombre });
      const servidor = await dispositivo.gatt.connect();
      const servicio = await servidor.getPrimaryService("heart_rate");
      const car = await servicio.getCharacteristic("heart_rate_measurement");
      estado.caracteristica = car;
      car.addEventListener("characteristicvaluechanged", (e) => recibir(leerMedicion(e.target.value)));
      await car.startNotifications();
      enUso(true, t("Conectado a {nombre}. Quédate quieto un minuto para medir tu pulso en reposo.", { nombre: estado.nombre }));
      ui.detalle.textContent = "";
      try {
        const bat = await (await servidor.getPrimaryService("battery_service")).getCharacteristic("battery_level");
        ui.detalle.textContent = t("Batería del reloj: {pct} %", { pct: (await bat.readValue()).getUint8(0) });
      } catch {  }
    } catch (e) {
      const motivos = {
        NotFoundError: t("No elegiste ningún dispositivo, o ninguno cercano transmite el pulso. Activa en tu reloj la opción de transmitir la frecuencia cardiaca y vuelve a intentar."),
        SecurityError: t("El navegador bloqueó Bluetooth. Abre la página en http://localhost:5000 o con HTTPS."),
        NetworkError: t("Se perdió la conexión con el reloj. Acércalo a la computadora e intenta de nuevo."),
        NotSupportedError: t("Este dispositivo no ofrece el servicio estándar de frecuencia cardiaca."),
      };
      enUso(false, motivos[e.name] || t("No se pudo conectar: {error}", { error: e.message }));
    }
  }

  function alDesconectar() {
    if (estado.simulacion) return;
    enUso(false, t("Se desconectó {nombre}. Las lecturas del último minuto siguen disponibles.", { nombre: estado.nombre }));
  }

  async function desconectar() {
    if (estado.simulacion) {
      clearInterval(estado.simulacion);
      estado.simulacion = null;
      enUso(false, t("Simulación detenida."));
      return;
    }
    try { if (estado.caracteristica) await estado.caracteristica.stopNotifications(); } catch {  }
    if (estado.dispositivo && estado.dispositivo.gatt.connected) estado.dispositivo.gatt.disconnect();
    enUso(false, t("Reloj desconectado."));
  }

  function simular() {
    reiniciarDatos();
    const base = Number(caja.dataset.base) || 62;
    let fase = 0;
    estado.nombre = t("simulación");
    estado.simulacion = setInterval(() => {
      fase += 0.15;
      const lpm = Math.round(base + 3 * Math.sin(fase) + (Math.random() - 0.5) * 3);
      const rrBase = 60000 / lpm;
      recibir({ lpm, contacto: true, rr: [rrBase + (Math.random() - 0.5) * 60] });
    }, 1000);
    enUso(true, t("Simulación: así se verían los datos de un reloj real (una lectura por segundo)."));
    ui.detalle.textContent = "";
  }

  ui.usar.addEventListener("click", () => {
    const prom = promedio();
    if (!prom) return;
    const campo = $("#campo-fc");
    campo.value = Math.round(prom);
    campo.classList.add("llenado-dictado");
    campo.dispatchEvent(new Event("input", { bubbles: true }));
    const disp = $("#campo-dispositivo");
    if (disp) disp.value = estado.simulacion ? t("simulación de reloj") : estado.nombre;
    ui.estado.textContent = t("Listo: {lpm} lpm en tu pulso en reposo. Revisa y guarda el registro.", { lpm: Math.round(prom) });
  });

  ui.conectar.addEventListener("click", conectar);
  ui.simular.addEventListener("click", simular);
  ui.desconectar.addEventListener("click", desconectar);
  if (!navigator.bluetooth) {
    ui.estado.textContent = t("Este navegador no permite Bluetooth (usa Chrome o Edge en la computadora). Puedes probar la simulación.");
  }

  document.addEventListener("astronauta-cambiado", (e) => { caja.dataset.base = e.detail.fc_reposo || 62; });
})();
