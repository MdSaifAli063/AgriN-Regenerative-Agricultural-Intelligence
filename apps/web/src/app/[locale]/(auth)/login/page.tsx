"use client";

import React, { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Sprout, Users, Building2, Microscope, ArrowRight, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { useAuthStore } from "@/lib/auth/store";
import { cn } from "@/lib/utils";
import type { UserRole } from "@krishinet/shared";

interface DemoRoleOption {
  role: UserRole;
  title: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  defaultUser: {
    user_id: string;
    full_name: string;
    phone_number: string;
    country_iso: string;
  };
}

const DEMO_ROLES: DemoRoleOption[] = [
  {
    role: "farmer",
    title: "Smallholder Farmer",
    subtitle: "Ramesh Patel • Wardha, India (Cotton & Soybean)",
    icon: Sprout,
    defaultUser: {
      user_id: "demo-farmer-001",
      full_name: "Ramesh Patel",
      phone_number: "+919876543210",
      country_iso: "IND",
    },
  },
  {
    role: "extension_officer",
    title: "Extension Field Officer",
    subtitle: "Dr. Ananya Rao • District Agronomist",
    icon: Users,
    defaultUser: {
      user_id: "demo-officer-001",
      full_name: "Dr. Ananya Rao",
      phone_number: "+919876543211",
      country_iso: "IND",
    },
  },
  {
    role: "government_admin",
    title: "Government Policy Admin",
    subtitle: "Carlos Silva • Ministry of Agriculture (BRICS Node Brazil)",
    icon: Building2,
    defaultUser: {
      user_id: "demo-gov-001",
      full_name: "Carlos Silva",
      phone_number: "+5511999998888",
      country_iso: "BRA",
    },
  },
  {
    role: "researcher",
    title: "Agronomy Researcher",
    subtitle: "Prof. Thabo Ndlovu • Soil Science & Climate Analogue Lab",
    icon: Microscope,
    defaultUser: {
      user_id: "demo-res-001",
      full_name: "Prof. Thabo Ndlovu",
      phone_number: "+27821234567",
      country_iso: "ZAF",
    },
  },
];

export default function LoginPage() {
  const router = useRouter();
  const params = useParams();
  const locale = (params?.locale as string) || "en";

  const { loginWithDev, isLoading, error } = useAuthStore();
  const [selectedRole, setSelectedRole] = useState<UserRole>("farmer");

  const handleLogin = async (overrideRole?: UserRole) => {
    const roleToUse = overrideRole || selectedRole;
    const roleConfig = DEMO_ROLES.find((r) => r.role === roleToUse) || DEMO_ROLES[0];

    try {
      await loginWithDev({
        role: roleConfig.role,
        user_id: roleConfig.defaultUser.user_id,
        full_name: roleConfig.defaultUser.full_name,
        phone_number: roleConfig.defaultUser.phone_number,
        country_iso: roleConfig.defaultUser.country_iso,
      });

      // Role-aware redirect
      if (roleConfig.role === "farmer") {
        router.push(`/${locale}/dashboard`);
      } else if (roleConfig.role === "extension_officer") {
        router.push(`/${locale}/officer`);
      } else {
        router.push(`/${locale}/brics`);
      }
    } catch {
      // Handled via store state
    }
  };

  return (
    <div className="min-h-screen bg-surface-soft flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-2">
        <div className="mx-auto h-14 w-14 rounded-2xl bg-primary flex items-center justify-center text-white shadow-green-md">
          <Sprout className="h-8 w-8" />
        </div>
        <h1 className="text-3xl font-extrabold text-primary-dark tracking-tight">
          KrishiNet-BRICS
        </h1>
        <p className="text-sm text-text-muted">
          Sovereign Regenerative Agricultural Intelligence Network
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-xl">
        <Card className="p-6 sm:p-8 shadow-card-hover bg-white border border-border">
          <CardHeader className="px-0 pt-0">
            <CardTitle>Sign In with Sovereign Identity</CardTitle>
            <CardDescription>
              Select a persona below to enter with full cryptographic RBAC credentials in DEMO MODE.
            </CardDescription>
          </CardHeader>

          <CardContent className="px-0 space-y-4">
            {error && (
              <div
                role="alert"
                className="p-3 bg-red-50 border border-red-200 text-status-risk rounded-xl text-xs font-semibold"
              >
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 gap-3">
              {DEMO_ROLES.map((item) => {
                const Icon = item.icon;
                const isSelected = selectedRole === item.role;

                return (
                  <div
                    key={item.role}
                    onClick={() => {
                      setSelectedRole(item.role);
                      handleLogin(item.role);
                    }}
                    className={cn(
                      "p-4 rounded-xl border flex items-center justify-between cursor-pointer transition-all select-none",
                      isSelected
                        ? "border-primary bg-primary-light/40 shadow-sm ring-1 ring-primary"
                        : "border-border hover:border-primary/60 hover:bg-surface-soft"
                    )}
                  >
                    <div className="flex items-center gap-3.5">
                      <div
                        className={cn(
                          "h-10 w-10 rounded-btn flex items-center justify-center flex-shrink-0 transition-colors",
                          isSelected
                            ? "bg-primary text-white"
                            : "bg-surface-soft border border-border text-primary-dark"
                        )}
                      >
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="text-base font-bold text-text">
                          {item.title}
                        </div>
                        <div className="text-xs text-text-muted mt-0.5">
                          {item.subtitle}
                        </div>
                      </div>
                    </div>

                    <ArrowRight
                      className={cn(
                        "h-5 w-5 transition-transform",
                        isSelected
                          ? "text-primary translate-x-1"
                          : "text-text-muted opacity-40"
                      )}
                    />
                  </div>
                );
              })}
            </div>

            <div className="pt-4">
              <Button
                variant="primary"
                fullWidth
                size="lg"
                isLoading={isLoading}
                onClick={() => handleLogin()}
              >
                Continue as {DEMO_ROLES.find((r) => r.role === selectedRole)?.title}
              </Button>
            </div>

            <div className="pt-4 border-t border-border flex items-center justify-center gap-2 text-xs text-text-muted">
              <ShieldCheck className="h-4 w-4 text-primary" />
              <span>OIDC 2.0 / Keycloak Realm Sovereign Auth Enabled</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
