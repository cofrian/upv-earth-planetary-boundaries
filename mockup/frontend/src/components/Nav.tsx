"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Dashboard", description: "Panel ejecutivo" },
  { href: "/analysis", label: "Análisis exploratorio", description: "AED del corpus" },
  { href: "/papers", label: "Explorar corpus", description: "Tabla de papers" },
  { href: "/upload", label: "Subir paper", description: "PDF → SPECTER2" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 border-b border-line/70 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-4 lg:flex-row lg:items-center lg:justify-between lg:px-10">
        <Link href="/dashboard" className="group flex items-center gap-4">
          <Image
            src="/etsinf-logo.svg"
            alt="ETSINF — Escola Tècnica Superior d'Enginyeria Informàtica"
            width={340}
            height={148}
            priority
            className="h-12 w-auto"
          />
          <span className="hidden h-9 w-px bg-line sm:inline-block" aria-hidden />
          <Image
            src="/upv-logo.svg"
            alt="Universitat Politècnica de València"
            width={300}
            height={90}
            priority
            className="hidden h-10 w-auto sm:block"
          />
          <span className="hidden h-9 w-px bg-line lg:inline-block" aria-hidden />
          <div className="hidden lg:block">
            <p className="text-base font-semibold tracking-tight text-textMain">UPV-EARTH</p>
            <p className="text-[11px] uppercase tracking-[0.22em] text-textMuted">
              Planetary Boundaries Lab
            </p>
          </div>
        </Link>

        <nav className="flex flex-wrap items-center gap-1.5 rounded-2xl border border-line bg-surface-1 p-1">
          {links.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                title={item.description}
                className={`rounded-xl px-3.5 py-2 text-sm font-medium transition ${
                  active
                    ? "bg-emerald-500 text-white shadow-emerald"
                    : "text-textSubtle hover:bg-surface-2 hover:text-textMain"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
