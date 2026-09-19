/*
 * ShoppingHeld card for Home Assistant
 * Zeigt die ShoppingHeld-Einkaufsliste wie in der App: nach Kategorien gruppiert, Kategorie-Kacheln
 * mit "offen/gesamt", komplett abgehakte Kategorien ausgegraut, Antippen hakt ab.
 *
 * Konfiguration:
 *   type: custom:shoppingheld-card
 *   entity: todo.shoppingheld_einkaufsliste   # die To-do-Entität der Integration
 *   title: Einkaufsliste                      # optional (Standard: Listenname aus ShoppingHeld)
 *   hide_add: false                           # true = Eingabefeld zum Hinzufügen ausblenden
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
  },
};

const SH_CSS = `
  :host { display: block; }
  [hidden] { display: none !important; }
  ha-card { overflow: hidden; }
  .head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; padding: 16px 16px 4px; }
  .title { font-size: 20px; font-weight: 600; color: var(--primary-text-color); }
  .sub { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
  .chip { display: inline-block; margin-left: 6px; padding: 1px 8px; border-radius: 10px; font-size: 12px;
          background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .add { display: flex; gap: 8px; padding: 8px 16px 4px; }
  .add input { flex: 1; min-width: 0; padding: 10px 12px; font-size: 15px; border-radius: 10px;
               border: 1px solid var(--divider-color); background: var(--card-background-color);
               color: var(--primary-text-color); outline: none; }
  .add input:focus { border-color: var(--primary-color); }
  .add button { padding: 0 16px; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer;
                background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .add button:disabled { opacity: .5; cursor: default; }
  .error { margin: 6px 16px 0; font-size: 13px; color: var(--error-color, #db4437); }
  .list { padding: 8px 16px 16px; display: flex; flex-direction: column; gap: 10px; }
  .msg { padding: 24px 16px; text-align: center; color: var(--secondary-text-color); }
  .cat-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; cursor: pointer;
                padding: 10px 12px; border-radius: 12px; border-left: 4px solid var(--accent);
                background: color-mix(in srgb, var(--bg) 55%, var(--card-background-color, #fff));
                color: var(--primary-text-color); font-weight: 600; font-size: 14px; user-select: none; }
  .cat-count { font-size: 12px; font-weight: 500; opacity: .75; white-space: nowrap; }
  /* Alle Artikel der Kategorie abgehakt: Kachel ausgegraut, wie in der App */
  .cat.done .cat-header { filter: grayscale(1); opacity: .5; }
  .items { margin-top: 4px; display: flex; flex-direction: column; }
  .item { display: flex; align-items: center; gap: 10px; padding: 8px 6px 8px 10px; border-radius: 10px; cursor: pointer;
          color: var(--primary-text-color); }
  .item:hover { background: var(--secondary-background-color); }
  .check { flex: none; width: 20px; height: 20px; border-radius: 50%; border: 2px solid var(--accent); box-sizing: border-box;
           display: flex; align-items: center; justify-content: center; font-size: 12px; line-height: 1; color: #fff; }
  .item.checked .check { background: var(--accent); }
  .text { flex: 1; min-width: 0; overflow-wrap: anywhere; font-size: 15px; }
  .item.checked .text { text-decoration: line-through; opacity: .5; }
  .amount { flex: none; font-size: 12px; font-weight: 600; padding: 1px 8px; border-radius: 10px;
            background: var(--secondary-background-color); color: var(--secondary-text-color); }
  .item.checked .amount { opacity: .5; }
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
    this._error = '';
    this._built = false;
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error('Bitte "entity" angeben (z. B. todo.shoppingheld_einkaufsliste).');
    }
    this._config = { hide_add: false, hide_checked: false, ...config };
    this._build();
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const state = this._config ? hass.states[this._config.entity] : undefined;
    if (state !== this._lastState) {
      this._lastState = state;
      this._pending.clear();
      this._render();
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
          ],
        },
      ],
      computeLabel: (schema) =>
        ({
          entity: 'Einkaufsliste',
          title: 'Titel (optional)',
          hide_add: 'Eingabefeld ausblenden',
          hide_checked: 'Abgehakte ausblenden',
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
    return items.map((i) => (this._pending.has(i.id) ? { ...i, checked: this._pending.get(i.id) } : i));
  }

  // ---- Aufbau (einmalig) -----------------------------------------------------------------
  _build() {
    if (this._built) return;
    this._built = true;
    const root = this.shadowRoot;
    root.innerHTML = `<style>${SH_CSS}</style>
      <ha-card>
        <div class="head"><span class="title"></span><span class="sub"></span></div>
        <form class="add"><input type="text" autocomplete="off" /><button type="submit"></button></form>
        <div class="error" hidden></div>
        <div class="list"></div>
      </ha-card>`;
    this._el = {
      title: root.querySelector('.title'),
      sub: root.querySelector('.sub'),
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
      el.sub.textContent = '';
      el.list.append(this._message(`${this._t('notFound')} ${this._config.entity}`));
      return;
    }
    if (state.state === 'unavailable') {
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

    if (item.unit || item.amount > 1) {
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

    row.addEventListener('click', () => this._toggleItem(item));
    row.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' || ev.key === ' ') {
        ev.preventDefault();
        this._toggleItem(item);
      }
    });
    return row;
  }

  // ---- Aktionen --------------------------------------------------------------------------
  _call(domain, service, data) {
    return this._hass.callService(domain, service, data, { entity_id: this._config.entity });
  }

  _fail(err) {
    this._pending.clear();
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

  _removeItem(item) {
    this._error = '';
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
    description: 'Deine ShoppingHeld-Einkaufsliste nach Kategorien, mit Abhaken und Hinzufügen.',
    documentationURL: 'https://github.com/floh2111/HA-shoppingheld',
  });
}
