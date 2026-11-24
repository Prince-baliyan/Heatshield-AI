import type { ReactNode } from "react";
import { Footer } from "./Footer";
import { Navbar } from "./Navbar";

interface PlatformShellProps {
  children: ReactNode;
}

export function PlatformShell({ children }: PlatformShellProps) {
  return (
    <div className="min-h-screen text-slate-100">
      <Navbar />
      <main>{children}</main>
      <Footer />
    </div>
  );
}
