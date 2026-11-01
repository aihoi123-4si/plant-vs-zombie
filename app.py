import streamlit as st
import base64, os

st.set_page_config(page_title="Plants vs Zombies - Bản Việt Hóa Hoàn Chỉnh", layout="wide")
st.markdown("<h1 style='text-align:center;color:#5fbf3a;margin:0'>🌻 PLANTS vs ZOMBIES - FULL EDITION 🧟</h1>", unsafe_allow_html=True)

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
        if folder in seen or not os.path.isdir(folder): continue
        seen.add(folder)
        for name in sorted(os.listdir(folder)):
            if os.path.splitext(name)[1].lower() in AUDIO_MIME:
                found.append(os.path.join(folder, name))
    return found[0] if found else None

@st.cache_data(show_spinner=False)
def _file_to_uri(path, mtime):
    ext = os.path.splitext(path)[1].lower()
    with open(path, "rb") as f: data = f.read()
    return f"data:{AUDIO_MIME.get(ext, 'audio/mpeg')};base64," + base64.b64encode(data).decode()

music_uri = ""
p = _find_music()
if p and os.path.getsize(p) <= MAX_MB * 1024 * 1024:
    music_uri = _file_to_uri(p, os.path.getmtime(p))

game_code = r"""
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
html,body{margin:0;padding:0;background:#0f1a12;height:100%;overflow:hidden;display:flex;justify-content:center;align-items:center}
#c{border-radius:10px;box-shadow:0 6px 30px rgba(0,0,0,.8);touch-action:none;user-select:none;cursor:pointer}
</style></head>
<body><canvas id="c" width="900" height="600"></canvas>
<script>
const MUSIC_SRC="""" + music_uri + R"""";
const cv=document.getElementById('c'); let ctx=cv.getContext('2d');
const W=900,H=600,GX=140,CW=80,RH=100;
let S='MENU', G=null, isMuted=false;

// ---------- Âm thanh hệ thống ----------
const AC=window.AudioContext||window.webkitAudioContext; let au=null;
function initAudio(){ try{ if(!au&&AC) au=new AC(); if(au&&au.state==='suspended') au.resume(); }catch(e){ au=null; } }
function tone(type,f1,f2,dur,vol){
  initAudio(); if(!au) return; const t=au.currentTime;
  const o=au.createOscillator(), g=au.createGain(); o.type=type; o.frequency.setValueAtTime(f1,t);
  if(f2!==f1) o.frequency.exponentialRampToValueAtTime(Math.max(20,f2),t+dur);
  g.gain.setValueAtTime(vol,t); g.gain.exponentialRampToValueAtTime(.0001,t+dur); o.connect(g); g.connect(au.destination); o.start(t); o.stop(t+dur+.02);
}
const SFX={
  shoot:()=>tone('triangle',520,300,.08,.1), splat:()=>tone('sawtooth',200,90,.09,.1),
  sun:()=>{tone('sine',700,1000,.12,.16);tone('sine',1000,1400,.12,.13);}, plant:()=>tone('sine',320,150,.14,.18),
  boom:()=>{tone('sawtooth',160,30,.5,.3);}, chomp:()=>tone('square',140,70,.12,.15),
  win:()=>[523,659,784,1047].forEach((f,i)=>tone('triangle',f,f,.25,.2)),
  lose:()=>[330,262,220,165].forEach((f,i)=>tone('sawtooth',f,f*.9,.4,.2)),
  mower:()=>tone('sawtooth',80,120,.4,.15)
};
function snd(n){ try{ SFX[n](); }catch(e){} }

const bgm=new Audio(MUSIC_SRC); bgm.loop=true; bgm.volume=.5;
function playBgm(){ if(!isMuted && MUSIC_SRC) bgm.play().catch(()=>{}); }

// ---------- Dữ liệu Cây trồng & Zombie ----------
const PLANTS={
  sunflower:{n:'Hướng Dương',cost:50,hp:300,col:'#ffd93b'},
  peashooter:{n:'Đậu Bắn',cost:100,hp:300,col:'#6cc644'},
  wallnut:{n:'Hạt Óc Chó',cost:50,hp:4000,col:'#c68b3e'},
  snowpea:{n:'Đậu Tuyết',cost:175,hp:300,col:'#8fd3f0'},
  cherrybomb:{n:'Cherry Bomb',cost:150,hp:300,col:'#d62828'}
};
const SEEDS=Object.keys(PLANTS);

class Game {
  constructor(){
    this.sun=200; this.time=0;
    this.grid=Array.from({length:5}, ()=>Array(9).fill(null));
    this.plants=[]; this.zombies=[]; this.projectiles=[]; this.suns=[];
    this.mowers=Array.from({length:5}, (_,r)=>({r, x:GX-35, active:false}));
    this.selCard=null;
    this.spawnTimer=0;
  }
  update(){
    this.time++;
    // Rơi mặt trời tự nhiên
    if(this.time%350===0){
      this.suns.push({x:Math.random()*(W-GX-50)+GX+25, y:-20, targetY:Math.random()*350+120, val:25, life:500});
      snd('sun');
    }
    // Sinh Zombie tự động theo thời gian
    this.spawnTimer++;
    if(this.spawnTimer > 300 && Math.random() < 0.4){
      this.spawnTimer = 0;
      let r = Math.floor(Math.random()*5);
      this.zombies.push({r, x:W+30, y:r*RH+130, hp:200, maxHp:200, sp:1.2, eating:false, fr:0});
    }
    // Cập nhật máy cắt cỏ
    this.mowers.forEach(m=>{
      if(m.active){
        m.x+=7;
        this.zombies.forEach(z=>{
          if(z.r===m.r && Math.abs(z.x-m.x)<30){ z.hp=0; snd('boom'); }
        });
        if(m.x>W+50) m.active=false;
      }
    });
    // Cập nhật đạn đậu
    for(let i=this.projectiles.length-1; i>=0; i--){
      let p=this.projectiles[i]; p.x+=p.vx;
      let hit=false;
      for(let z of this.zombies){
        if(z.r===p.r && Math.abs(z.x-p.x)<25 && z.hp>0){
          hit=true; z.hp-=20; snd('splat');
          if(p.ice) z.sp=0.6;
          break;
        }
      }
      if(hit || p.x>W+50) this.projectiles.splice(i,1);
    }
    // Cập nhật mặt trời trên sân
    for(let i=this.suns.length-1; i>=0; i--){
      let s=this.suns[i];
      if(s.y<s.targetY) s.y+=1.5;
      s.life--; if(s.life<=0) this.suns.splice(i,1);
    }
    // Cập nhật Cây
    this.plants.forEach(pl=>{
      pl.timer=(pl.timer||0)+1;
      if(pl.id==='sunflower' && pl.timer%500===0){
        this.suns.push({x:pl.c*CW+GX+40, y:pl.r*RH+120, targetY:pl.r*RH+150, val:25, life:500});
        snd('sun');
      }
      if((pl.id==='peashooter'||pl.id==='snowpea') && pl.timer%90===0){
        let hasZ=this.zombies.some(z=>z.r===pl.r && z.x>pl.c*CW+GX && z.x<W);
        if(hasZ){
          this.projectiles.push({r:pl.r, x:pl.c*CW+GX+40, y:pl.r*RH+120, vx:6, ice:pl.id==='snowpea'});
          snd('shoot');
        }
      }
      if(pl.id==='cherrybomb' && pl.timer===30){
        this.zombies.forEach(z=>{
          if(Math.abs(z.r-pl.r)<=1 && Math.abs(z.x-(pl.c*CW+GX+40))<120){ z.hp=0; }
        });
        snd('boom');
        this.plants=this.plants.filter(p=>p!==pl);
        this.grid[pl.r][pl.c]=null;
      }
    });
    // Cập nhật Zombie
    for(let i=this.zombies.length-1; i>=0; i--){
      let z=this.zombies[i]; z.fr+=0.1;
      let target=this.plants.find(pl=>pl.r===z.r && Math.abs((pl.c*CW+GX+40)-z.x)<25);
      if(target){
        z.eating=true; target.hp-=2;
        if(target.hp<=0){
          this.grid[target.r][target.c]=null;
          this.plants=this.plants.filter(p=>p!==target);
          z.eating=false;
        }
      } else {
        z.eating=false; z.x-=z.sp*0.3;
      }
      // Zombie chạm biên trái -> kích hoạt máy cắt cỏ hoặc thua
      if(z.x < GX - 10){
        let m=this.mowers.find(item=>item.r===z.r && !item.active);
        if(m){ m.active=true; snd('mower'); }
        else { S='LOSE'; snd('lose'); }
      }
      if(z.hp<=0) this.zombies.splice(i,1);
    }
  }
  draw(){
    // Vẽ nền sân vườn
    for(let r=0; r<5; r++){
      for(let c=0; c<9; c++){
        ctx.fillStyle=(r+c)%2===0 ? '#58a82f' : '#4f9c2a';
        ctx.fillRect(GX+c*CW, r*RH+100, CW, RH);
        ctx.strokeStyle='rgba(0,0,0,0.15)'; ctx.strokeRect(GX+c*CW, r*RH+100, CW, RH);
      }
    }
    // Vẽ máy cắt cỏ
    this.mowers.forEach(m=>{
      ctx.fillStyle='#e82424'; ctx.fillRect(GX-45, m.r*RH+125, 35, 25);
      ctx.fillStyle='#222'; ctx.beginPath(); ctx.arc(GX-35, m.r*RH+150, 7,0,7); ctx.arc(GX-20, m.r*RH+150, 7,0,7); ctx.fill();
    });
    // Vẽ cây
    this.plants.forEach(pl=>{
      let px=pl.c*CW+GX+40, py=pl.r*RH+150;
      ctx.fillStyle=PLANTS[pl.id].col;
      ctx.beginPath(); ctx.arc(px, py-20, 26, 0, 7); ctx.fill();
      ctx.strokeStyle='#222'; ctx.lineWidth=2; ctx.stroke();
      ctx.fillStyle='#fff'; ctx.font='bold 12px Arial'; ctx.textAlign='center';
      ctx.fillText(PLANTS[pl.id].n.substring(0,4), px, py-16);
    });
    // Vẽ Zombie
    this.zombies.forEach(z=>{
      ctx.fillStyle='#7a6a55'; ctx.fillRect(z.x-15, z.y-45, 30, 45); // Thân
      ctx.fillStyle='#a8c496'; ctx.beginPath(); ctx.arc(z.x, z.y-55, 14, 0, 7); ctx.fill(); // Đầu
      ctx.fillStyle='#c0242b'; ctx.fillRect(z.x-15, z.y-20, 30, 6); // Thanh máu nhỏ
      ctx.fillStyle='#4cd137'; ctx.fillRect(z.x-15, z.y-20, 30*(z.hp/z.maxHp), 6);
    });
    // Vẽ đạn đậu
    this.projectiles.forEach(p=>{
      ctx.fillStyle=p.ice?'#8fd3f0':'#6cc644';
      ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, 7); ctx.fill();
    });
    // Vẽ mặt trời
    this.suns.forEach(s=>{
      ctx.fillStyle='#ffd93b'; ctx.beginPath(); ctx.arc(s.x, s.y, 18, 0, 7); ctx.fill();
      ctx.strokeStyle='#e67e22'; ctx.lineWidth=2; ctx.stroke();
      ctx.fillStyle='#d35400'; ctx.font='bold 12px Arial'; ctx.textAlign='center'; ctx.fillText('+25', s.x, s.y+4);
    });
    // Vẽ thanh chọn cây phía trên
    ctx.fillStyle='#3e2723'; ctx.fillRect(0, 0, W, 100);
    ctx.fillStyle='#f1c40f'; ctx.font='bold 18px Arial'; ctx.textAlign='left';
    ctx.fillText('☀️ Mặt trời: '+this.sun, 20, 55);

    SEEDS.forEach((id, idx)=>{
      let sx=180+idx*75, sy=15;
      ctx.fillStyle = this.selCard===id ? '#e74c3c' : '#7f8c8d';
      ctx.fillRect(sx, sy, 68, 72);
      ctx.strokeStyle='#2c3e50'; ctx.lineWidth=2; ctx.strokeRect(sx, sy, 68, 72);
      ctx.fillStyle='#fff'; ctx.font='bold 11px Arial'; ctx.textAlign='center';
      ctx.fillText(PLANTS[id].n, sx+34, sy+30);
      ctx.fillStyle='#f1c40f'; ctx.fillText(PLANTS[id].cost+' ☀️', sx+34, sy+58);
    });
  }
}

// Bắt sự kiện click chuột chơi game
cv.addEventListener('click', e=>{
  let rect=cv.getBoundingClientRect();
  let mx=e.clientX-rect.left, my=e.clientY-rect.top;

  if(S==='MENU'){
    S='PLAY'; G=new Game(); playBgm();
    return;
  }
  if(S==='PLAY'){
    // Click nhặt mặt trời
    for(let i=G.suns.length-1; i>=0; i--){
      let s=G.suns[i];
      if(Math.hypot(mx-s.x, my-s.y)<25){
        G.sun+=s.val; G.suns.splice(i,1); snd('sun');
        return;
      }
    }
    // Click chọn thẻ bài cây
    SEEDS.forEach((id, idx)=>{
      let sx=180+idx*75, sy=15;
      if(mx>=sx && mx<=sx+68 && my>=sy && my<=sy+72){
        if(G.sun>=PLANTS[id].cost){ G.selCard=id; snd('plant'); }
      }
    });
    // Click trồng cây lên lưới ô vuông sân vườn
    if(G.selCard && mx>=GX && mx<GX+9*CW && my>=100 && my<600){
      let c=Math.floor((mx-GX)/CW), r=Math.floor((my-100)/RH);
      if(r>=0 && r<5 && c>=0 && c<9 && !G.grid[r][c]){
        G.sun-=PLANTS[G.selCard].cost;
        G.grid[r][c]={id:G.selCard, hp:PLANTS[G.selCard].hp, r, c};
        G.plants.push(G.grid[r][c]);
        G.selCard=null; snd('plant');
      }
    }
  }
  if(S==='LOSE' || S==='WIN'){ S='MENU'; }
});

function loop(){
  ctx.fillStyle='#0f1a12'; ctx.fillRect(0,0,W,H);
  if(S==='MENU'){
    ctx.fillStyle='#5fbf3a'; ctx.font='bold 34px Arial'; ctx.textAlign='center';
    ctx.fillText('🌻 PLANTS vs ZOMBIES 🧟', W/2, 220);
    ctx.fillStyle='#fff'; ctx.font='bold 20px Arial';
    ctx.fillText('Nhấp chuột vào màn hình để bắt đầu chơi!', W/2, 290);
  } else if(S==='PLAY'){
    G.update(); G.draw();
  } else if(S==='LOSE'){
    ctx.fillStyle='#e74c3c'; ctx.font='bold 40px Arial'; ctx.textAlign='center';
    ctx.fillText('ZOMBIES ĐÃ ĂN NÃO BẠN!', W/2, 260);
    ctx.fillStyle='#fff'; ctx.font='20px Arial';
    ctx.fillText('Nhấp chuột để chơi lại', W/2, 320);
  }
  requestAnimationFrame(loop);
}
loop();
</script></body></html>
"""

st.components.v1.html(game_code, height=620, scrolling=False)
