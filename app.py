import streamlit as st
import base64, os

st.set_page_config(page_title="Plants vs Zombies - Classic Edition", layout="wide")
st.markdown("<h1 style='text-align:center;color:#5fbf3a;margin:0'>🌻 PLANTS vs ZOMBIES - CLASSIC REMAKE 🧟</h1>", unsafe_allow_html=True)

game_code = r"""
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body{margin:0;padding:0;background:#050b07;display:flex;justify-content:center;align-items:center;height:100vh;overflow:hidden;font-family:'Arial Black',Arial,sans-serif}
#gameBox{position:relative;border:5px solid #284e30;border-radius:16px;box-shadow:0 12px 50px rgba(0,0,0,.9);background:#112215;overflow:hidden}
canvas{display:block;cursor:pointer}
</style></head>
<body>
<div id="gameBox"><canvas id="c" width="960" height="600"></canvas></div>
<script>
const cv=document.getElementById('c'), ctx=cv.getContext('2d');
const W=960, H=600, GX=140, CW=80, RH=100;
let S='MENU', G=null;

// ---------- Âm thanh Web Audio API ----------
const AC = window.AudioContext || window.webkitAudioContext; let au = null;
function initAu(){ if(!au && AC) au = new AC(); if(au && au.state==='suspended') au.resume(); }
function playTone(f1, f2, dur, type='sine', vol=0.15){
  initAu(); if(!au) return;
  const t = au.currentTime, o = au.createOscillator(), g = au.createGain();
  o.type = type; o.frequency.setValueAtTime(f1, t);
  if(f2) o.frequency.exponentialRampToValueAtTime(f2, t+dur);
  g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t+dur);
  o.connect(g); g.connect(au.destination); o.start(t); o.stop(t+dur);
}
const SFX = {
  sun: () => { playTone(650, 950, 0.15, 'sine', 0.2); playTone(950, 1300, 0.12, 'sine', 0.15); },
  plant: () => playTone(320, 160, 0.12, 'triangle', 0.25),
  shoot: () => playTone(520, 260, 0.08, 'triangle', 0.12),
  splat: () => playTone(190, 80, 0.08, 'sawtooth', 0.15),
  boom: () => playTone(110, 20, 0.45, 'sawtooth', 0.35),
  mower: () => playTone(80, 160, 0.6, 'sawtooth', 0.3),
  lose: () => [300, 220, 150, 100].forEach((f,i)=>setTimeout(()=>playTone(f,f*0.8,0.35,'sawtooth',0.3), i*220)),
  win: () => [400, 500, 600, 800].forEach((f,i)=>setTimeout(()=>playTone(f,f*1.1,0.25,'triangle',0.25), i*150))
};

// ---------- Định nghĩa Cây trồng chuẩn nguyên tác ----------
const PLANTS = {
  sunflower: {n:'Hướng Dương', cost:50, hp:300, col:'#ffd93b'},
  peashooter: {n:'Đậu Bắn', cost:100, hp:300, col:'#6cc644'},
  wallnut: {n:'Hạt Óc Chó', cost:50, hp:4000, col:'#c68b3e'},
  snowpea: {n:'Đậu Tuyết', cost:175, hp:300, col:'#8fd3f0'},
  repeater: {n:'Đậu Kép', cost:200, hp:300, col:'#4aae30'},
  cherrybomb: {n:'Cherry', cost:150, hp:300, col:'#d62828'}
};
const SEEDS = Object.keys(PLANTS);

const ZOM_TYPES = {
  basic: {name:'Zombie Thường', hp:200, sp:0.95, col:'#7a6a55'},
  cone: {name:'Zombie Nón', hp:450, sp:0.85, col:'#e87a1e'},
  bucket: {name:'Zombie Xô', hp:1000, sp:0.75, col:'#9aa0a6'}
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
    this.mowers = Array.from({length:5}, (_,r)=>({r, x:GX-45, active:false}));
    this.selCard = null;
    this.shovel = false;
    this.spawnTimer = 0;
    this.wave = 1;
    this.maxWaves = 4;
    this.zombiesSpawned = 0;
    this.zombiesPerWave = 8;
  }
  update(){
    this.time++;
    // Mặt trời rơi tự nhiên
    if(this.time % 260 === 0){
      this.suns.push({x: Math.random()*(W-GX-100)+GX+50, y:-20, targetY: Math.random()*360+110, val:25, life:600});
      SFX.sun();
    }
    // Sinh Zombie theo đợt sóng
    this.spawnTimer++;
    if(this.spawnTimer > 170 && this.zombiesSpawned < this.zombiesPerWave){
      this.spawnTimer = 0;
      this.zombiesSpawned++;
      let r = Math.floor(Math.random()*5);
      let tKey = 'basic';
      if(this.wave >= 2 && Math.random()<0.45) tKey = 'cone';
      if(this.wave >= 3 && Math.random()<0.3) tKey = 'bucket';
      let zData = ZOM_TYPES[tKey];
      this.zombies.push({r, x:W+30, y:r*RH+140, hp:zData.hp, maxHp:zData.hp, sp:zData.sp, type:tKey, eating:false, fr:Math.random()*10});
    } else if(this.zombiesSpawned >= this.zombiesPerWave && this.zombies.length === 0){
      this.wave++;
      this.zombiesSpawned = 0;
      if(this.wave > this.maxWaves){ S = 'WIN'; SFX.win(); }
    }
    // Máy cắt cỏ quét sân
    this.mowers.forEach(m=>{
      if(m.active){
        m.x += 9;
        this.zombies.forEach(z=>{
          if(z.r === m.r && Math.abs(z.x - m.x) < 35){ z.hp = 0; SFX.boom(); this.addParticles(z.x, z.y, '#e74c3c', 15); }
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
          hit = true; z.hp -= p.dmg; SFX.splat();
          this.addParticles(p.x, p.y, p.ice?'#8fd3f0':'#6cc644', 5);
          if(p.ice) z.sp = 0.5;
          break;
        }
      }
      if(hit || p.x > W+50) this.projectiles.splice(i,1);
    }
    // Mặt trời trên sân
    for(let i=this.suns.length-1; i>=0; i--){
      let s = this.suns[i];
      if(s.y < s.targetY) s.y += 2.5;
      s.life--; if(s.life <= 0) this.suns.splice(i,1);
    }
    // Hiệu ứng hạt
    for(let i=this.particles.length-1; i>=0; i--){
      let pt = this.particles[i]; pt.x += pt.vx; pt.y += pt.vy; pt.life--;
      if(pt.life <= 0) this.particles.splice(i,1);
    }
    // Cây trồng hoạt động
    this.plants.forEach(pl=>{
      pl.timer = (pl.timer || 0) + 1;
      if(pl.id === 'sunflower' && pl.timer % 380 === 0){
        this.suns.push({x: pl.c*CW+GX+40, y: pl.r*RH+120, targetY: pl.r*RH+150, val:25, life:500});
        SFX.sun();
      }
      if((pl.id === 'peashooter' || pl.id === 'snowpea' || pl.id === 'repeater') && pl.timer % 70 === 0){
        let hasZ = this.zombies.some(z => z.r === pl.r && z.x > pl.c*CW+GX && z.x < W);
        if(hasZ){
          let isIce = (pl.id === 'snowpea');
          this.projectiles.push({r: pl.r, x: pl.c*CW+GX+40, y: pl.r*RH+120, vx: 8, dmg: 20, ice: isIce});
          SFX.shoot();
          if(pl.id === 'repeater'){
            setTimeout(()=>{ if(S==='PLAY') this.projectiles.push({r: pl.r, x: pl.c*CW+GX+40, y: pl.r*RH+120, vx: 8, dmg: 20, ice: false}); }, 120);
          }
        }
      }
      if(pl.id === 'cherrybomb' && pl.timer === 22){
        this.zombies.forEach(z=>{
          if(Math.abs(z.r - pl.r) <= 1 && Math.abs(z.x - (pl.c*CW+GX+40)) < 130){ z.hp = 0; }
        });
        SFX.boom();
        this.addParticles(pl.c*CW+GX+40, pl.r*RH+150, '#e74c3c', 35);
        this.plants = this.plants.filter(p => p !== pl);
        this.grid[pl.r][pl.c] = null;
      }
    });
    // Zombie di chuyển
    for(let i=this.zombies.length-1; i>=0; i--){
      let z = this.zombies[i]; z.fr += 0.12;
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
    // Nền sân vườn xanh mướt chuẩn PvZ
    for(let r=0; r<5; r++){
      for(let c=0; c<9; c++){
        ctx.fillStyle = (r+c)%2 === 0 ? '#62b236' : '#57a32f';
        ctx.fillRect(GX+c*CW, r*RH+100, CW, RH);
        ctx.strokeStyle = 'rgba(0,0,0,0.14)'; ctx.lineWidth=1; ctx.strokeRect(GX+c*CW, r*RH+100, CW, RH);
      }
    }
    // Máy cắt cỏ đỏ phía bên trái
    this.mowers.forEach(m=>{
      ctx.fillStyle = '#e82424'; ctx.fillRect(GX-45, m.r*RH+130, 32, 22);
      ctx.fillStyle = '#111'; ctx.beginPath(); ctx.arc(GX-35, m.r*RH+155, 6,0,7); ctx.arc(GX-22, m.r*RH+155, 6,0,7); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.fillRect(GX-20, m.r*RH+133, 6, 8);
    });

    // Vẽ Cây Trồng chi tiết cách điệu sinh động
    this.plants.forEach(pl=>{
      let px = pl.c*CW+GX+40, py = pl.r*RH+150;
      ctx.save(); ctx.translate(px, py);
      if(pl.id === 'sunflower'){
        // Thân & lá
        ctx.fillStyle='#3a8a2a'; ctx.fillRect(-3, -15, 6, 20);
        // Cánh hoa vàng
        for(let i=0; i<10; i++){
          let ang = i * Math.PI / 5;
          ctx.fillStyle='#ffd93b'; ctx.beginPath(); ctx.ellipse(Math.cos(ang)*16, Math.sin(ang)*16-20, 8, 5, ang, 0, 7); ctx.fill();
        }
        // Nhụy hoa nâu & mắt cười
        ctx.fillStyle='#8b5a2b'; ctx.beginPath(); ctx.arc(0, -20, 11, 0, 7); ctx.fill();
        ctx.fillStyle='#fff'; ctx.fillRect(-4, -23, 3, 4); ctx.fillRect(1, -23, 3, 4);
        ctx.fillStyle='#000'; ctx.fillRect(-3, -22, 1.5, 2); ctx.fillRect(2, -22, 1.5, 2);
      } else if(pl.id === 'peashooter' || pl.id === 'snowpea' || pl.id === 'repeater'){
        ctx.fillStyle='#3a8a2a'; ctx.fillRect(-3, -15, 6, 20);
        ctx.fillStyle = pl.id==='snowpea'?'#8fd3f0':'#6cc644';
        ctx.beginPath(); ctx.arc(0, -26, 17, 0, 7); ctx.fill();
        ctx.strokeStyle='#2d6a1f'; ctx.lineWidth=2; ctx.stroke();
        // Mõm ống đậu
        ctx.fillRect(5, -31, 14, 11); ctx.strokeRect(5, -31, 14, 11);
        if(pl.id==='repeater'){ ctx.fillRect(5, -20, 14, 9); ctx.strokeRect(5, -20, 14, 9); }
        // Mắt
        ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(-3, -30, 5, 0, 7); ctx.fill();
        ctx.fillStyle='#000'; ctx.beginPath(); ctx.arc(-2, -30, 2, 0, 7); ctx.fill();
      } else if(pl.id === 'wallnut'){
        ctx.fillStyle='#c68b3e'; ctx.beginPath(); ctx.ellipse(0, -22, 22, 26, 0, 0, 7); ctx.fill();
        ctx.strokeStyle='#7a5225'; ctx.lineWidth=3; ctx.stroke();
        // Mắt hạt óc chó lo lắng
        ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(-7, -26, 6, 0, 7); ctx.arc(7, -26, 6, 0, 7); ctx.fill();
        ctx.fillStyle='#000'; ctx.beginPath(); ctx.arc(-7, -26, 2, 0, 7); ctx.arc(7, -26, 2, 0, 7); ctx.fill();
        ctx.strokeStyle='#7a5225'; ctx.lineWidth=2; ctx.beginPath(); ctx.arc(0, -12, 8, 0, Math.PI); ctx.stroke();
      } else if(pl.id === 'cherrybomb'){
        ctx.fillStyle='#d62828'; ctx.beginPath(); ctx.arc(-10, -20, 14, 0, 7); ctx.arc(10, -20, 14, 0, 7); ctx.fill();
        ctx.fillStyle='#2e7d32'; ctx.fillRect(-2, -38, 4, 10);
      }
      ctx.restore();
    });

    // Vẽ Zombie cực chi tiết (Áo vest, cà vạt đỏ, đầu trọc xanh)[cite: 3]
    this.zombies.forEach(z=>{
      ctx.save(); ctx.translate(z.x, z.y);
      // Thân & áo khoác nâu, cà vạt đỏ
      ctx.fillStyle='#594838'; ctx.fillRect(-12, -45, 24, 38);
      ctx.fillStyle='#a62b2b'; ctx.fillRect(-3, -38, 5, 20); // Cà vạt đỏ
      // Chân
      ctx.fillStyle='#2c3e50'; ctx.fillRect(-10, -8, 8, 12); ctx.fillRect(2, -8, 8, 12);
      // Đầu Zombie (Da xanh, mắt lồi to, tóc thưa)
      ctx.fillStyle='#a8c496'; ctx.beginPath(); ctx.arc(0, -54, 15, 0, 7); ctx.fill();
      ctx.strokeStyle='#5f7a52'; ctx.lineWidth=2; ctx.stroke();
      // Tóc thưa lơ thơ
      ctx.strokeStyle='#333'; ctx.lineWidth=1.5;
      ctx.beginPath(); ctx.moveTo(-6,-67); ctx.lineTo(-9,-72); ctx.moveTo(2,-68); ctx.lineTo(4,-74); ctx.stroke();
      // Mắt lồi trắng toát
      ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(-5, -55, 6, 0, 7); ctx.arc(5, -53, 5, 0, 7); ctx.fill();
      ctx.fillStyle='#000'; ctx.beginPath(); ctx.arc(-4, -55, 2, 0, 7); ctx.arc(6, -53, 2, 0, 7); ctx.fill();
      // Mũ nón bảo vệ nếu có
      if(z.type==='cone'){
        ctx.fillStyle='#e87a1e'; ctx.beginPath(); ctx.moveTo(-14,-62); ctx.lineTo(0,-88); ctx.lineTo(14,-62); ctx.closePath(); ctx.fill();
        ctx.strokeStyle='#b3540c'; ctx.lineWidth=2; ctx.stroke();
      } else if(z.type==='bucket'){
        ctx.fillStyle='#9aa0a6'; ctx.beginPath(); ctx.moveTo(-16,-60); ctx.lineTo(-12,-85); ctx.lineTo(12,-85); ctx.lineTo(16,-60); ctx.closePath(); ctx.fill();
        ctx.strokeStyle='#525860'; ctx.lineWidth=2; ctx.stroke();
      }
      // Thanh máu nhỏ trên đầu
      ctx.fillStyle='#333'; ctx.fillRect(-16, -78, 32, 5);
      ctx.fillStyle='#e74c3c'; ctx.fillRect(-16, -78, 32*(z.hp/z.maxHp), 5);
      ctx.restore();
    });

    // Đạn đậu & hạt
    this.projectiles.forEach(p=>{
      ctx.fillStyle = p.ice ? '#8fd3f0' : '#6cc644';
      ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, 7); ctx.fill();
      ctx.strokeStyle = '#2d6a1f'; ctx.lineWidth = 1.5; ctx.stroke();
    });
    this.particles.forEach(pt=>{
      ctx.fillStyle = pt.color; ctx.fillRect(pt.x, pt.y, 4, 4);
    });
    // Mặt trời
    this.suns.forEach(s=>{
      ctx.fillStyle = '#ffd93b'; ctx.beginPath(); ctx.arc(s.x, s.y, 20, 0, 7); ctx.fill();
      ctx.strokeStyle = '#e67e22'; ctx.lineWidth = 2.5; ctx.stroke();
      ctx.fillStyle = '#d35400'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center'; ctx.fillText('25$', s.x, s.y+4);
    });

    // --- THANH GIAO DIỆN PHÍA TRÊN CỔ ĐIỂN (WOODEN BAR)[cite: 2] ---
    ctx.fillStyle = '#3b2213'; ctx.fillRect(0, 0, W, 100);
    ctx.strokeStyle = '#23130a'; ctx.lineWidth = 4; ctx.strokeRect(0, 0, W, 100);

    // Điểm mặt trời
    ctx.fillStyle = '#ffd700'; ctx.font = 'bold 19px "Arial Black", Arial'; ctx.textAlign = 'left';
    ctx.fillText('☀️ ' + this.sun, 18, 58);

    // Thẻ bài cây trồng[cite: 2]
    SEEDS.forEach((id, idx)=>{
      let sx = 150 + idx * 75, sy = 12;
      let sel = (this.selCard === id);
      ctx.fillStyle = sel ? '#27ae60' : '#5c3a21';
      ctx.fillRect(sx, sy, 68, 76);
      ctx.strokeStyle = sel ? '#fff' : '#23130a'; ctx.lineWidth = sel ? 3 : 2; ctx.strokeRect(sx, sy, 68, 76);
      ctx.fillStyle = '#fff'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center';
      ctx.fillText(PLANTS[id].n, sx+34, sy+30);
      ctx.fillStyle = '#f1c40f'; ctx.fillText(PLANTS[id].cost + ' ☀️', sx+34, sy+58);
    });

    // Nút Xẻng (Shovel)[cite: 2]
    let sx = 610, sy = 12;
    ctx.fillStyle = this.shovel ? '#e74c3c' : '#7f8c8d';
    ctx.fillRect(sx, sy, 58, 76);
    ctx.strokeStyle = '#23130a'; ctx.lineWidth = 2; ctx.strokeRect(sx, sy, 58, 76);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 13px Arial'; ctx.textAlign = 'center';
    ctx.fillText('⛏️ Xẻng', sx+29, sy+42);

    // Thanh tiến trình Đợt sóng (Wave Progress) góc phải[cite: 2]
    ctx.fillStyle = '#1a0f08'; ctx.fillRect(720, 36, 180, 24);
    ctx.strokeStyle = '#5c3a21'; ctx.lineWidth = 2; ctx.strokeRect(720, 36, 180, 24);
    ctx.fillStyle = '#5fbf3a'; ctx.fillRect(722, 38, 176 * (this.wave / this.maxWaves), 20);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 12px Arial'; ctx.textAlign = 'center';
    ctx.fillText(`WAVE ${this.wave} / ${this.maxWaves}`, 810, 52);
  }
}

// Xử lý sự kiện Click chuột chính xác
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
    // Chọn thẻ bài cây
    SEEDS.forEach((id, idx)=>{
      let sx = 150 + idx * 75, sy = 12;
      if(mx >= sx && mx <= sx+68 && my >= sy && my <= sy+76){
        if(G.sun >= PLANTS[id].cost){
          G.selCard = id; G.shovel = false; SFX.plant();
        }
      }
    });
    // Chọn xẻng
    if(mx >= 610 && mx <= 668 && my >= 12 && my <= 88){
      G.shovel = !G.shovel; G.selCard = null; SFX.plant();
    }
    // Trồng hoặc đào cây trên sân
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
  ctx.fillStyle = '#0f1f12'; ctx.fillRect(0, 0, W, H);
  if(S === 'MENU'){
    // Sảnh chờ phong cách cổ điển PvZ
    let g = ctx.createLinearGradient(0,0,0,H);
    g.addColorStop(0,'#4ca1af'); g.addColorStop(1,'#2c3e50');
    ctx.fillStyle = g; ctx.fillRect(0,0,W,H);

    ctx.fillStyle = '#76ba1b'; ctx.font = 'bold 44px "Arial Black", Arial'; ctx.textAlign = 'center';
    ctx.shadowColor = '#000'; ctx.shadowBlur = 10;
    ctx.fillText('PLANTS vs ZOMBIES', W/2, 180);
    ctx.shadowBlur = 0;

    ctx.fillStyle = '#fff'; ctx.font = 'bold 22px Arial';
    ctx.fillText('CLASSIC REMAKE EDITION', W/2, 230);

    ctx.fillStyle = '#f1c40f'; ctx.fillRect(W/2 - 160, 310, 320, 60);
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.strokeRect(W/2 - 160, 310, 320, 60);
    ctx.fillStyle = '#2c3e50'; ctx.font = 'bold 24px Arial';
    ctx.fillText('CHƠI NGAY (CLICK)', W/2, 348);
  } else if(S === 'PLAY'){
    G.update(); G.draw();
  } else if(S === 'LOSE'){
    ctx.fillStyle = '#111'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle = '#e74c3c'; ctx.font = 'bold 42px "Arial Black"'; ctx.textAlign = 'center';
    ctx.fillText('ZOMBIES ĐÃ ĂN NÃO BẠN!', W/2, 250);
    ctx.fillStyle = '#fff'; ctx.font = '20px Arial';
    ctx.fillText('Click để quay về Sảnh chính', W/2, 320);
  } else if(S === 'WIN'){
    ctx.fillStyle = '#111'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle = '#f1c40f'; ctx.font = 'bold 42px "Arial Black"'; ctx.textAlign = 'center';
    ctx.fillText('🎉 BẠN ĐÃ CHIẾN THẮNG KHU VƯỜN!', W/2, 250);
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
