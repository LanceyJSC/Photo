(() => {
  const $ = id => document.getElementById(id);
  const channels = window.WTC_CHANNELS;
  const el = { power:$('power'), osd:$('osd'), osdCh:$('osdCh'), osdName:$('osdName'), lower:$('lower'),
    lowArtist:$('lowArtist'), lowTitle:$('lowTitle'), lowMeta:$('lowMeta'), ident:$('ident'), identSub:$('identSub'),
    nosignal:$('nosignal'), nsText:$('nsText'), stat:$('static'), guide:$('guide'), guideList:$('guideList') };

  const store = {
    get(k, d){ try { return localStorage.getItem(k) ?? d; } catch { return d; } },
    set(k, v){ try { localStorage.setItem(k, v); } catch {} },
  };

  let player, apiReady = false, on = false, muted = store.get('wtc.muted') === '1';
  let chIdx = Math.min(+store.get('wtc.ch', 0) || 0, channels.length - 1);
  let queues = {}, current = null, timers = [], poll = null, shownUp = false, failStreak = 0;

  // ---------- helpers ----------
  const later = (fn, ms) => { const t = setTimeout(fn, ms); timers.push(t); return t; };
  const clearTimers = () => { timers.forEach(clearTimeout); timers = []; clearInterval(poll); };
  const shuffle = a => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.random() * (i + 1) | 0; [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const pad = n => String(n).padStart(2, '0');

  function nextVideo(ch) {
    const q = queues[ch.num] || (queues[ch.num] = []);
    if (!q.length) {
      let fresh = shuffle(ch.videos);
      if (current && fresh[0] === current.v && fresh.length > 1) fresh.push(fresh.shift());
      q.push(...fresh);
    }
    return q.shift();
  }

  // ---------- TV static ----------
  const ctx = el.stat.getContext('2d');
  let staticRaf = 0;
  function drawStatic() {
    const w = el.stat.width = 160, h = el.stat.height = 90;
    const img = ctx.createImageData(w, h);
    for (let i = 0; i < img.data.length; i += 4) { const v = Math.random() * 255 | 0; img.data[i] = img.data[i+1] = img.data[i+2] = v; img.data[i+3] = 255; }
    ctx.putImageData(img, 0, 0);
    staticRaf = requestAnimationFrame(drawStatic);
  }
  function staticBurst(ms = 600) {
    el.stat.classList.add('on'); cancelAnimationFrame(staticRaf); drawStatic();
    later(() => { el.stat.classList.remove('on'); cancelAnimationFrame(staticRaf); }, ms);
  }

  // ---------- overlays ----------
  function showOSD() {
    const ch = channels[chIdx];
    el.osdCh.textContent = pad(ch.num); el.osdName.textContent = ch.name; el.osd.hidden = false;
    clearTimeout(showOSD.t); showOSD.t = setTimeout(() => el.osd.hidden = true, 3500);
  }
  function showLower(ms = 8000) {
    if (!current) return;
    const [, artist, title, year] = current.v;
    el.lowArtist.textContent = artist; el.lowTitle.textContent = `“${title}”`;
    el.lowMeta.textContent = `${year} · ${channels[chIdx].name}`;
    el.lower.classList.add('show');
    clearTimeout(showLower.t); showLower.t = setTimeout(() => el.lower.classList.remove('show'), ms);
  }
  function showIdent(sub, ms) {
    el.identSub.textContent = sub; el.ident.classList.add('show');
    later(() => el.ident.classList.remove('show'), ms);
  }
  function setNoSignal(msg) { el.nsText.textContent = msg || 'NO SIGNAL'; el.nosignal.hidden = !msg && msg !== ''; }

  // ---------- playback ----------
  function tune(i, { ident = false } = {}) {
    clearTimers(); el.lower.classList.remove('show'); el.nosignal.hidden = true;
    chIdx = (i + channels.length) % channels.length; store.set('wtc.ch', chIdx);
    const ch = channels[chIdx];
    staticBurst(650); showOSD(); renderGuide();
    if (ident) showIdent(ch.tag.toUpperCase(), 1800);
    later(() => playNext(), ident ? 1900 : 450);
  }

  function playNext() {
    const ch = channels[chIdx];
    const v = nextVideo(ch);
    current = { v, ch: ch.num }; shownUp = false;
    if (!apiReady) return;
    player.loadVideoById({ videoId: v[0] });
    player.setVolume(100); muted ? player.mute() : player.unMute();
    renderGuide();
  }

  function startPoll() {
    clearInterval(poll);
    poll = setInterval(() => {
      if (!player || !player.getDuration) return;
      const d = player.getDuration(), t = player.getCurrentTime();
      if (d > 20 && d - t < 12 && !shownUp) {
        shownUp = true;
        const q = queues[channels[chIdx].num] || [];
        if (q.length) { const n = q[0]; el.lowArtist.textContent = 'UP NEXT'; el.lowTitle.textContent = `${n[1]} — “${n[2]}”`; el.lowMeta.textContent = channels[chIdx].name; el.lower.classList.add('show'); clearTimeout(showLower.t); showLower.t = setTimeout(() => el.lower.classList.remove('show'), 9000); }
      }
    }, 500);
  }

  function onState(e) {
    const S = YT.PlayerState;
    if (e.data === S.PLAYING) {
      failStreak = 0; el.nosignal.hidden = true;
      if (!onState.announced || onState.announced !== current.v[0]) { onState.announced = current.v[0]; later(() => showLower(), 1500); }
      startPoll();
    } else if (e.data === S.ENDED) {
      clearInterval(poll); el.lower.classList.remove('show');
      showIdent('WTC · MUSIC TELEVISION', 1600); staticBurst(350);
      later(playNext, 1700);
    }
  }
  function onError() {
    // Unavailable / embedding disabled: skip to the next one.
    if (++failStreak > channels[chIdx].videos.length) { setNoSignal('NO SIGNAL — CHECK CONNECTION'); return; }
    playNext();
  }

  // ---------- guide / remote ----------
  function renderGuide() {
    el.guideList.innerHTML = '';
    channels.forEach((c, i) => {
      const li = document.createElement('li'), b = document.createElement('button');
      b.className = i === chIdx ? 'cur' : '';
      const now = i === chIdx && current ? `Now: ${current.v[1]} — ${current.v[2]}` : c.tag;
      b.innerHTML = `<span class="n">${pad(c.num)}</span><span>${c.name}</span><span class="t"></span>`;
      b.querySelector('.t').textContent = now;
      b.onclick = () => { if (!on) return; tune(i, { ident: true }); };
      li.append(b); el.guideList.append(li);
    });
  }
  const full = () => { const tv = $('tv'); document.fullscreenElement ? document.exitFullscreen() : (tv.requestFullscreen?.() || tv.webkitRequestFullscreen?.()); };
  const toggleMute = () => { muted = !muted; store.set('wtc.muted', muted ? '1' : '0'); if (apiReady) muted ? player.mute() : player.unMute(); $('btnMute').textContent = muted ? 'UNMUTE' : 'MUTE'; };
  const act = {
    up: () => on && tune(chIdx + 1, { ident: true }),
    down: () => on && tune(chIdx - 1, { ident: true }),
    skip: () => { if (!on) return; clearTimers(); staticBurst(400); later(playNext, 350); },
    mute: toggleMute, guide: () => el.guide.hidden = !el.guide.hidden, full,
  };
  $('btnNext').onclick = act.up; $('btnPrev').onclick = act.down; $('btnSkip').onclick = act.skip;
  $('btnMute').onclick = act.mute; $('btnGuide').onclick = act.guide; $('btnFull').onclick = act.full;
  $('btnMute').textContent = muted ? 'UNMUTE' : 'MUTE';
  addEventListener('keydown', e => {
    const k = e.key.toLowerCase();
    if (k === 'arrowright' || k === 'arrowup') act.up();
    else if (k === 'arrowleft' || k === 'arrowdown') act.down();
    else if (k === 'n') act.skip(); else if (k === 'm') act.mute(); else if (k === 'g') act.guide(); else if (k === 'f') act.full();
    else if (/^[1-9]$/.test(k) && on) { const i = channels.findIndex(c => c.num === +k); if (i >= 0) tune(i, { ident: true }); }
    else if ((k === ' ' || k === 'enter') && on && e.target === document.body) { const s = player.getPlayerState(); s === 1 ? player.pauseVideo() : player.playVideo(); }
  });

  // ---------- boot ----------
  renderGuide();
  window.onYouTubeIframeAPIReady = () => {
    player = new YT.Player('player', {
      host: 'https://www.youtube-nocookie.com',
      playerVars: { controls: 0, disablekb: 1, modestbranding: 1, rel: 0, playsinline: 1, iv_load_policy: 3, fs: 0 },
      events: { onReady: () => { apiReady = true; if (on) tune(chIdx, { ident: true }); }, onStateChange: onState, onError },
    });
  };
  const s = document.createElement('script'); s.src = 'https://www.youtube.com/iframe_api';
  s.onerror = () => { el.power.classList.add('off'); setNoSignal('NO SIGNAL — CAN’T REACH YOUTUBE'); };
  document.head.append(s);

  el.power.onclick = () => {
    on = true; el.power.classList.add('off');
    showIdent(channels[chIdx].tag.toUpperCase(), 1800); staticBurst(500); showOSD();
    if (apiReady) later(playNext, 1900);
    else later(() => { if (!apiReady) setNoSignal('WARMING UP…'); }, 3000);
  };
  // if the API becomes ready after power-on, onReady (above) starts playback
})();
