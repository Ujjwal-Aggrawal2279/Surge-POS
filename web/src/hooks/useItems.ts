import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import type { Item, ItemPrice, StockEntry, POSProfile } from "@/types/pos";

interface ItemsResponse {
  items: Item[];
  watermark: string | null;
  count: number;
  tombstones?: string[];
}

interface PricesResponse {
  prices: ItemPrice[];
  price_list: string;
  watermark: string | null;
  count: number;
}

interface StockResponse {
  stock: StockEntry[];
  watermark: string | null;
  count: number;
}

interface ProfilesResponse {
  profiles: POSProfile[];
}

export function useProfiles() {
  return useQuery({
    queryKey: ["pos-profiles"],
    queryFn: () => get<ProfilesResponse>("surge.api.items.get_pos_profiles"),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useItems(profile: string) {
  return useQuery({
    queryKey: ["items", profile],
    queryFn: async () => {
      const res = await get<ItemsResponse>("surge.api.items.get_items", { profile });
      if (res.tombstones?.length) {
        const dead = new Set(res.tombstones);
        res.items = res.items.filter((i) => !dead.has(i.item_code));
      }
      return res;
    },
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    refetchInterval: 60_000,   // safety net: catches missed realtime events
  });
}

export function useItemPrices(profile: string) {
  return useQuery({
    queryKey: ["item-prices", profile],
    queryFn: () =>
      get<PricesResponse>("surge.api.items.get_item_prices", { profile }),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    refetchInterval: 60_000,   // safety net: catches missed realtime events
  });
}

export function useStock(warehouse: string) {
  return useQuery({
    queryKey: ["stock", warehouse],
    queryFn: () =>
      get<StockResponse>("surge.api.stock.get_stock", { warehouse }),
    staleTime: 15_000,
    gcTime: 2 * 60_000,
    refetchInterval: 30_000,
  });
}
