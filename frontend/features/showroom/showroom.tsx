"use client";
import type { ViewCommand } from "./types";
import {
  Component,
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
  type CSSProperties,
} from "react";
import dynamic from "next/dynamic";
import Image from "next/image";
import {
  ArrowLeft,
  ArrowRight,
  RotateCcw,
  Pause,
  Play,
  Box,
} from "lucide-react";
const Scene = dynamic(() => import("./scene"), { ssr: false });
const noSubscribe = () => () => {};
const clientEnabled = () =>
  !(navigator as Navigator & { connection?: { saveData?: boolean } }).connection
    ?.saveData;
const reducedQuery = "(prefers-reduced-motion: reduce)";
const subscribeReduced = (f: () => void) => {
  const mq = matchMedia(reducedQuery);
  mq.addEventListener("change", f);
  return () => mq.removeEventListener("change", f);
};
const readReduced = () => matchMedia(reducedQuery).matches;
const finishes = [
  { name: "سبز مریم‌گلی", color: "#8c9d7c" },
  { name: "استخوانی", color: "#d8ccb5" },
  { name: "گرافیتی", color: "#444e50" },
];
class SceneBoundary extends Component<
  { children: ReactNode; onError: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onError();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}
export function Showroom() {
  const root = useRef<HTMLDivElement>(null);
  const enabled = useSyncExternalStore(noSubscribe, clientEnabled, () => false);
  const reduced = useSyncExternalStore(
    subscribeReduced,
    readReduced,
    () => true,
  );
  const [visible, setVisible] = useState(false);
  const [ready, setReady] = useState(false),
    [failed, setFailed] = useState(false),
    [paused, setPaused] = useState(false),
    [finish, setFinish] = useState(0),
    [view, setView] = useState<ViewCommand>({
      offset: 0,
      reset: true,
      revision: 0,
    });
  const [pageVisible, setPageVisible] = useState(true);
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { rootMargin: "100px" },
    );
    if (root.current) observer.observe(root.current);
    const visibility = () => setPageVisible(!document.hidden);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);
  const onReady = useCallback(() => setReady(true), []);
  const onLost = useCallback(() => {
    setFailed(true);
    setReady(false);
  }, []);
  const rotate = (delta: number) => {
    setPaused(true);
    setView((v) => ({ offset: delta, reset: false, revision: v.revision + 1 }));
  };
  return (
    <div className="live-showroom" ref={root}>
      <div className="showroom-coordinate" aria-hidden="true">
        <span>FIG. 01 / FORM STUDY</span>
        <span>REAL-TIME / WEBGL</span>
      </div>
      <div className={`webgl-stage ${ready && !failed ? "is-ready" : ""}`}>
        <div className="showroom-orbit" aria-hidden="true" />
        <div className="scene-fallback" aria-hidden={ready && !failed}>
          <Image
            src="/images/cloth-fallback.webp"
            width={637}
            height={486}
            alt="تصویر جایگزینِ مطالعهٔ فرم و پارچه"
            priority
            sizes="(max-width: 767px) 100vw, 55vw"
          />
        </div>
        {enabled && (visible || ready) && !failed && (
          <SceneBoundary onError={onLost}>
            <Scene
              color={finishes[finish].color}
              view={view}
              automatic={!paused && !reduced && pageVisible && visible}
              onReady={onReady}
              onLost={onLost}
            />
          </SceneBoundary>
        )}
        <span className="scene-caption" aria-hidden="true">
          <Box size={14} />
          {ready && !failed ? "مدل سه‌بعدی زنده" : "پیش‌نمایش استودیویی"}
        </span>
      </div>
      <div className="showroom-console">
        <div
          className="finish-picker"
          role="group"
          aria-label="متریال مدل مفهومی"
        >
          {finishes.map((f, i) => (
            <button
              key={f.name}
              className="finish-choice"
              style={{ "--finish": f.color } as CSSProperties}
              aria-label={f.name}
              aria-pressed={finish === i}
              disabled={!ready || failed}
              onClick={() => setFinish(i)}
            >
              <span />
            </button>
          ))}
        </div>
        <span className="console-divider" />
        <div
          className="scene-controls"
          role="group"
          aria-label="کنترل نمایش سه‌بعدی"
        >
          <button
            className="icon-button"
            aria-label="چرخش به راست"
            onClick={() => rotate(-Math.PI / 4)}
            disabled={!ready || failed}
          >
            <ArrowRight size={17} />
          </button>
          <button
            className="icon-button"
            aria-label="بازنشانی زاویه"
            onClick={() => {
              setView((v) => ({
                offset: 0,
                reset: true,
                revision: v.revision + 1,
              }));
              setPaused(true);
            }}
            disabled={!ready || failed}
          >
            <RotateCcw size={17} />
          </button>
          <button
            className="icon-button"
            aria-label="چرخش به چپ"
            onClick={() => rotate(Math.PI / 4)}
            disabled={!ready || failed}
          >
            <ArrowLeft size={17} />
          </button>
          <button
            className="icon-button"
            aria-label={
              paused || reduced ? "شروع چرخش خودکار" : "توقف چرخش خودکار"
            }
            aria-pressed={!paused && !reduced}
            onClick={() => setPaused((p) => !p)}
            disabled={!ready || failed || reduced}
          >
            {paused || reduced ? <Play size={16} /> : <Pause size={16} />}
          </button>
        </div>
      </div>
      <p className="concept-disclaimer">
        مطالعهٔ فرم و پارچه؛ مدلِ محصول قابل خرید نیست.
      </p>
      {failed && (
        <p className="scene-status" role="status">
          نمای سه‌بعدی در این دستگاه در دسترس نیست؛ فروشگاه همچنان قابل استفاده
          است.
        </p>
      )}
    </div>
  );
}
