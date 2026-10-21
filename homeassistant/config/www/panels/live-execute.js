// Live execute feedback: request HA stdout/returncode, treat missing reports
// as failure, and persist occupancy only for slots that reported ok.
import { applyRoutePlan } from "./assignment-store.js";

export function encodePlanB64(plan) {
  return btoa(unescape(encodeURIComponent(JSON.stringify(plan))));
}

/** HA frontend: callService(domain, service, serviceData, target, notifyOnError, returnResponse) */
export function liveExecuteCallServiceArgs(planB64) {
  return [
    "shell_command",
    "avaccess_execute_route_plan",
    { plan_b64: planB64, live: true },
    undefined,
    true,
    true,
  ];
}

export function extractShellCommandStdout(response) {
  if (response == null) return null;
  if (typeof response === "string") return response;
  if (typeof response !== "object") return null;
  if (typeof response.stdout === "string") return response.stdout;
  if (typeof response.output === "string") return response.output;
  const nested = response.response;
  if (nested && typeof nested === "object") {
    if (typeof nested.stdout === "string") return nested.stdout;
    if (typeof nested.output === "string") return nested.output;
  }
  return null;
}

export function extractShellCommandReturncode(response) {
  if (response == null || typeof response !== "object") return null;
  if (Number.isFinite(response.returncode)) return response.returncode;
  const nested = response.response;
  if (nested && typeof nested === "object" && Number.isFinite(nested.returncode)) {
    return nested.returncode;
  }
  return null;
}

export function parseLiveExecuteReport(response) {
  const stdout = extractShellCommandStdout(response);
  if (!stdout || typeof stdout !== "string") return null;
  const lines = stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    try {
      const parsed = JSON.parse(lines[i]);
      if (parsed && typeof parsed === "object" && Array.isArray(parsed.slots)) {
        return parsed;
      }
    } catch {
      // keep scanning for a JSON report line
    }
  }
  return null;
}

export function interpretLiveServiceResponse(response) {
  const returncode = extractShellCommandReturncode(response);
  const report = parseLiveExecuteReport(response);
  const missingReport = report == null;
  const failedReport = Boolean(report && report.ok === false);
  const nonzero = returncode !== 0;
  const failed = missingReport || failedReport || nonzero;
  return { returncode, report, missingReport, failedReport, failed };
}

export function liveFailureWarning(outcome) {
  const { returncode, report, missingReport, failed } = outcome ?? {};
  if (!failed) return null;
  if (missingReport) {
    if (returncode != null && returncode !== 0) {
      return `Live execute failed: no report (exit ${returncode})`;
    }
    return "Live execute failed: no report from Home Assistant";
  }
  const reportErrors = (report?.errors ?? []).map(String).filter(Boolean);
  if (returncode != null && returncode !== 0) {
    if (reportErrors.length) return reportErrors[0];
    return `Live execute failed: exit ${returncode}`;
  }
  if (reportErrors.length) return reportErrors[0];
  return "Live execute failed";
}

export function mergeLiveReportIntoPlan(plan, report) {
  const reportSlots = Array.isArray(report?.slots) ? report.slots : [];
  const slots = (plan.slots ?? []).map((slot, index) => {
    const match =
      reportSlots.find((item) => item?.encoderId && item.encoderId === slot.encoderId) ??
      reportSlots[index];
    if (!match || typeof match !== "object") return slot;
    const next = { ...slot };
    if (match.status) next.status = match.status;
    const err = match.error ?? match.message;
    if (err) {
      next.error = err;
      next.message = err;
    } else if (match.status === "ok") {
      delete next.error;
      delete next.message;
    }
    return next;
  });
  const warnings = [...(plan.warnings ?? [])];
  for (const err of report?.errors ?? []) {
    if (err && !warnings.includes(err)) warnings.push(String(err));
  }
  return { ...plan, slots, warnings };
}

function markUnackedSlotsError(slots, message) {
  return (slots ?? []).map((slot) => {
    if (slot.status === "ok" || slot.status === "error") return slot;
    return {
      ...slot,
      status: "error",
      error: slot.error ?? message,
      message: slot.message ?? slot.error ?? message,
    };
  });
}

export function finalizeLivePlan(plan, outcome) {
  let next = { ...(plan ?? {}), slots: [...(plan?.slots ?? [])], warnings: [...(plan?.warnings ?? [])] };
  if (outcome?.report) {
    next = mergeLiveReportIntoPlan(next, outcome.report);
  }
  const warning = liveFailureWarning(outcome);
  const warnings = [...(next.warnings ?? [])];
  if (warning && !warnings.includes(warning)) warnings.push(warning);
  if (outcome?.failed) {
    const message = warning ?? "Live execute failed";
    return {
      ...next,
      slots: markUnackedSlotsError(next.slots, message),
      warnings,
      error: next.error ?? message,
    };
  }
  return { ...next, warnings };
}

export function occupancyPlanFromLiveResult(plan) {
  const okSlots = (plan?.slots ?? []).filter((slot) => slot.status === "ok");
  return {
    ...plan,
    slots: okSlots,
    error: undefined,
    warnings: [],
  };
}

export function liveExecuteExceptionPlan(plan, error) {
  const message = `Live execute failed: ${error?.message ?? error}`;
  const warnings = [...(plan?.warnings ?? [])];
  if (!warnings.includes(message)) warnings.push(message);
  return {
    ...(plan ?? {}),
    slots: markUnackedSlotsError(plan?.slots, message),
    warnings,
    error: plan?.error ?? message,
  };
}

export async function runLiveSend({
  plan,
  assignments,
  callService,
  applyPlan = applyRoutePlan,
  encodePlan = encodePlanB64,
}) {
  const plan_b64 = encodePlan(plan);
  const args = liveExecuteCallServiceArgs(plan_b64);
  const response = await callService(...args);
  const outcome = interpretLiveServiceResponse(response);
  const lastPlan = finalizeLivePlan(plan, outcome);
  const occupancyPlan = occupancyPlanFromLiveResult(lastPlan);
  const nextAssignments =
    occupancyPlan.slots.length > 0 ? applyPlan(assignments, occupancyPlan) : assignments;
  return { lastPlan, assignments: nextAssignments, outcome };
}

export async function runLiveSendSafe(opts) {
  if (typeof opts?.callService !== "function") {
    return {
      lastPlan: liveExecuteExceptionPlan(opts?.plan, new Error("Home Assistant is not connected")),
      assignments: opts?.assignments,
      outcome: { failed: true, missingService: true },
    };
  }
  try {
    return await runLiveSend(opts);
  } catch (error) {
    return {
      lastPlan: liveExecuteExceptionPlan(opts.plan, error),
      assignments: opts.assignments,
      outcome: { failed: true, error },
    };
  }
}

export function runDryRunSend({ plan, assignments, applyPlan = applyRoutePlan }) {
  const lastPlan = {
    ...plan,
    practice: true,
    warnings: [...(plan?.warnings ?? [])],
  };
  return {
    lastPlan,
    assignments: applyPlan(assignments, plan),
  };
}

export function createInFlightLock() {
  let sending = false;
  return {
    isSending() {
      return sending;
    },
    tryBegin() {
      if (sending) return false;
      sending = true;
      return true;
    },
    end() {
      sending = false;
    },
  };
}

export async function guardedSend(lock, sendFn) {
  if (!lock.tryBegin()) return { ignored: true };
  try {
    const result = await sendFn();
    if (result && typeof result === "object") return { ignored: false, ...result };
    return { ignored: false, result };
  } finally {
    lock.end();
  }
}

export function isTakeArmed({ ready, sending }) {
  return Boolean(ready) && !sending;
}
