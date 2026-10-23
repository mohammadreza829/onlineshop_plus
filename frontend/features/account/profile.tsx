"use client";
import { Package, Heart, MapPin, ArrowLeft } from "lucide-react";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { useApi } from "@/lib/api/hooks";
import { api, resetCSRF } from "@/lib/api/client";
import type { User } from "@/lib/api/types";
import { ErrorNotice, Loading } from "@/components/ui/states";
import { useToast } from "@/components/providers";
export function Profile({ overview = false }: { overview?: boolean }) {
  const q = useApi<User>("me/"),
    client = useQueryClient(),
    router = useRouter(),
    toast = useToast(),
    [logoutError, setLogoutError] = useState<unknown>(),
    [loggingOut, setLoggingOut] = useState(false);
  const edit = useMutation({
    mutationFn: (data: unknown) =>
      api<User>("me/", { method: "PATCH", body: data }),
    onSuccess: (data) => {
      client.setQueryData(["me/"], data);
      toast("مشخصات شما به‌روز شد.");
    },
  });
  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true);
    setLogoutError(undefined);
    try {
      await api("auth/logout/", { method: "POST" });
    } catch (e) {
      setLogoutError(e);
    } finally {
      resetCSRF();
      await client.cancelQueries();
      client.clear();
      const ch = new BroadcastChannel("osp-auth");
      ch.postMessage("logout");
      ch.close();
      setLoggingOut(false);
      router.refresh();
    }
  }
  if (q.isPending) return <Loading />;
  if (q.isError) return <ErrorNotice error={q.error} />;
  return (
    <div className="panel stack">
      <h2>
        {overview
          ? "خوش آمدید، " + (q.data.first_name || "همراه گرامی")
          : "مشخصات من"}
      </h2>
      <p className="small subtle">
        شمارهٔ همراه: <bdi dir="ltr">{q.data.phone}</bdi>
      </p>
      {overview ? (
        <>
          <p>
            سفارش‌ها، آدرس‌ها و انتخاب‌های ذخیره‌شدهٔ شما در این بخش در
            دسترس‌اند.
          </p>
          <div className="account-shortcuts">
            <Link href="/account/orders">
              <Package size={24} aria-hidden="true" />
              <span>
                سفارش‌های من<small>جزئیات و پیگیری سفارش</small>
              </span>
              <ArrowLeft size={18} aria-hidden="true" />
            </Link>
            <Link href="/account/favorites">
              <Heart size={24} aria-hidden="true" />
              <span>
                علاقه‌مندی‌ها<small>انتخاب‌های ذخیره‌شدهٔ شما</small>
              </span>
              <ArrowLeft size={18} aria-hidden="true" />
            </Link>
            <Link href="/account/addresses">
              <MapPin size={24} aria-hidden="true" />
              <span>
                آدرس‌های من<small>مدیریت نشانی‌های تحویل</small>
              </span>
              <ArrowLeft size={18} aria-hidden="true" />
            </Link>
          </div>
        </>
      ) : (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            if (edit.isPending) return;
            const f = new FormData(e.currentTarget);
            edit.mutate({
              first_name: f.get("first_name"),
              last_name: f.get("last_name"),
            });
          }}
        >
          <div className="form-grid">
            <label className="field">
              نام
              <input
                name="first_name"
                maxLength={150}
                autoComplete="given-name"
                defaultValue={q.data.first_name}
              />
            </label>
            <label className="field">
              نام خانوادگی
              <input
                name="last_name"
                maxLength={150}
                autoComplete="family-name"
                defaultValue={q.data.last_name}
              />
            </label>
          </div>
          {edit.isError && <ErrorNotice error={edit.error} />}
          <button className="button" disabled={edit.isPending}>
            ذخیرهٔ مشخصات
          </button>
        </form>
      )}
      <button className="text-link" disabled={loggingOut} onClick={logout}>
        خروج از حساب
      </button>
      {logoutError !== undefined && <ErrorNotice error={logoutError} />}
    </div>
  );
}
