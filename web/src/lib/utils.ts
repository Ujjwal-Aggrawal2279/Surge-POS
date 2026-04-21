import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function paise(amount: number): number {
  return Math.round(amount * 100);
}

export function fromPaise(paise: number): number {
  return paise / 100;
}

export function formatCurrency(paise: number, currency = "INR"): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(paise / 100);
}

export function uuidv7(): string {
  const now = Date.now();
  const hi = Math.floor(now / 0x1000);
  const lo = now & 0xfff;
  const rand = crypto.getRandomValues(new Uint8Array(10));
  rand[0] = ((rand[0] ?? 0) & 0x0f) | 0x70; // version 7
  rand[2] = ((rand[2] ?? 0) & 0x3f) | 0x80; // variant
  const hex = [
    hi.toString(16).padStart(8, "0"),
    lo.toString(16).padStart(4, "0"),
    rand.slice(0, 2).reduce((s, b) => s + b.toString(16).padStart(2, "0"), ""),
    rand.slice(2, 4).reduce((s, b) => s + b.toString(16).padStart(2, "0"), ""),
    rand.slice(4).reduce((s, b) => s + b.toString(16).padStart(2, "0"), ""),
  ];
  return `${hex[0]}-${hex[1]}-${hex[2]}-${hex[3]}-${hex[4]}`;
}
