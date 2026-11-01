PY_HEAD = r'''import streamlit as st
import base64, os

st.set_page_config(page_title="Plants vs Zombies - Bản Việt Hóa", layout="wide")
st.markdown("<h1 style='text-align:center;color:#5fbf3a;margin:0'>🌻 PLANTS vs ZOMBIES 🧟</h1>", unsafe_allow_html=True)

# ================= NHẠC NỀN =================
# Đặt file nhạc (mp3/ogg/wav/m4a) cùng thư mục với file .py này (hoặc trong music/, assets/, static/),
# hoặc tải lên ở ô bên dưới. Nếu không có file, game tự phát nhạc tổng hợp.
AUDIO_MIME = {".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav",
              ".m4a": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac"}
MAX_MB = 25

def _find_music():
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    folders = [here, os.path.join(here, "music"), os.path.join(here, "assets"),
               os.path.join(here, "static"), os.getcwd()]
    found, seen = [], set()
    for folder in folders:
        if folder in seen or not os.path.isdir(folder):
            continue
        seen.add(folder)
        for name in sorted(os.listdir(folder)):
            if os.path.splitext(name)[1].lower() in AUDIO_MIME:
                found.append(os.path.join(folder, name))
    pref = ("pvz", "plants", "zombie", "theme", "music", "bgm", "nhac", "song")
    found.sort(key=lambda p: (0 if any(k in os.path.basename(p).lower() for k in pref) else 1))
    return found[0] if found else None

@st.cache_data(show_spinner=False)
def _file_to_uri(path, mtime):
    ext = os.path.splitext(path)[1].lower()
    with open(path, "rb") as f:
        data = f.read()
    return f"data:{AUDIO_MIME.get(ext, 'audio/mpeg')};base64," + base64.b64encode(data).decode()

music_uri, music_label = "", "Chưa có file nhạc -> dùng nhạc tổng hợp dự phòng"
with st.expander("🎵 Nhạc nền (bấm để tải file nhạc nếu muốn)"):
    up = st.file_uploader("Chọn file nhạc", type=[e[1:] for e in AUDIO_MIME])
    if up is not None:
        if up.size > MAX_MB * 1024 * 1024:
            st.warning(f"File lớn hơn {MAX_MB} MB, hãy chọn file nhỏ hơn.")
        else:
            ext = os.path.splitext(up.name)[1].lower()
            music_uri = f"data:{AUDIO_MIME.get(ext, 'audio/mpeg')};base64," + base64.b64encode(up.getvalue()).decode()
            music_label = f"Đang dùng file đã tải lên: {up.name}"
    if not music_uri:
        p = _find_music()
        if p and os.path.getsize(p) <= MAX_MB * 1024 * 1024:
            music_uri = _file_to_uri(p, os.path.getmtime(p))
            music_label = f"Đang dùng file: {os.path.basename(p)}"
    st.caption(music_label + "  •  Nhạc bắt đầu phát sau cú bấm chuột đầu tiên trong game.")

game_code = r"""
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
html,body{margin:0;padding:0;background:#0f1a12;height:100%;overflow:hidden}
#c{position:absolute;left:0;top:0;border-radius:10px;box-shadow:0 6px 30px rgba(0,0,0,.6);touch-action:none;user-select:none;cursor:default}
</style></head>
<body><canvas id="c" width="900" height="600"></canvas>
<script>
'''

JS_BASE = r'''
const MUSIC_SRC="__MUSIC_SRC__";
const store={get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
if(typeof CanvasRenderingContext2D!=='undefined'&&!CanvasRenderingContext2D.prototype.roundRect){
  CanvasRenderingContext2D.prototype.roundRect=function(x,y,w,h,r){r=Array.isArray(r)?(r[0]||0):(r||0);this.moveTo(x+r,y);this.arcTo(x+w,y,x+w,y+h,r);this.arcTo(x+w,y+h,x,y+h,r);this.arcTo(x,y+h,x,y,r);this.arcTo(x,y,x+w,y,r);this.closePath();};
}
const cv=document.getElementById('c'); let ctx=cv.getContext('2d');
const W=900,H=600,GX=130,CW=80,LT=100;
let SAVE={level:0,unlocked:['peashooter'],coins:0,slots:6,sunUp:0,surv:{},last:[]};
try{ Object.assign(SAVE,JSON.parse(store.get('pvz_save')||'{}')||{}); }catch(e){}
function save(){ store.set('pvz_save',JSON.stringify(SAVE)); }
let isMuted=store.get('pvz_muted')==='1', sfxOn=store.get('pvz_sfx')!=='0';
let G=null, S='MENU', PAUSED=false;

// ---------- Âm thanh ----------
const AC=window.AudioContext||window.webkitAudioContext; let au=null;
function initAudio(){ try{ if(!au&&AC) au=new AC(); if(au&&au.state==='suspended') au.resume(); }catch(e){ au=null; } }
function tone(type,f1,f2,dur,vol,delay){
  if(!sfxOn) return; initAudio(); if(!au) return; const t=au.currentTime+(delay||0);
  const o=au.createOscillator(), g=au.createGain(); o.type=type; o.frequency.setValueAtTime(f1,t);
  if(f2!==f1) o.frequency.exponentialRampToValueAtTime(Math.max(20,f2),t+dur);
  g.gain.setValueAtTime(vol,t); g.gain.exponentialRampToValueAtTime(.0001,t+dur); o.connect(g); g.connect(au.destination); o.start(t); o.stop(t+dur+.02);
}
const SFXF={
  shoot:()=>tone('triangle',520,300,.08,.1), splat:()=>tone('sawtooth',200,90,.09,.1),
  sun:()=>{tone('sine',700,1000,.12,.16);tone('sine',1000,1400,.12,.13,.08);}, plant:()=>tone('sine',320,150,.14,.18),
  boom:()=>{tone('sawtooth',160,30,.5,.3);tone('square',90,30,.4,.18);}, chomp:()=>tone('square',140,70,.12,.15),
  groan:()=>tone('sawtooth',110,70,.7,.08), coin:()=>tone('square',988,1318,.1,.1),
  win:()=>[523,659,784,1047].forEach((f,i)=>tone('triangle',f,f,.25,.2,i*.15)),
  lose:()=>[330,262,220,165].forEach((f,i)=>tone('sawtooth',f,f*.9,.4,.2,i*.25)),
  freeze:()=>tone('sine',1200,300,.35,.18), shovel:()=>tone('square',250,120,.1,.12),
  wave:()=>{tone('sawtooth',90,60,1.2,.22);tone('sawtooth',100,70,1.2,.18,.3);}, bad:()=>tone('square',120,100,.15,.12),
  mower:()=>tone('sawtooth',80,120,.4,.15)
};
function snd(n){ try{ SFXF[n](); }catch(e){} }

// ---------- Nhạc nền ----------
let useSynth=!MUSIC_SRC||MUSIC_SRC.indexOf('__MUSIC')===0, musicOn=false, synthTimer=null, mstep=0;
const bgm=new Audio();
if(!useSynth){ bgm.src=MUSIC_SRC; bgm.loop=true; bgm.volume=.6; bgm.addEventListener('error',()=>{ useSynth=true; if(musicOn&&!isMuted) startSynth(); }); }
const MEL_D=[392,0,440,494,0,523,494,440,392,0,330,349,392,0,294,0], MEL_N=[220,0,262,0,330,0,262,247,220,0,196,0,247,262,0,0], BAS=[98,98,110,110,87,87,98,98];
function nt(type,f,d,v,t){ const o=au.createOscillator(), g=au.createGain(); o.type=type; o.frequency.value=f; g.gain.setValueAtTime(v,t); g.gain.linearRampToValueAtTime(.0001,t+d); o.connect(g); g.connect(au.destination); o.start(t); o.stop(t+d); }
function startSynth(){
  if(synthTimer) return; initAudio(); if(!au) return;
  synthTimer=setInterval(()=>{ if(isMuted||PAUSED) return; const t=au.currentTime, night=!!(G&&G.map&&G.map.night&&S==='PLAY'), mel=night?MEL_N:MEL_D, f=mel[mstep%16];
    if(f) nt('square',f,.22,.03,t); if(mstep%2===0) nt('triangle',BAS[(mstep>>1)%8]*(night?.75:1),.4,.06,t); mstep++; },240);
}
function stopSynth(){ if(synthTimer){ clearInterval(synthTimer); synthTimer=null; } }
function playMusic(){ if(isMuted) return; if(useSynth){ startSynth(); return; } try{ const p=bgm.play(); if(p&&p.catch) p.catch(()=>{}); }catch(e){} }
function pauseMusic(){ stopSynth(); try{ bgm.pause(); }catch(e){} }
function toggleMusic(){ isMuted=!isMuted; store.set('pvz_muted',isMuted?'1':'0'); if(isMuted) pauseMusic(); else playMusic(); }
function toggleSfx(){ sfxOn=!sfxOn; store.set('pvz_sfx',sfxOn?'1':'0'); }

// ---------- Tiện ích vẽ ----------
const E_=(c,x,y,rx,ry,f,s,r,lw)=>{c.beginPath();c.ellipse(x,y,rx,ry,r||0,0,7);if(f){c.fillStyle=f;c.fill();}if(s){c.strokeStyle=s;c.lineWidth=lw||2;c.stroke();}};
const C_=(c,x,y,r,f,s,lw)=>{c.beginPath();c.arc(x,y,r,0,7);if(f){c.fillStyle=f;c.fill();}if(s){c.strokeStyle=s;c.lineWidth=lw||2;c.stroke();}};
const L_=(c,x1,y1,x2,y2,w,col)=>{c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.beginPath();c.moveTo(x1,y1);c.lineTo(x2,y2);c.stroke();};
const R_=(c,x,y,w,h,r,f,s)=>{c.beginPath();c.roundRect(x,y,w,h,r);if(f){c.fillStyle=f;c.fill();}if(s){c.strokeStyle=s;c.lineWidth=2;c.stroke();}};
function T(str,x,y,size,fill,align,stroke,lw){ ctx.font='bold '+size+'px "Arial Black",Arial,sans-serif'; ctx.textAlign=align||'left'; ctx.lineJoin='round';
  if(stroke){ ctx.lineWidth=lw||Math.max(3,size/6); ctx.strokeStyle=stroke; ctx.strokeText(str,x,y); } ctx.fillStyle=fill||'#fff'; ctx.fillText(str,x,y); }
function rnd(a,b){ return a+Math.random()*(b-a); }
const SPR={};
function sprite(key,w,h,ox,oy,fn){ let s=SPR[key]; if(s) return s; const cn=document.createElement('canvas'); cn.width=w; cn.height=h; const c=cn.getContext('2d'); c.translate(ox,oy); fn(c); s={cn,ox,oy,w,h}; SPR[key]=s; return s; }
function blit(s,x,y,sc,al,flip){ ctx.save(); ctx.translate(x,y); if(flip) ctx.scale(-1,1); if(sc&&sc!==1) ctx.scale(sc,sc); if(al!==undefined&&al<1) ctx.globalAlpha=al; ctx.drawImage(s.cn,-s.ox,-s.oy); ctx.restore(); }
'''

JS_DATA = r'''
// ================= DỮ LIỆU CÂY =================
const PLANTS={
  peashooter:{n:'Đậu Bắn',cost:100,cd:7.5,hp:300,k:'shoot',desc:'Bắn đậu vào zombie trên cùng hàng.'},
  sunflower:{n:'Hoa Hướng Dương',cost:50,cd:7.5,hp:300,k:'sun',desc:'Tạo ra thêm mặt trời cho bạn.'},
  cherrybomb:{n:'Cherry Bomb',cost:150,cd:50,hp:300,k:'bomb',desc:'Nổ tung mọi zombie trong vùng 3x3.'},
  wallnut:{n:'Hạt Óc Chó',cost:50,cd:30,hp:4000,k:'wall',desc:'Lớp vỏ cứng giúp chặn đường zombie.'},
  potatomine:{n:'Potato Mine',cost:25,cd:30,hp:300,k:'mine',desc:'Cần thời gian để kích hoạt, rồi nổ tung zombie bước lên.'},
  snowpea:{n:'Đậu Tuyết',cost:175,cd:7.5,hp:300,k:'shoot',desc:'Bắn đậu băng làm zombie chậm lại.'},
  chomper:{n:'Chomper',cost:150,cd:7.5,hp:300,k:'chomp',desc:'Nuốt chửng một zombie, nhưng nhai rất lâu.'},
  repeater:{n:'Repeater',cost:200,cd:7.5,hp:300,k:'shoot',desc:'Bắn hai viên đậu mỗi lượt.'},
  puffshroom:{n:'Puff-shroom',cost:0,cd:7.5,hp:300,k:'shoot',mush:1,desc:'Nấm miễn phí bắn xa gần. Ngủ vào ban ngày.'},
  sunshroom:{n:'Sun-shroom',cost:25,cd:7.5,hp:300,k:'sun',mush:1,desc:'Tạo mặt trời nhỏ, lớn dần sẽ tạo nhiều hơn.'},
  fumeshroom:{n:'Fume-shroom',cost:75,cd:7.5,hp:300,k:'fume',mush:1,desc:'Phun khói xuyên qua cả cửa lưới.'},
  gravebuster:{n:'Grave Buster',cost:75,cd:7.5,hp:300,k:'grave',mush:1,desc:'Ăn bia mộ, dọn chỗ để trồng cây.'},
  hypnoshroom:{n:'Hypno-shroom',cost:75,cd:30,hp:300,k:'hypno',mush:1,desc:'Zombie ăn nó sẽ quay sang đánh đồng bọn.'},
  iceshroom:{n:'Ice-shroom',cost:75,cd:50,hp:300,k:'ice',mush:1,desc:'Đóng băng mọi zombie trên sân.'},
  doomshroom:{n:'Doom-shroom',cost:125,cd:50,hp:300,k:'doom',mush:1,desc:'Vụ nổ khổng lồ, để lại hố sâu.'},
  lilypad:{n:'Lily Pad',cost:25,cd:7.5,hp:300,k:'base',desc:'Cho phép trồng cây trên mặt nước.'},
  squash:{n:'Squash',cost:50,cd:30,hp:300,k:'squash',desc:'Nhảy đè bẹp zombie đến gần.'},
  threepeater:{n:'Threepeater',cost:325,cd:7.5,hp:300,k:'shoot',desc:'Bắn đậu vào 3 hàng cùng lúc.'},
  tanglekelp:{n:'Tangle Kelp',cost:25,cd:30,hp:300,k:'kelp',water:1,desc:'Kéo zombie xuống nước. Chỉ trồng trên nước.'},
  jalapeno:{n:'Jalapeno',cost:125,cd:50,hp:300,k:'jala',desc:'Thiêu rụi mọi zombie trên cả hàng.'},
  spikeweed:{n:'Spikeweed',cost:100,cd:7.5,hp:300,k:'spike',desc:'Gai nhọn gây sát thương zombie bước lên.'},
  torchwood:{n:'Torchwood',cost:175,cd:7.5,hp:300,k:'torch',desc:'Biến đậu đi qua thành đậu lửa mạnh gấp đôi.'},
  tallnut:{n:'Tall-nut',cost:125,cd:30,hp:8000,k:'wall',desc:'Vỏ cứng cao, zombie không nhảy qua được.'},
  seashroom:{n:'Sea-shroom',cost:0,cd:7.5,hp:300,k:'shoot',mush:1,water:1,desc:'Nấm biển miễn phí, chỉ trồng trên nước.'},
  plantern:{n:'Plantern',cost:25,cd:30,hp:300,k:'lantern',desc:'Soi sáng, xua tan sương mù xung quanh.'},
  cactus:{n:'Cactus',cost:125,cd:7.5,hp:300,k:'shoot',desc:'Bắn gai xuyên cửa lưới.'},
  blover:{n:'Blover',cost:100,cd:7.5,hp:300,k:'blover',desc:'Thổi bay sương mù trong một lúc.'},
  starfruit:{n:'Starfruit',cost:125,cd:7.5,hp:300,k:'star',desc:'Bắn 5 ngôi sao theo nhiều hướng.'},
  flowerpot:{n:'Flower Pot',cost:25,cd:7.5,hp:300,k:'base',desc:'Cho phép trồng cây trên mái nhà.'},
  cabbagepult:{n:'Cabbage-pult',cost:100,cd:7.5,hp:300,k:'lob',desc:'Ném bắp cải theo đường vòng.'},
  kernelpult:{n:'Kernel-pult',cost:100,cd:7.5,hp:300,k:'lob',desc:'Ném bắp và bơ làm zombie đứng im.'},
  melonpult:{n:'Melon-pult',cost:300,cd:7.5,hp:300,k:'lob',desc:'Ném dưa hấu nổ lan sang hàng bên.'},
  coffeebean:{n:'Coffee Bean',cost:75,cd:7.5,hp:300,k:'coffee',desc:'Đánh thức nấm đang ngủ.'}
};
const PORDER=Object.keys(PLANTS);
const REWARDS=['sunflower','cherrybomb','wallnut','potatomine','snowpea','chomper','repeater','fumeshroom','gravebuster','hypnoshroom','squash','threepeater','jalapeno','torchwood','tallnut','tanglekelp','cactus','blover','starfruit','iceshroom','kernelpult','coffeebean','melonpult','doomshroom',null];
const INTRO={1:['puffshroom','sunshroom'],2:['lilypad','spikeweed'],3:['seashroom','plantern'],4:['flowerpot','cabbagepult']};

// ================= DỮ LIỆU ZOMBIE =================
const ZD={
  basic:{n:'Zombie Thường',hp:200,sp:4.7,dps:100,c:1,desc:'Chậm chạp, thích ăn não.'},
  flag:{n:'Zombie Cầm Cờ',hp:200,sp:3.8,dps:100,c:1,desc:'Báo hiệu đợt zombie khổng lồ.'},
  cone:{n:'Zombie Nón',hp:200,sp:4.7,dps:100,arm:360,ak:'cone',c:2,desc:'Chiếc nón giúp chịu đòn gấp ba.'},
  bucket:{n:'Zombie Xô',hp:200,sp:4.7,dps:100,arm:1100,ak:'bucket',c:4,desc:'Chiếc xô sắt rất cứng.'},
  pole:{n:'Zombie Nhảy Sào',hp:340,sp:2.5,dps:100,c:2,desc:'Chạy nhanh và nhảy qua cây đầu tiên.'},
  news:{n:'Zombie Đọc Báo',hp:200,sp:4.7,dps:100,arm:150,ak:'paper',c:2,desc:'Mất báo sẽ nổi điên và chạy nhanh.'},
  door:{n:'Zombie Cửa Lưới',hp:200,sp:4.7,dps:100,sh:1100,c:4,desc:'Cửa lưới chặn đậu, nhưng không chặn đạn bắn vòng.'},
  football:{n:'Zombie Bóng Bầu Dục',hp:270,sp:2.5,dps:100,arm:1400,ak:'helmet',c:5,desc:'Chạy nhanh và rất trâu.'},
  duck:{n:'Zombie Phao Vịt',hp:200,sp:4.7,dps:100,swim:1,c:1,desc:'Bơi trên hồ.'},
  duckcone:{n:'Zombie Phao Nón',hp:200,sp:4.7,dps:100,arm:360,ak:'cone',swim:1,c:2,desc:'Bơi trên hồ với nón.'},
  duckbucket:{n:'Zombie Phao Xô',hp:200,sp:4.7,dps:100,arm:1100,ak:'bucket',swim:1,c:4,desc:'Bơi trên hồ với xô.'},
  snorkel:{n:'Zombie Ống Thở',hp:200,sp:4.7,dps:100,swim:1,snorkel:1,c:2,desc:'Lặn dưới nước, chỉ nổi lên khi ăn cây.'},
  imp:{n:'Imp',hp:270,sp:2.6,dps:100,c:1,desc:'Nhỏ và nhanh, bị Gargantuar ném đi.'},
  garg:{n:'Gargantuar',hp:3000,sp:8,dps:0,smash:1,c:15,desc:'Khổng lồ. Đập nát cây chỉ bằng một cú.'}
};
const ZORDER=Object.keys(ZD);
const WAT={basic:'duck',cone:'duckcone',bucket:'duckbucket'};

// ================= BẢN ĐỒ & MÀN CHƠI =================
const MAPS=[
  {id:'DAY',n:'Sân Vườn Ban Ngày',rows:5,night:false,water:[],roof:false,fog:false},
  {id:'NIGHT',n:'Nghĩa Địa Ban Đêm',rows:5,night:true,water:[],roof:false,fog:false},
  {id:'POOL',n:'Hồ Bơi',rows:6,night:false,water:[2,3],roof:false,fog:false},
  {id:'FOG',n:'Hồ Bơi Sương Mù',rows:6,night:true,water:[2,3],roof:false,fog:true},
  {id:'ROOF',n:'Mái Nhà',rows:5,night:false,water:[],roof:true,fog:false}
];
function lvInfo(k){ const w=Math.floor(k/5), i=k%5; return {k,w,i,d:k,map:MAPS[w],waves:4+i+(w>>1),name:(w+1)+'-'+(i+1)}; }
function allowedZ(L){
  const d=L.d, a=['basic'];
  if(d>=2) a.push('cone'); if(d>=5) a.push('pole'); if(d>=8) a.push('news'); if(d>=10) a.push('bucket'); if(d>=13) a.push('door'); if(d>=17) a.push('football');
  return a;
}
function genWave(L,j,big,surv){
  const d=L.d+(surv?Math.floor(j/3):0), list=[], pool=allowedZ({d});
  let b=(1+d*.32+j*.75)*(big?2.4:1); if(j===0&&!surv) b=Math.min(b,2);
  if(big) list.push('flag');
  let guard=0;
  while(b>0&&guard++<60){ const t=pool[Math.floor(Math.random()*pool.length)], c=ZD[t].c; if(c>b+.6&&list.length>0&&Math.random()<.6) { b-=1; continue; } list.push(t); b-=c; }
  if(L.map.water.length&&d>=11&&Math.random()<.6) list.push('snorkel');
  if(d>=20&&big&&(surv||j===L.waves-1)) list.push('garg');
  if(!list.length) list.push('basic');
  return list;
}
'''JS_ART = r'''
// ================= ĐỒ HỌA CÂY =================
const eyes_=(c,x,y,s,sl)=>{ s=s||1; if(sl){ L_(c,x-4*s,y,x+4*s,y,2,'#222'); L_(c,x+5*s,y+1,x+13*s,y+1,2,'#222'); return; }
  C_(c,x,y,5*s,'#fff','#333',1.2); C_(c,x+9*s,y+1,4.6*s,'#fff','#333',1.2); C_(c,x+1.6*s,y+.5,2.2*s,'#111'); C_(c,x+10.4*s,y+1.4,2*s,'#111'); };
const leaves_=(c,col)=>{ E_(c,-15,-10,13,5.5,col||'#4fb035','#2d7a1f',-.5); E_(c,13,-13,13,5.5,col||'#4fb035','#2d7a1f',.5); };
function peaH(c,x,y,col,dk,twin,brow,r){ r=r||17; L_(c,0,0,x*.5,y+r-2,6,'#3f9a2a'); C_(c,x,y,r,col,dk,2.5); E_(c,x+r+5,y+3,10,8,col,dk); E_(c,x+r+12,y+3,3.5,5.5,'#1d4d15');
  if(twin) E_(c,x+r+3,y-9,8,6,col,dk); eyes_(c,x-4,y-6,r/17); if(brow){ L_(c,x-9,y-14,x+3,y-9,3,dk); L_(c,x+6,y-9,x+19,y-14,3,dk); } E_(c,x-6,y-r,8,4,col,dk,-.6); }
function mush(c,cap,dk,o){ o=o||{}; const s=o.s||1, sl=o.sleep;
  E_(c,0,-12,9*s,14*s,'#f1e6cf','#b8a98a'); E_(c,0,-30*s+(sl?5:0),(sl?16:15)*s,(sl?10:13)*s,cap,dk);
  if(o.spots){ C_(c,-6*s,-34*s,3,'rgba(255,255,255,.7)'); C_(c,6*s,-32*s,2.5,'rgba(255,255,255,.7)'); }
  eyes_(c,-8,-14*s,.8,sl); if(!sl) E_(c,2,-5,4,2.5,'#6b2a2a'); if(sl){ T_z(c); } if(o.extra) o.extra(c); }
function T_z(c){ c.fillStyle='#fff'; c.font='bold 14px Arial'; c.fillText('z',12,-38); c.font='bold 10px Arial'; c.fillText('z',20,-48); }
const PD={
  peashooter(c){ leaves_(c); peaH(c,0,-42,'#6cc644','#3d8b2a'); },
  snowpea(c){ leaves_(c,'#5fb0a0'); peaH(c,0,-42,'#8fd3f0','#3b8fb5'); C_(c,-4,-62,3,'#fff'); C_(c,3,-64,2,'#fff'); },
  repeater(c){ leaves_(c); peaH(c,0,-42,'#4aae30','#2a7020',true,true); },
  threepeater(c){ leaves_(c); peaH(c,-8,-60,'#6cc644','#3d8b2a',false,false,12); peaH(c,6,-40,'#6cc644','#3d8b2a',false,false,12); peaH(c,-8,-20,'#6cc644','#3d8b2a',false,false,12); },
  sunflower(c){ L_(c,0,0,0,-34,6,'#3f9a2a'); leaves_(c); for(let i=0;i<12;i++){ const a=i/12*6.283; E_(c,Math.cos(a)*21,-50+Math.sin(a)*21,10,5,'#ffd93b','#d99a00',a); }
    C_(c,0,-50,15,'#8b5a2b','#5a3a18',2.5); C_(c,-5,-53,2.5,'#2a1a0a'); C_(c,5,-53,2.5,'#2a1a0a'); c.strokeStyle='#2a1a0a'; c.lineWidth=2; c.beginPath(); c.arc(0,-48,7,.2,2.9); c.stroke(); },
  cherrybomb(c){ L_(c,-14,-34,-2,-62,3,'#3f7a2a'); L_(c,14,-36,-2,-62,3,'#3f7a2a'); E_(c,2,-64,9,4,'#4fb035','#2d7a1f',-.3);
    [[-14,-18],[15,-20]].forEach(([x,y])=>{ C_(c,x,y,17,'#d62828','#7a1010',2.5); E_(c,x-3,y-8,6,3,'rgba(255,255,255,.4)'); C_(c,x-6,y-2,4,'#fff'); C_(c,x+6,y-2,4,'#fff'); C_(c,x-5,y-1,2,'#111'); C_(c,x+5,y-1,2,'#111'); L_(c,x-11,y-9,x-2,y-5,2.5,'#400'); L_(c,x+11,y-9,x+2,y-5,2.5,'#400'); c.strokeStyle='#400'; c.lineWidth=2; c.beginPath(); c.arc(x,y+9,5,3.4,6); c.stroke(); }); },
  wallnut(c,st){ E_(c,0,-34,26,32,'#c68b3e','#8a5a1f',0,2.5); E_(c,-8,-48,8,12,'rgba(255,230,180,.35)',null,.4); eyes_(c,-12,-40,1.1,st==='h2'); c.strokeStyle='#5a3a18'; c.lineWidth=2.5; c.beginPath(); c.arc(0,-22,8,.3,2.8); c.stroke();
    if(st==='h1'||st==='h2'){ L_(c,-14,-58,-4,-46,2,'#4a2a10'); L_(c,-4,-46,-12,-36,2,'#4a2a10'); } if(st==='h2'){ L_(c,10,-56,4,-42,2,'#4a2a10'); L_(c,4,-42,14,-30,2,'#4a2a10'); } },
  tallnut(c,st){ E_(c,0,-46,24,48,'#b87a32','#7a4a18',0,2.5); E_(c,-8,-70,7,16,'rgba(255,230,180,.3)',null,.4); eyes_(c,-12,-58,1.1,st==='h2'); c.strokeStyle='#5a3a18'; c.lineWidth=2.5; c.beginPath(); c.arc(0,-38,8,.3,2.8); c.stroke();
    if(st==='h1'||st==='h2'){ L_(c,-12,-80,-2,-66,2,'#4a2a10'); L_(c,-2,-66,-12,-52,2,'#4a2a10'); } if(st==='h2'){ L_(c,10,-76,4,-60,2,'#4a2a10'); } },
  potatomine(c,st){ if(st!=='armed'){ E_(c,0,-8,22,10,'#7a5230','#4a2f18'); C_(c,-8,-12,3,'#5a3a20'); C_(c,6,-10,2.5,'#5a3a20'); }
    else { E_(c,0,-20,22,18,'#c9985a','#7a5a2a',0,2.5); eyes_(c,-12,-24,.9); E_(c,0,-12,6,3,'#5a2a1a'); L_(c,0,-37,0,-46,3,'#555'); C_(c,0,-48,5,'#f33','#900',1.5); } },
  chomper(c,st){ L_(c,0,0,0,-30,7,'#3f8f3a'); leaves_(c,'#4fb035'); C_(c,0,-52,22,'#9b4fc2','#5e2a80',2.5);
    if(st==='chew'){ E_(c,6,-48,13,6,'#6b2a8a'); eyes_(c,-8,-60,.9); C_(c,18,-70,2,'#7cf'); }
    else { c.fillStyle='#d62d57'; c.beginPath(); c.moveTo(4,-52); c.lineTo(36,-76); c.lineTo(36,-30); c.closePath(); c.fill(); c.strokeStyle='#5e2a80'; c.lineWidth=2.5; c.stroke();
      c.fillStyle='#fff'; for(let i=0;i<4;i++){ c.beginPath(); c.moveTo(12+i*5,-58-i*5); c.lineTo(15+i*5,-50-i*4); c.lineTo(18+i*5,-60-i*5); c.fill(); } eyes_(c,-12,-62,.9); } },
  squash(c){ E_(c,0,-30,22,28,'#b5d63a','#6e8a14',0,2.5); E_(c,-6,-44,7,10,'rgba(255,255,255,.3)'); L_(c,0,-58,2,-66,4,'#3f7a2a'); eyes_(c,-12,-36,1); L_(c,-14,-44,-3,-39,3,'#4a5a10'); L_(c,4,-39,16,-44,3,'#4a5a10'); E_(c,0,-18,8,3.5,'#5a2a1a'); },
  lilypad(c){ E_(c,0,-3,34,11,'#3fa83c','#25702a',0,2.5); E_(c,-8,-5,12,3,'rgba(255,255,255,.2)'); c.fillStyle='#5aa0d8'; c.beginPath(); c.moveTo(0,-3); c.lineTo(36,-12); c.lineTo(36,6); c.closePath(); c.fill(); },
  flowerpot(c){ c.fillStyle='#c4602a'; c.beginPath(); c.moveTo(-22,-20); c.lineTo(22,-20); c.lineTo(16,0); c.lineTo(-16,0); c.closePath(); c.fill(); c.strokeStyle='#7a3a15'; c.lineWidth=2.5; c.stroke(); R_(c,-25,-26,50,9,3,'#d8703a','#7a3a15'); E_(c,0,-22,20,3,'#3a2a1a'); },
  tanglekelp(c){ for(let i=0;i<6;i++){ const x=-20+i*8; c.strokeStyle=i%2?'#2a8a6a':'#1f7058'; c.lineWidth=7; c.lineCap='round'; c.beginPath(); c.moveTo(x,0); c.bezierCurveTo(x-10,-18,x+10,-30,x-4,-52+(i%3)*4); c.stroke(); }
    C_(c,0,-38,12,'#2a8a6a','#14503c',2); eyes_(c,-9,-42,.8); },
  jalapeno(c){ c.save(); c.rotate(-.15); E_(c,0,-30,17,32,'#e0301e','#8a1008',0,2.5); E_(c,-6,-40,4,14,'rgba(255,255,255,.35)'); c.restore(); L_(c,0,-62,6,-72,5,'#3f8f2a'); eyes_(c,-12,-34,.95); L_(c,-12,-42,-2,-37,3,'#400'); L_(c,4,-37,14,-42,3,'#400'); E_(c,0,-18,6,3,'#400'); },
  spikeweed(c){ E_(c,0,-4,32,7,'#4a8a2a','#2d5a1a'); for(let i=0;i<7;i++){ c.fillStyle='#d8d8d8'; c.strokeStyle='#777'; c.lineWidth=1.5; c.beginPath(); c.moveTo(-28+i*9,-6); c.lineTo(-23+i*9,-24); c.lineTo(-18+i*9,-6); c.closePath(); c.fill(); c.stroke(); } },
  torchwood(c){ R_(c,-18,-46,36,46,8,'#7a4a24','#4a2a10'); for(let i=0;i<3;i++) E_(c,0,-34+i*9,14,3,null,'rgba(60,30,10,.5)',0,1.5); eyes_(c,-12,-34,.9); E_(c,0,-14,7,3,'#2a1a0a');
    E_(c,0,-58,15,16,'#ff8a1e'); E_(c,0,-60,10,12,'#ffd23f'); E_(c,0,-62,5,7,'#fff4b0'); },
  plantern(c){ leaves_(c,'#4fb035'); R_(c,-16,-50,32,36,14,'#ffd23f','#b8860b'); for(let i=-1;i<=1;i++) L_(c,i*8,-48,i*8,-16,1.5,'rgba(150,100,0,.5)'); eyes_(c,-9,-34,.85); E_(c,0,-23,5,2.5,'#6b3a0a'); L_(c,0,-50,0,-58,4,'#3f8f2a'); },
  cactus(c){ R_(c,-11,-62,22,62,10,'#4fae4f','#2a7a2a'); R_(c,-26,-44,12,10,4,'#4fae4f','#2a7a2a'); R_(c,-26,-52,10,16,4,'#4fae4f','#2a7a2a'); R_(c,14,-34,12,10,4,'#4fae4f','#2a7a2a');
    for(let i=0;i<6;i++){ L_(c,-8,-56+i*9,-14,-58+i*9,1.5,'#fff'); L_(c,8,-52+i*9,14,-54+i*9,1.5,'#fff'); } C_(c,0,-66,6,'#ff7ab0','#a03060',1.5); eyes_(c,-9,-44,.9); E_(c,0,-30,5,2.5,'#2a5a2a'); },
  blover(c){ for(let i=0;i<4;i++){ const a=i*Math.PI/2+.8; c.save(); c.translate(0,-34); c.rotate(a); E_(c,16,0,15,12,'#7ed348','#3d8b2a'); c.restore(); } C_(c,0,-34,10,'#6cc644','#3d8b2a'); eyes_(c,-8,-38,.7); L_(c,0,-22,0,0,5,'#3f9a2a'); },
  starfruit(c){ L_(c,0,0,0,-18,5,'#6b8f2a'); c.fillStyle='#ffd93b'; c.strokeStyle='#b8860b'; c.lineWidth=2.5; c.beginPath(); for(let i=0;i<10;i++){ const r=i%2?15:30, a=i*Math.PI/5-Math.PI/2; c.lineTo(Math.cos(a)*r,-42+Math.sin(a)*r); } c.closePath(); c.fill(); c.stroke(); eyes_(c,-9,-46,.85); E_(c,0,-34,4,2,'#6b3a0a'); },
  cabbagepult(c){ catBase(c); C_(c,-4,-52,15,'#9ccf6a','#4f8f2a',2.5); c.strokeStyle='#5fa83a'; c.lineWidth=1.5; c.beginPath(); c.arc(-4,-52,9,.5,4); c.stroke(); },
  kernelpult(c){ catBase(c); E_(c,-4,-50,11,16,'#ffd93b','#b8860b'); for(let i=0;i<6;i++) C_(c,-8+(i%2)*8,-56+((i/2)|0)*7,2.5,'#fff0a0'); E_(c,-12,-44,6,14,'#7ec04a','#3d8b2a',.3); },
  melonpult(c){ catBase(c); C_(c,-4,-54,19,'#2f9a4a','#17602a',2.5); for(let i=-1;i<=1;i++) L_(c,-4+i*7,-70,-4+i*5,-38,2,'#1a6a30'); },
  coffeebean(c){ E_(c,0,-24,16,22,'#5a3a22','#3a2412',.2,2.5); L_(c,-2,-42,3,-8,2,'#3a2412'); eyes_(c,-10,-28,.8); E_(c,0,-14,5,2.5,'#2a1208'); },
  puffshroom(c,st){ mush(c,'#8e5bbf','#5a3a85',{spots:1,s:.85,sleep:st==='sleep'}); },
  seashroom(c,st){ mush(c,'#4aa8c8','#2a6a88',{spots:1,s:.85,sleep:st==='sleep'}); C_(c,16,-48,3,'rgba(200,240,255,.7)'); },
  sunshroom(c,st){ mush(c,'#f4a22a','#b86a10',{spots:1,s:st==='big'?1.15:.8,sleep:st==='sleep'}); },
  fumeshroom(c,st){ mush(c,'#9b4fc2','#5e2a80',{spots:1,s:1.1,sleep:st==='sleep',extra:cc=>{ E_(cc,18,-30,9,6,'#7a3a9a','#4a1a60'); }}); },
  gravebuster(c,st){ mush(c,'#4a4a58','#25252f',{s:1,sleep:st==='sleep',extra:cc=>{ L_(cc,-14,-40,-22,-48,3,'#bbb'); L_(cc,14,-40,22,-48,3,'#bbb'); }}); },
  hypnoshroom(c,st){ mush(c,'#e0508a','#8a1f4a',{s:1,sleep:st==='sleep',extra:cc=>{ C_(cc,0,-31,10,null,'#ffe066',2); C_(cc,0,-31,6,null,'#6ad',2); C_(cc,0,-31,2.5,'#fff'); }}); },
  iceshroom(c,st){ mush(c,'#7ec8f0','#2a7aa8',{s:1,sleep:st==='sleep',extra:cc=>{ cc.fillStyle='#e8f8ff'; for(let i=0;i<3;i++){ cc.beginPath(); cc.moveTo(-8+i*8,-42); cc.lineTo(-5+i*8,-54); cc.lineTo(-2+i*8,-42); cc.fill(); } }}); },
  doomshroom(c,st){ mush(c,'#4a2a6a','#1a0a2a',{s:1.2,sleep:st==='sleep',spots:1,extra:cc=>{ C_(cc,-6,-40,2.5,'#ff3030'); C_(cc,6,-40,2.5,'#ff3030'); }}); }
};
function catBase(c){ R_(c,-26,-12,52,10,3,'#8a5a2b','#4a2f10'); C_(c,-16,-4,8,'#555','#222',2); C_(c,16,-4,8,'#555','#222',2); L_(c,10,-12,-12,-40,6,'#a8743a'); L_(c,-12,-40,-14,-34,10,'#7a5028'); eyes_(c,2,-24,.6); }
function plantSprite(id,st){ return sprite('p_'+id+'_'+(st||''),130,130,65,118,c=>PD[id](c,st)); }
function plantIcon(id,x,y,sc,al){ const s=plantSprite(id,id==='puffshroom'||PLANTS[id].mush?'':''); blit(s,x,y,sc,al); }

// ================= ĐỒ HỌA ZOMBIE =================
function ZDRAW(c,type,fr,o){
  const sc=type==='garg'?1.7:(type==='imp'?.62:1); c.scale(sc,sc);
  const sw=Math.sin(fr*Math.PI/2), swim=ZD[type].swim, skin='#a8c496', skinD='#5f7a52';
  const showBody=!(o.sub);
  if(swim){ C_(c,0,0,0); }
  // chân
  if(showBody && !swim){ [[-1,'#3d3b38'],[1,'#4d4a46']].forEach(([s,col])=>{ const fx=s*sw*11+(s>0?3:-5), fy=-2-Math.max(0,s*sw)*5; L_(c,0,-34,fx,fy,10,col); E_(c,fx-3,fy+1,9,4,'#2a2420'); }); }
  // thân
  if(showBody){
    R_(c,-13,-70,26,38,6,'#7a6a55','#3a2e20'); c.fillStyle='#e8e2d0'; c.beginPath(); c.moveTo(-5,-70); c.lineTo(5,-70); c.lineTo(0,-58); c.fill(); c.fillStyle='#8b2c2c'; c.fillRect(-2,-60,4,16);
    if(type==='football'){ E_(c,-4,-68,17,10,'#b82020','#601010'); }
    if(type==='garg'){ c.fillStyle='#7d6a55'; c.fillRect(-13,-52,26,6); }
  }
  // đầu
  const hy=-82, hx=-4;
  if(showBody||o.sub){ C_(c,hx,hy,15,skin,skinD,2.5); E_(c,hx+11,hy-1,4,5,skin,skinD); L_(c,hx-4,hy-14,hx-8,hy-22,2,'#2a2018'); L_(c,hx+2,hy-15,hx+3,hy-23,2,'#2a2018');
    C_(c,hx-9,hy-3,5.5,'#fff','#333',1.2); C_(c,hx-9.5,hy-3,2.6,o.rage?'#e00':'#b22'); C_(c,hx+1,hy-2,3.8,'#fff','#333',1.2); C_(c,hx,hy-2,1.8,'#b22');
    if(o.eat){ E_(c,hx-5,hy+7,6,4.5,'#3a1010'); } else { L_(c,hx-9,hy+7,hx+1,hy+8,2,'#3a1010'); c.fillStyle='#eee'; c.fillRect(hx-6,hy+7,2.5,2.5); c.fillRect(hx-1,hy+7,2.5,2.5); } }
  // trang bị đầu
  if(type==='cone'||type==='duckcone'){ const t=o.armor; c.fillStyle='#e87a1e'; c.strokeStyle='#8a4a10'; c.lineWidth=2; c.beginPath(); if(t>1){ c.moveTo(-18,hy-10); c.lineTo(-4,hy-34); c.lineTo(10,hy-10); } else { c.moveTo(-18,hy-10); c.lineTo(-8,hy-22); c.lineTo(-2,hy-18); c.lineTo(10,hy-10); } c.closePath(); c.fill(); c.stroke(); L_(c,-12,hy-17,6,hy-17,3,'#fff'); }
  if(type==='bucket'||type==='duckbucket'){ const t=o.armor; c.fillStyle='#9aa0a6'; c.strokeStyle='#4a5056'; c.lineWidth=2; c.beginPath(); c.moveTo(-20,hy-12); c.lineTo(-17,hy-34+(t<2?6:0)); c.lineTo(13,hy-34+(t<2?6:0)); c.lineTo(16,hy-12); c.closePath(); c.fill(); c.stroke(); E_(c,-2,hy-12,18,4,'#7a8086','#4a5056'); if(t<2){ L_(c,-8,hy-26,-2,hy-20,2,'#4a5056'); } }
  if(type==='football'){ C_(c,hx,hy-2,17,'#c0242b','#601010',2.5); L_(c,hx-13,hy+3,hx+14,hy+3,2,'#ddd'); L_(c,hx-13,hy+9,hx+14,hy+9,2,'#ddd'); L_(c,hx+10,hy-6,hx+10,hy+12,2,'#ddd'); }
  if(type==='snorkel'){ C_(c,hx-4,hy-6,8,'#3a7ab0','#1a3a60',2); L_(c,hx+6,hy-12,hx+12,hy-34,3,'#e8a020'); L_(c,hx+10,hy-34,hx+18,hy-34,3,'#e8a020'); }
  if(type==='flag'){ L_(c,10,-98,10,0,3,'#7a5028'); c.fillStyle='#c0242b'; c.fillRect(-14,-114,24,16); c.fillStyle='#fff'; c.fillRect(-4,-109,6,6); }
  if(type==='pole'&&!o.jumped){ L_(c,-28,-6,14,-92,3,'#9a6a30'); }
  // tay
  if(showBody){ const ay=o.eat?-5:0, bob=sw*3; L_(c,-6,-62,-30,-56+ay+bob,8,'#6a5a45'); L_(c,-30,-56+ay+bob,-38,-58+ay+bob,7,skin); C_(c,-39,-58+ay+bob,5,skin,skinD,1.5);
    if(!o.hurt){ L_(c,-4,-60,-28,-52-ay-bob,8,'#7a6a55'); C_(c,-31,-52-ay-bob,5,skin,skinD,1.5); } }
  // vật phẩm trước mặt
  if(type==='door'&&o.shield){ const t=o.shield; R_(c,-50,-92,24,86,2,'rgba(120,130,135,.35)','#6a7076'); c.strokeStyle='rgba(60,70,75,.7)'; c.lineWidth=1; for(let i=0;i<9;i++){ c.beginPath(); c.moveTo(-50,-90+i*10); c.lineTo(-26,-90+i*10); c.stroke(); } for(let i=0;i<4;i++){ c.beginPath(); c.moveTo(-46+i*6,-92); c.lineTo(-46+i*6,-8); c.stroke(); } if(t<2){ L_(c,-48,-70,-30,-40,2,'#222'); } }
  if(type==='news'&&o.armor){ R_(c,-52,-80,26,34,2,'#f2f0e6','#888'); for(let i=0;i<5;i++) L_(c,-49,-74+i*6,-29,-74+i*6,1.5,'#777'); }
  if(swim){ E_(c,0,-30,24,8,'#f4c430','#a07a10',0,2.5); E_(c,0,-27,24,7,null,'#fff',0,1); C_(c,-24,-36,7,'#ffd23f','#a07a10',1.5); E_(c,-30,-36,4,2.5,'#ff8a1e'); }
  if(type==='garg'){ L_(c,-12,-60,-60,-30,14,'#6a5a45'); E_(c,-68,-24,14,34,'#8a5a30','#4a2f10',.5,3); C_(c,10,-96,9,skin,skinD,1.5); C_(c,12,-98,3,'#fff'); }
}
function zSprite(z,fr,eat){
  const a=z.armor?(z.armor.hp/z.armor.max>.5?2:1):0, s=z.shield?(z.shield.hp/z.shield.max>.5?2:1):0, hurt=z.hp<=100?1:0, big=z.type==='garg';
  const key=['z',z.type,fr,eat?1:0,a,s,hurt,z.rage?1:0,z.jumped?1:0,z.sub?1:0,z.imp?1:0].join('|');
  const sz=big?[300,300,150,270]:[180,170,90,150];
  return sprite(key,sz[0],sz[1],sz[2],sz[3],c=>ZDRAW(c,z.type,fr,{armor:a,shield:s,hurt,eat,rage:z.rage,jumped:z.jumped,sub:z.sub,imp:z.imp}));
}
function tintOf(sp,key,col){ const k='t|'+key+'|'+col; let t=SPR[k]; if(t) return t; const cn=document.createElement('canvas'); cn.width=sp.w; cn.height=sp.h; const c=cn.getContext('2d'); c.drawImage(sp.cn,0,0); c.globalCompositeOperation='source-atop'; c.fillStyle=col; c.fillRect(0,0,sp.w,sp.h); t={cn,ox:sp.ox,oy:sp.oy,w:sp.w,h:sp.h}; SPR[k]=t; return t; }

// ================= NỀN BẢN ĐỒ =================
const BG={};
function cloud_(c,x,y,s){ c.fillStyle='rgba(255,255,255,.9)'; c.beginPath(); c.arc(x,y,14*s,0,7); c.arc(x+16*s,y-8*s,18*s,0,7); c.arc(x+34*s,y,14*s,0,7); c.fill(); }
function bgFor(M){
  if(BG[M.id]) return BG[M.id];
  const cn=document.createElement('canvas'); cn.width=W; cn.height=H; const c=cn.getContext('2d'), rows=M.rows, RH=500/rows, night=M.night;
  let sky=c.createLinearGradient(0,0,0,110); if(night){ sky.addColorStop(0,'#0a1030'); sky.addColorStop(1,'#243060'); } else { sky.addColorStop(0,'#74c0f0'); sky.addColorStop(1,'#dff3ff'); }
  c.fillStyle=sky; c.fillRect(0,0,W,H);
  if(night){ c.fillStyle='#fff'; for(let i=0;i<40;i++) c.fillRect(Math.random()*W,Math.random()*90,1.6,1.6); C_(c,780,40,20,'#f4f0c8'); C_(c,772,34,4,'rgba(0,0,0,.08)'); } else { cloud_(c,300,40,1); cloud_(c,560,26,.8); cloud_(c,700,58,1.1); }
  const lawnA=night?'#2c5a34':'#58a82f', lawnB=night?'#336840':'#4f9c2a';
  if(M.roof){
    c.fillStyle='#7fb8e8'; c.fillRect(0,0,W,100);
    for(let r=0;r<rows;r++) for(let k=0;k<9;k++){ const x=GX+k*CW, y=100+r*RH, slope=k>=5; c.fillStyle=slope?((r+k)%2?'#8e4524':'#9a4d28'):((r+k)%2?'#b5632f':'#a85a2a'); c.fillRect(x,y,CW,RH);
      c.strokeStyle='rgba(60,25,10,.45)'; c.lineWidth=1.5; c.strokeRect(x,y,CW,RH); for(let q=0;q<4;q++){ c.beginPath(); c.moveTo(x,y+q*RH/4); c.lineTo(x+CW,y+q*RH/4); c.stroke(); } if(slope){ c.fillStyle='rgba(0,0,0,'+((k-4)*.07)+')'; c.fillRect(x,y,CW,RH); } }
    c.fillStyle='#7a4a2a'; c.fillRect(0,100,GX,500); c.fillStyle='#5a3a20'; c.fillRect(GX+CW*9,100,60,500); R_(c,GX+CW*8,30,54,76,3,'#8a4a2a','#4a2a10'); R_(c,GX+CW*8-6,22,66,12,3,'#6a3a20','#3a1a08');
  } else {
    c.fillStyle=night?'#2a4a2a':'#3c8a24'; c.fillRect(0,88,W,14); for(let i=0;i<W;i+=26){ C_(c,i,90,11,night?'#244a28':'#3f9a2a'); }
    for(let r=0;r<rows;r++) for(let k=0;k<9;k++){ const x=GX+k*CW, y=100+r*RH, water=M.water.includes(r);
      if(water){ const g=c.createLinearGradient(0,y,0,y+RH); g.addColorStop(0,night?'#1f5a8a':'#3aa8dc'); g.addColorStop(1,night?'#174a78':'#2a8ac0'); c.fillStyle=g; } else c.fillStyle=(r+k)%2?lawnA:lawnB;
      c.fillRect(x,y,CW,RH); }
    if(M.water.length){ const y0=100+M.water[0]*RH, h=M.water.length*RH; c.strokeStyle='#e6eef4'; c.lineWidth=6; c.strokeRect(GX,y0,CW*9,h); c.strokeStyle='rgba(255,255,255,.25)'; c.lineWidth=2; for(let r=1;r<M.water.length;r++){ c.beginPath(); c.moveTo(GX,y0+r*RH); c.lineTo(GX+CW*9,y0+r*RH); c.stroke(); } }
    c.fillStyle=night?'#1a2a1a':'#d8c9a2'; c.fillRect(0,100,GX,500); c.fillStyle=night?'#243424':'#c4b48a'; for(let i=0;i<7;i++) for(let j=0;j<4;j++) R_(c,6+j*30,104+i*74,26,66,5,night?'#2c3e2c':'#cdbd94');
    c.fillStyle=night?'#1e3a22':'#2f7a22'; c.fillRect(GX+CW*9,100,60,500);
  }
  c.fillStyle='rgba(0,0,0,.18)'; c.fillRect(GX-4,100,4,500);
  if(night){ c.fillStyle='rgba(8,12,40,.22)'; c.fillRect(0,100,W,500); }
  BG[M.id]=cn; return cn;
}
'''JS_ENGINE = r'''
// ================= ENGINE =================
const cxr=c=>GX+(c+.5)*CW, cyr=r=>LT+(r+.5)*G.RH;
function seedCd0(id){ const c=PLANTS[id].cd; return c>=30?c*.6:0; }
function newGame(L,seeds,surv){
  const M=L.map, rows=M.rows, RH=500/rows;
  G={L,map:M,rows,RH,surv:!!surv,t:0,sun:50+SAVE.sunUp*50,grid:[],PL:[],Z:[],proj:[],suns:[],coins:[],parts:[],fx:[],pend:[],mow:[],
     bar:seeds.map(id=>({id,cd:seedCd0(id)})),sel:null,shovel:false,wave:0,waves:surv?99999:L.waves,wt:surv?24:22,since:0,hp0:1,sunT:5,intro:3.6,
     banner:null,over:null,reward:null,fog:[],blow:0,kills:0,earned:0,final:false,shake:0,lastDie:{x:600,y:300},lose:0,notify:0};
  for(let r=0;r<rows;r++){ G.grid[r]=[]; G.fog[r]=[]; for(let c=0;c<9;c++){ G.grid[r][c]={base:null,plant:null,grave:false,crater:0}; G.fog[r][c]=0; } G.mow[r]={x:58,on:false,used:false}; }
  if(M.id==='NIGHT'){ let n=3+L.i, guard=0; while(n>0&&guard++<80){ const r=Math.floor(Math.random()*rows), c=3+Math.floor(Math.random()*6); if(!G.grid[r][c].grave){ G.grid[r][c].grave=true; n--; } } }
  S='PLAY'; PAUSED=false;
}
function cellOf(px,py){ const c=Math.floor((px-GX)/CW), r=Math.floor((py-LT)/G.RH); return (c>=0&&c<9&&r>=0&&r<G.rows)?{r,c}:null; }
function isWater(r){ return G.map.water.indexOf(r)>=0; }
function canPlant(id,r,c){
  const P=PLANTS[id], cl=G.grid[r][c], w=isWater(r), roof=G.map.roof;
  if(id==='coffeebean') return !!(cl.plant&&cl.plant.sleep);
  if(id==='gravebuster') return cl.grave&&!cl.plant;
  if(cl.grave||cl.crater>0) return false;
  if(id==='lilypad') return w&&!cl.base&&!cl.plant;
  if(id==='flowerpot') return roof&&!cl.base&&!cl.plant;
  if(cl.plant) return false;
  if(P.water) return w;
  if(w) return cl.base==='lily';
  if(roof) return cl.base==='pot';
  return true;
}
function addP(x,y,n,col,spd,life,sz){ if(G.parts.length>260) return; for(let i=0;i<n;i++){ const a=Math.random()*6.283, v=rnd(.3,1)*(spd||90); G.parts.push({x,y,vx:Math.cos(a)*v,vy:Math.sin(a)*v-20,l:life||.6,m:life||.6,col,sz:sz||3}); } }
function addSun(x,y,v,kind){ G.suns.push({x,y,v,kind,ty:kind==='sky'?y:y+34,vy:kind==='sky'?52:-80,age:0,fly:null}); }
function doPlant(id,r,c){
  const P=PLANTS[id], cl=G.grid[r][c], seed=G.bar.find(s=>s.id===id);
  G.sun-=P.cost; if(seed) seed.cd=P.cd; snd('plant');
  if(id==='lilypad'){ cl.base='lily'; return; }
  if(id==='flowerpot'){ cl.base='pot'; return; }
  if(id==='coffeebean'){ cl.plant.sleep=false; addP(cxr(c),cyr(r),14,'#b98b5a',80); return; }
  if(id==='gravebuster'){ cl.plant=mkPlant(id,r,c); G.PL.push(cl.plant); return; }
  const p=mkPlant(id,r,c); cl.plant=p; G.PL.push(p);
  if(id==='blover'){ G.blow=12; snd('wave'); }
}
function mkPlant(id,r,c){
  const P=PLANTS[id], p={id,r,c,hp:P.hp,max:P.hp,age:0,cd:1,sunT:id==='sunshroom'?12:rnd(5,9),sleep:!!P.mush&&!G.map.night,seed:Math.random()*6,rec:0,n:0,t:0,big:false,chew:0,bite:0,jump:0,pull:0,burst:0,spT:0};
  if(id==='potatomine') p.armT=15;
  if(P.k==='bomb'||P.k==='ice'||P.k==='doom') p.fuse=id==='doomshroom'?1.6:1;
  return p;
}
function rmPlant(p){ const cl=G.grid[p.r][p.c]; if(cl.plant===p) cl.plant=null; const i=G.PL.indexOf(p); if(i>=0) G.PL.splice(i,1); }
function killPlantFx(p){ addP(cxr(p.c),cyr(p.r),8,'#4a8a2a',70); }

// ---------- Zombie ----------
function makeZ(type,r,x,rise){
  const D=ZD[type], z={type,r,x:x||W+40+Math.random()*60,hp:D.hp,mhp:D.hp,armor:D.arm?{k:D.ak,hp:D.arm,max:D.arm}:null,shield:D.sh?{hp:D.sh,max:D.sh}:null,
    st:'walk',fr:Math.random()*4,slow:0,frz:0,stun:0,hyp:false,sub:!!D.snorkel,jumped:false,rage:false,dead:0,eatT:0,flash:0,riseT:rise||0,wv:G.wave-1,imp:type==='garg',jy:0,jt:0,swim:!!D.swim};
  return z;
}
function rowFor(type){
  const D=ZD[type], rows=[]; for(let r=0;r<G.rows;r++){ if(D.swim?isWater(r):!isWater(r)) rows.push(r); }
  return rows.length?rows[Math.floor(Math.random()*rows.length)]:Math.floor(Math.random()*G.rows);
}
function hurt(z,d,o){
  o=o||{}; if(z.dead>0) return;
  if(z.shield && !o.lob && !o.pierce && !o.boom){ z.shield.hp-=d; z.flash=.1; if(z.shield.hp<=0) z.shield=null; return; }
  let rest=d;
  if(z.armor){ z.armor.hp-=rest; if(z.armor.hp<=0){ rest=-z.armor.hp; if(z.armor.k==='paper'){ z.rage=true; z.stun=.7; } z.armor=null; } else rest=0; }
  if(rest>0) z.hp-=rest; z.flash=.1;
  if(z.hp<=0) killZ(z);
}
function killZ(z){
  if(z.dead>0) return; z.dead=.9; G.kills++; G.lastDie={x:Math.min(780,Math.max(220,z.x)),y:cyr(z.r)};
  addP(z.x,cyr(z.r)-30,6,'#7a8a6a',80,.5); snd('splat');
  const r=Math.random(); if(r<.2) G.coins.push({x:z.x,y:cyr(z.r)+10,v:r<.03?50:10,age:0,vy:-120});
}
function hasT(r,x,range){ for(const z of G.Z){ if(z.r===r&&z.dead<=0&&!z.sub&&!z.hyp&&z.riseT<=0&&z.x>x-14&&z.x<x+range&&z.x<W-8) return true; } return false; }
function firstZ(r,x){ let b=null; for(const z of G.Z){ if(z.r===r&&z.dead<=0&&!z.sub&&!z.hyp&&z.riseT<=0&&z.x>x-20&&z.x<W-8&&(!b||z.x<b.x)) b=z; } return b; }

// ---------- Đợt zombie ----------
function spawnWave(){
  const j=G.wave, L=G.L, big=G.surv?((j+1)%10===0):(j===G.waves-1||(G.waves>=8&&j===(G.waves>>1)));
  let list=genWave(L,j,big,G.surv);
  if(G.map.water.length) list=list.map(t=>(WAT[t]&&Math.random()<.5)?WAT[t]:t);
  G.wave++; G.since=0; G.wt=G.surv?26:(24+Math.random()*4); G.hp0=0;
  list.forEach((t,i)=>{ G.pend.push({t:big?rnd(0,5):rnd(0,3.5)+(j===0?0:0),type:t,row:rowFor(t)}); G.hp0+=ZD[t].hp+(ZD[t].arm||0)+(ZD[t].sh||0); });
  if(G.map.id==='NIGHT'&&j>0){ const gr=[]; for(let r=0;r<G.rows;r++) for(let c=0;c<9;c++) if(G.grid[r][c].grave) gr.push([r,c]);
    for(let i=0;i<Math.min(2,gr.length);i++){ const g=gr[Math.floor(Math.random()*gr.length)]; G.pend.push({t:rnd(1,4),type:'basic',row:g[0],x:cxr(g[1]),rise:2.2}); } }
  if(!G.surv&&j===G.waves-1) G.final=true;
  if(big){ G.banner={txt:G.surv?'MỘT ĐỢT ZOMBIE KHỔNG LỒ ĐANG ĐẾN!':(j===G.waves-1?'ĐỢT CUỐI CÙNG!':'MỘT ĐỢT ZOMBIE KHỔNG LỒ ĐANG ĐẾN!'),t:4,col:'#ff5030'}; snd('wave'); }
  else if(j===0){ G.banner={txt:'Zombie đang đến!',t:2.5,col:'#ffd23f'}; snd('groan'); } else snd('groan');
}
function waveHP(){ let s=0; for(const z of G.Z){ if(z.dead<=0&&z.wv===G.wave-1) s+=Math.max(0,z.hp)+(z.armor?z.armor.hp:0)+(z.shield?z.shield.hp:0); } return s; }

// ---------- Cập nhật ----------
function explode(p){
  const px=cxr(p.c), py=cyr(p.r), id=p.id;
  if(id==='cherrybomb'){ for(const z of G.Z) if(z.dead<=0&&Math.abs(z.r-p.r)<=1&&Math.abs(z.x-px)<CW*1.6) hurt(z,1800,{boom:1}); G.fx.push({k:'boom',x:px,y:py,t:.5,m:.5,r:CW*1.5}); G.shake=.35; snd('boom'); }
  else if(id==='jalapeno'){ for(const z of G.Z) if(z.dead<=0&&z.r===p.r) hurt(z,1800,{boom:1}); G.fx.push({k:'fire',x:px,y:py,t:.8,m:.8}); G.shake=.3; snd('boom'); }
  else if(id==='iceshroom'){ for(const z of G.Z) if(z.dead<=0){ hurt(z,20,{boom:1}); z.frz=4; z.slow=12; } G.fx.push({k:'ice',x:W/2,y:H/2,t:.7,m:.7}); snd('freeze'); }
  else if(id==='doomshroom'){ for(const z of G.Z) if(z.dead<=0&&Math.abs(z.r-p.r)<=2&&Math.abs(z.x-px)<CW*2.9) hurt(z,1800,{boom:1}); G.grid[p.r][p.c].crater=60; G.fx.push({k:'boom',x:px,y:py,t:.8,m:.8,r:CW*2.8,dark:1}); G.shake=.7; snd('boom'); }
  rmPlant(p);
}
function fire(p,r,k){
  const px=cxr(p.c), y=cyr(r)-G.RH*.14;
  const pr={x:px+26,y,vx:340,vy:0,row:r,k:k||'pea',dmg:20,dir:true};
  if(p.id==='cactus'){ pr.k='spike'; pr.pierce=true; } if(p.id==='puffshroom'||p.id==='seashroom'){ pr.k='puff'; pr.vx=300; }
  if(p.id==='snowpea') pr.k='snow';
  G.proj.push(pr); p.rec=.35; snd('shoot');
}
function updPlants(dt){
  for(let i=G.PL.length-1;i>=0;i--){
    const p=G.PL[i], P=PLANTS[p.id]; p.age+=dt; if(p.rec>0) p.rec-=dt;
    if(p.hp<=0){ killPlantFx(p); rmPlant(p); continue; }
    if(p.sleep) continue;
    const px=cxr(p.c), py=cyr(p.r);
    switch(P.k){
      case 'shoot': {
        const rate=(p.id==='puffshroom'||p.id==='seashroom')?1.5:1.45, range=(p.id==='puffshroom'||p.id==='seashroom')?CW*3.7:9999;
        const rowsT=p.id==='threepeater'?[p.r-1,p.r,p.r+1].filter(r=>r>=0&&r<G.rows):[p.r];
        p.cd-=dt;
        if(p.cd<=0){ if(rowsT.some(r=>hasT(r,px,range))){ rowsT.forEach(r=>fire(p,r)); p.cd=rate; if(p.id==='repeater') p.burst=.16; } else p.cd=.05; }
        if(p.burst>0){ p.burst-=dt; if(p.burst<=0) fire(p,p.r); }
        break; }
      case 'fume': { p.cd-=dt; if(p.cd<=0){ if(hasT(p.r,px,CW*4.4)){ for(const z of G.Z) if(z.r===p.r&&z.dead<=0&&!z.sub&&!z.hyp&&z.x>px&&z.x<px+CW*4.4&&z.x<W-8) hurt(z,20,{pierce:1}); G.fx.push({k:'fume',x:px+28,y:cyr(p.r)-12,t:.4,m:.4}); p.rec=.35; snd('shoot'); p.cd=1.5; } else p.cd=.05; } break; }
      case 'sun': { if(p.id==='sunshroom'&&!p.big&&p.age>120) p.big=true; p.sunT-=dt; if(p.sunT<=0){ addSun(px+rnd(-14,14),py-14,(p.id==='sunshroom'&&!p.big)?15:25,'plant'); p.sunT=24; } break; }
      case 'bomb': case 'ice': case 'doom': { p.fuse-=dt; if(p.fuse<=0) explode(p); break; }
      case 'jala': { p.fuse=(p.fuse===undefined?1:p.fuse)-dt; if(p.fuse<=0) explode(p); break; }
      case 'mine': { if(p.armT>0){ p.armT-=dt; break; } let hit=false; for(const z of G.Z) if(z.r===p.r&&z.dead<=0&&!z.sub&&!z.hyp&&Math.abs(z.x-px)<46){ hit=true; break; }
        if(hit){ for(const z of G.Z) if(z.r===p.r&&z.dead<=0&&Math.abs(z.x-px)<CW*.95) hurt(z,1800,{boom:1}); G.fx.push({k:'boom',x:px,y:py,t:.4,m:.4,r:CW*.9}); snd('boom'); G.shake=.2; rmPlant(p); } break; }
      case 'chomp': {
        if(p.chew>0){ p.chew-=dt; break; }
        if(p.bite>0){ p.bite-=dt; if(p.bite<=0){ if(p.tgt&&p.tgt.dead<=0){ killZ(p.tgt); G.Z.splice(G.Z.indexOf(p.tgt),1); snd('chomp'); } p.tgt=null; p.chew=42; } break; }
        for(const z of G.Z) if(z.r===p.r&&z.dead<=0&&!z.sub&&!z.hyp&&z.riseT<=0&&z.type!=='garg'&&z.x>px-12&&z.x<px+CW*1.3){ p.tgt=z; p.bite=.8; break; }
        break; }
      case 'squash': {
        if(p.jump>0){ p.jump-=dt; if(p.jump<=0){ for(const z of G.Z) if(z.r===p.r&&z.dead<=0&&Math.abs(z.x-p.tx)<60) hurt(z,1800,{boom:1}); addP(p.tx,cyr(p.r)+20,10,'#9aa070',90); G.shake=.25; snd('boom'); rmPlant(p); } break; }
        for(const z of G.Z) if(z.r===p.r&&z.dead<=0&&!z.sub&&!z.hyp&&z.riseT<=0&&z.x>px-34&&z.x<px+CW*1.1){ p.jump=.55; p.tx=z.x; p.jx=px; break; }
        break; }
      case 'kelp': {
        if(p.pull>0){ p.pull-=dt; if(p.pull<=0) rmPlant(p); break; }
        for(const z of G.Z) if(z.r===p.r&&z.dead<=0&&!z.hyp&&Math.abs(z.x-px)<48){ hurt(z,9999,{boom:1}); p.pull=1.1; addP(px,cyr(p.r),12,'#6ac0f0',90); snd('splat'); break; }
        break; }
      case 'spike': { p.spT-=dt; if(p.spT<=0){ let hit=false; for(const z of G.Z) if(z.r===p.r&&z.dead<=0&&!z.sub&&!z.hyp&&Math.abs(z.x-px)<CW*.5){ hurt(z,20,{lob:1}); hit=true; } if(hit){ p.rec=.2; p.spT=.45; } else p.spT=.1; } break; }
      case 'grave': { p.t+=dt; if(p.t>=4){ G.grid[p.r][p.c].grave=false; addP(px,py,14,'#888',90); rmPlant(p); } break; }
      case 'blover': { p.t+=dt; if(p.t>=1.3) rmPlant(p); break; }
      case 'star': { p.cd-=dt; if(p.cd<=0){ if(hasT(p.r,px,9999)){ [[1,0],[0,-1],[0,1],[-.8,-.6],[-.8,.6]].forEach(v=>G.proj.push({x:px,y:py-20,vx:v[0]*300,vy:v[1]*300,k:'star',dmg:20,dir:true})); p.rec=.35; snd('shoot'); p.cd=1.6; } else p.cd=.1; } break; }
      case 'lob': { p.cd-=dt; if(p.cd<=0){ const z=firstZ(p.r,px);
        if(z){ p.n++; const T=1.0, v=(CW/ZD[z.type].sp)*(z.slow>0?.5:1)*(z.st==='walk'?1:0), kind=p.id==='cabbagepult'?'cab':(p.id==='melonpult'?'melon':(p.n%4===0?'butter':'kern'));
          G.proj.push({arc:true,x0:px+6,y0:py-30,x1:Math.max(px+30,z.x-v*T),y1:cyr(p.r)-G.RH*.1,t:0,T,k:kind,row:p.r,dmg:kind==='melon'?80:(kind==='cab'?40:(kind==='butter'?40:30))}); p.rec=.4; snd('shoot'); p.cd=3.1; } else p.cd=.1; } break; }
    }
  }
}
function landArc(p){
  let tz=null, bd=1e9; for(const z of G.Z) if(z.r===p.row&&z.dead<=0&&!z.sub&&!z.hyp&&z.riseT<=0){ const d=Math.abs(z.x-p.x1); if(d<70&&d<bd){ bd=d; tz=z; } }
  if(tz){ hurt(tz,p.dmg,{lob:1}); if(p.k==='butter'){ tz.stun=4; } addP(tz.x,p.y1,6,p.k==='melon'?'#d33':(p.k==='kern'||p.k==='butter'?'#ffd23f':'#9ccf6a'),90,.4); snd('splat'); }
  if(p.k==='melon'){ for(const z of G.Z) if(z!==tz&&z.dead<=0&&!z.sub&&!z.hyp&&Math.abs(z.r-p.row)<=1&&Math.abs(z.x-p.x1)<CW*1.1) hurt(z,40,{lob:1}); G.fx.push({k:'splash',x:p.x1,y:p.y1,t:.35,m:.35}); }
}
function updProj(dt){
  for(let i=G.proj.length-1;i>=0;i--){
    const p=G.proj[i];
    if(p.arc){ p.t+=dt; const u=Math.min(1,p.t/p.T); p.x=p.x0+(p.x1-p.x0)*u; p.y=p.y0+(p.y1-p.y0)*u-Math.sin(u*Math.PI)*110; if(u>=1){ landArc(p); G.proj.splice(i,1); } continue; }
    p.x+=p.vx*dt; p.y+=p.vy*dt;
    if(p.x>W+20||p.x<-20||p.y<70||p.y>H){ G.proj.splice(i,1); continue; }
    if(G.map.roof&&p.dir&&p.x>cxr(5)-30){ addP(p.x,p.y,3,'#8a8',50,.3); G.proj.splice(i,1); continue; }
    if(p.row!==undefined&&(p.k==='pea'||p.k==='snow')){ const c=Math.floor((p.x-GX)/CW); if(c>=0&&c<9){ const pl=G.grid[p.row][c].plant; if(pl&&pl.id==='torchwood'&&!p.fire&&Math.abs(p.x-cxr(c))<16){ p.fire=true; p.k='pea'; p.dmg*=2; addP(p.x,p.y,4,'#ff8a1e',60,.3); } } }
    let hit=null;
    for(const z of G.Z){ if(z.dead>0||z.sub||z.hyp||z.riseT>0) continue; if(p.row!==undefined?z.r!==p.row:Math.abs(cyr(z.r)-p.y)>G.RH*.55) continue; if(Math.abs(z.x-p.x)<17){ hit=z; break; } }
    if(hit){
      hurt(hit,p.dmg,{pierce:p.pierce}); if(p.k==='snow'){ hit.slow=10; }
      if(p.fire){ for(const z of G.Z) if(z!==hit&&z.r===hit.r&&z.dead<=0&&Math.abs(z.x-hit.x)<50) hurt(z,13,{lob:1}); }
      addP(p.x,p.y,3,p.k==='snow'?'#aef':(p.fire?'#ff8a1e':'#8fdc4f'),60,.3); snd('splat'); G.proj.splice(i,1);
    }
  }
}
function plantAtZ(z){ let b=null; for(const p of G.PL){ if(p.r!==z.r) continue; const px=cxr(p.c); if(px>z.x-40&&px<z.x+26&&(!b||px>cxr(b.c))) b=p; } return b; }
function nearPlant(z,d){ for(const p of G.PL){ if(p.r!==z.r) continue; const px=cxr(p.c); if(px<z.x-18&&px>z.x-d) return p; } return null; }
function updZ(dt){
  for(let i=G.Z.length-1;i>=0;i--){
    const z=G.Z[i], D=ZD[z.type];
    if(z.dead>0){ z.dead-=dt; if(z.dead<=0) G.Z.splice(i,1); continue; }
    if(z.flash>0) z.flash-=dt;
    if(z.riseT>0){ z.riseT-=dt; continue; }
    if(z.frz>0){ z.frz-=dt; continue; }
    if(z.stun>0){ z.stun-=dt; continue; }
    const sf=z.slow>0?.5:1; if(z.slow>0) z.slow-=dt;
    z.fr+=dt*(z.st==='eat'?3.5:5.5*sf);
    if(z.type==='garg'&&!z.threw&&z.hp<D.hp/2){ z.threw=true; z.imp=false; G.Z.push(makeZ('imp',z.r,z.x-CW*1.6)); }
    if(z.hyp){
      const f=G.Z.find(o=>o!==z&&!o.hyp&&o.dead<=0&&o.r===z.r&&!o.sub&&o.x>z.x&&o.x-z.x<46);
      if(f){ z.st='eat'; hurt(f,110*dt,{lob:1}); } else { z.st='walk'; z.x+=CW/D.sp*sf*dt; }
      if(z.x>W+60){ G.Z.splice(i,1); } continue;
    }
    if(z.st==='jump'){ z.jt-=dt; const u=1-Math.max(0,z.jt)/.9; z.x=z.jx0+(z.jx1-z.jx0)*u; z.jy=Math.sin(u*Math.PI)*62; if(z.jt<=0){ z.st='walk'; z.jumped=true; z.jy=0; } continue; }
    if(z.type==='pole'&&!z.jumped){ const np=nearPlant(z,80); if(np){ if(np.id==='tallnut'){ z.jumped=true; } else { z.st='jump'; z.jt=.9; z.jx0=z.x; z.jx1=z.x-CW*1.6; continue; } } }
    const tgt=plantAtZ(z);
    if(tgt){
      z.st='eat'; if(z.snorkel) z.sub=false;
      if(tgt.id==='hypnoshroom'&&!tgt.sleep){ z.hyp=true; rmPlant(tgt); addP(z.x,cyr(z.r)-60,8,'#ff6ab0',60,.8); snd('plant'); continue; }
      if(D.smash){ z.smT=(z.smT||0)-dt; if(z.smT<=0){ tgt.hp=0; z.smT=1.4; snd('boom'); G.shake=.3; } }
      else { tgt.hp-=D.dps*dt*sf; z.eatT-=dt; if(z.eatT<=0){ snd('chomp'); z.eatT=.7; } }
    } else {
      z.st='walk'; if(z.snorkel) z.sub=true;
      const spd=z.rage?2.4:D.sp; z.x-=CW/spd*sf*dt;
    }
    const m=G.mow[z.r];
    if(z.x<GX-5&&!m.used&&!m.on){ m.on=true; snd('mower'); }
    if(z.x<GX-72&&!m.on){ G.lose=1; }
  }
  for(const m of G.mow){ if(m.on){ m.x+=330*dt; for(const z of G.Z) if(!z.hyp&&z.dead<=0&&G.mow.indexOf(m)===z.r&&z.x<m.x+46&&z.x>m.x-40){ hurt(z,99999,{boom:1}); } if(m.x>W+60){ m.on=false; m.used=true; } } }
}
function updMisc(dt){
  for(let i=G.suns.length-1;i>=0;i--){ const s=G.suns[i]; s.age+=dt;
    if(s.fly){ s.x+=(52-s.x)*Math.min(1,dt*9); s.y+=(40-s.y)*Math.min(1,dt*9); if(Math.hypot(s.x-52,s.y-40)<14){ G.sun+=s.v; G.suns.splice(i,1); snd('sun'); } continue; }
    if(s.kind==='sky'){ if(s.y<s.ty) s.y+=s.vy*dt; } else { s.vy+=240*dt; s.y+=s.vy*dt; if(s.y>=s.ty){ s.y=s.ty; s.vy=0; } }
    if(s.age>10) G.suns.splice(i,1); }
  for(let i=G.coins.length-1;i>=0;i--){ const c=G.coins[i]; c.age+=dt; if(c.vy<0||c.fly===undefined){ c.vy+=400*dt; c.y+=c.vy*dt; if(c.vy>0&&c.age>.4) c.vy=0; }
    if(c.fly){ c.x+=(860-c.x)*Math.min(1,dt*7); c.y+=(570-c.y)*Math.min(1,dt*7); if(Math.hypot(c.x-860,c.y-570)<14){ SAVE.coins+=c.v; G.earned+=c.v; G.coins.splice(i,1); snd('coin'); } continue; }
    if(c.age>9) G.coins.splice(i,1); }
  for(let i=G.parts.length-1;i>=0;i--){ const p=G.parts[i]; p.l-=dt; p.x+=p.vx*dt; p.y+=p.vy*dt; p.vy+=160*dt; if(p.l<=0) G.parts.splice(i,1); }
  for(let i=G.fx.length-1;i>=0;i--){ G.fx[i].t-=dt; if(G.fx[i].t<=0) G.fx.splice(i,1); }
  for(const cell of [].concat(...G.grid)) if(cell.crater>0) cell.crater-=dt;
  if(G.blow>0) G.blow-=dt;
  if(G.map.fog){ for(let r=0;r<G.rows;r++) for(let c=0;c<9;c++){ let lit=G.blow>0||c<5; if(!lit) for(const p of G.PL) if(p.id==='plantern'&&Math.hypot(c-p.c,(r-p.r)*G.RH/CW)<2.7){ lit=true; break; } const tg=lit?0:.9; G.fog[r][c]+=(tg-G.fog[r][c])*Math.min(1,dt*2.5); } }
  if(G.shake>0) G.shake-=dt; if(G.banner){ G.banner.t-=dt; if(G.banner.t<=0) G.banner=null; }
}
function update(dt){
  if(S!=='PLAY'||!G||PAUSED||G.over) return;
  dt=Math.min(dt,.05); G.t+=dt;
  if(G.intro>0) G.intro-=dt;
  for(const s of G.bar) if(s.cd>0) s.cd-=dt;
  if(!G.map.night&&!G.sunOff){ G.sunT-=dt; if(G.sunT<=0){ addSun(GX+rnd(20,700),-20,25,'sky'); G.sun&&0; G.suns[G.suns.length-1].ty=LT+rnd(40,G.rows*G.RH-60); G.sunT=rnd(9,12); } }
  if(G.intro<=0){
    if(G.wave<G.waves){ G.wt-=dt; G.since+=dt; const lowHp=G.wave>0&&G.since>14&&G.pend.length===0&&waveHP()<G.hp0*.3; if(G.wt<=0||lowHp) spawnWave(); }
    for(let i=G.pend.length-1;i>=0;i--){ const e=G.pend[i]; e.t-=dt; if(e.t<=0){ G.pend.splice(i,1); const z=makeZ(e.type,e.row,e.x,e.rise); G.Z.push(z); } }
  }
  updPlants(dt); updZ(dt); updProj(dt); updMisc(dt);
  if(G.lose){ endGame(false); return; }
  if(G.final&&G.wave>=G.waves&&!G.Z.length&&!G.pend.length&&!G.reward) G.reward={x:G.lastDie.x,y:G.lastDie.y,t:0};
  if(G.reward) G.reward.t+=dt;
}
function endGame(win){
  if(G.over) return;
  if(win){ const k=G.L.k; if(SAVE.level<=k) SAVE.level=k+1; let nw=null; const rw=REWARDS[k]; if(rw&&SAVE.unlocked.indexOf(rw)<0){ SAVE.unlocked.push(rw); nw=rw; }
    const w=Math.floor((k+1)/5); if((k+1)%5===0&&INTRO[w]) INTRO[w].forEach(id=>{ if(SAVE.unlocked.indexOf(id)<0){ SAVE.unlocked.push(id); } });
    G.over={win:true,nw}; snd('win'); }
  else { G.over={win:false}; if(G.surv){ const key=G.map.id; SAVE.surv[key]=Math.max(SAVE.surv[key]||0,G.wave); } snd('lose'); }
  save(); stopSynthIfNeeded();
}
function stopSynthIfNeeded(){}
'''
