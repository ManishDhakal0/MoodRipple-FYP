// js/main.js — All application logic: bridge setup, navigation, detection, analytics, settings.

var bridge   = null;
var settings = {};
var _charts  = {};
var _ttsOn   = false;
// Session tracking
var _moodTotals   = {energized:0,focused:0,calm:0,drowsy:0};
var _detCount     = 0;
var _confTotal    = 0;
var _sessionStart = 0;
var _sessionTimer = null;
var pageIds  = ['dashPage','spotifyPage','calendarPage','analyticsPage','settingsPage','chatPage'];

// ── Navigation ───────────────────────────────────────────────────────────────
function navTo(i) {
  pageIds.forEach(function(id,j){ document.getElementById(id).classList.toggle('active',j===i); });
  document.querySelectorAll('.nav-btn').forEach(function(b){ b.classList.toggle('active',+b.dataset.pg===i); });
  if(bridge) bridge.navigate(i);
  if(i===3) bridge&&bridge.request_analytics();
  if(i===4) bridge&&bridge.request_settings();
}

// ── Detection controls ───────────────────────────────────────────────────────
function startDet() {
  document.getElementById('startBtn').disabled=true;
  var sb=document.getElementById('stopBtn'); sb.disabled=false; sb.style.opacity='1';
  document.getElementById('camPh').style.display='none';
  document.getElementById('liveIndicator').style.display='block';
  // Reset session stats
  _moodTotals={energized:0,focused:0,calm:0,drowsy:0};
  _detCount=0; _confTotal=0; _sessionStart=Date.now();
  document.getElementById('sesCount').textContent='0';
  document.getElementById('sesDom').textContent='—';
  document.getElementById('sesConf').textContent='—';
  ['bE','bF','bC','bD'].forEach(function(id){document.getElementById(id).style.width='0%';});
  ['pE','pF','pC','pD'].forEach(function(id){document.getElementById(id).textContent='0%';});
  if(_sessionTimer) clearInterval(_sessionTimer);
  _sessionTimer=setInterval(function(){
    if(!_sessionStart) return;
    var s=Math.floor((Date.now()-_sessionStart)/1000);
    var m=Math.floor(s/60),sec=s%60;
    var el=document.getElementById('sesTimer');
    if(el) el.textContent=m+'m '+(sec<10?'0':'')+sec+'s';
  },1000);
  if(bridge) bridge.start_detection();
}
function stopDet() {
  document.getElementById('startBtn').disabled=false;
  var sb2=document.getElementById('stopBtn'); sb2.disabled=true; sb2.style.opacity='0.55';
  var f=document.getElementById('camFeed'); f.style.display='none'; f.src='';
  document.getElementById('camPh').style.display='flex';
  document.getElementById('liveIndicator').style.display='none';
  if(_sessionTimer){clearInterval(_sessionTimer);_sessionTimer=null;}
  var el=document.getElementById('sesTimer'); if(el) el.textContent='Stopped';
  if(bridge) bridge.stop_detection();
}

// ── Text emotion ─────────────────────────────────────────────────────────────
function doTxtAnalyze() {
  var t=document.getElementById('txtIn').value.trim(); if(!t) return;
  document.getElementById('txtRes').textContent='Analyzing…';
  if(bridge) bridge.analyze_text(t);
}

// ── Chat helpers ─────────────────────────────────────────────────────────────
function addBubble(cid,txt,isUser) {
  var b=document.createElement('div'); b.className='bubble '+(isUser?'user':'bot');
  b.textContent=txt; var c=document.getElementById(cid);
  c.appendChild(b); c.scrollTop=c.scrollHeight;
}
function sendMini() {
  var i=document.getElementById('miniInp'),t=i.value.trim(); if(!t) return;
  addBubble('miniMsgs',t,true); i.value=''; if(bridge) bridge.send_chat(t);
}
function sendFull() {
  var i=document.getElementById('fullInp'),t=i.value.trim(); if(!t) return;
  addBubble('fullMsgs',t,true); i.value=''; if(bridge) bridge.send_chat(t);
}

// ── Calendar renderer ─────────────────────────────────────────────────────────
function renderCal(evs,id) {
  var c=document.getElementById(id);
  if(!evs||!evs.length){c.innerHTML='<div class="cal-empty">No upcoming events</div>';return;}
  c.innerHTML=evs.slice(0,8).map(function(ev){
    var s=ev.start?(ev.start.dateTime||ev.start.date||''):'';
    var ts=s?new Date(s).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}):'';
    return '<div class="cal-ev"><div class="cal-ev-title">'+(ev.summary||'Untitled')+'</div>'
      +(ts?'<div class="cal-ev-time">🕐 '+ts+'</div>':'')+'</div>';
  }).join('');
}

// ── Settings ──────────────────────────────────────────────────────────────────
function togSet(key) {
  var el=document.getElementById('tog_'+key); var on=el.classList.toggle('on'); settings[key]=on;
}
function doSave() {
  settings['mood_cooldown_secs']       = parseInt(document.getElementById('set_mood_cooldown').value)||30;
  settings['openai_api_key']           = document.getElementById('set_openai_key').value.trim();
  settings['drowsy_night_hour']        = parseInt(document.getElementById('set_drowsy_night_hour').value)||22;
  settings['drowsy_day_music']         = document.getElementById('set_drowsy_day_music').value;
  settings['drowsy_night_music']       = document.getElementById('set_drowsy_night_music').value;
  if(bridge) bridge.save_settings(JSON.stringify(settings));
  setStatus('Settings saved.','#34d399');
}
function applySettings(d) {
  settings=d;
  ['auto_start_detection','auto_export_session','show_mood_widget','smart_drowsy_response'].forEach(function(k){
    var el=document.getElementById('tog_'+k); if(el) el.classList.toggle('on',!!d[k]);
  });
  var cd=document.getElementById('set_mood_cooldown');      if(cd) cd.value=d.mood_cooldown_secs||30;
  var ok=document.getElementById('set_openai_key');         if(ok) ok.value=d.openai_api_key||'';
  var nh=document.getElementById('set_drowsy_night_hour');  if(nh) nh.value=d.drowsy_night_hour||22;
  var dm=document.getElementById('set_drowsy_day_music');   if(dm) dm.value=d.drowsy_day_music||'drowsy';
  var nm=document.getElementById('set_drowsy_night_music'); if(nm) nm.value=d.drowsy_night_music||'calm';
}

// ── Status bar ────────────────────────────────────────────────────────────────
function setStatus(msg,col){
  var el=document.getElementById('stTxt'); el.textContent=msg; el.style.color=col||'var(--t3)';
}

// ── Analytics ─────────────────────────────────────────────────────────────────
var _adays  = 7;

function aSetRange(days, btn) {
  _adays = days;
  document.querySelectorAll('.a-range-btn').forEach(function(b){ b.classList.remove('active'); });
  btn.classList.add('active');
  if (bridge) { try { bridge.request_analytics_range(days); } catch(e) { bridge.request_analytics(); } }
}

function _mkChart(id, cfg) {
  if (_charts[id]) { try { _charts[id].destroy(); } catch(e) {} delete _charts[id]; }
  var el = document.getElementById(id); if (!el) return null;
  try { _charts[id] = new Chart(el, cfg); return _charts[id]; } catch(e) { return null; }
}

var _MC = { energized:'#a78bfa', focused:'#60a5fa', calm:'#34d399', drowsy:'#fb923c' };
var _EC = { happy:'#a78bfa', surprise:'#c4b5fd', neutral:'#94a3b8',
            fear:'#f472b6', sad:'#60a5fa', angry:'#f87171', disgust:'#fb923c' };
var _DL = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
var _HL = (function(){ var a=[]; for(var i=0;i<24;i++) a.push(i===0?'12a':i<12?i+'a':i===12?'12p':(i-12)+'p'); return a; })();

function _cap(s){ return s ? s.charAt(0).toUpperCase()+s.slice(1) : '—'; }

function _baseOpts(extra) {
  var o = {
    responsive:true, maintainAspectRatio:false,
    animation:{ duration:500, easing:'easeOutQuart' },
    plugins:{
      legend:{ display:false },
      tooltip:{ backgroundColor:'rgba(14,14,22,0.94)', titleColor:'rgba(232,236,244,0.85)',
                bodyColor:'rgba(232,236,244,0.50)', borderColor:'rgba(255,255,255,0.09)',
                borderWidth:1, padding:10, cornerRadius:8 }
    },
    scales:{
      x:{ grid:{ color:'rgba(255,255,255,0.04)' }, ticks:{ color:'rgba(232,236,244,0.28)', font:{size:9} } },
      y:{ grid:{ color:'rgba(255,255,255,0.04)' }, ticks:{ color:'rgba(232,236,244,0.28)', font:{size:9} } }
    }
  };
  return o;
}

function renderAnalytics(d) {
  if (!d) return;

  /* ── KPI tiles ─────────────────────────────────────────────────────── */
  document.getElementById('aKpiDet').textContent = (d.total_detections||0).toLocaleString();
  document.getElementById('aKpiSess').textContent = (d.sessions||d.session_count||Math.max(1,Math.ceil((d.total_detections||0)/20))).toLocaleString();
  var mEl = document.getElementById('aKpiMood');
  mEl.textContent = _cap(d.dominant_mood||'—');
  var mc = _MC[d.dominant_mood]||'#8b5cf6';
  mEl.style.color = mc;
  mEl.closest('.kpi-tile').style.setProperty('--kpi-color', mc);
  // Peak hour from hourly_moods
  (function(){
    var hm=d.hourly_moods||{};
    var bestH=null,bestTotal=0;
    for(var h=0;h<24;h++){var hd=hm[String(h)]||{};var tot=Object.keys(hd).reduce(function(a,k){return a+hd[k];},0);if(tot>bestTotal){bestTotal=tot;bestH=h;}}
    var el=document.getElementById('aKpiHour');
    el.textContent=bestH!==null?(bestH<12?(bestH||12)+'am':(bestH===12?'12pm':(bestH-12)+'pm')):'—';
  })();
  document.getElementById('aKpiConf').textContent = d.avg_confidence ? Math.round(d.avg_confidence*100)+'%' : '—';
  document.getElementById('aKpiTrax').textContent = (d.top_tracks||[]).length || (d.tracks_played||'—');
  document.getElementById('aKpiDrwy').textContent = (d.drowsy_count||d.drowsy_events||0).toLocaleString();
  document.getElementById('aKpiWell').textContent = (d.wellbeing_score!==null&&d.wellbeing_score!==undefined)?d.wellbeing_score+'%':'—';

  /* ── Insight cards ─────────────────────────────────────────────────── */
  (function(){
    var hm=d.hourly_moods||{};
    var bestH=null,bestTotal=0;
    for(var h=0;h<24;h++){var hd=hm[String(h)]||{};var tot=Object.keys(hd).reduce(function(a,k){return a+hd[k];},0);if(tot>bestTotal){bestTotal=tot;bestH=h;}}
    document.getElementById('insActive').textContent=bestH!==null?(bestH<12?(bestH||12)+':00 AM':(bestH===12?'12:00 PM':(bestH-12)+':00 PM')):'—';

    // Best day: from timeline pick day with highest energized
    var tl=d.timeline||[],dayEn={};
    tl.forEach(function(pt){var dt=new Date(pt.ts*1000);var key=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][dt.getDay()];if(pt.mood==='energized'){dayEn[key]=(dayEn[key]||0)+1;}});
    var bestDay=Object.keys(dayEn).reduce(function(a,b){return(dayEn[a]||0)>(dayEn[b]||0)?a:b;},'—');
    document.getElementById('insBestDay').textContent=bestDay||'—';

    // Drowsy risk %
    var tot=d.total_detections||0;
    var drwy=d.drowsy_count||d.drowsy_events||0;
    document.getElementById('insDrwyRisk').textContent=tot?Math.round(drwy/tot*100)+'%':'0%';

    // Music lift — placeholder derived from wellbeing
    var wb=d.wellbeing_score;
    document.getElementById('insMusicLift').textContent=wb?'+'+Math.max(0,Math.round(wb*0.15))+'%':'—';

    // Emotion range — count unique emotions in timeline
    var emoSet={};
    (d.timeline||[]).forEach(function(pt){if(pt.emotion)emoSet[pt.emotion]=1;});
    document.getElementById('insEmoRange').textContent=Object.keys(emoSet).length||'—';

    // Focus window — hour block with most 'focused' mood
    var focH=null,focMax=0;
    for(var h=0;h<24;h++){var fd=(hm[String(h)]||{}).focused||0;if(fd>focMax){focMax=fd;focH=h;}}
    document.getElementById('insFocus').textContent=focH!==null?(focH<12?(focH||12)+'-'+(focH+1)+'am':(focH===12?'12-1pm':(focH-12)+'-'+(focH-11)+'pm')):'—';
  })();

  /* ── Timeline — smooth stacked area ───────────────────────────────── */
  (function(){
    var tl = d.timeline||[];
    var sub = document.getElementById('aTimelineSub');
    if (sub) sub.textContent = tl.length ? tl.length+' data points' : '';
    if (!tl.length) {
      _mkChart('cTimeline',{type:'line',data:{labels:[],datasets:[]},options:_baseOpts()});
      return;
    }
    var days = d.days||7;
    var buckets={}, moods=['energized','focused','calm','drowsy'];
    tl.forEach(function(pt){
      var dt=new Date(pt.ts*1000);
      var key=days<=1?(dt.getHours()+':00'):((dt.getMonth()+1)+'/'+dt.getDate());
      if(!buckets[key]){buckets[key]={energized:0,focused:0,calm:0,drowsy:0};}
      buckets[key][pt.mood]=(buckets[key][pt.mood]||0)+1;
    });
    var lbs=Object.keys(buckets);
    var areaColors={energized:'rgba(251,191,36,',focused:'rgba(139,92,246,',calm:'rgba(56,189,248,',drowsy:'rgba(239,68,68,'};
    var opts=_baseOpts();
    opts.plugins.legend={display:true,labels:{color:'rgba(232,236,244,0.32)',font:{size:9},padding:12,boxWidth:10,boxHeight:10}};
    opts.scales.x.stacked=true; opts.scales.y.stacked=true;
    opts.elements={line:{tension:0.4},point:{radius:0,hitRadius:8}};
    _mkChart('cTimeline',{
      type:'line',
      data:{
        labels:lbs,
        datasets:moods.map(function(m){
          var base=areaColors[m]||'rgba(139,92,246,';
          return{
            label:_cap(m),
            data:lbs.map(function(k){return(buckets[k]||{})[m]||0;}),
            fill:true,
            tension:0.4,
            backgroundColor:base+'0.35)',
            borderColor:base+'0.80)',
            borderWidth:1.5,
            pointRadius:0,
            stack:'mood'
          };
        })
      },
      options:opts
    });
  })();

  /* ── Hourly stacked bar ────────────────────────────────────────────── */
  (function(){
    var hm=d.hourly_moods||{}, moods=['energized','focused','calm','drowsy'];
    var hrs=Array.from({length:24},function(_,i){return i;});
    var opts=_baseOpts();
    opts.plugins.legend={display:true,labels:{color:'rgba(232,236,244,0.32)',font:{size:9},padding:10,boxWidth:10,boxHeight:10}};
    opts.scales.x={stacked:true,grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'rgba(232,236,244,0.25)',font:{size:8},maxRotation:0}};
    opts.scales.y={stacked:true,grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'rgba(232,236,244,0.28)',font:{size:9}}};
    _mkChart('cHourly',{type:'bar',data:{labels:_HL,datasets:moods.map(function(m){return{label:_cap(m),data:hrs.map(function(h){return(hm[String(h)]||{})[m]||0;}),backgroundColor:_MC[m]+'cc',borderWidth:0};})},options:opts});
  })();

  /* ── Mood donut ────────────────────────────────────────────────────── */
  (function(){
    var mc=d.mood_counts||{};
    var keys=Object.keys(mc),vals=keys.map(function(k){return mc[k];});
    if(!keys.length){_mkChart('cDonut',{type:'doughnut',data:{datasets:[{data:[1],backgroundColor:['rgba(255,255,255,0.04)']}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}}}});return;}
    _mkChart('cDonut',{type:'doughnut',data:{labels:keys.map(_cap),datasets:[{data:vals,backgroundColor:keys.map(function(k){return _MC[k]||'#666';}),borderWidth:3,borderColor:'#17171f',hoverOffset:5}]},options:{responsive:true,maintainAspectRatio:false,animation:{duration:600},cutout:'62%',plugins:{legend:{display:true,position:'right',labels:{color:'rgba(232,236,244,0.38)',font:{size:9},padding:10,boxWidth:10,boxHeight:10}},tooltip:{backgroundColor:'rgba(14,14,22,0.94)',titleColor:'rgba(232,236,244,0.85)',bodyColor:'rgba(232,236,244,0.50)',borderColor:'rgba(255,255,255,0.09)',borderWidth:1,cornerRadius:8}}}});
  })();

  /* ── Top Tracks list ───────────────────────────────────────────────── */
  (function(){
    var el=document.getElementById('aTopTracks');
    var trx=d.top_tracks||[];
    if(!trx.length){el.innerHTML='<div class="chart-empty">No track data yet</div>';return;}
    var mx=trx[0].cnt||1;
    el.innerHTML=trx.slice(0,8).map(function(t,i){
      var pct=Math.round(t.cnt/mx*100);
      return '<div class="trk-row">'
        +'<span style="font-size:10px;color:var(--t4);width:16px;flex-shrink:0;text-align:right">'+(i+1)+'</span>'
        +'<div style="flex:1;min-width:0">'
          +'<div style="font-size:12px;font-weight:600;color:var(--t1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+t.track+'</div>'
          +'<div style="font-size:10px;color:var(--t3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+t.artist+'</div>'
          +'<div style="margin-top:4px;height:3px;border-radius:2px;background:rgba(255,255,255,0.05)">'
            +'<div style="height:100%;width:'+pct+'%;background:#1DB954;border-radius:2px;transition:width 0.7s"></div></div>'
        +'</div>'
        +'<span style="font-size:11px;font-weight:700;color:#1DB954;flex-shrink:0">×'+t.cnt+'</span>'
        +'</div>';
    }).join('');
  })();
}

// ── Header drag ───────────────────────────────────────────────────────────────
var dragging=false,lx,ly;
document.querySelector('.header').addEventListener('mousedown',function(e){
  if(e.target.tagName==='BUTTON'||e.target.closest('#mainNav')||e.target.closest('.hdr-right')) return;
  dragging=true; lx=e.screenX; ly=e.screenY; e.preventDefault();
});
document.addEventListener('mousemove',function(e){
  if(!dragging) return;
  var dx=e.screenX-lx,dy=e.screenY-ly; lx=e.screenX; ly=e.screenY;
  if(bridge&&(dx||dy)) bridge.drag_move(dx,dy);
});
document.addEventListener('mouseup',function(){dragging=false;});

// ── QWebChannel + bridge signals ──────────────────────────────────────────────
new QWebChannel(qt.webChannelTransport,function(ch){
  bridge=ch.objects.bridge;

  bridge.frame_updated.connect(function(url){
    var f=document.getElementById('camFeed'); f.src=url; f.style.display='block';
    document.getElementById('camPh').style.display='none';
  });

  bridge.emotion_updated.connect(function(em,conf,mood){
    var emo={happy:'😄',sad:'😢',angry:'😠',fear:'😨',disgust:'🤢',surprise:'😲',neutral:'😐',drowsy:'😴'};
    var mico={energized:'⚡',focused:'🎯',calm:'🌊',drowsy:'☕'};
    var mcol={energized:'#a78bfa',focused:'#60a5fa',calm:'#34d399',drowsy:'#fb923c'};
    document.getElementById('emoEmoji').textContent=emo[em]||'😐';
    document.getElementById('emoName').textContent=em.charAt(0).toUpperCase()+em.slice(1);
    document.getElementById('emoConf').textContent='Confidence: '+(conf*100).toFixed(1)+'%';
    var mb=document.getElementById('moodBadge');
    mb.textContent=(mico[mood]||'🎯')+'\u00a0\u00a0'+mood.charAt(0).toUpperCase()+mood.slice(1);
    mb.style.color=mcol[mood]||'var(--accent)';
    mb.style.borderColor=mood==='drowsy'?'rgba(251,146,60,0.30)':'var(--acc-bd)';
    mb.style.background=mood==='drowsy'?'rgba(251,146,60,0.12)':'var(--acc-dim)';
    // Update running session totals
    _detCount++;
    _confTotal+=conf;
    if(mood in _moodTotals) _moodTotals[mood]++;
    // Find dominant mood
    var dom=Object.keys(_moodTotals).reduce(function(a,b){return _moodTotals[a]>=_moodTotals[b]?a:b;});
    var domEl=document.getElementById('sesDom');
    if(domEl){domEl.textContent=dom.charAt(0).toUpperCase()+dom.slice(1);domEl.style.color=mcol[dom]||'var(--accent)';}
    document.getElementById('sesCount').textContent=_detCount;
    document.getElementById('sesConf').textContent=Math.round(_confTotal/_detCount*100)+'%';
    // Update mood bars from session totals
    var total=Math.max(_detCount,1);
    function _sb(bi,pi,v){var p=Math.round(v/total*100);
      document.getElementById(bi).style.width=p+'%';
      document.getElementById(pi).textContent=p+'%';}
    _sb('bE','pE',_moodTotals.energized);
    _sb('bF','pF',_moodTotals.focused);
    _sb('bC','pC',_moodTotals.calm);
    _sb('bD','pD',_moodTotals.drowsy);
  });

  bridge.scores_updated.connect(function(js){
    // Raw CNN scores — bars driven by session totals in emotion_updated
    void js;
  });

  bridge.drowsy_updated.connect(function(js){
    var d=JSON.parse(js);
    if(!d.available||!d.face_detected){
      document.getElementById('drwySt').textContent=d.face_detected===false?'No face detected':'MediaPipe unavailable'; return;}
    document.getElementById('mEar').textContent=d.ear?(d.ear).toFixed(2):'—';
    document.getElementById('mPer').textContent=d.perclos?(d.perclos*100).toFixed(0)+'%':'—';
    document.getElementById('mYwn').textContent=d.yawn_count!==undefined?d.yawn_count+(d.is_yawning?' 😮':''):'—';
    document.getElementById('mBlk').textContent=d.blinks_per_min!==undefined?d.blinks_per_min:'—';
    document.getElementById('drwyAlert').style.display=d.is_drowsy?'block':'none';
    var stEl=document.getElementById('drwySt');
    var dotEl=stEl&&stEl.previousElementSibling;  // the colored dot before the text
    if(d.is_drowsy){
      stEl.textContent='Drowsy — switching music!';
      stEl.style.color='#f87171';
      if(dotEl){dotEl.style.background='#ef4444';dotEl.style.boxShadow='0 0 6px rgba(239,68,68,0.60)';}
    } else if(d.is_yawning){
      stEl.textContent='Yawning detected — watch out';
      stEl.style.color='#fbbf24';
      if(dotEl){dotEl.style.background='#f59e0b';dotEl.style.boxShadow='0 0 6px rgba(245,158,11,0.60)';}
    } else {
      stEl.textContent='Alert — Normal';
      stEl.style.color='var(--t3)';
      if(dotEl){dotEl.style.background='#22c55e';dotEl.style.boxShadow='0 0 6px rgba(34,197,94,0.50)';}
    }
  });

  bridge.status_updated.connect(function(msg,col){setStatus(msg,col);});

  bridge.spotify_updated.connect(function(js){
    var d=JSON.parse(js);
    document.getElementById('tName').textContent=d.track||'—';
    document.getElementById('tArtist').textContent=d.artist||'—';
    document.getElementById('tArt').textContent=d.art_emoji||'🎵';
    document.getElementById('spName').textContent=d.track||'—';
    document.getElementById('spArtist').textContent=d.artist||'—';
    document.getElementById('spArt').textContent=d.art_emoji||'🎵';
    document.getElementById('spStatus').textContent=d.connected?('Connected · '+(d.display_name||'')):'Not connected';
    document.getElementById('spConBtn').style.display=d.connected?'none':'';
    document.getElementById('spDisBtn').style.display=d.connected?'':'none';
    var db=document.getElementById('dashSpConBtn'); if(db) db.style.display=d.connected?'none':'';
  });

  bridge.calendar_updated.connect(function(js){
    var evs=JSON.parse(js); renderCal(evs,'calList'); renderCal(evs,'calPageList');
  });

  bridge.conn_updated.connect(function(sp,cal){
    document.getElementById('dotSp').classList.toggle('on',sp);
    document.getElementById('dotCal').classList.toggle('on',cal);
    document.getElementById('calStatus').textContent=cal?'Connected':'Not connected';
    document.getElementById('calConBtn').style.display=cal?'none':'';
    document.getElementById('calDisBtn').style.display=cal?'':'none';
  });

  bridge.chat_message.connect(function(txt,isUser){
    addBubble('miniMsgs',txt,isUser); addBubble('fullMsgs',txt,isUser);
  });

  bridge.tts_state.connect(function(enabled){
    _ttsOn = enabled;
    var btn = document.getElementById('ttsBtn');
    if (!btn) return;
    btn.textContent = enabled ? '🔊' : '🔇';
    btn.style.color         = enabled ? '#F5C518'                   : 'rgba(240,240,248,0.35)';
    btn.style.borderColor   = enabled ? 'rgba(245,197,24,0.40)'     : 'rgba(255,255,255,0.09)';
    btn.style.background    = enabled ? 'rgba(245,197,24,0.08)'     : 'transparent';
  });

  bridge.mic_status.connect(function(status){
    var btn = document.getElementById('micBtn');
    if (!btn) return;
    if (status === 'recording') {
      btn.textContent = '⏹ Stop';
      btn.style.background  = 'rgba(239,68,68,0.18)';
      btn.style.borderColor = 'rgba(239,68,68,0.45)';
      btn.style.color       = '#ef4444';
      btn.style.fontSize    = '12px';
    } else if (status === 'transcribing') {
      btn.textContent = '⏳…';
      btn.style.background  = 'rgba(251,191,36,0.12)';
      btn.style.borderColor = 'rgba(251,191,36,0.35)';
      btn.style.color       = '#fbbf24';
    } else {
      btn.textContent = '🎤';
      btn.style.background  = 'rgba(255,255,255,0.05)';
      btn.style.borderColor = 'rgba(255,255,255,0.10)';
      btn.style.color       = 'var(--t2)';
      btn.style.fontSize    = '16px';
    }
  });

  bridge.settings_data.connect(function(js){applySettings(JSON.parse(js));});
  bridge.analytics_data.connect(function(js){renderAnalytics(JSON.parse(js));});

  bridge.window_state.connect(function(state){
    var c=document.getElementById('appContainer');
    var mb=document.getElementById('maxBtn');
    if(state==='maximized'){c.classList.add('maximized');if(mb)mb.textContent='❐';}
    else{c.classList.remove('maximized');if(mb)mb.textContent='⬜';}
  });

  bridge.auth_result.connect(function(js){
    var d=JSON.parse(js);
    if(d.user){var u=d.user.username||'User';
      document.getElementById('uAvatar').textContent=u[0].toUpperCase();
      document.getElementById('uName').textContent=u;}
  });

  bridge.page_changed.connect(function(i){navTo(i);});
});
