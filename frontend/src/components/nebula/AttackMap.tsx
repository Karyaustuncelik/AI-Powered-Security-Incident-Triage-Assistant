// 3D Attack Map — Canvas 2D world map with animated attack vectors and geo-correlation.

import { useEffect, useRef, useState, useCallback } from "react";

type AttackEvent = {
  id: string;
  sourceCity: string;
  sourceLat: number;
  sourceLon: number;
  targetCity: string;
  targetLat: number;
  targetLon: number;
  type: string;
  severity: "critical" | "high" | "medium" | "low";
  timestamp: number;
  progress: number; // 0..1 animation progress
  active: boolean;
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f59e0b",
  medium: "#3b82f6",
  low: "#10b981",
};

// Simplified world map points (lat, lon pairs for continent outlines)
const WORLD_POINTS: [number, number][][] = [
  // North America
  [[-130,50],[-125,55],[-120,60],[-115,62],[-100,62],[-90,55],[-80,45],[-75,40],[-70,42],[-67,45],[-65,47],[-60,48],[-55,50],[-80,25],[-85,30],[-90,30],[-95,27],[-100,20],[-105,20],[-110,25],[-115,30],[-120,35],[-125,42],[-130,50]],
  // South America
  [[-80,10],[-75,5],[-70,5],[-60,0],[-50,-2],[-45,-5],[-40,-10],[-38,-15],[-40,-22],[-45,-25],[-50,-28],[-55,-33],[-58,-38],[-65,-45],[-70,-50],[-75,-48],[-75,-40],[-70,-18],[-75,-10],[-78,-5],[-80,0],[-80,10]],
  // Europe
  [[-10,36],[-5,36],[0,38],[5,43],[10,44],[15,45],[20,42],[25,40],[30,42],[28,45],[25,48],[20,50],[18,55],[22,58],[28,60],[30,65],[25,68],[20,68],[15,63],[10,58],[5,52],[0,50],[-5,44],[-10,36]],
  // Africa
  [[-15,12],[-17,15],[-15,28],[-5,36],[10,37],[15,33],[25,32],[30,30],[35,30],[40,12],[42,2],[40,-5],[35,-15],[30,-25],[28,-33],[25,-34],[20,-33],[18,-28],[15,-18],[12,-10],[8,-5],[5,5],[0,6],[-5,5],[-10,8],[-15,12]],
  // Asia
  [[30,42],[35,38],[40,38],[45,40],[50,42],[55,45],[60,42],[65,40],[70,35],[75,30],[80,28],[85,28],[90,25],[95,22],[100,20],[105,22],[110,20],[115,23],[120,25],[125,30],[130,35],[135,40],[140,42],[145,45],[140,50],[135,55],[130,58],[120,55],[110,52],[100,50],[90,52],[80,55],[70,60],[65,58],[60,55],[55,52],[50,48],[45,45],[40,42],[30,42]],
  // Australia
  [[115,-35],[118,-32],[122,-18],[130,-15],[135,-12],[140,-15],[145,-15],[150,-18],[153,-25],[152,-30],[150,-35],[145,-38],[140,-38],[135,-35],[130,-32],[125,-33],[118,-35],[115,-35]],
];

// Major cities for attack origins/targets
const CITIES: { name: string; lat: number; lon: number }[] = [
  { name: "New York", lat: 40.7, lon: -74.0 },
  { name: "London", lat: 51.5, lon: -0.1 },
  { name: "Moscow", lat: 55.7, lon: 37.6 },
  { name: "Beijing", lat: 39.9, lon: 116.4 },
  { name: "Tokyo", lat: 35.7, lon: 139.7 },
  { name: "São Paulo", lat: -23.5, lon: -46.6 },
  { name: "Sydney", lat: -33.9, lon: 151.2 },
  { name: "Dubai", lat: 25.2, lon: 55.3 },
  { name: "Singapore", lat: 1.3, lon: 103.8 },
  { name: "Mumbai", lat: 19.1, lon: 72.9 },
  { name: "Berlin", lat: 52.5, lon: 13.4 },
  { name: "Lagos", lat: 6.5, lon: 3.4 },
  { name: "Seoul", lat: 37.6, lon: 127.0 },
  { name: "Istanbul", lat: 41.0, lon: 28.9 },
  { name: "Toronto", lat: 43.7, lon: -79.4 },
  { name: "San Francisco", lat: 37.8, lon: -122.4 },
  { name: "Amsterdam", lat: 52.4, lon: 4.9 },
  { name: "Tehran", lat: 35.7, lon: 51.4 },
  { name: "Pyongyang", lat: 39.0, lon: 125.7 },
  { name: "Taipei", lat: 25.0, lon: 121.5 },
];

const ATTACK_TYPES = [
  "Brute Force", "SQL Injection", "DDoS", "Phishing", "Ransomware",
  "XSS", "RCE", "Credential Stuffing", "Port Scan", "APT Activity",
  "Zero-Day Exploit", "Supply Chain", "Man-in-the-Middle", "DNS Hijack",
];

const SEVERITIES: ("critical" | "high" | "medium" | "low")[] = ["critical", "high", "medium", "low"];

function randomCity() {
  return CITIES[Math.floor(Math.random() * CITIES.length)];
}

function generateAttack(): AttackEvent {
  let source = randomCity();
  let target = randomCity();
  while (target.name === source.name) target = randomCity();
  const sevWeights = [0.1, 0.25, 0.4, 0.25]; // crit, high, med, low
  const r = Math.random();
  let sevIdx = 0;
  let cum = 0;
  for (let i = 0; i < sevWeights.length; i++) {
    cum += sevWeights[i];
    if (r < cum) { sevIdx = i; break; }
  }
  return {
    id: Math.random().toString(36).slice(2, 10),
    sourceCity: source.name,
    sourceLat: source.lat,
    sourceLon: source.lon,
    targetCity: target.name,
    targetLat: target.lat,
    targetLon: target.lon,
    type: ATTACK_TYPES[Math.floor(Math.random() * ATTACK_TYPES.length)],
    severity: SEVERITIES[sevIdx],
    timestamp: Date.now(),
    progress: 0,
    active: true,
  };
}

function lonLatToXY(lon: number, lat: number, w: number, h: number, ox: number, oy: number): [number, number] {
  const x = ox + ((lon + 180) / 360) * w;
  const y = oy + ((90 - lat) / 180) * h;
  return [x, y];
}

export function AttackMap() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number>(0);
  const attacksRef = useRef<AttackEvent[]>([]);
  const [stats, setStats] = useState({ total: 0, critical: 0, high: 0, medium: 0, low: 0 });
  const [recentAttacks, setRecentAttacks] = useState<AttackEvent[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const pausedRef = useRef(false);
  const frameRef = useRef(0);

  const updateStats = useCallback(() => {
    const attacks = attacksRef.current;
    setStats({
      total: attacks.length,
      critical: attacks.filter(a => a.severity === "critical").length,
      high: attacks.filter(a => a.severity === "high").length,
      medium: attacks.filter(a => a.severity === "medium").length,
      low: attacks.filter(a => a.severity === "low").length,
    });
    setRecentAttacks(attacks.slice(-5).reverse());
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      const w = rect?.width || 900;
      const h = Math.max(500, (rect?.height || 500));
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    window.addEventListener("resize", resize);

    // Seed initial attacks
    for (let i = 0; i < 8; i++) {
      const a = generateAttack();
      a.progress = Math.random();
      a.timestamp = Date.now() - Math.random() * 30000;
      attacksRef.current.push(a);
    }
    updateStats();

    const render = () => {
      frameRef.current++;
      const w = canvas.width / (Math.min(window.devicePixelRatio || 1, 2));
      const h = canvas.height / (Math.min(window.devicePixelRatio || 1, 2));

      // Clear
      ctx.fillStyle = "rgba(3, 7, 18, 0.15)";
      ctx.fillRect(0, 0, w, h);

      // Map dimensions
      const mapPad = 40;
      const mapW = w - mapPad * 2;
      const mapH = h - mapPad * 2;

      // Draw grid
      ctx.strokeStyle = "rgba(148, 163, 184, 0.04)";
      ctx.lineWidth = 0.5;
      for (let i = 0; i <= 18; i++) {
        const x = mapPad + (i / 18) * mapW;
        ctx.beginPath(); ctx.moveTo(x, mapPad); ctx.lineTo(x, mapPad + mapH); ctx.stroke();
      }
      for (let i = 0; i <= 9; i++) {
        const y = mapPad + (i / 9) * mapH;
        ctx.beginPath(); ctx.moveTo(mapPad, y); ctx.lineTo(mapPad + mapW, y); ctx.stroke();
      }

      // Draw world map outlines
      ctx.strokeStyle = "rgba(34, 211, 238, 0.15)";
      ctx.lineWidth = 1;
      for (const continent of WORLD_POINTS) {
        ctx.beginPath();
        for (let i = 0; i < continent.length; i++) {
          const [x, y] = lonLatToXY(continent[i][0], continent[i][1], mapW, mapH, mapPad, mapPad);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fillStyle = "rgba(34, 211, 238, 0.02)";
        ctx.fill();
        ctx.stroke();
      }

      // Draw city dots
      for (const city of CITIES) {
        const [cx, cy] = lonLatToXY(city.lon, city.lat, mapW, mapH, mapPad, mapPad);
        ctx.fillStyle = "rgba(148, 163, 184, 0.3)";
        ctx.beginPath();
        ctx.arc(cx, cy, 2, 0, Math.PI * 2);
        ctx.fill();
      }

      // Generate new attacks
      if (!pausedRef.current && frameRef.current % 60 === 0) {
        attacksRef.current.push(generateAttack());
        if (attacksRef.current.length > 50) {
          attacksRef.current = attacksRef.current.slice(-50);
        }
        if (frameRef.current % 180 === 0) updateStats();
      }

      // Draw attacks
      const attacks = attacksRef.current;
      for (const attack of attacks) {
        if (!pausedRef.current) attack.progress = Math.min(1, attack.progress + 0.008);

        const [sx, sy] = lonLatToXY(attack.sourceLon, attack.sourceLat, mapW, mapH, mapPad, mapPad);
        const [tx, ty] = lonLatToXY(attack.targetLon, attack.targetLat, mapW, mapH, mapPad, mapPad);
        const color = SEVERITY_COLORS[attack.severity];

        // Source glow
        const srcGlow = ctx.createRadialGradient(sx, sy, 0, sx, sy, 12);
        srcGlow.addColorStop(0, color + "40");
        srcGlow.addColorStop(1, color + "00");
        ctx.fillStyle = srcGlow;
        ctx.beginPath();
        ctx.arc(sx, sy, 12, 0, Math.PI * 2);
        ctx.fill();

        // Source dot
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(sx, sy, 3, 0, Math.PI * 2);
        ctx.fill();

        // Arc path
        const midX = (sx + tx) / 2;
        const midY = (sy + ty) / 2 - Math.abs(tx - sx) * 0.2;

        // Draw arc trail
        const p = attack.progress;
        ctx.strokeStyle = color + "30";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.quadraticCurveTo(midX, midY, tx, ty);
        ctx.stroke();

        // Animated projectile on arc
        if (p < 1) {
          const t = p;
          const px = (1-t)*(1-t)*sx + 2*(1-t)*t*midX + t*t*tx;
          const py = (1-t)*(1-t)*sy + 2*(1-t)*t*midY + t*t*ty;

          // Projectile glow
          const projGlow = ctx.createRadialGradient(px, py, 0, px, py, 8);
          projGlow.addColorStop(0, color + "cc");
          projGlow.addColorStop(1, color + "00");
          ctx.fillStyle = projGlow;
          ctx.beginPath();
          ctx.arc(px, py, 8, 0, Math.PI * 2);
          ctx.fill();

          // Trail
          for (let i = 1; i <= 5; i++) {
            const tt = Math.max(0, t - i * 0.03);
            const trX = (1-tt)*(1-tt)*sx + 2*(1-tt)*tt*midX + tt*tt*tx;
            const trY = (1-tt)*(1-tt)*sy + 2*(1-tt)*tt*midY + tt*tt*ty;
            ctx.fillStyle = color + (Math.floor(30 - i * 5)).toString(16).padStart(2, '0');
            ctx.beginPath();
            ctx.arc(trX, trY, 3 - i * 0.4, 0, Math.PI * 2);
            ctx.fill();
          }
        }

        // Target pulse when hit
        if (p >= 0.95) {
          const pulseAlpha = 1 - (p - 0.95) / 0.05;
          const pulseR = 5 + (1 - pulseAlpha) * 20;
          ctx.strokeStyle = color + Math.floor(pulseAlpha * 100).toString(16).padStart(2, '0');
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(tx, ty, pulseR, 0, Math.PI * 2);
          ctx.stroke();
        }

        // Target dot
        ctx.fillStyle = p >= 0.95 ? color : "rgba(148, 163, 184, 0.3)";
        ctx.beginPath();
        ctx.arc(tx, ty, 3, 0, Math.PI * 2);
        ctx.fill();
      }

      rafRef.current = requestAnimationFrame(render);
    };

    rafRef.current = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", resize);
    };
  }, [updateStats]);

  useEffect(() => {
    pausedRef.current = isPaused;
  }, [isPaused]);

  return (
    <div className="attack-map-container">
      {/* Stats bar */}
      <div className="attack-map-stats">
        <div className="attack-map-stat">
          <span className="attack-map-stat-value">{stats.total}</span>
          <span className="attack-map-stat-label">Total Attacks</span>
        </div>
        <div className="attack-map-stat">
          <span className="attack-map-stat-value" style={{ color: SEVERITY_COLORS.critical }}>{stats.critical}</span>
          <span className="attack-map-stat-label">Critical</span>
        </div>
        <div className="attack-map-stat">
          <span className="attack-map-stat-value" style={{ color: SEVERITY_COLORS.high }}>{stats.high}</span>
          <span className="attack-map-stat-label">High</span>
        </div>
        <div className="attack-map-stat">
          <span className="attack-map-stat-value" style={{ color: SEVERITY_COLORS.medium }}>{stats.medium}</span>
          <span className="attack-map-stat-label">Medium</span>
        </div>
        <div className="attack-map-stat">
          <span className="attack-map-stat-value" style={{ color: SEVERITY_COLORS.low }}>{stats.low}</span>
          <span className="attack-map-stat-label">Low</span>
        </div>
        <button
          className={`attack-map-toggle ${isPaused ? "paused" : ""}`}
          onClick={() => setIsPaused(!isPaused)}
        >
          {isPaused ? "▶ Resume" : "⏸ Pause"}
        </button>
      </div>

      {/* Map canvas */}
      <div className="attack-map-canvas-wrap">
        <canvas ref={canvasRef} className="attack-map-canvas" />
      </div>

      {/* Recent attacks feed */}
      <div className="attack-map-feed">
        <div className="attack-map-feed-title">
          <span className="nebula-streaming-dot" />
          Live Attack Feed
        </div>
        {recentAttacks.map((a) => (
          <div key={a.id} className="attack-map-feed-item">
            <span
              className="attack-map-feed-dot"
              style={{ background: SEVERITY_COLORS[a.severity] }}
            />
            <div className="attack-map-feed-info">
              <span className="attack-map-feed-type">{a.type}</span>
              <span className="attack-map-feed-route">
                {a.sourceCity} → {a.targetCity}
              </span>
            </div>
            <span className={`badge badge-${a.severity}`}>{a.severity}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
