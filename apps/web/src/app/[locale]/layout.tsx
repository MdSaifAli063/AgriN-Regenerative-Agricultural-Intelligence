import React from "react";
import type { Metadata, Viewport } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { AppProviders } from "@/components/providers/AppProviders";
import { Header } from "@/components/common/Header";
import { OfflineBanner } from "@/components/ui/OfflineBanner";
import { DemoRibbon } from "@/components/common/DemoRibbon";
import { DisclaimerFooter } from "@/components/common/DisclaimerFooter";
import "../globals.css";

export const viewport: Viewport = {
  themeColor: "#16A34A",
};

export const metadata: Metadata = {
  title: "KrishiNet-BRICS | Sovereign Regenerative Agricultural Intelligence",
  description:
    "Mobile-first, offline-first digital public good delivering precision regenerative agronomy, edge disease diagnosis, and epidemiological outbreak intelligence across BRICS smallholder communities.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "KrishiNet",
  },
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const messages = await getMessages();
  const isRtl = locale === "ar" || locale === "fa";

  return (
    <html lang={locale} dir={isRtl ? "rtl" : "ltr"} suppressHydrationWarning>
      <body className="min-h-screen bg-background text-text flex flex-col antialiased" suppressHydrationWarning>
        {/* WCAG Skip to Main Content Link */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 z-50 px-4 py-2 bg-primary text-white font-bold rounded-btn shadow-card"
        >
          Skip to main content
        </a>

        <NextIntlClientProvider messages={messages} locale={locale}>
          <AppProviders>
            <DemoRibbon nodeCountry="IND" />
            <OfflineBanner />
            <Header />

            <main id="main-content" className="flex-1 w-full focus:outline-none" tabIndex={-1}>
              {children}
            </main>

            <DisclaimerFooter />
          </AppProviders>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
