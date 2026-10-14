import { NextRequest, NextResponse } from "next/server";
import { configuration, handleBFF } from "@/lib/auth/bff";
import { coordinator } from "@/lib/auth/coordination";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
async function handler(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  try {
    const { path } = await context.params;
    return await handleBFF(
      req,
      path.join("/") + "/",
      configuration(),
      coordinator(),
    );
  } catch {
    return NextResponse.json(
      { detail: "اتصال فروشگاه پیکربندی نشده یا موقتاً در دسترس نیست." },
      { status: 503, headers: { "Cache-Control": "private, no-store" } },
    );
  }
}
export {
  handler as GET,
  handler as POST,
  handler as PATCH,
  handler as PUT,
  handler as DELETE,
};
