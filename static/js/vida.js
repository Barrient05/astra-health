(() => {
  "use strict";

  const quieto = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const principal = document.getElementById("contenido");
  if (quieto || !principal || !("IntersectionObserver" in window)) return;

  const objetivos = [];
  for (const n of principal.children) {
    if (n.tagName === "SCRIPT" || n.tagName === "NOSCRIPT") continue;
    if (n.classList.contains("tablero")) continue;
    objetivos.push(n);
  }
  for (const n of document.querySelectorAll(".tablero > .bloque")) objetivos.push(n);
  if (!objetivos.length) return;

  function soltar(n, retraso) {
    n.style.animationDelay = retraso + "ms";
    n.classList.remove("revelar");
    n.classList.add("revelado");
  }

  for (const n of objetivos) n.classList.add("revelar");

  const ojo = new IntersectionObserver((entradas) => {
    let i = 0;
    for (const e of entradas) {
      if (!e.isIntersecting) continue;
      ojo.unobserve(e.target);
      soltar(e.target, Math.min(i++, 6) * 70);
    }
  }, { rootMargin: "0px 0px -6% 0px", threshold: 0.02 });

  for (const n of objetivos) ojo.observe(n);

  setTimeout(() => {
    for (const n of objetivos) if (n.classList.contains("revelar")) soltar(n, 0);
  }, 2500);
})();
