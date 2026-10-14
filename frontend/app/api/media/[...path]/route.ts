import { NextResponse } from "next/server";
import { configuration } from "@/lib/auth/bff";
export const runtime = "nodejs";
export async function GET(
  _req: Request,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  if (
    path.some(
      (p) =>
        !p ||
        p === "." ||
        p === ".." ||
        /[\\/%]/.test(p) ||
        [...p].some((char) => char.codePointAt(0)! < 32),
    ) ||
    !/\.(png|jpe?g|webp|avif|gif)$/i.test(path.at(-1) ?? "")
  )
    return new NextResponse(null, { status: 404 });
  try {
    const c = configuration(),
      r = await fetch(
        c.upstream + "/media/" + path.map(encodeURIComponent).join("/"),
        {
          cache: "no-store",
          redirect: "error",
          signal: AbortSignal.timeout(8000),
        },
      );
    const type = r.headers.get("content-type") ?? "";
    if (!r.ok || !/^image\/(png|jpeg|webp|avif|gif)(;|$)/.test(type))
      return new NextResponse(null, { status: 404 });
    if (Number(r.headers.get("content-length") ?? 0) > 5000000)
      return new NextResponse(null, { status: 413 });
    const reader = r.body?.getReader();
    if (!reader) return new NextResponse(null, { status: 404 });
    const chunks: Uint8Array[] = [];
    let length = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > 5000000) {
        await reader.cancel();
        return new NextResponse(null, { status: 413 });
      }
      chunks.push(value);
    }
    return new NextResponse(Buffer.concat(chunks), {
      headers: {
        "Content-Type": type,
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return new NextResponse(null, { status: 502 });
  }
}
