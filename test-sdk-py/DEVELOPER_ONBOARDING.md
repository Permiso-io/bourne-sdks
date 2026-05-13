# Custom Hooks SDK — integration gotchas (v2)

Observed against production hooks API (`bourneVersion: v2`).

- README reads like payload is free-form, but server validates `event`; arbitrary JSON will throw **400**.
- Auto `system_prompt` hook: SDK used **`source: "system"`** → server rejected.
- README **`tool_use`** example omits **`toolUseId`**; server requires it; **`tool_result`** must use same id.
- **`tool_result`**: no way of knowing that **`content`** is the field to use there.
- 400 response body is large Zod output; mapping it back to app code is slow.
