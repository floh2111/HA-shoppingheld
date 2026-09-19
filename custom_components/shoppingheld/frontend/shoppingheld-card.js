/*
 * ShoppingHeld card for Home Assistant
 * Zeigt die ShoppingHeld-Einkaufsliste wie in der App: nach Kategorien gruppiert, Kategorie-Kacheln
 * mit "offen/gesamt", komplett abgehakte Kategorien ausgegraut, Antippen hakt ab, Wischen nach links
 * löscht, +/- ändert die Menge. Oben ein Fortschrittsbalken ("12 von 18 im Wagen") und Vorschlags-Chips
 * (Basics und oft gekaufte Artikel) zum Antippen.
 *
 * Konfiguration:
 *   type: custom:shoppingheld-card
 *   entity: todo.shoppingheld_einkaufsliste   # die To-do-Entität der Integration
 *   title: Einkaufsliste                      # optional (Standard: Listenname aus ShoppingHeld)
 *   hide_add: false                           # true = Eingabefeld (und Vorschlags-Chips) ausblenden
 *   hide_chips: false                         # true = Vorschlags-Chips ausblenden
 *   hide_checked: false                       # true = abgehakte Artikel ausblenden
 */

const SH_CATEGORY_STYLE = {
  gemuese: { icon: '🍎', bg: '#e2f0cb', accent: '#4caf50' },
  milch: { icon: '🧊', bg: '#b5ead7', accent: '#00bcd4' },
  milchprodukte: { icon: '🥛', bg: '#eaf6ff', accent: '#5dade2' },
  brot: { icon: '🍞', bg: '#ffdac1', accent: '#ff9800' },
  fleisch: { icon: '🥩', bg: '#ffb7b2', accent: '#e91e63' },
  cerealien: { icon: '🥣', bg: '#fec8d8', accent: '#e91e63' },
  kaffee: { icon: '☕', bg: '#d2b48c', accent: '#795548' },
  getraenke: { icon: '🥤', bg: '#c7ceea', accent: '#3f51b5' },
  tk: { icon: '❄️', bg: '#b3e5fc', accent: '#03a9f4' },
  knabber: { icon: '🍿', bg: '#ffe5ec', accent: '#ff4081' },
  haushalt: { icon: '🧹', bg: '#e0bbe4', accent: '#9c27b0' },
  koerperpflege: { icon: '🧴', bg: '#fff3b8', accent: '#f9a825' },
  sonstiges: { icon: '📦', bg: '#e8e8e8', accent: '#9e9e9e' },
  konserven: { icon: '🥫', bg: '#f39c12', accent: '#d35400' },
  katzenfutter: { icon: '🐈', bg: '#9b59b6', accent: '#8e44ad' },
};

const SH_TEXT = {
  de: {
    placeholder: 'Artikel hinzufügen …',
    add: 'Hinzufügen',
    open: 'offen',
    today: 'Heute Einkaufstag',
    empty: 'Die Liste ist leer 🎉',
    unavailable: 'Nicht verfügbar',
    notFound: 'Entität nicht gefunden:',
    remove: 'Löschen',
    failed: 'Aktion fehlgeschlagen:',
    progress: (n, m) => `${n} von ${m} im Wagen`,
    progressDone: 'Alles im Wagen! 🎉',
    less: 'Weniger',
    more: 'Mehr',
    suggestion: 'Oft gekauft',
    basic: 'Basic',
  },
  en: {
    placeholder: 'Add item …',
    add: 'Add',
    open: 'open',
    today: 'Shopping day today',
    empty: 'The list is empty 🎉',
    unavailable: 'Unavailable',
    notFound: 'Entity not found:',
    remove: 'Delete',
    failed: 'Action failed:',
    progress: (n, m) => `${n} of ${m} in the cart`,
    progressDone: 'All in the cart! 🎉',
    less: 'Less',
    more: 'More',
    suggestion: 'Often bought',
    basic: 'Basic',
  },
};

const SH_CSS = `
  :host { display: block; }
  [hidden] { display: none !important; }
  ha-card { overflow: hidden; }
  .head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; padding: 16px 16px 4px; }
  .title { font-size: 20px; font-weight: 600; color: var(--primary-text-color); }
  .sub { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
  /* Getönt statt vollflächig: In Themes mit heller Primärfarbe (z. B. Frosted Glass) wäre weißer Text
     auf der Primärfarbe kaum lesbar. Fallback (ältere Browser ohne color-mix): neutrale Fläche. */
  .chip { display: inline-block; margin-left: 6px; padding: 1px 8px; border-radius: 10px; font-size: 12px;
          background: var(--secondary-background-color); color: var(--primary-text-color);
          border: 1px solid var(--primary-color);
          background: color-mix(in srgb, var(--primary-color) 25%, transparent); }
  /* Fortschritt: Balken + Text; bei "alles abgehakt" grün und einmal ein kleiner Glanz-Effekt */
  .progress { padding: 6px 16px 0; }
  .bar { height: 8px; border-radius: 4px; overflow: hidden; background: var(--divider-color);
         background: color-mix(in srgb, var(--primary-text-color) 14%, transparent); }
  .fill { position: relative; overflow: hidden; height: 100%; width: 0; border-radius: 4px;
          background: var(--primary-color); transition: width .4s ease, background-color .4s ease; }
  .fill::after { content: ''; position: absolute; inset: 0; transform: translateX(-100%);
                 background: linear-gradient(90deg, transparent, rgba(255,255,255,.6), transparent); }
  .ptext { margin-top: 4px; font-size: 13px; color: var(--secondary-text-color); transform-origin: left center; }
  .progress.complete .fill { background: var(--success-color, #43a047); }
  .progress.complete .ptext { color: var(--success-color, #43a047); font-weight: 600; }
  .progress.celebrate .fill::after { animation: sh-shine 1.1s ease-out 1; }
  .progress.celebrate .ptext { animation: sh-pop .6s ease-out 1; }
  @keyframes sh-shine { to { transform: translateX(100%); } }
  @keyframes sh-pop { 0% { transform: scale(.9); opacity: .4; } 60% { transform: scale(1.08); } 100% { transform: scale(1); opacity: 1; } }
  @media (prefers-reduced-motion: reduce) {
    .fill { transition: none; }
    .progress.celebrate .fill::after, .progress.celebrate .ptext { animation: none; }
  }
  /* Vorschlags-Chips: eine scrollbare Zeile über dem Eingabefeld */
  .chips { display: flex; gap: 6px; overflow-x: auto; padding: 10px 16px 2px; scrollbar-width: none; }
  .chips::-webkit-scrollbar { display: none; }
  .sug { flex: none; padding: 5px 11px; border-radius: 16px; font-size: 13px; cursor: pointer; white-space: nowrap;
         color: var(--primary-text-color); background: var(--secondary-background-color);
         border: 1px solid var(--divider-color); }
  .sug:hover { border-color: var(--primary-color); }
  .sug.often { border-style: dashed; }
  .add { display: flex; gap: 8px; padding: 8px 16px 4px; }
  .add input { flex: 1; min-width: 0; padding: 10px 12px; font-size: 15px; border-radius: 10px;
               border: 1px solid var(--divider-color); background: var(--card-background-color);
               color: var(--primary-text-color); outline: none; }
  .add input:focus { border-color: var(--primary-color); }
  .add button { padding: 0 16px; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer;
                border: 1px solid var(--primary-color); color: var(--primary-text-color);
                background: var(--secondary-background-color);
                background: color-mix(in srgb, var(--primary-color) 25%, transparent); }
  .add button:hover:not(:disabled) { background: color-mix(in srgb, var(--primary-color) 40%, transparent); }
  .add button:disabled { opacity: .5; cursor: default; }
  .error { margin: 6px 16px 0; font-size: 13px; color: var(--error-color, #db4437); }
  .list { padding: 8px 16px 16px; display: flex; flex-direction: column; gap: 10px; }
  .msg { padding: 24px 16px; text-align: center; color: var(--secondary-text-color); }
  .cat-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; cursor: pointer;
                padding: 10px 12px; border-radius: 12px; border-left: 4px solid var(--accent);
                background: var(--secondary-background-color);
                background: color-mix(in srgb, var(--bg) 55%, var(--card-background-color, #fff));
                color: var(--primary-text-color); font-weight: 600; font-size: 14px; user-select: none; }
  .cat-count { font-size: 12px; font-weight: 500; opacity: .75; white-space: nowrap; }
  /* Alle Artikel der Kategorie abgehakt: Kachel ausgegraut, wie in der App */
  .cat.done .cat-header { filter: grayscale(1); opacity: .5; }
  .items { margin-top: 4px; display: flex; flex-direction: column; }
  /* Wischen zum Löschen: Der rote Bereich ist nur so breit wie der freigelegte Streifen (wächst mit dem Wischen),
     damit er in durchscheinenden Themes (z. B. Frosted Glass) nicht hinter der Zeile hervorscheint. */
  .swipe { position: relative; overflow: hidden; border-radius: 10px; }
  .swipe-bg { position: absolute; top: 0; right: 0; bottom: 0; width: 0; overflow: hidden; white-space: nowrap;
              display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600;
              color: #fff; background: var(--error-color, #db4437); }
  .item { position: relative; z-index: 1; display: flex; align-items: center; gap: 10px; padding: 8px 6px 8px 10px;
          border-radius: 10px; cursor: pointer; color: var(--primary-text-color);
          touch-action: pan-y; user-select: none; -webkit-user-select: none; }
  .item:hover { background: var(--secondary-background-color); }
  .check { flex: none; width: 20px; height: 20px; border-radius: 50%; border: 2px solid var(--accent); box-sizing: border-box;
           display: flex; align-items: center; justify-content: center; font-size: 12px; line-height: 1; color: #fff; }
  .item.checked .check { background: var(--accent); }
  .text { flex: 1; min-width: 0; overflow-wrap: anywhere; font-size: 15px; }
  .item.checked .text { text-decoration: line-through; opacity: .5; }
  .amount { flex: none; font-size: 12px; font-weight: 600; padding: 1px 8px; border-radius: 10px;
            background: var(--secondary-background-color); color: var(--secondary-text-color); }
  .item.checked .amount { opacity: .5; }
  .step { flex: none; display: inline-flex; align-items: center; border-radius: 12px; overflow: hidden;
          background: var(--secondary-background-color); }
  .step button { border: none; background: none; cursor: pointer; width: 26px; height: 26px; padding: 0; font-size: 16px;
                 line-height: 1; color: var(--primary-text-color); }
  .step button:hover:not(:disabled) { background: var(--divider-color); }
  .step button:disabled { opacity: .3; cursor: default; }
  .step-val { min-width: 16px; text-align: center; font-size: 13px; font-weight: 600; color: var(--primary-text-color); }
  .del { flex: none; border: none; background: none; cursor: pointer; font-size: 15px; line-height: 1; padding: 6px 8px;
         color: var(--secondary-text-color); opacity: .45; border-radius: 8px; }
  .del:hover { opacity: 1; color: var(--error-color, #db4437); }
`;

class ShoppingHeldCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._toggled = new Map(); // Kategorie -> manuell auf-/zugeklappt
    this._seenOpen = new Set(); // Kategorien, die in dieser Sitzung schon offene Artikel hatten
    this._pending = new Map(); // Artikel-ID -> optimistisch angezeigter checked-Zustand
    this._pendingAmount = new Map(); // Artikel-ID -> { value, ts }: optimistisch angezeigte Menge
    this._removed = new Set(); // Artikel-IDs, die gelöscht wurden und bis zum Server-Stand ausgeblendet bleiben
    this._chipPending = new Set(); // Vorschläge, die gerade hinzugefügt werden (bis zum Server-Stand ausgeblendet)
    this._dragging = false; // gerade wird eine Zeile gewischt: Neuzeichnen zurückstellen
    this._renderPending = false;
    this._swipedAt = 0;
    this._wasComplete = undefined;
    this._error = '';
    this._built = false;
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error('Bitte "entity" angeben (z. B. todo.shoppingheld_einkaufsliste).');
    }
    this._config = { hide_add: false, hide_checked: false, hide_chips: false, ...config };
    this._build();
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const state = this._config ? hass.states[this._config.entity] : undefined;
    if (state !== this._lastState) {
      this._lastState = state;
      this._pending.clear();
      this._chipPending.clear();
      const ids = new Set(((state && state.attributes && state.attributes.items) || []).map((i) => i.id));
      for (const id of this._removed) if (!ids.has(id)) this._removed.delete(id);
      if (this._dragging) this._renderPending = true;
      else this._render();
    }
  }

  getCardSize() {
    const items = this._items().length;
    return Math.min(12, 3 + Math.ceil(items / 2));
  }

  static getConfigForm() {
    return {
      schema: [
        { name: 'entity', required: true, selector: { entity: { domain: 'todo', integration: 'shoppingheld' } } },
        { name: 'title', selector: { text: {} } },
        {
          type: 'grid',
          name: '',
          schema: [
            { name: 'hide_add', selector: { boolean: {} } },
            { name: 'hide_checked', selector: { boolean: {} } },
            { name: 'hide_chips', selector: { boolean: {} } },
          ],
        },
      ],
      computeLabel: (schema) =>
        ({
          entity: 'Einkaufsliste',
          title: 'Titel (optional)',
          hide_add: 'Eingabefeld ausblenden',
          hide_checked: 'Abgehakte ausblenden',
          hide_chips: 'Vorschläge ausblenden',
        })[schema.name] || schema.name,
    };
  }

  static getStubConfig(hass) {
    const entity = Object.keys((hass && hass.states) || {}).find(
      (id) => id.startsWith('todo.') && hass.states[id].attributes && hass.states[id].attributes.source === 'shoppingheld',
    );
    return { entity: entity || 'todo.shoppingheld_einkaufsliste' };
  }

  // ---- Hilfsfunktionen -------------------------------------------------------------------
  _t(key) {
    const lang = this._hass && this._hass.language && this._hass.language.startsWith('de') ? 'de' : 'en';
    return SH_TEXT[lang][key];
  }

  _state() {
    return this._hass && this._config ? this._hass.states[this._config.entity] : undefined;
  }

  _items() {
    const state = this._state();
    const items = state && state.attributes && Array.isArray(state.attributes.items) ? state.attributes.items : [];
    const now = Date.now();
    return items
      .filter((i) => !this._removed.has(i.id))
      .map((i) => {
        let item = i;
        if (this._pending.has(i.id)) item = { ...item, checked: this._pending.get(i.id) };
        const pa = this._pendingAmount.get(i.id);
        if (pa) {
          // Optimistische Menge, bis der Server-Stand sie bestätigt (oder nach 8 s aufgibt)
          if (pa.value === i.amount || now - pa.ts > 8000) this._pendingAmount.delete(i.id);
          else item = { ...item, amount: pa.value };
        }
        return item;
      });
  }

  // ---- Aufbau (einmalig) -----------------------------------------------------------------
  _build() {
    if (this._built) return;
    this._built = true;
    const root = this.shadowRoot;
    root.innerHTML = `<style>${SH_CSS}</style>
      <ha-card>
        <div class="head"><span class="title"></span><span class="sub"></span></div>
        <div class="progress" hidden>
          <div class="bar"><div class="fill"></div></div>
          <div class="ptext"></div>
        </div>
        <div class="chips" hidden></div>
        <form class="add"><input type="text" autocomplete="off" /><button type="submit"></button></form>
        <div class="error" hidden></div>
        <div class="list"></div>
      </ha-card>`;
    this._el = {
      title: root.querySelector('.title'),
      sub: root.querySelector('.sub'),
      progress: root.querySelector('.progress'),
      fill: root.querySelector('.fill'),
      ptext: root.querySelector('.ptext'),
      chips: root.querySelector('.chips'),
      form: root.querySelector('.add'),
      input: root.querySelector('.add input'),
      button: root.querySelector('.add button'),
      error: root.querySelector('.error'),
      list: root.querySelector('.list'),
    };
    this._el.form.addEventListener('submit', (ev) => {
      ev.preventDefault();
      this._addItem();
    });
  }

  // ---- Zeichnen --------------------------------------------------------------------------
  _render() {
    if (!this._built || !this._config) return;
    const el = this._el;
    const state = this._state();
    const attrs = (state && state.attributes) || {};

    el.title.textContent = this._config.title || attrs.list_name || 'Einkaufsliste';
    el.form.hidden = !!this._config.hide_add;
    el.input.placeholder = this._t('placeholder');
    el.button.textContent = this._t('add');
    el.error.hidden = !this._error;
    el.error.textContent = this._error;
    el.list.textContent = '';

    if (!this._hass) return;
    if (!state) {
      el.progress.hidden = true;
      el.chips.hidden = true;
      el.sub.textContent = '';
      el.list.append(this._message(`${this._t('notFound')} ${this._config.entity}`));
      return;
    }
    if (state.state === 'unavailable') {
      el.progress.hidden = true;
      el.chips.hidden = true;
      el.sub.textContent = '';
      el.list.append(this._message(this._t('unavailable')));
      return;
    }

    const items = this._items();
    const open = items.filter((i) => !i.checked).length;
    const shoppingToday = Array.isArray(attrs.shopping_days) && attrs.shopping_days.includes(new Date().getDay());
    el.sub.textContent = `${open} ${this._t('open')}`;
    if (shoppingToday) {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = `🛒 ${this._t('today')}`;
      el.sub.append(chip);
    }

    this._renderProgress(items);
    this._renderChips(attrs, items);

    const visible = this._config.hide_checked ? items.filter((i) => !i.checked) : items;
    if (visible.length === 0) {
      el.list.append(this._message(this._t('empty')));
      return;
    }

    // Die Artikel kommen schon in der Kategorie-Reihenfolge des Servers - nur zusammenfassen.
    const groups = [];
    const byCat = new Map();
    for (const item of visible) {
      const key = item.category || 'sonstiges';
      if (!byCat.has(key)) {
        const group = { category: key, items: [] };
        byCat.set(key, group);
        groups.push(group);
      }
      byCat.get(key).items.push(item);
    }
    for (const group of groups) el.list.append(this._renderCategory(group, attrs.categories || {}));
  }

  _renderProgress(items) {
    const el = this._el;
    const total = items.length;
    const checked = items.filter((i) => i.checked).length;
    el.progress.hidden = total === 0;
    if (total === 0) {
      this._wasComplete = false;
      return;
    }
    const complete = checked === total;
    el.fill.style.width = `${Math.round((checked / total) * 100)}%`;
    el.ptext.textContent = complete ? this._t('progressDone') : this._t('progress')(checked, total);
    el.progress.classList.toggle('complete', complete);
    // Kleine Animation nur beim Übergang zu "alles abgehakt", nicht beim bloßen Anzeigen eines fertigen Stands
    el.progress.classList.toggle('celebrate', complete && this._wasComplete === false);
    this._wasComplete = complete;
  }

  _renderChips(attrs, items) {
    const box = this._el.chips;
    box.textContent = '';
    if (this._config.hide_add || this._config.hide_chips) {
      box.hidden = true;
      return;
    }
    // Was schon offen auf der Liste steht (oder gerade hinzugefügt wird), muss nicht vorgeschlagen werden
    const onList = new Set(items.filter((i) => !i.checked && !i.unit).map((i) => String(i.text).toLowerCase()));
    const seen = new Set();
    const chips = [];
    const collect = (rows, often) => {
      for (const row of Array.isArray(rows) ? rows : []) {
        const text = row && typeof row.text === 'string' ? row.text.trim() : '';
        const key = text.toLowerCase();
        if (!text || seen.has(key) || onList.has(key) || this._chipPending.has(key)) continue;
        seen.add(key);
        chips.push({ text, key, category: row.category, often });
      }
    };
    collect(attrs.basics, false);
    collect(attrs.suggestions, true);
    for (const chip of chips.slice(0, 20)) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `sug${chip.often ? ' often' : ''}`;
      button.title = chip.often ? this._t('suggestion') : this._t('basic');
      button.textContent = `${chip.often ? '💡' : '+'} ${chip.text}`;
      button.addEventListener('click', () => this._addChip(chip));
      box.append(button);
    }
    box.hidden = chips.length === 0;
  }

  _message(text) {
    const div = document.createElement('div');
    div.className = 'msg';
    div.textContent = text;
    return div;
  }

  _renderCategory(group, labels) {
    const style = SH_CATEGORY_STYLE[group.category] || SH_CATEGORY_STYLE.sonstiges;
    const open = group.items.filter((i) => !i.checked).length;
    const done = group.items.length > 0 && open === 0;
    // Standard: Kategorien mit offenen Artikeln sind aufgeklappt, von Anfang an komplett abgehakte
    // zugeklappt. Wer in dieser Sitzung schon offene Artikel hatte, klappt beim Abhaken des letzten
    // Artikels NICHT zu (sonst verschwindet er unterm Finger und lässt sich nicht schnell zurücknehmen).
    if (open > 0) this._seenOpen.add(group.category);
    const expanded = this._toggled.has(group.category)
      ? this._toggled.get(group.category)
      : open > 0 || this._seenOpen.has(group.category);

    const cat = document.createElement('div');
    cat.className = `cat${done ? ' done' : ''}`;
    cat.style.setProperty('--bg', style.bg);
    cat.style.setProperty('--accent', style.accent);

    const header = document.createElement('div');
    header.className = 'cat-header';
    header.setAttribute('role', 'button');
    header.tabIndex = 0;
    const name = document.createElement('span');
    name.textContent = `${style.icon} ${labels[group.category] || group.category}`;
    const count = document.createElement('span');
    count.className = 'cat-count';
    count.textContent = `${open}/${group.items.length} ${this._t('open')} ${expanded ? '▲' : '▼'}`;
    header.append(name, count);
    const toggle = () => {
      this._toggled.set(group.category, !expanded);
      this._render();
    };
    header.addEventListener('click', toggle);
    header.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' || ev.key === ' ') {
        ev.preventDefault();
        toggle();
      }
    });
    cat.append(header);

    if (expanded) {
      const list = document.createElement('div');
      list.className = 'items';
      for (const item of group.items) list.append(this._renderItem(item));
      cat.append(list);
    }
    return cat;
  }

  _renderItem(item) {
    const wrap = document.createElement('div');
    wrap.className = 'swipe';
    const bg = document.createElement('div');
    bg.className = 'swipe-bg';
    bg.textContent = `🗑️ ${this._t('remove')}`;

    const row = document.createElement('div');
    row.className = `item${item.checked ? ' checked' : ''}`;
    row.setAttribute('role', 'button');
    row.tabIndex = 0;

    const check = document.createElement('span');
    check.className = 'check';
    check.textContent = item.checked ? '✓' : '';
    const text = document.createElement('span');
    text.className = 'text';
    text.textContent = item.text;
    row.append(check, text);

    if (!item.checked && !item.unit) {
      row.append(this._renderStepper(item));
    } else if (item.unit || item.amount > 1) {
      const amount = document.createElement('span');
      amount.className = 'amount';
      amount.textContent = item.unit ? `${item.amount} ${item.unit}` : `${item.amount}×`;
      row.append(amount);
    }

    const del = document.createElement('button');
    del.className = 'del';
    del.type = 'button';
    del.title = this._t('remove');
    del.setAttribute('aria-label', this._t('remove'));
    del.textContent = '✕';
    del.addEventListener('click', (ev) => {
      ev.stopPropagation();
      this._removeItem(item);
    });
    row.append(del);

    row.addEventListener('click', () => {
      if (Date.now() - this._swipedAt < 400) return; // Ende einer Wischgeste ist kein Antippen
      this._toggleItem(item);
    });
    row.addEventListener('keydown', (ev) => {
      if (ev.target !== row) return;
      if (ev.key === 'Enter' || ev.key === ' ') {
        ev.preventDefault();
        this._toggleItem(item);
      } else if (ev.key === 'Delete' || ev.key === 'Backspace') {
        ev.preventDefault();
        this._removeItem(item);
      }
    });
    this._attachSwipe(wrap, row, bg, item);
    wrap.append(bg, row);
    return wrap;
  }

  _renderStepper(item) {
    const box = document.createElement('span');
    box.className = 'step';
    const make = (label, title, disabled, delta) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = label;
      button.title = title;
      button.setAttribute('aria-label', title);
      button.disabled = disabled;
      button.addEventListener('click', (ev) => {
        ev.stopPropagation();
        this._setAmount(item, item.amount + delta);
      });
      return button;
    };
    const value = document.createElement('span');
    value.className = 'step-val';
    value.textContent = String(item.amount);
    box.append(make('−', this._t('less'), item.amount <= 1, -1), value, make('+', this._t('more'), item.amount >= 99, 1));
    return box;
  }

  // Wischen nach links löscht (Touch und Maus), ab 70 px Weg. Senkrechtes Scrollen bleibt dem Browser.
  _attachSwipe(wrap, row, bg, item) {
    const THRESHOLD = 70;
    const MAX = 120;
    let tracking = false;
    let dragging = false;
    let pointerId = null;
    let startX = 0;
    let startY = 0;
    let dx = 0;

    row.addEventListener('pointerdown', (ev) => {
      if (ev.pointerType === 'mouse' && ev.button !== 0) return;
      if (ev.target.closest('.step, .del')) return;
      tracking = true;
      dragging = false;
      pointerId = ev.pointerId;
      startX = ev.clientX;
      startY = ev.clientY;
      dx = 0;
    });
    row.addEventListener('pointermove', (ev) => {
      if (!tracking || ev.pointerId !== pointerId) return;
      const mx = ev.clientX - startX;
      const my = ev.clientY - startY;
      if (!dragging) {
        if (Math.abs(mx) < 8 || Math.abs(mx) < Math.abs(my)) return;
        dragging = true;
        this._dragging = true;
        try {
          row.setPointerCapture(pointerId);
        } catch (_err) {
          /* nicht schlimm: Wischen funktioniert dann nur innerhalb der Zeile */
        }
        row.style.transition = 'none';
        bg.style.transition = 'none';
      }
      dx = Math.max(-MAX, Math.min(0, mx));
      row.style.transform = `translateX(${dx}px)`;
      bg.style.width = `${-dx}px`;
    });
    const end = () => {
      if (!tracking) return;
      tracking = false;
      if (!dragging) return;
      dragging = false;
      this._swipedAt = Date.now();
      row.style.transition = 'transform .2s ease';
      bg.style.transition = 'width .2s ease';
      if (dx <= -THRESHOLD) {
        row.style.transform = 'translateX(-100%)';
        bg.style.width = '100%';
        setTimeout(() => {
          wrap.style.transition = 'max-height .2s ease, opacity .2s ease';
          wrap.style.maxHeight = `${wrap.offsetHeight}px`;
          requestAnimationFrame(() => {
            wrap.style.maxHeight = '0px';
            wrap.style.opacity = '0';
          });
          setTimeout(() => {
            this._endDrag();
            this._removeItem(item);
          }, 210);
        }, 200);
      } else {
        row.style.transform = 'translateX(0)';
        bg.style.width = '0px';
        setTimeout(() => this._endDrag(), 210);
      }
    };
    row.addEventListener('pointerup', end);
    row.addEventListener('pointercancel', end);
  }

  _endDrag() {
    this._dragging = false;
    if (this._renderPending) {
      this._renderPending = false;
      this._render();
    }
  }

  // ---- Aktionen --------------------------------------------------------------------------
  _call(domain, service, data) {
    return this._hass.callService(domain, service, data, { entity_id: this._config.entity });
  }

  _fail(err) {
    this._pending.clear();
    this._pendingAmount.clear();
    this._removed.clear();
    this._chipPending.clear();
    this._error = `${this._t('failed')} ${(err && err.message) || err}`;
    this._render();
  }

  _toggleItem(item) {
    this._error = '';
    this._pending.set(item.id, !item.checked); // sofort anzeigen, der Server-Stand folgt kurz danach
    this._render();
    Promise.resolve(
      this._call('todo', 'update_item', { item: String(item.id), status: item.checked ? 'needs_action' : 'completed' }),
    ).catch((err) => this._fail(err));
  }

  _setAmount(item, amount) {
    const value = Math.max(1, Math.min(99, amount));
    if (value === item.amount) return;
    this._error = '';
    this._pendingAmount.set(item.id, { value, ts: Date.now() });
    this._render();
    Promise.resolve(this._call('shoppingheld', 'set_amount', { item: String(item.id), amount: value })).catch((err) =>
      this._fail(err),
    );
  }

  _addChip(chip) {
    this._error = '';
    this._chipPending.add(chip.key);
    this._render();
    const data = { item: chip.text };
    if (chip.category) data.category = chip.category;
    Promise.resolve(this._call('shoppingheld', 'add_item', data)).catch((err) => this._fail(err));
  }

  _removeItem(item) {
    this._error = '';
    this._removed.add(item.id); // sofort ausblenden, der Server-Stand folgt kurz danach
    this._render();
    Promise.resolve(this._call('todo', 'remove_item', { item: [String(item.id)] })).catch((err) => this._fail(err));
  }

  async _addItem() {
    const text = this._el.input.value.trim();
    if (!text) return;
    this._error = '';
    this._el.button.disabled = true;
    try {
      await this._call('shoppingheld', 'add_item', { item: text });
      this._el.input.value = '';
    } catch (err) {
      this._fail(err);
    } finally {
      this._el.button.disabled = false;
      this._el.input.focus();
    }
  }
}

if (!customElements.get('shoppingheld-card')) {
  customElements.define('shoppingheld-card', ShoppingHeldCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === 'shoppingheld-card')) {
  window.customCards.push({
    type: 'shoppingheld-card',
    name: 'ShoppingHeld',
    description: 'Deine ShoppingHeld-Einkaufsliste nach Kategorien: Abhaken, Wischen zum Löschen, Menge ändern, Fortschrittsbalken und Vorschläge.',
    documentationURL: 'https://github.com/floh2111/HA-shoppingheld',
  });
}
