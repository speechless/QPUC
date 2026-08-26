// ═══════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════
let G = null, SM = [], ESPs = [], WS = null;
let ptsModal = { delta: 1, pid: null };
let ffPidA = null, ffPidB = null;
let ngPlayers = [];
let ngSelectedBuzzers = {}; // index → buzzer_id
let fourPendingPid = null, fourSelectedTheme = null;
let fourInterval = null, ffInterval = null;
let srvOff = 0;

function srvNow() { return Date.now()/1000 + srvOff; }

// ═══════════════════════════════════════════
//  WEBSOCKET
// ═══════════════════════════════════════════
function connect() {
  WS = new WebSocket(`ws://${location.hostname}:8765/web`);
  WS.onopen  = () => document.getElementById('wsdot').classList.add('ok');
  WS.onclose = () => { document.getElementById('wsdot').classList.remove('ok'); setTimeout(connect, 3000); };
  WS.onmessage = e => {
    const d = JSON.parse(e.data);
    if (d.type === 'state') {
      if (d.server_now) srvOff = d.server_now - Date.now()/1000;
      G = d.game; SM = d.saves_meta || []; ESPs = d.esp_list.sort((a, b) => a.name.localeCompare(b.name)) || [];
      render();
    }
  };
}
function s(obj) { if (WS && WS.readyState === 1) WS.send(JSON.stringify(obj)); }
connect();

// ═══════════════════════════════════════════
//  RENDER
// ═══════════════════════════════════════════
function render() {
  if (!G) return;
  const PL = { setup:'Setup', '9pts':'9 Points', '4suite':'4 à la Suite', facaface:'Face à Face', egalite:'Départage', fin:'Fin' };
  document.getElementById('tp-phase').textContent = PL[G.phase] || G.phase;
  document.getElementById('tp-mode').textContent  = G.nine_mode === 'auto' ? 'Auto' : 'Manuel';

  ['9pts','4suite','facaface','egalite','fin'].forEach(ph =>
    document.getElementById(`nav-${ph}`)?.classList.toggle('active', G.phase === ph));

  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const VMP = { setup:'v-setup', '9pts':'v-9pts', '4suite':'v-4suite', facaface:'v-facaface', egalite:'v-egalite', fin:'v-fin' };
  document.getElementById(VMP[G.phase] || 'v-setup')?.classList.add('active');

  renderSidebar();
  if (G.phase === '9pts')     render9pts();
  if (G.phase === '4suite')   render4suite();
  if (G.phase === 'facaface') renderFF();
  if (G.phase === 'egalite')  renderEq();
  if (G.phase === 'fin')      renderFin();
  renderLog();
}

function renderSidebar() {
  if (!G) return;
  // Joueurs
  document.getElementById('sb-players').innerHTML = G.players.map(p => {
    const pts = Math.min(p.points, 9);
    const isW = G.winner_pid === p.id;
    const badge = p.qualified ? '<span class="sb-badge bq">✓</span>'
      : isW ? '<span class="sb-badge bbuzz">🔔</span>' : '';
    const cls = p.qualified ? 'qualified-row' : isW ? 'winner-row' : p.eliminated ? 'elim-row' : '';
    return `<div class="sb-player ${cls}"><div class="sb-name">${q(p.name)}</div>${badge}<div class="sb-pts">${pts}</div></div>`;
  }).join('');

  // Buzzers ESP
  const espEl = document.getElementById('sb-esp');
  if (ESPs.length === 0) {
    espEl.innerHTML = '<span style="color:var(--muted);font-size:12px">Aucun connecté</span>';
  } else {
    espEl.innerHTML = ESPs.map(e =>
      `<div class="esp-item"><div class="esp-dot"></div><div class="esp-name">${q(e.name)}</div><code style="font-size:10px;color:var(--muted)">${q(e.id)}</code></div>`
    ).join('');
  }

  // Thèmes
  document.getElementById('sb-themes').innerHTML = G.themes.map((t, i) =>
    `<div><span style="color:var(--muted)">${i+1}. </span>${i===3?'<span style="color:var(--gold);font-style:italic">Thème Mystère</span>':q(t||'—')}</div>`
  ).join('');
}

// ─── 9 POINTS ──────────────────────────────
function render9pts() {
  if (!G) return;
  const isManual = G.nine_mode === 'manual';
  document.getElementById('tog-mode').checked = isManual;
  document.getElementById('nine-qvbadge').textContent = G.q_value + ' pt' + (G.q_value > 1 ? 's' : '');
  document.getElementById('manual-card').style.display = isManual ? 'block' : 'none';

  const wrong = G.buzzed_wrong || [];
  const allWrong = G.round_active && !G.winner_pid && wrong.length > 0 &&
    G.players.filter(p => !p.qualified && !p.eliminated).every(p => wrong.includes(p.id));

  // Score list
  document.getElementById('nine-score-list').innerHTML = G.players.map(p => {
    const pts  = Math.min(p.points, 9);
    const isW  = G.winner_pid === p.id;
    const isWr = wrong.includes(p.id);
    const cls  = p.qualified ? 'qualified-row' : isW ? 'winner-row' : p.eliminated ? 'elim-row' : '';
    const bars = Array.from({length:9}, (_, i) =>
      `<div class="np-bar ${i<pts?(p.qualified?'on qbar':'on'):''}"></div>`).join('');
    const badge = p.qualified ? '<span class="np-badge nbq">✓ QUALIFIÉ</span>'
      : isW  ? '<span class="np-badge nbbuzz">🔔 BUZZÉ</span>'
      : isWr ? '<span class="np-badge nbwrong">✗ FAUX</span>' : '';

    return `<div class="nine-player ${cls}">
      <div>
        <div class="np-name">${q(p.name)}</div>
        <div class="np-bars" style="margin-top:4px">${bars}</div>
      </div>
      ${badge}
      <div class="np-pts">${pts}</div>
    </div>`;
  }).join('');

  // Buzzer status
  const winner = G.winner_pid ? G.players.find(p => p.id === G.winner_pid) : null;
  const bs = document.getElementById('nine-buzz-status');
  const va = document.getElementById('nine-validate-area');
  const awa = document.getElementById('nine-all-wrong-area');

  if (winner) {
    bs.innerHTML = `🔔 <b>${q(winner.name)}</b> a buzzé — valider ?`;
    va.innerHTML = `<div class="answer-grid">
      <button class="btn btn-correct" onclick="s({cmd:'nine_validate',pid:'${winner.id}',correct:true})">✓<span style="font-size:14px;font-weight:400;display:block;margin-top:2px">Correct (+${G.q_value}pt)</span></button>
      <button class="btn btn-wrong"   onclick="s({cmd:'nine_validate',pid:'${winner.id}',correct:false})">✗<span style="font-size:14px;font-weight:400;display:block;margin-top:2px">Faux</span></button>
    </div>`;
    awa.innerHTML = '';
  } else if (allWrong) {
    bs.innerHTML = `⚠️ <b>Tous ont répondu faux</b>`;
    va.innerHTML = '';
    awa.innerHTML = `<button class="btn btn-orange btn-full" style="margin-top:6px" onclick="s({cmd:'reset_round'})">↺ Reset buzzers — nouvelle question</button>`;
  } else if (G.round_active) {
    bs.innerHTML = `⏳ <b>Question ouverte</b> — en attente d'un buzzer…`;
    va.innerHTML = ''; awa.innerHTML = '';
  } else {
    bs.textContent = 'Prêt pour une nouvelle question.';
    va.innerHTML = ''; awa.innerHTML = '';
  }
}

// ─── 4 À LA SUITE ──────────────────────────
function render4suite() {
  if (!G) return;
  const done    = G.four_done_pids || [];
  const players = G.players.filter(p => !p.eliminated);
  const active  = G.four_current_pid;
  const picking = !active && !fourPendingPid;
  const theming = !active && !!fourPendingPid;

  document.getElementById('four-pick-card').style.display  = picking  ? 'block' : 'none';
  document.getElementById('four-theme-card').style.display = theming  ? 'block' : 'none';
  document.getElementById('four-turn-card').style.display  = active   ? 'block' : 'none';

  // Pick list
  document.getElementById('four-pick-list').innerHTML = players.map(p => {
    const isDone = done.includes(p.id);
    return `<button class="btn ${isDone?'btn-ghost':'btn-blue'}" ${isDone?'disabled':''} onclick="selectFourPlayer('${p.id}')">${q(p.name)}${isDone?' ✓':''}</button>`;
  }).join('');

  // Sélection thème
  if (theming) {
    const pp = G.players.find(pl => pl.id === fourPendingPid);
    document.getElementById('four-theme-label').textContent = `${pp?pp.name:'—'} — Choisir un thème`;
    const taken = G.four_themes_taken || [];
    document.getElementById('four-theme-grid').innerHTML = G.themes.map((t, i) => {
      const isTaken = taken.includes(i);
      const isMystery = i === 3;
      const isSel = fourSelectedTheme === i;
      return `<div class="theme-tile ${isTaken?'taken':''} ${isMystery?'mystery':''} ${isSel?'selected':''}"
        onclick="${isTaken?'':'selectTheme('+i+')'}">${isTaken?'<span style="text-decoration:line-through">':''
        }${isMystery?'Thème Mystère':q(t||'Thème '+(i+1))}${isTaken?'</span>':''}</div>`;
    }).join('');
    document.getElementById('btn-start-after-theme').style.display = fourSelectedTheme !== null ? 'block' : 'none';
  }

  // Tour actif
  if (active) {
    const p = G.players.find(pl => pl.id === active);
    document.getElementById('four-turn-label').textContent = `Tour de ${p ? p.name : '—'}`;
    document.getElementById('four-score-cur').textContent = G.four_score || 0;
    document.getElementById('four-score-best').textContent = G.four_best || 0;

    // Dots
    const cur  = G.four_score || 0;
    const best = G.four_best  || 0;
    document.getElementById('four-dots-main').innerHTML = Array.from({length:4}, (_, i) => {
      const cls = i < cur ? 'on' : i < best ? 'best-only' : '';
      return `<div class="fdot ${cls}">✓</div>`;
    }).join('');

    clearInterval(fourInterval);
    tickFour();
    if (G.four_timer_running) fourInterval = setInterval(tickFour, 300);
  }
}
function selectFourPlayer(pid) { fourPendingPid = pid; fourSelectedTheme = null; render4suite(); }
function selectTheme(i) { fourSelectedTheme = i; render4suite(); }
function confirmThemeAndStart() {
  if (fourSelectedTheme === null || !fourPendingPid) return;
  s({ cmd:'four_choose_theme', pid:fourPendingPid, theme_index:fourSelectedTheme });
  s({ cmd:'four_start', pid:fourPendingPid });
  fourPendingPid = null; fourSelectedTheme = null;
}
function tickFour() {
  if (!G) return;
  const rem = Math.max(0, G.four_timer_end - srvNow());
  const el  = document.getElementById('four-chrono');
  if (!el) return;
  el.textContent = Math.ceil(rem);
  el.className = 'chrono-big ' + (rem <= 5 ? 'danger' : rem <= 15 ? 'warn' : 'ok');
}

// ─── FACE À FACE ────────────────────────────
function renderFF() {
  if (!G) return;
  document.getElementById('ff-target').textContent = G.ff_total_target || 12;
  const ready = G.ff_player_a && G.ff_player_b;
  document.getElementById('ff-setup-card').style.display = ready ? 'none' : 'block';
  document.getElementById('ff-duel-card').style.display  = ready ? 'block' : 'none';

  if (!ready) {
    const players = G.players.filter(p => !p.eliminated);
    ['a','b'].forEach(side => {
      const curPid = side === 'a' ? ffPidA : ffPidB;
      document.getElementById(`ff-pick-${side}`).innerHTML = players.map(p =>
        `<div class="ff-sel-btn ${curPid===p.id?'sel':''}" onclick="ffSel('${side}','${p.id}')">${q(p.name)}</div>`
      ).join('');
    });
    return;
  }

  const pa = G.players.find(p => p.id === G.ff_player_a);
  const pb = G.players.find(p => p.id === G.ff_player_b);
  const sa = (G.ff_scores||{})[G.ff_player_a]||0;
  const sb = (G.ff_scores||{})[G.ff_player_b]||0;
  document.getElementById('ff-na').textContent = pa?pa.name:'—';
  document.getElementById('ff-nb').textContent = pb?pb.name:'—';
  document.getElementById('ff-sa').textContent = sa;
  document.getElementById('ff-sb').textContent = sb;

  const buzzed = G.ff_buzzed_pid;
  const active = G.ff_active_pid;
  document.getElementById('ff-pane-a').className = 'ff-pane' + (buzzed===G.ff_player_a?' fb':active===G.ff_player_a?' fa':'');
  document.getElementById('ff-pane-b').className = 'ff-pane' + (buzzed===G.ff_player_b?' fb':active===G.ff_player_b?' fa':'');

  // Zone bar
  const zonePts = G.ff_zone_pts || 4;
  [4,3,2,1].forEach(z => document.getElementById(`fz${z}`)?.classList.toggle('active', z === zonePts));
  document.getElementById('ff-pts-badge').textContent = G.ff_timer_running
    ? `Vaut ${zonePts} pt${zonePts>1?'s':''} maintenant`
    : '— Lancez une question pour démarrer le chrono';

  // Buzz status
  const bs  = document.getElementById('ff-buzz-status');
  const ffg = document.getElementById('ff-answer-grid');
  if (buzzed) {
    const bp = G.players.find(p => p.id === buzzed);
    bs.innerHTML = `🔔 <b>${q(bp?bp.name:buzzed)}</b> buzze ! (${G.ff_current_pts||zonePts} pts)`;
    ffg.style.display = 'grid';
  } else if (G.ff_timer_running) {
    const ap = G.players.find(p => p.id === active);
    bs.innerHTML = `⏳ <b>${q(ap?ap.name:'—')}</b> a la main`;
    ffg.style.display = 'none';
  } else {
    bs.textContent = 'Appuyez sur ▶ pour lancer la question';
    ffg.style.display = 'none';
  }

  clearInterval(ffInterval);
  tickFF();
  if (G.ff_timer_running) ffInterval = setInterval(tickFF, 200);
}
function ffSel(side, pid) { if (side==='a') ffPidA=pid; else ffPidB=pid; renderFF(); }
function setupFF() {
  if (!ffPidA || !ffPidB || ffPidA===ffPidB) { alert('Sélectionne 2 joueurs différents'); return; }
  s({ cmd:'ff_setup', pid_a:ffPidA, pid_b:ffPidB });
}
function tickFF() {
  if (!G) return;
  const rem = Math.max(0, G.ff_timer_end - srvNow());
  const el  = document.getElementById('ff-chrono');
  if (!el) return;
  el.textContent = Math.ceil(rem);
  el.className = 'chrono-big ' + (rem <= 4 ? 'danger' : rem <= 8 ? 'warn' : 'ok');
}

// ─── ÉGALITÉ ────────────────────────────────
function renderEq() {
  if (!G) return;
  const eqPids = G.eq_pids||[], eqSc = G.eq_scores||{}, wid = G.winner_pid;
  document.getElementById('eq-list').innerHTML = eqPids.map(pid => {
    const p  = G.players.find(pl => pl.id === pid);
    const sc = eqSc[pid]||0;
    const isW = wid === pid;
    return `<div class="eq-player ${isW?'winner-row':''}">
      <div class="np-name">${q(p?p.name:pid)}</div>
      ${isW?'<span class="np-badge nbbuzz">🔔</span>':''}
      <div class="np-pts" style="margin-left:auto">${sc}/2</div>
    </div>`;
  }).join('');

  const winner = wid ? G.players.find(p => p.id === wid) : null;
  const bs = document.getElementById('eq-buzz-status');
  const va = document.getElementById('eq-validate-area');
  if (winner) {
    bs.innerHTML = `🔔 <b>${q(winner.name)}</b> — valider ?`;
    va.innerHTML = `<div class="answer-grid">
      <button class="btn btn-correct" onclick="s({cmd:'eq_answer',correct:true})">✓<span style="font-size:14px;font-weight:400;display:block;margin-top:2px">Correct</span></button>
      <button class="btn btn-wrong"   onclick="s({cmd:'eq_answer',correct:false})">✗<span style="font-size:14px;font-weight:400;display:block;margin-top:2px">Faux</span></button>
    </div>`;
  } else { bs.textContent = 'En attente d\'un buzzer…'; va.innerHTML=''; }
}

// ─── FIN ────────────────────────────────────
function renderFin() {
  if (!G) return;
  const qs = G.players.filter(p => p.qualified);
  document.getElementById('fin-content').innerHTML = qs.length
    ? qs.map(p => `<b style="color:var(--gold)">${q(p.name)}</b>`).join(' &amp; ')
    : '<span style="color:var(--muted)">—</span>';
}

// ─── LOG ─────────────────────────────────────
function renderLog() {
  if (!G) return;
  document.getElementById('log-wrap').innerHTML = [...(G.history||[])].reverse().slice(0,40).map(e =>
    `<div class="log-entry"><span class="lt">${e.t}</span>${q(e.msg)}</div>`).join('');
}

// ═══════════════════════════════════════════
//  NAVIGATION
// ═══════════════════════════════════════════
function goPhase(ph) {
  if (!confirm(`Passer en phase "${ph}" ?`)) return;
  s({ cmd:'set_phase', phase:ph });
}
function toggleMode(el) { s({ cmd:'nine_set_mode', mode: el.checked?'manual':'auto' }); }

// ═══════════════════════════════════════════
//  MODALS
// ═══════════════════════════════════════════
function openModal(id) {
  document.getElementById(id).classList.remove('hidden');
  if (id === 'm-new')   initNG();
  if (id === 'm-saves') renderSaves();
  if (id === 'm-pts')   initPtsModal();
}
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }
document.querySelectorAll('.modal-bg').forEach(m =>
  m.addEventListener('click', e => { if (e.target===m) m.classList.add('hidden'); }));

// ─── Nouvelle partie ────────────────────────
function initNG() {
  ngPlayers = [{name:'',bid:''},{name:'',bid:''}];
  ngSelectedBuzzers = {};
  renderNG();
  document.getElementById('ng-themes').innerHTML = Array.from({length:4}, (_,i) =>
    `<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
      <span style="font-size:12px;color:var(--muted);width:88px;flex-shrink:0">${i===3?'Mystère':'Thème '+(i+1)}</span>
      <input class="inp" id="ngt-${i}" placeholder="${i===3?'(caché côté public)':'Thème '+(i+1)}">
    </div>`).join('');
}
function renderNG() {
  document.getElementById('ng-players').innerHTML = ngPlayers.map((p, i) => {
    // Liste des buzzers disponibles pour ce joueur
    const bzList = ESPs.length === 0
      ? `<input class="inp" placeholder="buzzer1…" value="${q(p.bid||'')}" oninput="ngPlayers[${i}].bid=this.value" style="width:110px">`
      : `<select class="inp" style="width:130px" onchange="ngPlayers[${i}].bid=this.value">
          <option class="inp-option" value="">-- Buzzer --</option>
          ${ESPs.map(e => `<option class="inp-option" value="${q(e.id)}" ${p.bid===e.id?'selected':''}>${q(e.name)}</option>`).join('')}
        </select>`;
    return `<div style="display:flex;align-items:center;gap:7px;margin-bottom:7px">
      <input class="inp" placeholder="Nom ${i+1}" value="${q(p.name||'')}" oninput="ngPlayers[${i}].name=this.value" style="flex:1">
      ${bzList}
      ${i>=2?`<button class="btn btn-red" style="padding:8px 10px;font-size:13px" onclick="ngRem(${i})">✕</button>`:''}
    </div>`;
  }).join('');
}
function ngAdd() { if (ngPlayers.length>=4) return alert('4 joueurs max'); ngPlayers.push({name:'',bid:''}); renderNG(); }
function ngRem(i) { ngPlayers.splice(i,1); renderNG(); }
function ngSubmit() {
  const players = ngPlayers.filter(p => p.name.trim()).map(p => ({name:p.name.trim(), buzzer_id:p.bid||''}));
  if (players.length < 2) return alert('Au moins 2 joueurs requis');
  const themes = Array.from({length:4}, (_,i) => document.getElementById(`ngt-${i}`)?.value.trim()||'');
  s({ cmd:'setup_game', players, themes });
  closeModal('m-new');
}

// ─── Sauvegardes ────────────────────────────
function renderSaves() {
  const el = document.getElementById('saves-list');
  if (!SM.length) { el.innerHTML='<div style="color:var(--muted);font-size:13px">Aucune partie sauvegardée.</div>'; return; }
  el.innerHTML = [...SM].reverse().map(sv =>
    `<div class="save-item" onclick="loadSave('${sv.game_id}')">
      <div class="save-name">${q((sv.players||[]).join(', '))} ${sv.finished?'✓':''}</div>
      <div class="save-meta">${sv.created_at} · ${sv.phase} · ${sv.game_id}</div>
    </div>`).join('');
}
function loadSave(gid) {
  if (!confirm('Charger cette partie ?')) return;
  s({ cmd:'load_game', game_id:gid }); closeModal('m-saves');
}

// ─── Points manuels ─────────────────────────
function initPtsModal() {
  ptsModal = { delta:1, pid:null };
  document.querySelectorAll('.pts-tile').forEach(t => t.classList.remove('sel'));
  document.getElementById('pt-1')?.classList.add('sel');
  if (!G) return;
  document.getElementById('m-pts-players').innerHTML = G.players.filter(p=>!p.qualified&&!p.eliminated).map(p =>
    `<div class="player-pick" onclick="selPid('${p.id}')">${q(p.name)} (${Math.min(p.points,9)}/9)</div>`).join('');
}
function selDelta(d) {
  ptsModal.delta = d;
  document.querySelectorAll('.pts-tile').forEach(t => t.classList.remove('sel'));
  document.getElementById(`pt-${d > 0 ? d : d}`)?.classList.add('sel');
  // Refresh player list
  document.getElementById('m-pts-players').querySelectorAll('.player-pick').forEach(el => el.classList.remove('sel'));
  if (ptsModal.pid) document.querySelector(`.player-pick[onclick*="${ptsModal.pid}"]`)?.classList.add('sel');
}
function selPid(id) {
  ptsModal.pid = id;
  document.getElementById('m-pts-players').querySelectorAll('.player-pick').forEach(el => el.classList.remove('sel'));
  document.getElementById('m-pts-players').querySelector(`[onclick*="${id}"]`)?.classList.add('sel');
}
function confirmPts() {
  if (!ptsModal.pid) return alert('Choisis un joueur');
  s({ cmd:'nine_adjust', pid:ptsModal.pid, delta:ptsModal.delta });
  closeModal('m-pts');
}

// ═══════════════════════════════════════════
//  UTILS
// ═══════════════════════════════════════════
function q(s) { return String(s||'').replace(/[<>&"]/g, c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c])); }