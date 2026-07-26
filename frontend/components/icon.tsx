import type { SVGProps } from "react";
import { HugeiconsIcon } from "@hugeicons/react";
import {
  Add01Icon,
  Archive02Icon,
  ArrowDown01Icon,
  ArrowRight02Icon,
  Cancel01Icon,
  Download01Icon,
  Film01Icon,
  Navigation03Icon,
  PlayIcon,
  Refresh01Icon,
  Search01Icon,
  SearchVisualIcon,
  Shield01Icon,
  SparklesIcon,
  Tick02Icon,
} from "@hugeicons/core-free-icons";

export type IconName =
  | "arrow"
  | "archive"
  | "check"
  | "chevron"
  | "download"
  | "film"
  | "inspect"
  | "play"
  | "plus"
  | "refresh"
  | "search"
  | "send"
  | "shield"
  | "spark"
  | "x";

const icons = {
  arrow: ArrowRight02Icon,
  archive: Archive02Icon,
  check: Tick02Icon,
  chevron: ArrowDown01Icon,
  download: Download01Icon,
  film: Film01Icon,
  inspect: SearchVisualIcon,
  play: PlayIcon,
  plus: Add01Icon,
  refresh: Refresh01Icon,
  search: Search01Icon,
  send: Navigation03Icon,
  shield: Shield01Icon,
  spark: SparklesIcon,
  x: Cancel01Icon,
} as const;

export function Icon({
  name,
  className = "size-4",
  ...props
}: {
  name: IconName;
  className?: string;
} & Omit<SVGProps<SVGSVGElement>, "ref" | "size" | "strokeWidth">) {
  return (
    <HugeiconsIcon
      icon={icons[name]}
      size="1em"
      strokeWidth={1.65}
      color="currentColor"
      className={className}
      aria-hidden="true"
      {...props}
    />
  );
}
