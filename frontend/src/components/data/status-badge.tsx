import { OUTCOMES, PLAN_STATUS, SETUP_STATUS } from "@/lib/labels";
import type { SetupStatus, TradeOutcome, TradePlanStatus } from "@/types";
import { Badge } from "./badge";

type StatusBadgeProps =
  | { kind: "setup"; status: SetupStatus; className?: string }
  | { kind: "plan"; status: TradePlanStatus; className?: string }
  | { kind: "outcome"; status: TradeOutcome; className?: string };

/** Lifecycle badge for setups, trade plans and journal outcomes. */
export function StatusBadge(props: StatusBadgeProps) {
  const meta =
    props.kind === "setup"
      ? SETUP_STATUS[props.status]
      : props.kind === "plan"
        ? PLAN_STATUS[props.status]
        : { ...OUTCOMES[props.status], description: undefined };
  return (
    <Badge tone={meta.tone} dot className={props.className} title={meta.description}>
      {meta.label}
    </Badge>
  );
}
