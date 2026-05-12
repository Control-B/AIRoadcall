"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Store,
  Megaphone,
  BarChart3,
  Settings,
  Wrench,
  ChevronLeft,
  LogOut,
  Loader2,
  Mail,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { isAuthenticated, getUsername, logout } from "@/lib/admin-auth";
import { BrandMark } from "@/components/BrandMark";

const navItems = [
  { href: "/admin", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/admin/mechanics", icon: Wrench, label: "Mechanics" },
  { href: "/admin/leads", icon: Mail, label: "Email List" },
  { href: "/admin/shops", icon: Store, label: "Shops" },
  { href: "/admin/outreach", icon: Megaphone, label: "Outreach" },
  { href: "/admin/analytics", icon: BarChart3, label: "Analytics" },
  { href: "/admin/settings", icon: Settings, label: "Settings" },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [username, setUsername] = useState<string | null>(null);

  useEffect(() => {
    // Skip auth check on the login page itself
    if (pathname === "/admin/login") {
      setAuthed(true); // let the login page render without sidebar
      return;
    }

    if (!isAuthenticated()) {
      router.replace("/admin/login");
    } else {
      setAuthed(true);
      setUsername(getUsername());
    }
  }, [pathname, router]);

  // Login page — render without sidebar
  if (pathname === "/admin/login") {
    return <>{children}</>;
  }

  // Loading state while checking auth
  if (authed === null) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-roadcall-muted" />
      </div>
    );
  }

  async function handleLogout() {
    await logout();
    router.push("/admin/login");
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-roadcall-ink text-white flex flex-col shrink-0">
        <div className="p-6 border-b border-slate-800">
          <Link href="/admin" aria-label="Roadcall.ai admin dashboard" className="inline-flex items-center">
            <BrandMark width={170} height={56} />
          </Link>
          <p className="text-xs text-roadcall-muted mt-1">Admin Dashboard</p>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/admin" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-roadcall-silver/85 hover:bg-roadcall-panel hover:text-white"
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-800 space-y-3">
          {username && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-roadcall-silver/85 truncate">
                {username}
              </span>
              <button
                onClick={handleLogout}
                className="text-roadcall-muted hover:text-white transition-colors"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
          <Link
            href="/demo"
            className="flex items-center gap-2 text-sm text-roadcall-muted hover:text-white transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            View Demo Page
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
