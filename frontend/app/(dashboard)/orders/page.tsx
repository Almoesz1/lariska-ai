"use client";

import React, { useState } from "react";
import { 
  ShoppingCart, Search, Filter, CheckCircle2, Clock, XCircle, FileText, QrCode, Send, Eye,
  Download, TrendingUp
} from "lucide-react";

// Mock Data
const mockOrders = [
  { id: "ORD-9821", customer: "Mustofa", phone: "+62 812-3456-7890", items: 2, total: "Rp 155.000", status: "completed", date: "Today, 14:30", itemsList: [{ name: "Kopi Arabica 1kg", price: "Rp 120.000" }, { name: "Gula Aren 500g", price: "Rp 35.000" }] },
  { id: "ORD-9822", customer: "Brian", phone: "+62 813-9876-5432", items: 1, total: "Rp 45.000", status: "pending", date: "Today, 15:15", itemsList: [{ name: "Teh Melati Premium", price: "Rp 45.000" }] },
  { id: "ORD-9823", customer: "Ihsan", phone: "+62 856-1122-3344", items: 4, total: "Rp 320.000", status: "completed", date: "Yesterday, 09:10", itemsList: [{ name: "Kopi Robusta 1kg", price: "Rp 230.000" }, { name: "Filter Kopi V60", price: "Rp 90.000" }] },
  { id: "ORD-9824", customer: "Lugas", phone: "+62 812-9988-7766", items: 1, total: "Rp 85.000", status: "cancelled", date: "Yesterday, 11:45", itemsList: [{ name: "Madu Hutan 250ml", price: "Rp 85.000" }] },
  { id: "ORD-9825", customer: "Ali", phone: "+62 819-4455-6677", items: 3, total: "Rp 210.000", status: "completed", date: "Oct 12, 16:20", itemsList: [{ name: "Sirup Frambozen", price: "Rp 100.000" }, { name: "Susu Kental Manis", price: "Rp 110.000" }] },
  { id: "ORD-9826", customer: "Barakbah", phone: "+62 821-3322-1100", items: 2, total: "Rp 115.000", status: "pending", date: "Oct 12, 10:05", itemsList: [{ name: "Kopi Arabica 500g", price: "Rp 65.000" }, { name: "Gula Aren 500g", price: "Rp 50.000" }] },
];

export default function OrdersPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const filteredOrders = mockOrders.filter(order => {
    const matchesSearch = order.customer.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          order.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          order.phone.includes(searchTerm);
    const matchesStatus = statusFilter === "all" || order.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="h-full flex flex-col gap-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-semibold text-indigo-950 mb-1">Orders & Invoices</h1>
          <p className="text-slate-500 text-xs font-normal">Executive Order Matrix & Real-Time QRIS Telemetry.</p>
        </div>

        <div className="flex gap-3">
          <button className="flex items-center gap-2 bg-white/80 hover:bg-white backdrop-blur-md border border-slate-200/80 text-indigo-950 px-4 py-2.5 rounded-xl transition-all shadow-sm font-semibold text-xs cursor-pointer">
            <Download className="w-4 h-4 text-[#715bc9]" /> Export CSV
          </button>
          <button className="flex items-center gap-2 bg-[#715bc9] hover:bg-[#5f49b5] text-white px-5 py-2.5 rounded-xl transition-all shadow-md font-semibold text-xs cursor-pointer">
            <ShoppingCart className="w-4 h-4" /> New Order
          </button>
        </div>
      </div>

      {/* Top Financial & Telemetry KPI Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-2xl p-5 shadow-lg shadow-indigo-100/30">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Gross Revenue Today</p>
          <h4 className="text-2xl font-semibold text-indigo-950 mt-1">Rp 930.000</h4>
          <span className="text-[#715bc9] text-xs flex items-center gap-1 mt-1 font-medium">
            <TrendingUp className="w-3.5 h-3.5" /> +18.4% vs yesterday
          </span>
        </div>

        <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-2xl p-5 shadow-lg shadow-indigo-100/30">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Pending QRIS Payments</p>
          <h4 className="text-2xl font-semibold text-amber-600 mt-1">2 Orders</h4>
          <span className="text-amber-600 text-xs mt-1 block font-medium">Rp 160.000 awaiting scan</span>
        </div>

        <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-2xl p-5 shadow-lg shadow-indigo-100/30">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Verified Completed</p>
          <h4 className="text-2xl font-semibold text-emerald-600 mt-1">3 Orders</h4>
          <span className="text-emerald-600 text-xs mt-1 block font-medium">100% QRIS verified</span>
        </div>

        <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-2xl p-5 shadow-lg shadow-indigo-100/30">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Avg Basket Value</p>
          <h4 className="text-2xl font-semibold text-[#715bc9] mt-1">Rp 155.000</h4>
          <span className="text-[#715bc9] text-xs mt-1 block font-medium">2.1 items / transaction</span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-2xl p-4 shadow-md flex justify-between items-center">
        <div className="relative w-96">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            type="text"
            placeholder="Search by Order ID, Customer, or Phone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-[#715bc9]/20 focus:border-[#715bc9]"
          />
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5 text-[#715bc9]" /> Filter Status:
          </span>
          <div className="flex bg-slate-100/80 p-1 rounded-xl gap-1 text-xs font-medium">
            {['all', 'pending', 'completed', 'cancelled'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-4 py-1.5 rounded-lg capitalize transition-all cursor-pointer ${
                  statusFilter === st
                    ? "bg-[#715bc9] text-white shadow-sm font-semibold"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Executive Compact Matrix Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 flex-1 min-h-0 overflow-y-auto pr-1 custom-scrollbar">
        {filteredOrders.length > 0 ? (
          filteredOrders.map((o) => (
            <div key={o.id} className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-3xl p-6 shadow-lg shadow-indigo-100/30 flex flex-col justify-between space-y-5 hover:-translate-y-0.5 transition-all">
              <div>
                <div className="flex justify-between items-center mb-3">
                  <span className="font-mono text-xs font-semibold text-[#715bc9] bg-indigo-50 border border-indigo-100 px-2.5 py-1 rounded-lg">
                    {o.id}
                  </span>
                  <span className={`text-xs font-semibold px-3 py-1 rounded-full ${
                    o.status === 'completed' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                    o.status === 'pending' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                    'bg-rose-50 text-rose-700 border border-rose-200'
                  }`}>
                    {o.status === 'pending' ? 'QRIS Pending' : o.status}
                  </span>
                </div>

                <h3 className="font-semibold text-lg text-indigo-950 mt-1">{o.customer}</h3>
                <p className="text-slate-500 text-xs mt-0.5 font-normal">{o.phone} • {o.date}</p>

                {/* Line Items Preview */}
                <div className="mt-4 pt-3 border-t border-slate-100 space-y-1.5">
                  <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block mb-1">Items ({o.items})</span>
                  {o.itemsList?.map((it, idx) => (
                    <div key={idx} className="flex justify-between text-xs font-normal text-slate-700">
                      <span className="truncate pr-2">• {it.name}</span>
                      <span className="font-semibold text-slate-900 shrink-0">{it.price}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Footer */}
              <div className="pt-4 border-t border-slate-100 space-y-3">
                <div className="flex justify-between items-end">
                  <div>
                    <span className="text-[10px] text-slate-400 block uppercase font-medium tracking-wider">Total Amount</span>
                    <span className="text-xl font-semibold text-indigo-950">{o.total}</span>
                  </div>

                  <button className="text-slate-400 hover:text-indigo-950 transition-colors p-1 rounded-lg hover:bg-slate-100 cursor-pointer" title="View Details">
                    <Eye className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex gap-2 pt-1">
                  {o.status === 'pending' && (
                    <>
                      <button className="flex-1 bg-[#715bc9] hover:bg-[#5f49b5] text-white py-2 rounded-xl text-xs font-medium transition-all shadow-sm flex items-center justify-center gap-1.5 cursor-pointer">
                        <QrCode className="w-3.5 h-3.5" /> QRIS
                      </button>
                      <button className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded-xl text-xs font-medium transition-all shadow-sm flex items-center justify-center gap-1.5 cursor-pointer">
                        <Send className="w-3.5 h-3.5" /> Send WA
                      </button>
                    </>
                  )}
                  {o.status === 'completed' && (
                    <button className="w-full bg-indigo-50 text-[#715bc9] border border-indigo-100 hover:bg-indigo-100 py-2 rounded-xl text-xs font-medium transition-all flex items-center justify-center gap-1.5 cursor-pointer">
                      <FileText className="w-3.5 h-3.5" /> Download Receipt
                    </button>
                  )}
                  {o.status === 'cancelled' && (
                    <button className="w-full border border-slate-200 text-slate-500 hover:bg-slate-50 py-2 rounded-xl text-xs font-medium transition-all flex items-center justify-center gap-1.5 cursor-pointer">
                      View Order Logs
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-3 bg-white/70 backdrop-blur-md rounded-3xl p-12 text-center text-slate-500 font-medium">
            No orders match your search or filter criteria.
          </div>
        )}
      </div>
    </div>
  );
}



