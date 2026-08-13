"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bot, Users, LineChart, ShoppingCart, Package, Settings, LogOut, MessageSquare } from "lucide-react";

const navigation = [
  { name: "Live Demo", href: "/sales-brain", icon: MessageSquare },
  { name: "Products", href: "/products", icon: Package },
  { name: "Customers", href: "/customers", icon: Users },
  { name: "Orders", href: "/orders", icon: ShoppingCart },
  { name: "Insights", href: "/insights", icon: LineChart },
  { name: "Settings", href: "/settings", icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState({ name: "Manager kopdes", email: "admin@lariska.ai", avatar: "" });

  useEffect(() => {
    const loadUser = () => {
      const savedName = localStorage.getItem("user_name");
      const savedEmail = localStorage.getItem("user_email");
      const savedAvatar = localStorage.getItem("user_avatar");
      if (savedName || savedEmail || savedAvatar) {
        setUser({
          name: savedName || "Manager kopdes",
          email: savedEmail || "admin@lariska.ai",
          avatar: savedAvatar || "",
        });
      }
    };

    loadUser();
    window.addEventListener("storage", loadUser);
    return () => window.removeEventListener("storage", loadUser);
  }, []);

  const initials = user.name
    ? user.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
    : 'MK';

  return (
    <div className="min-h-screen bg-[#F8F9FF] font-sans text-slate-900 overflow-hidden relative flex">
      {/* Global Background gradients */}
      <div className="fixed top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-purple-300/30 blur-[120px] pointer-events-none" />
      <div className="fixed bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-300/20 blur-[120px] pointer-events-none" />

      {/* Sidebar */}
      <aside className="relative z-20 hidden w-64 flex-col justify-between border-r border-white/60 bg-white/40 p-6 backdrop-blur-xl md:flex md:h-screen">
        <div>
          {/* Logo */}
          <div className="flex items-center gap-2 mb-8 mt-1 cursor-default">
            <Bot className="w-9 h-9 text-[#715bc9]" />
            <span className="text-2xl font-black tracking-tight text-indigo-950">LARISKA<span className="text-[#715bc9]">.</span></span>
          </div>

          {/* Navigation */}
          <nav className="flex flex-col gap-2">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium select-none outline-none ${isActive
                    ? "bg-[#715bc9] text-white shadow-md shadow-[#715bc9]/25 font-semibold"
                    : "text-slate-600 hover:bg-white/70 hover:text-[#715bc9]"
                    }`}
                >
                  <item.icon className={`w-5 h-5 ${isActive ? "text-white" : "text-[#715bc9]"}`} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom Actions & User Profile */}
        <div className="flex flex-col gap-6">
          {/* User Profile */}
          <div className="flex items-center gap-3 px-4 py-3 bg-white/50 border border-white/60 rounded-xl shadow-sm">
            {user.avatar ? (
              <img src={user.avatar} alt={user.name} className="w-10 h-10 rounded-full object-cover border border-[#715bc9]/30 shrink-0" />
            ) : (
              <div className="w-10 h-10 rounded-full bg-[#715bc9]/10 border border-[#715bc9]/20 flex items-center justify-center text-[#715bc9] font-semibold text-sm shrink-0">
                {initials}
              </div>
            )}
            <div className="flex flex-col overflow-hidden">
              <span className="text-sm font-semibold text-slate-800 leading-tight truncate">{user.name}</span>
              <span className="text-xs text-slate-500 truncate">{user.email}</span>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <button
              onClick={() => router.push("/login")}
              className="group flex items-center gap-3 px-4 py-3 rounded-xl text-slate-600 hover:bg-red-50 hover:text-red-600 transition-all duration-200 w-full text-left"
            >
              <LogOut className="w-5 h-5 text-slate-400 group-hover:text-red-500 transition-colors" />
              <span className="font-medium">Logout</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile navigation: same information architecture, optimized for demo on a phone. */}
      <div className="fixed inset-x-0 top-0 z-30 border-b border-white/70 bg-white/75 px-4 py-3 backdrop-blur-xl md:hidden">
        <div className="flex items-center justify-between"><div className="flex items-center gap-2"><Bot className="h-6 w-6 text-[#715bc9]" /><span className="font-black tracking-tight text-indigo-950">LARISKA<span className="text-[#715bc9]">.</span></span></div><Link href="/settings" className="rounded-lg bg-indigo-50 px-2.5 py-1.5 text-xs font-bold text-[#715bc9]">Pengaturan</Link></div>
        <nav className="mt-3 flex gap-2 overflow-x-auto pb-0.5">{navigation.slice(0, 5).map((item) => { const active = pathname === item.href; return <Link key={item.name} href={item.href} className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold ${active ? "bg-[#715bc9] text-white" : "bg-white text-slate-600 ring-1 ring-slate-100"}`}><item.icon className="h-3.5 w-3.5" />{item.name}</Link>; })}</nav>
      </div>

      {/* Main Content */}
      <main className="relative z-10 h-screen flex-1 overflow-y-auto p-5 pt-32 md:p-8">
        <div className="max-w-6xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
