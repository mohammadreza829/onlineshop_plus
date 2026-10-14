"use client";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Heart, ShoppingBag, Shirt } from "lucide-react";
import { useApi } from "@/lib/api/hooks";
import { api } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { ProductDetail, Page, Review, Product } from "@/lib/api/types";
import { toman, number, date } from "@/lib/format";
import { rememberProduct } from "@/lib/api/product-index";
import { buyable, sizesFor, variantFor } from "./variants";
import { ErrorNotice, Loading, Empty } from "@/components/ui/states";
import { useToast } from "@/components/providers";
import { ProductGrid } from "@/features/catalog/card";
function Reviews({ slug }: { slug: string }) {
  const p = "products/" + encodeURIComponent(slug) + "/reviews/",
    [offset, setOffset] = useState(0),
    q = useApi<Page<Review>>(p + "?offset=" + offset + "&limit=10"),
    mine = useApi<Review>(p + "mine/"),
    client = useQueryClient(),
    toast = useToast();
  const save = useMutation({
    mutationFn: (data: { rating: number; text: string }) =>
      api<Review>(p + "mine/", { method: "PUT", body: data }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: [p + "mine/"] });
      toast("نظر شما ثبت شد و پس از تایید مدیر منتشر می‌شود.");
    },
  });
  const remove = useMutation({
    mutationFn: () => api(p + "mine/", { method: "DELETE" }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: [p + "mine/"] });
      toast("نظر شما حذف شد.");
    },
  });
  return (
    <section className="stack" aria-labelledby="reviews-title">
      <h2 id="reviews-title">نظر خریداران</h2>
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorNotice error={q.error} retry={() => q.refetch()} />
      ) : q.data.results.length ? (
        q.data.results.map((review) => (
          <article className="review" key={review.id}>
            <div className="spread">
              <span>امتیاز {number(review.rating)} از ۵</span>
              <time className="small subtle">{date(review.created)}</time>
            </div>
            <p>{review.text}</p>
          </article>
        ))
      ) : (
        <p className="subtle">هنوز نظر تاییدشده‌ای ثبت نشده است.</p>
      )}
      {q.data && q.data.count > 10 && (
        <div className="row">
          <button
            className="button secondary"
            disabled={!offset}
            onClick={() => setOffset(offset - 10)}
          >
            قبل
          </button>
          <button
            className="button secondary"
            disabled={!q.data.next}
            onClick={() => setOffset(offset + 10)}
          >
            بعد
          </button>
        </div>
      )}
      {mine.error instanceof ApiError && mine.error.status === 401 ? (
        <Link
          className="text-link"
          href={"/login?next=" + encodeURIComponent("/products/" + slug)}
        >
          برای ثبت نظر وارد شوید
        </Link>
      ) : (
        <div className="panel stack">
          <h3>تجربهٔ خرید شما</h3>
          <p className="small subtle">
            ثبت و ویرایش فقط برای خریدار واجد شرایط است؛ امکان ثبت را سرور بررسی
            می‌کند. هر ویرایش دوباره در انتظار تایید قرار می‌گیرد.
          </p>
          {mine.data && (
            <p className="notice">
              وضعیت نظر:{" "}
              {mine.data.status === "pending"
                ? "در انتظار تایید"
                : mine.data.status === "approved"
                  ? "تاییدشده"
                  : "ردشده"}
            </p>
          )}
          <form
            className="stack"
            key={mine.data?.updated}
            onSubmit={(e) => {
              e.preventDefault();
              if (save.isPending) return;
              const f = new FormData(e.currentTarget);
              save.mutate({
                rating: Number(f.get("rating")),
                text: String(f.get("text")),
              });
            }}
          >
            <label className="field">
              امتیاز
              <select name="rating" defaultValue={mine.data?.rating ?? 5}>
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {number(n)} از ۵
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              متن نظر
              <textarea
                name="text"
                required
                minLength={1}
                maxLength={2000}
                defaultValue={mine.data?.text ?? ""}
              />
            </label>
            {save.isError && <ErrorNotice error={save.error} />}
            <div className="row">
              <button className="button secondary" disabled={save.isPending}>
                {save.isPending
                  ? "در حال ثبت…"
                  : mine.data
                    ? "ویرایش نظر"
                    : "ثبت نظر برای بررسی"}
              </button>
              {mine.data && (
                <button
                  className="text-link"
                  type="button"
                  disabled={remove.isPending}
                  onClick={() => remove.mutate()}
                >
                  حذف نظر من
                </button>
              )}
            </div>
            {remove.isError && <ErrorNotice error={remove.error} />}
          </form>
        </div>
      )}
    </section>
  );
}
export function ProductDetailView({ slug }: { slug: string }) {
  const q = useApi<ProductDetail>("products/" + encodeURIComponent(slug) + "/"),
    [color, setColor] = useState<string>(),
    [size, setSize] = useState<string>(),
    [quantity, setQuantity] = useState(1),
    [imageIndex, setImageIndex] = useState(0),
    client = useQueryClient(),
    toast = useToast(),
    router = useRouter();
  const add = useMutation({
    mutationFn: (body: unknown) => api("cart/", { method: "POST", body }),
    onSuccess: () => {
      if (q.data) rememberProduct(q.data);
      void client.invalidateQueries({ queryKey: ["cart/"] });
      toast(
        "انتخاب شما به سبد اضافه شد. تعداد و مبلغ نهایی را در سبد بررسی کنید.",
      );
    },
  });
  const favorite = useMutation({
    mutationFn: () =>
      api("products/" + q.data?.id + "/favorite/", { method: "PUT" }),
    onSuccess: () => {
      void client.invalidateQueries({
        queryKey: ["favorites/?limit=12&offset=0"],
      });
      toast("در علاقه‌مندی‌ها ذخیره شد.");
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401)
        router.push("/login?next=" + encodeURIComponent("/products/" + slug));
    },
  });
  const rec = useApi<Product[]>(
    "products/" + encodeURIComponent(slug) + "/recommendations/?limit=4",
  );
  if (q.isPending) return <Loading />;
  if (q.isError)
    return q.error instanceof ApiError && q.error.status === 404 ? (
      <Empty
        title="این لباس در دسترس نیست"
        description="ممکن است محصول غیرفعال یا حذف شده باشد."
        href="/products"
      />
    ) : (
      <ErrorNotice error={q.error} retry={() => q.refetch()} />
    );
  const p = q.data,
    variants = p.variants,
    selected = variantFor(variants, color, size),
    stock = variants.length ? (selected?.inventory ?? 0) : p.inventory,
    price = selected?.final_price ?? p.final_price,
    images = [...p.images].sort(
      (a, b) =>
        Number(b.is_primary) - Number(a.is_primary) || a.order - b.order,
    ),
    image = images[imageIndex] ?? images[0];
  const canBuy = stock > 0 && (!variants.length || !!selected);
  return (
    <>
      <nav className="breadcrumb" aria-label="مسیر صفحه">
        <Link href="/products">فروشگاه</Link>
        <span>/</span>
        {p.category && (
          <Link
            href={"/products?category=" + encodeURIComponent(p.category.slug)}
          >
            {p.category.name}
          </Link>
        )}
        <span>/</span>
        <span>{p.name}</span>
      </nav>
      <div className="product-layout">
        <section aria-label="تصاویر محصول">
          <div className="product-media">
            {image?.image ? (
              <Image
                src={image.image}
                alt={image.description || p.name}
                width={780}
                height={1040}
                unoptimized
                priority
              />
            ) : (
              <div className="placeholder">
                <Shirt size={60} strokeWidth={1} />
                <span>برای این محصول تصویری ثبت نشده است.</span>
              </div>
            )}
          </div>
          {images.length > 1 && (
            <div className="gallery-thumbs">
              {images.map((im, i) => (
                <button
                  key={im.id}
                  aria-label={"تصویر " + number(i + 1)}
                  aria-pressed={imageIndex === i}
                  onClick={() => setImageIndex(i)}
                >
                  <Image
                    src={im.image}
                    alt={im.description || p.name}
                    width={70}
                    height={90}
                    unoptimized
                  />
                </button>
              ))}
            </div>
          )}
        </section>
        <section className="product-info stack">
          <div>
            <p className="eyebrow">
              {p.category?.name ?? "لباس"} /{" "}
              <span dir="ltr">{selected?.sku ?? p.sku}</span>
            </p>
            <h1>{p.name}</h1>
          </div>
          <div aria-live="polite">
            <p className="price-large">
              {variants.length && !selected ? "قیمت پایه: " : ""}
              {toman(price)}
            </p>
            {p.off > 0 && (
              <p className="small subtle">
                تخفیف محصول: {number(p.off)}٪؛ مبلغ انتخاب از سرور دریافت شده
                است.
              </p>
            )}
            {variants.length > 0 && !selected && (
              <p className="small subtle">
                قیمت قابل پرداخت پس از انتخاب رنگ و سایز مشخص می‌شود.
              </p>
            )}
          </div>
          {variants.length > 0 && (
            <>
              <fieldset>
                <legend>رنگ{color ? " / " + color : ""}</legend>
                <div className="choice-group">
                  {[...new Set(variants.map((v) => v.color))].map((c) => (
                    <button
                      className="choice"
                      key={c}
                      aria-pressed={c === color}
                      disabled={
                        !variants.some((v) => v.color === c && buyable(v))
                      }
                      onClick={() => {
                        setColor(c);
                        if (!variantFor(variants, c, size)) setSize(undefined);
                      }}
                    >
                      {c || "بدون رنگ"}
                      {!variants.some((v) => v.color === c && buyable(v))
                        ? " — ناموجود"
                        : ""}
                    </button>
                  ))}
                </div>
              </fieldset>
              <fieldset disabled={color === undefined}>
                <legend>سایز</legend>
                <div className="choice-group">
                  {sizesFor(variants, color).map((s) => (
                    <button
                      className="choice"
                      key={s}
                      aria-pressed={s === size}
                      disabled={!variantFor(variants, color, s)}
                      onClick={() => setSize(s)}
                    >
                      {s || "بدون سایز"}
                      {!variantFor(variants, color, s) ? " — ناموجود" : ""}
                    </button>
                  ))}
                </div>
                {color === undefined && (
                  <p className="small subtle">ابتدا رنگ را انتخاب کنید.</p>
                )}
              </fieldset>
            </>
          )}
          <p className="small" aria-live="polite">
            {stock > 0
              ? "موجود برای انتخاب شما"
              : variants.length && !selected
                ? "رنگ و سایز موجود را انتخاب کنید."
                : "در حال حاضر ناموجود است."}
          </p>
          <div className="row">
            <label className="field">
              تعداد
              <input
                className="quantity"
                type="number"
                min={1}
                max={Math.max(1, Math.min(stock, 100))}
                value={quantity}
                onChange={(e) =>
                  setQuantity(
                    Math.max(1, Math.min(100, Number(e.target.value) || 1)),
                  )
                }
              />
            </label>
            <button
              className="button"
              style={{ flex: 1, alignSelf: "end" }}
              disabled={!canBuy || quantity > stock || add.isPending}
              onClick={() =>
                add.mutate({
                  product_id: p.id,
                  quantity,
                  ...(selected ? { variant_id: selected.id } : {}),
                })
              }
            >
              <ShoppingBag size={19} />
              {add.isPending ? "در حال افزودن…" : "افزودن به سبد"}
            </button>
            <button
              className="icon-button"
              style={{ alignSelf: "end" }}
              aria-label="ذخیره در علاقه‌مندی‌ها"
              disabled={favorite.isPending}
              onClick={() => favorite.mutate()}
            >
              <Heart size={22} />
            </button>
          </div>
          {add.isError && <ErrorNotice error={add.error} />}{" "}
          {favorite.isError &&
            !(
              favorite.error instanceof ApiError &&
              favorite.error.status === 401
            ) && <ErrorNotice error={favorite.error} />}
          <p className="small subtle">
            افزودن به سبد رزرو موجودی نیست؛ قیمت و موجودی هنگام ثبت سفارش بررسی
            می‌شوند.
          </p>
          <details className="accordion" open>
            <summary>دربارهٔ این لباس</summary>
            <div>
              {p.description || "توضیح بیشتری برای این محصول ثبت نشده است."}
            </div>
          </details>
          {p.features.length > 0 && (
            <details className="accordion">
              <summary>ویژگی‌های محصول</summary>
              <div>
                {p.features.map((f) => (
                  <p key={f.id}>
                    {f.name}: {f.value}
                  </p>
                ))}
              </div>
            </details>
          )}
          <p className="subtle small">
            {p.rating_average === null
              ? "هنوز امتیازی ثبت نشده است."
              : `امتیاز ${number(p.rating_average)} از ۵ — ${number(p.rating_count)} نظر تاییدشده`}
          </p>
        </section>
      </div>
      <div className="section">
        <Reviews slug={slug} />
      </div>
      {rec.data && rec.data.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>انتخاب‌های دیگر</h2>
            <Link className="text-link" href="/products">
              همهٔ لباس‌ها
            </Link>
          </div>
          <ProductGrid products={rec.data} />
        </section>
      )}
    </>
  );
}
