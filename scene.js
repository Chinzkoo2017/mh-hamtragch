/* Product scenes: background-free product photo on a studio backdrop, with physically
   simulated capsules / softgels / powder / bubbles drawn on a canvas in front of it. */
(function () {
  "use strict";
  const REDUCE = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const DPR = Math.min(2, window.devicePixelRatio || 1);

  /* ---------- colour helpers ---------- */
  function hex(c) { c = c.replace("#", ""); return [0, 2, 4].map(i => parseInt(c.substr(i, 2), 16)); }
  function mix(c, t) { // t<0 darken, t>0 lighten
    const [r, g, b] = hex(c);
    const f = v => Math.round(t < 0 ? v * (1 + t) : v + (255 - v) * t);
    return `rgb(${f(r)},${f(g)},${f(b)})`;
  }
  function rgba(c, a) { const [r, g, b] = hex(c); return `rgba(${r},${g},${b},${a})`; }
  const rnd = (a, b) => a + Math.random() * (b - a);

  /* ---------- palettes ---------- */
  const CAPS = {
    green: { c1: "#2b4d29", c2: "#3a6534" },
    white: { c1: "#efeeea", c2: "#fafaf8" },
    beige: { c1: "#c8ad84", c2: "#d6c19d", speck: "#9c8461" },
    pearl: { c1: "#eceef1", c2: "#f7f8fa" },
    gel: { gel: "#e9b23a" }
  };

  /* ---------- items ---------- */
  function Capsule(s, style, z) {
    const sc = 0.72 + 0.5 * z;
    this.z = z; this.style = style;
    this.gel = !!style.gel;
    const ref = Math.min(s.H, s.W * 0.8);
    this.L = ref * (this.gel ? 0.085 : 0.12) * sc;
    this.R = this.gel ? this.L * 0.3 : this.L * 0.19;
    this.floor = s.floorY + s.H * 0.13 * z;
    const side = Math.random() < 0.5 ? -1 : 1;
    const band = s.W * rnd(0.05, 0.28);
    this.x = side < 0 ? band : s.W - band;
    if (z > 0.75 && Math.random() < 0.5) this.x = s.W * rnd(0.32, 0.68); // a few land in front of the product
    this.y = -rnd(0.05, 0.5) * s.H;
    this.vx = rnd(-0.08, 0.08) * s.W - side * rnd(0.02, 0.12) * s.W * (Math.random() < 0.6 ? 1 : -0.3);
    this.vy = rnd(0, 0.25) * s.H;
    this.a = rnd(0, Math.PI * 2);
    this.va = rnd(-9, 9);
    this.roll = rnd(0, 6);
    this.rest = rnd(-0.22, 0.22);
    this.delay = rnd(0, 1.1);
    this.done = false;
    this.speck = style.speck ? Array.from({ length: 14 }, () => [rnd(-0.45, 0.45), rnd(-0.8, 0.8), rnd(0.4, 1)]) : null;
  }
  Capsule.prototype.step = function (s, dt) {
    if (this.delay > 0) { this.delay -= dt; return; }
    if (this.done) return;
    const g = s.H * 3.4;
    this.vy += g * dt;
    this.x += this.vx * dt; this.y += this.vy * dt; this.a += this.va * dt;
    const half = this.gel ? this.L * 0.38 : this.L / 2 - this.R;
    const low = this.y + Math.abs(Math.sin(this.a)) * half + (this.gel ? this.R * 0.9 : this.R);
    if (low >= this.floor) {
      this.y -= low - this.floor;
      if (this.vy > 0) {
        this.vy = -this.vy * (this.gel ? 0.42 : 0.3);
        if (Math.abs(this.vy) < s.H * 0.06) this.vy = 0;
        // impact torque tips the capsule toward lying flat
        this.va = this.va * 0.45 - Math.sin(2 * this.a) * (this.gel ? 4 : 7);
      }
      this.vx *= this.gel ? 0.985 : 0.955;
      if (this.vy === 0) {
        const flat = Math.round((this.a - this.rest) / Math.PI) * Math.PI + this.rest;
        this.a += (flat - this.a) * (this.gel ? 0.08 : 0.18);
        this.va *= 0.82;
      }
      this.roll += this.vx * dt / Math.max(2, this.R);
      if (this.gel) this.a += this.vx * dt / (this.R * 1.4) * 0.15;
      if (Math.abs(this.vx) < s.W * 0.004 && this.vy === 0 && Math.abs(this.va) < 0.05) this.done = true;
    }
    const m = this.L * 0.6;
    if (this.x < m) { this.x = m; this.vx = Math.abs(this.vx) * 0.4; }
    if (this.x > s.W - m) { this.x = s.W - m; this.vx = -Math.abs(this.vx) * 0.4; }
  };
  Capsule.prototype.shadow = function (s, c) {
    if (this.delay > 0) return;
    const h = Math.max(0, this.floor - this.y);
    const k = Math.max(0, 1 - h / (s.H * 0.55));
    if (k <= 0) return;
    const w = this.L * (0.55 + 0.35 * Math.abs(Math.cos(this.a))) * (1.3 - 0.3 * k);
    const g = c.createRadialGradient(this.x, this.floor, 0, this.x, this.floor, w);
    g.addColorStop(0, `rgba(0,0,0,${0.32 * k})`); g.addColorStop(1, "rgba(0,0,0,0)");
    c.save(); c.translate(this.x, this.floor); c.scale(1, 0.22); c.translate(-this.x, -this.floor);
    c.fillStyle = g; c.beginPath(); c.arc(this.x, this.floor, w, 0, 7); c.fill(); c.restore();
    if (this.gel) { // warm caustic light through the gel
      const cg = c.createRadialGradient(this.x + this.L * 0.15, this.floor, 0, this.x + this.L * 0.15, this.floor, this.L * 0.5);
      cg.addColorStop(0, `rgba(255,200,80,${0.35 * k})`); cg.addColorStop(1, "rgba(255,200,80,0)");
      c.save(); c.translate(0, this.floor); c.scale(1, 0.3); c.translate(0, -this.floor);
      c.fillStyle = cg; c.beginPath(); c.arc(this.x + this.L * 0.15, this.floor, this.L * 0.5, 0, 7); c.fill(); c.restore();
    }
  };
  function rr(c, x, y, w, h, r) { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }
  Capsule.prototype.draw = function (c) {
    if (this.delay > 0) return;
    c.save(); c.translate(this.x, this.y); c.rotate(this.a);
    const L = this.L, R = this.R;
    if (this.gel) {
      const col = this.style.gel, rx = L * 0.42, ry = R;
      const g = c.createRadialGradient(-rx * 0.25, -ry * 0.35, ry * 0.1, 0, 0, rx);
      g.addColorStop(0, "rgba(255,246,200,0.95)"); g.addColorStop(0.35, rgba(col, 0.82));
      const [r0, g0, b0] = hex(col);
      g.addColorStop(0.85, `rgba(${Math.round(r0 * 0.7)},${Math.round(g0 * 0.55)},${Math.round(b0 * 0.3)},0.92)`);
      c.fillStyle = g; c.beginPath(); c.ellipse(0, 0, rx, ry, 0, 0, 7); c.fill();
      c.fillStyle = rgba(col, 0.35); c.beginPath(); c.ellipse(0, ry * 0.15, rx * 0.95, ry * 0.85, 0, 0, 7); c.fill();
      c.strokeStyle = "rgba(160,90,10,0.45)"; c.lineWidth = Math.max(0.6, ry * 0.08); c.beginPath(); c.ellipse(0, 0, rx, ry, 0, 0, 7); c.stroke();
      c.fillStyle = "rgba(255,255,255,0.85)"; c.beginPath(); c.ellipse(-rx * 0.35, -ry * 0.45, rx * 0.28, ry * 0.18, -0.2, 0, 7); c.fill();
      c.fillStyle = "rgba(255,255,255,0.35)"; c.beginPath(); c.ellipse(rx * 0.35, ry * 0.4, rx * 0.12, ry * 0.08, 0, 0, 7); c.fill();
      c.restore(); return;
    }
    const sh = Math.sin(this.roll) * 0.12;
    const grad = col => {
      const g = c.createLinearGradient(0, -R, 0, R);
      g.addColorStop(0, mix(col, -0.18)); g.addColorStop(Math.max(0.05, 0.22 + sh), mix(col, 0.55));
      g.addColorStop(Math.min(0.9, 0.48 + sh), col); g.addColorStop(1, mix(col, -0.42));
      return g;
    };
    // body (right) then cap (left, slightly wider, overlapping)
    c.fillStyle = grad(this.style.c2); rr(c, -L * 0.08, -R * 0.94, L * 0.58, R * 1.88, R * 0.94); c.fill();
    c.fillStyle = grad(this.style.c1); rr(c, -L / 2, -R, L * 0.56, R * 2, R); c.fill();
    c.strokeStyle = "rgba(0,0,0,0.12)"; c.lineWidth = Math.max(0.5, R * 0.06);
    c.beginPath(); c.moveTo(L * 0.06, -R * 0.96); c.lineTo(L * 0.06, R * 0.96); c.stroke();
    if (this.speck) { c.fillStyle = rgba(this.style.speck, 0.55); for (const [sx, sy, sr] of this.speck) { c.beginPath(); c.arc(sx * L, sy * R, sr * R * 0.09, 0, 7); c.fill(); } }
    c.globalAlpha = 0.55 + sh; c.fillStyle = "#fff"; rr(c, -L * 0.38, -R * (0.62 - sh), L * 0.72, R * 0.22, R * 0.11); c.fill();
    c.restore();
  };

  /* powder grain for collagen */
  function Grain(s, burst) {
    this.x = s.W * rnd(0.12, 0.3) + (burst ? rnd(-10, 10) : 0); this.y = -rnd(0, s.H * 0.15);
    this.vx = rnd(-0.05, 0.12) * s.W; this.vy = rnd(0.1, 0.4) * s.H;
    this.r = rnd(0.6, 2.2) * (Math.min(s.H, s.W * 0.8) / 300); this.a = rnd(0.55, 0.95);
    this.delay = rnd(0, 1.8); this.landed = false;
  }
  function Bubble(s) {
    this.reset(s, true);
  }
  Bubble.prototype.reset = function (s, first) {
    this.x = s.W * rnd(0.05, 0.95); this.y = first ? s.H * rnd(0.3, 1.1) : s.H + rnd(5, 40);
    this.r = rnd(2, 9) * (Math.min(s.H, s.W * 0.8) / 300); this.v = rnd(0.08, 0.2) * s.H; this.ph = rnd(0, 6); this.w = rnd(0.6, 1.6);
  };

  /* ---------- scene ---------- */
  function Scene(host, cfg) {
    this.host = host; this.cfg = cfg; this.items = []; this.grains = []; this.heap = null; this.bubbles = [];
    this.puffs = []; this.glints = [];
    host.classList.add("scene");
    host.style.setProperty("--w1", cfg.wall[0]); host.style.setProperty("--w2", cfg.wall[1]); host.style.setProperty("--fl", cfg.floor);
    host.insertAdjacentHTML("beforeend",
      `<span class="sc-wall"></span><span class="sc-floor"></span><span class="sc-shadow"></span>` +
      `<img class="sc-prod" alt="${cfg.alt || ""}" draggable="false"><canvas class="sc-fx"></canvas>`);
    const img = host.querySelector(".sc-prod");
    const alts = cfg.fallback || [];
    img.onerror = () => { const n = alts.shift(); if (n) { img.src = n; img.classList.add("flat"); } else img.onerror = null; };
    if (cfg.lazy) img.loading = "lazy";
    img.decoding = "async";
    img.src = cfg.cut;
    this.cv = host.querySelector(".sc-fx"); this.c = this.cv.getContext("2d");
    this.running = false; this.t = 0;
    Scene.all.push(this); Scene.io.observe(host);
  }
  Scene.all = [];
  Scene.prototype.size = function () {
    const r = this.host.getBoundingClientRect();
    if (!r.width) return false;
    this.W = r.width; this.H = r.height; this.floorY = this.H * 0.8;
    this.cv.width = Math.round(this.W * DPR); this.cv.height = Math.round(this.H * DPR);
    this.c.setTransform(DPR, 0, 0, DPR, 0, 0);
    return true;
  };
  Scene.prototype.start = function () {
    if (!this.size()) return;
    const cfg = this.cfg, n = Math.round((cfg.count || 9) * Math.min(1.6, Math.max(0.7, this.W / 320)));
    this.items = []; this.grains = []; this.puffs = []; this.glints = []; this.t = 0;
    if (cfg.fx === "capsule" || cfg.fx === "softgel" || cfg.fx === "mix") {
      const styles = cfg.styles.map(k => CAPS[k]);
      for (let i = 0; i < n; i++) this.items.push(new Capsule(this, styles[i % styles.length], Math.random()));
      this.items.sort((a, b) => a.z - b.z);
    }
    if (cfg.fx === "powder") {
      for (let i = 0; i < 520; i++) this.grains.push(new Grain(this, i < 200));
      this.heap = new Float32Array(Math.ceil(this.W / 3) + 1);
    }
    if (cfg.fx === "bubbles") {
      this.bubbles = Array.from({ length: Math.round(22 * this.W / 320) }, () => new Bubble(this));
    }
    if (REDUCE) { for (let i = 0; i < 360; i++) this.step(1 / 60); this.draw(); return; }
    if (!this.running) { this.running = true; this.last = performance.now(); requestAnimationFrame(this.loop.bind(this)); }
  };
  Scene.prototype.loop = function (now) {
    if (!this.running) return;
    const dt = Math.min(0.033, (now - this.last) / 1000); this.last = now;
    this.step(dt); this.draw();
    const settled = this.cfg.fx !== "bubbles" && this.t > 1.5 && this.items.every(i => i.done) && this.grains.every(g => g.landed) && !this.puffs.length;
    if (settled || !this.visible) { this.running = false; return; }
    requestAnimationFrame(this.loop.bind(this));
  };
  Scene.prototype.step = function (dt) {
    this.t += dt;
    for (const it of this.items) it.step(this, dt);
    if (this.grains.length) {
      const g = this.H * 1.6, fl = this.floorY + this.H * 0.06;
      for (const p of this.grains) {
        if (p.landed) continue;
        if (p.delay > 0) { p.delay -= dt; continue; }
        p.vy += g * dt; p.vx *= 0.985; p.vy *= 0.985;
        p.x += p.vx * dt; p.y += p.vy * dt;
        const b = Math.max(0, Math.min(this.heap.length - 1, Math.round(p.x / 3)));
        if (p.y >= fl - this.heap[b]) {
          p.landed = true; p.y = fl - this.heap[b];
          for (let k = -3; k <= 3; k++) { const j = b + k; if (j >= 0 && j < this.heap.length) this.heap[j] += (this.H * 0.0016) * (1 - Math.abs(k) / 4); }
          if (Math.random() < 0.05) this.puffs.push({ x: p.x, y: p.y, r: this.H * 0.02, a: 0.35 });
        }
      }
      for (const f of this.puffs) { f.r += this.H * 0.12 * dt; f.a -= 0.45 * dt; f.y -= this.H * 0.02 * dt; }
      this.puffs = this.puffs.filter(f => f.a > 0);
    }
    if (this.bubbles.length) {
      for (const b of this.bubbles) { b.y -= b.v * dt; b.ph += dt * 2.2 * b.w; if (b.y < -b.r * 2) b.reset(this); }
      if (Math.random() < dt * 1.4) this.glints.push({ x: this.W * rnd(0.3, 0.7), y: this.H * rnd(0.2, 0.7), t: 0, s: rnd(5, 11) * this.H / 300 });
      for (const g of this.glints) g.t += dt;
      this.glints = this.glints.filter(g => g.t < 0.9);
    }
  };
  Scene.prototype.draw = function () {
    const c = this.c; c.clearRect(0, 0, this.W, this.H);
    for (const it of this.items) it.shadow(this, c);
    for (const it of this.items) it.draw(c);
    if (this.grains.length) {
      const fl = this.floorY + this.H * 0.06, h = this.heap;
      // powder mound
      c.beginPath(); c.moveTo(0, fl);
      for (let i = 0; i < h.length; i++) c.lineTo(i * 3, fl - h[i]);
      c.lineTo(this.W, fl); c.closePath();
      const mg = c.createLinearGradient(0, fl - this.H * 0.08, 0, fl);
      mg.addColorStop(0, "#ffffff"); mg.addColorStop(1, "#ece6e2");
      c.fillStyle = mg; c.fill();
      for (const p of this.grains) {
        if (p.landed || p.delay > 0) continue;
        c.fillStyle = `rgba(255,255,255,${p.a})`; c.beginPath(); c.arc(p.x, p.y, p.r, 0, 7); c.fill();
      }
      for (const f of this.puffs) {
        const g = c.createRadialGradient(f.x, f.y, 0, f.x, f.y, f.r);
        g.addColorStop(0, `rgba(255,255,255,${f.a})`); g.addColorStop(1, "rgba(255,255,255,0)");
        c.fillStyle = g; c.beginPath(); c.arc(f.x, f.y, f.r, 0, 7); c.fill();
      }
    }
    for (const b of this.bubbles) {
      const x = b.x + Math.sin(b.ph) * b.r * 1.2;
      c.strokeStyle = "rgba(255,255,255,0.75)"; c.lineWidth = Math.max(0.8, b.r * 0.12);
      c.fillStyle = "rgba(255,255,255,0.12)";
      c.beginPath(); c.arc(x, b.y, b.r, 0, 7); c.fill(); c.stroke();
      c.fillStyle = "rgba(255,255,255,0.9)"; c.beginPath(); c.arc(x - b.r * 0.35, b.y - b.r * 0.35, b.r * 0.22, 0, 7); c.fill();
    }
    for (const g of this.glints) {
      const k = Math.sin(Math.PI * g.t / 0.9), s = g.s * k;
      c.save(); c.translate(g.x, g.y); c.rotate(g.t);
      c.fillStyle = `rgba(255,255,255,${0.9 * k})`;
      c.beginPath(); c.moveTo(0, -s); c.lineTo(s * 0.18, 0); c.lineTo(0, s); c.lineTo(-s * 0.18, 0); c.closePath(); c.fill();
      c.beginPath(); c.moveTo(-s, 0); c.lineTo(0, s * 0.18); c.lineTo(s, 0); c.lineTo(0, -s * 0.18); c.closePath(); c.fill();
      c.restore();
    }
  };
  Scene.io = new IntersectionObserver(entries => {
    for (const e of entries) {
      const s = Scene.all.find(x => x.host === e.target); if (!s) continue;
      const was = s.visible; s.visible = e.isIntersecting;
      if (s.visible && !was) s.start();
    }
  }, { threshold: 0.35 });
  Scene.replay = host => { const s = Scene.all.find(x => x.host === host); if (s && !s.running) s.start(); };
  Scene.forget = root => {
    for (const s of Scene.all.filter(x => root.contains(x.host))) { s.running = false; Scene.io.unobserve(s.host); }
    Scene.all = Scene.all.filter(x => !root.contains(x.host));
  };
  addEventListener("resize", () => { for (const s of Scene.all) if (s.visible && !s.running) { s.size(); s.draw(); } });
  window.Scene = Scene;
})();
