"use client";
import { useState, useEffect } from 'react';

const KEEPER_URL = process.env.NEXT_PUBLIC_KEEPER_URL || 'http://localhost:8000';

interface Order {
  id: string;
  amount_nara: number;
  price_usd: number;
  total_usd: number;
  payment_token: string;
  payment_chain_id: number;
  seller_pubkey: string;
  payment_address: string;
  status: string;
  created_at: number;
}

export default function Home() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ amount_nara: '', price_usd: '', payment_token: 'USDC' });

  useEffect(() => { fetchOrders(); }, []);

  const fetchOrders = async () => {
    try {
      const res = await fetch(`${KEEPER_URL}/api/orders?limit=50`);
      const data = await res.json();
      setOrders(data.orders || []);
      setTotal(data.total || 0);
    } catch (e) { console.error('Fetch failed:', e); }
    finally { setLoading(false); }
  };

  const handleBuy = async (orderId: string) => {
    const res = await fetch(`${KEEPER_URL}/api/orders/${orderId}`);
    const order = await res.json();
    alert(`Order #${orderId}\nAmount: ${order.amount_nara} NARA\nPrice: $${order.total_usd}\nPay to: ${order.payment_address}\n\nAfter payment, Keeper auto-releases NARA to you.`);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${KEEPER_URL}/api/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount_nara: parseFloat(form.amount_nara),
          price_usd: parseFloat(form.price_usd),
          payment_token: form.payment_token,
          payment_chain_id: 8453, // Base chain
          seller_pubkey: 'your_pubkey_here', // Replace with wallet connect
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      alert(`Order #${data.order_id} created!`);
      setShowCreate(false);
      fetchOrders();
    } catch (e: any) { alert('Error: ' + e.message); }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              🥜 Nara OTC
            </h1>
            <p className="text-gray-400 mt-1">Peer-to-peer NARA trading</p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg font-medium transition"
          >
            + New Order
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <div className="text-2xl font-bold">{total}</div>
            <div className="text-gray-500 text-sm">Active Orders</div>
          </div>
          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <div className="text-2xl font-bold">${orders.reduce((s, o) => s + o.total_usd, 0).toFixed(2)}</div>
            <div className="text-gray-500 text-sm">Total Volume</div>
          </div>
          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <div className="text-2xl font-bold">
              {orders.length > 0 ? `💵 ${orders[0].payment_token}` : '—'}
            </div>
            <div className="text-gray-500 text-sm">Payment Token</div>
          </div>
        </div>

        {/* Create Order Form */}
        {showCreate && (
          <form onSubmit={handleCreate} className="bg-gray-900 p-6 rounded-xl mb-6 border border-gray-800">
            <h2 className="text-lg font-semibold mb-4">Create Sell Order</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Amount NARA</label>
                <input type="number" step="any" className="w-full bg-gray-800 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 outline-none"
                  value={form.amount_nara} onChange={e => setForm({...form, amount_nara: e.target.value})} placeholder="100" required />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Price per NARA (USD)</label>
                <input type="number" step="any" className="w-full bg-gray-800 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 outline-none"
                  value={form.price_usd} onChange={e => setForm({...form, price_usd: e.target.value})} placeholder="0.05" required />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Payment Token</label>
                <select className="w-full bg-gray-800 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 outline-none"
                  value={form.payment_token} onChange={e => setForm({...form, payment_token: e.target.value})}>
                  <option value="USDC">USDC (Base)</option>
                  <option value="USDT">USDT (BSC)</option>
                </select>
              </div>
            </div>
            <button type="submit" className="mt-4 w-full bg-green-600 hover:bg-green-500 py-3 rounded-lg font-medium transition">
              Create Order
            </button>
          </form>
        )}

        {/* Orders Table */}
        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading orders...</div>
        ) : orders.length === 0 ? (
          <div className="text-center py-12 text-gray-500">No active orders. Create one to get started!</div>
        ) : (
          <div className="space-y-3">
            {orders.map((order) => (
              <div key={order.id} className="bg-gray-900 rounded-xl p-5 border border-gray-800 hover:border-gray-700 transition flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`inline-block w-2 h-2 rounded-full ${order.status === 'Active' ? 'bg-green-400' : 'bg-gray-500'}`} />
                    <span className="font-mono text-sm text-gray-500">#{order.id}</span>
                  </div>
                  <div className="mt-1">
                    <span className="text-lg font-semibold">{order.amount_nara}</span>
                    <span className="text-gray-400 ml-1">NARA</span>
                  </div>
                  <div className="text-sm text-gray-500">
                    ${order.price_usd}/NARA • Total: <span className="text-gray-300 font-medium">${order.total_usd}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-gray-500 mb-1">Pay with {order.payment_token}</div>
                  <div className="text-xs text-gray-500 mb-1 truncate max-w-[200px]">{order.payment_address}</div>
                  <div className="text-xs text-gray-600">Chain: {order.payment_chain_id === 8453 ? 'Base' : order.payment_chain_id}</div>
                </div>
                <button onClick={() => handleBuy(order.id)}
                  className="ml-6 bg-blue-600 hover:bg-blue-500 px-5 py-2.5 rounded-lg font-medium text-sm transition whitespace-nowrap">
                  Buy Now
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="mt-12 text-center text-gray-600 text-sm">
          Nara OTC v1.0 • Escrow auto-release via Keeper • Built on Nara Chain
        </div>
      </div>
    </div>
  );
}
