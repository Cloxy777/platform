import test from "node:test";
import assert from "node:assert/strict";
import {
  timingSafeEqual, verifyWebhook, parseAllowlist, isAllowed, parseCommand,
  firstSeen, sign, verifySignature, createClient,
} from "../src/index.js";

const req = (secret) => ({
  headers: new Headers(secret === undefined ? {} : { "X-Telegram-Bot-Api-Secret-Token": secret }),
});

test("timingSafeEqual", () => {
  assert.equal(timingSafeEqual("abc", "abc"), true);
  assert.equal(timingSafeEqual("abc", "abd"), false);
  assert.equal(timingSafeEqual("abc", "abcd"), false);
  assert.equal(timingSafeEqual("", ""), true);
  assert.equal(timingSafeEqual(null, ""), true);
  assert.equal(timingSafeEqual("é", "é"), true);
});

test("verifyWebhook", () => {
  assert.equal(verifyWebhook(req("s3cret"), "s3cret"), true);
  assert.equal(verifyWebhook(req("wrong"), "s3cret"), false);
  assert.equal(verifyWebhook(req(undefined), "s3cret"), false);
  assert.equal(verifyWebhook(req(""), ""), false, "empty secret never verifies");
  assert.equal(verifyWebhook(req("x"), undefined), false);
});

test("allowlist", () => {
  const al = parseAllowlist(" 1, 2,,-100 ");
  assert.deepEqual([...al], ["1", "2", "-100"]);
  assert.equal(isAllowed(al, 2), true);
  assert.equal(isAllowed(al, "-100"), true);
  assert.equal(isAllowed(al, 3), false);
  assert.equal(isAllowed(al, ""), false);
  assert.equal(isAllowed(al, undefined), false);
  assert.equal(isAllowed(parseAllowlist(undefined), "1"), false);
});

test("parseCommand", () => {
  assert.deepEqual(parseCommand("/Notify@MyBot 1h 3h"), { name: "/notify", args: "1h 3h" });
  assert.deepEqual(parseCommand("  /bookings "), { name: "/bookings", args: "" });
  assert.deepEqual(parseCommand(undefined), { name: "", args: "" });
});

test("firstSeen dedups", async () => {
  const store = new Map();
  const kv = { get: async (k) => store.get(k) ?? null, put: async (k, v) => void store.set(k, v) };
  assert.equal(await firstSeen(kv, 42), true);
  assert.equal(await firstSeen(kv, 42), false);
  assert.equal(await firstSeen(kv, 43), true);
  assert.equal(await firstSeen(undefined, 1), true);
  assert.equal(await firstSeen(kv, undefined), true);
});

test("sign / verifySignature", async () => {
  const s = await sign("k", "act:1:chat:5");
  assert.match(s, /^[0-9a-f]{16}$/);
  assert.equal(await verifySignature("k", "act:1:chat:5", s), true);
  assert.equal(await verifySignature("k", "act:2:chat:5", s), false);
  assert.equal(await verifySignature("other", "act:1:chat:5", s), false);
});

test("client.send builds request, throws on error", async () => {
  const calls = [];
  const ok = async (url, init) => (calls.push({ url, body: JSON.parse(init.body) }), { ok: true });
  const c = createClient({ token: "T", fetchImpl: ok });
  await c.send(5, "hi", { inline_keyboard: [] });
  assert.equal(calls[0].url, "https://api.telegram.org/botT/sendMessage");
  assert.deepEqual(calls[0].body, { chat_id: 5, text: "hi", parse_mode: "HTML", reply_markup: { inline_keyboard: [] } });
  const bad = async () => ({ ok: false, status: 400, text: async () => "nope" });
  await assert.rejects(createClient({ token: "T", fetchImpl: bad }).send(5, "x"), /sendMessage failed: 400 nope/);
});

test("client best-effort calls do not throw on HTTP error", async () => {
  const bad = async () => ({ ok: false, status: 500, text: async () => "x" });
  const c = createClient({ token: "T", fetchImpl: bad });
  await c.answerCallback("id", "t");
  await c.editText(1, 2, "t");
  await c.editMarkup(1, 2, {});
});

test("client requires token", () => {
  assert.throws(() => createClient({}), /token required/);
});
