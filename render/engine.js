// Ya Olsaydı? — çöp adam animasyon motoru (Canvas 2D).
// timeline.json'daki sahneleri kare kare çizer. window.renderFrame(t) -> JPEG dataURL.
const W = 1080, H = 1920;
const c = document.getElementById('c'), x = c.getContext('2d');
let TL = null;

// ------------------------------------------------------------------ yardımcılar
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const lerp = (a, b, k) => a + (b - a) * k;
const ease = k => (k = clamp(k), k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const out = k => 1 - Math.pow(1 - clamp(k), 3);
const back = k => { k = clamp(k); const c1 = 1.9; return 1 + (c1 + 1) * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
const seg = (t, a, b) => clamp((t - a) / (b - a));
const TAU = Math.PI * 2;
function rng(seed) { let s = (seed * 9301 + 49297) % 233280 || 1; return () => (s = (s * 16807) % 2147483647) / 2147483647; }
function hashStr(s) { let h = 7; for (const ch of String(s)) h = (h * 31 + ch.charCodeAt(0)) % 1000003; return h; }
const UP = s => String(s || '').toLocaleUpperCase('tr');
const SY = v => 520 + v * 1040;           // sahne y (0..1) -> piksel; 1 = yer
const GROUND = 1560;
function poly(pts) { x.beginPath(); pts.forEach(([a, b], i) => i ? x.lineTo(a, b) : x.moveTo(a, b)); x.closePath(); }
function circ(cx, cy, r) { x.beginPath(); x.arc(cx, cy, Math.max(0, r), 0, TAU); }
function rrect(a, b, w, h, r) { x.beginPath(); x.roundRect(a, b, w, h, r); }
function outlineFill(fill, lw = 6, stroke = '#0a0d24') { x.fillStyle = fill; x.fill(); x.lineWidth = lw; x.strokeStyle = stroke; x.stroke(); }

const STARS = (() => { const r = rng(11); return Array.from({length: 190}, () => [r() * W, r() * H * .8, r() * 2.6 + .5, r() * 6]); })();

// ------------------------------------------------------------------ arka planlar
function grad(stops) { const g = x.createLinearGradient(0, 0, 0, H); stops.forEach(([o, col]) => g.addColorStop(o, col)); x.fillStyle = g; x.fillRect(0, 0, W, H); }
function stars(t, a = 1) { for (const [sx, sy, r, ph] of STARS) { x.globalAlpha = a * (.4 + .6 * Math.abs(Math.sin(t * 1.3 + ph))); x.fillStyle = '#fff'; circ(sx, sy, r); x.fill(); } x.globalAlpha = 1; }
function hill(col, edge, y = GROUND) {
  x.fillStyle = col; x.beginPath(); x.moveTo(0, y + 40); x.quadraticCurveTo(W / 2, y - 60, W, y + 40); x.lineTo(W, H); x.lineTo(0, H); x.fill();
  if (edge) { x.strokeStyle = edge; x.lineWidth = 5; x.beginPath(); x.moveTo(0, y + 40); x.quadraticCurveTo(W / 2, y - 60, W, y + 40); x.stroke(); }
}
function flatGround(col, edge, y = GROUND) { x.fillStyle = col; x.fillRect(0, y, W, H - y); if (edge) { x.fillStyle = edge; x.fillRect(0, y, W, 8); } }
function softClouds(t, col = 'rgba(255,255,255,.85)') {
  x.fillStyle = col;
  for (let i = 0; i < 4; i++) { const cx = ((i * 330 + t * 18) % (W + 400)) - 200, cy = 640 + (i % 2) * 170;
    for (const [dx, dy, r] of [[-60, 10, 50], [0, -15, 70], [70, 8, 55]]) { circ(cx + dx, cy + dy, r); x.fill(); } }
}
const SKYLINE = (() => { const r = rng(5); const b = []; let px = -20; while (px < W + 40) { const w = 70 + r() * 110; b.push([px, w, 220 + r() * 420]); px += w + 6; } return b; })();
const BG = {
  night(t) { grad([[0, '#080b24'], [1, '#1f2c66']]); stars(t); hill('#141c42', 'rgba(140,170,255,.35)'); },
  day(t) { grad([[0, '#4aa8ff'], [1, '#bfe6ff']]); softClouds(t); hill('#4cb35a', '#6fd47c'); },
  sunset(t) { grad([[0, '#2a1a5e'], [.55, '#d0567a'], [1, '#ffb36b']]); stars(t, .35); hill('#2b1640', '#5a2f6e'); },
  space(t) { grad([[0, '#03040f'], [1, '#0d1240']]);
    const g = x.createRadialGradient(780, 700, 40, 780, 700, 600); g.addColorStop(0, 'rgba(140,80,255,.22)'); g.addColorStop(1, 'rgba(140,80,255,0)'); x.fillStyle = g; x.fillRect(0, 0, W, H);
    stars(t); },
  city(t) { grad([[0, '#ff9e6b'], [1, '#ffd9a8']]);
    for (const [bx, bw, bh] of SKYLINE) { x.fillStyle = '#6b4a7a'; x.fillRect(bx, GROUND - bh, bw, bh);
      x.fillStyle = 'rgba(255,230,150,.55)'; for (let wy = GROUND - bh + 24; wy < GROUND - 30; wy += 46) for (let wx = bx + 14; wx < bx + bw - 20; wx += 30) x.fillRect(wx, wy, 14, 20); }
    flatGround('#4a4a5a', '#2c2c38'); x.fillStyle = '#ffd23f'; for (let i = 0; i < 6; i++) x.fillRect(i * 200 + 40, GROUND + 120, 110, 12); },
  beach(t) { grad([[0, '#55b8ff'], [.55, '#bdeaff'], [1, '#bdeaff']]); softClouds(t);
    x.fillStyle = '#1f7fd6'; x.fillRect(0, GROUND - 170, W, 170);
    x.strokeStyle = 'rgba(255,255,255,.7)'; x.lineWidth = 5; x.beginPath(); for (let i = 0; i <= 40; i++) { const xx = i / 40 * W; x.lineTo(xx, GROUND - 170 + Math.sin(xx / 50 + t * 3) * 6); } x.stroke();
    flatGround('#f0d08a', '#d9b56a'); },
  desert(t) { grad([[0, '#ffb04a'], [1, '#ffe3a1']]); x.fillStyle = '#e8a64a';
    x.beginPath(); x.moveTo(0, GROUND - 60); x.quadraticCurveTo(300, GROUND - 200, 620, GROUND - 40); x.quadraticCurveTo(850, GROUND - 150, W, GROUND - 70); x.lineTo(W, H); x.lineTo(0, H); x.fill();
    flatGround('#f2c46b', '#d9a24f'); },
  snow(t) { grad([[0, '#9fc3e8'], [1, '#e8f3ff']]); hill('#ffffff', '#cfe3f7'); },
  room(t) { x.fillStyle = '#f3dcb3'; x.fillRect(0, 0, W, H); x.fillStyle = '#e8cc9c'; for (let i = 0; i < W; i += 90) x.fillRect(i, 0, 40, GROUND);
    rrect(640, 620, 330, 300, 14); outlineFill('#16205a', 12, '#8a5a32'); x.save(); x.beginPath(); x.rect(646, 626, 318, 288); x.clip(); stars(t, .8); x.restore();
    x.fillStyle = '#8a5a32'; x.fillRect(800, 620, 10, 300); x.fillRect(640, 765, 330, 10);
    flatGround('#a8743f', '#7a4f26'); },
  forest(t) { grad([[0, '#7cc6ff'], [1, '#d8f1ff']]);
    for (const [layer, col, yy] of [[0, '#3c8a5a', GROUND - 120], [1, '#2a6e46', GROUND - 40]]) { x.fillStyle = col;
      for (let i = -1; i < 9; i++) { const tx = i * 140 + layer * 70; poly([[tx, yy], [tx + 70, yy - 260 + layer * 60], [tx + 140, yy]]); x.fill(); } }
    flatGround('#3f9a4f', '#5cbf6a'); },
  red(t) { grad([[0, '#2a0508'], [.6, '#8a1a12'], [1, '#ff6a2a']]);
    const r = rng(3); x.fillStyle = 'rgba(255,200,150,.6)'; for (let i = 0; i < 60; i++) { const ax = (r() * W + t * 30 * (r() + .3)) % W, ay = (r() * H + t * 60 * (r() + .2)) % H; circ(ax, ay, 2 + r() * 3); x.fill(); }
    hill('#1a0a0a', '#ff6a2a'); },
};

// ------------------------------------------------------------------ nesneler (s = genişlik px, merkez/taban 0,0)
const P = {};
P.moon = (s, st) => { const r = s / 2; const gl = x.createRadialGradient(0, 0, r * .8, 0, 0, r * 1.6); gl.addColorStop(0, 'rgba(255,250,220,.35)'); gl.addColorStop(1, 'rgba(255,250,220,0)'); x.fillStyle = gl; circ(0, 0, r * 1.6); x.fill();
  const g = x.createRadialGradient(-r * .35, -r * .35, r * .1, 0, 0, r); g.addColorStop(0, '#fbf8ec'); g.addColorStop(1, '#bdb8a6'); x.fillStyle = g; circ(0, 0, r); x.fill();
  x.fillStyle = 'rgba(120,115,100,.35)'; for (const [a, b, cr] of [[-.3, -.2, .2], [.3, .1, .14], [-.1, .4, .12], [.35, -.4, .1], [-.5, .25, .08]]) { circ(a * r, b * r, cr * r); x.fill(); } };
P.earth = (s, st) => { const r = s / 2; const gl = x.createRadialGradient(0, 0, r, 0, 0, r * 1.18); gl.addColorStop(0, 'rgba(90,170,255,.55)'); gl.addColorStop(1, 'rgba(90,170,255,0)'); x.fillStyle = gl; circ(0, 0, r * 1.18); x.fill();
  x.save(); circ(0, 0, r); x.clip(); const g = x.createRadialGradient(-r * .3, -r * .4, r * .1, 0, 0, r); g.addColorStop(0, '#4aa3ff'); g.addColorStop(1, '#173f9c'); x.fillStyle = g; x.fillRect(-r, -r, 2 * r, 2 * r);
  x.fillStyle = '#3fae5a'; const rr = rng(4); for (let k = 0; k < 6; k++) { const cx = rr() * 1.4 - .7, cy = rr() * 1.4 - .7, rad = rr() * .25 + .15; x.beginPath(); for (let i = 0; i < 9; i++) { const a = i / 9 * TAU, q = rad * (.6 + rr() * .6); x.lineTo((cx + Math.cos(a) * q) * r, (cy + Math.sin(a) * q) * r); } x.fill(); }
  const sh = x.createLinearGradient(-r, -r, r, r); sh.addColorStop(.5, 'rgba(0,0,20,0)'); sh.addColorStop(1, 'rgba(0,0,20,.5)'); x.fillStyle = sh; x.fillRect(-r, -r, 2 * r, 2 * r); x.restore(); };
P.sun = (s, st) => { const r = s * .32; x.save(); x.rotate(st.t * .4); x.fillStyle = '#ffcc33'; for (let i = 0; i < 12; i++) { x.rotate(TAU / 12); poly([[-r * .18, -r * 1.1], [0, -r * 1.55], [r * .18, -r * 1.1]]); x.fill(); } x.restore();
  const g = x.createRadialGradient(0, 0, r * .2, 0, 0, r); g.addColorStop(0, '#fff3a0'); g.addColorStop(1, '#ffb020'); x.fillStyle = g; circ(0, 0, r); x.fill(); };
P.planet = (s, st) => { const r = s * .34, col = st.color || '#e0874a'; x.fillStyle = col; circ(0, 0, r); x.fill(); x.fillStyle = 'rgba(255,255,255,.18)'; x.fillRect(-r, -r * .3, 2 * r, r * .18);
  x.strokeStyle = 'rgba(255,230,180,.85)'; x.lineWidth = s * .03; x.beginPath(); x.ellipse(0, 0, r * 1.5, r * .38, -.3, 0, TAU); x.stroke(); };
P.asteroid = (s, st) => { const r = s / 2, rr = rng(8); poly(Array.from({length: 11}, (_, i) => { const a = i / 11 * TAU, q = r * (.7 + rr() * .3); return [Math.cos(a) * q, Math.sin(a) * q]; })); outlineFill('#8a7f72', s * .03, '#4a4038');
  x.fillStyle = '#6a6056'; for (const [a, b, q] of [[-.2, -.2, .18], [.25, .2, .12], [.1, -.35, .08]]) { circ(a * s, b * s, q * s); x.fill(); } };
P.meteor = (s, st) => { const g = x.createLinearGradient(0, 0, s * .9, -s * .9); g.addColorStop(0, 'rgba(255,200,80,.95)'); g.addColorStop(1, 'rgba(255,90,30,0)'); x.fillStyle = g; poly([[-s * .16, -s * .05], [s * .9, -s * .9], [s * .05, s * .16]]); x.fill(); P.asteroid(s * .38, st); };
P.rocket = (s, st) => { const w = s * .32, h = s; x.fillStyle = '#ff7a2a'; const f = 1 + .25 * Math.sin(st.t * 40); poly([[-w * .3, 0], [0, h * .35 * f], [w * .3, 0]]); x.fill();
  x.beginPath(); x.moveTo(0, -h); x.quadraticCurveTo(w * .9, -h * .6, w / 2, -h * .05); x.lineTo(-w / 2, -h * .05); x.quadraticCurveTo(-w * .9, -h * .6, 0, -h); outlineFill('#f4f4f8', s * .025);
  poly([[-w / 2, -h * .3], [-w, 0], [-w / 2, 0]]); outlineFill('#e8443a', s * .02); poly([[w / 2, -h * .3], [w, 0], [w / 2, 0]]); outlineFill('#e8443a', s * .02);
  circ(0, -h * .58, w * .2); outlineFill('#59c3ff', s * .02); };
P.ufo = (s, st) => { x.fillStyle = 'rgba(160,255,200,.25)'; poly([[-s * .18, 0], [s * .18, 0], [s * .4, s * .9], [-s * .4, s * .9]]); x.fill();
  x.beginPath(); x.ellipse(0, -s * .1, s * .2, s * .17, 0, Math.PI, 0); outlineFill('rgba(150,230,255,.9)', s * .02);
  x.beginPath(); x.ellipse(0, 0, s * .5, s * .13, 0, 0, TAU); outlineFill('#9aa3b8', s * .025);
  for (let i = -2; i <= 2; i++) { x.fillStyle = Math.sin(st.t * 8 + i) > 0 ? '#ffd23f' : '#ff5a5a'; circ(i * s * .17, s * .03, s * .03); x.fill(); } };
P.alien = (s, st) => { const h = s; x.strokeStyle = '#7be37b'; x.lineWidth = s * .04; x.lineCap = 'round';
  x.beginPath(); x.moveTo(0, -h * .35); x.lineTo(0, -h * .05); x.moveTo(0, -h * .2); x.lineTo(-s * .2, -h * .02); x.moveTo(0, -h * .2); x.lineTo(s * .2, -h * .02); x.moveTo(0, -h * .05); x.lineTo(-s * .1, 0); x.moveTo(0, -h * .05); x.lineTo(s * .1, 0); x.stroke();
  x.beginPath(); x.ellipse(0, -h * .55, s * .26, s * .22, 0, 0, TAU); outlineFill('#7be37b', s * .02);
  x.fillStyle = '#111'; for (const d of [-1, 1]) { x.beginPath(); x.ellipse(d * s * .1, -h * .57, s * .07, s * .1, d * .4, 0, TAU); x.fill(); }
  x.strokeStyle = '#7be37b'; x.lineWidth = s * .025; for (const d of [-1, 1]) { x.beginPath(); x.moveTo(d * s * .08, -h * .75); x.lineTo(d * s * .16, -h * .9); x.stroke(); circ(d * s * .16, -h * .9, s * .03); x.fillStyle = '#ffd23f'; x.fill(); } };
P.city = (s, st) => { const r = rng(9); let px = -s / 2; while (px < s / 2) { const w = s * (.08 + r() * .08), h = s * (.25 + r() * .45); x.fillStyle = st.off ? '#2a2f45' : '#5d6a8f'; x.fillRect(px, -h, w, h);
  x.fillStyle = st.off ? '#1c2033' : '#ffe08a'; for (let wy = -h + s * .03; wy < -s * .03; wy += s * .045) for (let wx = px + s * .015; wx < px + w - s * .02; wx += s * .03) x.fillRect(wx, wy, s * .012, s * .02); px += w + s * .008; } };
P.house = (s, st) => { const w = s * .8; x.fillStyle = '#f4e0c0'; x.fillRect(-w / 2, -w * .7, w, w * .7); x.lineWidth = s * .02; x.strokeStyle = '#0a0d24'; x.strokeRect(-w / 2, -w * .7, w, w * .7);
  poly([[-w * .62, -w * .68], [0, -w * 1.15], [w * .62, -w * .68]]); outlineFill('#d8443a', s * .02); x.fillStyle = '#8a5a32'; x.fillRect(-w * .1, -w * .38, w * .2, w * .38);
  x.fillStyle = st.off ? '#2a2f45' : '#ffe08a'; x.fillRect(w * .18, -w * .55, w * .2, w * .18); x.fillRect(-w * .38, -w * .55, w * .2, w * .18); };
P.building = (s, st) => { const w = s * .5, h = s * 1.3; x.fillStyle = '#7d8bb0'; x.fillRect(-w / 2, -h, w, h); x.lineWidth = s * .02; x.strokeStyle = '#0a0d24'; x.strokeRect(-w / 2, -h, w, h);
  x.fillStyle = st.off ? '#2a2f45' : '#ffe08a'; for (let wy = -h + s * .06; wy < -s * .1; wy += s * .11) for (let wx = -w / 2 + s * .05; wx < w / 2 - s * .06; wx += s * .11) x.fillRect(wx, wy, s * .06, s * .07); };
P.car = (s, st) => { const w = s; x.beginPath(); x.moveTo(-w * .5, -w * .12); x.lineTo(-w * .5, -w * .3); x.lineTo(-w * .3, -w * .32); x.lineTo(-w * .18, -w * .5); x.lineTo(w * .2, -w * .5); x.lineTo(w * .32, -w * .32); x.lineTo(w * .5, -w * .28); x.lineTo(w * .5, -w * .12); x.closePath(); outlineFill(st.color || '#ff5a5a', s * .02);
  x.fillStyle = '#9fe0ff'; poly([[-w * .14, -w * .46], [w * .17, -w * .46], [w * .26, -w * .33], [-w * .24, -w * .33]]); x.fill();
  for (const d of [-.3, .3]) { circ(d * w, -w * .1, w * .1); outlineFill('#222', s * .02); circ(d * w, -w * .1, w * .04); x.fillStyle = '#aaa'; x.fill(); } };
P.plane = (s, st) => { const w = s; x.beginPath(); x.ellipse(0, 0, w * .5, w * .08, 0, 0, TAU); outlineFill('#f4f4f8', s * .02);
  poly([[-w * .05, 0], [w * .12, -w * .38], [w * .2, -w * .38], [w * .12, 0]]); outlineFill('#59a0ff', s * .015); poly([[-w * .42, 0], [-w * .5, -w * .2], [-w * .4, -w * .2], [-w * .32, 0]]); outlineFill('#59a0ff', s * .015);
  x.fillStyle = '#59c3ff'; for (let i = 0; i < 5; i++) { circ(-w * .2 + i * w * .1, -w * .01, w * .02); x.fill(); } };
P.tree = (s, st) => { x.fillStyle = '#8a5a32'; x.fillRect(-s * .07, -s * .5, s * .14, s * .5); x.fillStyle = st.off ? '#6b5a3a' : '#3fae5a'; for (const [a, b, r] of [[0, -.75, .3], [-.2, -.6, .22], [.2, -.6, .22]]) { circ(a * s, b * s, r * s); x.fill(); } };
P.mountain = (s, st) => { poly([[-s / 2, 0], [0, -s * .75], [s / 2, 0]]); outlineFill('#7a86a8', s * .015); poly([[-s * .13, -s * .55], [0, -s * .75], [s * .13, -s * .55], [s * .05, -s * .5], [-s * .04, -s * .56]]); x.fillStyle = '#fff'; x.fill(); };
P.volcano = (s, st) => { poly([[-s / 2, 0], [-s * .12, -s * .55], [s * .12, -s * .55], [s / 2, 0]]); outlineFill('#6a4a3a', s * .015);
  x.fillStyle = '#ff6a2a'; poly([[-s * .12, -s * .55], [s * .12, -s * .55], [s * .05, -s * .3], [0, -s * .4], [-s * .06, -s * .25]]); x.fill();
  for (let i = 0; i < 4; i++) { const k = (st.t * .5 + i / 4) % 1; x.fillStyle = `rgba(90,90,100,${.6 * (1 - k)})`; circ(Math.sin(i * 2 + k * 3) * s * .1, -s * .6 - k * s * .6, s * (.06 + k * .14)); x.fill(); } };
P.cloud = (s, st) => { x.fillStyle = st.color || '#f4f6ff'; for (const [a, b, r] of [[-.25, 0, .2], [0, -.1, .28], [.27, 0, .2], [0, .05, .22]]) { circ(a * s, b * s, r * s); x.fill(); } };
P.lightning = (s, st) => { if (Math.sin(st.t * 23) < -.3) return; poly([[0, -s * .6], [-s * .2, 0], [-s * .02, 0], [-s * .12, s * .6], [s * .22, -s * .1], [s * .02, -s * .1], [s * .1, -s * .6]]); outlineFill('#ffe14a', s * .02); };
P.fire = (s, st) => { for (const [col, sc] of [['#ff4a1a', 1], ['#ff9a2a', .7], ['#ffe14a', .4]]) { const f = 1 + .12 * Math.sin(st.t * 18 + sc * 5);
  x.fillStyle = col; x.beginPath(); x.moveTo(-s * .35 * sc, 0); x.quadraticCurveTo(-s * .45 * sc, -s * .5 * sc * f, 0, -s * sc * f); x.quadraticCurveTo(s * .45 * sc, -s * .5 * sc * f, s * .35 * sc, 0); x.closePath(); x.fill(); } };
P.phone = (s, st) => { const w = s * .5, h = s * .95; rrect(-w / 2, -h / 2, w, h, s * .07); outlineFill('#222', s * .02); rrect(-w * .42, -h * .43, w * .84, h * .8, s * .03); x.fillStyle = st.off ? '#111' : '#59c3ff'; x.fill();
  if (st.text) { x.fillStyle = '#fff'; x.font = `${s * .11}px Black`; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(UP(st.text).slice(0, 6), 0, -h * .05); } };
P.laptop = (s, st) => { rrect(-s * .4, -s * .55, s * .8, s * .5, s * .03); outlineFill('#333', s * .02); x.fillStyle = st.off ? '#111' : '#59c3ff'; x.fillRect(-s * .35, -s * .5, s * .7, s * .4);
  poly([[-s * .5, 0], [s * .5, 0], [s * .42, -s * .06], [-s * .42, -s * .06]]); outlineFill('#9aa3b8', s * .02); };
P.wifi = (s, st) => { x.lineCap = 'round'; x.strokeStyle = st.off ? '#9aa3b8' : '#4ad37b'; x.lineWidth = s * .08; for (const r of [.15, .3, .45]) { x.beginPath(); x.arc(0, s * .25, r * s, -Math.PI * .78, -Math.PI * .22); x.stroke(); } x.fillStyle = x.strokeStyle; circ(0, s * .22, s * .06); x.fill();
  if (st.off) { x.strokeStyle = '#ff4a4a'; x.lineWidth = s * .09; x.beginPath(); x.moveTo(-s * .4, -s * .3); x.lineTo(s * .4, s * .35); x.stroke(); } };
P.clock = (s, st) => { const r = s * .45; circ(0, 0, r); outlineFill('#fff', s * .05, '#0a0d24'); x.strokeStyle = '#0a0d24'; x.lineCap = 'round';
  for (const [len, sp, lw] of [[.5, .4, .07], [.75, 4, .04]]) { const a = st.t * sp * (st.off ? 0 : 1) + 1; x.lineWidth = s * lw; x.beginPath(); x.moveTo(0, 0); x.lineTo(Math.sin(a) * r * len, -Math.cos(a) * r * len); x.stroke(); } };
P.calendar = (s, st) => { rrect(-s * .4, -s * .4, s * .8, s * .8, s * .05); outlineFill('#fff', s * .03); x.fillStyle = '#e8443a'; x.fillRect(-s * .4, -s * .4, s * .8, s * .2);
  x.fillStyle = '#0a0d24'; x.font = `${s * .22}px Black`; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(UP(st.text || '1').slice(0, 5), 0, s * .1); };
P.money = (s, st) => { for (let i = 2; i >= 0; i--) { x.save(); x.translate(i * s * .06, -i * s * .05); x.rotate(-.1); rrect(-s * .45, -s * .22, s * .9, s * .44, s * .03); outlineFill('#5fc46a', s * .02); circ(0, 0, s * .12); x.fillStyle = '#3e9a4a'; x.fill(); x.restore(); }
  x.fillStyle = '#fff'; x.font = `${s * .2}px Black`; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(st.text ? UP(st.text).slice(0, 4) : '₺', 0, 0); };
P.lightbulb = (s, st) => { if (!st.off) { const g = x.createRadialGradient(0, -s * .2, 0, 0, -s * .2, s * .6); g.addColorStop(0, 'rgba(255,230,120,.6)'); g.addColorStop(1, 'rgba(255,230,120,0)'); x.fillStyle = g; circ(0, -s * .2, s * .6); x.fill(); }
  circ(0, -s * .2, s * .3); outlineFill(st.off ? '#777' : '#ffe14a', s * .03); x.fillStyle = '#9aa3b8'; x.fillRect(-s * .13, s * .08, s * .26, s * .2); };
P.battery = (s, st) => { const lv = st.level ?? 1; rrect(-s * .45, -s * .22, s * .85, s * .44, s * .05); outlineFill('#fff', s * .04); x.fillStyle = '#0a0d24'; x.fillRect(s * .42, -s * .1, s * .07, s * .2);
  x.fillStyle = lv > .5 ? '#4ad37b' : lv > .2 ? '#ffc23a' : '#ff4a4a'; x.fillRect(-s * .4, -s * .17, s * .75 * clamp(lv), s * .34); };
P.robot = (s, st) => { x.strokeStyle = '#0a0d24'; x.lineWidth = s * .03; x.beginPath(); x.moveTo(0, -s); x.lineTo(0, -s * 1.12); x.stroke(); circ(0, -s * 1.14, s * .04); x.fillStyle = '#ff5a5a'; x.fill();
  rrect(-s * .25, -s, s * .5, s * .38, s * .06); outlineFill('#b8c4dc', s * .03); rrect(-s * .3, -s * .58, s * .6, s * .42, s * .05); outlineFill('#8e9bbd', s * .03);
  x.fillStyle = Math.sin(st.t * 3) > .9 ? '#0a0d24' : '#59e0ff'; for (const d of [-1, 1]) { circ(d * s * .1, -s * .82, s * .05); x.fill(); }
  x.fillStyle = '#0a0d24'; x.fillRect(-s * .1, -s * .7, s * .2, s * .03); x.fillStyle = '#8e9bbd'; x.fillRect(-s * .22, -s * .16, s * .12, s * .16); x.fillRect(s * .1, -s * .16, s * .12, s * .16); };
P.dino = (s, st) => { const b = Math.sin(st.t * 8) * s * .02; x.beginPath(); x.moveTo(-s * .5, -s * .35); x.quadraticCurveTo(-s * .2, -s * .5, 0, -s * .5); x.lineTo(s * .05, -s * .85 + b); x.lineTo(s * .45, -s * .85 + b); x.lineTo(s * .45, -s * .65 + b);
  x.lineTo(s * .2, -s * .62); x.lineTo(s * .2, -s * .3); x.lineTo(s * .12, 0); x.lineTo(s * .02, 0); x.lineTo(0, -s * .2); x.lineTo(-s * .15, -s * .2); x.lineTo(-s * .17, 0); x.lineTo(-s * .27, 0); x.lineTo(-s * .25, -s * .25); x.closePath(); outlineFill('#5fbf5a', s * .025);
  x.fillStyle = '#0a0d24'; circ(s * .3, -s * .77 + b, s * .03); x.fill(); x.fillStyle = '#fff'; for (let i = 0; i < 3; i++) { poly([[s * (.28 + i * .05), -s * .67 + b], [s * (.3 + i * .05), -s * .63 + b], [s * (.32 + i * .05), -s * .67 + b]]); x.fill(); } };
P.cat = (s, st) => { const c0 = st.color || '#ffa24a'; poly([[-s * .3, -s * .55], [-s * .25, -s * .85], [-s * .05, -s * .65]]); outlineFill(c0, s * .02); poly([[s * .3, -s * .55], [s * .25, -s * .85], [s * .05, -s * .65]]); outlineFill(c0, s * .02);
  x.beginPath(); x.ellipse(0, -s * .2, s * .3, s * .22, 0, 0, TAU); outlineFill(c0, s * .02); circ(0, -s * .52, s * .27); outlineFill(c0, s * .02);
  x.fillStyle = '#0a0d24'; for (const d of [-1, 1]) { x.beginPath(); x.ellipse(d * s * .1, -s * .55, s * .03, s * .06, 0, 0, TAU); x.fill(); } x.strokeStyle = '#0a0d24'; x.lineWidth = s * .012;
  for (const d of [-1, 1]) for (const k of [-1, 1]) { x.beginPath(); x.moveTo(d * s * .08, -s * .45); x.lineTo(d * s * .32, -s * .45 + k * s * .04); x.stroke(); } };
P.dog = (s, st) => { const c0 = st.color || '#c8894a'; x.beginPath(); x.ellipse(0, -s * .2, s * .32, s * .22, 0, 0, TAU); outlineFill(c0, s * .02); circ(0, -s * .55, s * .26); outlineFill(c0, s * .02);
  for (const d of [-1, 1]) { x.save(); x.translate(d * s * .24, -s * .62); x.rotate(d * (.3 + .15 * Math.sin(st.t * 6))); x.beginPath(); x.ellipse(0, s * .12, s * .08, s * .17, 0, 0, TAU); outlineFill('#7a4f26', s * .015); x.restore(); }
  x.fillStyle = '#0a0d24'; for (const d of [-1, 1]) { circ(d * s * .09, -s * .6, s * .035); x.fill(); } circ(0, -s * .48, s * .05); x.fill(); };
P.heart = (s, st) => { const p = 1 + .08 * Math.sin(st.t * 8); x.scale(p, p); x.beginPath(); x.moveTo(0, s * .35); x.bezierCurveTo(-s * .6, -s * .05, -s * .3, -s * .55, 0, -s * .2); x.bezierCurveTo(s * .3, -s * .55, s * .6, -s * .05, 0, s * .35); outlineFill(st.color || '#ff4a6a', s * .03); };
P.question = (s, st) => bigGlyph('?', s, st.color || '#ffd23f');
P.exclamation = (s, st) => bigGlyph('!', s, st.color || '#ff5a5a');
P.text = (s, st) => bigGlyph(UP(st.text || '?').slice(0, 14), s * .5, st.color || '#ffd23f');
function bigGlyph(g, s, col) { x.font = `${s}px Black`; x.textAlign = 'center'; x.textBaseline = 'middle'; x.lineJoin = 'round'; x.lineWidth = s * .14; x.strokeStyle = '#0a0d24'; x.strokeText(g, 0, 0); x.fillStyle = col; x.fillText(g, 0, 0); }
P.sign = (s, st) => { x.fillStyle = '#8a5a32'; x.fillRect(-s * .04, -s * .6, s * .08, s * .6); rrect(-s * .5, -s * .85, s, s * .38, s * .04); outlineFill('#d9a35a', s * .02);
  x.fillStyle = '#0a0d24'; const t = UP(st.text || 'DİKKAT'); x.font = `${Math.min(s * .16, s * 1.6 / Math.max(4, t.length))}px Black`; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(t, 0, -s * .66); };
P.thermometer = (s, st) => { const lv = st.level ?? .8; rrect(-s * .08, -s * .9, s * .16, s * .75, s * .08); outlineFill('#fff', s * .03); circ(0, -s * .13, s * .14); outlineFill('#ff4a4a', s * .03);
  x.fillStyle = '#ff4a4a'; x.fillRect(-s * .04, -s * .2 - s * .62 * clamp(lv), s * .08, s * .62 * clamp(lv)); if (st.text) { x.save(); x.translate(s * .45, -s * .6); bigGlyph(UP(st.text).slice(0, 6), s * .2, '#fff'); x.restore(); } };
P.bed = (s, st) => { x.fillStyle = '#8a5a32'; x.fillRect(-s / 2, -s * .35, s * .06, s * .35); x.fillRect(s * .44, -s * .25, s * .06, s * .25); rrect(-s * .45, -s * .22, s * .9, s * .14, s * .03); outlineFill('#5a7ad8', s * .015);
  rrect(-s * .43, -s * .3, s * .22, s * .1, s * .04); outlineFill('#fff', s * .015); };
P.burger = (s, st) => { x.beginPath(); x.ellipse(0, -s * .3, s * .42, s * .22, 0, Math.PI, 0); outlineFill('#e8a64a', s * .02); x.fillStyle = '#4ad37b'; x.fillRect(-s * .44, -s * .3, s * .88, s * .06);
  rrect(-s * .42, -s * .24, s * .84, s * .1, s * .04); outlineFill('#7a3a1a', s * .02); rrect(-s * .4, -s * .14, s * .8, s * .12, s * .05); outlineFill('#e8a64a', s * .02); };
P.ice = (s, st) => { rrect(-s * .4, -s * .7, s * .8, s * .7, s * .08); outlineFill('rgba(190,235,255,.85)', s * .03, '#5aa8d8'); x.fillStyle = 'rgba(255,255,255,.8)'; x.fillRect(-s * .28, -s * .58, s * .1, s * .3); };
P.satellite = (s, st) => { x.save(); x.rotate(Math.sin(st.t) * .2); x.fillStyle = '#3a5ad8'; x.fillRect(-s * .5, -s * .12, s * .32, s * .24); x.fillRect(s * .18, -s * .12, s * .32, s * .24);
  rrect(-s * .16, -s * .16, s * .32, s * .32, s * .04); outlineFill('#d8d8e0', s * .02); x.restore(); };
P.arrow_up = (s, st) => { poly([[0, -s * .5], [s * .35, -s * .1], [s * .13, -s * .1], [s * .13, s * .45], [-s * .13, s * .45], [-s * .13, -s * .1], [-s * .35, -s * .1]]); outlineFill(st.color || '#4ad37b', s * .03); };
P.arrow_down = (s, st) => { x.rotate(Math.PI); P.arrow_up(s, {...st, color: st.color || '#ff4a4a'}); };
P.book = (s, st) => { rrect(-s * .4, -s * .3, s * .8, s * .55, s * .03); outlineFill(st.color || '#d8443a', s * .02); x.fillStyle = '#fff'; x.fillRect(-s * .36, s * .17, s * .72, s * .05); };
P.tv = (s, st) => { rrect(-s * .45, -s * .7, s * .9, s * .6, s * .05); outlineFill('#333', s * .02); x.fillStyle = st.off ? '#111' : `hsl(${(st.t * 90) % 360},70%,60%)`; x.fillRect(-s * .38, -s * .63, s * .76, s * .46);
  x.strokeStyle = '#333'; x.lineWidth = s * .03; x.beginPath(); x.moveTo(-s * .2, -s * .1); x.lineTo(-s * .25, 0); x.moveTo(s * .2, -s * .1); x.lineTo(s * .25, 0); x.stroke(); };
P.crowd = (s, st) => { for (let i = 0; i < 5; i++) { const px = (i - 2) * s * .22, ph = st.t * 9 + i * 1.7; x.save(); x.translate(px, 0);
  stickRaw(0, 0, s * .0016, i % 2 ? runPose(ph, i % 3 ? 1 : -1) : mixPose(POSE.shock, POSE.panic, .5 + .5 * Math.sin(ph)), {color: ['#ffd23f', '#9fe0ff', '#ffb3c8', '#b4f0a0', '#fff'][i], hop: Math.abs(Math.sin(ph)) * 20 * s * .0016}); x.restore(); } };
P.person = (s, st) => stickRaw(0, 0, s * .0027, POSE[st.pose] || POSE.stand, {color: st.color || '#9fe0ff'});
P.ghost = (s, st) => { x.beginPath(); x.moveTo(-s * .35, s * .3); x.lineTo(-s * .35, -s * .1); x.arc(0, -s * .1, s * .35, Math.PI, 0); x.lineTo(s * .35, s * .3); for (let i = 0; i < 4; i++) x.quadraticCurveTo(s * (.35 - i * .175 - .09), s * (.42 + .05 * Math.sin(st.t * 6 + i)), s * (.35 - (i + 1) * .175), s * .3); outlineFill('rgba(255,255,255,.92)', s * .02);
  x.fillStyle = '#0a0d24'; for (const d of [-1, 1]) { circ(d * s * .12, -s * .12, s * .05); x.fill(); } x.beginPath(); x.ellipse(0, s * .04, s * .05, s * .07, 0, 0, TAU); x.fill(); };
P.water_drop = (s, st) => { x.beginPath(); x.moveTo(0, -s * .45); x.quadraticCurveTo(s * .35, 0, s * .3, s * .15); x.arc(0, s * .15, s * .3, 0, Math.PI); x.quadraticCurveTo(-s * .35, 0, 0, -s * .45); outlineFill('#59a8ff', s * .03); };
P.globe = P.earth;
P.star = (s, st) => { poly(Array.from({length: 10}, (_, i) => { const a = i / 10 * TAU - Math.PI / 2, r = i % 2 ? s * .2 : s * .45; return [Math.cos(a) * r, Math.sin(a) * r]; })); outlineFill(st.color || '#ffd23f', s * .03); };
P.gift = (s, st) => { rrect(-s * .38, -s * .6, s * .76, s * .6, s * .03); outlineFill('#ff5a8a', s * .02); x.fillStyle = '#ffd23f'; x.fillRect(-s * .06, -s * .6, s * .12, s * .6); x.fillRect(-s * .38, -s * .36, s * .76, s * .1); };
P.crown = (s, st) => { poly([[-s * .4, 0], [-s * .45, -s * .45], [-s * .2, -s * .2], [0, -s * .55], [s * .2, -s * .2], [s * .45, -s * .45], [s * .4, 0]]); outlineFill('#ffd23f', s * .03); };
P.magnet = (s, st) => { x.lineWidth = s * .2; x.strokeStyle = '#e8443a'; x.beginPath(); x.arc(0, 0, s * .3, Math.PI, 0); x.stroke(); x.fillStyle = '#ddd'; x.fillRect(-s * .4, 0, s * .2, s * .15); x.fillRect(s * .2, 0, s * .2, s * .15); };

const GROUNDED = new Set(['house', 'building', 'tree', 'mountain', 'volcano', 'car', 'city', 'bed', 'sign', 'dino', 'cat', 'dog', 'robot', 'alien', 'crowd', 'person', 'fire', 'rocket', 'laptop', 'tv', 'thermometer', 'burger', 'ice', 'gift', 'crown']);
const DEFCOL = {moon: '#d6d1bf', earth: '#3f7fd6', asteroid: '#8a7f72', planet: '#e0874a', sun: '#ffcc33', house: '#f4e0c0', building: '#7d8bb0', ice: '#bfe9ff', car: '#ff5a5a', robot: '#9aa8c8', phone: '#59c3ff'};

// ------------------------------------------------------------------ çöp adam
const POSE = {
  stand: {lean: 0, lA1: -.22, lA2: -.1, rA1: .22, rA2: .1, lL1: -.12, lL2: 0, rL1: .12, rL2: 0, face: 0, eyes: 0, mouth: 1, brow: 0},
  happy: {lean: 0, lA1: -.6, lA2: -.2, rA1: .6, rA2: .2, lL1: -.12, lL2: 0, rL1: .12, rL2: 0, face: 0, eyes: 0, mouth: 6, brow: 0},
  shock: {lean: -.06, lA1: -2.55, lA2: -.35, rA1: 2.55, rA2: .35, lL1: -.32, lL2: .05, rL1: .32, rL2: -.05, face: 0, eyes: 1, mouth: 2, brow: 1},
  point: {lean: -.04, lA1: -.75, lA2: 1.7, rA1: 2.55, rA2: .12, lL1: -.14, lL2: 0, rL1: .14, rL2: 0, face: .6, eyes: 1, mouth: 1, brow: 1},
  shrug: {lean: 0, lA1: -.55, lA2: -1.75, rA1: .55, rA2: 1.75, lL1: -.12, lL2: 0, rL1: .12, rL2: 0, face: 0, eyes: 1, mouth: 1, brow: 0},
  sad: {lean: .08, lA1: -.08, lA2: 0, rA1: .08, rA2: 0, lL1: -.08, lL2: 0, rL1: .08, rL2: 0, face: 0, eyes: 0, mouth: 5, brow: 3},
  think: {lean: 0, lA1: -.6, lA2: 1.3, rA1: .3, rA2: 2.7, lL1: -.12, lL2: 0, rL1: .12, rL2: 0, face: .4, eyes: 0, mouth: 0, brow: 1},
  panic: {lean: 0, lA1: -2.9, lA2: -.6, rA1: 2.2, rA2: 1.2, lL1: -.35, lL2: .3, rL1: .25, rL2: -.4, face: 0, eyes: 1, mouth: 4, brow: 1},
  wave: {lean: 0, lA1: -.22, lA2: -.1, rA1: 2.4, rA2: .6, lL1: -.12, lL2: 0, rL1: .12, rL2: 0, face: 0, eyes: 0, mouth: 6, brow: 0},
  celebrate: {lean: 0, lA1: -2.6, lA2: .2, rA1: 2.6, rA2: -.2, lL1: -.25, lL2: 0, rL1: .25, rL2: 0, face: 0, eyes: 0, mouth: 6, brow: 0},
  phone: {lean: .05, lA1: -.3, lA2: 2.3, rA1: .3, rA2: -2.3, lL1: -.12, lL2: 0, rL1: .12, rL2: 0, face: 0, eyes: 0, mouth: 0, brow: 0},
  facepalm: {lean: .1, lA1: -.2, lA2: 0, rA1: 2.2, rA2: 1.6, lL1: -.12, lL2: 0, rL1: .12, rL2: 0, face: 0, eyes: 0, mouth: 5, brow: 3},
  sit: {lean: -.05, lA1: -.3, lA2: 1.2, rA1: .3, rA2: -1.2, lL1: -1.5, lL2: 1.5, rL1: -1.4, rL2: 1.4, face: .4, eyes: 0, mouth: 1, brow: 0},
  scared: {lean: .12, lA1: -1.3, lA2: 2.4, rA1: 1.3, rA2: -2.4, lL1: -.2, lL2: .25, rL1: .2, rL2: -.25, face: 0, eyes: 1, mouth: 4, brow: 3},
  umbrella: {lean: 0, lA1: -.35, lA2: -.2, rA1: 2.75, rA2: .35, lL1: -.12, lL2: 0, rL1: .12, rL2: 0, face: -.4, eyes: 1, mouth: 4, brow: 1},
};
POSE.look_up = {...POSE.stand, face: 0, eyes: 1, mouth: 2, brow: 1, lA1: -.4, rA1: .4, look: 1};
POSE.cry = {...POSE.sad, mouth: 5, tears: 1};
POSE.angry = {...POSE.stand, lA1: -.5, lA2: 1.8, rA1: .5, rA2: -1.8, mouth: 5, brow: 2};
POSE.sleep = {...POSE.stand, eyes: 2, mouth: 0};
function mixPose(p, q, k) { const r = {}; for (const key in p) r[key] = typeof p[key] === 'number' ? lerp(p[key], q[key] ?? p[key], k) : (k < .5 ? p[key] : q[key] ?? p[key]); return r; }
function runPose(p, dir = 1) {
  const s = Math.sin(p);
  return {lean: .22 * dir, lA1: -.9 * s * dir, lA2: 1.5 * dir, rA1: .9 * s * dir, rA2: 1.5 * dir,
    lL1: .75 * s * dir, lL2: -(.35 + .9 * Math.max(0, Math.sin(p + 1.6))) * dir, rL1: -.75 * s * dir, rL2: -(.35 + .9 * Math.max(0, Math.sin(p + 1.6 + Math.PI))) * dir,
    face: dir, eyes: 1, mouth: 2, brow: 1};
}
function walkPose(p, dir = 1) { const r = runPose(p, dir); return {...r, lean: .04 * dir, lA1: r.lA1 * .5, rA1: r.rA1 * .5, lA2: .3 * dir, rA2: .3 * dir, lL1: r.lL1 * .55, rL1: r.rL1 * .55, lL2: r.lL2 * .4, rL2: r.rL2 * .4, eyes: 0, mouth: 1, brow: 0}; }
const dirv = a => [Math.sin(a), Math.cos(a)];
function stickRaw(px, gy, s, Pz, opt = {}) {
  const L = {torso: 120, ua: 68, fa: 64, th: 82, sh: 80, head: 36};
  const legs = [[Pz.lL1, Pz.lL2], [Pz.rL1, Pz.rL2]].map(([a, b]) => { const d1 = dirv(a), d2 = dirv(a + b); const k = [d1[0] * L.th, d1[1] * L.th]; return [k, [k[0] + d2[0] * L.sh, k[1] + d2[1] * L.sh]]; });
  const footY = Math.max(legs[0][1][1], legs[1][1][1]);
  const hip = [px, gy - footY * s - (opt.hop || 0)];
  const up = [Math.sin(Pz.lean), -Math.cos(Pz.lean)];
  const sh = [hip[0] + up[0] * L.torso * s, hip[1] + up[1] * L.torso * s];
  const hd = [sh[0] + up[0] * (L.head + 12) * s, sh[1] + up[1] * (L.head + 12) * s - (Pz.look ? 4 * s : 0)];
  const col = opt.color || '#fff';
  if (!opt.noShadow) { x.save(); x.globalAlpha = .3; x.fillStyle = '#000'; x.beginPath(); x.ellipse(px, gy + 6 * s, 70 * s, 12 * s, 0, 0, TAU); x.fill(); x.restore(); }
  x.save(); x.lineCap = x.lineJoin = 'round';
  const line = pts => { x.beginPath(); x.moveTo(pts[0][0], pts[0][1]); for (const q of pts.slice(1)) x.lineTo(q[0], q[1]); x.stroke(); };
  const hands = [];
  for (const pass of [0, 1]) {
    x.strokeStyle = pass ? col : 'rgba(10,13,36,.6)'; x.lineWidth = (pass ? 12 : 22) * s;
    for (const [k, f] of legs) line([hip, [hip[0] + k[0] * s, hip[1] + k[1] * s], [hip[0] + f[0] * s, hip[1] + f[1] * s]]);
    line([hip, sh]);
    hands.length = 0;
    for (const [a, b] of [[Pz.lA1, Pz.lA2], [Pz.rA1, Pz.rA2]]) { const d1 = dirv(a), d2 = dirv(a + b);
      const e = [sh[0] + d1[0] * L.ua * s, sh[1] + d1[1] * L.ua * s], h = [e[0] + d2[0] * L.fa * s, e[1] + d2[1] * L.fa * s]; line([sh, e, h]); hands.push(h); }
    circ(hd[0], hd[1], L.head * s); if (pass) { x.fillStyle = opt.headFill || '#121838'; x.fill(); } x.stroke();
  }
  if (opt.hat) { x.fillStyle = opt.hat; x.beginPath(); x.arc(hd[0], hd[1] - 6 * s, L.head * s, Math.PI, 0); x.fill(); x.fillRect(hd[0] - 4 * s, hd[1] - 10 * s, 58 * s, 10 * s); }
  if (opt.helmet) { x.strokeStyle = 'rgba(200,230,255,.9)'; x.lineWidth = 5 * s; x.fillStyle = 'rgba(150,200,255,.18)'; circ(hd[0], hd[1], L.head * 1.6 * s); x.fill(); x.stroke(); }
  // yüz
  const f = Pz.face * 12 * s, ey = hd[1] - 4 * s;
  x.fillStyle = col; x.strokeStyle = col; x.lineWidth = 5 * s;
  if (Pz.eyes > 1.5) { for (const ex of [-13, 13]) { x.beginPath(); x.arc(hd[0] + ex * s + f, ey, 6 * s, .2, Math.PI - .2); x.stroke(); } }
  else { const er = (Pz.eyes > .5 ? 7.5 : 5) * s; for (const ex of [-13, 13]) { circ(hd[0] + ex * s + f, ey - (Pz.look ? 5 * s : 0), er); x.fill(); } }
  if (Pz.brow > .5) for (const ex of [-13, 13]) { const b = Math.round(Pz.brow); const tilt = b === 2 ? (ex < 0 ? 5 : -5) : b === 3 ? (ex < 0 ? -5 : 5) : 0;
    x.beginPath(); x.moveTo(hd[0] + (ex - 8) * s + f, ey - (17 + tilt) * s); x.lineTo(hd[0] + (ex + 8) * s + f, ey - (17 - tilt) * s); x.stroke(); }
  const my = hd[1] + 16 * s, mx = hd[0] + f, m = Math.round(Pz.mouth);
  x.beginPath();
  if (m === 0) { x.moveTo(mx - 8 * s, my); x.lineTo(mx + 8 * s, my); x.stroke(); }
  else if (m === 1) { x.arc(mx, my - 6 * s, 11 * s, .3, Math.PI - .3); x.stroke(); }
  else if (m === 2) { x.ellipse(mx, my, 7 * s, 10 * s, 0, 0, TAU); x.stroke(); }
  else if (m === 4) { x.moveTo(mx - 11 * s, my); for (let i = 1; i <= 4; i++) x.lineTo(mx - 11 * s + i * 5.5 * s, my + (i % 2 ? -4 : 0) * s); x.stroke(); }
  else if (m === 5) { x.arc(mx, my + 9 * s, 10 * s, Math.PI + .4, -.4); x.stroke(); }
  else { x.moveTo(mx - 13 * s, my - 4 * s); x.quadraticCurveTo(mx, my + 16 * s, mx + 13 * s, my - 4 * s); x.closePath(); x.fill(); }
  if (Pz.tears) { x.fillStyle = '#59c3ff'; for (const ex of [-13, 13]) { const k = (opt.t || 0) * 2 % 1; circ(hd[0] + ex * s + f, ey + (10 + k * 40) * s, 4 * s); x.fill(); } }
  if (opt.zzz) { x.fillStyle = '#fff'; x.font = `${40 * s}px Black`; for (let i = 0; i < 3; i++) { const k = ((opt.t || 0) * .6 + i / 3) % 1; x.globalAlpha = 1 - k; x.fillText('z', hd[0] + (40 + k * 60) * s, hd[1] - (30 + k * 120) * s); } x.globalAlpha = 1; }
  x.restore();
  return {head: hd, hands};
}

function heroDraw(h, t, lt, D, scene) {
  if (!h || h.hidden) return;
  const a = h.action || 'stand', posx = {left: .3, center: .5, right: .7, far_left: .18, far_right: .82}[h.pos] ?? .5;
  let px = posx * W, gy = GROUND - 30, s = h.scale || 1.35, Pz, hop = 0, rot = 0, opt = {t, color: h.color || '#fff', hat: h.hat};
  const enter = out(seg(lt, 0, .3));
  if (scene.bg === 'space') {
    const e = (scene.props || []).find(p => p.type === 'earth' || p.type === 'globe' || p.type === 'moon' || p.type === 'planet');
    if (e && e._box) { s = Math.max(.35, e._box.s / 1600); px = e._box.x; gy = e._box.y - e._box.s / 2 + 4 * s; }
    else { opt.helmet = true; gy = 1500 + Math.sin(t * 1.5) * 20; rot = Math.sin(t * .8) * .15; }
  }
  if (a === 'run' || a === 'walk' || a === 'run_left' || a === 'walk_left' || a === 'panic_run') {
    const left = a.endsWith('_left'), speed = a.startsWith('walk') ? 7 : 13, dir = left ? -1 : 1;
    if (a === 'panic_run') { const ph = Math.sin(lt * 1.6); px = W / 2 + ph * W * .3; Pz = runPose(lt * speed, Math.cos(lt * 1.6) > 0 ? 1 : -1); Pz.mouth = 4; }
    else { px = lerp(posx * W - dir * 150, posx * W + dir * 330, seg(lt, 0, Math.max(1, D))); Pz = a.startsWith('walk') ? walkPose(lt * speed, dir) : runPose(lt * speed, dir); }
    hop = Math.abs(Math.sin(lt * speed)) * (a.startsWith('walk') ? 6 : 18);
  } else if (a === 'jump' || a === 'celebrate') { Pz = POSE.celebrate; hop = Math.max(0, Math.sin(lt * 7)) * 70; }
  else if (a === 'dance') { const k = .5 + .5 * Math.sin(lt * 8); Pz = mixPose(POSE.celebrate, {...POSE.happy, lA1: -1.4, rA1: .3}, k); Pz.lean = Math.sin(lt * 8) * .15; hop = Math.max(0, Math.sin(lt * 16)) * 20; }
  else if (a === 'wave') { Pz = {...POSE.wave, rA2: .6 + Math.sin(lt * 10) * .5}; }
  else if (a === 'scared' || a === 'shiver') { Pz = POSE.scared; px += Math.sin(lt * 60) * 5; }
  else if (a === 'fall') { Pz = POSE.panic; rot = ease(seg(lt, .2, .8)) * 1.5; }
  else if (a === 'sleep') { Pz = POSE.sleep; rot = -Math.PI / 2; opt.zzz = true; gy = GROUND - 60; }
  else if (a === 'shock') { Pz = mixPose(POSE.stand, POSE.shock, out(seg(lt, .05, .3))); hop = 50 * Math.sin(Math.PI * seg(lt, .05, .4)); }
  else if (a === 'panic') { Pz = mixPose(POSE.panic, {...POSE.panic, lA1: -2.2, rA1: 2.9}, .5 + .5 * Math.sin(lt * 10)); hop = Math.abs(Math.sin(lt * 10)) * 25; }
  else Pz = POSE[a] || POSE.stand;
  Pz = mixPose(POSE.stand, Pz, a === 'run' || a === 'walk' ? 1 : enter);
  if (h.emotion && EMO[h.emotion]) Pz = {...Pz, ...EMO[h.emotion]};
  // nefes / canlılık
  if (!['run', 'walk', 'run_left', 'walk_left', 'panic_run', 'sleep', 'fall'].includes(a)) { Pz.lean += Math.sin(t * 2.2) * .02; hop += Math.max(0, Math.sin(t * 2.2)) * 3; }
  x.save(); if (rot) { x.translate(px, gy); x.rotate(rot); x.translate(-px, -gy); }
  const res = stickRaw(px, gy, s, Pz, {...opt, hop});
  if (a === 'umbrella') umbrella(res.hands[1], s, t * 9);
  if (a === 'phone') { x.save(); const hm = [(res.hands[0][0] + res.hands[1][0]) / 2, (res.hands[0][1] + res.hands[1][1]) / 2]; x.translate(hm[0], hm[1] - 20 * s); P.phone(70 * s, {t}); x.restore(); }
  x.restore();
  if (a === 'think') { x.save(); x.fillStyle = 'rgba(255,255,255,.9)'; for (const [dx, dy, r] of [[60, -90, 10], [90, -140, 16]]) { circ(res.head[0] + dx * s, res.head[1] + dy * s, r * s); x.fill(); } x.restore(); }
  if (h.say) bubble(res.head[0], res.head[1] - 70 * s, h.say, seg(lt, .15, .4));
}
const EMO = {happy: {mouth: 6, brow: 0, eyes: 0}, sad: {mouth: 5, brow: 3}, shocked: {mouth: 2, eyes: 1, brow: 1}, scared: {mouth: 4, eyes: 1, brow: 3}, angry: {mouth: 5, brow: 2}, sleepy: {eyes: 2, mouth: 0}, confused: {mouth: 0, brow: 2}};
function umbrella(h, s, wob) {
  x.save(); x.translate(h[0], h[1]); x.rotate(Math.sin(wob) * .08);
  x.strokeStyle = '#fff'; x.lineWidth = 8 * s; x.beginPath(); x.moveTo(0, 40 * s); x.lineTo(0, -120 * s); x.stroke();
  x.fillStyle = '#ffcc33'; x.beginPath(); x.moveTo(-150 * s, -110 * s); x.quadraticCurveTo(0, -260 * s, 150 * s, -110 * s);
  for (let i = 0; i < 4; i++) x.quadraticCurveTo(150 * s - (i + .5) * 75 * s, -140 * s, 150 * s - (i + 1) * 75 * s, -110 * s);
  x.fill(); x.lineWidth = 6 * s; x.strokeStyle = '#0a0d24'; x.stroke(); x.restore();
}
function bubble(cx, by, txt, k) {
  if (k <= 0) return; txt = UP(txt); x.save(); x.font = '52px Black'; const w = Math.min(760, x.measureText(txt).width + 70), hgt = 100;
  const bx = clamp(cx - w / 2, 30, W - 30 - w); x.translate(cx, by); x.scale(back(k), back(k)); x.translate(-cx, -by);
  rrect(bx, by - hgt, w, hgt, 40); outlineFill('#fff', 8); poly([[cx - 20, by - 4], [cx + 20, by - 4], [cx, by + 36]]); x.fillStyle = '#fff'; x.fill();
  x.fillStyle = '#0a0d24'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(txt, bx + w / 2, by - hgt / 2, w - 40); x.restore();
}

// ------------------------------------------------------------------ nesne animasyonu
const POSXY = {'sky-left': [.25, .25], 'sky-center': [.5, .24], 'sky-right': [.75, .25], left: [.25, .5], center: [.5, .47], right: [.75, .5],
  'ground-left': [.2, 1], 'ground-center': [.5, 1], 'ground-right': [.8, 1], 'far-left': [.1, 1], 'far-right': [.9, 1]};
const SIZE = {xs: .1, s: .17, m: .28, l: .42, xl: .62, xxl: .85};
function propBox(p) {
  const [u, v] = POSXY[p.pos] || (GROUNDED.has(p.type) ? POSXY['ground-right'] : POSXY['sky-right']);
  const s = (SIZE[p.size] || .28) * W; const grounded = v >= .99;
  return {x: u * W, y: grounded ? GROUND - 18 : SY(v), s, grounded};
}
function drawProp(p, t, lt, D) {
  const fn = P[p.type]; if (!fn) return;
  const b = propBox(p); let {x: px, y: py, s} = b; let sc = 1, rot = 0, alpha = 1, k = lt / Math.max(.5, D);
  const st = {t, lt, D, k, color: p.color, text: p.text, off: p.off, level: p.level, pose: p.pose};
  const an = p.anim || 'idle', d0 = p.delay || 0, lk = Math.max(0, lt - d0);
  if (lt < d0) return;
  switch (an) {
    case 'pop': sc = back(seg(lk, 0, .35)); break;
    case 'grow': sc = lerp(.3, 1, ease(seg(lk, 0, D * .9))); break;
    case 'shrink': sc = lerp(1, .15, ease(seg(lk, 0, D * .9))); break;
    case 'approach': { const q = ease(seg(lk, 0, D * .85)); sc = lerp(.25, 1, q); py = lerp(py - 300, py, q); break; }
    case 'fall': { const q = seg(lk, 0, Math.min(1.2, D * .4)); py = lerp(-400, py, q * q); if (q >= 1) { const b2 = lk - Math.min(1.2, D * .4); py -= Math.abs(Math.sin(b2 * 8)) * 60 * Math.exp(-b2 * 4); } break; }
    case 'rise': py = lerp(H + 300, py, out(seg(lk, 0, Math.min(1.2, D * .5)))); break;
    case 'fly': px = lerp(-.3 * W, 1.3 * W, seg(lk, 0, D)); py += Math.sin(lk * 3) * 20; break;
    case 'fly_left': px = lerp(1.3 * W, -.3 * W, seg(lk, 0, D)); py += Math.sin(lk * 3) * 20; break;
    case 'spin': rot = lk * 2.5; sc = back(seg(lk, 0, .35)); break;
    case 'shake': px += Math.sin(lk * 55) * 10; sc = back(seg(lk, 0, .3)); break;
    case 'float': py += Math.sin(lk * 2.4) * 22; sc = back(seg(lk, 0, .35)); break;
    case 'pulse': sc = back(seg(lk, 0, .3)) * (1 + .08 * Math.sin(lk * 7)); break;
    case 'fade': alpha = 1 - seg(lk, D * .3, D * .9); break;
    case 'orbit': { const a = lk * 1.4; px = W / 2 + Math.cos(a) * W * .32; py = SY(.45) + Math.sin(a) * 160; sc = .85 + .15 * Math.sin(a); break; }
    case 'drain': st.level = 1 - seg(lk, .2, D * .9); sc = back(seg(lk, 0, .3)); break;
    case 'fill': st.level = seg(lk, .2, D * .9); sc = back(seg(lk, 0, .3)); break;
    case 'off': st.off = lk > D * .4; sc = back(seg(lk, 0, .3)); break;
    case 'break': break;
    default: sc = out(seg(lk, 0, .3)) * (1 + .015 * Math.sin(t * 2 + px)); py += Math.sin(t * 1.7 + px) * 4 * (b.grounded ? 0 : 1);
  }
  p._box = {x: px, y: py, s: s * sc};
  x.save(); x.globalAlpha = alpha; x.translate(px, py); x.rotate(rot); x.scale(sc, sc);
  if (an === 'break') {
    const bt = D * .45, q = seg(lk, bt, bt + 1.6);
    if (q <= 0) { x.translate(Math.sin(lk * 50) * 6 * seg(lk, bt - 1, bt), 0); fn(s, st); cracks(s, seg(lk, bt - 1.2, bt), b.grounded); }
    else shards(s, q, p.color || DEFCOL[p.type] || '#c8c0b0', b.grounded);
  } else fn(s, st);
  x.restore();
}
function cracks(s, k, grounded) {
  if (k <= 0) return; const r = rng(99), oy = grounded ? -s * .4 : 0; x.strokeStyle = '#2a1a10'; x.lineWidth = Math.max(3, s * .02); x.lineCap = 'round';
  for (let j = 0; j < 6; j++) { let a = j / 6 * TAU + r(), qx = 0, qy = oy; x.beginPath(); x.moveTo(qx, qy); const n = Math.ceil(6 * k); for (let i = 0; i < n; i++) { a += r() * .9 - .45; qx += Math.cos(a) * s * .08; qy += Math.sin(a) * s * .08; x.lineTo(qx, qy); } x.stroke(); }
}
function shards(s, q, col, grounded) {
  const r = rng(42); const oy = grounded ? -s * .4 : 0;
  x.globalAlpha *= 1 - seg(q, .75, 1);
  for (let i = 0; i < 24; i++) { const a = r() * TAU, v = r() * .8 + .3, rr = (r() * .12 + .05) * s, spin = r() * 4 - 2; const d = out(q) * v * s * 1.1;
    x.save(); x.translate(Math.cos(a) * d * 1.3, oy + Math.sin(a) * d * .7 + q * q * s * .3); x.rotate(spin * q * 3);
    poly(Array.from({length: 6}, (_, j) => [Math.cos(j / 6 * TAU) * rr * (.6 + r() * .5), Math.sin(j / 6 * TAU) * rr * (.6 + r() * .5)])); outlineFill(col, 3, 'rgba(0,0,0,.4)'); x.restore(); }
  if (q < .25) { x.globalAlpha = (1 - q / .25) * .9; const g = x.createRadialGradient(0, oy, 0, 0, oy, s); g.addColorStop(0, '#fff8d0'); g.addColorStop(1, 'rgba(255,160,60,0)'); x.fillStyle = g; circ(0, oy, s); x.fill(); }
}

// ------------------------------------------------------------------ hava / efekt katmanları
function weather(kind, t, lt, D, front) {
  if (!kind) return;
  const r = rng(77);
  if (kind === 'rain' && front) { x.strokeStyle = 'rgba(170,210,255,.6)'; x.lineWidth = 4; for (let i = 0; i < 120; i++) { const sx = r() * W, sp = 1400 + r() * 600, yy = ((r() * H + t * sp) % (H + 100)) - 50; x.beginPath(); x.moveTo(sx, yy); x.lineTo(sx - 12, yy + 40); x.stroke(); } }
  if (kind === 'snow' && front) { x.fillStyle = 'rgba(255,255,255,.9)'; for (let i = 0; i < 110; i++) { const sx = (r() * W + Math.sin(t + i) * 30), yy = (r() * H + t * (80 + r() * 90)) % H; circ(sx, yy, 3 + r() * 5); x.fill(); } }
  if (kind === 'meteors' && front) { for (let i = 0; i < 14; i++) { const t0 = r() * 3, sp = 900 + r() * 500, len = 120 + r() * 160, x0 = r() * 1300 - 100; const tt = lt - t0 * .6; if (tt < 0) continue; const p = (tt * sp) % 2600;
      const mx = x0 + p * .45, my = -200 + p; if (my > GROUND) continue; const g = x.createLinearGradient(mx, my, mx - len * .45, my - len); g.addColorStop(0, '#fff3c4'); g.addColorStop(1, 'rgba(255,120,40,0)');
      x.strokeStyle = g; x.lineWidth = 10; x.lineCap = 'round'; x.beginPath(); x.moveTo(mx, my); x.lineTo(mx - len * .45, my - len); x.stroke(); } }
  if (kind === 'confetti' && front) { for (let i = 0; i < 90; i++) { const sx = r() * W + Math.sin(t * 2 + i) * 40, yy = (r() * H + lt * (300 + r() * 300)) % H; x.save(); x.translate(sx, yy); x.rotate(t * 4 + i); x.fillStyle = `hsl(${r() * 360},90%,60%)`; x.fillRect(-8, -4, 16, 8); x.restore(); } }
  if (kind === 'wind' && front) { x.strokeStyle = 'rgba(255,255,255,.5)'; x.lineWidth = 5; x.lineCap = 'round'; for (let i = 0; i < 16; i++) { const yy = 600 + r() * 1000, sx = ((r() * W + lt * 1500) % (W + 600)) - 300; x.beginPath(); x.moveTo(sx, yy); x.quadraticCurveTo(sx + 100, yy - 30, sx + 220, yy); x.stroke(); } }
  if (kind === 'water_rise' && front) { const lvl = lerp(GROUND + 120, GROUND - 210, ease(seg(lt, .3, D * .9)));
    const g = x.createLinearGradient(0, lvl, 0, H); g.addColorStop(0, 'rgba(60,150,255,.88)'); g.addColorStop(1, 'rgba(20,60,160,.95)'); x.fillStyle = g; x.beginPath(); x.moveTo(0, H);
    const wy = xx => lvl + Math.sin(xx / 70 + t * 4) * 18 + Math.sin(xx / 23 - t * 6) * 6; for (let i = 0; i <= 54; i++) x.lineTo(i / 54 * W, wy(i / 54 * W)); x.lineTo(W, H); x.fill();
    x.strokeStyle = 'rgba(255,255,255,.8)'; x.lineWidth = 6; x.beginPath(); for (let i = 0; i <= 54; i++) { const xx = i / 54 * W; i ? x.lineTo(xx, wy(xx)) : x.moveTo(xx, wy(xx)); } x.stroke(); }
  if (kind === 'darkness' && front) { const k = seg(lt, .2, 1); const g = x.createRadialGradient(W / 2, 1250, 120, W / 2, 1250, 900); g.addColorStop(0, `rgba(0,0,8,${.25 * k})`); g.addColorStop(1, `rgba(0,0,8,${.88 * k})`); x.fillStyle = g; x.fillRect(0, 0, W, H); }
  if (kind === 'heat' && front) { x.fillStyle = `rgba(255,110,30,${.18 + .06 * Math.sin(t * 5)})`; x.fillRect(0, 0, W, H); }
  if (kind === 'fire' && front) { for (let i = 0; i < 9; i++) { x.save(); x.translate(i * 135 + 20, GROUND + 60); P.fire(170 + 40 * Math.sin(i * 3), {t: t + i}); x.restore(); } }
  if (kind === 'ice' && front) { x.fillStyle = 'rgba(200,240,255,.28)'; x.fillRect(0, 0, W, H); x.strokeStyle = 'rgba(255,255,255,.55)'; x.lineWidth = 4; for (let i = 0; i < 12; i++) { const a = r() * W, b = r() * H; x.beginPath(); x.moveTo(a, b); x.lineTo(a + 60, b + 40); x.lineTo(a + 20, b + 100); x.stroke(); } }
}

// ------------------------------------------------------------------ yazılar
function wrap(txt, maxW, size) { x.font = `${size}px Black`; const words = txt.split(' '), lines = []; let cur = '';
  for (const w of words) { const tst = cur ? cur + ' ' + w : w; if (x.measureText(tst).width > maxW && cur) { lines.push(cur); cur = w; } else cur = tst; } if (cur) lines.push(cur); return lines; }
function bigText(txt, cx, cy, size, k, col = '#ffd23f', maxW = 960) {
  if (k <= 0 || !txt) return; txt = UP(txt);
  let lines = wrap(txt, maxW, size); while (lines.length > 3 && size > 50) { size -= 8; lines = wrap(txt, maxW, size); }
  x.save(); x.translate(cx, cy); const sc = back(k); x.scale(sc, sc); x.globalAlpha = clamp(k * 3);
  x.font = `${size}px Black`; x.textAlign = 'center'; x.textBaseline = 'middle'; const lh = size * 1.08, y0 = -(lines.length - 1) * lh / 2;
  lines.forEach((ln, i) => { x.lineJoin = 'round'; x.lineWidth = size * .22; x.strokeStyle = '#0a0d24'; x.strokeText(ln, 0, y0 + i * lh); x.fillStyle = col; x.fillText(ln, 0, y0 + i * lh); });
  x.restore();
}
function pill(txt, cy, k, col = '#ffffff') {
  if (k <= 0) return; txt = UP(txt); x.save(); x.font = '64px Black'; const w = Math.min(980, x.measureText(txt).width + 70);
  x.translate(W / 2, cy); x.scale(back(k), back(k)); rrect(-w / 2, -48, w, 96, 48); x.fillStyle = 'rgba(10,13,36,.78)'; x.fill();
  x.lineWidth = 5; x.strokeStyle = col; x.stroke(); x.fillStyle = col; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(txt, 0, 3, w - 50); x.restore();
}
function fmtNum(n) { const a = Math.abs(n); const s = a >= 100 ? Math.round(n).toLocaleString('tr-TR') : (Math.round(n * 10) / 10).toLocaleString('tr-TR'); return s; }
function counter(cn, lt, D) {
  const k = ease(seg(lt, .2, Math.max(.8, D * .7))), v = lerp(+cn.from || 0, +cn.to || 0, k);
  const txt = `${fmtNum(v)} ${UP(cn.unit || '')}`.trim();
  x.save(); x.globalAlpha = seg(lt, .1, .3);
  pill((cn.label ? UP(cn.label) + ': ' : '') + txt, 560, seg(lt, .1, .4), '#ffd23f'); x.restore();
}
function choices(ch, lt) {
  const cols = ['#ff5a6a', '#4a9dff'];
  ch.slice(0, 2).forEach((txt, i) => { const k = back(seg(lt, .1 + i * .25, .45 + i * .25)); if (k <= 0) return; const cx = i ? 790 : 290, cy = 780;
    x.save(); x.translate(cx, cy); x.scale(k, k); rrect(-230, -170, 460, 340, 36); outlineFill(cols[i], 10);
    bigText(i ? 'B' : 'A', 0, -95, 90, 1, '#fff'); x.font = '50px Black'; x.fillStyle = '#fff'; x.textAlign = 'center'; x.textBaseline = 'middle';
    wrap(UP(txt), 400, 50).slice(0, 3).forEach((ln, j, arr) => x.fillText(ln, 0, 40 + (j - (arr.length - 1) / 2) * 58)); x.restore(); });
  if (lt > .5) pill('YA DA', 572, seg(lt, .5, .8), '#ffd23f');
}
function captions(t) {
  const sc = TL.scenes.find(s => t >= s.t0 && t < s.t1); if (sc && (sc.kind === 'hook' || sc.kind === 'outro')) return;
  const ch = TL.captions.find(c => t >= c.t0 && t < c.t1); if (!ch) return;
  const size = 82; x.font = `${size}px Black`; x.textBaseline = 'middle';
  const words = ch.words.map(w => ({...w, u: UP(w.w), wd: 0})); const sp = x.measureText(' ').width * 2.4;
  words.forEach(w => w.wd = x.measureText(w.u).width);
  const lines = [[]]; let lw = 0; for (const w of words) { if (lw + w.wd > 960 && lines[lines.length - 1].length) { lines.push([]); lw = 0; } lines[lines.length - 1].push(w); lw += w.wd + sp; }
  const lh = 96, y0 = 380 - (lines.length - 1) * lh / 2, appear = back(seg(t, ch.t0, ch.t0 + .12));
  x.save(); x.textAlign = 'center';
  lines.forEach((ln, li) => { const tw = ln.reduce((a, w) => a + w.wd, 0) + sp * (ln.length - 1); let px = W / 2 - tw / 2;
    for (const w of ln) { const on = t >= w.t0, cur = t >= w.t0 && t < w.t1; const pop = cur ? 1 + .06 * (1 - seg(t, w.t0, w.t0 + .15)) : 1;
      x.save(); x.translate(px + w.wd / 2, y0 + li * lh); x.scale(pop * appear, pop * appear); x.lineJoin = 'round'; x.lineWidth = 18; x.strokeStyle = '#0a0d24'; x.strokeText(w.u, 0, 0);
      x.fillStyle = cur ? '#ffd23f' : on ? '#ffffff' : 'rgba(255,255,255,.55)'; x.fillText(w.u, 0, 0); x.restore(); px += w.wd + sp; } });
  x.restore();
}

// ------------------------------------------------------------------ kare
function drawScene(sc, t) {
  const lt = t - sc.t0, D = sc.t1 - sc.t0;
  x.save();
  // kamera: yavaş yakınlaşma + sarsıntı
  let shake = 0; for (const s of (sc.shakes || [])) shake += Math.exp(-Math.max(0, lt - s) * 6) * (lt >= s ? 22 : 0);
  const z = sc.camera === 'zoom' ? 1 + .1 * ease(lt / D) : sc.camera === 'zoom_out' ? 1.12 - .12 * ease(lt / D) : 1 + .02 * Math.sin(t * .5);
  x.translate(W / 2 + Math.sin(t * 70) * shake, 1100 + Math.cos(t * 63) * shake); x.scale(z, z); x.translate(-W / 2, -1100);
  (BG[sc.bg] || BG.night)(t);
  const props = sc.props || [];
  const onGround = p => POSXY[p.pos] ? POSXY[p.pos][1] >= .99 : GROUNDED.has(p.type);
  for (const p of props) if (!onGround(p)) drawProp(p, t, lt, D);
  for (const p of props) if (onGround(p)) drawProp(p, t, lt, D);
  if (sc.friend) heroDraw({color: '#9fe0ff', hat: '#4a9dff', pos: 'right', ...sc.friend}, t, lt, D, sc);
  heroDraw(sc.hero, t, lt, D, sc);
  weather(sc.weather, t, lt, D, true);
  x.restore();
  if (sc.counter) counter(sc.counter, lt, D);
  if (sc.choices) choices(sc.choices, lt);
  if (sc.label && !sc.counter) pill(sc.label, 560, seg(lt, .15, .45));
  if (sc.kind === 'hook') bigText(sc.title, W / 2, 400, 110, seg(lt, .1, .45));
  if (sc.kind === 'outro') { bigText(sc.question || 'SEN OLSAN NE YAPARDIN?', W / 2, 470, 104, seg(lt, .1, .45));
    bigText('YORUMLARA YAZ', W / 2, 700, 72, seg(lt, .9, 1.2), '#ffffff');
    const bob = Math.sin(lt * 7) * 14; x.save(); x.globalAlpha = seg(lt, 1.1, 1.4); x.fillStyle = '#ffd23f'; poly([[540, 860 + bob], [490, 790 + bob], [590, 790 + bob]]); x.fill(); x.restore(); }
}
function frame(t) {
  x.setTransform(1, 0, 0, 1, 0, 0); x.globalAlpha = 1;
  const S = TL.scenes; const sc = S.find(s => t >= s.t0 && t < s.t1) || S[S.length - 1];
  drawScene(sc, t);
  for (const s of S) { const d = t - s.t0; if (s.t0 > 0 && Math.abs(d) < .16) { x.fillStyle = `rgba(10,13,36,${1 - Math.abs(d) / .16})`; x.fillRect(0, 0, W, H); } }
  // patlama flaşları
  for (const s of S) for (const f of (s.flashes || [])) { const d = t - (s.t0 + f); if (d >= 0 && d < .35) { x.fillStyle = `rgba(255,250,235,${.85 * (1 - d / .35)})`; x.fillRect(0, 0, W, H); } }
  captions(t);
  x.save(); x.font = '40px Black'; x.textAlign = 'center'; x.fillStyle = 'rgba(255,255,255,.9)'; x.lineWidth = 8; x.strokeStyle = 'rgba(10,13,36,.6)'; x.lineJoin = 'round';
  x.strokeText(UP(TL.channel || 'YA OLSAYDI?'), W / 2, 150); x.fillText(UP(TL.channel || 'YA OLSAYDI?'), W / 2, 150);
  x.fillStyle = 'rgba(255,255,255,.2)'; x.fillRect(80, 180, 920, 8); x.fillStyle = '#ffd23f'; x.fillRect(80, 180, 920 * clamp(t / TL.duration), 8); x.restore();
}
window.renderFrame = t => { frame(t); return c.toDataURL('image/jpeg', .9); };
fetch('timeline.json').then(r => r.json()).then(async tl => {
  TL = tl; await Promise.all([document.fonts.load('80px Black'), document.fonts.load('40px Semi')]); frame(0); window.READY = true;
});
