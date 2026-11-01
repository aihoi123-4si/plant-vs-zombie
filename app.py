import streamlit as st
import base64, os

st.set_page_config(page_title="Plants vs Zombies - Ultimate Edition", layout="wide")
st.markdown("<h1 style='text-align:center;color:#5fbf3a;margin:0'>🌻 PLANTS vs ZOMBIES - ULTIMATE EDITION 🧟</h1>", unsafe_allow_html=True)

game_code = r"""
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body{margin:0;padding:0;background:#080f0a;display:flex;justify-content:center;align-items:center;height:100vh;overflow:hidden;font-family:Arial,sans-serif}
#gameContainer{position:relative;border:4px solid #2e5a36;border-radius:14px;box-shadow:0 10px 40px rgba(0,0,0,.9);background:#182e1c;overflow:hidden}
canvas{display:block;cursor:pointer}
</style></head>
<body>
<div id="gameContainer">
  <canvas id="c" width="960" height="600"></canvas>
</div>
<script>
const cv=document.getElementById('c'), ctx=cv.getContext('2d');
const W=960, H=600, GX=140, CW=80, RH=100;
let S='MENU', G=null;

// ---------- Âm thanh Web Audio API sống động ----------
const AC = window.AudioContext || window.webkitAudioContext; let au = null;
function initAu(){ if(!au && AC) au = new AC(); if(au && au.state==='suspended') au.resume(); }
function playTone(f1, f2, dur, type='sine', vol=0.12){
  initAu(); if(!au) return;
  const t = au.currentTime, o = au.createOscillator(), g = au.createGain();
  o.type = type; o.frequency.setValueAtTime(f1, t);
  if(f2) o.frequency.exponentialRampToValueAtTime(f2, t+dur);
  g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t+dur);
  o.connect(g); g.connect(au.destination); o.start(t); o.stop(t+dur);
}
const SFX = {
  sun: () => playTone(650, 950, 0.15, 'sine', 0.15),
  plant: () => playTone(350, 180, 0.12, 'triangle', 0.2),
  shoot: () => playTone(520, 260, 0.08, 'triangle', 0.1),
  splat: () => playTone(190, 80, 0.08, 'sawtooth', 0.12),
  boom: () => playTone(110, 20, 0.45, 'sawtooth', 0.35),
  mower: () => playTone(80, 150, 0.6, 'sawtooth', 0.25),
  lose: () => [300, 220, 150, 100].forEach((f,i)=>setTimeout(()=>playTone(f,f*0.8,0.35,'sawtooth',0.25), i*220)),
  win: () => [400, 500, 600, 800].forEach((f,i)=>setTimeout(()=>playTone(f,f*1.1,0.25,'triangle',0.2), i*150))
};

// ---------- Định nghĩa Cây trồng ----------
const PLANTS = {
  sunflower: {n:'Hướng Dương', cost:50, hp:300, cd:300, col:'#ffd93b', icon:'🌻'},
  peashooter: {n:'Đậu Bắn', cost:100, hp:300, cd:200, col:'#6cc644', icon:'🌱'},
  wallnut: {n:'Hạt Óc Chó', cost:50, hp:4000, cd:500, col:'#c68b3e', icon:'🥜'},
  snowpea: {n:'Đậu Tuyết', cost:175, hp:300, cd:250, col:'#8fd3f0', icon:'❄️'},
  repeater: {n:'Đậu Kép', cost:200, hp:300, cd:250, col:'#4aae30', icon:'🌿'},
  cherrybomb: {n:'Cherry Bomb', cost:150, hp:300, cd:800, col:'#d62828', icon:'🍒'}
};
const SEEDS = Object.keys(PLANTS);

// ---------- Định nghĩa loại Zombie ----------
const ZOM_TYPES = {
  basic: {name:'Zombie Thường', hp:200, sp:1.0, col:'#7a6a55', c:1},
  cone: {name:'Zombie Nón', hp:450, sp:0.9, col:'#e87a1e', c:2},
  bucket: {name:'Zombie Xô', hp:1100, sp:0.8, col:'#9aa0a6', c:4}
};

class Game {
  constructor(){
    this.sun = 250;
    this.time = 0;
    this.grid = Array.from({length:5}, ()=>Array(9).fill(null));
    this.plants = [];
    this.zombies = [];
    this.projectiles = [];
    this.suns = [];
    this.particles = [];
    this.mowers = Array.from({length:5}, (_,r)=>({r, x:GX-40, active:false}));
    this.selCard = null;
    this.shovel = false;
    this.spawnTimer = 0;
    this.wave = 1;
    this.maxWaves = 5;
    this.zombiesSpawnedInWave = 0;
    this.zombiesPerWave = 10;
  }
  update(){
    this.time++;
    // Rơi mặt trời tự nhiên
    if(this.time % 280 === 0){
      this.suns.push({x: Math.random()*(W-GX-100)+GX+50, y:-20, targetY: Math.random()*360+110, val:25, life:600});
      SFX.sun();
    }
    // Sinh đợt sóng Zombie
    this.spawnTimer++;
    if(this.spawnTimer > 180 && this.zombiesSpawnedInWave < this.zombiesPerWave){
      this.spawnTimer = 0;
      this.zombiesSpawnedInWave++;
      let r = Math.floor(Math.random()*5);
      let tKey = 'basic';
      if(this.wave >= 2 && Math.random()<0.4) tKey = 'cone';
      if(this.wave >= 3 && Math.random()<0.25) tKey = 'bucket';
      let zData = ZOM_TYPES[tKey];
      this.zombies.push({r, x:W+30, y:r*RH+140, hp:zData.hp, maxHp:zData.hp, sp:zData.sp, type:tKey, col:zData.col, eating:false});
    } else if(this.zombiesSpawnedInWave >= this.zombiesPerWave && this.zombies.length === 0){
      this.wave++;
      this.zombiesSpawnedInWave = 0;
      if(this.wave > this.maxWaves){
        S = 'WIN'; SFX.win();
      }
    }
    // Máy cắt cỏ quét ngang
    this.mowers.forEach(m=>{
      if(m.active){
        m.x += 9;
        this.zombies.forEach(z=>{
          if(z.r === m.r && Math.abs(z.x - m.x) < 35){ z.hp = 0; SFX.boom(); this.addParticles(z.x, z.y, '#e74c3c', 15); }
        });
        if(m.x > W+50) m.active = false;
      }
    });
    // Đạn đậu bay
    for(let i=this.projectiles.length-1; i>=0; i--){
      let p = this.projectiles[i]; p.x += p.vx;
      let hit = false;
      for(let z of this.zombies){
        if(z.r === p.r && Math.abs(z.x - p.x) < 25 && z.hp > 0){
          hit = true; z.hp -= p.dmg; SFX.splat();
          this.addParticles(p.x, p.y, p.ice?'#8fd3f0':'#6cc644', 5);
          if(p.ice) z.sp = 0.55;
          break;
        }
      }
      if(hit || p.x > W+50) this.projectiles.splice(i,1);
    }
    // Mặt trời tồn tại trên sân
    for(let i=this.suns.length-1; i>=0; i--){
      let s = this.suns[i];
      if(s.y < s.targetY) s.y += 2.5;
      s.life--; if(s.life <= 0) this.suns.splice(i,1);
    }
    // Hiệu ứng hạt (Particles)
    for(let i=this.particles.length-1; i>=0; i--){
      let pt = this.particles[i];
      pt.x += pt.vx; pt.y += pt.vy; pt.life--;
      if(pt.life <= 0) this.particles.splice(i,1);
    }
    // Cây trồng hoạt động
    this.plants.forEach(pl=>{
      pl.timer = (pl.timer || 0) + 1;
      if(pl.id === 'sunflower' && pl.timer % 400 === 0){
        this.suns.push({x: pl.c*CW+GX+40, y: pl.r*RH+120, targetY: pl.r*RH+150, val:25, life:500});
        SFX.sun();
      }
      if((pl.id === 'peashooter' || pl.id === 'snowpea' || pl.id === 'repeater') && pl.timer % 75 === 0){
        let hasZ = this.zombies.some(z => z.r === pl.r && z.x > pl.c*CW+GX && z.x < W);
        if(hasZ){
          let isIce = (pl.id === 'snowpea');
          this.projectiles.push({r: pl.r, x: pl.c*CW+GX+40, y: pl.r*RH+120, vx: 7.5, dmg: 20, ice: isIce});
          SFX.shoot();
          if(pl.id === 'repeater'){
            setTimeout(()=>{
              if(S==='PLAY') this.projectiles.push({r: pl.r, x: pl.c*CW+GX+40, y: pl.r*RH+120, vx: 7.5, dmg: 20, ice: false});
            }, 120);
          }
        }
      }
      if(pl.id === 'cherrybomb' && pl.timer === 25){
        this.zombies.forEach(z=>{
          if(Math.abs(z.r - pl.r) <= 1 && Math.abs(z.x - (pl.c*CW+GX+40)) < 130){ z.hp = 0; }
        });
        SFX.boom();
        this.addParticles(pl.c*CW+GX+40, pl.r*RH+150, '#e74c3c', 35);
        this.plants = this.plants.filter(p => p !== pl);
        this.grid[pl.r][pl.c] = null;
      }
    });
    // Zombie di chuyển và tấn công
    for(let i=this.zombies.length-1; i>=0; i--){
      let z = this.zombies[i];
      let target = this.plants.find(pl => pl.r === z.r && Math.abs((pl.c*CW+GX+40) - z.x) < 25);
      if(target){
        z.eating = true; target.hp -= 2.5;
        if(target.hp <= 0){
          this.grid[target.r][target.c] = null;
          this.plants = this.plants.filter(p => p !== target);
          z.eating = false;
        }
      } else {
        z.eating = false; z.x -= z.sp * 0.45;
      }
      // Chạm mép trái -> Kích hoạt máy cắt cỏ
      if(z.x < GX - 15){
        let m = this.mowers.find(item => item.r === z.r && !item.active);
        if(m){ m.active = true; SFX.mower(); }
        else { S = 'LOSE'; SFX.lose(); }
      }
      if(z.hp <= 0) this.zombies.splice(i,1);
    }
  }
  addParticles(x, y, color, count){
    for(let i=0; i<count; i++){
      this.particles.push({x, y, vx:(Math.random()-.5)*6, vy:(Math.random()-.5)*6, life:25, color});
    }
  }
  draw(){
    // Vẽ sân vườn ô bàn cờ sinh động
    for(let r=0; r<5; r++){
      for(let c=0; c<9; c++){
        ctx.fillStyle = (r+c)%2 === 0 ? '#58a82f' : '#4f9c2a';
        ctx.fillRect(GX+c*CW, r*RH+100, CW, RH);
        ctx.strokeStyle = 'rgba(0,0,0,0.14)'; ctx.strokeRect(GX+c*CW, r*RH+100, CW, RH);
      }
    }
    // Máy cắt cỏ
    this.mowers.forEach(m=>{
      ctx.fillStyle = '#e82424'; ctx.fillRect(GX-45, m.r*RH+130, 32, 22);
      ctx.fillStyle = '#222'; ctx.beginPath(); ctx.arc(GX-35, m.r*RH+155, 6,0,7); ctx.arc(GX-22, m.r*RH+155, 6,0,7); ctx.fill();
    });
    // Cây trồng trên sân
    this.plants.forEach(pl=>{
      let px = pl.c*CW+GX+40, py = pl.r*RH+150;
      ctx.fillStyle = PLANTS[pl.id].col;
      ctx.beginPath(); ctx.arc(px, py-20, 27, 0, 7); ctx.fill();
      ctx.strokeStyle = '#1b3b18'; ctx.lineWidth = 3; ctx.stroke();
      ctx.fillStyle = '#fff'; ctx.font = 'bold 12px Arial'; ctx.textAlign = 'center';
      ctx.fillText(PLANTS[pl.id].icon + ' ' + PLANTS[pl.id].n, px, py-16);
    });
    // Zombie chi tiết
    this.zombies.forEach(z=>{
      ctx.fillStyle = z.col; ctx.fillRect(z.x-14, z.y-45, 28, 45); // Thân
      ctx.fillStyle = '#a8c496'; ctx.beginPath(); ctx.arc(z.x, z.y-55, 13, 0, 7); ctx.fill(); // Đầu
      // Thanh máu
      ctx.fillStyle = '#444'; ctx.fillRect(z.x-16, z.y-22, 32, 5);
      ctx.fillStyle = '#e74c3c'; ctx.fillRect(z.x-16, z.y-22, 32*(z.hp/z.maxHp), 5);
    });
    // Đạn bay
    this.projectiles.forEach(p=>{
      ctx.fillStyle = p.ice ? '#8fd3f0' : '#6cc644';
      ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, 7); ctx.fill();
    });
    // Hạt hiệu ứng
    this.particles.forEach(pt=>{
      ctx.fillStyle = pt.color; ctx.fillRect(pt.x, pt.y, 4, 4);
    });
    // Mặt trời
    this.suns.forEach(s=>{
      ctx.fillStyle = '#ffd93b'; ctx.beginPath(); ctx.arc(s.x, s.y, 19, 0, 7); ctx.fill();
      ctx.strokeStyle = '#e67e22'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = '#d35400'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center'; ctx.fillText('25$', s.x, s.y+4);
    });

    // --- THANH GIAO DIỆN PHÍA TRÊN ---
    ctx.fillStyle = '#26160e'; ctx.fillRect(0, 0, W, 100);
    ctx.fillStyle = '#ffd700'; ctx.font = 'bold 20px Arial'; ctx.textAlign = 'left';
    ctx.fillText('☀️ ' + this.sun, 20, 58);

    // Thẻ bài cây trồng
    SEEDS.forEach((id, idx)=>{
      let sx = 145 + idx * 74, sy = 12;
      let sel = (this.selCard === id);
      ctx.fillStyle = sel ? '#27ae60' : '#4a3525';
      ctx.fillRect(sx, sy, 68, 76);
      ctx.strokeStyle = sel ? '#fff' : '#1a0f08'; ctx.lineWidth = sel ? 3 : 2; ctx.strokeRect(sx, sy, 68, 76);
      ctx.fillStyle = '#fff'; ctx.font = 'bold 10px Arial'; ctx.textAlign = 'center';
      ctx.fillText(PLANTS[id].icon + ' ' + PLANTS[id].n, sx+34, sy+26);
      ctx.fillStyle = '#f1c40f'; ctx.fillText(PLANTS[id].cost + ' ☀️', sx+34, sy+58);
    });

    // Nút Xẻng (Shovel)
    let sx = 600, sy = 12;
    ctx.fillStyle = this.shovel ? '#e74c3c' : '#7f8c8d';
    ctx.fillRect(sx, sy, 60, 76);
    ctx.strokeStyle = '#2c3e50'; ctx.lineWidth = 2; ctx.strokeRect(sx, sy, 60, 76);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 13px Arial'; ctx.textAlign = 'center';
    ctx.fillText('⛏️ Xẻng', sx+30, sy+42);

    // Thông tin Đợt sóng (Wave)
    ctx.fillStyle = '#fff'; ctx.font = 'bold 14px Arial'; ctx.textAlign = 'right';
    ctx.fillText(`Wave: ${this.wave}/${this.maxWaves}`, W - 20, 55);
  }
}

// Xử lý sự kiện Click chuột
cv.addEventListener('click', e => {
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;

  if(S === 'MENU'){
    S = 'PLAY'; G = new Game();
    return;
  }
  if(S === 'PLAY'){
    // Nhặt mặt trời
    for(let i = G.suns.length - 1; i >= 0; i--){
      let s = G.suns[i];
      if(Math.hypot(mx - s.x, my - s.y) < 30){
        G.sun += s.val; G.suns.splice(i,1); SFX.sun();
        return;
      }
    }
    // Chọn thẻ cây
    SEEDS.forEach((id, idx)=>{
      let sx = 145 + idx * 74, sy = 12;
      if(mx >= sx && mx <= sx+68 && my >= sy && my <= sy+76){
        if(G.sun >= PLANTS[id].cost){
          G.selCard = id; G.shovel = false; SFX.plant();
        }
      }
    });
    // Chọn xẻng
    if(mx >= 600 && mx <= 660 && my >= 12 && my <= 88){
      G.shovel = !G.shovel; G.selCard = null; SFX.plant();
    }
    // Trồng cây hoặc đào cây trên sân
    if(mx >= GX && mx < GX + 9*CW && my >= 100 && my < 600){
      let c = Math.floor((mx - GX)/CW), r = Math.floor((my - 100)/RH);
      if(r >= 0 && r < 5 && c >= 0 && c < 9){
        if(G.shovel){
          if(G.grid[r][c]){
            G.plants = G.plants.filter(p => !(p.r === r && p.c === c));
            G.grid[r][c] = null; G.shovel = false; SFX.plant();
          }
        } else if(G.selCard && !G.grid[r][c]){
          G.sun -= PLANTS[G.selCard].cost;
          G.grid[r][c] = {id: G.selCard, hp: PLANTS[G.selCard].hp, r, c};
          G.plants.push(G.grid[r][c]);
          G.selCard = null; SFX.plant();
        }
      }
    }
  }
  if(S === 'LOSE' || S === 'WIN'){ S = 'MENU'; }
});

function loop(){
  ctx.fillStyle = '#142818'; ctx.fillRect(0, 0, W, H);
  if(S === 'MENU'){
    ctx.fillStyle = '#5fbf3a'; ctx.font = 'bold 40px Arial'; ctx.textAlign = 'center';
    ctx.fillText('🌻 PLANTS vs ZOMBIES 🧟', W/2, 210);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 20px Arial';
    ctx.fillText('Phiên bản Ultimate Edition - Click để bắt đầu!', W/2, 280);
    ctx.font = '15px Arial'; ctx.fillStyle = '#aaa';
    ctx.fillText('Trồng Hướng Dương kiếm mặt trời, chọn cây và xẻng ở thanh trên cùng.', W/2, 330);
  } else if(S === 'PLAY'){
    G.update(); G.draw();
  } else if(S === 'LOSE'){
    ctx.fillStyle = '#e74c3c'; ctx.font = 'bold 42px Arial'; ctx.textAlign = 'center';
    ctx.fillText('ZOMBIES ĐÃ ĂN NÃO BẠN!', W/2, 250);
    ctx.fillStyle = '#fff'; ctx.font = '20px Arial';
    ctx.fillText('Click để chơi lại từ đầu', W/2, 320);
  } else if(S === 'WIN'){
    ctx.fillStyle = '#f1c40f'; ctx.font = 'bold 42px Arial'; ctx.textAlign = 'center';
    ctx.fillText('🎉 BẠN ĐÃ BẢO VỆ THÀNH CÔNG KHU VƯỜN!', W/2, 250);
    ctx.fillStyle = '#fff'; ctx.font = '20px Arial';
    ctx.fillText('Click để chơi ván mới', W/2, 320);
  }
  requestAnimationFrame(loop);
}
loop();
</script>
</body>
</html>
"""

st.components.v1.html(game_code, height=620, scrolling=False)
