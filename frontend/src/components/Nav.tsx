"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clsx } from "clsx";
import { UserOut } from "@/lib/api";
import { clearToken } from "@/lib/auth";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/report/lost", label: "Report Lost" },
  { href: "/report/found", label: "Report Found" },
  { href: "/items", label: "My Items" },
  { href: "/search", label: "Search" },
  { href: "/notifications", label: "Notifications" },
];

export function Nav({ user, unreadCount = 0 }: { user: UserOut | null; unreadCount?: number }) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <Link href="/dashboard" className="text-lg font-semibold text-slate-900">
          FindBack AI
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={clsx(
                "relative rounded-md px-3 py-2 font-medium transition-colors",
                pathname === link.href ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
              )}
            >
              {link.label}
              {link.href === "/notifications" && unreadCount > 0 && (
                <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-lost text-[10px] font-semibold text-white">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </Link>
          ))}
          {user?.role === "Admin" && (
            <Link
              href="/admin"
              className={clsx(
                "rounded-md px-3 py-2 font-medium transition-colors",
                pathname === "/admin" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
              )}
            >
              Admin
            </Link>
          )}
          <button
            onClick={() => {
              clearToken();
              router.push("/login");
            }}
            className="ml-2 rounded-md px-3 py-2 font-medium text-slate-500 hover:bg-slate-100"
          >
            Log out
          </button>
        </nav>
      </div>
    </header>
  );
}
