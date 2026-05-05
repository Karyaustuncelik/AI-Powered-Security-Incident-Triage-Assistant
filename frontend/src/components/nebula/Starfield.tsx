// Canvas 2D — Cinematic cosmic starfield with nebula clouds, shooting stars, and parallax.
import { useEffect, useRef } from "react";

type Star = {
  x: number;
  y: number;
  z: number;
  baseZ: number;
  hue: number;
  twinkle: number;
};

type ShootingStar = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  hue: number;
};

type Props = {
  density?: number;
  warp?: number;
  interactive?: boolean;
  shootingStars?: boolean;
};

export function Starfield({
  density = 0.5,
  warp = 0.008,
  interactive = true,
  shootingStars = true,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const starsRef = useRef<Star[]>([]);
  const shootingRef = useRef<ShootingStar[]>([]);
  const mouseRef = useRef({ x: 0, y: 0, tx: 0, ty: 0 });
  const sizeRef = useRef({ w: 0, h: 0, dpr: 1 });
  const frameRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const makeStar = (w: number, h: number): Star => {
      const z = 1 + Math.random() * 9;
      return {
        x: (Math.random() - 0.5) * w * 2.5,
        y: (Math.random() - 0.5) * h * 2.5,
        z,
        baseZ: z,
        hue: 190 + Math.random() * 100,
        twinkle: Math.random() * Math.PI * 2,
      };
    };

    const makeShootingStar = (w: number, h: number): ShootingStar => {
      const angle = Math.PI * 0.15 + Math.random() * 0.3;
      const speed = 6 + Math.random() * 8;
      return {
        x: Math.random() * w * 0.8,
        y: Math.random() * h * 0.4,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 0,
        maxLife: 40 + Math.random() * 30,
        hue: 190 + Math.random() * 50,
      };
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = window.innerWidth;
      const h = window.innerHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      sizeRef.current = { w, h, dpr };

      const area = w * h;
      const count = Math.floor((area / 1000) * density);
      const stars: Star[] = [];
      for (let i = 0; i < count; i++) {
        stars.push(makeStar(w, h));
      }
      starsRef.current = stars;
    };

    const onMouse = (e: MouseEvent) => {
      if (!interactive) return;
      const { innerWidth: w, innerHeight: h } = window;
      mouseRef.current.tx = (e.clientX / w - 0.5) * 2;
      mouseRef.current.ty = (e.clientY / h - 0.5) * 2;
    };

    resize();
    window.addEventListener("resize", resize);
    if (interactive) window.addEventListener("mousemove", onMouse);

    const render = () => {
      frameRef.current++;
      const { w, h } = sizeRef.current;
      const m = mouseRef.current;
      m.x += (m.tx - m.x) * 0.035;
      m.y += (m.ty - m.y) * 0.035;

      // Clear with trail effect
      ctx.fillStyle = "rgba(3, 7, 18, 0.25)";
      ctx.fillRect(0, 0, w, h);

      // Nebula clouds
      drawNebula(ctx, w, h, m);

      // Stars
      const cx = w / 2;
      const cy = h / 2;
      const stars = starsRef.current;

      for (let i = 0; i < stars.length; i++) {
        const s = stars[i];
        s.z -= warp;
        if (s.z <= 0.3) {
          const fresh = makeStar(w, h);
          s.x = fresh.x;
          s.y = fresh.y;
          s.z = 8 + Math.random() * 2;
          s.baseZ = s.z;
          s.hue = fresh.hue;
          s.twinkle = fresh.twinkle;
          continue;
        }
        s.twinkle += 0.04;

        const k = 200 / s.z;
        const px = cx + s.x * k * 0.01 + m.x * 25 * (1 / s.z);
        const py = cy + s.y * k * 0.01 + m.y * 25 * (1 / s.z);
        const radius = Math.max(0.2, (10 - s.z) * 0.3);
        const alpha = 0.3 + 0.7 * Math.max(0, (10 - s.z) / 10) * (0.6 + 0.4 * Math.sin(s.twinkle));

        // Warp streak for near stars
        if (s.z < 2.5) {
          const prevK = 200 / (s.z + warp * 3);
          const ppx = cx + s.x * prevK * 0.01 + m.x * 25 * (1 / (s.z + warp * 3));
          const ppy = cy + s.y * prevK * 0.01 + m.y * 25 * (1 / (s.z + warp * 3));
          ctx.strokeStyle = `hsla(${s.hue}, 85%, 75%, ${alpha * 0.5})`;
          ctx.lineWidth = radius * 0.8;
          ctx.beginPath();
          ctx.moveTo(ppx, ppy);
          ctx.lineTo(px, py);
          ctx.stroke();
        }

        // Star glow
        if (s.z < 4) {
          const glowR = radius * 3;
          const g = ctx.createRadialGradient(px, py, 0, px, py, glowR);
          g.addColorStop(0, `hsla(${s.hue}, 90%, 80%, ${alpha * 0.25})`);
          g.addColorStop(1, `hsla(${s.hue}, 90%, 80%, 0)`);
          ctx.fillStyle = g;
          ctx.beginPath();
          ctx.arc(px, py, glowR, 0, Math.PI * 2);
          ctx.fill();
        }

        ctx.fillStyle = `hsla(${s.hue}, 85%, 85%, ${alpha})`;
        ctx.beginPath();
        ctx.arc(px, py, radius, 0, Math.PI * 2);
        ctx.fill();
      }

      // Shooting stars
      if (shootingStars && frameRef.current % 120 === 0 && Math.random() > 0.5) {
        shootingRef.current.push(makeShootingStar(w, h));
      }

      const shooting = shootingRef.current;
      for (let i = shooting.length - 1; i >= 0; i--) {
        const ss = shooting[i];
        ss.x += ss.vx;
        ss.y += ss.vy;
        ss.life++;

        const progress = ss.life / ss.maxLife;
        const alpha = progress < 0.3 ? progress / 0.3 : 1 - (progress - 0.3) / 0.7;
        const tailLen = 40 + progress * 30;

        ctx.strokeStyle = `hsla(${ss.hue}, 90%, 80%, ${alpha * 0.8})`;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(ss.x, ss.y);
        ctx.lineTo(ss.x - ss.vx / Math.abs(ss.vx) * tailLen * (ss.vx / Math.abs(ss.vx)),
                   ss.y - ss.vy / Math.abs(ss.vy) * tailLen * (ss.vy / Math.abs(ss.vy)));
        ctx.stroke();

        // Glow
        const glowG = ctx.createRadialGradient(ss.x, ss.y, 0, ss.x, ss.y, 8);
        glowG.addColorStop(0, `hsla(${ss.hue}, 90%, 90%, ${alpha * 0.6})`);
        glowG.addColorStop(1, `hsla(${ss.hue}, 90%, 90%, 0)`);
        ctx.fillStyle = glowG;
        ctx.beginPath();
        ctx.arc(ss.x, ss.y, 8, 0, Math.PI * 2);
        ctx.fill();

        if (ss.life >= ss.maxLife) {
          shooting.splice(i, 1);
        }
      }

      rafRef.current = requestAnimationFrame(render);
    };

    rafRef.current = requestAnimationFrame(render);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMouse);
    };
  }, [density, warp, interactive, shootingStars]);

  return <canvas ref={canvasRef} className="nb-starfield" aria-hidden="true" />;
}

function drawNebula(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  m: { x: number; y: number },
) {
  const now = Date.now() / 1000;

  // Purple nebula cloud
  const cx1 = w * 0.2 + Math.sin(now * 0.08) * 60 - m.x * 30;
  const cy1 = h * 0.25 + Math.cos(now * 0.1) * 40 - m.y * 30;
  const g1 = ctx.createRadialGradient(cx1, cy1, 0, cx1, cy1, Math.max(w, h) * 0.6);
  g1.addColorStop(0, "rgba(139, 92, 246, 0.14)");
  g1.addColorStop(0.3, "rgba(139, 92, 246, 0.05)");
  g1.addColorStop(1, "rgba(139, 92, 246, 0)");
  ctx.fillStyle = g1;
  ctx.fillRect(0, 0, w, h);

  // Cyan nebula cloud
  const cx2 = w * 0.8 + Math.cos(now * 0.06) * 50 - m.x * 35;
  const cy2 = h * 0.6 + Math.sin(now * 0.09) * 35 - m.y * 35;
  const g2 = ctx.createRadialGradient(cx2, cy2, 0, cx2, cy2, Math.max(w, h) * 0.5);
  g2.addColorStop(0, "rgba(34, 211, 238, 0.1)");
  g2.addColorStop(0.4, "rgba(34, 211, 238, 0.03)");
  g2.addColorStop(1, "rgba(34, 211, 238, 0)");
  ctx.fillStyle = g2;
  ctx.fillRect(0, 0, w, h);

  // Pink accent cloud
  const cx3 = w * 0.55 + Math.sin(now * 0.07) * 45 - m.x * 25;
  const cy3 = h * 0.15 + Math.cos(now * 0.11) * 30 - m.y * 25;
  const g3 = ctx.createRadialGradient(cx3, cy3, 0, cx3, cy3, Math.max(w, h) * 0.35);
  g3.addColorStop(0, "rgba(236, 72, 153, 0.08)");
  g3.addColorStop(0.5, "rgba(236, 72, 153, 0.02)");
  g3.addColorStop(1, "rgba(236, 72, 153, 0)");
  ctx.fillStyle = g3;
  ctx.fillRect(0, 0, w, h);
}
