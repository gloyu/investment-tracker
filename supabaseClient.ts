"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";

interface WatchlistItem {
  id: string;
  symbol: string;
  type: "stock" | "index";
  name: string | null;
  active: boolean;
}

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSymbol, setNewSymbol] = useState("");
  const [newType, setNewType] = useState<"stock" | "index">("stock");
  const [error, setError] = useState<string | null>(null);

  async function loadWatchlist() {
    setLoading(true);
    const { data, error } = await supabase
      .from("watchlist")
      .select("id, symbol, type, name, active")
      .order("symbol", { ascending: true });

    if (error) {
      setError(error.message);
    } else {
      setItems(data as WatchlistItem[]);
      setError(null);
    }
    setLoading(false);
  }

  useEffect(() => {
    loadWatchlist();
  }, []);

  async function addSymbol(e: React.FormEvent) {
    e.preventDefault();
    if (!newSymbol.trim()) return;

    const { error } = await supabase.from("watchlist").insert({
      symbol: newSymbol.trim().toUpperCase(),
      type: newType,
    });

    if (error) {
      setError(error.message);
      return;
    }

    setNewSymbol("");
    await loadWatchlist();
  }

  async function toggleActive(item: WatchlistItem) {
    const { error } = await supabase
      .from("watchlist")
      .update({ active: !item.active })
      .eq("id", item.id);

    if (error) {
      setError(error.message);
      return;
    }
    await loadWatchlist();
  }

  async function removeSymbol(id: string) {
    const { error } = await supabase.from("watchlist").delete().eq("id", id);
    if (error) {
      setError(error.message);
      return;
    }
    await loadWatchlist();
  }

  return (
    <div style={{ maxWidth: 600 }}>
      <h1>Watchlist</h1>

      <form onSubmit={addSymbol} style={{ display: "flex", gap: "0.5rem", margin: "1rem 0" }}>
        <input
          value={newSymbol}
          onChange={(e) => setNewSymbol(e.target.value)}
          placeholder="e.g. AAPL"
          style={{ padding: "0.5rem", flex: 1 }}
        />
        <select
          value={newType}
          onChange={(e) => setNewType(e.target.value as "stock" | "index")}
          style={{ padding: "0.5rem" }}
        >
          <option value="stock">Stock</option>
          <option value="index">Index</option>
        </select>
        <button type="submit" style={{ padding: "0.5rem 1rem" }}>
          Add
        </button>
      </form>

      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {loading ? (
        <p>Loading...</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
              <th>Symbol</th>
              <th>Type</th>
              <th>Active</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "0.5rem 0" }}>{item.symbol}</td>
                <td>{item.type}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={item.active}
                    onChange={() => toggleActive(item)}
                  />
                </td>
                <td>
                  <button onClick={() => removeSymbol(item.id)} style={{ color: "crimson" }}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={4} style={{ padding: "1rem 0", color: "#888" }}>
                  No symbols yet — add one above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
