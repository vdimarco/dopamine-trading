const START=1000, TARGET=100000;
const GOLD='#7dff9a', GREEN='#3dcc6a', MUTED='rgba(130,210,145,.55)', INK='#b8e6b8';
const BTC_COLOR='#4a7a58'; const SPY_COLOR=BTC_COLOR;
const FILL_UP='rgba(61,204,106,.12)';
const FILL_DN='rgba(200,107,122,.12)';
const FILL_FLAT='rgba(125,255,154,.06)';
const ALPHA_BAND='rgba(61,204,106,.14)';
let chart=null;
let fsActive=false;
let lastSnaps=null;
function money(n){return (n<0?"-":"")+"$"+Math.abs(n).toFixed(2)}
function pct(n){return (n>=0?"+":"")+n.toFixed(3)+"%"}
function cls(n){return n>0?"up":(n<0?"dn":"")}
function fmtTime(t){if(!t)return"";const m=String(t).match(/T(\d{2}:\d{2}:\d{2})/);return m?m[1]:t;}
function fillForPnl(pnl){
  if(pnl>0) return FILL_UP;
  if(pnl<0) return FILL_DN;
  return FILL_FLAT;
}
function yDomain(eqs, spyEqs, peakEq){
  const yVals=[...eqs, START, peakEq];
  for(const v of spyEqs){ if(v!=null&&!Number.isNaN(v)) yVals.push(v); }
  const yMin=Math.min(...yVals);
  const yMax=Math.max(...yVals);
  const pad=(yMax-yMin)*0.09||5;
  return {min:yMin-pad, max:yMax+pad};
}
function pointStyles(eqs, peakIdx){
  const n=eqs.length;
  const last=n-1;
  const pointRadius=eqs.map((_,i)=>{
    if(i===peakIdx) return 5;
    if(i===last) return 3;
    return 0;
  });
  const pointBg=eqs.map((_,i)=>{
    if(i===peakIdx) return GREEN;
    if(i===last) return GOLD;
    return 'transparent';
  });
  const pointBorder=eqs.map((_,i)=>{
    if(i===peakIdx||i===last) return '#010805';
    return 'transparent';
  });
  const pointBorderW=eqs.map((_,i)=>(i===peakIdx||i===last)?2:0);
  return {pointRadius, pointBg, pointBorder, pointBorderW};
}
const peakPlugin={
  id:'peakLabel',
  afterDatasetsDraw(c){
    const meta=c.getDatasetMeta(0);
    const peakIdx=c.$peakIdx;
    if(peakIdx==null||!meta||!meta.data[peakIdx]) return;
    const pt=meta.data[peakIdx];
    const ctx=c.ctx;
    ctx.save();
    ctx.font='500 9px IBM Plex Mono, monospace';
    ctx.fillStyle=GREEN;
    ctx.textAlign='center';
    ctx.fillText('PEAK', pt.x, pt.y-14);
    ctx.restore();
  }
};
const openPlugin={
  id:'openLabel',
  afterDatasetsDraw(c){
    const {ctx, chartArea:{left}, scales:{y}}=c;
    if(!y||left==null) return;
    const yy=y.getPixelForValue(START);
    if(yy<c.chartArea.top||yy>c.chartArea.bottom) return;
    ctx.save();
    ctx.font='500 9px IBM Plex Mono, monospace';
    ctx.fillStyle=MUTED;
    ctx.textAlign='left';
    ctx.fillText('OPEN', left+4, yy-4);
    ctx.restore();
  }
};

const livePulsePlugin={
  id:'livePulse',
  afterDatasetsDraw(c){
    const meta=c.getDatasetMeta(0);
    if(!meta||!meta.data.length) return;
    const pt=meta.data[meta.data.length-1];
    if(!pt||pt.x==null||pt.y==null) return;
    const phase=(performance.now()%3400)/3400;
    const breath=0.5+0.5*Math.sin(phase*Math.PI*2);
    const ctx=c.ctx;
    ctx.save();
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, 3.5+breath*4.5, 0, Math.PI*2);
    ctx.fillStyle='rgba(125,255,154,'+(0.05+breath*0.10).toFixed(3)+')';
    ctx.fill();
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, 2.2+breath*1.4, 0, Math.PI*2);
    ctx.fillStyle='rgba(125,255,154,'+(0.35+breath*0.45).toFixed(3)+')';
    ctx.fill();
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, 1.6, 0, Math.PI*2);
    ctx.fillStyle=GOLD;
    ctx.fill();
    ctx.restore();
  }
};
const guidePlugin={
  id:'guideLines',
  beforeDatasetsDraw(c){
    const peakEq=c.$peakEq;
    const {ctx, chartArea:{left,right}, scales:{y}}=c;
    const lines=[
      {v:START, color:MUTED, dash:[4,4]},
      {v:peakEq, color:GREEN, dash:[5,4]}
    ];
    ctx.save();
    lines.forEach(L=>{
      if(L.v==null||Number.isNaN(L.v)) return;
      const yy=y.getPixelForValue(L.v);
      if(yy<c.chartArea.top||yy>c.chartArea.bottom) return;
      ctx.strokeStyle=L.color;
      ctx.lineWidth=1;
      ctx.setLineDash(L.dash);
      ctx.beginPath(); ctx.moveTo(left,yy); ctx.lineTo(right,yy); ctx.stroke();
    });
    ctx.restore();
  }
};
const alphaBandPlugin={
  id:'alphaBand',
  beforeDatasetsDraw(c){
    const eqMeta=c.getDatasetMeta(0);
    const spyMeta=c.getDatasetMeta(1);
    if(!eqMeta||!spyMeta||!eqMeta.data.length) return;
    const eqs=c.data.datasets[0].data;
    const spies=c.data.datasets[1].data;
    const ctx=c.ctx;
    const {top,bottom}=c.chartArea;
    ctx.save();
    ctx.beginPath();
    let drawing=false;
    for(let i=0;i<eqMeta.data.length;i++){
      const eq=eqs[i], spy=spies[i];
      const pEq=eqMeta.data[i], pSpy=spyMeta.data[i];
      if(eq==null||spy==null||!pEq||!pSpy||eq<=spy){
        if(drawing){ ctx.closePath(); ctx.fillStyle=ALPHA_BAND; ctx.fill(); ctx.strokeStyle='rgba(61,204,106,.28)'; ctx.lineWidth=1; ctx.stroke(); ctx.beginPath(); drawing=false; }
        continue;
      }
      if(!drawing){
        ctx.moveTo(pSpy.x, Math.min(Math.max(pSpy.y,top),bottom));
        drawing=true;
      }
      ctx.lineTo(pEq.x, Math.min(Math.max(pEq.y,top),bottom));
    }
    if(drawing){
      for(let i=eqMeta.data.length-1;i>=0;i--){
        const eq=eqs[i], spy=spies[i];
        const pSpy=spyMeta.data[i];
        if(eq==null||spy==null||eq<=spy||!pSpy) break;
        ctx.lineTo(pSpy.x, Math.min(Math.max(pSpy.y,top),bottom));
      }
      ctx.closePath();
      ctx.fillStyle=ALPHA_BAND;
      ctx.fill();
      ctx.strokeStyle='rgba(61,204,106,.28)';
      ctx.lineWidth=1;
      ctx.stroke();
    }
    ctx.restore();
  }
};
function peakIndex(eqs){
  let peakIdx=0;
  for(let i=1;i<eqs.length;i++) if(eqs[i]>eqs[peakIdx]) peakIdx=i;
  return peakIdx;
}
function makeConfig(snaps, peakEq){
  const labels=snaps.map(s=>fmtTime(s.t));
  const eqs=snaps.map(s=>s.eq);
  const spyEqs=snaps.map(s=>s.spy_eq!=null?s.spy_eq:null);
  const peakIdx=peakIndex(eqs);
  const {pointRadius, pointBg, pointBorder, pointBorderW}=pointStyles(eqs, peakIdx);
  const lastEq=eqs[eqs.length-1];
  const lastPnl=(lastEq!=null?lastEq:START)-START;
  const {min:yMin, max:yMax}=yDomain(eqs, spyEqs, peakEq);
  const compactLegend=!!(typeof document!=='undefined'&&document.documentElement.classList.contains('chart-fs'));
  return {
    type:'line',
    data:{
      labels,
      datasets:[{
        label:'Equity',
        data:eqs,
        borderColor:GOLD,
        backgroundColor:fillForPnl(lastPnl),
        borderWidth:2,
        fill:true,
        tension:0.15,
        pointRadius,
        pointHoverRadius:5,
        pointBackgroundColor:pointBg,
        pointBorderColor:pointBorder,
        pointBorderWidth:pointBorderW,
        pointHoverBackgroundColor:GOLD,
        pointHoverBorderColor:'#010805',
        pointHoverBorderWidth:2
      },{
        label:'BTC',
        data:spyEqs,
        borderColor:SPY_COLOR,
        backgroundColor:'transparent',
        borderWidth:1.25,
        fill:false,
        tension:0.15,
        pointRadius:0,
        pointHoverRadius:4,
        pointHoverBackgroundColor:SPY_COLOR,
        pointHoverBorderColor:'#010805',
        pointHoverBorderWidth:2,
        spanGaps:true
      }]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      animation:{duration:400, easing:'easeOutQuad'},
      transitions:{
        active:{animation:{duration:400, easing:'easeOutQuad'}},
        resize:{animation:{duration:0}}
      },
      interaction:{mode:'index', intersect:false},
      plugins:{
        legend:{
          display:true,
          position:'top',
          align:'end',
          labels:{
            color:MUTED,
            boxWidth:compactLegend?8:12,
            boxHeight:2,
            padding:compactLegend?4:8,
            font:{family:'IBM Plex Mono', size:compactLegend?9:10}
          }
        },
        tooltip:{
          backgroundColor:'#04120a',
          titleColor:GOLD,
          bodyColor:INK,
          borderColor:'rgba(100,220,130,.18)',
          borderWidth:1,
          padding:10,
          displayColors:true,
          callbacks:{
            title(items){
              const i=items[0].dataIndex;
              return fmtTime(snaps[i].t)+' ET';
            },
            label(item){
              const s=snaps[item.dataIndex];
              if(item.datasetIndex===0){
                const p=s.pct!=null?s.pct:((s.eq-START)/START*100);
                return 'Equity  '+money(s.eq)+'  ('+pct(p)+')';
              }
              if(s.spy_eq==null) return 'BTC  n/a';
              const sp=((s.spy_eq-START)/START*100);
              return 'BTC  '+money(s.spy_eq)+'  ('+pct(sp)+')';
            },
            afterBody(items){
              const i=items[0].dataIndex;
              const s=snaps[i];
              const lines=[];
              if(s.spy_eq!=null){
                const a=((s.eq-START)-(s.spy_eq-START))/START*100;
                lines.push('Alpha  '+pct(a));
              }
              const below=peakEq-s.eq;
              if(below>0.005) lines.push('peak -'+money(below).replace(/^\$/,'$'));
              else if(i===peakIdx) lines.push('PEAK');
              return lines;
            }
          }
        }
      },
      scales:{
        x:{
          ticks:{color:MUTED, maxTicksLimit:8, font:{family:'IBM Plex Mono', size:10}},
          grid:{color:'rgba(100,220,130,.10)'},
          border:{color:'rgba(100,220,130,.18)'}
        },
        y:{
          min:yMin,
          max:yMax,
          ticks:{
            color:MUTED,
            font:{family:'IBM Plex Mono', size:10},
            callback:v=>'$'+Number(v).toFixed(0)
          },
          grid:{color:'rgba(100,220,130,.10)'},
          border:{color:'rgba(100,220,130,.18)'}
        }
      }
    },
    plugins:[guidePlugin, alphaBandPlugin, peakPlugin, openPlugin, livePulsePlugin]
  };
}
function applyChartData(snaps, peakEq){
  const labels=snaps.map(s=>fmtTime(s.t));
  const eqs=snaps.map(s=>s.eq);
  const spyEqs=snaps.map(s=>s.spy_eq!=null?s.spy_eq:null);
  const peakIdx=peakIndex(eqs);
  const styles=pointStyles(eqs, peakIdx);
  const lastEq=eqs[eqs.length-1];
  const lastPnl=(lastEq!=null?lastEq:START)-START;
  const dom=yDomain(eqs, spyEqs, peakEq);
  const ds0=chart.data.datasets[0];
  const ds1=chart.data.datasets[1];
  chart.data.labels=labels;
  ds0.data=eqs;
  ds0.backgroundColor=fillForPnl(lastPnl);
  ds0.pointRadius=styles.pointRadius;
  ds0.pointBackgroundColor=styles.pointBg;
  ds0.pointBorderColor=styles.pointBorder;
  ds0.pointBorderWidth=styles.pointBorderW;
  ds1.data=spyEqs;
  chart.options.scales.y.min=dom.min;
  chart.options.scales.y.max=dom.max;
  const compact=document.documentElement.classList.contains('chart-fs');
  chart.options.plugins.legend.labels.boxWidth=compact?8:12;
  chart.options.plugins.legend.labels.padding=compact?4:8;
  chart.options.plugins.legend.labels.font={family:'IBM Plex Mono', size:compact?9:10};
  chart.options.plugins.tooltip.callbacks={
    title(items){
      const i=items[0].dataIndex;
      return fmtTime(snaps[i].t)+' ET';
    },
    label(item){
      const s=snaps[item.dataIndex];
      if(item.datasetIndex===0){
        const p=s.pct!=null?s.pct:((s.eq-START)/START*100);
        return 'Equity  '+money(s.eq)+'  ('+pct(p)+')';
      }
      if(s.spy_eq==null) return 'BTC  n/a';
      const sp=((s.spy_eq-START)/START*100);
      return 'BTC  '+money(s.spy_eq)+'  ('+pct(sp)+')';
    },
    afterBody(items){
      const i=items[0].dataIndex;
      const s=snaps[i];
      const lines=[];
      if(s.spy_eq!=null){
        const a=((s.eq-START)-(s.spy_eq-START))/START*100;
        lines.push('Alpha  '+pct(a));
      }
      const below=peakEq-s.eq;
      if(below>0.005) lines.push('peak -'+money(below).replace(/^\$/,'$'));
      else if(i===peakIdx) lines.push('PEAK');
      return lines;
    }
  };
  chart.$peakIdx=peakIdx;
  chart.$peakEq=peakEq;
  chart.$snaps=snaps;
  chart.update('active');
}
function buildChart(snaps, peakEq){
  const canvas=document.getElementById('curve');
  const cfg=makeConfig(snaps, peakEq);
  if(chart){chart.destroy(); chart=null;}
  chart=new Chart(canvas.getContext('2d'), cfg);
  chart.$peakIdx=peakIndex(snaps.map(s=>s.eq));
  chart.$peakEq=peakEq;
  chart.$snaps=snaps;
}
function updateCurve(snaps, peakEq){
  if(!snaps||snaps.length<2){
    if(chart){chart.destroy(); chart=null;}
    lastSnaps=null;
    return;
  }
  lastSnaps=snaps;
  if(chart){
    applyChartData(snaps, peakEq);
  }else{
    buildChart(snaps, peakEq);
  }
}
function updateChartChrome(d, peakEq, eq){
  const pnlPct=d.pnl_pct!=null?d.pnl_pct:((eq-START)/START*100);
  const alpha=d.alpha_pct!=null?d.alpha_pct:0;
  const dd=peakEq>0?((eq-peakEq)/peakEq*100):0;
  const chipPnl=document.getElementById('chipPnl');
  const chipDd=document.getElementById('chipDd');
  const chipAlpha=document.getElementById('chipAlpha');
  if(chipPnl){
    chipPnl.textContent='P&L '+pct(pnlPct);
    chipPnl.className='chip '+cls(pnlPct);
  }
  if(chipDd){
    chipDd.textContent='DD '+pct(dd);
    chipDd.className='chip '+cls(dd);
  }
  if(chipAlpha){
    chipAlpha.textContent='Alpha '+pct(alpha);
    chipAlpha.className='chip '+cls(alpha);
  }
  const prog=(d.progress_pct!=null)?Math.max(0,Math.min(100,d.progress_pct)):Math.max(0, Math.min(100, ((eq-START)/(TARGET-START))*100));
  const fill=document.getElementById('progFill');
  const pval=document.getElementById('progVal');
  if(fill) fill.style.width=prog.toFixed(1)+'%';
  if(pval) pval.textContent=Math.round(prog)+'%';
  const chipLive=document.getElementById('chipLive');
  if(chipLive){
    chipLive.textContent='Live';
    chipLive.className='chip live-chip';
  }
}
function resizeChartSoon(){
  requestAnimationFrame(()=>{
    if(chart){
      const compact=document.documentElement.classList.contains('chart-fs');
      if(chart.options&&chart.options.plugins&&chart.options.plugins.legend){
        chart.options.plugins.legend.labels.boxWidth=compact?8:12;
        chart.options.plugins.legend.labels.padding=compact?4:8;
        chart.options.plugins.legend.labels.font={family:'IBM Plex Mono', size:compact?9:10};
      }
      chart.resize();
    }
    requestAnimationFrame(()=>{ if(chart) chart.resize(); });
  });
}
let fsHomeParent=null;
let fsHomeNext=null;
function fsTarget(){
  return document.getElementById('chartPanel');
}
function isIOSLike(){
  const ua=navigator.userAgent||'';
  if(/iP(hone|od|ad)/.test(ua)) return true;
  if(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1) return true;
  return false;
}
function setFsBtn(on){
  const btn=document.getElementById('fsBtn');
  if(!btn) return;
  btn.textContent=on?'Exit fullscreen':'Fullscreen';
  btn.setAttribute('aria-pressed', on?'true':'false');
  btn.classList.toggle('fs-btn-exit', !!on);
}
function enterFakeFs(){
  const el=fsTarget();
  if(!el) return;
  if(!fsHomeParent){
    fsHomeParent=el.parentNode;
    fsHomeNext=el.nextSibling;
    document.body.appendChild(el);
  }
  document.documentElement.classList.add('chart-fs');
  document.body.classList.add('chart-fs');
  document.body.style.overflow='hidden';
  document.documentElement.style.overflow='hidden';
  fsActive=true;
  setFsBtn(true);
  resizeChartSoon();
}
function exitFakeFs(){
  const el=fsTarget();
  document.documentElement.classList.remove('chart-fs');
  document.body.classList.remove('chart-fs');
  document.body.style.overflow='';
  document.documentElement.style.overflow='';
  if(el&&fsHomeParent){
    if(fsHomeNext&&fsHomeNext.parentNode===fsHomeParent){
      fsHomeParent.insertBefore(el, fsHomeNext);
    }else{
      fsHomeParent.appendChild(el);
    }
    fsHomeParent=null;
    fsHomeNext=null;
  }
  fsActive=false;
  setFsBtn(false);
  resizeChartSoon();
}
function isNativeFs(){
  return !!(document.fullscreenElement||document.webkitFullscreenElement);
}
function tryNativeFs(el){
  if(isIOSLike()||!el) return;
  try{
    if(el.requestFullscreen) el.requestFullscreen().catch(function(){});
    else if(el.webkitRequestFullscreen) el.webkitRequestFullscreen();
  }catch(_){}
}
function exitNativeFs(){
  if(!isNativeFs()) return;
  try{
    if(document.exitFullscreen) document.exitFullscreen().catch(function(){});
    else if(document.webkitExitFullscreen) document.webkitExitFullscreen();
  }catch(_){}
}
let fsLockUntil=0;
function toggleFullscreen(){
  const now=Date.now();
  if(now<fsLockUntil) return;
  fsLockUntil=now+350;
  const el=fsTarget();
  if(!el) return;
  if(fsActive||document.documentElement.classList.contains('chart-fs')||isNativeFs()){
    exitNativeFs();
    exitFakeFs();
    return;
  }
  enterFakeFs();
  tryNativeFs(el);
}
function wireFullscreen(){
  const btn=document.getElementById('fsBtn');
  if(btn) btn.addEventListener('click', (e)=>{ e.preventDefault(); e.stopPropagation(); toggleFullscreen(); });
  window.toggleChartFullscreen=toggleFullscreen;
  document.addEventListener('fullscreenchange', ()=>{
    if(isNativeFs()){
      if(!document.documentElement.classList.contains('chart-fs')) enterFakeFs();
      else{ fsActive=true; setFsBtn(true); resizeChartSoon(); }
    }else if(document.documentElement.classList.contains('chart-fs')){
      /* keep fake fs */
    }else{
      exitFakeFs();
    }
  });
  document.addEventListener('webkitfullscreenchange', ()=>{
    if(isNativeFs()){
      if(!document.documentElement.classList.contains('chart-fs')) enterFakeFs();
      else{ fsActive=true; setFsBtn(true); resizeChartSoon(); }
    }else if(!document.documentElement.classList.contains('chart-fs')){
      exitFakeFs();
    }
  });
  document.addEventListener('keydown', (e)=>{
    if(e.key==='Escape' && document.documentElement.classList.contains('chart-fs')){
      exitNativeFs();
      exitFakeFs();
    }
  });
  window.addEventListener('orientationchange', ()=>resizeChartSoon());
  window.addEventListener('resize', ()=>{ if(fsActive) resizeChartSoon(); });
  if(window.visualViewport){
    window.visualViewport.addEventListener('resize', ()=>{ if(fsActive) resizeChartSoon(); });
  }
}
async function load(){
  try{
    const r=await fetch('data.json?t='+Date.now());
    const d=await r.json();
    document.getElementById('equity').textContent=money(d.equity);
    const pnlEl=document.getElementById('pnl'); pnlEl.textContent=money(d.pnl)+' ('+pct(d.pnl_pct)+')'; pnlEl.className='val '+cls(d.pnl);
    const spyEl=document.getElementById('spy'); spyEl.textContent=pct(d.btc_pct!=null?d.btc_pct:d.spy_pct); spyEl.className='val '+cls(d.btc_pct!=null?d.btc_pct:d.spy_pct);
    const aEl=document.getElementById('alpha'); aEl.textContent=pct(d.alpha_pct); aEl.className='val '+cls(d.alpha_pct);
    const badge=document.getElementById('winBadge');
    const hit = (d.equity||0) >= TARGET || !!d.target_hit;
    if(hit){badge.textContent='TARGET HIT $100k';badge.className='badge win'}
    else if((d.pnl_pct||0) > 0){badge.textContent='CRYPTO PAPER · hunting';badge.className='badge'}
    else {badge.textContent='CRYPTO PAPER · hunting';badge.className='badge lose'}
    document.getElementById('clock').textContent='Updated '+((d.updated_at||'').slice(11,19)||'...')+' ET';
    document.getElementById('cash').textContent=money(d.cash);
    const rEl=document.getElementById('realized'); rEl.textContent=money(d.realized); rEl.className='val '+cls(d.realized);
    document.getElementById('high').textContent=money(d.high);
    {
      const el=document.getElementById('ends');
      if(d.ends_at){
        const m=String(d.ends_at).match(/(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/);
        el.textContent=m?(m[1].slice(5)+' '+m[2]):d.ends_at.slice(0,16);
      }else el.textContent='...';
    }
    const snaps=d.snaps||[];
    let peakEq=d.high!=null?d.high:START;
    if(snaps.length){
      const snapPeak=Math.max(...snaps.map(s=>s.eq));
      if(snapPeak>peakEq) peakEq=snapPeak;
    }
    const eq=d.equity!=null?d.equity:START;
    const dd=peakEq>0?((eq-peakEq)/peakEq*100):0;
    const toT=d.to_target!=null?d.to_target:(TARGET-eq);
    document.getElementById('peak').textContent=money(peakEq);
    const ddEl=document.getElementById('dd');
    ddEl.textContent=pct(dd);
    ddEl.className='val '+cls(dd);
    const ttEl=document.getElementById('toTarget');
    ttEl.textContent=money(toT);
    ttEl.className='val '+(toT<=0?'up':'');
    const dl=document.getElementById('daysLeft');
    if(dl){
      const days=d.days_remaining!=null?d.days_remaining:30;
      dl.textContent=(Math.round(days*10)/10)+'d';
    }
    const pr=document.getElementById('progress');
    if(pr){
      const pv=d.progress_pct!=null?d.progress_pct:Math.max(0,((eq-START)/(TARGET-START))*100);
      pr.textContent=pv.toFixed(2)+'%';
    }
    const uni=document.getElementById('universe');
    if(uni){
      uni.textContent=(d.universe||['BTC','ETH','SOL','DOGE','SUI']).join(' ');
    }
    document.getElementById('pos').innerHTML=(d.positions||[]).map(p=>{
      const mk=p.mark;
      const mkStr=mk>=1?mk.toFixed(2):(mk>=0.01?mk.toFixed(4):mk.toFixed(6));
      return '<tr><td>'+p.symbol+'</td><td>'+mkStr+'</td><td class="'+cls(p.u_pnl)+'">'+money(p.u_pnl)+'</td><td class="'+cls(p.u_pct)+'">'+pct(p.u_pct)+'</td></tr>';
    }).join('')||'<tr><td colspan=4>Flat · hunting</td></tr>';
    const fills=[...(d.fills||[])].reverse().slice(0,8);
    document.getElementById('fills').innerHTML=fills.map(f=>{
      const tm=(f.ts_et||'').slice(11,19);
      const rp=parseFloat(f.realized_pnl||0);
      const px=parseFloat(f.price);
      const pxStr=px>=1?px.toFixed(2):(px>=0.01?px.toFixed(4):px.toFixed(6));
      return '<tr><td>'+tm+'</td><td>'+f.side+'</td><td>'+f.symbol+'</td><td>'+pxStr+'</td><td class="'+cls(rp)+'">'+money(rp)+'</td></tr>';
    }).join('')||'<tr><td colspan=5>No fills yet</td></tr>';
    updateChartChrome(d, peakEq, eq);
    updateCurve(snaps, peakEq);
    buildFeedItems(d);
    startPulseLoop();
  }catch(e){document.getElementById('clock').textContent='Waiting for data...'}
}

function etClock(){
  try{
    return new Date().toLocaleTimeString('en-US',{timeZone:'America/New_York',hour12:false});
  }catch(_){
    const d=new Date();
    return d.toISOString().slice(11,19);
  }
}
function tickLiveClock(){
  const el=document.getElementById('liveClock');
  if(el) el.textContent='Live '+etClock()+' ET';
}
let feedItems=[];
let feedIdx=0;
let feedTimer=null;
function setFeedText(text){
  const el=document.getElementById('liveFeed');
  if(!el) return;
  if(el.textContent===text) return;
  el.classList.add('fade');
  setTimeout(()=>{
    el.textContent=text;
    el.classList.remove('fade');
  },220);
}
function buildFeedItems(d){
  const items=[];
  const fills=[...(d.fills||[])].reverse().slice(0,6);
  for(const f of fills){
    const t=(f.ts_et||'').slice(11,19);
    const px=parseFloat(f.price);
    items.push((t?t+' · ':'')+f.side+' '+f.symbol+' @ '+(Number.isFinite(px)?px.toFixed(2):'-'));
  }
  const pos=(d.positions||[]);
  if(pos.length){
    items.push('Open '+pos.map(p=>p.symbol).join(' · '));
  }else{
    items.push('Flat · hunting breakout');
  }
  items.push('Crypto desk heartbeat · '+etClock()+' ET');
  items.push('To $100k · '+money(d.to_target!=null?d.to_target:(TARGET-(d.equity||START))));
  if(d.days_remaining!=null) items.push(d.days_remaining.toFixed(1)+' days left');
  if((d.pnl_pct||0)>0) items.push('Book '+pct(d.pnl_pct)+' · vs BTC '+pct(d.btc_pct||d.spy_pct||0));
  else items.push('Book '+pct(d.pnl_pct||0)+' · hunting');
  if(!fills.length) items.unshift('Warming up · scanning BTC ETH SOL DOGE SUI');
  feedItems=items;
  if(feedIdx>=feedItems.length) feedIdx=0;
  if(feedItems.length) setFeedText(feedItems[feedIdx]);
}
function advanceFeed(){
  if(!feedItems.length) return;
  feedIdx=(feedIdx+1)%feedItems.length;
  let line=feedItems[feedIdx];
  if(line.indexOf('Crypto desk heartbeat')===0) line='Crypto desk heartbeat · '+etClock()+' ET';
  setFeedText(line);
}
function startFeedLoop(){
  if(feedTimer) return;
  feedTimer=setInterval(advanceFeed, 4200);
}
let pulseRaf=0;
let lastPulseDraw=0;
function pulseLoop(ts){
  pulseRaf=requestAnimationFrame(pulseLoop);
  if(!chart) return;
  if(ts-lastPulseDraw<90) return;
  lastPulseDraw=ts;
  try{ chart.draw(); }catch(_){}
}
function startPulseLoop(){
  if(pulseRaf) return;
  const reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(reduce) return;
  pulseRaf=requestAnimationFrame(pulseLoop);
}
function softChartNudge(){
  if(!chart) return;
  try{ chart.draw(); }catch(_){}
}
wireFullscreen();
load();
setInterval(load, 15000);
tickLiveClock();
setInterval(tickLiveClock, 1000);
startFeedLoop();
startPulseLoop();
setInterval(softChartNudge, 2500);
