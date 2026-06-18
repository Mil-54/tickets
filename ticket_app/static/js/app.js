// Sidebar toggle
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebarOverlay');
const hamburger = document.getElementById('btnHamburger');
if (hamburger) {
  hamburger.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('show');
  });
}
if (overlay) {
  overlay.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
  });
}

// Auto-dismiss flash
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(f => f.remove());
}, 5000);

// Donut chart
function drawDonut(id, data, total) {
  const svg = document.getElementById(id);
  if (!svg || total === 0) return;
  const cx = 60, cy = 60, r = 40, stroke = 18;
  const circ = 2 * Math.PI * r;
  let offset = 0;
  svg.innerHTML = '';
  data.forEach(d => {
    if (d.v === 0) return;
    const pct = d.v / total;
    const dash = pct * circ;
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', cx);
    circle.setAttribute('cy', cy);
    circle.setAttribute('r', r);
    circle.setAttribute('fill', 'none');
    circle.setAttribute('stroke', d.color);
    circle.setAttribute('stroke-width', stroke);
    circle.setAttribute('stroke-dasharray', `${dash} ${circ - dash}`);
    circle.setAttribute('stroke-dashoffset', -offset * circ);
    circle.setAttribute('transform', `rotate(-90 ${cx} ${cy})`);
    svg.appendChild(circle);
    offset += pct;
  });
  const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  text.setAttribute('x', cx);
  text.setAttribute('y', cy + 6);
  text.setAttribute('text-anchor', 'middle');
  text.setAttribute('fill', '#fff');
  text.setAttribute('font-size', '16');
  text.setAttribute('font-weight', 'bold');
  text.textContent = total;
  svg.appendChild(text);
}

// Counter animation
function animateCounter(el, target) {
  let start = 0;
  const duration = 800;
  const step = timestamp => {
    if (!start) start = timestamp;
    const progress = Math.min((timestamp - start) / duration, 1);
    el.textContent = Math.floor(progress * target);
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target;
  };
  requestAnimationFrame(step);
}
