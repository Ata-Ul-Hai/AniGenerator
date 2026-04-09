import React, { useRef, useState } from "react";
import { cn } from "../../lib/utils";

export const EvervaultCard: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className }) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState({});

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = cardRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const rx = (y / rect.height - 0.5) * 12;
    const ry = (x / rect.width - 0.5) * -12;
    setStyle({
      transform: `perspective(600px) rotateX(${rx}deg) rotateY(${ry}deg) scale(1.02)`,
      transition: "transform 0.1s ease",
    });
  };

  const resetStyle = () =>
    setStyle({ transform: "perspective(600px) rotateX(0) rotateY(0) scale(1)", transition: "transform 0.5s ease" });

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={resetStyle}
      style={style}
      className={cn(
        "relative rounded-2xl border border-zinc-800 bg-zinc-900/60 backdrop-blur-sm p-6 cursor-default",
        className
      )}
    >
      {children}
    </div>
  );
};
