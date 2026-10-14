import type { Variant } from "@/lib/api/types";
export const buyable = (v: Variant) => v.is_active && v.inventory > 0;
export function variantFor(
  variants: Variant[],
  color: string | undefined,
  size: string | undefined,
) {
  return variants.find(
    (v) => v.color === color && v.size === size && buyable(v),
  );
}
export function sizesFor(variants: Variant[], color: string | undefined) {
  return [
    ...new Set(variants.filter((v) => v.color === color).map((v) => v.size)),
  ];
}
