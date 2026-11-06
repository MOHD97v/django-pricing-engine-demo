/**
 * Presentation only. ALL pricing is calculated by Django's compute_price().
 * No client-side price formulas are used for quotes, tax or final totals.
 */
(() => {
  'use strict';
  const state = {products: [], product: null, selections: {}, quote: null, serial: 0};
  const $ = id => document.getElementById(id);
  const applyTheme = theme => {
    const dark = theme === 'dark';
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';

    const toggle = $('theme-toggle');
    if (!toggle) return;

    toggle.setAttribute('aria-pressed', String(dark));
    toggle.setAttribute(
      'aria-label',
      dark ? 'Switch to light mode' : 'Switch to dark mode'
    );
    toggle.querySelector('.theme-icon').textContent = dark ? '☀' : '☾';
    toggle.querySelector('.theme-label').textContent = dark ? 'LIGHT' : 'DARK';
  };
  const escapeHTML = s => String(s ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const money = value => `${Number(value ?? 0).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})} SAR`;
  const cookie = name => document.cookie.split(';').map(x => x.trim()).find(x => x.startsWith(`${name}=`))?.split('=').slice(1).join('=') ?? '';
  const http = async (url, options = {}) => {
    const response = await fetch(url, {
      credentials:'same-origin', ...options,
      headers: {...(options.headers || {}), ...(options.method === 'POST' ? {'Content-Type':'application/json','X-CSRFToken':decodeURIComponent(cookie('csrftoken'))} : {})}
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  };
  const picked = id => Object.prototype.hasOwnProperty.call(state.selections, String(id)) && Number(state.selections[String(id)].qty) > 0;
  const groupSelected = group => group.choices.filter(c => picked(c.id));
  const removeGroup = group => group.choices.forEach(c => delete state.selections[String(c.id)]);
  const setChoice = (group, choice, checked) => {
    if (checked && group.max_select === 1) removeGroup(group);
    if (checked) state.selections[String(choice.id)] = {level:null,qty:1};
    else delete state.selections[String(choice.id)];
    renderGroups(); refreshQuote();
  };

  const renderGroups = () => {
    const parent = $('option-groups'); parent.replaceChildren();
    for (const group of state.product.groups) {
      const section = document.createElement('section'); section.className = 'option-group';
      const header = document.createElement('div'); header.className = 'config-caption';
      header.innerHTML = `<h4>${escapeHTML(group.name)}</h4><small>${group.is_required ? 'REQUIRED' : 'OPTIONAL'} · ${escapeHTML(group.display.replace('_',' '))}</small>`;
      section.appendChild(header);
      if (group.display === 'stepper') {
        for (const choice of group.choices) {
          const current = Number(state.selections[String(choice.id)]?.qty ?? choice.default_quantity);
          const item = document.createElement('div'); item.className = 'stepper-row';
          const text = document.createElement('div'); text.innerHTML = `<strong>${escapeHTML(choice.name)}</strong><small>${money(choice.price_delta)} / extra unit · included ${choice.default_quantity}${choice.deduct_below_default?' · credits enabled':''}</small>`;
          const actions = document.createElement('div'); actions.className = 'stepper-actions';
          const minus = document.createElement('button'); minus.type = 'button'; minus.textContent = '−'; minus.setAttribute('aria-label',`Remove one ${choice.name}`); minus.disabled = current <= 0;
          const number = document.createElement('span'); number.textContent = String(current); number.setAttribute('aria-live','polite');
          const plus = document.createElement('button'); plus.type = 'button'; plus.textContent = '+'; plus.setAttribute('aria-label',`Add one ${choice.name}`); plus.disabled = choice.max_quantity > 0 && current >= choice.max_quantity;
          const change = diff => { const next = Math.max(0,current+diff); if(choice.max_quantity && next > choice.max_quantity) return; state.selections[String(choice.id)]={level:null,qty:next}; renderGroups(); refreshQuote(); };
          minus.onclick = () => change(-1); plus.onclick = () => change(1);
          actions.append(minus,number,plus); item.append(text,actions); section.appendChild(item);
        }
      } else if (group.uses_levels) {
        for (const choice of group.choices) {
          const selected = state.selections[String(choice.id)];
          const row = document.createElement('div'); row.className = 'stepper-row';
          const title = document.createElement('strong'); title.textContent = choice.name;
          const select = document.createElement('select'); select.setAttribute('aria-label',`${choice.name} intensity`); select.style.maxWidth='200px'; select.style.marginTop='0';
          const off = document.createElement('option'); off.value = ''; off.textContent = 'Not selected'; select.appendChild(off);
          for(const level of group.levels){const opt = document.createElement('option'); opt.value = String(level.id); opt.textContent=level.name; select.appendChild(opt);}
          select.value = selected?.level == null ? '' : String(selected.level);
          select.onchange = () => {if(!select.value) delete state.selections[String(choice.id)]; else state.selections[String(choice.id)]={level:Number(select.value),qty:1}; renderGroups(); refreshQuote();};
          row.append(title,select); section.appendChild(row);
        }
      } else if (group.display === 'dropdown') {
        const select = document.createElement('select'); select.setAttribute('aria-label',group.name);
        const placeholder = document.createElement('option'); placeholder.value=''; placeholder.textContent = `Choose ${group.name.toLowerCase()}`; select.appendChild(placeholder);
        for (const choice of group.choices){const opt=document.createElement('option');opt.value=String(choice.id);opt.textContent=`${choice.name}${Number(choice.price_delta)?' · '+money(choice.price_delta):''}`;select.appendChild(opt);}
        select.value=String(groupSelected(group)[0]?.id ?? '');
        select.onchange = () => {removeGroup(group);if(select.value)state.selections[select.value]={level:null,qty:1}; renderGroups();refreshQuote();};
        section.appendChild(select);
      } else if (group.display === 'checkbox') {
        for (const choice of group.choices) {
          const row=document.createElement('label');row.className='checkbox-row';
          const cb=document.createElement('input');cb.type='checkbox';cb.checked=picked(choice.id);cb.onchange=()=>setChoice(group,choice,cb.checked);
          const label=document.createElement('span');label.textContent=choice.name+(Number(choice.price_delta)?` · +${money(choice.price_delta)}`:'');row.append(cb,label);section.appendChild(row);
        }
      } else {
        const row=document.createElement('div');row.className='choice-list';
        for(const choice of group.choices){
          const btn=document.createElement('button');btn.type='button';btn.className='choice-button';btn.setAttribute('aria-pressed',String(picked(choice.id)));
          btn.setAttribute('aria-label',choice.name);btn.onclick=()=>setChoice(group,choice,!picked(choice.id));
          if(group.display==='swatch' && choice.color){const dot=document.createElement('span');dot.className='swatch-dot';dot.style.backgroundColor=choice.color;btn.appendChild(dot);}
          const label=document.createElement('span');label.textContent=choice.name;btn.appendChild(label);
          if(Number(choice.price_delta)){const cost=document.createElement('span');cost.className='choice-cost';cost.textContent=`+${money(choice.price_delta)}`;btn.appendChild(cost);}
          row.appendChild(btn);
        }
        section.appendChild(row);
      }
      parent.appendChild(section);
    }
  };

  const renderQuote = quote => {
    const parent=$('receipt-rows');parent.replaceChildren();
    const line=(label,value,cls='')=>{const row=document.createElement('div');row.className=`receipt-line ${cls}`;const left=document.createElement('span');left.textContent=label;const right=document.createElement('strong');right.textContent=value;row.append(left,right);parent.appendChild(row);};
    line('Original product base',money(quote.base));
    for(const adjustment of quote.adjustments){const amount=Number(adjustment.amount);const label=adjustment.label_en||adjustment.label||adjustment.kind;line(label,`${amount<0?'−':'+'}${money(Math.abs(amount))}`,amount<0?'negative':'');}
    line('Subtotal · excl. VAT',money(quote.subtotal),'subtotal');
    line('VAT · 15%',money(quote.vat));
    $('receipt-total').textContent=money(quote.total);
  };


  const refreshQuote = async () => {
    const own = ++state.serial;
    const panel = document.querySelector('.receipt');
    const rows = $('receipt-rows');
    const error = $('quote-error');
    const freeze = $('snapshot-button');

    freeze.disabled = true;
    error.hidden = true;
    state.quote = null;

    panel.classList.add('is-updating');
    rows.setAttribute('aria-busy', 'true');

    // Keep the previous quote visible while Django
    // calculates the next one.
    try {
      const quote = await http('/api/quote/', {
        method: 'POST',
        body: JSON.stringify({
          product_slug: state.product.slug,
          selections: state.selections
        })
      });

      // Ignore outdated responses from earlier clicks.
      if (own !== state.serial) return;

      state.quote = quote;
      renderQuote(quote);
      freeze.disabled = false;

    } catch (err) {
      if (own !== state.serial) return;

      const hasOldQuote = Boolean(
        rows.querySelector('.receipt-line')
      );

      error.textContent = (
        hasOldQuote
          ? 'Could not update this quote. Previous figures are shown for reference only. '
          : 'Could not calculate this quote. '
      ) + err.message;

      error.hidden = false;

    } finally {
      if (own === state.serial) {
        panel.classList.remove('is-updating');
        rows.removeAttribute('aria-busy');
      }
    }
  };


  const loadProduct = async slug => {
    try{
      const product=await http(`/api/products/${encodeURIComponent(slug)}/`);
      state.product=product;state.selections=JSON.parse(JSON.stringify(product.defaults));
      $('snapshot-section').hidden=true;
      for(const b of $('product-switch').querySelectorAll('button'))b.setAttribute('aria-selected',String(b.dataset.slug===slug));
      const intro=$('product-intro');intro.replaceChildren();
      const avatar=document.createElement('span');avatar.className='product-avatar';avatar.style.backgroundColor=product.accent+'20';avatar.textContent=product.icon;
      const copy=document.createElement('div');const heading=document.createElement('h3');heading.textContent=product.title;const desc=document.createElement('p');desc.textContent=product.description;copy.append(heading,desc);intro.append(avatar,copy);
      renderGroups();await refreshQuote();
    }catch(err){$('option-groups').textContent=`Could not load product: ${err.message}`;}
  };

  const load = async () => {
    try{
      const data=await http('/api/products/');state.products=data.products;
      if (!data.products.length) throw new Error('No products. Run: python manage.py seed_demo');
      const switcher=$('product-switch');switcher.replaceChildren();
      for (const p of data.products) {
        const btn=document.createElement('button');btn.type='button';btn.className='product-tab';btn.role='tab';btn.dataset.slug=p.slug;btn.setAttribute('aria-selected','false');
        btn.innerHTML=`<span class="product-tab-icon">${escapeHTML(p.icon)}</span><span><strong>${escapeHTML(p.category)}</strong><small>${escapeHTML(p.title)}</small></span>`;
        btn.onclick=()=>loadProduct(p.slug);switcher.appendChild(btn);
      }
      await loadProduct(data.products[0].slug);
    }catch(err){$('product-switch').textContent=`Cannot connect to Django: ${err.message}`;$('option-groups').textContent='Start the server after following the README quick start.';}
  };

  $('snapshot-button').addEventListener('click', async()=>{
    if(!state.quote || !state.product)return;
    const button=$('snapshot-button');button.disabled=true;button.textContent='Freezing snapshot…';
    try{
      const data=await http('/api/snapshots/',{method:'POST',body:JSON.stringify({product_slug:state.product.slug,selections:state.selections})});
      $('snapshot-id').textContent=data.id;$('snapshot-link').href=`/api/snapshots/${data.id}/`;
      $('snapshot-section').hidden=false;$('snapshot-section').scrollIntoView({behavior:'smooth',block:'nearest'});
    }catch(err){$('quote-error').textContent=err.message;$('quote-error').hidden=false;}
    finally{button.disabled=false;button.innerHTML='Freeze this quote <span aria-hidden="true">↗</span>';}
  });
  applyTheme(document.documentElement.dataset.theme || 'light');

  $('theme-toggle').addEventListener('click', () => {
    const current = document.documentElement.dataset.theme || 'light';
    const next = current === 'dark' ? 'light' : 'dark';

    applyTheme(next);

    try {
      localStorage.setItem('mohd-theme', next);
    } catch {
      // Theme still works even when browser storage is unavailable.
    }
  });

  load();
})();
