import React from "react";
import { cn } from "../../lib/utils";

export const BentoGrid: React.FC<{
  className?: string;
  children: React.ReactNode;
}> = ({ className, children }) => (
  <div className={cn("grid grid-cols-1 md:grid-cols-3 gap-4 auto-rows-[200px]", className)}>
    {children}
  </div>
);

export const BentoGridItem: React.FC<{
  className?: string;
  title?: string;
  description?: string;
  header?: React.ReactNode;
  icon?: React.ReactNode;
}> = ({ className, title, description, header, icon }) => (
  <div
    className={cn(
      "row-span-1 rounded-2xl border border-zinc-800 bg-zinc-900/60 backdrop-blur-sm p-5",
      "flex flex-col justify-between gap-2 hover:border-zinc-600 transition-colors duration-300",
      className
    )}
  >
    {header}
    <div>
      {icon && <div className="mb-2 text-zinc-400">{icon}</div>}
      {title && <h3 className="font-semibold text-zinc-100 text-sm">{title}</h3>}
      {description && <p className="text-xs text-zinc-500 mt-1 leading-relaxed">{description}</p>}
    </div>
  </div>
);
