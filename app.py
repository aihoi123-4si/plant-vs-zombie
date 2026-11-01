import streamlit as st
import base64, os

st.set_page_config(page_title="Plants vs Zombies - Bản Việt Hóa", layout="wide")
st.markdown("<h1 style='text-align:center;color:#5fbf3a;margin:0'>🌻 PLANTS vs ZOMBIES 🧟</h1>", unsafe_allow_html=True)

# ================= NHẠC NỀN =================
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
const MUSIC_SRC="""" + music_uri + R"""";
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

const PLANTS={
  peashooter:{n:'Đậu Bắn',cost:100,cd:7.5,hp:300,k:'shoot',desc:'Bắn đậu vào zombie trên cùng hàng.'},
  sunflower:{n:'Hoa Hướng Dương',cost:50,cd:7.5,hp:300,k:'sun',desc:'Tạo ra thêm mặt trời cho bạn.'},
  cherrybomb:{n:'Cherry Bomb',cost:150,cd:50,hp:300,k:'bomb',desc:'Nổ tung mọi zombie trong vùng 3x3.'},
  wallnut:{n:'Hạt Óc Chó',cost:50,cd:30,hp:4000,k:'wall',desc:'Lớp vỏ cứng giúp chặn đường zombie.'},
  potatomine:{n:'Potato Mine',cost:25,cd:30,hp:300,k:'mine',desc:'Cần thời gian để kích hoạt, rồi nổ tung zombie bước lên.'},
  snowpea:{n:'Đậu Tuyết',cost:175,cd:7.5,hp:300,k:'shoot',desc:'Bắn đậu băng làm zombie chậm lại.'},
  chomper:{n:'Chomper',cost:150,cd:7.5,hp:300,k:'chomp',desc:'Nuốt chửng một zombie, nhưng nhai rất lâu.'},
  repeater:{n:'Repeater',cost:200,cd:7.5,hp:300,k:'shoot',desc:'Bắn hai viên đậu mỗi lượt.'}
};
const MAPS=[
  {id:'DAY',n:'Sân Vườn Ban Ngày',rows:5,night:false,water:[],roof:false,fog:false}
];
function lvInfo(k){ const w=Math.floor(k/5), i=k%5; return {k,w,i,d:k,map:MAPS[w],waves:4+i,name:(w+1)+'-'+(i+1)}; }
function allowedZ(L){ return ['basic','cone']; }
function genWave(L,j,big,surv){
  return ['basic'];
}

// Giao diện điều khiển game loop
class PvZGame {
    constructor(lvNum){
        this.lvNum = lvNum;
        this.info = lvInfo(lvNum);
        this.map = this.info.map;
        this.rows = this.map.rows;
        this.sun = 150;
        this.score = 0;
        this.time = 0;
        this.grid = Array.from({length: this.rows}, ()=>Array(9).fill(null));
        this.plants = [];
        this.zombies = [];
        this.projectiles = [];
        this.suns = [];
        this.mowers = Array.from({length: this.rows}, (_, r)=>({r, x: GX - 40, active: false}));
        this.waves = [];
        this.waveIdx = 0;
        this.spawnTimer = 0;
        this.initWaves();
    }
    initWaves(){
        for(let i=0; i<this.info.waves; i++){
            this.waves.push({zombies: ['basic'], spawned: false});
        }
    }
    update(){
        this.time++;
        if(this.time % 420 === 0){
            this.suns.push({x: rnd(GX, GX + 8 * CW), y: -20, targetY: rnd(150, 500), val: 25, life: 600});
        }
    }
}

// Bắt đầu khởi chạy game
function drawMain(){
    ctx.fillStyle = '#0f1a12'; ctx.fillRect(0,0,W,H);
    T('🌻 PLANTS vs ZOMBIES 🧟', W/2, 200, 32, '#5fbf3a', 'center');
    T('Nhấn để bắt đầu chơi', W/2, 260, 20, '#fff', 'center');
}
function loop(){
    if(G) G.update();
    drawMain();
    requestAnimationFrame(loop);
}
loop();
cv.addEventListener('click', ()=>{
    if(S==='MENU'){ S='PLAY'; G=new PvZGame(0); playMusic(); }
});
</script></body></html>
"""

st.components.v1.html(game_code, height=620, scrolling=False)
