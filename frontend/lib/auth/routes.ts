type Rule = {
  pattern: RegExp;
  methods: string[];
  query?: string[];
  public?: boolean;
};
const slug = "[\\p{L}\\p{N}_-]+";
const rules: Rule[] = [
  { pattern: /^client-options\/$/, methods: ["GET"], public: true },
  {
    pattern: /^auth\/otp\/(request|verify)\/$/,
    methods: ["POST"],
    public: true,
  },
  { pattern: /^auth\/logout\/$/, methods: ["POST"] },
  { pattern: /^me\/$/, methods: ["GET", "PATCH"] },
  {
    pattern: /^products\/$/,
    methods: ["GET"],
    query: [
      "search",
      "category",
      "stock",
      "min_price",
      "max_price",
      "ordering",
      "limit",
      "offset",
    ],
    public: true,
  },
  {
    pattern: new RegExp("^products/" + slug + "/$", "u"),
    methods: ["GET"],
    public: true,
  },
  {
    pattern: new RegExp("^products/" + slug + "/recommendations/$", "u"),
    methods: ["GET"],
    query: ["limit"],
    public: true,
  },
  {
    pattern: new RegExp("^products/" + slug + "/reviews/$", "u"),
    methods: ["GET"],
    query: ["limit", "offset"],
    public: true,
  },
  {
    pattern: new RegExp("^products/" + slug + "/reviews/mine/$", "u"),
    methods: ["GET", "PUT", "DELETE"],
  },
  { pattern: /^products\/[1-9]\d*\/favorite\/$/, methods: ["PUT", "DELETE"] },
  {
    pattern: /^categories\/$/,
    methods: ["GET"],
    query: ["search", "parent", "roots_only", "limit", "offset"],
    public: true,
  },
  {
    pattern: new RegExp("^categories/" + slug + "/$", "u"),
    methods: ["GET"],
    public: true,
  },
  {
    pattern: /^addresses\/$/,
    methods: ["GET", "POST"],
    query: ["limit", "offset"],
  },
  { pattern: /^addresses\/[1-9]\d*\/$/, methods: ["GET", "PATCH", "DELETE"] },
  { pattern: /^cart\/$/, methods: ["GET", "POST", "DELETE"], public: true },
  {
    pattern: /^cart\/items\/[1-9]\d*\/$/,
    methods: ["PATCH", "DELETE"],
    query: ["variant_id"],
    public: true,
  },
  {
    pattern: /^orders\/$/,
    methods: ["GET"],
    query: ["status", "limit", "offset"],
  },
  { pattern: /^orders\/create\/$/, methods: ["POST"] },
  { pattern: /^orders\/[1-9]\d*\/$/, methods: ["GET"] },
  { pattern: /^orders\/[1-9]\d*\/(cancel|payment)\/$/, methods: ["POST"] },
  {
    pattern: /^orders\/[1-9]\d*\/tracking\/$/,
    methods: ["GET"],
    query: ["limit", "offset"],
  },
  { pattern: /^favorites\/$/, methods: ["GET"], query: ["limit", "offset"] },
  {
    pattern: /^notifications\/$/,
    methods: ["GET"],
    query: ["limit", "offset"],
  },
  { pattern: /^notifications\/[1-9]\d*\/read\/$/, methods: ["POST"] },
];
export function routeRule(path: string) {
  if (
    path.includes("..") ||
    /[\\%]/.test(path) ||
    [...path].some((char) => char.codePointAt(0)! <= 32)
  )
    return;
  return rules.find((r) => r.pattern.test(path));
}
export function filteredQuery(query: URLSearchParams, allow: string[] = []) {
  const out = new URLSearchParams();
  for (const k of allow) {
    const v = query.get(k);
    if (v !== null && v.length <= 250) out.set(k, v);
  }
  return out.toString();
}
