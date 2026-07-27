"use client";

import React, { useState } from "react";
import { ShoppingCart, Search, Filter, CheckCircle2, Clock, XCircle, MoreHorizontal } from "lucide-react";

const mockOrders = [
  { id: "ORD-9821", customer: "Mustofa", items: 2, total: "Rp 155.000", status: "completed", date: "Today, 14:30" },
  { id: "ORD-9822", customer: "Brian", items: 1, total: "Rp 45.000", status: "pending", date: "Today, 15:15" },
  { id: "ORD-9823", customer: "Ihsan", items: 4, total: "Rp 320.000", status: "completed", date: "Yesterday, 09:10" },
  { id: "ORD-9824", customer: "Lugas", items: 1, total: "Rp 85.000", status: "cancelled", date: "Yesterday, 11:45" },
  { id: "ORD-9825", customer: "Ali", items: 3, total: "Rp 210.000", status: "completed", date: "Oct 12, 16:20" },
  { id: "ORD-9826", customer: "Barakbah", items: 2, total: "Rp 115.000", status: "pending", date: "Oct 12, 10:05" },
];

export default function OrdersPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const filteredOrders = mockOrders.filter(order => {
    const matchesSearch = order.customer.toLowerCase().includes(searchTerm.toLowerCase()) || order.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || order.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="h-full flex flex-col gap-6">
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-serif font-bold text-indigo-950 mb-2">Orders</h1>
          <p className="text-slate-600">Track and manage your customer transactions.</p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 bg-white/60 hover:bg-white backdrop-blur-md border border-white/80 text-indigo-900 px-4 py-2 rounded-xl transition-colors shadow-sm font-medium">
            Export CSV
          </button>
          <button className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl transition-colors shadow-lg shadow-indigo-200 font-medium">
            <ShoppingCart className="w-4 h-4" /> New Order
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="bg-white/60 backdrop-blur-md border border-white rounded-3xl shadow-xl flex flex-col flex-1 overflow-hidden">
        
        {/* Toolbar */}
        <div className="p-6 border-b border-white/60 flex justify-between items-center bg-white/30">
          <div className="relative w-96">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input 
              type="text"
              placeholder="Search by Order ID or Customer..."
              className="w-full pl-11 pr-4 py-2.5 bg-white border border-white/80 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all placeholder:text-slate-400 text-sm"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-slate-500 font-medium">
              <Filter className="w-4 h-4" /> Filter by Status:
            </div>
            <div className="flex bg-white/50 border border-white/80 rounded-xl p-1 shadow-sm">
              <button 
                onClick={() => setStatusFilter("all")}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${statusFilter === 'all' ? 'bg-white shadow text-indigo-900' : 'text-slate-500 hover:text-slate-900'}`}
              >
                All
              </button>
              <button 
                onClick={() => setStatusFilter("pending")}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${statusFilter === 'pending' ? 'bg-white shadow text-amber-700' : 'text-slate-500 hover:text-slate-900'}`}
              >
                Pending
              </button>
              <button 
                onClick={() => setStatusFilter("completed")}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${statusFilter === 'completed' ? 'bg-white shadow text-emerald-700' : 'text-slate-500 hover:text-slate-900'}`}
              >
                Completed
              </button>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto custom-scrollbar">
          <table className="w-full text-left border-collapse min-w-[800px]">
            <thead className="sticky top-0 bg-white/80 backdrop-blur-xl border-b border-indigo-100 z-10">
              <tr className="text-indigo-950 text-sm">
                <th className="px-8 py-5 font-semibold">Order ID</th>
                <th className="px-8 py-5 font-semibold">Customer</th>
                <th className="px-8 py-5 font-semibold">Date</th>
                <th className="px-8 py-5 font-semibold text-center">Items</th>
                <th className="px-8 py-5 font-semibold">Total</th>
                <th className="px-8 py-5 font-semibold">Status</th>
                <th className="px-8 py-5 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-indigo-50/50">
              {filteredOrders.length > 0 ? (
                filteredOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-white/40 transition-colors text-slate-700 group">
                    <td className="px-8 py-5 font-bold text-indigo-900">{order.id}</td>
                    <td className="px-8 py-5 font-medium">{order.customer}</td>
                    <td className="px-8 py-5 text-sm text-slate-500">{order.date}</td>
                    <td className="px-8 py-5 text-center">
                      <span className="bg-slate-100 text-slate-600 px-2.5 py-1 rounded-md text-xs font-bold">{order.items}</span>
                    </td>
                    <td className="px-8 py-5 font-semibold text-slate-900">{order.total}</td>
                    <td className="px-8 py-5">
                      {order.status === 'completed' && (
                        <span className="flex items-center gap-1.5 text-emerald-700 bg-emerald-100/50 border border-emerald-200 px-3 py-1.5 rounded-full text-xs font-bold w-fit shadow-sm">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Completed
                        </span>
                      )}
                      {order.status === 'pending' && (
                        <span className="flex items-center gap-1.5 text-amber-700 bg-amber-100/50 border border-amber-200 px-3 py-1.5 rounded-full text-xs font-bold w-fit shadow-sm">
                          <Clock className="w-3.5 h-3.5" /> Pending
                        </span>
                      )}
                      {order.status === 'cancelled' && (
                        <span className="flex items-center gap-1.5 text-rose-700 bg-rose-100/50 border border-rose-200 px-3 py-1.5 rounded-full text-xs font-bold w-fit shadow-sm">
                          <XCircle className="w-3.5 h-3.5" /> Cancelled
                        </span>
                      )}
                    </td>
                    <td className="px-8 py-5 text-right">
                      <button className="text-slate-400 hover:text-indigo-600 transition-colors p-1 rounded-lg hover:bg-indigo-50 opacity-0 group-hover:opacity-100">
                        <MoreHorizontal className="w-5 h-5" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-8 py-16 text-center text-slate-500">
                    No orders found matching your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
