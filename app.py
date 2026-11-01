import streamlit as st
import base64, os

st.set_page_config(page_title="Plants vs Zombies - HD Deluxe Edition", layout="wide")
st.markdown("<h1 style='text-align:center;color:#5fbf3a;margin:0'>🌻 PLANTS vs ZOMBIES - HD DELUXE REMAKE 🧟</h1>", unsafe_allow_html=True)

game_code = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    margin: 0; padding: 0;
    background: #030805;
    display: flex; justify-content: center; align-items: center;
    height: 100vh; overflow: hidden;
    font-family: 'Arial Black', Arial, sans-serif;
    user-select: none;
  }
  #gameBox {
    position: relative;
    border: 6px solid #1a3320;
    border-radius: 16px;
    box-shadow: 0 15px 60px rgba(0,0,0,0.95);
    background: #0d1a10;
    overflow: hidden;
  }
  canvas { display: block; cursor: pointer; }
</style>
</head>
<body>
<div id="gameBox">
  <canvas id="c" width="960" height="600"></canvas>
</div>

<script>
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');
const W = 960, H = 600, GX = 140, CW = 80, RH = 100;

// ---------- LƯU TRỮ TIẾN TRÌNH (LOCALSTORAGE) ----------
const store = {
  get(k) { try { return localStorage.getItem(k); } catch(e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch(e) {} }
};

let SAVE = { level: 1, unlocked: ['peashooter'] };
try {
  let loaded = JSON.parse(store.get('pvz_hd_save'));
  if (loaded) SAVE = Object.assign(SAVE, loaded);
} catch(e) {}

function saveGame() {
  store.set('pvz_hd_save', JSON.stringify(SAVE));
}

let S = 'MENU', G = null, UNLOCK_REWARD = null;

// ---------- ÂM THANH WEB AUDIO API ----------
const AC = window.AudioContext || window.webkitAudioContext;
let au = null;
function playTone(f1, f2, dur, type='sine', vol=0.12) {
  try {
    if (!au && AC) au = new AC();
    if (au && au.state === 'suspended') au.resume();
    if (!au) return;
    const t = au.currentTime;
    const o = au.createOscillator(), g = au.createGain();
    o.type = type; o.frequency.setValueAtTime(f1, t);
    if (f2) o.frequency.exponentialRampToValueAtTime(Math.max(20, f2), t + dur);
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g); g.connect(au.destination);
    o.start(t); o.stop(t + dur);
  } catch(e) {}
}

const SFX = {
  sun: () => { playTone(650, 950, 0.12, 'sine', 0.15); playTone(950, 1300, 0.1, 'sine', 0.12); },
  plant: () => playTone(320, 160, 0.1, 'triangle', 0.2),
  shoot: () => playTone(520, 260, 0.08, 'triangle', 0.1),
  splat: () => playTone(190, 80, 0.08, 'sawtooth', 0.1),
  boom: () => playTone(110, 20, 0.45, 'sawtooth', 0.3),
  chomp: () => playTone(150, 70, 0.15, 'square', 0.2),
  vault: () => playTone(300, 600, 0.2, 'sine', 0.2),
  mower: () => playTone(80, 160, 0.5, 'sawtooth', 0.25),
  lose: () => [300, 220, 150, 100].forEach((f,i)=>setTimeout(()=>playTone(f,f*0.8,0.3,'sawtooth',0.25), i*200)),
  win: () => [400, 500, 600, 800].forEach((f,i)=>setTimeout(()=>playTone(f,f*1.1,0.2,'triangle',0.2), i*150))
};

// ---------- DANH MỤC CÂY TRỒNG ----------
const PLANTS = {
  peashooter: {n:'Đậu Bắn', cost:100, hp:300, cd:140, col:'#6cc644', desc:'Bắn đạn đậu tiêu diệt Zombie'},
  sunflower: {n:'Hướng Dương', cost:50, hp:300, cd:140, col:'#ffd93b', desc:'Sản sinh thêm mặt trời'},
  wallnut: {n:'Óc Chó', cost:50, hp:4000, cd:380, col:'#c68b3e', desc:'Lá chắn chịu đựng nhiều sát thương'},
  cherrybomb: {n:'Cherry Bomb', cost:150, hp:300, cd:550, col:'#d62828', desc:'Nổ tung khu vực 3x3'},
  potatomine: {n:'Mìn Khoai', cost:25, hp:300, cd:320, col:'#8c6239', desc:'Cần thời gian mọc, nổ khi dẫm lên'},
  snowpea: {n:'Đậu Tuyết', cost:175, hp:300, cd:180, col:'#8fd3f0', desc:'Bắn đậu băng làm chậm tốc độ Zombie'},
  chomper: {n:'Ăn Thịt', cost:150, hp:300, cd:240, col:'#9b59b6', desc:'Nuốt chửng 1 Zombie lập tức'},
  repeater: {n:'Đậu Kép', cost:200, hp:300, cd:180, col:'#4aae30', desc:'Bắn 2 viên đậu liên tiếp'}
};

const UNLOCK_ORDER = ['peashooter', 'sunflower', 'wallnut', 'cherrybomb', 'potatomine', 'snowpea', 'chomper', 'repeater'];

const ZOM_TYPES = {
  basic: {name:'Zombie Thường', hp:200, sp:0.85, col:'#7a6a55'},
  cone: {name:'Zombie Nón', hp:450, sp:0.75, col:'#e87a1e'},
  bucket: {name:'Zombie Xô', hp:1000, sp:0.65, col:'#9aa0a6'},
  pole: {name:'Zombie Sào', hp:300, sp:1.2, col:'#a0522d', vault:true}
};

class Game {
  constructor(level) {
    this.level = level;
    this.sun = 150 + Math.min(level * 25, 100);
    this.time = 0;
    this.grid = Array.from({length:5}, () => Array(9).fill(null));
    this.plants = [];
    this.zombies = [];
    this.projectiles = [];
    this.suns = [];
    this.particles = [];
    this.mowers = Array.from({length:5}, (_,r) => ({r, x:GX-45, active:false}));
    this.cooldowns = {};
    SAVE.unlocked.forEach(k => this.cooldowns[k] = 0);
    this.selCard = null;
    this.shovel = false;
    this.spawnTimer = 0;
    this.wave = 1;
    this.maxWaves = 3 + Math.floor(level / 2);
    this.zSpawned = 0;
    this.zPerWave = 6 + level * 2;
    this.waveBannerTimer = 0;
  }

  update() {
    this.time++;
    if (this.waveBannerTimer > 0) this.waveBannerTimer--;

    for (let k in this.cooldowns) {
      if (this.cooldowns[k] > 0) this.cooldowns[k]--;
    }

    if (this.time % 250 === 0) {
      this.suns.push({
        x: Math.random() * (W - GX - 100) + GX + 50,
        y: -20, targetY: Math.random() * 350 + 120,
        val: 25, life: 550
      });
      SFX.sun();
    }

    this.spawnTimer++;
    if (this.spawnTimer > 150 && this.zSpawned < this.zPerWave) {
      this.spawnTimer = 0;
      this.zSpawned++;
      let r = Math.floor(Math.random() * 5);
      let tKey = 'basic';
      if (this.level >= 2 && Math.random() < 0.35) tKey = 'cone';
      if (this.level >= 3 && Math.random() < 0.25) tKey = 'bucket';
      if (this.level >= 2 && Math.random() < 0.3) tKey = 'pole';
      let zData = ZOM_TYPES[tKey];
      this.zombies.push({
        r, x: W + 30, y: r * RH + 140,
        hp: zData.hp, maxHp: zData.hp, sp: zData.sp,
        type: tKey, eating: false,
        hasPole: zData.vault, jumping: false, jumpProgress: 0
      });
    } else if (this.zSpawned >= this.zPerWave && this.zombies.length === 0) {
      this.wave++;
      this.zSpawned = 0;
      if (this.wave > this.maxWaves) {
        let nextIdx = SAVE.unlocked.length;
        if (nextIdx < UNLOCK_ORDER.length) {
          let newPlant = UNLOCK_ORDER[nextIdx];
          if (!SAVE.unlocked.includes(newPlant)) {
            SAVE.unlocked.push(newPlant);
            UNLOCK_REWARD = newPlant;
          }
        }
        SAVE.level++;
        saveGame();
        S = 'WIN'; SFX.win();
      } else {
        this.waveBannerTimer = 120;
      }
    }

    this.mowers.forEach(m => {
      if (m.active) {
        m.x += 10;
        this.zombies.forEach(z => {
          if (z.r === m.r && Math.abs(z.x - m.x) < 35) {
            z.hp = 0; SFX.boom(); this.addParticles(z.x, z.y, '#e74c3c', 12);
          }
        });
        if (m.x > W + 50) m.active = false;
      }
    });

    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      let p = this.projectiles[i]; p.x += p.vx;
      let hit = false;
      for (let z of this.zombies) {
        if (z.r === p.r && Math.abs(z.x - p.x) < 25 && z.hp > 0) {
          hit = true; z.hp -= p.dmg; SFX.splat();
          this.addParticles(p.x, p.y, p.ice ? '#8fd3f0' : '#6cc644', 5);
          if (p.ice) z.sp *= 0.7;
          break;
        }
      }
      if (hit || p.x > W + 50) this.projectiles.splice(i, 1);
    }

    for (let i = this.suns.length - 1; i >= 0; i--) {
      let s = this.suns[i];
      if (s.y < s.targetY) s.y += 2.5;
      s.life--; if (s.life <= 0) this.suns.splice(i, 1);
    }
    for (let i = this.particles.length - 1; i >= 0; i--) {
      let pt = this.particles[i]; pt.x += pt.vx; pt.y += pt.vy; pt.life--;
      if (pt.life <= 0) this.particles.splice(i, 1);
    }

    this.plants.forEach(pl => {
      pl.timer = (pl.timer || 0) + 1;
      if (pl.id === 'sunflower' && pl.timer % 340 === 0) {
        this.suns.push({
          x: pl.c * CW + GX + 40, y: pl.r * RH + 120,
          targetY: pl.r * RH + 150, val: 25, life: 480
        });
        SFX.sun();
      }
      if ((pl.id === 'peashooter' || pl.id === 'snowpea' || pl.id === 'repeater') && pl.timer % 65 === 0) {
        let hasZ = this.zombies.some(z => z.r === pl.r && z.x > pl.c * CW + GX && z.x < W);
        if (hasZ) {
          let isIce = (pl.id === 'snowpea');
          this.projectiles.push({ r: pl.r, x: pl.c * CW + GX + 40, y: pl.r * RH + 120, vx: 8.5, dmg: 20, ice: isIce });
          SFX.shoot();
          if (pl.id === 'repeater') {
            setTimeout(() => {
              if (S === 'PLAY') this.projectiles.push({ r: pl.r, x: pl.c * CW + GX + 40, y: pl.r * RH + 120, vx: 8.5, dmg: 20, ice: false });
            }, 120);
          }
        }
      }
      if (pl.id === 'potatomine') {
        if (pl.timer > 280) pl.armed = true;
        if (pl.armed) {
          let victim = this.zombies.find(z => z.r === pl.r && Math.abs((pl.c * CW + GX + 40) - z.x) < 30);
          if (victim) {
            victim.hp = 0; SFX.boom();
            this.addParticles(pl.c * CW + GX + 40, pl.r * RH + 150, '#8c6239', 25);
            this.plants = this.plants.filter(p => p !== pl);
            this.grid[pl.r][pl.c] = null;
          }
        }
      }
      if (pl.id === 'chomper' && !pl.digesting) {
        let prey = this.zombies.find(z => z.r === pl.r && (z.x - (pl.c * CW + GX + 40)) > 0 && (z.x - (pl.c * CW + GX + 40)) < 55);
        if (prey) {
          prey.hp = 0; pl.digesting = true; pl.digestTimer = 380; SFX.chomp();
        }
      }
      if (pl.digesting) {
        pl.digestTimer--;
        if (pl.digestTimer <= 0) pl.digesting = false;
      }
      if (pl.id === 'cherrybomb' && pl.timer === 18) {
        this.zombies.forEach(z => {
          if (Math.abs(z.r - pl.r) <= 1 && Math.abs(z.x - (pl.c * CW + GX + 40)) < 140) z.hp = 0;
        });
        SFX.boom();
        this.addParticles(pl.c * CW + GX + 40, pl.r * RH + 150, '#e74c3c', 35);
        this.plants = this.plants.filter(p => p !== pl);
        this.grid[pl.r][pl.c] = null;
      }
    });

    for (let i = this.zombies.length - 1; i >= 0; i--) {
      let z = this.zombies[i];
      if (z.jumping) {
        z.jumpProgress += 0.05; z.x -= 3;
        if (z.jumpProgress >= 1) z.jumping = false;
        continue;
      }

      let target = this.plants.find(pl => pl.r === z.r && Math.abs((pl.c * CW + GX + 40) - z.x) < 25);
      if (target) {
        if (z.hasPole && !z.jumping) {
          z.jumping = true; z.jumpProgress = 0; z.hasPole = false; SFX.vault();
          continue;
        }
        z.eating = true; target.hp -= 2.5;
        if (target.hp <= 0) {
          this.grid[target.r][target.c] = null;
          this.plants = this.plants.plants = this.plants.filter(p => p !== target);
          z.eating = false;
        }
      } else {
        z.eating = false; z.x -= z.sp * 0.45;
      }

      if (z.x < GX - 15) {
        let m = this.mowers.find(item => item.r === z.r && !item.active);
        if (m) { m.active = true; SFX.mower(); }
        else { S = 'LOSE'; SFX.lose(); }
      }
      if (z.hp <= 0) this.zombies.splice(i, 1);
    }
  }

  addParticles(x, y, color, count) {
    for (let i = 0; i < count; i++) {
      this.particles.push({ x, y, vx: (Math.random() - .5) * 6, vy: (Math.random() - .5) * 6, life: 25, color });
    }
  }

  draw() {
    // --- VẼ ĐỒ HỌA MAP SÂN VƯỜN CAO CẤP (HD) ---
    // Nền trời & mây phía trên
    let skyGrad = ctx.createLinearGradient(0, 0, 0, 100);
    skyGrad.addColorStop(0, '#2980b9'); skyGrad.addColorStop(1, '#6dd5ed');
    ctx.fillStyle = skyGrad; ctx.fillRect(0, 0, W, 100);

    // Mây trôi trang trí
    ctx.fillStyle = 'rgba(255,255,255,0.6)';
    ctx.beginPath(); ctx.arc(200, 40, 20, 0, 7); ctx.arc(220, 35, 25, 0, 7); ctx.arc(240, 42, 18, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.arc(700, 50, 22, 0, 7); ctx.arc(725, 42, 28, 0, 7); ctx.arc(750, 50, 20, 0, 7); ctx.fill();

    // Các ô đất sân vườn (Đan xen màu sắc chân thực)
    for (let r = 0; r < 5; r++) {
      for (let c = 0; c < 9; c++) {
        ctx.fillStyle = (r + c) % 2 === 0 ? '#4e9828' : '#458a24';
        ctx.fillRect(GX + c * CW, r * RH + 100, CW, RH);
        // Viền ô đất nhẹ nhàng
        ctx.strokeStyle = 'rgba(0,0,0,0.18)'; ctx.lineWidth = 1.5;
        ctx.strokeRect(GX + c * CW, r * RH + 100, CW, RH);
      }
    }

    // Hàng rào phía bên phải sân vườn
    ctx.fillStyle = '#dcdde1';
    for(let r=0; r<5; r++) {
      let hx = GX + 9 * CW - 5;
      ctx.fillRect(hx, r * RH + 105, 8, 90);
      ctx.fillStyle = '#718093'; ctx.fillRect(hx - 2, r * RH + 130, 12, 6); ctx.fillRect(hx - 2, r * RH + 170, 12, 6);
      ctx.fillStyle = '#dcdde1';
    }

    // Máy cắt cỏ siêu nét bên trái
    this.mowers.forEach(m => {
      ctx.fillStyle = '#e74c3c'; ctx.fillRect(GX - 46, m.r * RH + 130, 34, 22);
      ctx.fillStyle = '#c0392b'; ctx.fillRect(GX - 46, m.r * RH + 148, 34, 6);
      ctx.fillStyle = '#2f3640'; ctx.beginPath(); ctx.arc(GX - 36, m.r * RH + 155, 7, 0, 7); ctx.arc(GX - 22, m.r * RH + 155, 7, 0, 7); ctx.fill();
      ctx.fillStyle = '#f5f6fa'; ctx.fillRect(GX - 22, m.r * RH + 133, 6, 8);
    });

    // --- VẼ CÂY TRỒNG HD CHI TIẾT ---
    this.plants.forEach(pl => {
      let px = pl.c * CW + GX + 40, py = pl.r * RH + 150;
      ctx.save(); ctx.translate(px, py);
      if (pl.id === 'sunflower') {
        ctx.fillStyle = '#27ae60'; ctx.fillRect(-3, -16, 6, 20);
        for (let i = 0; i < 12; i++) {
          let ang = i * Math.PI / 6;
          ctx.fillStyle = '#f1c40f'; ctx.beginPath(); ctx.ellipse(Math.cos(ang) * 17, Math.sin(ang) * 17 - 20, 9, 5, ang, 0, 7); ctx.fill();
          ctx.strokeStyle = '#d35400'; ctx.lineWidth = 1; ctx.stroke();
        }
        ctx.fillStyle = '#784212'; ctx.beginPath(); ctx.arc(0, -20, 12, 0, 7); ctx.fill();
        ctx.fillStyle = '#fff'; ctx.fillRect(-4, -23, 3, 4); ctx.fillRect(1, -23, 3, 4);
        ctx.fillStyle = '#000'; ctx.fillRect(-3, -22, 1.5, 2); ctx.fillRect(2, -22, 1.5, 2);
      } else if (pl.id === 'peashooter' || pl.id === 'snowpea' || pl.id === 'repeater') {
        ctx.fillStyle = '#27ae60'; ctx.fillRect(-3, -16, 6, 20);
        ctx.fillStyle = pl.id === 'snowpea' ? '#00d2d3' : '#2ecc71';
        ctx.beginPath(); ctx.arc(0, -26, 17, 0, 7); ctx.fill();
        ctx.strokeStyle = '#1e8449'; ctx.lineWidth = 2; ctx.stroke();
        ctx.fillStyle = pl.id === 'snowpea' ? '#01a3a4' : '#27ae60';
        ctx.fillRect(5, -32, 16, 12); ctx.strokeRect(5, -32, 16, 12);
        if (pl.id === 'repeater') { ctx.fillRect(5, -18, 16, 10); ctx.strokeRect(5, -18, 16, 10); }
        ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(-3, -30, 5, 0, 7); ctx.fill();
        ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(-2, -30, 2, 0, 7); ctx.fill();
      } else if (pl.id === 'wallnut') {
        ctx.fillStyle = '#d35400'; ctx.beginPath(); ctx.ellipse(0, -22, 23, 27, 0, 0, 7); ctx.fill();
        ctx.strokeStyle = '#7e5109'; ctx.lineWidth = 3; ctx.stroke();
        ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(-7, -26, 6, 0, 7); ctx.arc(7, -26, 6, 0, 7); ctx.fill();
        ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(-7, -26, 2, 0, 7); ctx.arc(7, -26, 2, 0, 7); ctx.fill();
        ctx.strokeStyle = '#7e5109'; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(0, -12, 8, 0, Math.PI); ctx.stroke();
      } else if (pl.id === 'potatomine') {
        ctx.fillStyle = '#a0522d';
        if (pl.armed) { ctx.beginPath(); ctx.arc(0, -12, 15, 0, 7); ctx.fill(); ctx.fillStyle = '#e74c3c'; ctx.fillRect(-3, -26, 6, 8); }
        else { ctx.beginPath(); ctx.ellipse(0, -8, 15, 9, 0, 0, 7); ctx.fill(); }
      } else if (pl.id === 'chomper') {
        ctx.fillStyle = '#8e44ad'; ctx.beginPath(); ctx.arc(0, -24, 20, 0, 7); ctx.fill();
        ctx.fillStyle = pl.digesting ? '#2c3e50' : '#e74c3c'; ctx.fillRect(6, -35, 15, 15);
      } else if (pl.id === 'cherrybomb') {
        ctx.fillStyle = '#c0392b'; ctx.beginPath(); ctx.arc(-11, -20, 15, 0, 7); ctx.arc(11, -20, 15, 0, 7); ctx.fill();
        ctx.fillStyle = '#27ae60'; ctx.fillRect(-2, -41, 4, 12);
      }
      ctx.restore();
    });

    // --- VẼ ZOMBIE HD CHI TIẾT (ÁO VEST, CÀ VẠT ĐỎ, TÓC THƯA, MẮT LỒI) ---
    this.zombies.forEach(z => {
      ctx.save(); ctx.translate(z.x, z.y);
      // Thân & Áo khoác
      ctx.fillStyle = '#4a3b2c'; ctx.fillRect(-13, -46, 26, 38);
      ctx.fillStyle = '#c0392b'; ctx.fillRect(-3, -40, 6, 22); // Cà vạt đỏ
      // Chân
      ctx.fillStyle = '#2c3e50'; ctx.fillRect(-10, -8, 8, 12); ctx.fillRect(2, -8, 8, 12);
      // Đầu Zombie xanh đặc trưng
      ctx.fillStyle = '#a8c496'; ctx.beginPath(); ctx.arc(0, -55, 15, 0, 7); ctx.fill();
      ctx.strokeStyle = '#4f6a42'; ctx.lineWidth = 2; ctx.stroke();
      // Tóc thưa lơ thơ
      ctx.strokeStyle = '#111'; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(-6, -68); ctx.lineTo(-10, -75); ctx.moveTo(2, -69); ctx.lineTo(6, -76); ctx.stroke();
      // Mắt lồi trắng to
      ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(-5, -56, 6.5, 0, 7); ctx.arc(5, -54, 5.5, 0, 7); ctx.fill();
      ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(-4, -56, 2, 0, 7); ctx.arc(6, -54, 2, 0, 7); ctx.fill();
      
      if (z.hasPole) {
        ctx.strokeStyle = '#8d6e63'; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(10, -60); ctx.lineTo(25, -20); ctx.stroke();
      }
      if (z.type === 'cone') {
        ctx.fillStyle = '#e67e22'; ctx.beginPath(); ctx.moveTo(-15, -63); ctx.lineTo(0, -92); ctx.lineTo(15, -63); ctx.closePath(); ctx.fill();
        ctx.strokeStyle = '#d35400'; ctx.lineWidth = 2; ctx.stroke();
      } else if (z.type === 'bucket') {
        ctx.fillStyle = '#95a5a6'; ctx.beginPath(); ctx.moveTo(-17, -60); ctx.lineTo(-13, -88); ctx.lineTo(13, -88); ctx.lineTo(17, -60); ctx.closePath(); ctx.fill();
        ctx.strokeStyle = '#7f8c8d'; ctx.lineWidth = 2; ctx.stroke();
      }

      // Thanh máu nhỏ trên đầu
      ctx.fillStyle = '#222'; ctx.fillRect(-16, -82, 32, 5);
      ctx.fillStyle = '#e74c3c'; ctx.fillRect(-16, -82, 32 * (z.hp / z.maxHp), 5);
      ctx.restore();
    });

    // Đạn & Hiệu ứng hạt
    this.projectiles.forEach(p => {
      ctx.fillStyle = p.ice ? '#00d2d3' : '#2ecc71';
      ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, 7); ctx.fill();
      ctx.strokeStyle = '#1e8449'; ctx.lineWidth = 1.5; ctx.stroke();
    });
    this.particles.forEach(pt => {
      ctx.fillStyle = pt.color; ctx.fillRect(pt.x, pt.y, 4, 4);
    });

    // Mặt trời rơi
    this.suns.forEach(s => {
      ctx.fillStyle = '#f1c40f'; ctx.beginPath(); ctx.arc(s.x, s.y, 20, 0, 7); ctx.fill();
      ctx.strokeStyle = '#e67e22'; ctx.lineWidth = 2.5; ctx.stroke();
      ctx.fillStyle = '#d35400'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center'; ctx.fillText('25$', s.x, s.y + 4);
    });

    // --- THANH GIAO DIỆN GỖ CỔ ĐIỂN CAO CẤP ---
    ctx.fillStyle = '#3e2723'; ctx.fillRect(0, 0, W, 100);
    ctx.strokeStyle = '#1b120c'; ctx.lineWidth = 5; ctx.strokeRect(0, 0, W, 100);

    ctx.fillStyle = '#ffd700'; ctx.font = 'bold 20px "Arial Black"'; ctx.textAlign = 'left';
    ctx.fillText('☀️ ' + this.sun, 18, 58);

    // Thẻ bài cây trồng HD
    SAVE.unlocked.forEach((id, idx) => {
      let sx = 140 + idx * 74, sy = 12;
      let sel = (this.selCard === id);
      let cd = this.cooldowns[id] || 0;
      let maxCd = PLANTS[id].cd;

      ctx.fillStyle = sel ? '#27ae60' : '#5d4037';
      ctx.fillRect(sx, sy, 68, 76);
      ctx.strokeStyle = sel ? '#fff' : '#1b120c'; ctx.lineWidth = sel ? 3 : 2; ctx.strokeRect(sx, sy, 68, 76);
      
      ctx.fillStyle = '#fff'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center';
      ctx.fillText(PLANTS[id].n, sx + 34, sy + 28);
      ctx.fillStyle = '#f1c40f'; ctx.fillText(PLANTS[id].cost + ' ☀️', sx + 34, sy + 58);

      if (cd > 0) {
        ctx.fillStyle = 'rgba(0,0,0,0.65)';
        let h = 76 * (cd / maxCd);
        ctx.fillRect(sx, sy + 76 - h, 68, h);
      }
    });

    // Nút xẻng
    let sx = 740, sy = 12;
    ctx.fillStyle = this.shovel ? '#e74c3c' : '#7f8c8d';
    ctx.fillRect(sx, sy, 58, 76);
    ctx.strokeStyle = '#1b120c'; ctx.lineWidth = 2; ctx.strokeRect(sx, sy, 58, 76);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 13px Arial'; ctx.textAlign = 'center';
    ctx.fillText('⛏️ Xẻng', sx + 29, sy + 42);

    // Thanh tiến trình Wave
    ctx.fillStyle = '#1b120c'; ctx.fillRect(815, 36, 130, 24);
    ctx.strokeStyle = '#5d4037'; ctx.lineWidth = 2; ctx.strokeRect(815, 36, 130, 24);
    ctx.fillStyle = '#27ae60'; ctx.fillRect(817, 38, 126 * (this.wave / this.maxWaves), 20);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center';
    ctx.fillText(`WAVE ${this.wave}/${this.maxWaves}`, 880, 52);

    // Cảnh báo sóng Zombie lớn
    if (this.waveBannerTimer > 0) {
      ctx.fillStyle = '#e74c3c'; ctx.font = 'bold 30px "Arial Black"'; ctx.textAlign = 'center';
      ctx.shadowColor = '#000'; ctx.shadowBlur = 8;
      ctx.fillText('A HUGE WAVE OF ZOMBIES IS APPROACHING!', W / 2, 280);
      ctx.shadowBlur = 0;
    }
  }
}

// Bắt sự kiện click
cv.addEventListener('click', e => {
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;

  if (S === 'MENU') {
    S = 'PLAY'; G = new Game(SAVE.level);
    return;
  }

  if (S === 'PLAY') {
    for (let i = G.suns.length - 1; i >= 0; i--) {
      let s = G.suns[i];
      if (Math.hypot(mx - s.x, my - s.y) < 30) {
        G.sun += s.val; G.suns.splice(i, 1); SFX.sun();
        return;
      }
    }

    SAVE.unlocked.forEach((id, idx) => {
      let sx = 140 + idx * 74, sy = 12;
      if (mx >= sx && mx <= sx + 68 && my >= sy && my <= sy + 76) {
        if (G.sun >= PLANTS[id].cost && (!G.cooldowns[id] || G.cooldowns[id] <= 0)) {
          G.selCard = id; G.shovel = false; SFX.plant();
        }
      }
    });

    if (mx >= 740 && mx <= 798 && my >= 12 && my <= 88) {
      G.shovel = !G.shovel; G.selCard = null; SFX.plant();
    }

    if (mx >= GX && mx < GX + 9 * CW && my >= 100 && my < 600) {
      let c = Math.floor((mx - GX) / CW), r = Math.floor((my - 100) / RH);
      if (r >= 0 && r < 5 && c >= 0 && c < 9) {
        if (G.shovel) {
          if (G.grid[r][c]) {
            G.plants = G.plants.filter(p => !(p.r === r && p.c === c));
            G.grid[r][c] = null; G.shovel = false; SFX.plant();
          }
        } else if (G.selCard && !G.grid[r][c]) {
          G.sun -= PLANTS[G.selCard].cost;
          G.cooldowns[G.selCard] = PLANTS[G.selCard].cd;
          G.grid[r][c] = { id: G.selCard, hp: PLANTS[G.selCard].hp, r, c };
          G.plants.push(G.grid[r][c]);
          G.selCard = null; SFX.plant();
        }
      }
    }
  }

  if (S === 'LOSE') { S = 'MENU'; }
  if (S === 'WIN') { S = 'MENU'; UNLOCK_REWARD = null; }
});

function loop() {
  ctx.fillStyle = '#0d1a10'; ctx.fillRect(0, 0, W, H);
  if (S === 'MENU') {
    let g = ctx.createLinearGradient(0,0,0,H);
    g.addColorStop(0,'#1e3c72'); g.addColorStop(1,'#2a5298');
    ctx.fillStyle = g; ctx.fillRect(0,0,W,H);

    ctx.fillStyle = '#f1c40f'; ctx.font = 'bold 48px "Arial Black"'; ctx.textAlign = 'center';
    ctx.shadowColor = '#000'; ctx.shadowBlur = 12;
    ctx.fillText('PLANTS vs ZOMBIES', W/2, 170);
    ctx.shadowBlur = 0;

    ctx.fillStyle = '#fff'; ctx.font = 'bold 22px Arial';
    ctx.fillText(`HD DELUXE EDITION - MÀN 1-${SAVE.level}`, W/2, 230);

    ctx.fillStyle = '#27ae60'; ctx.fillRect(W/2 - 170, 310, 340, 65);
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 4; ctx.strokeRect(W/2 - 170, 310, 340, 65);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 26px "Arial Black"';
    ctx.fillText('BẮT ĐẦU CHƠI', W/2, 353);
  } else if (S === 'PLAY') {
    G.update(); G.draw();
  } else if (S === 'LOSE') {
    ctx.fillStyle = '#111'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle = '#e74c3c'; ctx.font = 'bold 44px "Arial Black"'; ctx.textAlign = 'center';
    ctx.fillText('ZOMBIES ĐÃ ĂN NÃO BẠN!', W/2, 250);
    ctx.fillStyle = '#fff'; ctx.font = '20px Arial';
    ctx.fillText('Click để thử lại', W/2, 320);
  } else if (S === 'WIN') {
    ctx.fillStyle = '#0d1a10'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle = '#f1c40f'; ctx.font = 'bold 42px "Arial Black"'; ctx.textAlign = 'center';
    ctx.fillText('🎉 MÀN CHƠI HOÀN THÀNH!', W/2, 170);

    if (UNLOCK_REWARD) {
      ctx.fillStyle = '#27ae60'; ctx.fillRect(W/2 - 140, 220, 280, 150);
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.strokeRect(W/2 - 140, 220, 280, 150);
      ctx.fillStyle = '#fff'; ctx.font = 'bold 18px Arial';
      ctx.fillText('BẠN MỞ KHÓA CÂY MỚI!', W/2, 255);
      ctx.font = 'bold 24px Arial'; ctx.fillStyle = '#ffd700';
      ctx.fillText(PLANTS[UNLOCK_REWARD].n, W/2, 300);
      ctx.font = '14px Arial'; ctx.fillStyle = '#fff';
      ctx.fillText(PLANTS[UNLOCK_REWARD].desc, W/2, 335);
    }

    ctx.fillStyle = '#fff'; ctx.font = '20px Arial';
    ctx.fillText('Click để tiếp tục màn tiếp theo', W/2, 440);
  }
  requestAnimationFrame(loop);
}
loop();
</script>
</body>
</html>
"""

st.components.v1.html(game_code, height=620, scrolling=False)
