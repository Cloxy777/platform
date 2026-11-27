import { test } from "node:test";
import assert from "node:assert/strict";
import { validateRegistry, validateManifest, validateReport, validateCommandResult } from "../src/registry.js";

const good = () => ({
  bots: {
    main: { token_secret: "BOT_MAIN_TOKEN", webhook_secret: "BOT_MAIN_WEBHOOK_SECRET", domains: ["carry", "health"] },
    solo: { token_secret: "BOT_SOLO_TOKEN", webhook_secret: "BOT_SOLO_WEBHOOK_SECRET", domains: ["carry"] },
  },
  domains: {
    carry: { transport: "service-binding", target: "CARRY", privacy: "normal", acl: { chats: ["1", 2], owners: ["1"] } },
    health: { transport: "https", target: "https://h.example/api", privacy: "minimal", acl: { chats: ["1"] } },
  },
});

test("valid registry; domain in two bots is allowed", () => assert.deepEqual(validateRegistry(good()), []));

test("rejects non-objects and empties", () => {
  assert.ok(validateRegistry(null).length);
  assert.ok(validateRegistry({ bots: {}, domains: {} }).length);
});

test("secret refs are names, not values, and unique", () => {
  const r = good();
  r.bots.main.token_secret = "123456789:AAAA-token-value";
  assert.match(validateRegistry(r).join("\n"), /bots\.main\.token_secret/);
  const dup = good();
  dup.bots.solo.token_secret = "BOT_MAIN_TOKEN";
  assert.match(validateRegistry(dup).join("\n"), /already used/);
});

test("cross references", () => {
  const r = good();
  r.bots.main.domains.push("ghost");
  assert.match(validateRegistry(r).join("\n"), /unknown domain "ghost"/);
  const orphan = good();
  orphan.domains.extra = { transport: "service-binding", target: "X", acl: { chats: ["1"] } };
  assert.match(validateRegistry(orphan).join("\n"), /domains\.extra: not served/);
});

test("acl rules", () => {
  const r = good();
  r.domains.carry.acl = { chats: [], owners: ["9"] };
  assert.match(validateRegistry(r).join("\n"), /acl\.chats/);
  const o = good();
  o.domains.carry.acl.owners = ["99"];
  assert.match(validateRegistry(o).join("\n"), /must also be in chats/);
});

test("https transport needs https url; bad names rejected", () => {
  const r = good();
  r.domains.health.target = "http://h.example";
  r.domains.Bad_Name = { transport: "service-binding", target: "X", acl: { chats: ["1"] } };
  const e = validateRegistry(r).join("\n");
  assert.match(e, /https URL required/);
  assert.match(e, /Bad_Name: name must match/);
});

test("manifest", () => {
  const m = {
    name: "carry",
    version: "1.0.0",
    privacy: "normal",
    commands: [{ cmd: "due", help: "next payout" }],
    schedule: [{ id: "daily", cron: "0 5 * * *" }],
  };
  assert.deepEqual(validateManifest(m), []);
  assert.match(validateManifest({ ...m, commands: [m.commands[0], m.commands[0]] }).join(), /duplicate/);
  assert.match(validateManifest({ ...m, schedule: [{ id: "x", cron: "daily" }] }).join(), /cron/);
  assert.ok(validateManifest({ ...m, privacy: "secret" }).length);
});

test("report: normal and minimal privacy", () => {
  const rep = (lines) => ({ digest: { title: "Carry", status: "ok", lines, ts: "2026-11-27T05:00:00Z" } });
  assert.deepEqual(validateReport(rep(["next payout in 3 days"])), []);
  assert.ok(validateReport(rep(["next payout in 3 days"]), { privacy: "minimal" }).length);
  assert.deepEqual(validateReport(rep(["labs: review due", "documents: 12"]), { privacy: "minimal" }), []);
  assert.ok(validateReport({ digest: { title: "x", status: "bad", lines: [], ts: "nope" } }).length >= 2);
});

test("command result and proposal", () => {
  assert.deepEqual(validateCommandResult({ text: "ok" }), []);
  assert.deepEqual(
    validateCommandResult({ text: "ok", proposal: { id: "p1", summary: "run workflow", expires: "2026-11-27T06:00:00Z" } }),
    []
  );
  assert.ok(validateCommandResult({ text: "ok", proposal: { id: "p1" } }).length);
  assert.ok(validateCommandResult({}).length);
});
