(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const CH = window.WTC_CHANNELS;
  const COLORS = ['#ffe600', '#ff3b30', '#ff9f0a', '#ff2d95', '#00e5ff', '#b6ff3b'];
  const pad = n => String(n).padStart(2, '0');
  const store = {
    get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} },
  };

  // ---------- state ----------
  let player = null, ready = false, on = false, playing = false;
  let muted = store.get('wtc.muted') === '1';
  let chIdx = Math.min(Math.max(+store.get('wtc.ch', 0) || 0, 0), CH.length - 1);
  const ok = {};            // videoId -> true/false once verified embeddable
  const queues = {};        // channel num -> upcoming videos
  let current = null, failStreak = 0, announced = '', timers = [], poll = null, stall = null, checked = 0, total = 0;

  const later = (fn, ms) => { const t = setTimeout(fn, ms); timers.push(t); return t; };
  const clearTimers = () => { timers.forEach(clearTimeout); timers = []; };
  const shuffle = a => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.random() * (i + 1) | 0; [a[i], a[j]] = [a[j], a[i]]; } return a; };

  // ---------- verify videos can actually be embedded (YouTube oEmbed: 401/404 = blocked/removed) ----------
  const norm = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
  async function verify(v) {
    const [id, artist, title] = v;
    try {
      const r = await fetch('https://www.youtube.com/oembed?format=json&url=' + encodeURIComponent('https://www.youtube.com/watch?v=' + id));
      if (r.status === 401 || r.status === 403 || r.status === 404) ok[id] = false;
      else if (r.ok) {
        const j = await r.json(), hay = norm(j.title + ' ' + j.author_name);
        const toks = norm(artist + ' ' + title).split(' ').filter(t => t.length >= 4);
        ok[id] = toks.length ? toks.some(t => hay.includes(t)) : true;   // drops wrong/mislabelled IDs
      }
    } catch { /* offline / CORS: leave unknown, the player's own error handler decides */ }
    checked++; renderStatus();
  }
  function verifyAll() {
    const seen = new Set(), list = [];
    CH.forEach(c => c.videos.forEach(v => { if (!seen.has(v[0])) { seen.add(v[0]); list.push(v); } }));
    total = list.length;
    // current channel first, 6 at a time
    list.sort((a, b) => CH[chIdx].videos.includes(b) - CH[chIdx].videos.includes(a));
    let i = 0; const worker = async () => { while (i < list.length) await verify(list[i++]); };
    for (let k = 0; k < 6; k++) worker();
  }
  function renderStatus() {
    const good = Object.values(ok).filter(Boolean).length, bad = Object.values(ok).filter(x => x === false).length;
    $('status').textContent = checked >= total && total ? `${good} videos verified playable${bad ? ` · ${bad} blocked by YouTube, skipped` : ''}` : `checking videos… ${checked}/${total}`;
  }

  // ---------- queue ----------
  function pick(chan, avoidId) {
    const q = queues[chan.num] || (queues[chan.num] = []);
    for (let tries = 0; tries < chan.videos.length * 2 + 2; tries++) {
      if (!q.length) { const f = shuffle(chan.videos); if (f[0][0] === avoidId && f.length > 1) f.push(f.shift()); q.push(...f); }
      const v = q.shift();
      if (ok[v[0]] !== false) return v;
    }
    return null;
  }
  const peek = chan => { const q = queues[chan.num] || []; return q.find(v => ok[v[0]] !== false) || null; };

  // ---------- visuals ----------
  const snow = $('snow'), sctx = snow.getContext('2d'); let snowRaf = 0;
  function drawSnow() {
    const w = snow.width = 192, h = snow.height = 108, img = sctx.createImageData(w, h);
    for (let i = 0; i < img.data.length; i += 4) { const v = Math.random() * 255 | 0; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
    sctx.putImageData(img, 0, 0); snowRaf = requestAnimationFrame(drawSnow);
  }
  function burst(ms) { snow.classList.add('on'); cancelAnimationFrame(snowRaf); drawSnow(); later(() => { snow.classList.remove('on'); cancelAnimationFrame(snowRaf); }, ms); }
  function showIdent(sub, ms) { $('identSub').textContent = sub; $('ident').classList.add('show'); later(() => $('ident').classList.remove('show'), ms); }
  function showOSD() {
    $('osdNum').textContent = pad(CH[chIdx].num); $('osdName').textContent = CH[chIdx].name; $('osd').classList.add('show');
    clearTimeout(showOSD.t); showOSD.t = setTimeout(() => $('osd').classList.remove('show'), 3500);
  }
  function lower(kick, artist, title, ms) {
    $('lowKick').textContent = kick; $('lowArtist').textContent = artist; $('lowTitle').textContent = title;
    $('lower').classList.add('show'); clearTimeout(lower.t); lower.t = setTimeout(() => $('lower').classList.remove('show'), ms);
  }
  function renderNow() {
    const c = CH[chIdx];
    $('nowCh').textContent = `CH ${pad(c.num)} · ${c.name}`;
    if (current) { $('nowArtist').textContent = current[1]; $('nowTitle').textContent = '“' + current[2] + '”'; $('nowYear').textContent = current[3]; }
    const n = peek(c); $('nextTxt').textContent = n ? `${n[1]} — ${n[2]}` : '—';
    const items = [`NOW ON ${c.name}`, current ? `${current[1]} · ${current[2]}` : c.tag, n ? `UP NEXT: ${n[1]} — ${n[2]}` : '', 'WTC · MUSIC TELEVISION'].filter(Boolean);
    const html = items.map(t => `<span>★ ${t.replace(/</g, '&lt;')}</span>`).join('');
    $('ticker').innerHTML = html + html;
    document.querySelectorAll('.ch').forEach((b, i) => b.classList.toggle('on', i === chIdx));
  }
  function showNotice(msg) {
    $('noticeMsg').textContent = msg;
    const l = $('noticeLink'); if (current) { l.href = 'https://www.youtube.com/watch?v=' + current[0]; l.hidden = false; } else l.hidden = true;
    $('notice').hidden = false;
  }

  // ---------- playback ----------
  function load(v) {
    current = v; announced = ''; $('tapplay').hidden = true; $('notice').hidden = true;
    clearInterval(poll); clearTimeout(stall);
    if (!ready) return;
    player.loadVideoById(v[0]);                       // called directly inside the tap -> mobile autoplay allowed
    muted ? player.mute() : player.unMute();
    // if the browser refused autoplay, offer a big tap-to-play button
    stall = setTimeout(() => { if (!playing) $('tapplay').hidden = false; }, 4000);
    renderNow();
  }
  function playNext(kind) {
    const v = pick(CH[chIdx], current && current[0]);
    if (!v) { current = null; showNotice('YouTube is blocking every video on this channel from playing here. Try another channel.'); return; }
    load(v);
  }
  function tune(i, instant) {
    chIdx = (i + CH.length) % CH.length; store.set('wtc.ch', chIdx);
    clearTimers(); $('lower').classList.remove('show'); failStreak = 0; playing = false;
    burst(600); showOSD(); showIdent(CH[chIdx].tag.toUpperCase(), instant ? 900 : 1300);
    playNext();
  }
  function onState(e) {
    const S = YT.PlayerState;
    if (e.data === S.PLAYING) {
      playing = true; failStreak = 0; clearTimeout(stall); $('tapplay').hidden = true; $('notice').hidden = true;
      $('btnPlay').textContent = '❚❚';
      if (current && announced !== current[0]) { announced = current[0]; later(() => lower('NOW PLAYING', current[1], '“' + current[2] + '” · ' + current[3], 8000), 1400); }
      clearInterval(poll);
      poll = setInterval(() => {
        const d = player.getDuration(), t = player.getCurrentTime(), n = peek(CH[chIdx]);
        if (n && d > 25 && d - t < 12 && d - t > 10.2) lower('UP NEXT', n[1], '“' + n[2] + '”', 8000);
      }, 400);
    } else if (e.data === S.PAUSED) { playing = false; $('btnPlay').textContent = '▶'; }
    else if (e.data === S.ENDED) {
      playing = false; clearInterval(poll); $('lower').classList.remove('show');
      burst(350); showIdent('WTC · MUSIC TELEVISION', 1300); playNext();
    }
  }
  function onError(e) {
    // 2 bad id · 5 html5 error · 100 removed · 101/150 embedding not allowed
    if (current) ok[current[0]] = false;
    if (++failStreak > 12) { showNotice('Couldn’t play any videos. Check your connection, or open this one on YouTube.'); return; }
    later(() => playNext(), 150);
  }

  // ---------- controls ----------
  const act = {
    up: () => on && tune(chIdx + 1), down: () => on && tune(chIdx - 1),
    skip: () => { if (!on) return; burst(450); failStreak = 0; playNext(); },
    play: () => { if (!ready || !on) return; player.getPlayerState() === 1 ? player.pauseVideo() : player.playVideo(); },
    mute: () => { muted = !muted; store.set('wtc.muted', muted ? '1' : '0'); if (ready) muted ? player.mute() : player.unMute(); $('muteIcon').textContent = muted ? '🔇' : '🔊'; },
    full: () => { const s = $('stage'); document.fullscreenElement ? document.exitFullscreen() : (s.requestFullscreen || s.webkitRequestFullscreen || (() => {})).call(s); },
  };
  $('btnNext').onclick = act.up; $('btnPrev').onclick = act.down; $('btnSkip').onclick = act.skip;
  $('btnPlay').onclick = act.play; $('btnMute').onclick = act.mute; $('btnFull').onclick = act.full;
  $('tapplay').onclick = () => { $('tapplay').hidden = true; try { player.playVideo(); } catch {} };
  $('noticeRetry').onclick = () => { $('notice').hidden = true; failStreak = 0; playNext(); };
  if (!(document.fullscreenEnabled || document.webkitFullscreenEnabled)) $('btnFull').hidden = true;
  $('muteIcon').textContent = muted ? '🔇' : '🔊';
  addEventListener('keydown', e => {
    const k = e.key.toLowerCase();
    if (k === 'arrowright' || k === 'arrowup') act.up(); else if (k === 'arrowleft' || k === 'arrowdown') act.down();
    else if (k === 'n') act.skip(); else if (k === 'm') act.mute(); else if (k === 'f') act.full(); else if (k === ' ') { e.preventDefault(); act.play(); }
    else if (/^[1-9]$/.test(k) && on) { const i = CH.findIndex(c => c.num === +k); if (i >= 0) tune(i); }
  });
  // swipe the picture up/down to change channel; tap to show channel + song
  let ty = null;
  const sh = $('shield');
  sh.addEventListener('touchstart', e => { ty = e.touches[0].clientY; }, { passive: true });
  sh.addEventListener('touchend', e => {
    if (ty == null) return; const dy = e.changedTouches[0].clientY - ty; ty = null;
    if (dy < -50) act.up(); else if (dy > 50) act.down(); else if (on && current) { showOSD(); lower('NOW PLAYING', current[1], '“' + current[2] + '” · ' + current[3], 5000); }
  }, { passive: true });
  sh.addEventListener('click', e => { if (e.pointerType === 'mouse' && on && current) { showOSD(); lower('NOW PLAYING', current[1], '“' + current[2] + '” · ' + current[3], 5000); } });

  // ---------- channel chips ----------
  const rail = $('channels');
  CH.forEach((c, i) => {
    const b = document.createElement('button');
    b.className = 'ch'; b.style.setProperty('--c', COLORS[i % COLORS.length]); b.setAttribute('role', 'listitem');
    b.innerHTML = `<span class="n">${pad(c.num)}</span><span class="nm"></span><span class="tg"></span>`;
    b.querySelector('.nm').textContent = c.name.replace('WTC ', ''); b.querySelector('.tg').textContent = c.tag;
    b.onclick = () => { if (on) tune(i); else { chIdx = i; renderNow(); } };
    rail.append(b);
  });
  renderNow(); verifyAll();

  // ---------- boot ----------
  window.onYouTubeIframeAPIReady = () => {
    player = new YT.Player('player', {
      width: '100%', height: '100%',
      playerVars: { controls: 0, disablekb: 1, modestbranding: 1, rel: 0, playsinline: 1, iv_load_policy: 3, fs: 0, origin: location.origin },
      events: { onReady: () => { ready = true; if (on && !current) tune(chIdx, true); }, onStateChange: onState, onError },
    });
  };
  const sc = document.createElement('script'); sc.src = 'https://www.youtube.com/iframe_api';
  sc.onerror = () => { $('splash').classList.add('off'); showNotice('Can’t reach YouTube. Check your connection and reload.'); };
  document.head.append(sc);

  $('splash').onclick = () => {
    on = true; $('splash').classList.add('off');
    if (ready) tune(chIdx); else { burst(500); showIdent(CH[chIdx].tag.toUpperCase(), 1500); showOSD(); }
  };
})();
