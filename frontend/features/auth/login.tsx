"use client";
import { site } from "@/config/site";
import { useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { api, resetCSRF } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { ascii, phone, number } from "@/lib/format";
import { internalRedirect } from "@/lib/api/filters";
import { ErrorNotice } from "@/components/ui/states";
const schema = z.object({
  phone: z
    .string()
    .transform(phone)
    .refine((v) => /^09\d{9}$/.test(v), "شمارهٔ همراه معتبر وارد کنید."),
});
export function Login() {
  const [step, setStep] = useState<"phone" | "code">("phone"),
    [mobile, setMobile] = useState(""),
    [code, setCode] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(),
    [until, setUntil] = useState(0),
    [seconds, setSeconds] = useState(0),
    otpRef = useRef<HTMLInputElement>(null),
    lock = useRef(false),
    router = useRouter(),
    search = useSearchParams(),
    client = useQueryClient();
  useEffect(() => {
    if (step === "code") otpRef.current?.focus();
  }, [step]);
  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: { phone: "" },
  });
  useEffect(() => {
    const tick = () =>
      setSeconds(Math.max(0, Math.ceil((until - Date.now()) / 1000)));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [until]);
  async function request(value: string) {
    if (lock.current || Date.now() < until) return;
    lock.current = true;
    setBusy(true);
    setError(undefined);
    try {
      await api("auth/otp/request/", {
        method: "POST",
        body: { phone: value },
      });
      setMobile(value);
      setStep("code");
      setUntil(Date.now() + site.otpResendSeconds * 1000);
    } catch (e) {
      setError(e);
      if (e instanceof ApiError && e.retryAfter)
        setUntil(Date.now() + e.retryAfter * 1000);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  async function verify() {
    if (
      lock.current ||
      (Date.now() < until && error instanceof ApiError && error.status === 429)
    )
      return;
    const normalized = ascii(code).trim();
    if (!/^\d{6}$/.test(normalized)) {
      setError(new Error("کد شش‌رقمی را وارد کنید."));
      return;
    }
    lock.current = true;
    setBusy(true);
    setError(undefined);
    try {
      await api("auth/otp/verify/", {
        method: "POST",
        body: { phone: mobile, code: normalized },
      });
      resetCSRF();
      await client.cancelQueries();
      client.clear();
      const ch = new BroadcastChannel("osp-auth");
      ch.postMessage("login");
      ch.close();
      router.replace(internalRedirect(search.get("next")));
      router.refresh();
    } catch (e) {
      setError(e);
      if (e instanceof ApiError && e.retryAfter)
        setUntil(Date.now() + e.retryAfter * 1000);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  return (
    <div className="panel auth-panel stack">
      <p className="eyebrow">حساب کاربری / ورود امن</p>
      <h1 style={{ fontSize: 30 }}>
        {step === "phone" ? "خوش آمدید." : "کد تایید را وارد کنید."}
      </h1>
      <p className="subtle small">
        {step === "phone" ? (
          "شمارهٔ همراه خود را وارد کنید تا درخواست کد ثبت شود."
        ) : (
          <>
            درخواست ارسال برای <bdi dir="ltr">{mobile}</bdi> ثبت شد. دریافت
            پیامک ممکن است کمی زمان ببرد.
          </>
        )}
      </p>
      {step === "phone" ? (
        <form
          className="stack"
          onSubmit={(e) => {
            void form.handleSubmit((v) => request(v.phone))(e);
          }}
        >
          <label className="field">
            شمارهٔ همراه
            <input
              {...form.register("phone")}
              dir="ltr"
              inputMode="tel"
              autoComplete="tel"
              placeholder="09xxxxxxxxx"
              aria-invalid={!!form.formState.errors.phone}
            />
          </label>
          {form.formState.errors.phone && (
            <p className="field-error">{form.formState.errors.phone.message}</p>
          )}
          <button className="button" disabled={busy || seconds > 0}>
            {busy ? "در حال درخواست…" : "دریافت کد تایید"}
          </button>
        </form>
      ) : (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            void verify();
          }}
        >
          <label className="field">
            کد تایید شش‌رقمی
            <input
              dir="ltr"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(ascii(e.target.value).slice(0, 6))}
              maxLength={6}
              ref={otpRef}
            />
          </label>
          <button
            className="button"
            disabled={
              busy ||
              (error instanceof ApiError && error.status === 429 && seconds > 0)
            }
          >
            {busy ? "در حال بررسی…" : "تایید و ورود"}
          </button>
          <div className="spread">
            <button
              className="text-link"
              type="button"
              disabled={busy || seconds > 0}
              onClick={() => request(mobile)}
            >
              {seconds > 0
                ? `ارسال دوباره تا ${number(seconds)} ثانیه دیگر`
                : "ارسال دوبارهٔ کد"}
            </button>
            <button
              type="button"
              className="text-link"
              disabled={busy}
              onClick={() => {
                setStep("phone");
                setError(undefined);
                setCode("");
              }}
            >
              تغییر شماره
            </button>
          </div>
        </form>
      )}
      {error !== undefined && <ErrorNotice error={error} />}{" "}
      {step === "phone" && seconds > 0 && (
        <p className="small" role="status">
          تلاش بعدی پس از {number(seconds)} ثانیه
        </p>
      )}
    </div>
  );
}
