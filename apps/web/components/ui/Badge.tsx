const VARIANT_STYLES: Record<string, string> = {
  success: "bg-green-100 text-green-800",
  warning: "bg-amber-100 text-amber-800",
  danger: "bg-red-100 text-red-800",
  neutral: "bg-slate-100 text-slate-700",
  info: "bg-brand-blue/10 text-brand-blue",
};

export function Badge({
  label,
  variant = "neutral",
}: {
  label: string;
  variant?: keyof typeof VARIANT_STYLES;
}) {
  return (
    <span
      className={`inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${VARIANT_STYLES[variant]}`}
    >
      {label}
    </span>
  );
}
