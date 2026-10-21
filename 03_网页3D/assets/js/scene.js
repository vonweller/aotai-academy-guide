/**
 * 鳌台书院 · 三维场景（Three.js）
 * ---------------------------------------------------------------
 * 1) 若存在 assets/aotai_academy.glb（Blender 产出）则优先用它；
 * 2) 否则用本文件里的程序化岭南书院场景（门楼/石狮/云墙/天井/水池/假山/讲堂/工坊/六角亭/竹林）；
 * 3) 负责书生小人、行走路径、灯笼与光照。
 *
 * 坐标：Y 向上，米制，门前朝 +Z（与 02_数据/map.json 一致）。
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export const PALETTE = {
  tile: 0x6b6f73,        // 黛瓦
  tileDark: 0x4e5257,
  wall: 0xe8e3d8,        // 白墙
  wallDim: 0xd8d2c5,
  wood: 0x5a3a22,        // 深木
  woodLight: 0x8a5f3a,
  stone: 0x8a8f8a,       // 青石
  stoneDark: 0x6d726d,
  grass: 0x6f8f4f,
  grassDark: 0x57743d,
  water: 0x4f7f8f,
  gold: 0xc9a353,
  red: 0xa8352a,
  bamboo: 0x6f8f43,
  leaf: 0x4f7a3a,
};

const FALLBACK_MAP = {
  // 页面坐标 = Blender(x, y) 绕 Y 转 180° => (-x, -y)
  // 门楼 z=-17.6，前院 z=-9.5，讲堂 z=+6.5，工坊 (-8.2, -9.5)，六角亭 z=+13.5
  stages: [
    { stage: 1, key: 'gate', name_cn: '门口迎宾', actorStop: [0, 0, -22.0] },
    { stage: 2, key: 'front_yard', name_cn: '前院溯源', actorStop: [0, 0, -14.0] },
    { stage: 3, key: 'hall', name_cn: '讲堂楹联', actorStop: [0, 0, 0.0] },
    { stage: 4, key: 'workshop', name_cn: '庭院工坊', actorStop: [-3.0, 0, -4.0] },
    { stage: 5, key: 'pavilion', name_cn: '尾声留墨', actorStop: [3.5, 0, 9.0] },
  ],
  walkPaths: {
    '1-2': [[0, 0, -22.0], [0, 0, -18.5], [0, 0, -16.0], [0, 0, -14.0]],
    '2-3': [[0, 0, -14.0], [0, 0, -9.0], [0, 0, -3.0], [0, 0, 0.0]],
    '3-4': [[0, 0, 0.0], [-1.5, 0, -2.0], [-3.0, 0, -4.0]],
    '4-5': [[-3.0, 0, -4.0], [0, 0, 1.0], [2.0, 0, 6.0], [3.5, 0, 9.0]],
  },
  cameraPresets: {
    overview: { from: [26, 22, -34], look: [0, 2, -4] },
    gate: { from: [0, 3.6, -26], look: [0, 3.6, -17.6] },
    hall: { from: [0, 6.0, -4], look: [0, 3.0, 6.5] },
    workshop: { from: [0, 5.0, -3], look: [-8.2, 1.8, -9.5] },
    north: { from: [14, 12, -2], look: [0, 2, -16] },
  },
};

export const MAP = { ...FALLBACK_MAP };

/** 与后端/静态目录解耦的资源地址 */
export function assetUrl(p) {
  return new URL(p, document.baseURI).href;
}

// ------------------------------------------------------------------
// 纹理工具（程序化 canvas，不依赖外部图片）
// ------------------------------------------------------------------
function canvasTex(w, h, draw, repeat = [1, 1]) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const ctx = c.getContext('2d');
  draw(ctx, w, h);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeat[0], repeat[1]);
  t.anisotropy = 4;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function tileTexture() {
  return canvasTex(128, 128, (ctx, w, h) => {
    ctx.fillStyle = '#6b6f73'; ctx.fillRect(0, 0, w, h);
    for (let y = 0; y < h; y += 16) {
      for (let x = 0; x < w; x += 24) {
        const off = (y / 16) % 2 ? 12 : 0;
        ctx.fillStyle = ((x + y) / 8) % 3 < 1 ? '#75797d' : '#63676b';
        ctx.fillRect(x + off, y, 22, 14);
        ctx.strokeStyle = 'rgba(40,44,48,0.55)';
        ctx.strokeRect(x + off + 0.5, y + 0.5, 22, 14);
      }
    }
  });
}

function stoneTexture() {
  return canvasTex(128, 128, (ctx, w, h) => {
    ctx.fillStyle = '#8a8f8a'; ctx.fillRect(0, 0, w, h);
    for (let i = 0; i < 900; i++) {
      const x = Math.random() * w, y = Math.random() * h;
      const g = 110 + Math.random() * 50;
      ctx.fillStyle = 'rgba(' + g + ',' + (g + 4) + ',' + g + ',0.35)';
      ctx.fillRect(x, y, 1 + Math.random() * 2, 1 + Math.random() * 2);
    }
    ctx.strokeStyle = 'rgba(70,76,72,0.35)'; ctx.lineWidth = 1;
    for (let y = 0; y < h; y += 32) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
  });
}

function woodTexture() {
  return canvasTex(64, 128, (ctx, w, h) => {
    ctx.fillStyle = '#5a3a22'; ctx.fillRect(0, 0, w, h);
    for (let i = 0; i < 60; i++) {
      ctx.strokeStyle = 'rgba(' + (60 + Math.random() * 40) + ',' + (38 + Math.random() * 25) + ',18,0.5)';
      ctx.beginPath();
      const x = Math.random() * w;
      ctx.moveTo(x, 0); ctx.bezierCurveTo(x + 3, h / 3, x - 3, h * 2 / 3, x, h);
      ctx.stroke();
    }
  });
}

function latticeTexture() {
  return canvasTex(128, 128, (ctx, w, h) => {
    ctx.fillStyle = '#3d2a19'; ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = '#8a5f3a'; ctx.lineWidth = 3;
    for (let i = 0; i <= w; i += 16) {
      ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, h); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(w, i); ctx.stroke();
    }
    ctx.strokeStyle = 'rgba(200,160,90,0.45)'; ctx.lineWidth = 1.5;
    for (let i = 0; i <= w; i += 32) {
      ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i + 32, h); ctx.stroke();
    }
  }, [1, 1]);
}

function plaqueTexture(text, bg = '#26303a', fg = '#d9b45b') {
  return canvasTex(512, 160, (ctx, w, h) => {
    ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = fg; ctx.lineWidth = 8; ctx.strokeRect(10, 10, w - 20, h - 20);
    ctx.fillStyle = fg;
    ctx.font = 'bold 96px "STKaiti","KaiTi","Songti SC",serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(text, w / 2, h / 2 + 4);
  });
}

function stripTexture(text, bg = '#f2ece0', fg = '#3a2a1c') {
  return canvasTex(96, 512, (ctx, w, h) => {
    ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = fg;
    ctx.font = 'bold 52px "STKaiti","KaiTi","Songti SC",serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    [...text].forEach((ch, i) => ctx.fillText(ch, w / 2, 50 + i * 62));
  });
}

function grassTexture() {
  return canvasTex(256, 256, (ctx, w, h) => {
    ctx.fillStyle = '#6f8f4f'; ctx.fillRect(0, 0, w, h);
    for (let i = 0; i < 6000; i++) {
      const x = Math.random() * w, y = Math.random() * h;
      const g = 100 + Math.random() * 70;
      ctx.fillStyle = 'rgba(' + (70 + Math.random() * 40) + ',' + g + ',' + (50 + Math.random() * 30) + ',0.5)';
      ctx.fillRect(x, y, 1.5, 1.5);
    }
  }, [12, 12]);
}

// ------------------------------------------------------------------
// 基础构件
// ------------------------------------------------------------------
const MAT = {};

function initMaterials() {
  MAT.tile = new THREE.MeshStandardMaterial({ map: tileTexture(), roughness: 0.9, metalness: 0.05 });
  MAT.stone = new THREE.MeshStandardMaterial({ map: stoneTexture(), roughness: 0.95 });
  MAT.wall = new THREE.MeshStandardMaterial({ color: PALETTE.wall, roughness: 0.92 });
  MAT.wallDim = new THREE.MeshStandardMaterial({ color: PALETTE.wallDim, roughness: 0.94 });
  MAT.wood = new THREE.MeshStandardMaterial({ map: woodTexture(), roughness: 0.8, color: 0xb98f6a });
  MAT.woodDark = new THREE.MeshStandardMaterial({ color: PALETTE.wood, roughness: 0.78 });
  MAT.lattice = new THREE.MeshStandardMaterial({ map: latticeTexture(), roughness: 0.85 });
  MAT.gold = new THREE.MeshStandardMaterial({ color: PALETTE.gold, roughness: 0.45, metalness: 0.35 });
  MAT.red = new THREE.MeshStandardMaterial({ color: PALETTE.red, roughness: 0.7 });
  MAT.grass = new THREE.MeshStandardMaterial({ map: grassTexture(), roughness: 1 });
  MAT.stoneDark = new THREE.MeshStandardMaterial({ color: PALETTE.stoneDark, roughness: 0.95 });
  MAT.water = new THREE.MeshStandardMaterial({
    color: PALETTE.water, roughness: 0.15, metalness: 0.35, transparent: true, opacity: 0.82,
  });
  MAT.bamboo = new THREE.MeshStandardMaterial({ color: PALETTE.bamboo, roughness: 0.85 });
  MAT.leaf = new THREE.MeshStandardMaterial({ color: PALETTE.leaf, roughness: 0.9, side: THREE.DoubleSide });
  MAT.skin = new THREE.MeshStandardMaterial({ color: 0xf0cfae, roughness: 0.85 });
  MAT.robe = new THREE.MeshStandardMaterial({ color: 0x2f4a6b, roughness: 0.82 });
  MAT.robeTrim = new THREE.MeshStandardMaterial({ color: 0xd8dbe0, roughness: 0.8 });
  MAT.hair = new THREE.MeshStandardMaterial({ color: 0x1d1a18, roughness: 0.7 });
  MAT.lantern = new THREE.MeshStandardMaterial({ color: 0xd9532f, emissive: 0x8a2a10, emissiveIntensity: 0.9, roughness: 0.6 });
}

function box(w, h, d, mat, x = 0, y = 0, z = 0, group) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y + h / 2, z);
  m.castShadow = true; m.receiveShadow = true;
  if (group) group.add(m);
  return m;
}

function cyl(rt, rb, h, mat, x = 0, y = 0, z = 0, seg = 16, group) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat);
  m.position.set(x, y + h / 2, z);
  m.castShadow = true; m.receiveShadow = true;
  if (group) group.add(m);
  return m;
}

/** 硬山顶 / 庑殿顶：用「四坡 + 屋脊 + 瓦垄」拼出来 */
function roof(group, w, d, h, x, y, z, overhang = 1.0) {
  const W = w + overhang * 2, D = d + overhang * 2;
  const shape = new THREE.Shape();
  shape.moveTo(-W / 2, 0); shape.lineTo(W / 2, 0); shape.lineTo(0, h); shape.closePath();
  const g = new THREE.ExtrudeGeometry(shape, { depth: D, bevelEnabled: false });
  g.translate(0, 0, -D / 2);
  const m = new THREE.Mesh(g, MAT.tile);
  m.rotation.y = 0; m.position.set(x, y, z);
  m.castShadow = true; m.receiveShadow = true;
  group.add(m);
  // 屋脊
  const ridge = box(W * 0.98, 0.18, 0.42, MAT.tileDark || MAT.tile, 0, 0, 0);
  ridge.position.set(x, y + h - 0.06, z);
  group.add(ridge);
  // 瓦垄（沿坡面的细长条）
  const rows = Math.max(8, Math.floor(W / 0.45));
  for (let i = 0; i < rows; i++) {
    const t = (i / (rows - 1)) * 2 - 1;
    const bar = box(0.08, 0.06, D * 0.98, MAT.tileDark || MAT.tile, 0, 0, 0);
    bar.position.set(x + t * W * 0.5, y + h * (1 - Math.abs(t)) + 0.03, z);
    group.add(bar);
  }
}

/** 歇山/硬山顶的「檐口起翘」：用几段小圆柱近似 */
function eaveCurve(group, x, y, z, len, dir = 1) {
  for (let i = 0; i < 5; i++) {
    const t = i / 4;
    const seg = cyl(0.07, 0.07, len * 0.22, MAT.tileDark || MAT.tile, 0, 0, 0, 6);
    seg.rotation.z = Math.PI / 2;
    seg.position.set(x + dir * (len * 0.11 + t * len * 0.42), y + Math.sin(t * Math.PI * 0.5) * 0.22, z);
    group.add(seg);
  }
}

function latticeDoor(w, h, mat = MAT.lattice) {
  const g = new THREE.Group();
  const panel = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.06), mat);
  panel.position.y = h / 2;
  panel.castShadow = true; panel.receiveShadow = true;
  g.add(panel);
  const frame = new THREE.Mesh(new THREE.BoxGeometry(w + 0.16, 0.12, 0.12), MAT.woodDark);
  frame.position.y = h + 0.02; g.add(frame);
  for (const s of [-1, 1]) {
    const side = new THREE.Mesh(new THREE.BoxGeometry(0.1, h + 0.1, 0.12), MAT.woodDark);
    side.position.set(s * (w / 2 + 0.04), h / 2, 0);
    g.add(side);
  }
  return g;
}

function plaque(text, w = 2.6, h = 0.8) {
  const m = new THREE.Mesh(
    new THREE.PlaneGeometry(w, h),
    new THREE.MeshStandardMaterial({ map: plaqueTexture(text), roughness: 0.6, metalness: 0.1 })
  );
  m.castShadow = false;
  return m;
}

function couplet(text) {
  const m = new THREE.Mesh(
    new THREE.PlaneGeometry(0.42, 2.4),
    new THREE.MeshStandardMaterial({ map: stripTexture(text), roughness: 0.7 })
  );
  return m;
}

// ------------------------------------------------------------------
// 场景各部分
// ------------------------------------------------------------------
function buildGround(group) {
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(80, 80), MAT.grass);
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  group.add(ground);

  // 中轴青石板路
  const road = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 34), MAT.stone);
  road.rotation.x = -Math.PI / 2;
  road.position.set(0, 0.02, 4);
  road.receiveShadow = true;
  group.add(road);

  // 前院天井
  const yard = new THREE.Mesh(new THREE.PlaneGeometry(14, 12), MAT.stone);
  yard.rotation.x = -Math.PI / 2;
  yard.position.set(0, 0.015, 9.5);
  yard.receiveShadow = true;
  group.add(yard);

  // 池塘
  const pond = new THREE.Mesh(new THREE.CircleGeometry(2.6, 32), MAT.water);
  pond.rotation.x = -Math.PI / 2;
  pond.position.set(3.6, 0.08, 10.5);
  group.add(pond);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(2.65, 0.16, 8, 40), MAT.stoneDark);
  rim.rotation.x = -Math.PI / 2; rim.position.set(3.6, 0.1, 10.5);
  group.add(rim);

  // 台阶（门外，+Z 侧）
  for (let i = 0; i < 3; i++) {
    box(8 - i * 0.6, 0.16, 0.7, MAT.stone, 0, 0.08 + i * 0.16, 19.2 + i * 0.6, group);
  }
}

function buildGate(group) {
  const g = new THREE.Group();
  g.name = 'gate';
  // 台基
  box(11, 0.5, 3.2, MAT.stone, 0, 0, 17.6, g);
  // 四柱
  for (const x of [-4.2, -1.4, 1.4, 4.2]) {
    cyl(0.24, 0.28, 4.0, MAT.red, x, 0.5, 17.0, 12, g);
  }
  // 横梁
  box(10.4, 0.42, 0.5, MAT.woodDark, 0, 4.2, 16.9, g);
  box(10.8, 0.28, 0.7, MAT.red, 0, 4.6, 16.9, g);
  // 门板（两扇，向内敞开，露出院内）
  for (const side of [-1, 1]) {
    const pivot = new THREE.Group();
    pivot.position.set(side * 1.5, 0, 16.8);
    const leaf = new THREE.Mesh(new THREE.BoxGeometry(1.48, 3.6, 0.12), MAT.lattice);
    leaf.position.set(-side * 0.74, 2.3, 0);
    leaf.castShadow = true;
    pivot.add(leaf);
    pivot.rotation.y = side * 1.15;   // 向院内开
    g.add(pivot);
  }
  // 门框
  for (const x of [-1.65, 1.65]) box(0.2, 3.8, 0.3, MAT.woodDark, x, 1.9, 16.8, g);
  // 牌匾
  const p = plaque('鰲台書院', 3.4, 1.0);
  p.position.set(0, 4.2, 17.28);
  g.add(p);
  // 屋顶
  roof(g, 11.2, 3.4, 2.0, 0, 5.0, 17.0, 0.9);
  // 灯笼
  for (const x of [-3.0, 3.0]) {
    const l = new THREE.Mesh(new THREE.SphereGeometry(0.32, 12, 10), MAT.lantern);
    l.position.set(x, 3.9, 17.2);
    g.add(l);
    const light = new THREE.PointLight(0xff9a4a, 1.1, 9, 2);
    light.position.set(x, 3.9, 17.2);
    g.add(light);
  }
  group.add(g);
  return g;
}

function buildLion(group, x, z, flip = 1) {
  const g = new THREE.Group();
  g.position.set(x, 0, z);
  g.rotation.y = flip > 0 ? -0.18 : 0.18;
  // 基座
  box(1.4, 0.7, 1.6, MAT.stone, 0, 0, 0, g);
  box(1.2, 0.22, 1.4, MAT.stoneDark, 0, 0.7, 0, g);
  // 身躯
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.62, 16, 12), MAT.stone);
  body.scale.set(0.82, 1.0, 1.15);
  body.position.set(0, 1.45, 0);
  body.castShadow = true;
  g.add(body);
  // 头
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.46, 16, 12), MAT.stone);
  head.position.set(0, 2.05, 0.34);
  head.castShadow = true;
  g.add(head);
  // 鬃毛
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * Math.PI * 2;
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.14, 8, 6), MAT.stoneDark);
    m.position.set(Math.cos(a) * 0.44, 2.12 + Math.sin(a) * 0.1, 0.28 + Math.sin(a) * 0.28);
    g.add(m);
  }
  // 眼
  for (const s of [-1, 1]) {
    const e = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 6), MAT.stoneDark);
    e.position.set(s * 0.17, 2.18, 0.72);
    g.add(e);
  }
  // 前腿
  for (const s of [-1, 1]) box(0.24, 0.7, 0.3, MAT.stone, s * 0.3, 0.75, 0.55, g);
  // 绣球
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 10), MAT.stoneDark);
  ball.position.set(0.3, 0.82, 0.95);
  g.add(ball);
  group.add(g);
  return g;
}

/** 云墙：波浪顶 + 漏窗 */
function buildCloudWall(group, z0, z1, x, mirror = 1) {
  const g = new THREE.Group();
  const len = Math.abs(z1 - z0);
  const seg = 12;
  for (let i = 0; i < seg; i++) {
    const z = z0 + (z1 - z0) * (i + 0.5) / seg;
    const h = 2.4 + Math.sin((i / seg) * Math.PI * 3) * 0.32;
    const w = new THREE.Mesh(new THREE.BoxGeometry(0.5, h, len / seg + 0.02), MAT.wall);
    w.position.set(x, h / 2, z);
    w.castShadow = true; w.receiveShadow = true;
    g.add(w);
    // 墙帽（黛瓦）
    const cap = new THREE.Mesh(new THREE.BoxGeometry(0.78, 0.16, len / seg + 0.06), MAT.tile);
    cap.position.set(x, h + 0.06, z);
    cap.castShadow = true;
    g.add(cap);
  }
  // 漏窗（两个）
  for (const t of [0.28, 0.72]) {
    const z = z0 + (z1 - z0) * t;
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.09, 8, 24), MAT.stoneDark);
    ring.rotation.y = Math.PI / 2;
    ring.position.set(x, 1.7, z);
    g.add(ring);
    // 窗芯格栅
    for (let i = -2; i <= 2; i++) {
      const bar = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.1, 0.05), MAT.woodDark);
      bar.position.set(x + 0.01, 1.7, z + i * 0.22);
      g.add(bar);
    }
  }
  group.add(g);
  return g;
}

function buildHall(group) {
  const g = new THREE.Group();
  g.name = 'hall';
  // 台基
  box(18, 0.7, 11, MAT.stone, 0, 0, -6.5, g);
  for (let i = 0; i < 2; i++) box(7 - i * 0.5, 0.18, 0.7, MAT.stone, 0, 0.7 + i * 0.18, 0.2 - i * 0.55, g);
  // 后墙与侧墙
  box(16, 4.4, 0.5, MAT.wall, 0, 0.7, -11.4, g);
  box(0.5, 4.4, 9.6, MAT.wall, -7.8, 0.7, -6.6, g);
  box(0.5, 4.4, 9.6, MAT.wall, 7.8, 0.7, -6.6, g);
  // 前墙（留门洞）
  box(6.6, 4.4, 0.5, MAT.wall, -4.7, 0.7, -1.7, g);
  box(6.6, 4.4, 0.5, MAT.wall, 4.7, 0.7, -1.7, g);
  box(2.8, 1.0, 0.5, MAT.wall, 0, 4.1, -1.7, g);
  // 廊柱
  for (const x of [-6.2, -2.2, 2.2, 6.2]) {
    cyl(0.26, 0.3, 3.9, MAT.red, x, 0.7, -1.4, 12, g);
    box(0.9, 0.16, 0.9, MAT.stone, x, 0.7, -1.4, g);
  }
  // 大门 + 格栅
  const d1 = latticeDoor(1.3, 3.4);
  d1.position.set(-1.45, 0.7, -1.68);
  g.add(d1);
  const d2 = latticeDoor(1.3, 3.4);
  d2.position.set(1.45, 0.7, -1.68);
  g.add(d2);
  // 匾额
  const p = plaque('講堂', 2.6, 0.78);
  p.position.set(0, 4.05, -1.42);
  g.add(p);
  // 楹联
  const c1 = couplet('書聲琅琅傳嶺南');
  c1.position.set(-3.5, 2.5, -1.40);
  g.add(c1);
  const c2 = couplet('文脈綿綿續鰲臺');
  c2.position.set(3.5, 2.5, -1.40);
  g.add(c2);
  // 檐口
  box(17.4, 0.32, 1.1, MAT.tile, 0, 4.9, -1.2, g);
  // 屋顶
  roof(g, 17.2, 10.4, 3.4, 0, 5.1, -6.6, 1.2);
  eaveCurve(g, -8.6, 5.1, -1.4, 3.2, 1);
  eaveCurve(g, 8.6, 5.1, -1.4, 3.2, -1);
  // 灯笼
  for (const x of [-5.4, 5.4]) {
    const l = new THREE.Mesh(new THREE.SphereGeometry(0.3, 12, 10), MAT.lantern);
    l.position.set(x, 4.3, -1.9);
    g.add(l);
    const light = new THREE.PointLight(0xffa050, 1.0, 10, 2);
    light.position.set(x, 4.2, -1.9);
    g.add(light);
  }
  // 堂内地面
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(15, 9), MAT.stone);
  floor.rotation.x = -Math.PI / 2; floor.position.set(0, 0.72, -6.6);
  g.add(floor);
  group.add(g);
  return g;
}

function buildWorkshop(group) {
  const g = new THREE.Group();
  g.name = 'workshop';
  box(7, 0.5, 8, MAT.stone, 9.5, 0, 2, g);
  box(6.2, 3.4, 7.2, MAT.wallDim, 9.5, 0.5, 2, g);
  const door = latticeDoor(1.6, 2.4);
  door.position.set(7.1, 0.5, 2); door.rotation.y = -Math.PI / 2;
  g.add(door);
  roof(g, 6.6, 7.6, 2.2, 9.5, 4.0, 2, 0.8);
  const p = plaque('工坊', 1.8, 0.6);
  p.rotation.y = -Math.PI / 2;
  p.position.set(6.38, 3.5, 2);
  g.add(p);
  group.add(g);
  return g;
}

function buildPavilion(group) {
  const g = new THREE.Group();
  g.name = 'pavilion';
  box(4.6, 0.4, 4.6, MAT.stone, -6.5, 0, -13.5, g);
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    cyl(0.16, 0.18, 3.0, MAT.red, -6.5 + Math.cos(a) * 1.55, 0.4, -13.5 + Math.sin(a) * 1.55, 10, g);
  }
  const roofG = new THREE.Mesh(new THREE.ConeGeometry(2.9, 1.7, 6), MAT.tile);
  roofG.position.set(-6.5, 4.15, -13.5);
  roofG.castShadow = true;
  g.add(roofG);
  const finial = new THREE.Mesh(new THREE.SphereGeometry(0.18, 10, 8), MAT.gold);
  finial.position.set(-6.5, 5.1, -13.5);
  g.add(finial);
  const l = new THREE.Mesh(new THREE.SphereGeometry(0.24, 10, 8), MAT.lantern);
  l.position.set(-6.5, 3.3, -13.5);
  g.add(l);
  const light = new THREE.PointLight(0xffa050, 0.9, 8, 2);
  light.position.set(-6.5, 3.3, -13.5);
  g.add(light);
  group.add(g);
  return g;
}

function buildRockery(group) {
  const g = new THREE.Group();
  const rocks = [
    { p: [-4.2, 0.9, 10.2], s: [1.4, 1.8, 1.2], r: 0.3 },
    { p: [-5.1, 0.7, 9.1], s: [1.0, 1.2, 0.9], r: 1.2 },
    { p: [-3.5, 0.5, 9.4], s: [0.8, 0.9, 0.8], r: 2.1 },
    { p: [-4.6, 1.7, 9.8], s: [0.6, 0.7, 0.6], r: 0.8 },
  ];
  for (const r of rocks) {
    const m = new THREE.Mesh(new THREE.DodecahedronGeometry(0.9, 0), MAT.stoneDark);
    m.position.set(r.p[0], r.p[1], r.p[2]);
    m.scale.set(r.s[0], r.s[1], r.s[2]);
    m.rotation.set(r.r, r.r * 1.7, r.r * 0.6);
    m.castShadow = true; m.receiveShadow = true;
    g.add(m);
  }
  group.add(g);
  return g;
}

function buildBamboo(group, x, z, n = 7) {
  const g = new THREE.Group();
  g.position.set(x, 0, z);
  for (let i = 0; i < n; i++) {
    const h = 3.2 + Math.random() * 2.2;
    const bx = (Math.random() - 0.5) * 1.6;
    const bz = (Math.random() - 0.5) * 1.6;
    const stalk = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.075, h, 6), MAT.bamboo);
    stalk.position.set(bx, h / 2, bz);
    stalk.rotation.z = (Math.random() - 0.5) * 0.12;
    stalk.castShadow = true;
    g.add(stalk);
    for (let k = 0; k < 5; k++) {
      const leaf = new THREE.Mesh(new THREE.PlaneGeometry(0.85, 0.22), MAT.leaf);
      leaf.position.set(bx + (Math.random() - 0.5) * 0.9, h * (0.55 + Math.random() * 0.42), bz + (Math.random() - 0.5) * 0.9);
      leaf.rotation.set(Math.random() * 1.2 - 0.6, Math.random() * Math.PI, Math.random() * 1.2 - 0.6);
      g.add(leaf);
    }
  }
  group.add(g);
  return g;
}

function buildTree(group, x, z, s = 1) {
  const g = new THREE.Group();
  g.position.set(x, 0, z);
  const trunk = cyl(0.16 * s, 0.26 * s, 2.4 * s, MAT.woodDark, 0, 0, 0, 8, g);
  trunk.castShadow = true;
  const cols = [0x4f7a3a, 0x5d8a45, 0x446b33];
  for (let i = 0; i < 5; i++) {
    const f = new THREE.Mesh(new THREE.IcosahedronGeometry((0.95 - i * 0.1) * s, 0), new THREE.MeshStandardMaterial({
      color: cols[i % 3], roughness: 0.95, flatShading: true,
    }));
    f.position.set((Math.random() - 0.5) * 1.1 * s, (2.4 + Math.random() * 1.2) * s, (Math.random() - 0.5) * 1.1 * s);
    f.castShadow = true;
    g.add(f);
  }
  group.add(g);
  return g;
}

// ------------------------------------------------------------------
// 书生小人
// ------------------------------------------------------------------
export function createScholar() {
  const g = new THREE.Group();
  g.name = 'scholar';

  const body = new THREE.Group();       // 站立部分（上下摆动）
  g.add(body);

  // 长袍
  const robe = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.42, 1.05, 14, 1, true), MAT.robe);
  robe.position.y = 0.72;
  robe.castShadow = true;
  body.add(robe);
  // 袍边
  const trim = new THREE.Mesh(new THREE.CylinderGeometry(0.425, 0.44, 0.12, 14), MAT.robeTrim);
  trim.position.y = 0.24;
  body.add(trim);
  // 上身
  const torso = new THREE.Mesh(new THREE.SphereGeometry(0.3, 14, 12), MAT.robe);
  torso.scale.set(1, 1.25, 0.85);
  torso.position.y = 1.22;
  torso.castShadow = true;
  body.add(torso);
  // 领口
  const collar = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.045, 6, 14), MAT.robeTrim);
  collar.rotation.x = Math.PI / 2;
  collar.position.y = 1.46;
  body.add(collar);
  // 头
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.24, 16, 14), MAT.skin);
  head.position.y = 1.62;
  head.castShadow = true;
  body.add(head);
  // 发髻
  const hair = new THREE.Mesh(new THREE.SphereGeometry(0.235, 16, 12, 0, Math.PI * 2, 0, Math.PI * 0.62), MAT.hair);
  hair.position.y = 1.66;
  body.add(hair);
  const bun = new THREE.Mesh(new THREE.SphereGeometry(0.105, 10, 8), MAT.hair);
  bun.position.set(0, 1.86, -0.03);
  body.add(bun);
  // 眼睛
  const eyeMat = new THREE.MeshStandardMaterial({ color: 0x23303a, roughness: 0.4 });
  for (const s of [-1, 1]) {
    const e = new THREE.Mesh(new THREE.SphereGeometry(0.033, 8, 6), eyeMat);
    e.position.set(s * 0.085, 1.65, 0.215);
    body.add(e);
  }
  // 嘴角
  const mouth = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.015, 0.01), new THREE.MeshStandardMaterial({ color: 0xa85a5a }));
  mouth.position.set(0, 1.55, 0.232);
  body.add(mouth);

  // 手臂（可摆动的两条）
  const armMat = MAT.robe;
  function makeArm(side) {
    const pivot = new THREE.Group();
    pivot.position.set(side * 0.3, 1.36, 0);
    const upper = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.085, 0.5, 8), armMat);
    upper.position.y = -0.25;
    upper.castShadow = true;
    pivot.add(upper);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(0.075, 8, 8), MAT.skin);
    hand.position.y = -0.52;
    pivot.add(hand);
    // 书卷/折扇（右手）
    if (side > 0) {
      const fan = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.42, 6), MAT.woodLight || MAT.wood);
      fan.rotation.z = Math.PI / 2;
      fan.position.set(0.06, -0.58, 0.06);
      pivot.add(fan);
    }
    body.add(pivot);
    return pivot;
  }
  const armL = makeArm(-1);
  const armR = makeArm(1);

  // 腿（藏在袍里，走路时轻微摆动）
  function makeLeg(side) {
    const pivot = new THREE.Group();
    pivot.position.set(side * 0.12, 0.5, 0);
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.065, 0.5, 8), new THREE.MeshStandardMaterial({ color: 0x2a3a4a }));
    leg.position.y = -0.25;
    pivot.add(leg);
    const shoe = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.07, 0.26), new THREE.MeshStandardMaterial({ color: 0x1d1a18 }));
    shoe.position.set(0, -0.52, 0.05);
    pivot.add(shoe);
    g.add(pivot);
    return pivot;
  }
  const legL = makeLeg(-1);
  const legR = makeLeg(1);

  // 方便外部做动画
  g.userData = { body, armL, armR, legL, legR, walkPhase: 0, moving: false };
  return g;
}

// ------------------------------------------------------------------
// 世界
// ------------------------------------------------------------------
export class World {
  constructor(container) {
    this.container = container;
    this.clock = new THREE.Clock();
    this.actors = [];
    this.lanternLights = [];
    this.glbLoaded = false;
    this.pathVisible = false;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xa8bcc8);
    this.scene.fog = new THREE.Fog(0xa8bcc8, 85, 190);

    this.camera = new THREE.PerspectiveCamera(46, 1, 0.1, 400);
    this.camera.position.set(16, 12, 30);

    this.renderer = new THREE.WebGLRenderer({ canvas: container, antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    initMaterials();
    this._lights();
    this._sky();

    this.procGroup = new THREE.Group();
    this.procGroup.name = 'procedural';
    this.scene.add(this.procGroup);
    buildGround(this.procGroup);
    buildGate(this.procGroup);
    buildLion(this.procGroup, -2.6, 16.3, 1);
    buildLion(this.procGroup, 2.6, 16.3, -1);
    buildCloudWall(this.procGroup, 7.5, 15.5, -8.4, 1);
    buildCloudWall(this.procGroup, 7.5, 15.5, 8.4, -1);
    buildHall(this.procGroup);
    buildWorkshop(this.procGroup);
    buildPavilion(this.procGroup);
    buildRockery(this.procGroup);
    buildBamboo(this.procGroup, -6.4, 6.2, 9);
    buildBamboo(this.procGroup, 6.6, 6.6, 7);
    buildBamboo(this.procGroup, -5.6, -8.2, 6);
    buildTree(this.procGroup, -12, 6, 1.2);
    buildTree(this.procGroup, 12.5, 7, 1.1);
    buildTree(this.procGroup, -11, -6, 1.0);
    buildTree(this.procGroup, 11.5, -9, 1.15);

    this.pathGroup = new THREE.Group();
    this.pathGroup.visible = false;
    this.scene.add(this.pathGroup);

    this._bindResize();
    this._animate = this._animate.bind(this);
    this.renderer.setAnimationLoop(this._animate);
  }

  _sky() {
    // 渐变天空球
    const geo = new THREE.SphereGeometry(180, 32, 16);
    const mat = new THREE.ShaderMaterial({
      side: THREE.BackSide,
      uniforms: {
        top: { value: new THREE.Color(0x6f93a8) },
        bottom: { value: new THREE.Color(0xdfd7c4) },
        offset: { value: 20 },
        exponent: { value: 0.85 },
      },
      vertexShader: 'varying vec3 vWorld; void main(){ vWorld = (modelMatrix*vec4(position,1.0)).xyz; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
      fragmentShader: 'uniform vec3 top; uniform vec3 bottom; uniform float offset; uniform float exponent; varying vec3 vWorld; void main(){ float h = normalize(vWorld + vec3(0.0, offset, 0.0)).y; gl_FragColor = vec4(mix(bottom, top, pow(max(h,0.0), exponent)), 1.0); }',
    });
    this.scene.add(new THREE.Mesh(geo, mat));
  }

  _lights() {
    const hemi = new THREE.HemisphereLight(0xdfeaf2, 0x5a5a4a, 1.15);
    this.scene.add(hemi);
    const sun = new THREE.DirectionalLight(0xfff2dc, 2.0);
    sun.position.set(18, 28, 16);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = -30;
    sun.shadow.camera.right = 30;
    sun.shadow.camera.top = 30;
    sun.shadow.camera.bottom = -30;
    sun.shadow.camera.near = 1;
    sun.shadow.camera.far = 90;
    sun.shadow.bias = -0.0008;
    this.scene.add(sun);
    this.sun = sun;
    const fill = new THREE.DirectionalLight(0xbcd0e0, 0.5);
    fill.position.set(-16, 12, -20);
    this.scene.add(fill);
  }

  // ---------- GLB（Blender 产出）----------
  async tryLoadGLB(url) {
    return new Promise((resolve) => {
      const loader = new GLTFLoader();
      loader.load(url, (gltf) => {
        const root = gltf.scene;
        root.name = 'aotai_glb';
        // Blender +Y（门前）导出后是 glTF -Z，绕 Y 转 180° 让它朝 +Z（与 map.json 一致）
        root.rotation.y = Math.PI;
        root.traverse((o) => {
          if (o.isMesh) {
            o.castShadow = true;
            o.receiveShadow = true;
            // Blender 文字平面导出后 U 轴反向 -> 在 three 里水平翻转贴图
            const mats = Array.isArray(o.material) ? o.material : [o.material];
            for (const m of mats) {
              if (!m) continue;
              const name = (m.name || '') + (o.name || '');
              if (/TEX_|plaque|text|couplet/i.test(m.name || '') && m.map) {
                // Blender 平面导出后纹理 U 轴反向：运行时水平镜像，正面才是正读
                m.map.wrapS = THREE.RepeatWrapping;
                m.map.repeat.x = -1;
                m.map.offset.x = 1;
                m.map.needsUpdate = true;
                m.side = THREE.FrontSide;
                m.needsUpdate = true;
              }
            }
          }
        });
        // 只落地下沉，不做 XZ 居中（Blender 场景与 map.json 用同一套坐标）
        const bbox = new THREE.Box3().setFromObject(root);
        const size = new THREE.Vector3(); bbox.getSize(size);
        root.position.y -= bbox.min.y;
        this.scene.add(root);
        this.glbGroup = root;
        this.glbLoaded = true;
        console.info('[world] GLB 已加载', size.toArray().map((v) => +v.toFixed(2)));
        // Blender 场景更精细：隐藏程序化场景，只留地面接触阴影
        this.setProceduralVisible(false);
        resolve(true);
      }, undefined, (err) => {
        console.info('[world] 未找到 GLB，使用程序化场景（这是正常的）', err && err.message);
        resolve(false);
      });
    });
  }

  setProceduralVisible(v) {
    this.procGroup.visible = v;
  }

  // ---------- 小人 ----------
  addScholar() {
    const s = createScholar();
    this.scene.add(s);
    this.scholar = s;
    return s;
  }

  placeScholar(pos, faceTo) {
    if (!this.scholar) return;
    this.scholar.position.set(pos[0], pos[1], pos[2]);
    if (faceTo) {
      this.scholar.rotation.y = Math.atan2(faceTo[0] - pos[0], faceTo[2] - pos[2]);
    }
  }

  walkPath(points, speed = 1.6, onArrive) {
    if (!this.scholar) { if (onArrive) onArrive(); return; }
    const curve = new THREE.CatmullRomCurve3(
      points.map((p) => new THREE.Vector3(p[0], p[1], p[2])), false, 'catmullrom', 0.35
    );
    const len = curve.getLength();
    const dur = Math.max(0.6, len / speed);
    this.walk = { curve, t: 0, dur, onArrive, len };
    this.scholar.userData.moving = true;
  }

  stopWalk() {
    if (this.walk && this.walk.onArrive) {
      const cb = this.walk.onArrive;
      this.walk = null;
      this.scholar.userData.moving = false;
      cb();
    } else {
      this.walk = null;
      if (this.scholar) this.scholar.userData.moving = false;
    }
  }

  setPathVisible(v) {
    this.pathVisible = v;
    this.pathGroup.visible = v;
  }

  showPath(points) {
    while (this.pathGroup.children.length) {
      const c = this.pathGroup.children.pop();
      c.geometry && c.geometry.dispose();
    }
    if (!points || points.length < 2) return;
    const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(p[0], p[1] + 0.06, p[2])), false, 'catmullrom', 0.35);
    const geo = new THREE.TubeGeometry(curve, 80, 0.055, 6, false);
    const mat = new THREE.MeshBasicMaterial({ color: 0xd9b45b, transparent: true, opacity: 0.85 });
    this.pathGroup.add(new THREE.Mesh(geo, mat));
    for (const p of points) {
      const d = new THREE.Mesh(new THREE.SphereGeometry(0.16, 10, 8), new THREE.MeshBasicMaterial({ color: 0xf2d489 }));
      d.position.set(p[0], p[1] + 0.1, p[2]);
      this.pathGroup.add(d);
    }
  }

  /** 让相机跟随小人（走路时用）；offset 为相对小人的相机偏移 */
  followActor(offset) {
    this.follow = offset ? new THREE.Vector3(offset[0], offset[1], offset[2]) : null;
  }

  // ---------- 相机 ----------
  setCameraPreset(preset) {
    if (!preset) return;
    const from = preset.from || [16, 12, 30];
    const look = preset.look || [0, 2, 0];
    this.camTween = {
      from: this.camera.position.clone(),
      to: new THREE.Vector3(from[0], from[1], from[2]),
      lookFrom: this.orbit ? this.orbit.target.clone() : new THREE.Vector3(0, 2, 0),
      lookTo: new THREE.Vector3(look[0], look[1], look[2]),
      t: 0, dur: 1.1,
    };
  }

  setOrbitTarget(v) {
    if (this.orbit) this.orbit.target.set(v[0], v[1], v[2]);
  }

  _bindResize() {
    const onResize = () => {
      const w = this.container.clientWidth || window.innerWidth;
      const h = this.container.clientHeight || window.innerHeight;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h, false);
    };
    this._onResize = onResize;
    window.addEventListener('resize', onResize);
    onResize();
  }

  _animate() {
    const dt = Math.min(this.clock.getDelta(), 0.05);
    const t = this.clock.elapsedTime;

    // 走路
    if (this.walk && this.scholar) {
      this.walk.t += dt;
      const k = Math.min(1, this.walk.t / this.walk.dur);
      const eased = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      const pos = this.walk.curve.getPointAt(Math.min(0.9999, eased));
      const ahead = this.walk.curve.getPointAt(Math.min(0.9999, Math.min(1, eased + 0.02)));
      this.scholar.position.copy(pos);
      const ang = Math.atan2(ahead.x - pos.x, ahead.z - pos.z);
      // 朝向插值
      let diff = ang - this.scholar.rotation.y;
      while (diff > Math.PI) diff -= Math.PI * 2;
      while (diff < -Math.PI) diff += Math.PI * 2;
      this.scholar.rotation.y += diff * Math.min(1, dt * 8);
      const ud = this.scholar.userData;
      ud.walkPhase += dt * 9;
      ud.body.position.y = Math.abs(Math.sin(ud.walkPhase)) * 0.06;
      ud.body.rotation.z = Math.sin(ud.walkPhase) * 0.03;
      ud.armL.rotation.x = Math.sin(ud.walkPhase) * 0.55;
      ud.armR.rotation.x = -Math.sin(ud.walkPhase) * 0.55;
      ud.legL.rotation.x = Math.sin(ud.walkPhase) * 0.7;
      ud.legR.rotation.x = -Math.sin(ud.walkPhase) * 0.7;
      if (k >= 1) {
        const cb = this.walk.onArrive;
        this.walk = null;
        ud.moving = false;
        ud.body.position.y = 0;
        ud.body.rotation.z = 0;
        ud.armL.rotation.x = 0; ud.armR.rotation.x = 0;
        ud.legL.rotation.x = 0; ud.legR.rotation.x = 0;
        if (cb) cb();
      }
    } else if (this.scholar) {
      const ud = this.scholar.userData;
      ud.body.position.y = Math.sin(t * 1.6) * 0.012;
      ud.armL.rotation.x = Math.sin(t * 1.2) * 0.05 - 0.05;
      ud.armR.rotation.x = -Math.sin(t * 1.2) * 0.05 + 0.05;
    }

    // 跟随小人（平滑，不打断用户旋转/缩放）
    if (this.follow && this.scholar && this.orbit) {
      const target = new THREE.Vector3(
        this.scholar.position.x,
        this.scholar.position.y + 1.15,
        this.scholar.position.z
      );
      const cur = this.orbit.target.clone();
      const next = cur.clone().lerp(target, Math.min(1, dt * 3.2));
      const delta = next.clone().sub(cur);
      this.orbit.target.copy(next);
      this.camera.position.add(delta);
      // 相机与目标的距离保持在期望值附近
      const desired = this.follow.clone();
      const dir = this.camera.position.clone().sub(next);
      const dist = dir.length();
      const wantDist = desired.length();
      if (Math.abs(dist - wantDist) > 2.5) {
        dir.setLength(dist + (wantDist - dist) * Math.min(1, dt * 1.6));
        this.camera.position.copy(next.clone().add(dir));
      }
      if (this.camTween) this.camTween = null;
    }

    // 相机
    if (this.orbit) {
      this.orbit.update();
    }
    if (this.camTween) {
      this.camTween.t += dt;
      const k = Math.min(1, this.camTween.t / this.camTween.dur);
      const e = 1 - Math.pow(1 - k, 3);
      const p = this.camTween.from.clone().lerp(this.camTween.to, e);
      this.camera.position.copy(p);
      const look = this.camTween.lookFrom.clone().lerp(this.camTween.lookTo, e);
      if (this.orbit) this.orbit.target.copy(look);
      this.camera.lookAt(look);
      if (k >= 1) this.camTween = null;
    } else if (!this.orbit) {
      this.camera.lookAt(0, 2, 0);
    }

    // 灯光呼吸
    for (const l of this.lanternLights) {
      l.intensity = 0.85 + Math.sin(t * 2 + l.userData.ph) * 0.12;
    }

    this.renderer.render(this.scene, this.camera);
  }

  dispose() {
    window.removeEventListener('resize', this._onResize);
    this.renderer.setAnimationLoop(null);
    this.renderer.dispose();
  }
}

export { FALLBACK_MAP };
