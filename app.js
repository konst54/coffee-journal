import { validateDataset, selectBrews, brewLine, value, duration } from './model.js';

export function createViewer(root, doc = document) {
  let dataset, trusted = false, coffeeId = '', deviceId = '', sort = 'recent';
  const selected = new Set();
  const el = (tag, text, cls) => {
    const n = doc.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  const name = (items, id) => items.find(x => x.id === id)?.name;
  function render() {
    const banner = el('p', trusted ? 'Личные данные · авторизованный просмотр' : 'Вымышленные данные · демонстрация, не ваши записи', 'banner');
    const header = el('header'); header.append(el('h1', 'Дневник кофе'), banner);
    const toolbar = el('nav', undefined, 'toolbar');
    function selector(label, options, current, onChange) {
      const wrap = el('label', label); const s = el('select');
      for (const [id, title] of options) { const o = el('option', title); o.value = id; o.selected = id === current; s.append(o); }
      s.value = current; s.addEventListener('change', () => { onChange(s.value); selected.clear(); render(); });
      wrap.append(s); toolbar.append(wrap);
    }
    selector('Кофе', dataset.coffees.map(c => [c.id, c.name]), coffeeId, v => coffeeId = v);
    selector('Девайс', [['', 'Все'], ...dataset.equipment.filter(e => e.kind === 'brewer').map(e => [e.id,e.name])], deviceId, v => deviceId = v);
    selector('Порядок', [['recent','Сначала новые'],['rating','По оценке']], sort, v => sort = v);
    const coffee = dataset.coffees.find(c => c.id === coffeeId);
    const about = el('section', undefined, 'about');
    about.append(el('h2', coffee?.name ?? 'Кофе пока нет'));
    about.append(el('p', [coffee?.roaster, coffee?.origin, coffee?.process, coffee?.variety].filter(Boolean).join(' · ')));
    if (coffee?.labeled_notes) about.append(el('p', `На пачке: ${coffee.labeled_notes}`));
    const brews = selectBrews(dataset, {coffeeId, deviceId, sort});
    const cards = el('section', undefined, 'brews');
    cards.append(el('p', `Пробы: ${brews.length} · выберите до 3 для сравнения`, 'hint'));
    for (const brew of brews) {
      const card = el('article');
      const check = el('input'); check.type='checkbox'; check.checked=selected.has(brew.id); check.disabled=selected.size>=3&&!check.checked;
      check.setAttribute('aria-label', `Сравнить пробу ${brew.brewed_at ?? brew.id}`);
      check.addEventListener('change', () => { if (check.checked && selected.size<3) selected.add(brew.id); else selected.delete(brew.id); render(); });
      const line = el('label', undefined, 'line'); line.append(check, el('span', brewLine(brew, name(dataset.equipment,brew.brewer_id))));
      card.append(line, el('p', brew.taste_notes || 'Вкусовой комментарий не указан', 'taste'));
      const detail = el('details'); detail.append(el('summary','Рецепт и подробности'));
      const batch=dataset.batches.find(b=>b.id===brew.batch_id);
      detail.append(el('p', `Заварено: ${value(brew.brewed_at)} · Обжарка: ${value(batch?.roast_date)}`));
      detail.append(el('p', `Кофемолка: ${value(name(dataset.equipment,brew.grinder_id))} · Настройка: ${value(brew.grind_setting)}`));
      const recipe = dataset.recipes.find(r => r.id === brew.recipe_id);
      if (recipe) {
        detail.append(el('p', `Рецепт: ${recipe.name}`));
        for (const step of recipe.steps ?? []) detail.append(el('p', `${value(step.name)} · ${value(step.instruction)} · ${duration(step.duration_s)} · ${value(step.water_g,' г')}`));
      }
      if (brew.recipe_notes) detail.append(el('p', `Фактически: ${brew.recipe_notes}`));
      if (brew.bypass_water_g != null) detail.append(el('p', `Разбавление: ${brew.bypass_water_g} г`));
      if (brew.output_g != null) detail.append(el('p', `Выход: ${brew.output_g} г`));
      card.append(detail); cards.append(card);
    }
    if (!brews.length) cards.append(el('p','Проб с выбранными параметрами пока нет.'));
    const compare=el('section', undefined, 'compare');
    if (selected.size) {
      compare.append(el('h2',`Сравнение · ${selected.size}`));
      for(const brew of brews.filter(b=>selected.has(b.id))) {
        const block=el('div',undefined,'compare-item'); block.append(el('strong',brewLine(brew,name(dataset.equipment,brew.brewer_id))),el('p',brew.taste_notes||'—'),el('p',brew.recipe_notes||'—')); compare.append(block);
      }
    }
    root.replaceChildren(header,toolbar,about,compare,cards);
  }
  function load(data,isTrusted=false) {
    dataset=validateDataset(data); trusted=isTrusted; selected.clear(); coffeeId=dataset.coffees[0]?.id ?? ''; render();
  }
  return {
    loadDataset: data => load(data,false),
    loadAuthenticated: async adapter => {
      const result = await adapter();
      if (result?.authenticated !== true) throw new Error('Authentication required');
      load(result.dataset,true);
    }
  };
}
