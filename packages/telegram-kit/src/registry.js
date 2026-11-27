// Gateway registry and domain-contract validators (docs/contract.md).
// Zero dependencies. Pure functions: return an array of error strings, [] when valid.
// Separate from index.js on purpose: the vendored single-file kit is unaffected.

const NAME = /^[a-z][a-z0-9-]{0,31}$/;
const SECRET_REF = /^[A-Z][A-Z0-9_]{2,63}$/;
const TRANSPORTS = ["service-binding", "https"];
const PRIVACY = ["normal", "minimal"];
const STATUS = ["ok", "warn", "fail"];
const CMD = /^[a-z][a-z0-9_]{0,31}$/;

const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const isStr = (v) => typeof v === "string" && v.length > 0;

function idList(v, path, errs, { required }) {
  if (v === undefined && !required) return;
  if (!Array.isArray(v) || (required && v.length === 0)) {
    errs.push(`${path}: non-empty array of chat ids required`);
    return;
  }
  v.forEach((id, i) => {
    if (!(typeof id === "string" || Number.isInteger(id)) || String(id).trim() === "")
      errs.push(`${path}[${i}]: chat id must be a non-empty string or integer`);
  });
}

/**
 * Validate the private registry (design 2.3). Checks shape, name syntax, secret
 * references (names only, never values), cross references between bots and
 * domains, and that every domain is served by at least one bot.
 */
export function validateRegistry(reg) {
  const errs = [];
  if (!isObj(reg)) return ["registry: object required"];
  const { bots, domains } = reg;
  if (!isObj(bots) || Object.keys(bots).length === 0) errs.push("bots: non-empty object required");
  if (!isObj(domains) || Object.keys(domains).length === 0) errs.push("domains: non-empty object required");
  if (errs.length) return errs;

  const served = new Set();
  const secrets = new Map();
  const claim = (ref, where) => {
    if (secrets.has(ref)) errs.push(`${where}: secret ref ${ref} already used by ${secrets.get(ref)}`);
    else secrets.set(ref, where);
  };

  for (const [name, bot] of Object.entries(bots)) {
    const p = `bots.${name}`;
    if (!NAME.test(name)) errs.push(`${p}: name must match ${NAME}`);
    if (!isObj(bot)) {
      errs.push(`${p}: object required`);
      continue;
    }
    for (const k of ["token_secret", "webhook_secret"]) {
      if (!SECRET_REF.test(bot[k] ?? "")) errs.push(`${p}.${k}: UPPER_SNAKE secret name required (a reference, not a value)`);
      else claim(bot[k], `${p}.${k}`);
    }
    if (!Array.isArray(bot.domains) || bot.domains.length === 0) {
      errs.push(`${p}.domains: non-empty array required`);
      continue;
    }
    if (new Set(bot.domains).size !== bot.domains.length) errs.push(`${p}.domains: duplicates`);
    for (const d of bot.domains) {
      if (!(d in domains)) errs.push(`${p}.domains: unknown domain "${d}"`);
      else served.add(d);
    }
  }

  for (const [name, dom] of Object.entries(domains)) {
    const p = `domains.${name}`;
    if (!NAME.test(name)) errs.push(`${p}: name must match ${NAME}`);
    if (!isObj(dom)) {
      errs.push(`${p}: object required`);
      continue;
    }
    if (!TRANSPORTS.includes(dom.transport)) errs.push(`${p}.transport: one of ${TRANSPORTS.join(", ")}`);
    if (!isStr(dom.target)) errs.push(`${p}.target: non-empty string required`);
    else if (dom.transport === "https" && !/^https:\/\//.test(dom.target))
      errs.push(`${p}.target: https URL required for transport https`);
    if (!PRIVACY.includes(dom.privacy ?? "normal")) errs.push(`${p}.privacy: one of ${PRIVACY.join(", ")}`);
    if (!isObj(dom.acl)) errs.push(`${p}.acl: object required`);
    else {
      idList(dom.acl.chats, `${p}.acl.chats`, errs, { required: true });
      idList(dom.acl.owners, `${p}.acl.owners`, errs, { required: false });
      const chats = new Set((Array.isArray(dom.acl.chats) ? dom.acl.chats : []).map(String));
      for (const o of Array.isArray(dom.acl.owners) ? dom.acl.owners : [])
        if (!chats.has(String(o))) errs.push(`${p}.acl.owners: ${o} must also be in chats`);
    }
    if (!served.has(name)) errs.push(`${p}: not served by any bot`);
  }
  return errs;
}

/** Validate a domain's GET /manifest answer. */
export function validateManifest(m) {
  const errs = [];
  if (!isObj(m)) return ["manifest: object required"];
  if (!NAME.test(m.name ?? "")) errs.push(`name: must match ${NAME}`);
  if (!isStr(m.version)) errs.push("version: non-empty string required");
  if (!PRIVACY.includes(m.privacy)) errs.push(`privacy: one of ${PRIVACY.join(", ")}`);
  if (!Array.isArray(m.commands)) errs.push("commands: array required");
  else {
    const seen = new Set();
    m.commands.forEach((c, i) => {
      if (!isObj(c) || !CMD.test(c.cmd ?? "")) errs.push(`commands[${i}].cmd: must match ${CMD}`);
      else if (seen.has(c.cmd)) errs.push(`commands[${i}].cmd: duplicate "${c.cmd}"`);
      else seen.add(c.cmd);
      if (isObj(c) && !isStr(c.help)) errs.push(`commands[${i}].help: non-empty string required`);
    });
  }
  if (m.schedule !== undefined) {
    if (!Array.isArray(m.schedule)) errs.push("schedule: array required");
    else
      m.schedule.forEach((s, i) => {
        if (!isObj(s) || !isStr(s.id)) errs.push(`schedule[${i}].id: non-empty string required`);
        if (!isObj(s) || !/^\S+( \S+){4}$/.test(s.cron ?? "")) errs.push(`schedule[${i}].cron: 5-field cron expression required`);
      });
  }
  return errs;
}

/**
 * Validate a POST /report answer. A privacy "minimal" domain may return only
 * "<label>: ok|review due|stale|<count>" lines (privacy rule, design 2.7).
 */
export function validateReport(r, { privacy = "normal" } = {}) {
  const errs = [];
  const d = r?.digest;
  if (!isObj(d)) return ["digest: object required"];
  if (!isStr(d.title)) errs.push("digest.title: non-empty string required");
  if (!STATUS.includes(d.status)) errs.push(`digest.status: one of ${STATUS.join(", ")}`);
  if (!Array.isArray(d.lines) || d.lines.some((l) => typeof l !== "string")) errs.push("digest.lines: array of strings required");
  if (!isStr(d.ts) || Number.isNaN(Date.parse(d.ts))) errs.push("digest.ts: ISO timestamp required");
  if (privacy === "minimal" && Array.isArray(d.lines)) {
    d.lines.forEach((l, i) => {
      if (!/^[a-z_ ]{1,32}: (ok|review due|stale|\d{1,6})$/.test(l))
        errs.push(`digest.lines[${i}]: minimal domain allows only "<label>: ok|review due|stale|<count>"`);
    });
  }
  return errs;
}

/** Validate a POST /command answer. A proposal must carry id, summary and expiry. */
export function validateCommandResult(c) {
  const errs = [];
  if (!isObj(c)) return ["result: object required"];
  if (!isStr(c.text)) errs.push("text: non-empty string required");
  if (c.buttons !== undefined && !Array.isArray(c.buttons)) errs.push("buttons: array required");
  if (c.proposal !== undefined) {
    const p = c.proposal;
    if (!isObj(p) || !isStr(p.id) || !isStr(p.summary) || Number.isNaN(Date.parse(p.expires ?? "")))
      errs.push("proposal: {id, summary, expires (ISO)} required");
  }
  return errs;
}
