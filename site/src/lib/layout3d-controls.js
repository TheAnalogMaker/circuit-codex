// Load Three.js, layout data and a WebGL context only after opening the view.
export function initLayout3D(root) {
  if (root.dataset.initialized) return;
  root.dataset.initialized = 'true';
  const $ = (selector) => root.querySelector(selector);
  const stage = $('[data-stage]');
  const overlay = $('[data-loading]');
  const status = $('[data-status]');
  const retry = $('[data-retry]');
  const fallback = $('[data-fallback]');
  const select = $('[data-component]');
  const explode = $('[data-explode]');
  const layers = [...root.querySelectorAll('[data-layer]')];
  const lifetime = new AbortController();
  const listen = (target, event, fn) => target.addEventListener(event, fn, { signal: lifetime.signal });
  let scene = null;
  let model = null;
  let pending = false;
  let request = null;
  let destroyed = false;

  function enableControls(enabled) {
    root.querySelectorAll('[data-controls] button, [data-controls] fieldset, [data-explode], [data-component]')
      .forEach((control) => { control.disabled = !enabled; });
  }

  function showSelection(component) {
    select.value = component?.id || '';
    $('[data-part-empty]').hidden = !!component;
    $('[data-part-detail]').hidden = !component;
    $('[data-clear]').hidden = !component;
    const list = $('[data-leads-list]');
    list.replaceChildren();
    const empty = $('[data-leads-empty]');
    if (!component) {
      empty.textContent = 'Choose a component to follow the leads that meet it.';
      empty.hidden = false;
      list.hidden = true;
      return;
    }
    $('[data-part-value]').textContent = `${component.ref || component.id} · ${component.value || component.label}`;
    $('[data-part-role]').textContent = component.role || component.label;
    const link = $('[data-bom-link]');
    link.hidden = !component.ref;
    link.href = component.ref ? `#part-${encodeURIComponent(component.ref)}` : '#parts';
    const attached = model.connections.filter((wire) => wire.fromOwner === component.id || wire.toOwner === component.id);
    // Display actual fork landings separately, without claiming an entire net.
    for (const wire of attached) {
      const item = document.createElement('li');
      item.textContent = `${wire.from} → ${wire.to}${wire.kind === 'heater' ? ' · heater' : ''}`;
      list.append(item);
    }
    list.hidden = attached.length === 0;
    empty.hidden = attached.length > 0;
    empty.textContent = 'No separately routed lead meets this part in the reference layout.';
  }

  function fail(error) {
    console.warn('3D layout unavailable:', error);
    scene?.dispose();
    scene = null;
    stage.replaceChildren();
    enableControls(false);
    showSelection(null);
    overlay.hidden = false;
    retry.hidden = false;
    fallback.hidden = false;
    status.textContent = 'The 3D view could not load. It needs WebGL 2 and a working connection. You can retry or use the reference drawing.';
    root.dataset.state = 'error';
  }

  async function load() {
    if (scene || pending || destroyed) return;
    pending = true;
    root.dataset.state = 'loading';
    overlay.hidden = false;
    retry.hidden = true;
    fallback.hidden = true;
    status.textContent = 'Loading the 3D board…';
    request = new AbortController();
    const controller = request;
    let timeout;
    // Bound the entire load, including a stalled module import after the data
    // has already arrived; aborting a completed fetch alone cannot do that.
    const deadline = new Promise((_, reject) => {
      timeout = setTimeout(() => {
        controller.abort();
        reject(new Error('The 3D viewer load timed out'));
      }, 20000);
    });
    try {
      const [data, { createLayoutScene }] = await Promise.race([
        Promise.all([
          fetch(root.dataset.source, { signal: controller.signal }).then((response) => {
            if (!response.ok) throw new Error(`Layout data returned ${response.status}`);
            return response.json();
          }),
          import('./layout3d-scene.js'),
        ]),
        deadline,
      ]);
      model = data;
      if (model.schemaVersion !== 1 || model.id !== root.dataset.ampId || !Array.isArray(model.components)) {
        throw new Error('Layout data does not match this circuit');
      }
      if (destroyed) return;
      scene = createLayoutScene(stage, model, { onSelect: showSelection, onError: fail });
      const canvas = scene.canvas || stage.querySelector('canvas');
      if (!canvas) throw new Error('The renderer did not create a canvas');
      canvas.tabIndex = 0;
      canvas.setAttribute('role', 'img');
      canvas.setAttribute('aria-label', '5F1 interactive board. Arrow keys rotate; plus and minus zoom. Use Inspect a component to select parts with the keyboard.');
      listen(canvas, 'keydown', (event) => {
        if (event.altKey || event.ctrlKey || event.metaKey || !scene) return;
        const rotation = { ArrowLeft: [-0.15, 0], ArrowRight: [0.15, 0], ArrowUp: [0, -0.12], ArrowDown: [0, 0.12] }[event.key];
        if (rotation) {
          event.preventDefault();
          scene.rotate(...rotation);
          root.querySelectorAll('[data-view]').forEach((button) => button.setAttribute('aria-pressed', 'false'));
        } else if (['+', '=', '-', '_'].includes(event.key)) {
          event.preventDefault();
          scene.zoom(['+', '='].includes(event.key) ? 1.22 : 0.82);
        }
      });
      // Respect browser-restored checkbox/slider values as well as defaults.
      layers.forEach((input) => scene.setLayer(input.dataset.layer, input.checked));
      scene.setExplode(Number(explode.value) / 100);
      $('[data-explode-output]').textContent = `${explode.value}%`;
      enableControls(true);
      overlay.hidden = true;
      status.textContent = '3D board ready.';
      root.dataset.state = 'ready';
    } catch (error) {
      if (!destroyed) fail(error);
    } finally {
      clearTimeout(timeout);
      pending = false;
      request = null;
    }
  }

  listen(root, 'toggle', () => {
    if (root.open) {
      if (scene) requestAnimationFrame(() => scene?.resize());
      else load();
    }
  });
  listen(retry, 'click', load);
  layers.forEach((input) => listen(input, 'change', () => scene?.setLayer(input.dataset.layer, input.checked)));
  listen(explode, 'input', () => {
    $('[data-explode-output]').textContent = `${explode.value}%`;
    scene?.setExplode(Number(explode.value) / 100);
  });
  root.querySelectorAll('[data-view]').forEach((button) => listen(button, 'click', () => {
    scene?.setView(button.dataset.view);
    root.querySelectorAll('[data-view]').forEach((b) => b.setAttribute('aria-pressed', String(b === button)));
  }));
  root.querySelectorAll('[data-zoom]').forEach((button) => listen(button, 'click', () => scene?.zoom(button.dataset.zoom === 'in' ? 1.22 : 0.82)));
  listen(select, 'change', () => {
    const component = model?.components.find((c) => c.id === select.value);
    if (component) {
      const layer = component.mount === 'board' ? 'components' : 'hardware';
      layers.find((input) => input.dataset.layer === layer).checked = true;
      scene?.setLayer(layer, true);
    }
    scene?.selectComponent(component?.id || null);
  });
  listen($('[data-clear]'), 'click', () => scene?.selectComponent(null));
  listen($('[data-reset]'), 'click', () => {
    layers.forEach((input) => {
      input.checked = input.dataset.layer !== 'labels';
      scene?.setLayer(input.dataset.layer, input.checked);
    });
    explode.value = '0';
    $('[data-explode-output]').textContent = '0%';
    scene?.setExplode(0);
    scene?.selectComponent(null);
    scene?.reset();
    root.querySelectorAll('[data-view]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.view === 'perspective')));
  });
  const openFromHash = () => {
    if (location.hash === '#layout-3d') { root.open = true; load(); }
  };
  listen(window, 'hashchange', openFromHash);
  function dispose() {
    destroyed = true;
    request?.abort();
    scene?.dispose();
    lifetime.abort();
  }
  listen(window, 'pagehide', (event) => { if (!event.persisted) dispose(); });
  listen(document, 'astro:before-swap', dispose);
  openFromHash();
  if (root.open) load();
}
