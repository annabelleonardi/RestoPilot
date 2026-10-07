export const formatIDR = (n: number): string =>
  new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(n);

export const formatCompactIDR = (n: number): string =>
  `Rp ${(n / 1_000_000).toFixed(1)}M`;

export const formatPct = (n: number): string =>
  `${n > 0 ? "+" : ""}${n.toFixed(1)}%`;
