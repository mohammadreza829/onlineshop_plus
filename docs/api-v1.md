# API v1

Base path: `/api/v1/`. Interactive docs: `/api/docs/`. OpenAPI: `/api/schema/`.
All money values are whole **Toman**, encoded as decimal strings. The gateway adapter alone converts Toman to Rial.

## Architecture and compatibility

- `shop/selectors.py`: public catalog visibility/filtering, reused by HTML and API.
- `orders/selectors.py`, `addresses/selectors.py`: owner-scoped reads; another owner's ID returns 404.
- `orders/policies.py`: ownership/cancellation decisions. Services recheck cancellation under the order row lock to avoid a paid-order/cancel race.
- `orders/services.py`, `payment/services.py`: checkout and money/stock mutations. Ownership is also checked at the service boundary, not just in HTTP views.
- `account/services.py`: common OTP authentication for session login and JWT.
- `addresses/services.py`: address updates and serialized default-address decisions; HTML and API share phone/postcode validation.
- `/orders/api/v1/...` remains a compatibility alias for the existing cart/order API. It is omitted from the canonical schema. The old item-delete route only accepts DELETE; its previous accidental GET/POST behavior is intentionally removed.
- Existing HTML routes remain session-authenticated; frontend redesign is phase 6. The only template change here converts default-address mutation from a GET link to a CSRF-protected POST form.

## Authentication

No public password-to-token endpoint is exposed: customer sign-in uses OTP.

| Method | Route (relative to base) | Input / result |
|---|---|---|
| POST | `auth/otp/request/` | `{ "phone": "09121234567" }` → 202 message |
| POST | `auth/otp/verify/` | `{ "phone": "09121234567", "code": "123456" }` → `access`, `refresh` |
| POST | `auth/token/refresh/` | `{ "refresh": "..." }` → new `access` and rotated `refresh` |
| POST | `auth/logout/` | Authenticated; `{ "refresh": "..." }` → 204, own refresh token blacklisted |
| GET/PATCH | `me/` | Own id/phone/first_name/last_name; only names are writable |

For protected API requests use `Authorization: Bearer <access>`. Access tokens last 5 minutes; refresh tokens last 1 day. After refresh, replace BOTH stored tokens; the previous refresh is blacklisted. Logout revokes only the supplied refresh, not all devices; existing access tokens remain usable until their short expiry. Inactive users are rejected at OTP login, access authentication and refresh.

Django session authentication remains available. Session-authenticated unsafe requests require a CSRF token. JWT tokens are returned in JSON, not placed in cookies by this API. Use HTTPS and safe client token storage; do not put tokens in URLs or logs. `JWT_SIGNING_KEY` may be set separately from the Django secret (minimum 32 characters in production); otherwise the Django secret is used.

## Catalog (public, read-only)

| Method | Route | Query parameters |
|---|---|---|
| GET | `products/` | `search`, `category` (slug), `stock=available\|out`, `min_price`, `max_price`, `ordering` |
| GET | `products/{slug}/` | Product, category, description, features and image URLs |
| GET | `categories/` | `search`, `parent` (positive id), `roots_only=true\|false` |
| GET | `categories/{slug}/` | Category id/name/slug/parent |

Products include base `price`, percent `off`, computed `final_price`, available inventory and category. Inactive products are never listed or retrievable. Search matches product name/description/SKU. Category filtering is exact, not recursive. Price ranges and price sorting use the **base price before discount**, not final_price. Allowed ordering: `price`, `-price`, `created`, `-created`, `name`, `-name`; default `-created`, with primary-key tie-breaking. Invalid filter values return 400.

Category search matches name/slug; `parent` and `roots_only=true` cannot be combined. Detail includes direct parent id, not a recursively expanded tree.

List responses use `{ "count": ..., "next": ..., "previous": ..., "results": [...] }`. Use `limit` and `offset`; default limit 20, maximum 100. Pagination is offset-based and is not a snapshot of a changing catalog.

## Addresses (authenticated)

- GET/POST `addresses/`: own addresses / create.
- GET/PATCH/DELETE `addresses/{id}/`: own address only.
- Input: `title`, `receiver_name`, `receiver_phone`, `province`, `city`, `full_address`, `postal_code`, `is_default`.
- Owner is always assigned from authentication; client-supplied owner/privilege fields are not writable.
- Phone accepts supported Iranian formats/digits and is normalized to `09...`; postcode is normalized to 10 ASCII digits.
- The first address becomes default; setting a default demotes the others within the serialized service operation.
- Province choices currently retain the existing model's five entries; full geography coverage is not added by this phase.

## Cart and checkout

**The cart is still session/cookie-bound, even with JWT.** A bearer token identifies the customer but does NOT identify or synchronize a cart. Preserve the same session cookie from cart creation through checkout. Separate clients/devices with the same JWT have separate carts. This is deliberate compatibility behavior, not an account-synced mobile cart. Cross-origin client/CORS integration is not configured by this phase.

| Method | Route | Behavior |
|---|---|---|
| GET | `cart/` | Items + item_count, subtotal, discount, post_price, total_price, is_empty |
| POST | `cart/` | `{ "product_id": 1, "quantity": 2 }`; adds 1–100 units per request, capped by available stock |
| DELETE | `cart/` | Clear cart |
| DELETE | `cart/items/{product_id}/` | Remove one product |
| GET | `orders/` | Own paginated orders; optional valid `status` filter |
| GET | `orders/{id}/` | Own order and immutable line snapshots |
| POST | `orders/create/` | `{ "address_id": 1 }`; create/reserve from current cookie cart → 201 |
| POST | `orders/{id}/cancel/` | Cancel own unpaid pending order; return updated order |
| POST | `orders/{id}/payment/` | Start/retry payment for own payable order → gateway `payment_url` |

Order creation returns `message`, `reserved_until`, `order`, and two links:

- `payment_url`: legacy HTML POST route; requires browser session login + CSRF.
- `payment_api_url`: POST this with bearer auth to get the real gateway redirect URL. Do not navigate directly to this POST endpoint.

The actual gateway callback remains `/payment/verify/` and can verify without a session (the gateway response, not browser `Status`, is authoritative). A bearer-only client is not logged into the HTML callback: order details are hidden and its cookie cart is not automatically cleared there. After a successful return, authenticate and query the order, then clear the cart explicitly. Do not treat a redirect's `Status=OK` alone as proof of payment.

Order creation reserves stock, not payment. Errors include empty/invalid cart, non-owned address, insufficient inventory and expired reservation. Existing unpaid orders can be replaced by a new checkout as in phase 1. Customer cancellation is checked under a lock and cannot cancel an already-paid order. Parallel checkouts are serialized on the customer row so only one unpaid pending checkout remains; old orders are rechecked after locking so a concurrent successful payment is not canceled.

## Errors, limits and operations

- 400: invalid input or disallowed business action; field errors and/or `detail`.
- 401: missing/invalid/expired bearer authentication on protected endpoints.
- 403: session CSRF failure or permission denial.
- 404: unknown/inaccessible resource; no disclosure of another customer's data.
- 405: unsupported method. 429: throttled, with `Retry-After`.
- 503: OTP SMS provider unavailable; no successful login/token issuance is implied.

Rates: anonymous 60/minute per IP; authenticated 300/minute per user; auth scope 10/minute, cart 60/minute, checkout/payment/cancel 10/minute. OTP also retains phone/IP hourly limits, resend cooldown and failed-code attempt limits. DRF throttling uses cache and is best effort, not an atomic security boundary or a DDoS firewall; concurrent requests can exceed a limit. A shared cache and correctly trusted proxy/IP configuration are needed for multi-worker deployment (phase 3). Do not trust arbitrary client-supplied forwarded-IP headers.

Run `python manage.py migrate` to create SimpleJWT blacklist tables and schedule `python manage.py flushexpiredtokens` daily. Refresh rotation is not a device-session management system; per-device access revocation and atomic concurrent refresh guarantees are not implemented here.

Real SMS, production settlement, cross-origin frontend behavior, load testing and security assessment are separate release checks. Do not infer production readiness from unit tests alone.


## توسعه فاز ۴

قرارداد variant، کوپن، نظرات/امتیاز، علاقه‌مندی، timeline/notification و staff dashboard: [امکانات فروشگاهی](shop-features.md). فیلدهای جدید additive هستند؛ محصول دارای variant باید `variant_id` دریافت کند. تخفیف کوپن در پاسخ checkout نهایی می‌شود.


## توسعه فاز ۵

`ordering=relevance` برای search PostgreSQL و `GET /api/v1/products/{slug}/recommendations/?limit=8` (سقف ۲۰، عمومی) اضافه شد. [قرارداد جستجو/پیشنهاد و کش](backend-performance.md). داده مالی/خصوصی در shared cache قرار نمی‌گیرد؛ تصمیم نوع فرانت به گفت‌وگو با صاحب پروژه موکول است.
