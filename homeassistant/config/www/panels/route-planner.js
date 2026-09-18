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

function slot(index, encoderId, program, tvs) {
  return {
    index,
    encoderId,
    program,
    tvs: [...tvs].sort((a, b) => a - b),
    tune: program.channelNumber ? { channelNumber: String(program.channelNumber) } : null,
    udp: null,
    status: "planned",
  };
}

export function buildRoutePlan({
  mode,
  programs,
  selectedTvs = [],
  busyEncoderIds = [],
  commit = "dry_run",
}) {
  const warnings = [];
  const list = Array.isArray(programs) ? [...programs] : [];

  if (mode === "preset_1") {
    if (!list[0]) return { mode, commit, slots: [], warnings, error: "No program selected" };
    return {
      mode,
      commit,
      slots: [slot(1, "ENC-01", list[0], Array.from({ length: 35 }, (_, i) => i + 1))],
      warnings,
    };
  }

  if (mode === "preset_2" || mode === "preset_3") {
    const n = mode === "preset_2" ? 4 : 9;
    if (list.length === 0) return { mode, commit, slots: [], warnings, error: "No program selected" };
    if (list.length > n) {
      warnings.push(`Ignored ${list.length - n} extra program(s); cap is ${n}`);
    }
    const chosen = list.slice(0, n);
    return {
      mode,
      commit,
      slots: chosen.map((program, i) => slot(i + 1, encoderIdForOrdinal(i + 1), program, stripedTvs(n, i + 1))),
      warnings,
    };
  }

  if (mode === "adhoc") {
    if (!list[0]) return { mode, commit, slots: [], warnings, error: "No program selected" };
    const tvs = [...new Set(selectedTvs)].sort((a, b) => a - b);
    if (tvs.length === 0) return { mode, commit, slots: [], warnings, error: "No TVs selected" };
    const free = listFreeEncoders(busyEncoderIds, { includeSpare: true });
    if (free.length === 0) return { mode, commit, slots: [], warnings, error: "No free encoders" };
    return {
      mode,
      commit,
      slots: [slot(1, free[0], list[0], tvs)],
      warnings,
    };
  }

  return { mode, commit, slots: [], warnings, error: `Unknown mode: ${mode}` };
}
