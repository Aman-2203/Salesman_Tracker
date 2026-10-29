// ──────────────────────────────────────
// Salesman Tracker — Main JavaScript
// Enhanced Mobile & UX Interactions
// ──────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initFlashMessages();
  initMobileMenu();
  initLiveClock();
  initGeolocationButtons();
});

// ── Flash messages auto-dismiss ──
function initFlashMessages() {
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(f => {
    const closeBtn = f.querySelector('.flash-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => dismissFlash(f));
    }
    setTimeout(() => dismissFlash(f), 5000);
  });
}

function dismissFlash(el) {
  if (!el) return;
  el.style.opacity = '0';
  el.style.transform = 'translateX(20px)';
  el.style.transition = 'all 0.25s ease';
  setTimeout(() => el.remove(), 250);
}

// ── Mobile sidebar drawer toggle & interactions ──
function initMobileMenu() {
  const toggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const closeBtn = document.getElementById('sidebar-close');
  const toggleButtons = document.querySelectorAll('[data-toggle-sidebar]');

  if (!sidebar) return;

  function openSidebar() {
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  function toggleSidebar() {
    if (sidebar.classList.contains('open')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  }

  if (toggle) {
    toggle.addEventListener('click', e => {
      e.stopPropagation();
      toggleSidebar();
    });
  }

  toggleButtons.forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      toggleSidebar();
    });
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', closeSidebar);
  }

  if (overlay) {
    overlay.addEventListener('click', closeSidebar);
  }

  // Close sidebar on clicking any nav-link on mobile
  const navLinks = sidebar.querySelectorAll('.nav-item');
  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth <= 768) {
        closeSidebar();
      }
    });
  });
}

// ── Live Clock (GMT+5:30 IST) ──
function initLiveClock() {
  const clock = document.getElementById('live-clock');
  const punchClock = document.getElementById('punch-clock');
  if (!clock && !punchClock) return;

  function tick() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-GB', {
      timeZone: 'Asia/Kolkata',
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
    if (clock) clock.textContent = `${timeStr} (IST)`;
    if (punchClock) punchClock.textContent = timeStr;
  }

  tick();
  setInterval(tick, 1000);
}

// ── Geolocation for forms (lat/lng hidden fields) ──
function initGeolocationButtons() {
  document.querySelectorAll('[data-get-location]').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetLat = btn.dataset.lat || 'lat';
      const targetLng = btn.dataset.lng || 'lng';
      btn.disabled = true;
      const originalText = btn.innerHTML;
      btn.innerHTML = '<i class="bi bi-broadcast"></i> Getting location...';

      if (!navigator.geolocation) {
        btn.textContent = 'Geolocation not supported';
        return;
      }

      navigator.geolocation.getCurrentPosition(
        pos => {
          const { latitude, longitude } = pos.coords;
          const latInput = document.getElementById(targetLat) || document.querySelector(`[name="${targetLat}"]`);
          const lngInput = document.getElementById(targetLng) || document.querySelector(`[name="${targetLng}"]`);
          if (latInput) latInput.value = latitude.toFixed(6);
          if (lngInput) lngInput.value = longitude.toFixed(6);

          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-check-circle-fill"></i> Location captured';
          btn.classList.remove('btn-primary', 'btn-ghost');
          btn.classList.add('btn-success');

          const display = document.getElementById('location-display');
          if (display) display.textContent = `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
        },
        () => {
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-x-circle-fill"></i> Failed - retry';
          setTimeout(() => { btn.innerHTML = originalText; }, 3000);
        },
        { enableHighAccuracy: true, timeout: 15000 }
      );
    });
  });
}

// ── Order form: dynamic item rows ──
function addOrderItem() {
  const container = document.getElementById('order-items');
  if (!container) return;

  const idx = container.children.length;
  const row = document.createElement('div');
  row.className = 'order-item-row animate-fade-in';
  row.innerHTML = `
    <input type="text" name="item_name" class="item-name-input" placeholder="Product name" required>
    <input type="number" name="item_qty" class="item-qty-input" placeholder="Qty" min="0.1" step="0.1" value="1" oninput="calcOrderTotal()">
    <input type="number" name="item_price" class="item-price-input" placeholder="Price ₹" min="0" step="0.01" value="0" oninput="calcOrderTotal()">
    <span class="item-subtotal" id="subtotal-${idx}">₹0.00</span>
    <button type="button" class="btn btn-ghost btn-sm" onclick="this.closest('.order-item-row').remove(); calcOrderTotal()" title="Remove item">✕</button>
  `;
  container.appendChild(row);
}

function calcOrderTotal() {
  let total = 0;
  const rows = document.querySelectorAll('.order-item-row');
  rows.forEach((row, i) => {
    const qty = parseFloat(row.querySelector('[name="item_qty"]')?.value || 0);
    const price = parseFloat(row.querySelector('[name="item_price"]')?.value || 0);
    const sub = qty * price;
    total += sub;
    const display = row.querySelector('.item-subtotal') || document.getElementById(`subtotal-${i}`);
    if (display) display.textContent = `₹${sub.toFixed(2)}`;
  });
  const totalEl = document.getElementById('order-total');
  if (totalEl) totalEl.textContent = `₹${total.toFixed(2)}`;
}

// ── Beat plan: customer selection ──
function toggleCustomerSelect(checkbox) {
  const card = checkbox.closest('.customer-select-card');
  if (!card) return;
  card.classList.toggle('selected', checkbox.checked);
}

// ── Confirmation dialogs ──
function confirmAction(form, message) {
  if (confirm(message || 'Are you sure?')) {
    form.submit();
  }
}
