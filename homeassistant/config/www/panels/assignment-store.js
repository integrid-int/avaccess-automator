// homeassistant/config/www/panels/assignment-store.js
export function createEmptyAssignments() {
  return {};
}

export function applyAssignment(assignments, route) {
  const next = { ...assignments };
  const selected = new Set(route.tvs);
  for (const [routeId, existing] of Object.entries(next)) {
    if (routeId === route.routeId) continue;
    const remaining = existing.tvs.filter((tv) => !selected.has(tv));
    if (remaining.length === 0) delete next[routeId];
    else next[routeId] = { ...existing, tvs: remaining };
  }
  if (!route.tvs.length) {
    delete next[route.routeId];
    return next;
  }
  next[route.routeId] = {
    kind: route.kind,
    sportId: route.sportId ?? null,
    label: route.label,
    channel: route.channel,
    presetId: route.presetId ?? null,
    tvs: [...route.tvs].sort((a, b) => a - b),
    updatedAt: new Date().toISOString(),
  };
  return next;
}

export function getAssignmentForTv(assignments, tv) {
  for (const [routeId, assignment] of Object.entries(assignments)) {
    if (assignment.tvs.includes(tv)) return { routeId, ...assignment };
  }
  return null;
}

export function loadAssignments(storage, key) {
  try {
    const raw = storage.getItem(key);
    return raw ? JSON.parse(raw) : createEmptyAssignments();
  } catch {
    return createEmptyAssignments();
  }
}

export function saveAssignments(storage, key, assignments) {
  storage.setItem(key, JSON.stringify(assignments));
}
