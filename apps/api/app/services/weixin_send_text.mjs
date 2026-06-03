import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

const packageEntry = process.env.WXILINK_PACKAGE_ENTRY || "weixin-proxy-ilink";
const packageModule = await import(
  packageEntry.includes("\\") || packageEntry.includes("/")
    ? pathToFileURL(packageEntry).href
    : packageEntry
);

const {
  StateStore,
  WeixinClient,
  createSendMessageError,
  isSuccessfulPayload,
  loadRuntimeConfig,
} = packageModule;

const [, , userId, textPath] = process.argv;

if (!userId || !textPath) {
  console.error("Usage: node weixin_send_text.mjs <user_id> <text-file-path>");
  process.exit(1);
}

try {
  const config = loadRuntimeConfig();
  const store = new StateStore(config.statePath);
  const state = await store.load();
  if (!state.token) {
    throw new Error("尚未登录，请先执行 wxilink login。");
  }

  const contextToken = state.contextTokens?.[userId];
  if (!contextToken) {
    throw new Error(`缺少 ${userId} 的 context_token。请先启动 wxilink listen，并让对方给 Bot 发一条消息。`);
  }

  const text = await readFile(textPath, "utf8");
  const client = new WeixinClient({
    baseUrl: state.baseUrl || config.baseUrl,
    token: state.token,
    timeoutMs: config.apiTimeoutMs,
  });
  const response = await client.sendText({ toUserId: userId, contextToken, text });
  if (!isSuccessfulPayload(response)) {
    throw createSendMessageError(response, userId);
  }

  console.log(JSON.stringify({
    ok: true,
    target_user_id: userId,
    text_length: text.length,
    state_path: config.statePath,
    response,
  }));
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
