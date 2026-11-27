// Status-only domain: a generic Worker for domains whose data is a tiny, linted
// status.json (docs/contract.md). Counters and dates carry no values, names or
// titles, so the same lint serves privacy "minimal" domains (health) and normal ones.
// Zero dependencies. Pure functions plus createStatusDomain(), which returns the four
// contract handlers and a Worker `fetch`.
//
// status.json shape (nothing else is allowed):
//   { "as_of": "YYYY-MM-DD",
//     "max_age_days": 30,                      // optional, 1..365, default 30
//     "counters": { "<label>": <int 0..999999> },
//     "due": [ { "label": "<label>", "date": "YYYY-MM-DD" } ] }
// label: lowercase letters, spaces, underscores, 1..32 chars (the minimal-privacy line format).

const LABEL = /^[a-z_ ]{1,32}$/;
const ISO = /^\d{4}-\d{2}-\d{2}$/;
const DAY = 86400000;
const RESERVED = new Set(["status age days"]);
const TOP_KEYS = new Set(["as_of", "max_age_days", "counters", "due"]);

const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const validDate = (s) => typeof s === "string" && ISO.test(s) && !Number.isNaN(Date.parse(`${s}T00:00:00Z`)) && new Date(`${s}T00:00:00Z`).toISOString().slice(0, 10) === s;

/** Returns error strings ([] = valid). Messages never echo values from the file. */
export function validateStatus(s) {
  const errs = [];
  if (!isObj(s)) return ["status: object required"];
  for (const k of Object.keys(s)) if (!TOP_KEYS.has(k)) errs.push(`${k}: key not allowed (status-only schema)`);
  if (!validDate(s.as_of)) errs.push("as_of: valid YYYY-MM-DD required");
  if (s.max_age_days !== undefined && !(Number.isInteger(s.max_age_days) && s.max_age_days >= 1 && s.max_age_days <= 365))
    errs.push("max_age_days: integer 1..365");
  const labels = new Set();
  const claim = (label, where) => {
    if (typeof label !== "string" || !LABEL.test(label)) errs.push(`${where}: label must match ${LABEL}`);
    else if (RESERVED.has(label)) errs.push(`${where}: label is reserved`);
    else if (labels.has(label)) errs.push(`${where}: duplicate label`);
    else labels.add(label);
  };
  if (!isObj(s.counters)) errs.push("counters: object required");
  else
    Object.entries(s.counters).forEach(([label, n], i) => {
      claim(label, `counters[${i}]`); // index, never the label: a bad label may be the very text we must not echo
      if (!(Number.isInteger(n) && n >= 0 && n <= 999999)) errs.push(`counters[${i}]: integer 0..999999 required`);
    });
  if (s.due !== undefined) {
    if (!Array.isArray(s.due)) errs.push("due: array required");
    else
      s.due.forEach((d, i) => {
        if (!isObj(d) || Object.keys(d).some((k) => k !== "label" && k !== "date")) errs.push(`due[${i}]: only {label, date} allowed`);
        if (isObj(d)) {
          claim(d.label, `due[${i}].label`);
          if (!validDate(d.date)) errs.push(`due[${i}].date: valid YYYY-MM-DD required`);
        }
      });
  }
  return errs;
}

const dayStart = (now) => Date.parse(`${now.toISOString().slice(0, 10)}T00:00:00Z`);
const daysBetween = (isoDate, now) => Math.round((dayStart(now) - Date.parse(`${isoDate}T00:00:00Z`)) / DAY);

/** Report lines in the minimal-privacy format plus an overall level ("ok" or "warn"). */
export function summarize(status, now = new Date()) {
  const age = daysBetween(status.as_of, now);
  const lines = Object.entries(status.counters).map(([l, n]) => `${l}: ${n}`);
  let level = "ok";
  for (const d of status.due ?? []) {
    const over = daysBetween(d.date, now) >= 0;
    lines.push(`${d.label}: ${over ? "review due" : "ok"}`);
    if (over) level = "warn";
  }
  lines.push(`status age days: ${age}`);
  if (age > (status.max_age_days ?? 30)) {
    lines.push("status: stale");
    level = "warn";
  }
  return { lines, level };
}

/** Due items sorted by date: "<label>: review due" once the date has passed, else "<label>: in N d". */
export function dueLines(status, now = new Date()) {
  return [...(status.due ?? [])]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((d) => {
      const left = -daysBetween(d.date, now);
      return left <= 0 ? `${d.label}: review due` : `${d.label}: in ${left} d`;
    });
}

export function createStatusDomain({ name, version = "0.1.0", privacy = "minimal", status, now = () => new Date() }) {
  const errs = validateStatus(status);
  if (errs.length) throw new Error(`status.json invalid: ${errs.join("; ")}`);
  const commands = [
    { cmd: "status", help: "counters and what is due" },
    { cmd: "due", help: "due and review dates" },
  ];
  const manifest = () => ({ name, version, privacy, commands, schedule: [] });
  const report = () => {
    const t = now();
    const { lines, level } = summarize(status, t);
    return { digest: { title: name, status: level, lines, ts: t.toISOString() } };
  };
  const command = ({ cmd }) => {
    if (cmd === "status") return { text: summarize(status, now()).lines.join("\n") };
    if (cmd === "due") return { text: dueLines(status, now()).join("\n") || "nothing scheduled" };
    return { text: "unknown command" };
  };
  const action = ({ action_id }) => ({ text: `nothing to do for ${String(action_id)}` }); // no side effects
  const json = (body, code = 200) => new Response(JSON.stringify(body), { status: code, headers: { "content-type": "application/json" } });
  const fetch = async (request) => {
    const { pathname } = new URL(request.url);
    if (request.method === "GET" && pathname === "/manifest") return json(manifest());
    if (request.method !== "POST") return json({ error: "method not allowed" }, 405);
    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "bad json" }, 400);
    }
    if (!body || typeof body.request_id !== "string" || body.request_id === "") return json({ error: "request_id required" }, 400);
    if (pathname === "/report") return json(report());
    if (pathname === "/command") return json(command(body));
    if (pathname === "/action") return json(action(body));
    return json({ error: "not found" }, 404);
  };
  return { manifest, report, command, action, fetch };
}
