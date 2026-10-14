export default function Loading() {
  return (
    <div
      className="container page"
      style={{ minHeight: "calc(100vh - 76px)" }}
      role="status"
      aria-label="در حال بارگذاری"
    >
      <div className="skeleton" />
    </div>
  );
}
