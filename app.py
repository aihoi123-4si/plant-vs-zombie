import streamlit as st
import base64, os

st.set_page_config(page_title="Plants vs Zombies - Bản Việt Hóa Chơi Ngay", layout="wide")
st.markdown("<h1 style='text-align:center;color:#5fbf3a;margin:0'>🌻 PLANTS vs ZOMBIES - PLAYABLE EDITION 🧟</h1>", unsafe_allow_html=True)

# ================= NHẠC NỀN (TÙY CHỌN) =================
AUDIO_MIME = {".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav"}
def _find_music():
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    for name in os.listdir(here):
        if os.path.splitext(name)[1].lower() in AUDIO_MIME:
            return os.path.join(here, name)
    return None

music_uri = ""
p = _find_music()
if p:
    with open(p, "rb") as f:
        music_uri = f"data:audio/mpeg;base64," + base64.b64encode(f.read()).decode()

game_code = r"""
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body{margin:0;padding:0;background:#09110c;display:flex;justify-content:center;align-items:center;height:100vh;overflow:hidden}
#c{border:4px solid #355e3b;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,.9);cursor:pointer;background:#2b5420}
</style></head>
<body>
<canvas id="c" width="900" height="600"></canvas>
<script>
const MUSIC_SRC="""" + music_uri + R"""";
const cv=document.getElementById('c'), ctx=cv.getContext('2d');
const W=900, H=600, GX=130, CW=80, RH=100;
let S='MENU', G=null, isMuted=false;

// ---------- Âm thanh Web Audio API (Không sợ lỗi file) ----------
const AC = window.AudioContext || window.webkitAudioContext; let au = null;
function initAu(){ if(!au && AC) au = new AC(); if(au && au.state==='suspended') au.resume(); }
function playTone(f1, f2, dur, type='sine', vol=0.1){
  initAu(); if(!au) return;
  const t = au.currentTime, o = au.createOscillator(), g = au.createGain();
  o.type = type; o.frequency.setValueAtTime(f1, t);
  if(f2) o.frequency.exponentialRampToValueAtTime(f2, t+dur);
  g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t+dur);
  o.connect(g); g.connect(au.destination); o.start(t); o.stop(t+dur);
}
const SFX = {
  sun: () => { playTone(600, 900, 0.15, 'sine', 0.15); },
  plant: () => { playTone(300, 150, 0.12, 'triangle', 0.2); },
  shoot: () => { playTone(500, 250, 0.08, 'triangle', 0.1); },
  splat: () => { playTone(180, 80, 0.08, 'sawtooth', 0.1); },
  boom: () => { playTone(120, 30, 0.4, 'sawtooth', 0.3); },
  mower: () => { playTone(80, 140, 0.5, 'sawtooth', 0.2); },
  lose: () => { [300, 220, 150].forEach((f,i)=>setTimeout(()=>playTone(f,f*0.8,0.3,'sawtooth',0.2), i*250)); }
};

const PLANTS = {
  sunflower: {n:'Hướng Dương', cost:50, hp:300, col:'#ffd93b'},
  peashooter: {n:'Đậu Bắn', cost:100, hp:300, col:'#6cc644'},
  wallnut: {n:'Hạt Óc Chó', cost:50, hp:4000, col:'#c68b3e'},
  snowpea: {n:'Đậu Tuyết', cost:175, hp:300, col:'#8fd3f0'},
  cherrybomb: {n:'Cherry Bomb', cost:150, hp:300, col:'#d62828'}
};
const SEEDS = Object.keys(PLANTS);

class Game {
  constructor(){
    this.sun = 200;
    this.time = 0;
    this.grid = Array.from({length:5}, ()=>Array(9).fill(null));
    this.plants = [];
    this.zombies = [];
    this.projectiles = [];
    this.suns = [];
    this.mowers = Array.from({length:5}, (_,r)=>({r, x:GX-35, active:false}));
    this.selCard = null;
    this.spawnTimer = 0;
  }
  update(){
    this.time++;
    // Rơi mặt trời tự nhiên
    if(this.time % 300 === 0){
      this.suns.push({x: Math.random()*(W-GX-80)+GX+40, y:-20, targetY: Math.random()*350+120, val:25, life:600});
      SFX.sun();
    }
    // Sinh Zombie tự động
    this.spawnTimer++;
    if(this.spawnTimer > 240){
      this.spawnTimer = 0;
      let r = Math.floor(Math.random()*5);
      this.zombies.push({r, x:W+30, y:r*RH+140, hp:200, maxHp:200, sp:1.1, eating:false});
    }
    // Máy cắt cỏ quét qua
    this.mowers.forEach(m=>{
      if(m.active){
        m.x += 8;
        this.zombies.forEach(z=>{
          if(z.r === m.r && Math.abs(z.x - m.x) < 35){ z.hp = 0; SFX.boom(); }
        });
        if(m.x > W+50) m.active = false;
      }
    });
    // Đạn đậu
    for(let i=this.projectiles.length-1; i>=0; i--){
      let p = this.projectiles[i]; p.x += p.vx;
      let hit = false;
      for(let z of this.zombies){
        if(z.r === p.r && Math.abs(z.x - p.x) < 25 && z.hp > 0){
          hit = true; z.hp -= 25; SFX.splat();
          if(p.ice) z.sp = 0.5;
          break;
        }
      }
      if(hit || p.x > W+50) this.projectiles.splice(i,1);
    }
    // Mặt trời
    for(let i=this.suns.length-1; i>=0; i--){
      let s = this.suns[i];
      if(s.y < s.targetY) s.y += 2;
      s.life--; if(s.life <= 0) this.suns.splice(i,1);
    }
    // Cây trồng hoạt động
    this.plants.forEach(pl=>{
      pl.timer = (pl.timer || 0) + 1;
      if(pl.id === 'sunflower' && pl.timer % 450 === 0){
        this.suns.push({x: pl.c*CW+GX+40, y: pl.r*RH+120, targetY: pl.r*RH+150, val:25, life:500});
        SFX.sun();
      }
      if((pl.id === 'peashooter' || pl.id === 'snowpea') && pl.timer % 80 === 0){
        let hasZ = this.zombies.some(z => z.r === pl.r && z.x > pl.c*CW+GX && z.x < W);
        if(hasZ){
          this.projectiles.push({r: pl.r, x: pl.c*CW+GX+40, y: pl.r*RH+120, vx: 7, ice: pl.id==='snowpea'});
          SFX.shoot();
        }
      }
      if(pl.id === 'cherrybomb' && pl.timer === 25){
        this.zombies.forEach(z=>{
          if(Math.abs(z.r - pl.r) <= 1 && Math.abs(z.x - (pl.c*CW+GX+40)) < 120){ z.hp = 0; }
        });
        SFX.boom();
        this.plants = this.plants.filter(p => p !== pl);
        this.grid[pl.r][pl.c] = null;
      }
    });
    // Zombie di chuyển & ăn cây
    for(let i=this.zombies.length-1; i>=0; i--){
      let z = this.zombies[i];
      let target = this.plants.find(pl => pl.r === z.r && Math.abs((pl.c*CW+GX+40) - z.x) < 25);
      if(target){
        z.eating = true; target.hp -= 2;
        if(target.hp <= 0){
          this.grid[target.r][target.c] = null;
          this.plants = this.plants.filter(p => p !== target);
          z.eating = false;
        }
      } else {
        z.eating = false; z.x -= z.sp * 0.4;
      }
      // Chạm mép trái
      if(z.x < GX - 15){
        let m = this.mowers.find(item => item.r === z.r && !item.active);
        if(m){ m.active = true; SFX.mower(); }
        else { S = 'LOSE'; SFX.lose(); }
      }
      if(z.hp <= 0) this.zombies.splice(i,1);
    }
  }
  draw(){
    // Vẽ sân cỏ
    for(let r=0; r<5; r++){
      for(let c=0; c<9; c++){
        ctx.fillStyle = (r+c)%2 === 0 ? '#58a82f' : '#4f9c2a';
        ctx.fillRect(GX+c*CW, r*RH+100, CW, RH);
        ctx.strokeStyle = 'rgba(0,0,0,0.12)'; ctx.strokeRect(GX+c*CW, r*RH+100, CW, RH);
      }
    }
    // Máy cắt cỏ
    this.mowers.forEach(m=>{
      ctx.fillStyle = '#e82424'; ctx.fillRect(GX-45, m.r*RH+130, 32, 22);
      ctx.fillStyle = '#222'; ctx.beginPath(); ctx.arc(GX-35, m.r*RH+155, 6,0,7); ctx.arc(GX-22, m.r*RH+155, 6,0,7); ctx.fill();
    });
    // Cây trồng
    this.plants.forEach(pl=>{
      let px = pl.c*CW+GX+40, py = pl.r*RH+150;
      ctx.fillStyle = PLANTS[pl.id].col;
      ctx.beginPath(); ctx.arc(px, py-20, 26, 0, 7); ctx.fill();
      ctx.strokeStyle = '#1b3b18'; ctx.lineWidth = 3; ctx.stroke();
      ctx.fillStyle = '#fff'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center';
      ctx.fillText(PLANTS[pl.id].n, px, py-16);
    });
    // Zombie
    this.zombies.forEach(z=>{
      ctx.fillStyle = '#7a6a55'; ctx.fillRect(z.x-14, z.y-45, 28, 45); // Thân
      ctx.fillStyle = '#a8c496'; ctx.beginPath(); ctx.arc(z.x, z.y-55, 13, 0, 7); ctx.fill(); // Đầu
      ctx.fillStyle = '#444'; ctx.fillRect(z.x-15, z.y-22, 30, 5);
      ctx.fillStyle = '#e74c3c'; ctx.fillRect(z.x-15, z.y-22, 30*(z.hp/z.maxHp), 5);
    });
    // Đạn
    this.projectiles.forEach(p=>{
      ctx.fillStyle = p.ice ? '#8fd3f0' : '#6cc644';
      ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, 7); ctx.fill();
    });
    // Mặt trời
    this.suns.forEach(s=>{
      ctx.fillStyle = '#ffd93b'; ctx.beginPath(); ctx.arc(s.x, s.y, 18, 0, 7); ctx.fill();
      ctx.strokeStyle = '#e67e22'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = '#d35400'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center'; ctx.fillText('25$', s.x, s.y+4);
    });
    // Thanh chọn bài phía trên
    ctx.fillStyle = '#3e2723'; ctx.fillRect(0, 0, W, 100);
    ctx.fillStyle = '#ffd700'; ctx.font = 'bold 18px Arial'; ctx.textAlign = 'left';
    ctx.fillText('☀️ ' + this.sun, 20, 58);

    SEEDS.forEach((id, idx)=>{
      let sx = 160 + idx * 75, sy = 14;
      let sel = (this.selCard === id);
      ctx.fillStyle = sel ? '#27ae60' : '#7f8c8d';
      ctx.fillRect(sx, sy, 68, 74);
      ctx.strokeStyle = sel ? '#fff' : '#2c3e50'; ctx.lineWidth = sel ? 3 : 2; ctx.strokeRect(sx, sy, 68, 74);
      ctx.fillStyle = '#fff'; ctx.font = 'bold 10px Arial'; ctx.textAlign = 'center';
      ctx.fillText(PLANTS[id].n, sx+34, sy+28);
      ctx.fillStyle = '#f1c40f'; ctx.fillText(PLANTS[id].cost + ' ☀️', sx+34, sy+56);
    });
  }
}

// Bắt sự kiện nhấp chuột chính xác tuyệt đối
cv.addEventListener('click', e => {
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;

  if(S === 'MENU'){
    S = 'PLAY'; G = new Game();
    return;
  }
  if(S === 'PLAY'){
    // Click nhặt mặt trời
    for(let i = G.suns.length - 1; i >= 0; i--){
      let s = G.suns[i];
      if(Math.hypot(mx - s.x, my - s.y) < 28){
        G.sun += s.val; G.suns.splice(i,1); SFX.sun();
        return;
      }
    }
    // Click chọn thẻ cây
    SEEDS.forEach((id, idx)=>{
      let sx = 160 + idx * 75, sy = 14;
      if(mx >= sx && mx <= sx+68 && my >= sy && my <= sy+74){
        if(G.sun >= PLANTS[id].cost){ G.selCard = id; SFX.plant(); }
      }
    });
    // Click trồng cây lên ô đất
    if(G.selCard && mx >= GX && mx < GX + 9*CW && my >= 100 && my < 600){
      let c = Math.floor((mx - GX)/CW), r = Math.floor((my - 100)/RH);
      if(r >= 0 && r < 5 && c >= 0 && c < 9 && !G.grid[r][c]){
        G.sun -= PLANTS[G.selCard].cost;
        G.grid[r][c] = {id: G.selCard, hp: PLANTS[G.selCard].hp, r, c};
        G.plants.push(G.grid[r][c]);
        G.selCard = null; SFX.plant();
      }
    }
  }
  if(S === 'LOSE'){ S = 'MENU'; }
});

function loop(){
  ctx.fillStyle = '#1e3f20'; ctx.fillRect(0, 0, W, H);
  if(S === 'MENU'){
    ctx.fillStyle = '#5fbf3a'; ctx.font = 'bold 36px Arial'; ctx.textAlign = 'center';
    ctx.fillText('🌻 PLANTS vs ZOMBIES 🧟', W/2, 220);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 20px Arial';
    ctx.fillText('Nhấp chuột vào đây để bắt đầu!', W/2, 290);
  } else if(S === 'PLAY'){
    G.update(); G.draw();
  } else if(S === 'LOSE'){
    ctx.fillStyle = '#e74c3c'; ctx.font = 'bold 40px Arial'; ctx.textAlign = 'center';
    ctx.fillText('ZOMBIES ĐÃ ĂN NÃO BẠN!', W/2, 260);
    ctx.fillStyle = '#fff'; ctx.font = '20px Arial';
    ctx.fillText('Nhấp chuột để chơi lại', W/2, 320);
  }
  requestAnimationFrame(loop);
}
loop();
</script>
</body>
</html>
"""

st.components.v1.html(game_code, height=620, scrolling=False)
