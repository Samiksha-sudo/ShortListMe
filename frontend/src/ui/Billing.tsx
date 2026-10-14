import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getUsage, openPortal, startCheckout, type Usage } from "../api";
import { go } from "../lib/route";
import { Alert, Badge, Button, Card, CardHead, ErrorState } from "./primitives";

export const PRICE = "£20";
const CHECKOUT_PARAM = "billing";

export const useUsage = () => useQuery({ queryKey: ["billing"], queryFn: getUsage, staleTime: 10_000 });

/** The checkout page sends people back to /?billing=success; read it once and tidy the address bar. */
function useCheckoutReturn(): "success" | "cancelled" | null {
  const [result] = useState<"success" | "cancelled" | null>(() => {
    const v = new URLSearchParams(window.location.search).get(CHECKOUT_PARAM);
    return v === "success" || v === "cancelled" ? v : null;
  });
  useEffect(() => {
    if (!result) return;
    const url = new URL(window.location.href);
    url.searchParams.delete(CHECKOUT_PARAM);
    window.history.replaceState(null, "", url.pathname + url.search + url.hash);
  }, [result]);
  return result;
}

/** Sends the user to Stripe Checkout. */
export function UpgradeButton({ label = `Upgrade for ${PRICE}/month` }: { label?: string }) {
  const go = useMutation({ mutationFn: startCheckout, onSuccess: ({ url }) => { window.location.assign(url); } });
  return (
    <>
      <Button variant="primary" icon="sparkles" loading={go.isPending || go.isSuccess} onClick={() => go.mutate()}>{label}</Button>
      {go.isError && <ErrorState title="Couldn't start checkout" message={go.error.message} />}
    </>
  );
}

export function usageLine(u: Usage): string {
  if (u.plan === "admin") return `Unlimited (${u.used} used)`;
  return u.plan === "pro"
    ? `${u.remaining} of ${u.limit} tailorings left this month`
    : `${u.remaining} of ${u.limit} free tailorings left`;
}

/** Shown when the server answers 402: the free allowance or the monthly quota is used up. */
export function QuotaReached({ message }: { message: string }) {
  const usage = useUsage();
  const pro = usage.data?.plan === "pro";
  return (
    <Alert tone="warning" title={pro ? "You've reached this month's limit" : "You've used your free tailorings"}
      actions={!pro && <UpgradeButton />}>
      {message}
    </Alert>
  );
}

const PLAN_FACTS: Record<Usage["plan"], { price: string; cycle: string; includes: string; payment: string }> = {
  free: { price: "£0", cycle: "No billing", includes: "5 tailorings in total", payment: "No card on file" },
  pro: { price: `${PRICE}/month`, cycle: "Monthly, renews automatically", includes: "50 tailorings per rolling 30 days", payment: "Card via Stripe (change or cancel in Manage subscription)" },
  admin: { price: "£0", cycle: "Never billed", includes: "Unlimited tailorings", payment: "Not required" },
};

/** Dashboard card: plan, a usage bar and what the plan costs. */
export function PlanSummary() {
  const usage = useUsage();
  const u = usage.data;
  const pct = u && u.limit > 0 ? Math.min(100, Math.round((u.used / u.limit) * 100)) : 0;
  return (
    <Card>
      <CardHead title="Plan and billing" subtitle={u ? PLAN_FACTS[u.plan].price : undefined}
        action={u && <Badge tone={u.plan === "free" ? "neutral" : "success"}>{{ free: "Free", pro: "Pro", admin: "Admin" }[u.plan]}</Badge>} />
      {usage.isError && <ErrorState title="Couldn't load your plan" message={usage.error.message} onRetry={() => void usage.refetch()} />}
      {u && (
        <>
          {u.plan !== "admin" && (
            <div className="progress-bar" role="progressbar" aria-valuemin={0} aria-valuemax={u.limit} aria-valuenow={u.used} aria-label="Tailorings used">
              <i style={{ width: `${pct}%` }} />
            </div>
          )}
          <div className="settings-row"><span>Usage</span><b>{usageLine(u)}</b></div>
          <div className="settings-row"><span>Included</span><b>{PLAN_FACTS[u.plan].includes}</b></div>
          <div className="settings-row"><span>Billing</span><b>{PLAN_FACTS[u.plan].cycle}</b></div>
          <div className="settings-row"><span>Payment method</span><b>{PLAN_FACTS[u.plan].payment}</b></div>
          {u.plan === "free" && <div className="settings-row"><span>Upgrade for more every month.</span><UpgradeButton /></div>}
          {u.plan === "pro" && <div className="settings-row"><span>Invoices, card and cancellation</span><Button onClick={() => go("settings")}>Manage in Settings</Button></div>}
        </>
      )}
    </Card>
  );
}

/** Settings card: plan, usage, and the upgrade / manage button. */
export function PlanCard() {
  const qc = useQueryClient();
  const returned = useCheckoutReturn();
  const usage = useQuery({
    queryKey: ["billing"], queryFn: getUsage,
    // The webhook can land a moment after the redirect, so keep checking until the plan flips.
    refetchInterval: (q) => (returned === "success" && q.state.data?.plan !== "pro" && q.state.dataUpdateCount < 15 ? 2000 : false),
  });
  const portal = useMutation({ mutationFn: openPortal, onSuccess: ({ url }) => { window.location.assign(url); } });
  useEffect(() => { if (returned === "success") void qc.invalidateQueries({ queryKey: ["billing"] }); }, [returned, qc]);

  return (
    <Card>
      <CardHead title="Plan" subtitle={`Free accounts get a few tailorings to try it. Pro is ${PRICE}/month.`} />
      {returned === "success" && usage.data?.plan === "pro" && <Alert tone="success" title="You're on Pro">Thanks for subscribing.</Alert>}
      {returned === "success" && usage.data?.plan !== "pro" && <Alert tone="info" title="Confirming your payment…">This usually takes a few seconds.</Alert>}
      {returned === "cancelled" && <Alert tone="info" title="Checkout cancelled">You haven't been charged.</Alert>}
      {usage.isError && <ErrorState title="Couldn't load your plan" message={usage.error.message} onRetry={() => void usage.refetch()} />}
      {usage.data && (
        <>
          <div className="settings-row">
            <span>Current plan</span>
            <Badge tone={usage.data.plan === "free" ? "neutral" : "success"}>{{ free: "Free", pro: "Pro", admin: "Admin" }[usage.data.plan]}</Badge>
          </div>
          <div className="settings-row"><span>Usage</span><b>{usageLine(usage.data)}</b></div>
          <div className="settings-row"><span>Price</span><b>{PLAN_FACTS[usage.data.plan].price}</b></div>
          <div className="settings-row"><span>Billing</span><b>{PLAN_FACTS[usage.data.plan].cycle}</b></div>
          <div className="settings-row"><span>Payment method</span><b>{PLAN_FACTS[usage.data.plan].payment}</b></div>
          {usage.data.plan !== "admin" && <div className="settings-row">
            <span>{usage.data.plan === "pro" ? "Change your card or cancel any time." : "Upgrade for more tailorings every month."}</span>
            {usage.data.plan === "pro"
              ? <Button loading={portal.isPending} onClick={() => portal.mutate()}>Manage subscription</Button>
              : <UpgradeButton />}
          </div>}
          {portal.isError && <ErrorState title="Couldn't open subscription settings" message={portal.error.message} />}
        </>
      )}
    </Card>
  );
}
