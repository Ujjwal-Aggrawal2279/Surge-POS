import { useState, useMemo, useCallback } from "react";
import {
  Search,
  Wine, Beer, Coffee, Milk, GlassWater,
  Cigarette, Cookie, Apple, Leaf, Wheat, Grape, Candy, Package,
  type LucideIcon,
} from "lucide-react";
import { useCartStore } from "@/stores/cart";
import { formatCurrency, cn } from "@/lib/utils";
import type { Item, ItemPrice, StockEntry, Cashier } from "@/types/pos";

const GROUP_ICON_MAP: Array<{
  keywords: string[];
  Icon: LucideIcon;
  bg: string;
  fg: string;
}> = [
  { keywords: ["whisky","whiskey","scotch","bourbon","rum","vodka","gin","brandy","tequila","spirit","liquor","wine","champagne","prosecco"], Icon: Wine,       bg: "bg-purple-50",  fg: "text-purple-400" },
  { keywords: ["beer","lager","ale","stout","porter","pilsner","craft","cider"],                                                              Icon: Beer,       bg: "bg-amber-50",   fg: "text-amber-500"  },
  { keywords: ["coffee","espresso","latte","cappuccino","tea","chai","brew"],                                                                 Icon: Coffee,     bg: "bg-stone-50",   fg: "text-stone-400"  },
  { keywords: ["milk","dairy","cream","curd","yogurt","paneer","butter","ghee","cheese"],                                                    Icon: Milk,       bg: "bg-sky-50",     fg: "text-sky-400"    },
  { keywords: ["water","juice","soda","soft drink","cola","beverage","drink","mocktail","cocktail","energy"],                                Icon: GlassWater, bg: "bg-cyan-50",    fg: "text-cyan-400"   },
  { keywords: ["grape","wine grape","raisin"],                                                                                               Icon: Grape,      bg: "bg-violet-50",  fg: "text-violet-400" },
  { keywords: ["tobacco","cigarette","cigar","hookah","vape","pan","gutka"],                                                                 Icon: Cigarette,  bg: "bg-zinc-50",    fg: "text-zinc-400"   },
  { keywords: ["snack","chips","namkeen","nuts","biscuit","cracker","popcorn"],                                                              Icon: Cookie,     bg: "bg-orange-50",  fg: "text-orange-400" },
  { keywords: ["fruit","fresh","vegetable","produce","salad"],                                                                               Icon: Apple,      bg: "bg-green-50",   fg: "text-green-400"  },
  { keywords: ["herb","spice","organic","natural","leaf","tulsi","mint"],                                                                    Icon: Leaf,       bg: "bg-emerald-50", fg: "text-emerald-400"},
  { keywords: ["wheat","grain","flour","bread","atta","cereal","rice","dal"],                                                                Icon: Wheat,      bg: "bg-yellow-50",  fg: "text-yellow-500" },
  { keywords: ["candy","sweet","chocolate","mithai","confection","dessert"],                                                                 Icon: Candy,      bg: "bg-pink-50",    fg: "text-pink-400"   },
];

function getGroupStyle(itemGroup: string): { Icon: LucideIcon; bg: string; fg: string } {
  const g = itemGroup.toLowerCase();
  for (const entry of GROUP_ICON_MAP) {
    if (entry.keywords.some((k) => g.includes(k))) return entry;
  }
  return { Icon: Package, bg: "bg-muted", fg: "text-muted-foreground/40" };
}

interface Props {
  items: Item[];
  prices: Map<string, number>;
  stock: Map<string, number>;
  warehouse: string;
  cashier: Cashier;
}

export function ItemGrid({ items, prices, stock, warehouse, cashier }: Props) {
  const [search, setSearch] = useState("");
  const [activeGroup, setActiveGroup] = useState("All");
  const addItem = useCartStore((s) => s.addItem);
  const updateQty = useCartStore((s) => s.updateQty);
  const cartItems = useCartStore((s) => s.items);

  const categories = useMemo(() => {
    const groups = [...new Set(items.map((i) => i.item_group))].filter(Boolean).sort();
    return ["All", ...groups];
  }, [items]);

  const filtered = useMemo(() => {
    let list = items;
    if (activeGroup !== "All") list = list.filter((i) => i.item_group === activeGroup);
    const q = search.toLowerCase().trim();
    if (q)
      list = list.filter(
        (i) =>
          i.item_name.toLowerCase().includes(q) ||
          i.item_code.toLowerCase().includes(q) ||
          i.barcodes.some((b) => b.toLowerCase().includes(q)),
      );
    return list;
  }, [items, search, activeGroup]);

  const cartMap = useMemo(
    () => new Map(cartItems.map((i) => [i.item_code, i.qty])),
    [cartItems],
  );

  const handleAdd = useCallback(
    (item: Item) => {
      addItem({
        item_code: item.item_code,
        item_name: item.item_name,
        rate_paise: prices.get(item.item_code) ?? 0,
        discount_paise: 0,
        warehouse,
      });
    },
    [prices, warehouse, addItem],
  );

  const today = new Date().toLocaleDateString("en-IN", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="flex h-full flex-col gap-4">

      <div className="flex shrink-0 items-center justify-between gap-4">
        <div>
          <p className="text-base font-bold text-[#212B36]">Welcome, {cashier.full_name}</p>
          <p className="text-sm font-normal text-[#646B72]">{today}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#A6AAAF]" />
            <input
              type="text"
              placeholder="Search Product"
              className="h-8.5 w-64 rounded-[5px] border border-[#E6EAED] bg-white pl-8 pr-3 text-xs text-[#212B36] placeholder:text-[#A6AAAF] outline-none focus:border-[#FE9F43]"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key !== "Enter") return;
                const q = search.trim();
                if (!q) return;
                const exact =
                  filtered.find((i) => i.barcodes.some((b) => b === q)) ??
                  filtered.find((i) => i.item_code === q);
                if (exact) {
                  handleAdd(exact);
                  setSearch("");
                }
              }}
              autoFocus
            />
          </div>
          <button
            type="button"
            onClick={() => setActiveGroup("All")}
            className="h-7.5 rounded-[5px] bg-[#FF9025] px-4 text-xs font-medium text-white transition-colors hover:bg-[#e8821e]"
          >
            View All Categories
          </button>
        </div>
      </div>

      <div className="flex shrink-0 gap-2 overflow-x-auto pb-0.5 [scrollbar-width:none]">
        {categories.map((cat) => {
          const isAll = cat === "All";
          const { Icon: GroupIcon, fg } = isAll ? { Icon: null, fg: "" } : getGroupStyle(cat);
          return (
            <button
              key={cat}
              type="button"
              onClick={() => setActiveGroup(cat)}
              className={cn(
                "flex h-9.25 shrink-0 items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-sm font-medium text-[#212B36] transition-all",
                "shadow-[0px_4px_60px_rgba(231,231,231,0.47)]",
                activeGroup === cat
                  ? "border-2 border-[#FE9F43]"
                  : "border border-[#E6EAED] hover:border-[#FE9F43]/60",
              )}
            >
              {isAll ? (
                <img
                  src="/assets/surge/images/categories/all.png"
                  alt="All"
                  className="h-5 w-5 object-contain"
                />
              ) : (
                GroupIcon && <GroupIcon className={cn("h-4 w-4 shrink-0", fg)} />
              )}
              {cat}
            </button>
          );
        })}
      </div>

      <div className="grid auto-rows-max gap-2.75 overflow-y-auto pb-2 grid-cols-[repeat(auto-fill,minmax(160px,1fr))]">
        {filtered.map((item) => {
          const qty = stock.get(item.item_code) ?? 0;
          const rate = prices.get(item.item_code) ?? 0;
          const outOfStock = qty <= 0;
          const inCart = cartMap.get(item.item_code) ?? 0;

          const { Icon: GroupIcon, bg: groupBg, fg: groupFg } = getGroupStyle(item.item_group);

          return (
            <div
              key={item.item_code}
              onClick={() => !outOfStock && handleAdd(item)}
              className={cn(
                "relative flex flex-col overflow-hidden rounded-[10px] bg-white transition-all",
                "shadow-[0px_4px_60px_rgba(231,231,231,0.47)]",
                outOfStock
                  ? "cursor-not-allowed opacity-50 border border-[#E6EAED]"
                  : inCart > 0
                    ? "cursor-pointer border-2 border-[#FE9F43] hover:shadow-md active:scale-[0.98]"
                    : "cursor-pointer border border-[#E6EAED] hover:border-[#FE9F43] hover:shadow-md active:scale-[0.98]",
              )}
            >
              <div className={cn("relative h-29.25 overflow-hidden rounded-t-[10px]", groupBg)}>
                {item.image ? (
                  <img
                    src={item.image}
                    alt={item.item_name}
                    className="h-full w-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center">
                    <GroupIcon className={cn("h-12 w-12", groupFg)} strokeWidth={1.25} />
                  </div>
                )}

                {inCart > 0 && (
                  <span className="absolute left-2 top-2 flex h-5 min-w-5 items-center justify-center rounded-full bg-[#6938EF] px-1.5 text-[10px] font-bold text-white">
                    {inCart}
                  </span>
                )}

                {!outOfStock && (
                  inCart > 0 ? (
                    <button
                      type="button"
                      title={`Remove one ${item.item_name} from cart`}
                      onClick={(e) => {
                        e.stopPropagation();
                        updateQty(item.item_code, inCart - 1);
                      }}
                      className="absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-red-500 text-white shadow-md transition-all hover:bg-red-600 active:scale-95"
                    >
                      <svg width="8" height="2" viewBox="0 0 10 2" fill="none" aria-hidden="true">
                        <path d="M1 1h8" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
                      </svg>
                    </button>
                  ) : (
                    <button
                      type="button"
                      title={`Add ${item.item_name} to cart`}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAdd(item);
                      }}
                      className="absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-[#3EB780] text-white shadow-md transition-all hover:bg-[#32a36d] active:scale-95"
                    >
                      <svg width="8" height="8" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                        <path d="M5 1v8M1 5h8" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
                      </svg>
                    </button>
                  )
                )}
              </div>

              <div className="flex h-18.5 flex-col justify-center gap-1 px-4 py-3">
                <p className="truncate text-sm font-bold leading-5.25 text-[#212B36]">
                  {item.item_name}
                </p>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-[#0E9384]">{formatCurrency(rate)}</span>
                  <span className="text-sm text-[#DD2590]">
                    {outOfStock ? "Out" : `${qty} Pcs`}
                  </span>
                </div>
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <p className="col-span-full py-16 text-center text-sm text-[#646B72]">No items found</p>
        )}
      </div>
    </div>
  );
}

export function buildPriceMap(prices: ItemPrice[]): Map<string, number> {
  return new Map(prices.map((p) => [p.item_code, Math.round(p.price_list_rate * 100)]));
}

export function buildStockMap(stock: StockEntry[]): Map<string, number> {
  return new Map(stock.map((s) => [s.item_code, s.actual_qty]));
}
