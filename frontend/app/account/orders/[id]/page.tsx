import { notFound } from "next/navigation";
import { cookies } from "next/headers";
import { OrderDetail } from "@/features/account/orders";
import { configuration, names } from "@/lib/auth/bff";
import { unseal } from "@/lib/auth/crypto";
export const dynamic = "force-dynamic";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!/^[1-9]\d*$/.test(id)) notFound();
  // Read-only existence/ownership check: never refresh in a Server Component, where
  // rotated cookies could not be delivered back to the browser.
  try {
    const c = configuration(),
      jar = await cookies(),
      access = unseal<string>(jar.get(names(c).access)?.value, c.secret);
    if (access) {
      const response = await fetch(c.upstream + "/api/v1/orders/" + id + "/", {
        headers: { Authorization: "Bearer " + access },
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(5000),
      });
      if (response.status === 404) notFound();
    }
  } catch (e) {
    if (e instanceof Error && e.message.includes("NEXT_HTTP_ERROR_FALLBACK"))
      throw e;
  }
  return <OrderDetail id={id} />;
}
