import { test } from "node:test";
import assert from "node:assert/strict";
import { validateStatus, summarize, dueLines, createStatusDomain } from "../src/status-domain.js";
import { validateManifest, validateReport, validateCommandResult } from "../src/registry.js";

const NOW = new Date("2026-11-27T05:00:00Z");
const good = () => ({
  as_of: "2026-11-20",
  counters: { documents: 13, "active restrictions": 2, "unprocessed files": 0 },
  due: [{ label: "restriction review", date: "2026-12-01" }, { label: "annual check", date: "2026-11-01" }],
});

test("valid status", () => assert.deepEqual(validateStatus(good()), []));

test("lint: only status-only keys; free text and values are rejected", () => {
  assert.ok(validateStatus({ ...good(), notes: "BP 120/80" }).join().includes("key not allowed"));
  const text = good();
  text.counters["Blood glucose 5.1"] = 1; // uppercase, digits, dot: not a label
  assert.ok(validateStatus(text).join().includes("label must match"));
  const val = good();
  val.counters.documents = "13";
  assert.ok(validateStatus(val).join().includes("integer"));
  const extra = good();
  extra.due[0].note = "hba1c";
  assert.ok(validateStatus(extra).join().includes("only {label, date}"));
});

test("lint: dates, duplicates, reserved labels, and messages never echo values", () => {
  const bad = good();
  bad.as_of = "2026-02-30";
  assert.ok(validateStatus(bad).join().includes("as_of"));
  const dup = good();
  dup.due[0].label = "documents";
  assert.ok(validateStatus(dup).join().includes("duplicate"));
  const res = good();
  res.counters["status age days"] = 1;
  assert.ok(validateStatus(res).join().includes("reserved"));
  const leaky = good();
  leaky.counters["SECRET-VALUE-123"] = 5;
  assert.ok(!validateStatus(leaky).join().includes("SECRET-VALUE-123"));
  assert.ok(validateStatus(null).length && validateStatus({ as_of: "2026-11-20", counters: [] }).length);
});

test("summarize: counters, due state, age, staleness", () => {
  const { lines, level } = summarize(good(), NOW);
  assert.deepEqual(lines, [
    "documents: 13", "active restrictions: 2", "unprocessed files: 0",
    "restriction review: ok", "annual check: review due", "status age days: 7",
  ]);
  assert.equal(level, "warn");
  const quiet = { as_of: "2026-11-26", counters: { documents: 1 } };
  assert.equal(summarize(quiet, NOW).level, "ok");
  const stale = { as_of: "2026-09-01", counters: { documents: 1 }, max_age_days: 14 };
  assert.ok(summarize(stale, NOW).lines.includes("status: stale"));
  assert.equal(summarize(stale, NOW).level, "warn");
  const due = { as_of: "2026-11-27", counters: {}, due: [{ label: "x", date: "2026-11-27" }] };
  assert.equal(summarize(due, NOW).lines[0], "x: review due"); // due on the day itself
});

test("dueLines sorted with days left", () => {
  assert.deepEqual(dueLines(good(), NOW), ["annual check: review due", "restriction review: in 4 d"]);
});

test("domain handlers satisfy the contract; minimal privacy report lines pass", async () => {
  const d = createStatusDomain({ name: "health", privacy: "minimal", status: good(), now: () => NOW });
  assert.deepEqual(validateManifest(d.manifest()), []);
  assert.deepEqual(validateReport(d.report(), { privacy: "minimal" }), []);
  for (const cmd of ["status", "due", "nope"]) assert.deepEqual(validateCommandResult(d.command({ cmd })), []);
  assert.match(d.action({ action_id: "p" }).text, /nothing to do/);
  const call = (m, p, b) => d.fetch(new Request(`https://x.invalid${p}`, { method: m, body: b === undefined ? undefined : JSON.stringify(b) }));
  assert.equal((await call("GET", "/manifest")).status, 200);
  assert.equal((await call("POST", "/report", {})).status, 400);
  assert.equal((await call("GET", "/report")).status, 405);
  assert.equal((await call("POST", "/nope", { request_id: "x" })).status, 404);
  const r = await (await call("POST", "/report", { request_id: "r" })).json();
  assert.deepEqual(validateReport(r, { privacy: "minimal" }), []);
});

test("createStatusDomain refuses an invalid status", () => {
  assert.throws(() => createStatusDomain({ name: "x", status: { as_of: "bad", counters: {} } }), /invalid/);
});
