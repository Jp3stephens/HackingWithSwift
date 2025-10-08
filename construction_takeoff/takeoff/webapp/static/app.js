const form = document.getElementById('takeoff-form');
const tradeSelect = document.getElementById('trade');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('drawing-file');
const dropZoneTitle = document.getElementById('drop-zone-title');
const dropZoneSubtitle = document.getElementById('drop-zone-subtitle');
const loadingState = document.getElementById('loading-state');
const resultsSection = document.getElementById('results');
const errorBanner = document.getElementById('error-banner');
const downloadBtn = document.getElementById('download-btn');
const lineItemsBody = document.getElementById('line-items');
const reviewList = document.getElementById('review-items');
const reviewEmpty = document.getElementById('review-empty');
const metaDrawings = document.getElementById('meta-drawings');
const metaElements = document.getElementById('meta-elements');
const metaLines = document.getElementById('meta-lines');
const summaryMaterial = document.getElementById('summary-material-cost');
const summaryLabor = document.getElementById('summary-labor-cost');
const summaryTotal = document.getElementById('summary-total-cost');
const summaryHours = document.getElementById('summary-labor-hours');
const heroMaterial = document.getElementById('hero-material-cost');
const heroLabor = document.getElementById('hero-labor-cost');
const heroTotal = document.getElementById('hero-total-cost');
const heroReview = document.getElementById('hero-review-summary');
const markupSection = document.getElementById('markup-section');
const markupGallery = document.getElementById('markup-gallery');
const markupMetadataList = document.getElementById('markup-metadata');
const markupEmpty = document.getElementById('markup-empty');
const markupPreviewContainer = document.getElementById('markup-preview-container');
const markupInfo = document.getElementById('markup-info');
const markupEmptyDefault = markupEmpty ? markupEmpty.textContent : '';

const PDF_JS_SRC = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.9.179/build/pdf.min.js';
const PDF_JS_WORKER = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.9.179/build/pdf.worker.min.js';
let pdfjsLoader = null;

let downloadUrl = null;

disableDownload();

function disableDownload() {
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
    downloadUrl = null;
  }
  downloadBtn.href = '#';
  downloadBtn.classList.add('pointer-events-none', 'opacity-40');
  downloadBtn.setAttribute('aria-disabled', 'true');
}

function enableDownload(csv, tradeLabel) {
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
  }
  const blob = new Blob([csv], { type: 'text/csv' });
  downloadUrl = URL.createObjectURL(blob);
  downloadBtn.href = downloadUrl;
  downloadBtn.download = `${tradeLabel.toLowerCase().replace(/\s+/g, '-')}-estimate.csv`;
  downloadBtn.classList.remove('pointer-events-none', 'opacity-40');
  downloadBtn.setAttribute('aria-disabled', 'false');
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value ?? 0);
}

function formatNumber(value, decimals = 2) {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value ?? 0);
}

function resetDropzone() {
  dropZoneTitle.textContent = 'Drag & drop files here';
  dropZoneSubtitle.textContent = 'PDF, JSON, or ZIP exports up to 25MB.';
}

function updateDropzone(file) {
  if (!file) {
    resetDropzone();
    return;
  }
  const sizeMb = file.size ? (file.size / (1024 * 1024)).toFixed(2) : '0.00';
  dropZoneTitle.textContent = file.name;
  dropZoneSubtitle.textContent = `${sizeMb} MB • ${file.type || 'application/octet-stream'}`;
}

function setLoading(isLoading) {
  if (isLoading) {
    loadingState.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    errorBanner.classList.add('hidden');
    disableDownload();
  } else {
    loadingState.classList.add('hidden');
  }
}

function setError(message) {
  if (message) {
    errorBanner.textContent = message;
    errorBanner.classList.remove('hidden');
  } else {
    errorBanner.textContent = '';
    errorBanner.classList.add('hidden');
  }
}

function clearTable() {
  lineItemsBody.innerHTML = '';
}

function clearReview() {
  reviewList.innerHTML = '';
}

function renderLineItems(items) {
  clearTable();
  if (!items.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 8;
    cell.className = 'px-5 py-5 text-center text-sm text-slate-300';
    cell.textContent = 'No line items were generated for the selected trade.';
    row.appendChild(cell);
    lineItemsBody.appendChild(row);
    return;
  }

  items.forEach((item) => {
    const row = document.createElement('tr');
    row.className = 'hover:bg-slate-800/40 transition';

    const cells = [
      { value: item.description, align: 'text-left' },
      { value: formatNumber(item.quantity, 2), align: 'text-right' },
      { value: item.unit, align: 'text-right' },
      { value: formatCurrency(item.material_unit_cost), align: 'text-right' },
      { value: formatCurrency(item.material_cost), align: 'text-right' },
      { value: formatNumber(item.labor_hours, 2), align: 'text-right' },
      { value: formatCurrency(item.labor_rate_per_hour), align: 'text-right' },
      { value: formatCurrency(item.labor_cost), align: 'text-right' },
    ];

    cells.forEach(({ value, align }) => {
      const cell = document.createElement('td');
      cell.className = `${align} px-5 py-4 text-sm text-slate-200`;
      cell.textContent = value;
      row.appendChild(cell);
    });

    lineItemsBody.appendChild(row);
  });
}

function renderReview(items) {
  clearReview();
  if (!items.length) {
    reviewEmpty.classList.remove('hidden');
    return;
  }

  reviewEmpty.classList.add('hidden');

  const severityStyles = {
    info: 'border-sky-400/30 bg-sky-500/10 text-sky-100',
    warning: 'border-amber-400/30 bg-amber-500/10 text-amber-100',
    critical: 'border-rose-400/30 bg-rose-500/10 text-rose-100',
  };

  items.forEach((item) => {
    const li = document.createElement('li');
    li.className = `rounded-2xl border px-4 py-3 text-sm ${severityStyles[item.severity] || severityStyles.info}`;

    const title = document.createElement('div');
    title.className = 'flex items-center gap-2 font-semibold';
    title.innerHTML = `<span class="inline-flex h-2.5 w-2.5 rounded-full bg-current"></span>${item.severity.toUpperCase()}`;

    const message = document.createElement('p');
    message.className = 'mt-1 leading-relaxed';
    message.textContent = item.message;

    li.appendChild(title);
    li.appendChild(message);
    reviewList.appendChild(li);
  });
}

async function renderResults(data) {
  summaryMaterial.textContent = formatCurrency(data.metrics.material_cost);
  summaryLabor.textContent = formatCurrency(data.metrics.labor_cost);
  summaryTotal.textContent = formatCurrency(data.metrics.total_cost);
  summaryHours.textContent = formatNumber(data.metrics.labor_hours, 2);

  heroMaterial.textContent = formatCurrency(data.metrics.material_cost);
  heroLabor.textContent = formatCurrency(data.metrics.labor_cost);
  heroTotal.textContent = formatCurrency(data.metrics.total_cost);
  heroReview.textContent = data.review_summary;

  metaDrawings.textContent = `${data.drawing_count} ${data.drawing_count === 1 ? 'drawing' : 'drawings'}`;
  metaElements.textContent = `${data.element_count} ${data.element_count === 1 ? 'element' : 'elements'}`;
  metaLines.textContent = `${data.line_item_count} ${data.line_item_count === 1 ? 'line item' : 'line items'}`;

  renderLineItems(data.line_items);
  renderReview(data.review);
  await renderMarkups(data.markups || {});

  enableDownload(data.csv, data.trade_label);

  resultsSection.classList.remove('hidden');
}

function renderMarkupMetadataList(metadata) {
  if (!metadata.length) {
    return;
  }

  metadata.forEach((entry) => {
    const item = document.createElement('li');
    item.className = 'rounded-xl border border-slate-600/60 bg-slate-900/60 p-3 text-xs text-slate-200 shadow-inner shadow-black/30';

    const source = entry.source ? entry.source.split('#')[0] : 'uploaded drawing';
    const bbox = Array.isArray(entry.bounding_box)
      ? entry.bounding_box.map((value) => Number(value).toFixed(2)).join(', ')
      : '—';

    item.innerHTML = `
      <div class="font-semibold text-slate-100">${entry.element_id} · ${entry.category}</div>
      <div class="mt-1 text-slate-300">${source}</div>
      <div class="mt-1 text-slate-400">Bounds: [${bbox}]</div>
    `;

    markupMetadataList.appendChild(item);
  });
}

function decodeDataUrl(dataUrl) {
  if (!dataUrl || typeof dataUrl !== 'string') {
    return new Uint8Array();
  }

  const parts = dataUrl.split(',');
  const base64 = parts.length > 1 ? parts[1] : parts[0];
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

async function ensurePdfJs() {
  if (pdfjsLoader) {
    return pdfjsLoader;
  }

  if (window.pdfjsLib) {
    window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDF_JS_WORKER;
    pdfjsLoader = Promise.resolve(window.pdfjsLib);
    return pdfjsLoader;
  }

  pdfjsLoader = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = PDF_JS_SRC;
    script.async = true;
    script.onload = () => {
      if (window.pdfjsLib) {
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDF_JS_WORKER;
        resolve(window.pdfjsLib);
      } else {
        pdfjsLoader = null;
        reject(new Error('PDF.js failed to load.'));
      }
    };
    script.onerror = () => {
      pdfjsLoader = null;
      reject(new Error('PDF.js failed to load.'));
    };
    document.head.appendChild(script);
  });

  return pdfjsLoader;
}

function createHighlightDiv(entry, overlay, width, height) {
  if (!entry || !overlay) {
    return;
  }

  const coords = Array.isArray(entry.bounding_box)
    ? entry.bounding_box.map((value) => Number(value))
    : [];

  if (coords.length !== 4 || coords.some((value) => Number.isNaN(value))) {
    return;
  }

  const [x1, y1, x2, y2] = coords;
  const left = Math.min(x1, x2) * width;
  const top = Math.min(y1, y2) * height;
  const rectWidth = Math.abs(x2 - x1) * width;
  const rectHeight = Math.abs(y2 - y1) * height;

  if (!rectWidth || !rectHeight) {
    return;
  }

  const highlight = document.createElement('div');
  highlight.style.position = 'absolute';
  highlight.style.pointerEvents = 'none';
  highlight.style.left = `${left}px`;
  highlight.style.top = `${top}px`;
  highlight.style.width = `${rectWidth}px`;
  highlight.style.height = `${rectHeight}px`;
  highlight.style.border = '2px solid rgba(56,189,248,0.85)';
  highlight.style.background = 'rgba(56,189,248,0.22)';
  highlight.style.borderRadius = '12px';
  highlight.style.boxShadow = '0 18px 32px rgba(56,189,248,0.28)';
  highlight.title = `${entry.element_id || 'element'} · ${entry.category || ''}`;
  overlay.appendChild(highlight);
}

async function renderMarkupPreview(preview, pdfjsLib) {
  if (!markupPreviewContainer) {
    return;
  }

  const card = document.createElement('div');
  card.className = 'space-y-4 rounded-2xl border border-white/10 bg-slate-900/60 p-4 shadow-inner shadow-black/40';

  const header = document.createElement('div');
  header.className = 'flex items-center justify-between gap-3';

  const title = document.createElement('h4');
  title.className = 'text-sm font-semibold text-slate-100 truncate';
  title.textContent = preview.filename || (preview.source ? preview.source.split('/').pop() : 'Drawing preview');
  title.title = preview.source || preview.filename || 'Drawing preview';
  header.appendChild(title);

  const pageCount = Array.isArray(preview.pages) ? preview.pages.length : 0;
  const badge = document.createElement('span');
  badge.className = 'rounded-full border border-slate-600/60 px-3 py-1 text-xs text-slate-300';
  badge.textContent = `${pageCount} page${pageCount === 1 ? '' : 's'}`;
  header.appendChild(badge);

  card.appendChild(header);

  const status = document.createElement('p');
  status.className = 'text-xs text-slate-400';
  status.textContent = 'Rendering preview…';
  card.appendChild(status);

  const pagesContainer = document.createElement('div');
  pagesContainer.className = 'space-y-4';
  card.appendChild(pagesContainer);

  markupPreviewContainer.appendChild(card);

  try {
    const pdfBytes = decodeDataUrl(preview.data_url);
    const pdf = await pdfjsLib.getDocument({ data: pdfBytes }).promise;

    if (!pageCount) {
      status.textContent = 'No markup highlights were captured for this drawing.';
      return;
    }

    status.classList.add('hidden');
    status.textContent = '';

    for (const pageInfo of preview.pages) {
      const pageSection = document.createElement('div');
      pageSection.className = 'space-y-2';

      const pageTitle = document.createElement('div');
      pageTitle.className = 'text-xs font-semibold uppercase tracking-wide text-slate-300';
      pageTitle.textContent = `Page ${pageInfo.page_number}`;
      pageSection.appendChild(pageTitle);

      const canvasWrapper = document.createElement('div');
      canvasWrapper.className = 'relative overflow-hidden rounded-xl border border-white/10 bg-slate-950/40 shadow-inner shadow-black/30';

      const canvas = document.createElement('canvas');
      canvas.className = 'w-full';
      const overlay = document.createElement('div');
      overlay.className = 'absolute inset-0';
      overlay.style.pointerEvents = 'none';

      canvasWrapper.appendChild(canvas);
      canvasWrapper.appendChild(overlay);
      pageSection.appendChild(canvasWrapper);
      pagesContainer.appendChild(pageSection);

      const page = await pdf.getPage(pageInfo.page_number);
      const viewport = page.getViewport({ scale: 1.3 });
      const context = canvas.getContext('2d');
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      canvas.style.width = '100%';
      canvas.style.height = 'auto';

      await page.render({ canvasContext: context, viewport }).promise;

      const { width, height } = canvas;
      (pageInfo.elements || []).forEach((entry) => createHighlightDiv(entry, overlay, width, height));
    }
  } catch (error) {
    status.classList.remove('hidden');
    status.className = 'text-xs text-rose-200';
    status.textContent = `Failed to render preview: ${error.message || error}`;
  }
}

async function renderMarkups(markups) {
  if (!markupSection) {
    return;
  }

  const overlays = Array.isArray(markups.overlays) ? markups.overlays : [];
  const previews = Array.isArray(markups.previews) ? markups.previews : [];
  const metadata = Array.isArray(markups.metadata) ? markups.metadata : [];
  const message = markups.message || '';
  const supported = markups.supported !== false && (overlays.length > 0 || previews.length > 0);

  markupGallery.innerHTML = '';
  if (markupPreviewContainer) {
    markupPreviewContainer.innerHTML = '';
  }
  markupMetadataList.innerHTML = '';

  if (markupInfo) {
    markupInfo.textContent = '';
    markupInfo.classList.add('hidden');
  }

  if (markupEmpty) {
    markupEmpty.textContent = markupEmptyDefault;
    markupEmpty.classList.add('hidden');
  }

  markupSection.classList.remove('hidden');

  if (!supported) {
    if (markupEmpty) {
      markupEmpty.textContent = message || markupEmptyDefault;
      markupEmpty.classList.remove('hidden');
    }
    if (markupInfo && message) {
      markupInfo.textContent = message;
      markupInfo.classList.remove('hidden');
    }
    renderMarkupMetadataList(metadata);
    return;
  }

  if (markupInfo && message) {
    markupInfo.textContent = message;
    markupInfo.classList.remove('hidden');
  }

  overlays.forEach((overlay) => {
    const card = document.createElement('div');
    card.className = 'space-y-3 rounded-2xl border border-white/10 bg-slate-900/60 p-4 shadow-inner shadow-black/40';

    const header = document.createElement('div');
    header.className = 'flex items-center justify-between gap-3';

    const title = document.createElement('h4');
    title.className = 'text-sm font-semibold text-slate-100 truncate';
    title.title = overlay.source || overlay.filename;
    title.textContent = overlay.filename;

    const downloadLink = document.createElement('a');
    downloadLink.href = overlay.data_url;
    downloadLink.download = overlay.filename;
    downloadLink.className = 'inline-flex items-center gap-1 rounded-full border border-slate-600/60 px-3 py-1 text-xs font-semibold text-slate-200 transition hover:border-sky-400/80 hover:text-white';
    downloadLink.innerHTML = '<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M7.5 10.5L12 15m0 0l4.5-4.5M12 15V3" /></svg>PDF';

    header.appendChild(title);
    header.appendChild(downloadLink);

    const frame = document.createElement('iframe');
    frame.src = overlay.data_url;
    frame.title = `Markup overlay ${overlay.filename}`;
    frame.className = 'h-64 w-full rounded-xl border border-white/10 bg-white/5';

    card.appendChild(header);
    card.appendChild(frame);

    markupGallery.appendChild(card);
  });

  if (previews.length && markupPreviewContainer) {
    try {
      const pdfjsLib = await ensurePdfJs();
      for (const preview of previews) {
        await renderMarkupPreview(preview, pdfjsLib);
      }
    } catch (error) {
      const warning = document.createElement('p');
      warning.className = 'rounded-2xl border border-amber-400/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100';
      warning.textContent = error.message || 'Unable to load interactive preview.';
      markupPreviewContainer.appendChild(warning);
    }
  }

  renderMarkupMetadataList(metadata);
}

function validateForm() {
  if (!tradeSelect.value) {
    throw new Error('Select a trade before running the takeoff.');
  }
  if (!fileInput.files || !fileInput.files.length) {
    throw new Error('Upload a drawing export to continue.');
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    validateForm();
  } catch (error) {
    setError(error.message);
    return;
  }

  setLoading(true);
  setError('');

  const formData = new FormData();
  formData.append('trade', tradeSelect.value);
  formData.append('drawing', fileInput.files[0]);

  try {
    const response = await fetch('/api/takeoff', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let message = 'Failed to run takeoff. Please try again.';
      try {
        const payload = await response.json();
        message = payload.detail || message;
      } catch (err) {
        // ignore
      }
      throw new Error(message);
    }

    const data = await response.json();
    await renderResults(data);
    setError('');
  } catch (error) {
    setError(error.message || 'Unexpected error.');
    disableDownload();
  } finally {
    setLoading(false);
  }
});

fileInput.addEventListener('change', (event) => {
  const file = event.target.files[0];
  updateDropzone(file);
});

dropZone.addEventListener('click', () => {
  fileInput.click();
});

dropZone.addEventListener('dragover', (event) => {
  event.preventDefault();
  dropZone.classList.add('border-sky-400', 'bg-slate-900/80');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('border-sky-400', 'bg-slate-900/80');
});

dropZone.addEventListener('drop', (event) => {
  event.preventDefault();
  dropZone.classList.remove('border-sky-400', 'bg-slate-900/80');
  const [file] = event.dataTransfer.files;
  if (!file) {
    return;
  }
  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  fileInput.files = dataTransfer.files;
  updateDropzone(file);
});

resetDropzone();
