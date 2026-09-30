"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { Sprout, Menu, X, Shield, LogOut, User } from "lucide-react";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { AccessibilityBar } from "./AccessibilityBar";
import { SyncStatusChip } from "@/components/ui/SyncStatusChip";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/lib/auth/store";
import { cn } from "@/lib/utils";

export function Header() {
  const params = useParams();
  const pathname = usePathname();
  const router = useRouter();
  const locale = (params?.locale as string) || "en";
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const { user, role, isAuthenticated, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push(`/${locale}/login`);
  };

  const navLinks = [
    { href: `/${locale}/dashboard`, label: "Today's Advice", roleRequired: "farmer" },
    { href: `/${locale}/fields`, label: "My Fields", roleRequired: "farmer" },
    { href: `/${locale}/scan`, label: "Scan a Leaf", roleRequired: "farmer" },
    { href: `/${locale}/officer`, label: "Officer Portal", roleRequired: "extension_officer" },
    { href: `/${locale}/brics`, label: "BRICS Hub", roleRequired: "government_admin" },
    { href: `/${locale}/design`, label: "Design System", roleRequired: null },
  ];

  return (
    <header className="sticky top-0 z-40 w-full bg-white/95 backdrop-blur-md border-b border-border shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Logo and Brand */}
        <Link
          href={`/${locale}/dashboard`}
          className="flex items-center gap-2.5 focus:outline-none focus:ring-2 focus:ring-primary rounded-btn p-1 select-none"
        >
          <div className="h-9 w-9 rounded-xl bg-primary flex items-center justify-center text-white shadow-green-sm">
            <Sprout className="h-5 w-5" />
          </div>
          <div>
            <span className="font-extrabold text-lg text-primary-dark tracking-tight leading-none block">
              KrishiNet
            </span>
            <span className="text-[10px] font-bold text-text-muted tracking-wider uppercase block">
              BRICS Intelligence
            </span>
          </div>
        </Link>

        {/* Desktop Navigation Links */}
        <nav aria-label="Main Navigation" className="hidden md:flex items-center gap-1.5 text-sm font-semibold">
          {navLinks.map((link) => {
            if (link.roleRequired && role && link.roleRequired !== role && role !== "researcher") {
              return null;
            }
            const isActive = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "px-3 py-2 rounded-btn transition-colors",
                  isActive
                    ? "bg-primary-light text-primary-dark font-bold"
                    : "text-text hover:bg-surface-soft hover:text-primary-dark"
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Global Controls & User Status */}
        <div className="flex items-center gap-2 sm:gap-3">
          <SyncStatusChip className="hidden sm:inline-flex" />
          <AccessibilityBar className="hidden lg:flex" />
          <LanguageSwitcher currentLocale={locale} />

          {isAuthenticated ? (
            <div className="flex items-center gap-2">
              <span className="hidden xl:inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-1 rounded bg-surface-soft border border-border text-text">
                <User className="h-3.5 w-3.5 text-primary" />
                <span className="truncate max-w-[120px]">{user?.full_name || role}</span>
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                aria-label="Sign out of system"
                className="h-9 px-2 text-text-muted hover:text-status-risk"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <Link href={`/${locale}/login`}>
              <Button variant="primary" size="sm">
                Sign In
              </Button>
            </Link>
          )}

          {/* Mobile hamburger menu toggle */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
            className="md:hidden p-2 rounded-btn border border-border hover:bg-surface-soft text-text"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-border bg-white px-4 py-4 space-y-3 animate-in slide-in-from-top-2 duration-150">
          <nav className="flex flex-col space-y-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  "px-3 py-2.5 rounded-btn text-base font-medium",
                  pathname.startsWith(link.href)
                    ? "bg-primary-light text-primary-dark font-bold"
                    : "text-text hover:bg-surface-soft"
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="pt-3 border-t border-border flex items-center justify-between">
            <AccessibilityBar />
            <SyncStatusChip />
          </div>
        </div>
      )}
    </header>
  );
}
