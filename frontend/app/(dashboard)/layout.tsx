"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, Users, LineChart, ShoppingCart, Package, Settings, LogOut } from "lucide-react";

const navigation = [
  { name: "Products", href: "/products", icon: Package },
  { name: "Customers", href: "/customers", icon: Users },
  { name: "Orders", href: "/orders", icon: ShoppingCart },
  { name: "Insights", href: "/insights", icon: LineChart },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[#F8F9FF] font-sans text-slate-900 overflow-hidden relative flex">
      {/* Global Background gradients */}
      <div className="fixed top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-purple-300/30 blur-[120px] pointer-events-none" />
      <div className="fixed bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-300/20 blur-[120px] pointer-events-none" />

      {/* Sidebar */}
      <aside className="relative z-20 w-64 flex flex-col justify-between h-screen p-6 bg-white/40 backdrop-blur-xl border-r border-white/60">
        <div>
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 mb-10 hover:opacity-80 transition-opacity">
            <Bot className="w-8 h-8 text-indigo-600" />
            <span className="text-2xl font-bold tracking-tight text-indigo-950">
              LARISKA<span className="text-indigo-600">.</span>
            </span>
          </Link>

          {/* Navigation */}
          <nav className="flex flex-col gap-2">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                    isActive
                      ? "bg-indigo-600 text-white shadow-lg shadow-indigo-200"
                      : "text-slate-600 hover:bg-white/60 hover:text-indigo-900"
                  }`}
                >
                  <item.icon className={`w-5 h-5 ${isActive ? "text-indigo-100" : "text-indigo-400"}`} />
                  <span className="font-medium">{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom Actions */}
        <div className="flex flex-col gap-2">
          <Link
            href="/settings"
            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
              pathname === "/settings"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-200"
                : "text-slate-600 hover:bg-white/60 hover:text-indigo-900"
            }`}
          >
            <Settings className={`w-5 h-5 ${pathname === "/settings" ? "text-indigo-100" : "text-indigo-400"}`} />
            <span className="font-medium">Settings</span>
          </Link>
          <button className="group flex items-center gap-3 px-4 py-3 rounded-xl text-slate-600 hover:bg-red-50 hover:text-red-600 transition-all duration-200 w-full text-left">
            <LogOut className="w-5 h-5 text-slate-400 group-hover:text-red-500 transition-colors" />
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 relative z-10 h-screen overflow-y-auto p-8">
        <div className="max-w-6xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
