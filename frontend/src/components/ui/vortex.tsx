import { useEffect, useRef } from "react";
import { cn } from "../../lib/utils";

interface VortexProps {
  children?: React.ReactNode;
  className?: string;
  containerClassName?: string;
  particleCount?: number;
  baseHue?: number;
  baseSpeed?: number;
  rangeSpeed?: number;
  baseRadius?: number;
  rangeRadius?: number;
}

function rand(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

export function Vortex({
  children,
  className,
  containerClassName,
  particleCount = 500,
  baseHue = 0,
  baseSpeed = 0,
  rangeSpeed = 1.5,
  baseRadius = 1,
  rangeRadius = 2,
}: VortexProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;

    function resize() {
      if (!canvas || !containerRef.current) return;
      canvas.width = containerRef.current.offsetWidth;
      canvas.height = containerRef.current.offsetHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    const particles = Array.from({ length: particleCount }, () => ({
      x: rand(0, canvas.width),
      y: rand(0, canvas.height),
      vx: rand(-1, 1),
      vy: rand(-1, 1),
      radius: rand(baseRadius, baseRadius + rangeRadius),
      speed: rand(baseSpeed + 0.1, baseSpeed + rangeSpeed),
      alpha: rand(0.1, 0.4),
    }));

    function draw() {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p) => {
        p.x += p.vx * p.speed;
        p.y += p.vy * p.speed;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${baseHue}, 5%, 75%, ${p.alpha})`;
        ctx.fill();
      });
      animId = requestAnimationFrame(draw);
    }
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
    };
  }, [particleCount, baseHue, baseSpeed, rangeSpeed, baseRadius, rangeRadius]);

  return (
    <div ref={containerRef} className={cn("relative overflow-hidden", containerClassName)}>
      <canvas ref={canvasRef} className="absolute inset-0 z-0 pointer-events-none" />
      <div className={cn("relative z-10", className)}>{children}</div>
    </div>
  );
}
