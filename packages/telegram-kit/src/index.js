// telegram-kit: small, dependency-free helpers for a Telegram webhook bot
// running on Cloudflare Workers. No personal data, no domain logic.

const API = "https://api.telegram.org";

/** Constant-time string comparison (UTF-8 bytes). Length mismatch -> false. */
export function timingSafeEqual(a, b) {
  const enc = new TextEncoder();
  const x = enc.encode(String(a ?? ""));
  const y = enc.encode(String(b ?? ""));
  // Always loop over the longer length so timing does not reveal where they differ.
  let diff = x.length ^ y.length;
  const n = Math.max(x.length, y.length);
  for (let i = 0; i < n; i++) diff |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return diff === 0;
}

/**
 * True if the request carries the expected X-Telegram-Bot-Api-Secret-Token.
 * An unset/empty secret never verifies.
 */
export function verifyWebhook(request, secret) {
  if (!secret) return false;
  const header = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
  if (header === null) return false;
  return timingSafeEqual(header, secret);
}

/** "1, 2,,3" -> Set{"1","2","3"} (ids kept as strings). */
export function parseAllowlist(csv) {
  return new Set(
    String(csv ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
  );
}

/** Chat id (string or number) is in the allowlist set. Empty id never matches. */
export function isAllowed(allowlist, chatId) {
  const id = String(chatId ?? "").trim();
  return id !== "" && allowlist.has(id);
}

/** "/Cmd@MyBot a b" -> { name: "/cmd", args: "a b" } */
export function parseCommand(text) {
  const [first, ...rest] = String(text ?? "").trim().split(/\s+/);
  return { name: (first || "").split("@")[0].toLowerCase(), args: rest.join(" ") };
}

/**
 * Update-id dedup (Telegram retries on non-2xx/timeouts). Returns true the
 * first time an update_id is seen, false on a repeat. Best-effort: KV is
 * eventually consistent, so this narrows duplicates rather than guaranteeing
 * exactly-once. Missing id or kv -> true (do not drop updates).
 */
export async function firstSeen(kv, updateId, ttlSeconds = 86400) {
  if (!kv || updateId === undefined || updateId === null) return true;
  const key = `upd:${updateId}`;
  if (await kv.get(key)) return false;
  await kv.put(key, "1", { expirationTtl: Math.max(60, ttlSeconds) });
  return true;
}

/** HMAC-SHA256 hex of `data` with `secret`, truncated to `bytes` bytes. */
export async function sign(secret, data, bytes = 8) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(data)));
  return [...mac.slice(0, bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Constant-time check of a signature produced by sign(). */
export async function verifySignature(secret, data, signature, bytes = 8) {
  return timingSafeEqual(await sign(secret, data, bytes), signature);
}

/**
 * Bot API client. `fetchImpl` is injectable for tests.
 * send() throws on a non-2xx response; the other calls are best-effort
 * (they never throw on HTTP errors), matching how callbacks/edits are used.
 */
export function createClient({ token, fetchImpl = fetch, parseMode = "HTML" }) {
  if (!token) throw new Error("telegram-kit: token required");
  const call = (method, body) =>
    fetchImpl(`${API}/bot${token}/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

  return {
    async send(chatId, text, replyMarkup) {
      const body = { chat_id: chatId, text, parse_mode: parseMode };
      if (replyMarkup) body.reply_markup = replyMarkup;
      const resp = await call("sendMessage", body);
      if (!resp.ok) throw new Error(`sendMessage failed: ${resp.status} ${await resp.text()}`);
    },
    async answerCallback(callbackQueryId, text) {
      await call("answerCallbackQuery", { callback_query_id: callbackQueryId, text });
    },
    async editText(chatId, messageId, text) {
      await call("editMessageText", { chat_id: chatId, message_id: messageId, text, parse_mode: parseMode });
    },
    async editMarkup(chatId, messageId, replyMarkup) {
      await call("editMessageReplyMarkup", { chat_id: chatId, message_id: messageId, reply_markup: replyMarkup });
    },
  };
}
