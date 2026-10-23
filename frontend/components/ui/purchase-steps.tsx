import { ShoppingBag, MapPin, CreditCard } from "lucide-react";
const steps = [
  { label: "سبد خرید", Icon: ShoppingBag },
  { label: "تحویل و ثبت", Icon: MapPin },
  { label: "وضعیت پرداخت", Icon: CreditCard },
];
/** Location in the flow only; never implies a successful order or payment. */
export function PurchaseSteps({ current }: { current: 0 | 1 | 2 }) {
  return (
    <ol className="purchase-steps" aria-label="مراحل خرید">
      {steps.map(({ label, Icon }, index) => (
        <li key={label} aria-current={index === current ? "step" : undefined}>
          <Icon size={20} aria-hidden="true" />
          <span>{label}</span>
        </li>
      ))}
    </ol>
  );
}
