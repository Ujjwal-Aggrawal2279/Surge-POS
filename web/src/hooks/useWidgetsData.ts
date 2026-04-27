import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import type { WidgetsData } from "@/types/pos";

const PLACEHOLDER: WidgetsData = { top_products: [], low_stock: [], recent_items: [] };

export function useWidgetsData() {
  return useQuery<WidgetsData>({
    queryKey: ["widgets-data"],
    queryFn: () => get<WidgetsData>("surge.api.dashboard.get_widgets_data"),
    staleTime: 120_000,
    placeholderData: PLACEHOLDER,
  });
}
