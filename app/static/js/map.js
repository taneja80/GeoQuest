/* ===================================================
   GeoQuest — Interactive World Map
   Leaflet.js + CartoDB Dark Matter tiles
   Markers colored by continent, sized by population
   =================================================== */

// --- Continent config ---
const CONTINENT_COLORS = {
  'Africa':        '#f59e0b',
  'Asia':          '#22d3ee',
  'Europe':        '#818cf8',
  'North America': '#4ade80',
  'South America': '#c084fc',
  'Oceania':       '#fb923c',
  'Antarctica':    '#94a3b8',
  'Unknown':       '#6b7280',
};

const CONTINENT_EMOJIS = {
  'Africa': '🌍', 'Asia': '🏯', 'Europe': '🗼',
  'North America': '🗽', 'South America': '🌿',
  'Oceania': '🦘', 'Antarctica': '🧊',
};

// --- State ---
let map;
let allMarkers   = [];
let activeMarker = null;

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  loadCountries();
});

function initMap() {
  map = L.map('map', {
    center: [20, 10],
    zoom: 2,
    minZoom: 2,
    maxZoom: 10,
    zoomControl: false,
    worldCopyJump: true,
  });

  L.control.zoom({ position: 'bottomright' }).addTo(map);

  // CartoDB Dark Matter (no labels) — free, no API key
  L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png',
    {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> ' +
        '&copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19,
    }
  ).addTo(map);

  // Close info panel on map click
  map.on('click', () => closeInfoPanel());
}

// --- Load country data from Flask API ---
function loadCountries() {
  setLoading(true);
  fetch('/api/countries')
    .then(r => r.json())
    .then(countries => {
      setLoading(false);
      if (!countries.length) {
        document.getElementById('map-status').textContent =
          'No country data found. Try running flask update-data first.';
        return;
      }
      buildMarkers(countries);
      buildFilters(countries);
      buildLegend();
      updateStatBar(countries);
      initSearch(countries);
    })
    .catch(err => {
      setLoading(false);
      console.error('Map load error:', err);
      document.getElementById('map-status').textContent =
        'Failed to load country data.';
    });
}

// --- Helpers ---
function getColor(continent) {
  return CONTINENT_COLORS[continent] || CONTINENT_COLORS['Unknown'];
}

function getRadius(pop) {
  if (!pop || pop < 1000) return 5;
  const r = (Math.log10(pop) - 3) * 2.4;
  return Math.max(5, Math.min(22, r));
}

function fmtPop(n) {
  if (!n) return 'N/A';
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return Math.round(n / 1e3) + 'K';
  return n.toString();
}

function fmtArea(n) {
  if (!n) return 'N/A';
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 }) + ' km²';
}

function setLoading(on) {
  document.getElementById('map-status').style.display = on ? 'flex' : 'none';
}

// --- Markers ---
function buildMarkers(countries) {
  countries.forEach(country => {
    const color  = getColor(country.continent);
    const radius = getRadius(country.population);

    const marker = L.circleMarker([country.lat, country.lng], {
      radius,
      fillColor: color,
      fillOpacity: 0.82,
      color: color,
      weight: 1.5,
      opacity: 0.95,
    });

    marker._data = country;
    marker._radius = radius;
    marker._color  = color;

    // Hover tooltip
    marker.bindTooltip(buildTooltip(country), {
      direction: 'top',
      offset: L.point(0, -radius - 6),
      className: 'gq-tooltip',
      sticky: false,
    });

    marker.on('mouseover', function () {
      if (this !== activeMarker) {
        this.setStyle({ fillOpacity: 1, weight: 2.5 });
        this.setRadius(radius + 4);
      }
    });

    marker.on('mouseout', function () {
      if (this !== activeMarker) {
        this.setStyle({ fillOpacity: 0.82, weight: 1.5 });
        this.setRadius(radius);
      }
    });

    marker.on('click', function (e) {
      L.DomEvent.stopPropagation(e);
      selectMarker(this);
    });

    marker.addTo(map);
    allMarkers.push(marker);
  });
}

function buildTooltip(c) {
  return `
    <div class="gq-tip-inner">
      ${c.flag_svg ? `<img src="${c.flag_svg}" class="tip-flag" alt="">` : ''}
      <div>
        <strong>${c.name}</strong>
        ${c.capital ? `<br><small>🏙️ ${c.capital}</small>` : ''}
      </div>
    </div>`;
}

function selectMarker(marker) {
  // Deselect previous
  if (activeMarker && activeMarker !== marker) {
    const prev = activeMarker;
    prev.setStyle({ fillOpacity: 0.82, weight: 1.5, color: prev._color });
    prev.setRadius(prev._radius);
  }
  activeMarker = marker;
  // Highlight selected
  marker.setStyle({ fillOpacity: 1, weight: 3, color: '#ffffff' });
  marker.setRadius(marker._radius + 5);
  showInfoPanel(marker._data);

  // Fly to, slightly offset left so panel doesn't cover marker
  map.flyTo(
    [marker._data.lat, marker._data.lng],
    Math.max(map.getZoom(), 4),
    { duration: 1, easeLinearity: 0.4 }
  );
}

function deselectMarker() {
  if (activeMarker) {
    activeMarker.setStyle({ fillOpacity: 0.82, weight: 1.5, color: activeMarker._color });
    activeMarker.setRadius(activeMarker._radius);
    activeMarker = null;
  }
}

// --- Info Panel ---
function showInfoPanel(c) {
  const panel = document.getElementById('info-panel');
  const color = getColor(c.continent);
  const emoji = CONTINENT_EMOJIS[c.continent] || '🌍';

  document.getElementById('panel-body').innerHTML = `
    <div class="panel-flag-wrap">
      ${c.flag_svg
        ? `<img src="${c.flag_svg}" class="panel-flag" alt="Flag of ${c.name}">`
        : `<div class="panel-flag-ph">🌐</div>`}
    </div>
    <div class="panel-name">${c.name}</div>
    <span class="panel-continent-tag" style="background:${color}22;color:${color};border:1px solid ${color}44">
      ${emoji} ${c.continent}
    </span>

    <div class="panel-stats">
      ${c.capital    ? `<div class="pstat"><div class="pstat-icon">🏙️</div><div><div class="pstat-label">Capital</div><div class="pstat-val">${c.capital}</div></div></div>` : ''}
      ${c.population ? `<div class="pstat"><div class="pstat-icon">👥</div><div><div class="pstat-label">Population</div><div class="pstat-val">${fmtPop(c.population)}</div></div></div>` : ''}
      ${c.area       ? `<div class="pstat"><div class="pstat-icon">📐</div><div><div class="pstat-label">Area</div><div class="pstat-val">${fmtArea(c.area)}</div></div></div>` : ''}
    </div>

    <a href="${c.url}" class="panel-link-btn">
      Explore ${c.name} →
    </a>
  `;

  panel.classList.add('open');
}

function closeInfoPanel() {
  document.getElementById('info-panel').classList.remove('open');
  deselectMarker();
}

// --- Continent Filter ---
function buildFilters(countries) {
  const continents = ['All', ...new Set(
    countries.map(c => c.continent).filter(Boolean).sort()
  )];
  const wrap = document.getElementById('filter-wrap');

  wrap.innerHTML = continents.map(cont => {
    const color = cont === 'All' ? null : getColor(cont);
    const style = color
      ? `style="border-color:${color}55;color:${color}"`
      : '';
    return `<button class="gq-filter ${cont === 'All' ? 'active' : ''}"
                    data-continent="${cont}" ${style}>
              ${CONTINENT_EMOJIS[cont] || ''} ${cont}
            </button>`;
  }).join('');

  wrap.addEventListener('click', e => {
    const btn = e.target.closest('.gq-filter');
    if (!btn) return;
    wrap.querySelectorAll('.gq-filter').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    applyFilter(btn.dataset.continent);
  });
}

function applyFilter(continent) {
  closeInfoPanel();
  allMarkers.forEach(m => {
    const visible = continent === 'All' || m._data.continent === continent;
    m.setStyle({ fillOpacity: visible ? 0.82 : 0.06, opacity: visible ? 0.95 : 0.15 });
  });

  if (continent !== 'All') {
    const visible = allMarkers.filter(m => m._data.continent === continent);
    if (visible.length) {
      const group = L.featureGroup(visible);
      map.flyToBounds(group.getBounds().pad(0.3), { duration: 1.4 });
    }
  } else {
    map.flyTo([20, 10], 2, { duration: 1.2 });
  }
}

// --- Legend ---
function buildLegend() {
  const wrap = document.getElementById('legend-wrap');
  wrap.innerHTML = Object.entries(CONTINENT_COLORS)
    .filter(([k]) => k !== 'Unknown')
    .map(([cont, color]) =>
      `<div class="leg-item">
         <span class="leg-dot" style="background:${color};box-shadow:0 0 6px ${color}88"></span>
         <span class="leg-label">${cont}</span>
       </div>`
    ).join('');
}

// --- Stat bar ---
function updateStatBar(countries) {
  document.getElementById('stat-total').textContent = countries.length;
  const conts = new Set(countries.map(c => c.continent).filter(c => c && c !== 'Unknown'));
  document.getElementById('stat-conts').textContent = conts.size;
}

// --- Search ---
function initSearch(countries) {
  const input   = document.getElementById('map-search-input');
  const results = document.getElementById('map-search-results');

  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (q.length < 2) { results.innerHTML = ''; results.hidden = true; return; }

    const hits = countries
      .filter(c => c.name.toLowerCase().includes(q))
      .slice(0, 7);

    if (!hits.length) { results.innerHTML = ''; results.hidden = true; return; }

    results.innerHTML = hits.map(c => `
      <div class="sr-item" data-name="${c.name}">
        ${c.flag_svg ? `<img src="${c.flag_svg}" class="sr-flag" alt="">` : '<span class="sr-flag-ph">🌐</span>'}
        <span class="sr-name">${c.name}</span>
        ${c.capital ? `<span class="sr-cap">${c.capital}</span>` : ''}
      </div>`).join('');
    results.hidden = false;
  });

  results.addEventListener('click', e => {
    const item = e.target.closest('.sr-item');
    if (!item) return;
    const name = item.dataset.name;
    const marker = allMarkers.find(m => m._data.name === name);
    if (marker) selectMarker(marker);
    input.value = name;
    results.hidden = true;
  });

  document.addEventListener('click', e => {
    if (!e.target.closest('#map-search-wrap')) results.hidden = true;
  });

  input.addEventListener('keydown', e => {
    if (e.key === 'Escape') { results.hidden = true; input.blur(); }
  });
}
