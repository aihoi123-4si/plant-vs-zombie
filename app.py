import streamlit as st
import base64, os

st.set_page_config(page_title="Plants vs Zombies - Classic Remake", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background-color: #050b07; }
    iframe { border-radius: 14px; box-shadow: 0 10px 40px rgba(0,0,0,0.9); }
    </style>
    <h1 style='text-align:center; color:#5fbf3a; font-family:"Arial Black", sans-serif; margin-bottom: 5px;'>
        🌻 PLANTS vs ZOMBIES - CLASSIC REMAKE 🧟
    </h1>
    """, 
    unsafe_allow_html=True
)

AUDIO_MIME = {".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav"}
def _find_music():
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    folders = [here, os.path.join(here, "music"), os.path.join(here, "assets"), os.getcwd()]
    for folder in folders:
        if not os.path.isdir(folder): continue
        for name in sorted(os.listdir(folder)):
            if os.path.splitext(name)[1].lower() in AUDIO_MIME:
                return os.path.join(folder, name)
    return None

music_uri = ""
p = _find_music()
if p and os.path.getsize(p) <= 25 * 1024 * 1024:
    with open(p, "rb") as f:
        music_uri = f"data:audio/mpeg;base64," + base64.b64encode(f.read()).decode()

game_code = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { margin:0; padding:0; background:#040905; display:flex; justify-content:center; align-items:center; height:100vh; overflow:hidden; font-family:'Arial Black', sans-serif; user-select:none; }
  #gameContainer { position:relative; width:960px; height:600px; border:5px solid #284e30; border-radius:16px; box-shadow:0 12px 50px rgba(0,0,0,0.95); background:#112215; overflow:hidden; }
  canvas { display:block; cursor:default; }
</style>
</head>
<body>
<div id="gameContainer">
  <canvas id="c" width="960" height="600"></canvas>
</div>

<script>
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');
const W = 960, H = 600, GX = 140, CW = 80, RH = 100;
const MUSIC_SRC = """" + music_uri + R"""";

// ---------- STORAGE SYSTEM ----------
const store = {
  get(k){ try { return localStorage.getItem(k); } catch(e){ return null; } },
  set(k,v){ try { localStorage.setItem(k,v); } catch(e){} }
};

let SAVE = {
  level: 1,
  unlocked: ['peashooter'],
  sunUp: 0
};
try {
  let s = JSON.parse(store.get('pvz_save_extended') || '{}');
  if(s && s.unlocked) Object.assign(SAVE, s);
} catch(e){}

function saveGameData(){ store.set('pvz_save_extended', JSON.stringify(SAVE)); }

// ---------- AUDIO ENGINE ----------
const AC = window.AudioContext || window.webkitAudioContext;
let au = null;
function initAudio(){
  try {
    if(!au && AC) au = new AC();
    if(au && au.state === 'suspended') au.resume();
  } catch(e){}
}

function tone(type, f1, f2, dur, vol, delay=0){
  initAudio(); if(!au) return;
  const t = au.currentTime + delay;
  const o = au.createOscillator(), g = au.createGain();
  o.type = type; o.frequency.setValueAtTime(f1, t);
  if(f2 && f2 !== f1) o.frequency.exponentialRampToValueAtTime(Math.max(20, f2), t + dur);
  g.gain.setValueAtTime(vol, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g); g.connect(au.destination);
  o.start(t); o.stop(t + dur + 0.02);
}

const SFX = {
  sun: () => { tone('sine', 700, 1000, 0.12, 0.18); tone('sine', 1000, 1400, 0.12, 0.15, 0.06); },
  plant: () => tone('triangle', 320, 150, 0.14, 0.22),
  shoot: () => tone('triangle', 520, 300, 0.08, 0.12),
  splat: () => tone('sawtooth', 200, 90, 0.09, 0.15),
  boom: () => { tone('sawtooth', 160, 30, 0.5, 0.35); tone('square', 90, 30, 0.4, 0.2); },
  chomp: () => tone('square', 140, 70, 0.12, 0.2),
  vault: () => tone('sine', 300, 600, 0.2, 0.25),
  mower: () => tone('sawtooth', 80, 160, 0.5, 0.3),
  win: () => [523, 659, 784, 1047].forEach((f, i) => tone('triangle', f, f, 0.25, 0.2, i * 0.15)),
  lose: () => [330, 262, 220, 165].forEach((f, i) => tone('sawtooth', f, f * 0.9, 0.35, 0.25, i * 0.22)),
  hugeWave: () => tone('sawtooth', 90, 40, 1.2, 0.3)
};

const bgm = new Audio();
if (MUSIC_SRC) { bgm.src = MUSIC_SRC; bgm.loop = true; bgm.volume = 0.4; }
function playBGM(){ try { if(MUSIC_SRC) bgm.play().catch(()=>{}); } catch(e){} }
function stopBGM(){ try { bgm.pause(); bgm.currentTime = 0; } catch(e){} }

// ---------- GAME DATA & REWARDS ----------
const REWARD_UNLOCKS = {
  1: { key: 'sunflower', name: 'Hoa Hướng Dương', desc: 'Tạo thêm mặt trời bổ sung cho trận chiến!' },
  2: { key: 'cherrybomb', name: 'Cherry Bomb', desc: 'Nổ tung tất cả zombie trong phạm vi 3x3!' },
  3: { key: 'wallnut', name: 'Hạt Óc Chó', desc: 'Vỏ phòng thủ cực kỳ cứng cáp giúp chặn đường zombie!' },
  4: { key: 'potatomine', name: 'Mìn Khoai Tây', desc: 'Mất thời gian mọc lên, nổ tung zombie giẫm lên!' },
  5: { key: 'snowpea', name: 'Đậu Tuyết', desc: 'Bắn ra viên đậu băng làm chậm tốc độ di chuyển zombie!' },
  6: { key: 'chomper', name: 'Cây Ăn Thịt', desc: 'Nuốt chửng zombie trong một miếng, nhai rất lâu!' },
  7: { key: 'repeater', name: 'Đậu Kép', desc: 'Bắn 2 viên đậu liên tiếp cực kỳ uy lực!' }
};

const PLANTS = {
  peashooter: { name:'Đậu Bắn', cost:100, cd:7.5, hp:300, desc:'Bắn đậu thẳng vào zombie.' },
  sunflower:  { name:'Hướng Dương', cost:50, cd:7.5, hp:300, desc:'Tạo ra mặt trời rơi.' },
  cherrybomb: { name:'Cherry Bomb', cost:150, cd:35, hp:300, desc:'Nổ lan diện rộng.' },
  wallnut:    { name:'Óc Chó', cost:50, cd:25, hp:4000, desc:'Chặn đường zombie.' },
  potatomine: { name:'Mìn Khoai', cost:25, cd:25, hp:300, desc:'Bẫy nổ dưới đất.' },
  snowpea:    { name:'Đậu Tuyết', cost:175, cd:7.5, hp:300, desc:'Bắn đậu làm chậm.' },
  chomper:    { name:'Ăn Thịt', cost:150, cd:7.5, hp:300, desc:'Nuốt chửng zombie.' },
  repeater:   { name:'Đậu Kép', cost:200, cd:7.5, hp:300, desc:'Bắn 2 viên đậu.' }
};

const ZOM_TYPES = {
  basic:  { name:'Zombie Thường', hp:200, sp:0.85, arm:0 },
  cone:   { name:'Zombie Nón', hp:560, sp:0.8, arm:360 },
  bucket: { name:'Zombie Xô', hp:1300, sp:0.7, arm:1100 },
  pole:   { name:'Zombie Sào', hp:340, sp:1.2, arm:0, vault:true }
};

// ---------- STATE ENGINE ----------
let S = 'MENU'; // MENU, PLAY, REWARD, LOSE, WIN
let G = null;
let rewardModalData = null;

class Game {
  constructor(levelNum){
    this.level = levelNum;
    this.sun = 150 + Math.min(levelNum * 25, 100);
    this.time = 0;
    this.grid = Array.from({length:5}, () => Array(9).fill(null));
    this.plants = [];
    this.zombies = [];
    this.projectiles = [];
    this.suns = [];
    this.particles = [];
    this.mowers = Array.from({length:5}, (_, r) => ({ r, x: GX - 45, active: false }));
    this.selCard = null;
    this.shovel = false;
    this.cooldowns = {};
    SAVE.unlocked.forEach(k => this.cooldowns[k] = 0);
    
    this.wave = 1;
    this.maxWaves = 3 + Math.min(levelNum, 5);
    this.waveTimer = 0;
    this.zombiesSpawnedInWave = 0;
    this.zombiesPerWave = 6 + levelNum * 2;
    this.bannerText = "";
    this.bannerLife = 0;
  }

  showBanner(txt, dur=120){
    this.bannerText = txt;
    this.bannerLife = dur;
  }

  update(){
    this.time++;

    // Decrease cooldowns
    for(let k in this.cooldowns){
      if(this.cooldowns[k] > 0) this.cooldowns[k]--;
    }

    // Natural sun spawn
    if(this.time % 280 === 0){
      this.suns.push({
        x: Math.random() * (W - GX - 120) + GX + 60,
        y: -20,
        targetY: Math.random() * 340 + 130,
        val: 25,
        life: 650
      });
      SFX.sun();
    }

    // Spawn Waves Logic
    this.waveTimer++;
    if(this.waveTimer > 150 && this.zombiesSpawnedInWave < this.zombiesPerWave){
      this.waveTimer = 0;
      this.zombiesSpawnedInWave++;

      let r = Math.floor(Math.random() * 5);
      let pool = ['basic'];
      if(this.level >= 2) pool.push('cone');
      if(this.level >= 3) pool.push('pole');
      if(this.level >= 4) pool.push('bucket');

      let tKey = pool[Math.floor(Math.random() * pool.length)];
      let zData = ZOM_TYPES[tKey];
      
      this.zombies.push({
        r, x: W + 30, y: r * RH + 140,
        hp: zData.hp, maxHp: zData.hp, sp: zData.sp,
        type: tKey, eating: false,
        vault: zData.vault, hasPole: zData.vault, jumping: false, jumpProgress: 0,
        fr: Math.random() * 10
      });

      if(this.zombiesSpawnedInWave === 1 && this.wave === this.maxWaves){
        this.showBanner("A HUGE WAVE OF ZOMBIES IS APPROACHING!", 150);
        SFX.hugeWave();
      }
    } else if(this.zombiesSpawnedInWave >= this.zombiesPerWave && this.zombies.length === 0){
      if(this.wave < this.maxWaves){
        this.wave++;
        this.zombiesSpawnedInWave = 0;
        this.waveTimer = -60;
      } else {
        triggerWin(this.level);
      }
    }

    // Lawn Mowers
    this.mowers.forEach(m => {
      if(m.active){
        m.x += 10;
        this.zombies.forEach(z => {
          if(z.r === m.r && Math.abs(z.x - m.x) < 35){
            z.hp = 0; SFX.boom();
            this.addParticles(z.x, z.y, '#e74c3c', 15);
          }
        });
        if(m.x > W + 50) m.active = false;
      }
    });

    // Projectiles
    for(let i = this.projectiles.length - 1; i >= 0; i--){
      let p = this.projectiles[i];
      p.x += p.vx;
      let hit = false;
      for(let z of this.zombies){
        if(z.r === p.r && Math.abs(z.x - p.x) < 25 && z.hp > 0){
          hit = true; z.hp -= p.dmg; SFX.splat();
          this.addParticles(p.x, p.y, p.ice ? '#8fd3f0' : '#6cc644', 6);
          if(p.ice) z.slowTimer = 180;
          break;
        }
      }
      if(hit || p.x > W + 50) this.projectiles.splice(i, 1);
    }

    // Suns
    for(let i = this.suns.length - 1; i >= 0; i--){
      let s = this.suns[i];
      if(s.y < s.targetY) s.y += 2.5;
      s.life--;
      if(s.life <= 0) this.suns.splice(i, 1);
    }

    // Particles
    for(let i = this.particles.length - 1; i >= 0; i--){
      let pt = this.particles[i];
      pt.x += pt.vx; pt.y += pt.vy; pt.life--;
      if(pt.life <= 0) this.particles.splice(i, 1);
    }

    // Plants Logic
    this.plants.forEach(pl => {
      pl.timer = (pl.timer || 0) + 1;

      if(pl.id === 'sunflower' && pl.timer % 320 === 0){
        this.suns.push({
          x: pl.c * CW + GX + 40, y: pl.r * RH + 120,
          targetY: pl.r * RH + 150, val: 25, life: 500
        });
        SFX.sun();
      }

      if((pl.id === 'peashooter' || pl.id === 'snowpea' || pl.id === 'repeater') && pl.timer % 65 === 0){
        let hasZ = this.zombies.some(z => z.r === pl.r && z.x > pl.c * CW + GX && z.x < W);
        if(hasZ){
          let isIce = (pl.id === 'snowpea');
          this.projectiles.push({ r: pl.r, x: pl.c * CW + GX + 40, y: pl.r * RH + 120, vx: 8.5, dmg: 20, ice: isIce });
          SFX.shoot();
          if(pl.id === 'repeater'){
            setTimeout(() => {
              if(S === 'PLAY' && G) G.projectiles.push({ r: pl.r, x: pl.c * CW + GX + 40, y: pl.r * RH + 120, vx: 8.5, dmg: 20, ice: false });
            }, 120);
          }
        }
      }

      if(pl.id === 'potatomine'){
        if(pl.timer > 280) pl.armed = true;
        if(pl.armed){
          let victim = this.zombies.find(z => z.r === pl.r && Math.abs((pl.c * CW + GX + 40) - z.x) < 30);
          if(victim){
            victim.hp = 0; SFX.boom();
            this.addParticles(pl.c * CW + GX + 40, pl.r * RH + 150, '#8c6239', 30);
            this.removePlant(pl);
          }
        }
      }

      if(pl.id === 'chomper' && !pl.digesting){
        let prey = this.zombies.find(z => z.r === pl.r && (z.x - (pl.c * CW + GX + 40)) > 0 && (z.x - (pl.c * CW + GX + 40)) < 55);
        if(prey){
          prey.hp = 0; pl.digesting = true; pl.digestTimer = 420; SFX.chomp();
        }
      }
      if(pl.digesting){
        pl.digestTimer--;
        if(pl.digestTimer <= 0) pl.digesting = false;
      }

      if(pl.id === 'cherrybomb' && pl.timer === 18){
        this.zombies.forEach(z => {
          if(Math.abs(z.r - pl.r) <= 1 && Math.abs(z.x - (pl.c * CW + GX + 40)) < 140){ z.hp = 0; }
        });
        SFX.boom();
        this.addParticles(pl.c * CW + GX + 40, pl.r * RH + 150, '#e74c3c', 40);
        this.removePlant(pl);
      }
    });

    // Zombie AI & Movement
    for(let i = this.zombies.length - 1; i >= 0; i--){
      let z = this.zombies[i];
      z.fr += 0.15;

      if(z.slowTimer > 0) { z.slowTimer--; z.spMod = 0.55; } else { z.spMod = 1.0; }

      if(z.jumping){
        z.jumpProgress += 0.06;
        z.x -= 3.5;
        if(z.jumpProgress >= 1){ z.jumping = false; }
        continue;
      }

      let target = this.plants.find(pl => pl.r === z.r && Math.abs((pl.c * CW + GX + 40) - z.x) < 25);
      if(target){
        if(z.hasPole && !z.jumping){
          z.jumping = true; z.jumpProgress = 0; z.hasPole = false; SFX.vault();
          continue;
        }
        z.eating = true;
        target.hp -= 3;
        if(target.hp <= 0){
          this.removePlant(target);
          z.eating = false;
        }
      } else {
        z.eating = false;
        z.x -= z.sp * z.spMod * 0.45;
      }

      if(z.x < GX - 15){
        let m = this.mowers.find(item => item.r === z.r && !item.active);
        if(m){ m.active = true; SFX.mower(); }
        else { triggerGameOver(); }
      }

      if(z.hp <= 0) this.zombies.splice(i, 1);
    }
  }

  removePlant(pl){
    this.grid[pl.r][pl.c] = null;
    this.plants = this.plants.filter(p => p !== pl);
  }

  addParticles(x, y, color, count){
    for(let i=0; i<count; i++){
      this.particles.push({
        x, y,
        vx: (Math.random() - 0.5) * 7,
        vy: (Math.random() - 0.5) * 7,
        life: 25,
        color
      });
    }
  }

  draw(){
    // Draw Lawn
    for(let r=0; r<5; r++){
      for(let c=0; c<9; c++){
        ctx.fillStyle = (r+c)%2 === 0 ? '#5ea832' : '#519929';
        ctx.fillRect(GX + c*CW, r*RH + 100, CW, RH);
        ctx.strokeStyle = 'rgba(0,0,0,0.12)'; ctx.lineWidth = 1;
        ctx.strokeRect(GX + c*CW, r*RH + 100, CW, RH);
      }
    }

    // Lawn Mowers
    this.mowers.forEach(m => {
      ctx.fillStyle = '#d92b2b'; ctx.fillRect(GX - 45, m.r * RH + 130, 32, 22);
      ctx.fillStyle = '#111'; ctx.beginPath(); ctx.arc(GX - 35, m.r * RH + 155, 6, 0, 7); ctx.arc(GX - 22, m.r * RH + 155, 6, 0, 7); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.fillRect(GX - 20, m.r * RH + 133, 6, 8);
    });

    // Plants Rendering
    this.plants.forEach(pl => {
      let px = pl.c * CW + GX + 40, py = pl.r * RH + 150;
      ctx.save(); ctx.translate(px, py);
      
      if(pl.id === 'sunflower'){
        ctx.fillStyle = '#2d7a1f'; ctx.fillRect(-3, -16, 6, 20);
        for(let i=0; i<12; i++){
          let ang = i * Math.PI / 6;
          ctx.fillStyle = '#ffd93b'; ctx.beginPath(); ctx.ellipse(Math.cos(ang)*17, Math.sin(ang)*17 - 20, 9, 5, ang, 0, 7); ctx.fill();
        }
        ctx.fillStyle = '#7a4a18'; ctx.beginPath(); ctx.arc(0, -20, 12, 0, 7); ctx.fill();
        ctx.fillStyle = '#fff'; ctx.fillRect(-4, -23, 3, 4); ctx.fillRect(1, -23, 3, 4);
        ctx.fillStyle = '#000'; ctx.fillRect(-3, -22, 1.5, 2); ctx.fillRect(2, -22, 1.5, 2);
      } else if(pl.id === 'peashooter' || pl.id === 'snowpea' || pl.id === 'repeater'){
        ctx.fillStyle = '#2d7a1f'; ctx.fillRect(-3, -16, 6, 20);
        ctx.fillStyle = pl.id==='snowpea'?'#8fd3f0':'#6cc644';
        ctx.beginPath(); ctx.arc(0, -26, 17, 0, 7); ctx.fill();
        ctx.fillRect(5, -31, 15, 11);
        if(pl.id==='repeater'){ ctx.fillRect(5, -19, 15, 9); }
        ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(-3, -30, 5, 0, 7); ctx.fill();
        ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(-2, -30, 2, 0, 7); ctx.fill();
      } else if(pl.id === 'wallnut'){
        ctx.fillStyle = '#c68b3e'; ctx.beginPath(); ctx.ellipse(0, -22, 23, 27, 0, 0, 7); ctx.fill();
        ctx.strokeStyle = '#6e4718'; ctx.lineWidth = 3; ctx.stroke();
        ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(-7, -26, 6, 0, 7); ctx.arc(7, -26, 6, 0, 7); ctx.fill();
        ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(-7, -26, 2, 0, 7); ctx.arc(7, -26, 2, 0, 7); ctx.fill();
      } else if(pl.id === 'potatomine'){
        ctx.fillStyle = '#8c6239';
        if(pl.armed){
          ctx.beginPath(); ctx.arc(0, -12, 14, 0, 7); ctx.fill();
          ctx.fillStyle = '#e74c3c'; ctx.fillRect(-3, -24, 6, 6);
        } else {
          ctx.beginPath(); ctx.ellipse(0, -8, 14, 8, 0, 0, 7); ctx.fill();
        }
      } else if(pl.id === 'chomper'){
        ctx.fillStyle = '#9b59b6'; ctx.beginPath(); ctx.arc(0, -24, 20, 0, 7); ctx.fill();
        ctx.fillStyle = pl.digesting ? '#333' : '#e74c3c'; ctx.fillRect(5, -34, 14, 14);
      } else if(pl.id === 'cherrybomb'){
        ctx.fillStyle = '#d62828'; ctx.beginPath(); ctx.arc(-11, -20, 15, 0, 7); ctx.arc(11, -20, 15, 0, 7); ctx.fill();
        ctx.fillStyle = '#2e7d32'; ctx.fillRect(-2, -40, 4, 12);
      }
      ctx.restore();
    });

    // Zombies Rendering
    this.zombies.forEach(z => {
      ctx.save(); ctx.translate(z.x, z.y);
      if(z.slowTimer > 0) ctx.fillStyle = '#5b8caf'; else ctx.fillStyle = '#4a3b2c';
      ctx.fillRect(-13, -46, 26, 38);
      ctx.fillStyle = '#c0392b'; ctx.fillRect(-3, -40, 6, 22);
      
      ctx.fillStyle = '#a8c496'; ctx.beginPath(); ctx.arc(0, -55, 15, 0, 7); ctx.fill();
      ctx.strokeStyle = '#4f6a42'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(-5, -56, 6.5, 0, 7); ctx.arc(5, -54, 5.5, 0, 7); ctx.fill();
      ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(-4, -56, 2, 0, 7); ctx.arc(6, -54, 2, 0, 7); ctx.fill();

      if(z.hasPole){
        ctx.strokeStyle = '#a0522d'; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(10,-60); ctx.lineTo(25,-20); ctx.stroke();
      }
      if(z.type === 'cone'){
        ctx.fillStyle = '#e87a1e'; ctx.beginPath(); ctx.moveTo(-15,-63); ctx.lineTo(0,-90); ctx.lineTo(15,-63); ctx.closePath(); ctx.fill();
      } else if(z.type === 'bucket'){
        ctx.fillStyle = '#9aa0a6'; ctx.beginPath(); ctx.moveTo(-17,-60); ctx.lineTo(-13,-87); ctx.lineTo(13,-87); ctx.lineTo(17,-60); ctx.closePath(); ctx.fill();
      }
      ctx.fillStyle = '#222'; ctx.fillRect(-16, -80, 32, 5);
      ctx.fillStyle = '#e74c3c'; ctx.fillRect(-16, -80, 32 * (z.hp / z.maxHp), 5);
      ctx.restore();
    });

    // Projectiles
    this.projectiles.forEach(p => {
      ctx.fillStyle = p.ice ? '#8fd3f0' : '#6cc644';
      ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, 7); ctx.fill();
    });

    // Particles
    this.particles.forEach(pt => {
      ctx.fillStyle = pt.color; ctx.fillRect(pt.x, pt.y, 4, 4);
    });

    // Suns
    this.suns.forEach(s => {
      ctx.fillStyle = '#ffd93b'; ctx.beginPath(); ctx.arc(s.x, s.y, 20, 0, 7); ctx.fill();
      ctx.strokeStyle = '#d35400'; ctx.lineWidth = 2.5; ctx.stroke();
      ctx.fillStyle = '#b7410e'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center'; ctx.fillText('25$', s.x, s.y + 4);
    });

    // --- WOOD SEED BAR (TOP UI) ---
    ctx.fillStyle = '#2f1a0e'; ctx.fillRect(0, 0, W, 100);
    ctx.strokeStyle = '#150a04'; ctx.lineWidth = 4; ctx.strokeRect(0, 0, W, 100);

    ctx.fillStyle = '#ffd700'; ctx.font = 'bold 20px "Arial Black", Arial'; ctx.textAlign = 'left';
    ctx.fillText('☀️ ' + this.sun, 18, 48);
    ctx.fillStyle = '#8bc34a'; ctx.font = 'bold 13px Arial';
    ctx.fillText('Màn 1-' + this.level, 18, 76);

    // Seed Cards
    SAVE.unlocked.forEach((id, idx) => {
      let sx = 140 + idx * 72, sy = 12;
      let sel = (this.selCard === id);
      let cdRatio = (this.cooldowns[id] || 0) / (PLANTS[id].cd * 60);

      ctx.fillStyle = sel ? '#27ae60' : (cdRatio > 0 ? '#332115' : '#4d301b');
      ctx.fillRect(sx, sy, 66, 76);
      ctx.strokeStyle = sel ? '#fff' : '#150a04'; ctx.lineWidth = sel ? 3 : 2; ctx.strokeRect(sx, sy, 66, 76);
      
      ctx.fillStyle = '#fff'; ctx.font = 'bold 10px Arial'; ctx.textAlign = 'center';
      ctx.fillText(PLANTS[id].name, sx + 33, sy + 30);
      ctx.fillStyle = '#f1c40f'; ctx.fillText(PLANTS[id].cost + ' ☀️', sx + 33, sy + 58);

      if(cdRatio > 0){
        ctx.fillStyle = 'rgba(0,0,0,0.6)';
        ctx.fillRect(sx, sy, 66, 76 * cdRatio);
      }
    });

    // Shovel Button
    let shx = 740, shy = 12;
    ctx.fillStyle = this.shovel ? '#e74c3c' : '#7f8c8d';
    ctx.fillRect(shx, shy, 58, 76);
    ctx.strokeStyle = '#150a04'; ctx.lineWidth = 2; ctx.strokeRect(shx, shy, 58, 76);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 13px Arial'; ctx.textAlign = 'center';
    ctx.fillText('⛏️ Xẻng', shx + 29, shy + 42);

    // Wave Progress Bar
    ctx.fillStyle = '#100602'; ctx.fillRect(815, 36, 130, 24);
    ctx.strokeStyle = '#4d301b'; ctx.lineWidth = 2; ctx.strokeRect(815, 36, 130, 24);
    ctx.fillStyle = '#5fbf3a'; ctx.fillRect(817, 38, 126 * (this.wave / this.maxWaves), 20);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center';
    ctx.fillText(`WAVE ${this.wave}/${this.maxWaves}`, 880, 52);

    // Banner Text
    if(this.bannerLife > 0){
      this.bannerLife--;
      ctx.fillStyle = 'rgba(0,0,0,0.75)'; ctx.fillRect(150, 250, 660, 70);
      ctx.fillStyle = '#ff1744'; ctx.font = 'bold 24px "Arial Black", Arial'; ctx.textAlign = 'center';
      ctx.fillText(this.bannerText, W/2, 293);
    }
  }
}

function triggerGameOver(){
  S = 'LOSE'; stopBGM(); SFX.lose();
}

function triggerWin(lvl){
  stopBGM(); SFX.win();
  let reward = REWARD_UNLOCKS[lvl];
  if(reward && !SAVE.unlocked.includes(reward.key)){
    SAVE.unlocked.push(reward.key);
    rewardModalData = reward;
  } else {
    rewardModalData = null;
  }
  SAVE.level = lvl + 1;
  saveGameData();
  S = 'REWARD';
}

// ---------- INTERACTION HANDLER ----------
cv.addEventListener('click', e => {
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;

  if(S === 'MENU'){
    S = 'PLAY'; G = new Game(SAVE.level); playBGM();
    return;
  }

  if(S === 'REWARD'){
    S = 'PLAY'; G = new Game(SAVE.level); playBGM();
    return;
  }

  if(S === 'PLAY' && G){
    // Collect Suns
    for(let i = G.suns.length - 1; i >= 0; i--){
      let s = G.suns[i];
      if(Math.hypot(mx - s.x, my - s.y) < 32){
        G.sun += s.val; G.suns.splice(i, 1); SFX.sun();
        return;
      }
    }

    // Select Seed Card
    SAVE.unlocked.forEach((id, idx) => {
      let sx = 140 + idx * 72, sy = 12;
      if(mx >= sx && mx <= sx + 66 && my >= sy && my <= sy + 76){
        if(G.sun >= PLANTS[id].cost && (G.cooldowns[id] || 0) <= 0){
          G.selCard = id; G.shovel = false; SFX.plant();
        }
      }
    });

    // Select Shovel
    if(mx >= 740 && mx <= 798 && my >= 12 && my <= 88){
      G.shovel = !G.shovel; G.selCard = null; SFX.plant();
    }

    // Grid Placement / Shovel Action
    if(mx >= GX && mx < GX + 9 * CW && my >= 100 && my < 600){
      let c = Math.floor((mx - GX) / CW), r = Math.floor((my - 100) / RH);
      if(r >= 0 && r < 5 && c >= 0 && c < 9){
        if(G.shovel){
          if(G.grid[r][c]){
            G.removePlant(G.grid[r][c]);
            G.shovel = false; SFX.plant();
          }
        } else if(G.selCard && !G.grid[r][c]){
          G.sun -= PLANTS[G.selCard].cost;
          G.cooldowns[G.selCard] = PLANTS[G.selCard].cd * 60;
          G.grid[r][c] = { id: G.selCard, hp: PLANTS[G.selCard].hp, r, c };
          G.plants.push(G.grid[r][c]);
          G.selCard = null; SFX.plant();
        }
      }
    }
  }

  if(S === 'LOSE'){ S = 'MENU'; }
});

// ---------- MAIN GAME LOOP ----------
function loop(){
  ctx.fillStyle = '#0f1f12'; ctx.fillRect(0, 0, W, H);

  if(S === 'MENU'){
    let g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, '#3498db'); g.addColorStop(0.5, '#2ecc71'); g.addColorStop(1, '#8e44ad');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);

    ctx.fillStyle = '#76ba1b'; ctx.font = 'bold 50px "Arial Black", Arial'; ctx.textAlign = 'center';
    ctx.shadowColor = '#000'; ctx.shadowBlur = 12;
    ctx.fillText('PLANTS vs ZOMBIES', W/2, 160);
    ctx.shadowBlur = 0;

    ctx.fillStyle = '#fff'; ctx.font = 'bold 22px Arial';
    ctx.fillText('Màn hiện tại: 1-' + SAVE.level, W/2, 210);

    ctx.fillStyle = '#e67e22'; ctx.fillRect(W/2 - 170, 300, 340, 65);
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 4; ctx.strokeRect(W/2 - 170, 300, 340, 65);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 26px "Arial Black", Arial';
    ctx.fillText('BẮT ĐẦU CHƠI', W/2, 343);
  } else if(S === 'PLAY' && G){
    G.update(); G.draw();
  } else if(S === 'REWARD'){
    ctx.fillStyle = '#111'; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#f1c40f'; ctx.font = 'bold 36px "Arial Black"'; ctx.textAlign = 'center';
    ctx.fillText('🎉 MÀN CHƠI HOÀN THÀNH!', W/2, 160);

    if(rewardModalData){
      ctx.fillStyle = '#27ae60'; ctx.fillRect(W/2 - 180, 210, 360, 200);
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.strokeRect(W/2 - 180, 210, 360, 200);
      
      ctx.fillStyle = '#fff'; ctx.font = 'bold 22px Arial';
      ctx.fillText('MỞ KHÓA CÂY MỚI!', W/2, 250);
      ctx.fillStyle = '#ffd700'; ctx.font = 'bold 26px Arial';
      ctx.fillText(rewardModalData.name, W/2, 295);
      ctx.fillStyle = '#eee'; ctx.font = '15px Arial';
      ctx.fillText(rewardModalData.desc, W/2, 340);
    }

    ctx.fillStyle = '#e67e22'; ctx.fillRect(W/2 - 140, 440, 280, 55);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 20px Arial';
    ctx.fillText('MÀN TIẾP THEO ▶', W/2, 475);
  } else if(S === 'LOSE'){
    ctx.fillStyle = '#111'; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#e74c3c'; ctx.font = 'bold 44px "Arial Black"'; ctx.textAlign = 'center';
    ctx.fillText('ZOMBIES ĐÃ ĂN NÃO BẠN!', W/2, 250);
    ctx.fillStyle = '#fff'; ctx.font = '20px Arial';
    ctx.fillText('Click để thử lại', W/2, 320);
  }

  requestAnimationFrame(loop);
}

loop();
</script>
</body>
</html>
"""

st.components.v1.html(game_code, height=620, scrolling=False)
