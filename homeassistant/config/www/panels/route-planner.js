const ALL_ENCODERS = Array.from({ length: 10 }, (_, i) => `ENC-${String(i + 1).padStart(2, "0")}`);

export function stripedTvs(stripeCount, encoderOrdinal) {
  return Array.from({ length: 35 }, (_, i) => i + 1).filter(
    (tv) => (tv - 1) % stripeCount === encoderOrdinal - 1
  );
}

export function encoderIdForOrdinal(ordinal) {
  return `ENC-${String(ordinal).padStart(2, "0")}`;
}

export function listFreeEncoders(busyEncoderIds, { includeSpare = true } = {}) {
  const busy = new Set(busyEncoderIds);
  const pool = includeSpare ? ALL_ENCODERS : ALL_ENCODERS.slice(0, 9);
  return pool.filter((id) => !busy.has(id));
}

function programHasTuneChannel(program) {
  const n = program?.channelNumber;
  return n != null && String(n).trim() !== "";
}

function missingChannelError(programs) {
  const missing = (Array.isArray(programs) ? programs : []).filter(
    (program) => program && !programHasTuneChannel(program)
  );
  if (!missing.length) return "";
  if (missing.length === 1) {
    const label = missing[0].label || missing[0].id || "selected program";
    return `Cannot Take: ${label} has no DirecTV channel`;
  }
  return `Cannot Take: ${missing.length} selected programs have no DirecTV channel`;
}

function finishPlan(plan, programs) {
  const error = missingChannelError(programs);
  if (!error) return plan;
  return { ...plan, slots: [], error };
}

function slot(index, encoderId, program, tvs) {
  return {
    index,
    encoderId,
    program,
    tvs: [...tvs].sort((a, b) => a - b),
    tune: programHasTuneChannel(program)
      ? { channelNumber: String(program.channelNumber).trim() }
      : null,
    udp: null,
    status: "planned",
  };
}

export function listReplaceChoices(assignments) {
  if (!assignments || typeof assignments !== "object") return [];
  return Object.entries(assignments)
    .filter(([, route]) => (route?.tvs?.length ?? 0) > 0)
    .map(([id, route]) => ({
      encoderId: route.encoderId || id,
      label: route.label || route.encoderId || id,
      channel: route.channel || "",
      tvs: [...route.tvs].sort((a, b) => a - b),
    }))
    .sort((a, b) => String(a.encoderId).localeCompare(String(b.encoderId)));
}

function singleEncoderForTvs(assignments, tvs) {
  if (!assignments || !tvs.length) return null;
  let encoderId = null;
  for (const tv of tvs) {
    let found = null;
    for (const [id, route] of Object.entries(assignments)) {
      if (route?.tvs?.includes(tv)) {
        found = route.encoderId || id;
        break;
      }
    }
    if (!found) return null;
    if (encoderId && encoderId !== found) return null;
    encoderId = found;
  }
  return encoderId;
}

function replacedProgram(assignments, encoderId, tvs) {
  const route = assignments?.[encoderId];
  if (!route) return null;
  const oldTvs = [...(route.tvs || [])];
  return {
    encoderId,
    label: route.label || encoderId,
    channel: route.channel || "",
    offTvs: oldTvs.filter((tv) => !tvs.includes(tv)).sort((a, b) => a - b),
  };
}

export function leftoverTvsKeepShowingCopy(replaced) {
  const count = replaced?.offTvs?.length ?? 0;
  if (!count) return "";
  const tvs = count === 1 ? "1 TV" : `${count} TVs`;
  return `${tvs} will keep showing the retuned program until reassigned`;
}

export function planNeedsReuseConfirm(plan) {
  return (plan?.replaced?.offTvs?.length ?? 0) > 0;
}

export function reuseConfirmKey(plan) {
  const off = plan?.replaced?.offTvs ?? [];
  if (!off.length) return "";
  const encoderId = plan.slots?.[0]?.encoderId ?? plan.replaced?.encoderId ?? "";
  return `${encoderId}:${off.join(",")}`;
}

export function buildRoutePlan({
  mode,
  programs,
  selectedTvs = [],
  busyEncoderIds = [],
  assignments = null,
  replaceEncoderId = null,
  commit = "dry_run",
}) {
  const warnings = [];
  const list = Array.isArray(programs) ? [...programs] : [];

  if (mode === "preset_1") {
    if (!list[0]) return { mode, commit, slots: [], warnings, error: "No program selected" };
    return finishPlan(
      {
        mode,
        commit,
        slots: [slot(1, "ENC-01", list[0], Array.from({ length: 35 }, (_, i) => i + 1))],
        warnings,
      },
      [list[0]]
    );
  }

  if (mode === "preset_2" || mode === "preset_3") {
    const n = mode === "preset_2" ? 4 : 9;
    if (list.length === 0) return { mode, commit, slots: [], warnings, error: "No program selected" };
    if (list.length > n) {
      warnings.push(`Ignored ${list.length - n} extra program(s); cap is ${n}`);
    }
    const chosen = list.slice(0, n);
    return finishPlan(
      {
        mode,
        commit,
        slots: chosen.map((program, i) => slot(i + 1, encoderIdForOrdinal(i + 1), program, stripedTvs(n, i + 1))),
        warnings,
      },
      chosen
    );
  }

  if (mode === "adhoc") {
    if (!list[0]) return { mode, commit, slots: [], warnings, error: "No program selected" };
    const tvs = [...new Set(selectedTvs)].sort((a, b) => a - b);
    if (tvs.length === 0) return { mode, commit, slots: [], warnings, error: "No TVs selected" };

    let encoderId = null;
    let replaced = null;
    if (replaceEncoderId) {
      const choices = listReplaceChoices(assignments);
      if (!choices.some((choice) => choice.encoderId === replaceEncoderId)) {
        return { mode, commit, slots: [], warnings, error: "Choose a program to replace" };
      }
      encoderId = replaceEncoderId;
      replaced = replacedProgram(assignments, replaceEncoderId, tvs);
    } else {
      const free = listFreeEncoders(busyEncoderIds, { includeSpare: true });
      if (free.length > 0) {
        encoderId = free[0];
      } else {
        const covered = singleEncoderForTvs(assignments, tvs);
        if (covered) {
          encoderId = covered;
          const info = replacedProgram(assignments, covered, tvs);
          if (info?.offTvs?.length) replaced = info;
        } else {
          return {
            mode,
            commit,
            slots: [],
            warnings,
            error: "No free encoders",
            replaceChoices: listReplaceChoices(assignments),
          };
        }
      }
    }

    return finishPlan(
      {
        mode,
        commit,
        slots: [slot(1, encoderId, list[0], tvs)],
        warnings,
        ...(replaced ? { replaced } : {}),
      },
      [list[0]]
    );
  }

  return { mode, commit, slots: [], warnings, error: `Unknown mode: ${mode}` };
}
