"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/api/hooks";
import type { Address, ClientOptions, Page } from "@/lib/api/types";
import { phone, ascii } from "@/lib/format";
import { ErrorNotice, Loading, Empty } from "@/components/ui/states";
import { useToast } from "@/components/providers";
const schema = z.object({
  title: z.string().trim().min(1, "عنوان لازم است.").max(100),
  receiver_name: z.string().trim().min(1, "نام لازم است.").max(100),
  receiver_phone: z
    .string()
    .transform(phone)
    .refine((v) => /^09\d{9}$/.test(v), "شمارهٔ همراه معتبر وارد کنید."),
  province: z.string().min(1, "استان را انتخاب کنید."),
  city: z.string().trim().min(1, "شهر لازم است.").max(100),
  full_address: z.string().trim().min(1, "نشانی لازم است."),
  postal_code: z
    .string()
    .transform((v) => ascii(v).replace(/[\s-]/g, ""))
    .refine((v) => /^\d{10}$/.test(v), "کد پستی باید ۱۰ رقم باشد."),
  is_default: z.boolean(),
});
export function AddressForm({
  address,
  onDone,
}: {
  address?: Address;
  onDone: () => void;
}) {
  const options = useApi<ClientOptions>("client-options/"),
    client = useQueryClient();
  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      title: address?.title ?? "",
      receiver_name: address?.receiver_name ?? "",
      receiver_phone: address?.receiver_phone ?? "",
      province: address?.province ?? "",
      city: address?.city ?? "",
      full_address: address?.full_address ?? "",
      postal_code: address?.postal_code ?? "",
      is_default: address?.is_default ?? false,
    },
  });
  const save = useMutation({
    mutationFn: (body: unknown) =>
      api(address ? "addresses/" + address.id + "/" : "addresses/", {
        method: address ? "PATCH" : "POST",
        body,
      }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["addresses/?limit=100"] });
      onDone();
    },
  });
  const labels = {
    title: "عنوان آدرس",
    receiver_name: "نام تحویل‌گیرنده",
    receiver_phone: "شمارهٔ تحویل‌گیرنده",
    city: "شهر",
    postal_code: "کد پستی",
  } as const;
  return (
    <form
      className="panel stack"
      onSubmit={form.handleSubmit((v) => {
        if (!save.isPending) save.mutate(v);
      })}
    >
      <h3>{address ? "ویرایش آدرس" : "آدرس جدید"}</h3>
      <div className="form-grid">
        {Object.entries(labels).map(([key, label]) => {
          const k = key as keyof typeof labels;
          return (
            <label className="field" key={k}>
              {label}
              <input
                {...form.register(k)}
                dir={
                  ["receiver_phone", "postal_code"].includes(k)
                    ? "ltr"
                    : undefined
                }
                autoComplete={
                  k === "postal_code"
                    ? "postal-code"
                    : k === "receiver_phone"
                      ? "tel"
                      : undefined
                }
                inputMode={
                  k === "receiver_phone"
                    ? "tel"
                    : k === "postal_code"
                      ? "numeric"
                      : "text"
                }
              />
              {form.formState.errors[k] && (
                <span className="field-error">
                  {form.formState.errors[k]?.message}
                </span>
              )}
            </label>
          );
        })}
        <label className="field">
          استان
          <select {...form.register("province")} disabled={!options.data}>
            <option value="">انتخاب استان</option>
            {options.data?.provinces.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
          {form.formState.errors.province && (
            <span className="field-error">
              {form.formState.errors.province.message}
            </span>
          )}
        </label>
        <label className="field full">
          نشانی دقیق
          <textarea
            {...form.register("full_address")}
            autoComplete="street-address"
          />
          {form.formState.errors.full_address && (
            <span className="field-error">
              {form.formState.errors.full_address.message}
            </span>
          )}
        </label>
      </div>
      <label className="row small">
        <input type="checkbox" {...form.register("is_default")} />
        آدرس پیش‌فرض من
      </label>
      <p className="small subtle">
        فقط استان‌های موجود در فهرست پشتیبانی می‌شوند؛ شهر را مطابق نشانی واقعی
        وارد کنید.
      </p>
      {options.isError && (
        <ErrorNotice error={options.error} retry={() => options.refetch()} />
      )}{" "}
      {save.isError && <ErrorNotice error={save.error} />}
      <div className="row">
        <button className="button" disabled={save.isPending || !options.data}>
          {save.isPending ? "در حال ذخیره…" : "ذخیرهٔ آدرس"}
        </button>
        <button className="button secondary" type="button" onClick={onDone}>
          انصراف
        </button>
      </div>
    </form>
  );
}
export function Addresses({
  select,
  selected,
}: {
  select?: (id: number) => void;
  selected?: number;
}) {
  const q = useApi<Page<Address>>("addresses/?limit=100"),
    [form, setForm] = useState<Address | "new" | undefined>(),
    [offset, setOffset] = useState(0),
    more = useApi<Page<Address>>(
      "addresses/?limit=100&offset=" + offset,
      offset > 0,
    ),
    client = useQueryClient(),
    toast = useToast();
  const remove = useMutation({
    mutationFn: (id: number) =>
      api("addresses/" + id + "/", { method: "DELETE" }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["addresses/?limit=100"] });
      void client.invalidateQueries({
        queryKey: ["addresses/?limit=100&offset=" + offset],
      });
      toast("آدرس حذف شد.");
    },
  });
  const active = offset > 0 ? more : q;
  return (
    <div className="stack">
      <div className="spread">
        <h2>{select ? "نشانی تحویل" : "آدرس‌های من"}</h2>
        <button className="button secondary" onClick={() => setForm("new")}>
          آدرس جدید
        </button>
      </div>
      {form && (
        <AddressForm
          key={form === "new" ? "new" : form.id}
          address={form === "new" ? undefined : form}
          onDone={() => setForm(undefined)}
        />
      )}{" "}
      {active.isPending ? (
        <Loading />
      ) : active.isError ? (
        <ErrorNotice error={active.error} retry={() => active.refetch()} />
      ) : active.data.results.length ? (
        active.data.results.map((a) => (
          <article
            className={
              "panel stack address-card" +
              (select && selected === a.id ? " selected" : "")
            }
            key={a.id}
          >
            {select ? (
              <label className="row address-selection">
                <input
                  type="radio"
                  name="address-selection"
                  value={a.id}
                  checked={selected === a.id}
                  onChange={() => select(a.id)}
                />
                <strong>{a.title}</strong>
                {a.is_default && <span className="badge">پیش‌فرض</span>}
              </label>
            ) : (
              <h3>
                {a.title}{" "}
                {a.is_default && <span className="badge">پیش‌فرض</span>}
              </h3>
            )}
            <p>
              {a.receiver_name} · {a.city}
              <br />
              {a.full_address}
            </p>
            <p className="small subtle">
              کد پستی: <bdi dir="ltr">{a.postal_code}</bdi> · تلفن:{" "}
              <bdi dir="ltr">{a.receiver_phone}</bdi>
            </p>
            <div className="row">
              <button className="text-link" onClick={() => setForm(a)}>
                ویرایش
              </button>
              <button
                className="text-link"
                disabled={remove.isPending}
                onClick={() => {
                  if (window.confirm("این آدرس حذف شود؟")) remove.mutate(a.id);
                }}
              >
                حذف آدرس
              </button>
            </div>
          </article>
        ))
      ) : (
        <Empty
          title="آدرسی ثبت نشده است"
          description="برای تحویل سفارش، نشانی واقعی خود را اضافه کنید."
        />
      )}
      {active.data && (offset > 0 || active.data.next) && (
        <nav className="row">
          <button
            className="button secondary"
            disabled={!offset}
            onClick={() => setOffset(Math.max(0, offset - 100))}
          >
            قبل
          </button>
          <button
            className="button secondary"
            disabled={!active.data.next}
            onClick={() => setOffset(offset + 100)}
          >
            بعد
          </button>
        </nav>
      )}
      {remove.isError && <ErrorNotice error={remove.error} />}
    </div>
  );
}
