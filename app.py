import streamlit as st
import base64, os

st.set_page_config(page_title="Plants vs Zombies - Streamlit Fix", layout="wide")
st.markdown("<h1 style='text-align:center;color:#5fbf3a;margin:0'>🌻 PLANTS vs ZOMBIES 🧟</h1>", unsafe_allow_html=True)

game_code = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    margin: 0; padding: 0;
    background: #0b140d;
    display: flex; justify-content: center; align-items: center;
    height: 100vh; overflow: hidden;
    font-family: 'Arial Black', Arial, sans-serif;
    user-select: none;
  }
  #gameContainer {
    position: relative;
    border: 4px solid #2d5a32;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.8);
    background: #142817;
    overflow: hidden;
  }
  canvas { display: block; cursor: pointer; }
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
let S = 'MENU', G = null;

// ---------- Âm thanh an toàn (Không bị nghẽn iframe) ----------
const AC = window.AudioContext || window.webkitAudioContext;
let au = null;
function playTone(f1, f2, dur, type='sine', vol=0.1) {
  try {
    if (!au && AC) au = new AC();
    if (au && au.state === 'suspended') au.resume();
    if (!au) return;
    const t = au.currentTime;
    const o = au.createOscillator(), g = au.createGain();
    o.type = type;
    o.frequency.setValueAtTime(f1, t);
    if (f2) o.frequency.exponentialRampToValueAtTime(Math.max(20, f2), t + dur);
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g); g.connect(au.destination);
    o.start(t); o.stop(t + dur);
  } catch(e) {}
}

const SFX = {
  sun: () => playTone(650, 950, 0.12, 'sine', 0.12),
  plant: () => playTone(320, 160, 0.1, 'triangle', 0.2),
  shoot: () => playTone(520, 260, 0.08, 'triangle', 0.1),
  splat: () => playTone(190, 80, 0.08, 'sawtooth', 0.1),
  boom: () => playTone(110, 20, 0.4, 'sawtooth', 0.3),
  mower: () => playTone(80, 150, 0.5, 'sawtooth', 0.2),
  lose: () => [300, 200, 100].forEach((f,i)=>setTimeout(()=>playTone(f,f*0.8,0.3,'sawtooth',0.2), i*200)),
  win: () => [400, 500, 600, 800].forEach((f,i)=>setTimeout(()=>playTone(f,f*1.1,0.2,'triangle',0.2), i*150))
};

// ---------- Dữ liệu Cây & Zombie ----------
const PLANTS = {
  sunflower: {n:'Hướng Dương', cost:50, hp:300, col:'#ffd93b'},
  peashooter: {n:'Đậu Bắn', cost:100, hp:300, col:'#6cc644'},
  wallnut: {n:'Óc Chó', cost:50, hp:4000, col:'#c68b3e'},
  snowpea: {n:'Đậu Tuyết', cost:175, hp:300, col:'#8fd3f0'},
  cherrybomb: {n:'Cherry', cost:150, hp:300, col:'#d62828'}
};
const SEEDS = Object.keys(PLANTS);

const ZOM_TYPES = {
  basic: {hp:200, sp:0.8, col:'#7a6a55'},
  cone: {hp:450, sp:0.7, col:'#e87a1e'},
  bucket: {hp:1000, sp:0.6, col:'#9aa0a6'}
};

class Game {
  constructor() {
    this.sun = 200;
    this.time = 0;
    this.grid = Array.from({length:5}, () => Array(9).fill(null));
    this.plants = [];
    this.zombies = [];
    this.projectiles = [];
    this.suns = [];
    this.particles = [];
    this.mowers = Array.from({length:5}, (_,r) => ({r, x:GX-40, active:false}));
    this.selCard = null;
    this.shovel = false;
    this.spawnTimer = 0;
    this.wave = 1;
    this.maxWaves = 4;
    this.zCount = 0;
  }

  update() {
    this.time++;

    // Mặt trời rơi
    if (this.time % 280 === 0) {
      this.suns.push({
        x: Math.random() * (W - GX - 100) + GX + 50,
        y: -20, targetY: Math.random() * 350 + 120,
        val: 25, life: 500
      });
      SFX.sun();
    }

    // Sinh Zombie
    this.spawnTimer++;
    if (this.spawnTimer > 180 && this.zCount < 8) {
      this.spawnTimer = 0;
      this.zCount++;
      let r = Math.floor(Math.random() * 5);
      let tKey = 'basic';
      if (this.wave >= 2 && Math.random() < 0.4) tKey = 'cone';
      if (this.wave >= 3 && Math.random() < 0.3) tKey = 'bucket';
      let zData = ZOM_TYPES[tKey];
      this.zombies.push({
        r, x: W + 30, y: r * RH + 140,
        hp: zData.hp, maxHp: zData.hp, sp: zData.sp,
        type: tKey, eating: false
      });
    } else if (this.zCount >= 8 && this.zombies.length === 0) {
      this.wave++;
      this.zCount = 0;
      if (this.wave > this.maxWaves) { S = 'WIN'; SFX.win(); }
    }

    // Máy cắt cỏ
    this.mowers.forEach(m => {
      if (m.active) {
        m.x += 10;
        this.zombies.forEach(z => {
          if (z.r === m.r && Math.abs(z.x - m.x) < 35) {
            z.hp = 0; SFX.boom();
          }
        });
        if (m.x > W + 50) m.active = false;
      }
    });

    // Đạn đậu
    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      let p = this.projectiles[i]; p.x += p.vx;
      let hit = false;
      for (let z of this.zombies) {
        if (z.r === p.r && Math.abs(z.x - p.x) < 25 && z.hp > 0) {
          hit = true; z.hp -= p.dmg; SFX.splat();
          if (p.ice) z.sp = 0.4;
          break;
        }
      }
      if (hit || p.x > W + 50) this.projectiles.splice(i, 1);
    }

    // Cập nhật mặt trời
    for (let i = this.suns.length - 1; i >= 0; i--) {
      let s = this.suns[i];
      if (s.y < s.targetY) s.y += 2;
      s.life--;
      if (s.life <= 0) this.suns.splice(i, 1);
    }

    // Cây hoạt động
    this.plants.forEach(pl => {
      pl.timer = (pl.timer || 0) + 1;
      if (pl.id === 'sunflower' && pl.timer % 380 === 0) {
        this.suns.push({
          x: pl.c * CW + GX + 40, y: pl.r * RH + 120,
          targetY: pl.r * RH + 150, val: 25, life: 450
        });
        SFX.sun();
      }
      if ((pl.id === 'peashooter' || pl.id === 'snowpea') && pl.timer % 70 === 0) {
        let hasZ = this.zombies.some(z => z.r === pl.r && z.x > pl.c * CW + GX && z.x < W);
        if (hasZ) {
          this.projectiles.push({
            r: pl.r, x: pl.c * CW + GX + 40, y: pl.r * RH + 120,
            vx: 8, dmg: 20, ice: (pl.id === 'snowpea')
          });
          SFX.shoot();
        }
      }
      if (pl.id === 'cherrybomb' && pl.timer === 20) {
        this.zombies.forEach(z => {
          if (Math.abs(z.r - pl.r) <= 1 && Math.abs(z.x - (pl.c * CW + GX + 40)) < 130) {
            z.hp = 0;
          }
        });
        SFX.boom();
        this.plants = this.plants.filter(p => p !== pl);
        this.grid[pl.r][pl.c] = null;
      }
    });

    // Zombie tấn công
    for (let i = this.zombies.length - 1; i >= 0; i--) {
      let z = this.zombies[i];
      let target = this.plants.find(pl => pl.r === z.r && Math.abs((pl.c * CW + GX + 40) - z.x) < 25);
      if (target) {
        z.eating = true; target.hp -= 2.5;
        if (target.hp <= 0) {
          this.grid[target.r][target.c] = null;
          this.plants = this.plants.filter(p => p !== target);
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

  draw() {
    // Vẽ cỏ
    for (let r = 0; r < 5; r++) {
      for (let c = 0; c < 9; c++) {
        ctx.fillStyle = (r + c) % 2 === 0 ? '#5ea832' : '#519929';
        ctx.fillRect(GX + c * CW, r * RH + 100, CW, RH);
        ctx.strokeStyle = 'rgba(0,0,0,0.1)';
        ctx.strokeRect(GX + c * CW, r * RH + 100, CW, RH);
      }
    }

    // Máy cắt cỏ
    this.mowers.forEach(m => {
      ctx.fillStyle = '#e82424';
      ctx.fillRect(GX - 45, m.r * RH + 130, 32, 22);
      ctx.fillStyle = '#111';
      ctx.beginPath();
      ctx.arc(GX - 35, m.r * RH + 155, 6, 0, 7);
      ctx.arc(GX - 22, m.r * RH + 155, 6, 0, 7);
      ctx.fill();
    });

    // Cây
    this.plants.forEach(pl => {
      let px = pl.c * CW + GX + 40, py = pl.r * RH + 150;
      ctx.fillStyle = PLANTS[pl.id].col;
      ctx.beginPath(); ctx.arc(px, py - 20, 24, 0, 7); ctx.fill();
      ctx.strokeStyle = '#1b3b18'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = '#fff'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center';
      ctx.fillText(PLANTS[pl.id].n, px, py - 16);
    });

    // Zombie
    this.zombies.forEach(z => {
      ctx.fillStyle = '#4a3b2c'; ctx.fillRect(z.x - 13, z.y - 45, 26, 38);
      ctx.fillStyle = '#c0392b'; ctx.fillRect(z.x - 3, z.y - 38, 5, 20);
      ctx.fillStyle = '#a8c496'; ctx.beginPath(); ctx.arc(z.x, z.y - 54, 14, 0, 7); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(z.x - 4, z.y - 55, 5, 0, 7); ctx.arc(z.x + 4, z.y - 54, 4, 0, 7); ctx.fill();
      ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(z.x - 3, z.y - 55, 2, 0, 7); ctx.arc(z.x + 5, z.y - 54, 2, 0, 7); ctx.fill();
      if (z.type === 'cone') {
        ctx.fillStyle = '#e87a1e';
        ctx.beginPath(); ctx.moveTo(z.x - 14, z.y - 62); ctx.lineTo(z.x, z.y - 86); ctx.lineTo(z.x + 14, z.y - 62); ctx.fill();
      } else if (z.type === 'bucket') {
        ctx.fillStyle = '#9aa0a6';
        ctx.beginPath(); ctx.moveTo(z.x - 15, z.y - 60); ctx.lineTo(z.x - 12, z.y - 82); ctx.lineTo(z.x + 12, z.y - 82); ctx.lineTo(z.x + 15, z.y - 60); ctx.fill();
      }
      ctx.fillStyle = '#222'; ctx.fillRect(z.x - 16, z.y - 78, 32, 5);
      ctx.fillStyle = '#e74c3c'; ctx.fillRect(z.x - 16, z.y - 78, 32 * (z.hp / z.maxHp), 5);
    });

    // Đạn
    this.projectiles.forEach(p => {
      ctx.fillStyle = p.ice ? '#8fd3f0' : '#6cc644';
      ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, 7); ctx.fill();
    });

    // Mặt trời
    this.suns.forEach(s => {
      ctx.fillStyle = '#ffd93b'; ctx.beginPath(); ctx.arc(s.x, s.y, 18, 0, 7); ctx.fill();
      ctx.strokeStyle = '#d35400'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = '#b7410e'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center'; ctx.fillText('25$', s.x, s.y + 4);
    });

    // Giao diện gỗ phía trên
    ctx.fillStyle = '#3b2213'; ctx.fillRect(0, 0, W, 100);
    ctx.fillStyle = '#ffd700'; ctx.font = 'bold 18px Arial'; ctx.textAlign = 'left';
    ctx.fillText('☀️ ' + this.sun, 18, 58);

    SEEDS.forEach((id, idx) => {
      let sx = 150 + idx * 75, sy = 12;
      let sel = (this.selCard === id);
      ctx.fillStyle = sel ? '#27ae60' : '#5c3a21';
      ctx.fillRect(sx, sy, 68, 76);
      ctx.strokeStyle = sel ? '#fff' : '#23130a'; ctx.lineWidth = sel ? 3 : 2;
      ctx.strokeRect(sx, sy, 68, 76);
      ctx.fillStyle = '#fff'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center';
      ctx.fillText(PLANTS[id].n, sx + 34, sy + 30);
      ctx.fillStyle = '#f1c40f'; ctx.fillText(PLANTS[id].cost + ' ☀️', sx + 34, sy + 58);
    });

    // Nút xẻng
    let sx = 610, sy = 12;
    ctx.fillStyle = this.shovel ? '#e74c3c' : '#7f8c8d';
    ctx.fillRect(sx, sy, 58, 76);
    ctx.strokeStyle = '#23130a'; ctx.lineWidth = 2; ctx.strokeRect(sx, sy, 58, 76);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 13px Arial'; ctx.textAlign = 'center';
    ctx.fillText('⛏️ Xẻng', sx + 29, sy + 42);

    // Tiến trình Wave
    ctx.fillStyle = '#100602'; ctx.fillRect(720, 36, 180, 24);
    ctx.fillStyle = '#5fbf3a'; ctx.fillRect(722, 38, 176 * (this.wave / this.maxWaves), 20);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 12px Arial'; ctx.textAlign = 'center';
    ctx.fillText(`WAVE ${this.wave} / ${this.maxWaves}`, 810, 52);
  }
}

// ---------- Xử lý Click Chuột ----------
cv.addEventListener('click', e => {
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;

  if (S === 'MENU') {
    S = 'PLAY'; G = new Game();
    return;
  }

  if (S === 'PLAY') {
    // Nhặt mặt trời
    for (let i = G.suns.length - 1; i >= 0; i--) {
      let s = G.suns[i];
      if (Math.hypot(mx - s.x, my - s.y) < 30) {
        G.sun += s.val; G.suns.splice(i, 1); SFX.sun();
        return;
      }
    }

    // Chọn thẻ cây
    SEEDS.forEach((id, idx) => {
      let sx = 150 + idx * 75, sy = 12;
      if (mx >= sx && mx <= sx + 68 && my >= sy && my <= sy + 76) {
        if (G.sun >= PLANTS[id].cost) {
          G.selCard = id; G.shovel = false; SFX.plant();
        }
      }
    });

    // Chọn xẻng
    if (mx >= 610 && mx <= 668 && my >= 12 && my <= 88) {
      G.shovel = !G.shovel; G.selCard = null; SFX.plant();
    }

    // Trồng / Đào cây
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
          G.grid[r][c] = { id: G.selCard, hp: PLANTS[G.selCard].hp, r, c };
          G.plants.push(G.grid[r][c]);
          G.selCard = null; SFX.plant();
        }
      }
    }
  }

  if (S === 'LOSE' || S === 'WIN') { S = 'MENU'; }
});

function loop() {
  ctx.fillStyle = '#0f1f12'; ctx.fillRect(0, 0, W, H);
  if (S === 'MENU') {
    let g = ctx.createLinearGradient(0,0,0,H);
    g.addColorStop(0,'#3498db'); g.addColorStop(0.5,'#2ecc71'); g.addColorStop(1,'#8e44ad');
    ctx.fillStyle = g; ctx.fillRect(0,0,W,H);

    ctx.fillStyle = '#27ae60'; ctx.font = 'bold 50px Arial'; ctx.textAlign = 'center';
    ctx.fillText('PLANTS vs ZOMBIES', W/2, 180);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 22px Arial';
    ctx.fillText('FIXED & PLAYABLE EDITION', W/2, 230);

    ctx.fillStyle = '#e67e22'; ctx.fillRect(W/2 - 150, 310, 300, 60);
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.strokeRect(W/2 - 150, 310, 300, 60);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 24px Arial';
    ctx.fillText('BẮT ĐẦU CHƠI', W/2, 348);
  } else if (S === 'PLAY') {
    G.update(); G.draw();
  } else if (S === 'LOSE') {
    ctx.fillStyle = '#111'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle = '#e74c3c'; ctx.font = 'bold 40px Arial'; ctx.textAlign = 'center';
    ctx.fillText('ZOMBIES ĐÃ ĂN NÃO BẠN!', W/2, 250);
    ctx.fillStyle = '#fff'; ctx.font = '20px Arial';
    ctx.fillText('Click để quay về Sảnh chính', W/2, 320);
  } else if (S === 'WIN') {
    ctx.fillStyle = '#111'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle = '#f1c40f'; ctx.font = 'bold 40px Arial'; ctx.textAlign = 'center';
    ctx.fillText('🎉 BẠN ĐÃ CHIẾN THẮNG!', W/2, 250);
    ctx.fillStyle = '#fff'; ctx.font = '20px Arial';
    ctx.fillText('Click để chơi lại ván mới', W/2, 320);
  }
  requestAnimationFrame(loop);
}
loop();
</script>
</body>
</html>
"""

st.components.v1.html(game_code, height=620, scrolling=False)
