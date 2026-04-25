const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const scoreEl = document.getElementById('score');
const highEl = document.getElementById('high');
const assistantLine = document.getElementById('assistantLine');
const restartBtn = document.getElementById('restartBtn');

const ROAD_LEFT = 230;
const ROAD_RIGHT = 670;
const CAR_W = 45;
const CAR_H = 70;

let tiltY = 0;
let score = 0;
let highScore = 0;
let gameOver = false;
let speed = 5;
let roadOffset = 0;
let obstacleTick = 0;

const car = { x: (ROAD_LEFT + ROAD_RIGHT) / 2 - CAR_W / 2, y: 400, w: CAR_W, h: CAR_H };
const obstacles = [];

function setAssistant(text) {
  if (text) assistantLine.textContent = `Assistant: ${text}`;
}

async function fetchComment(eventName) {
  try {
    const res = await fetch('/game/comment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event: eventName, score })
    });
    const data = await res.json();
    if (data.comment) setAssistant(data.comment);
  } catch (_) {}
}

function spawnObstacle() {
  const laneWidth = (ROAD_RIGHT - ROAD_LEFT) / 3;
  const lane = Math.floor(Math.random() * 3);
  obstacles.push({
    x: ROAD_LEFT + lane * laneWidth + laneWidth / 2 - 22,
    y: -80,
    w: 44,
    h: 70
  });
}

function drawRoad() {
  ctx.fillStyle = '#1f2a36';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#2a3442';
  ctx.fillRect(ROAD_LEFT, 0, ROAD_RIGHT - ROAD_LEFT, canvas.height);

  ctx.strokeStyle = '#f8f0c8';
  ctx.lineWidth = 4;
  for (let i = -1; i < 12; i++) {
    const y = ((i * 60) + roadOffset) % (canvas.height + 60);
    ctx.beginPath();
    ctx.moveTo((ROAD_LEFT + ROAD_RIGHT) / 2, y);
    ctx.lineTo((ROAD_LEFT + ROAD_RIGHT) / 2, y + 30);
    ctx.stroke();
  }
}

function drawCar() {
  ctx.fillStyle = '#68e1ff';
  ctx.fillRect(car.x, car.y, car.w, car.h);
  ctx.fillStyle = '#baf2ff';
  ctx.fillRect(car.x + 8, car.y + 8, car.w - 16, 16);
}

function drawObstacles() {
  ctx.fillStyle = '#ff5a5a';
  obstacles.forEach(o => ctx.fillRect(o.x, o.y, o.w, o.h));
}

function collides(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

function update() {
  if (gameOver) return;

  roadOffset += speed;
  score += 1;
  speed = Math.min(11, 5 + score / 600);
  scoreEl.textContent = score;

  const steering = Math.max(-1, Math.min(1, -tiltY));
  car.x += steering * 8;

  if (car.x < ROAD_LEFT) car.x = ROAD_LEFT;
  if (car.x + car.w > ROAD_RIGHT) car.x = ROAD_RIGHT - car.w;

  obstacleTick += 1;
  if (obstacleTick > 35) {
    spawnObstacle();
    obstacleTick = 0;
  }

  for (let i = obstacles.length - 1; i >= 0; i--) {
    const o = obstacles[i];
    o.y += speed;

    if (collides(car, o)) {
      gameOver = true;
      fetchComment('game_over');
      if (score > highScore) {
        highScore = score;
        highEl.textContent = highScore;
        setAssistant(`New high score. ${highScore}.`);
      }
      return;
    }

    if (o.y > canvas.height + 90) {
      obstacles.splice(i, 1);
      if (Math.random() > 0.65) fetchComment('near_miss');
    }
  }

  if (score > 0 && score % 250 === 0) fetchComment('danger');
}

function renderGameOver() {
  if (!gameOver) return;
  ctx.fillStyle = 'rgba(0,0,0,.55)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 48px sans-serif';
  ctx.fillText('GAME OVER', 320, 230);
  ctx.font = '24px sans-serif';
  ctx.fillText(`Score: ${score}`, 390, 275);
}

function tick() {
  drawRoad();
  update();
  drawObstacles();
  drawCar();
  renderGameOver();
  requestAnimationFrame(tick);
}

function resetGame() {
  score = 0;
  gameOver = false;
  speed = 5;
  car.x = (ROAD_LEFT + ROAD_RIGHT) / 2 - CAR_W / 2;
  obstacles.length = 0;
  setAssistant('Restarted. Tilt to steer.');
}

restartBtn.addEventListener('click', resetGame);
window.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowLeft') tiltY = 0.8;
  if (e.key === 'ArrowRight') tiltY = -0.8;
  if (e.key.toLowerCase() === 'r') resetGame();
});
window.addEventListener('keyup', () => { tiltY = 0; });

const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
const ws = new WebSocket(`${wsProto}://${location.host}/sensor-stream`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  tiltY = Number(data.gyro.y || 0);
};

fetch('/game/start', { method: 'POST' })
  .then(r => r.json())
  .then(d => setAssistant(d.narration || 'Starting game...'))
  .catch(() => setAssistant('Sensor link active.'));

tick();
