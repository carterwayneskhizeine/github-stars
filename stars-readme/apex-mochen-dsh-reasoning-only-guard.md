# dsh-reasoning-only-guard

**Stops a reasoning-only turn from bricking a session.**

If a turn produces no visible text and no tool call, this plugin injects a small text block so the
assistant message that gets persisted is never empty.

## The failure it prevents

When a model answers entirely inside its reasoning channel, the turn has no text and no tool call.
The assistant message is then persisted with empty content, and **every later turn of that session
replays it**. A gateway rejects an assistant message with neither content nor tool_calls
(`content or tool_calls must be set`) — so from that point on, every request in that session fails.
The session is permanently unusable, and the work in it is not reachable through chat any more.

The failure is documented in DSH itself. From `packages/llm/llm-deepseek/src/serialize.ts`:

```ts
// Text-less turns send "" — NEVER null. Pure tool-call turns: the official samples
// replay message.content verbatim (which is "") and some gateways reject null
// outright. Reasoning-ONLY turns (the model can answer entirely in the reasoning
// channel, e.g. a v4-flash greeting): the live API rejects null-content/no-tool_calls
// assistant messages with a 400 ("content or tool_calls must be set"), and since the
// message sits durably in the session log, a null here bricks every later turn of
// that session.
content: text,
```

That comment describes `null`; the current code sends `""`. **An empty string is still "unset" as far
as the check is concerned**, which is why the community verification of this defect reports the
failure mode surviving on master — see DSH discussion
[#6520](https://github.com/deepseek-ai/deepseek-harness/discussions/6520) (item 2), which also
records the only known workaround: unpack `session.v3.jsonl.zstd`, replace the empty content of the
reasoning-only assistant record by hand, and repack.

### What this plugin is, precisely

- **Preventive, not a repair.** It stops the empty message from being persisted in the first place.
  It cannot fix a session that is *already* poisoned — that entry is already in the log, and a fix
  for it means editing the session store, which is deliberately outside this plugin's scope.
- **Reproduced end to end here — against a rule-enforcing stub, not the live API.** With a
  reasoning-only stream, the empty assistant message really is persisted; DSH's own `serialize.ts`
  really does turn it into `{"role":"assistant","content":""}` with no `tool_calls`; and a gateway
  applying the rule documented in that same file really does answer `400 content or tool_calls must
  be set` for the next turn — while the guard makes that same turn return `200`. Raw output for every
  step is in [EVIDENCE.md](./EVIDENCE.md). **What is still only community-reported** is whether the
  live DeepSeek gateway rejects `content: ""` exactly as it rejects `null`; the stub encodes the
  documented rule, it does not replace a live reproduction.
- **The shipped test mock cannot express this condition.** `llm-mock-server` both forbids an empty
  `successText` and always appends a text block after reasoning in its `reasoning_success` scenario,
  so no DSH test could ever have created this turn. `test/reasoning-only-server.mjs` is the missing
  fixture — see [EVIDENCE.md](./EVIDENCE.md).
- **Not a core fix.** The clean fix belongs in the adapter. DSH does not accept external pull
  requests today (`CONTRIBUTING.md`: *"we are currently unable to accept external PRs"*), so a
  plugin is the reachable seam.

## Install

```bash
dsh plugin --profile web add github:apex-mochen/dsh-reasoning-only-guard
```

Restart the profile afterwards. Nothing else is required — the guard is active as soon as the
profile composes it.

## Configuration

```yaml
- id: dsh-reasoning-only-guard
  config:
    placeholder: '[no visible output on this turn]'   # default: a longer explanatory sentence
    includeFailedTurns: false                         # also guard error/aborted turns
    enabled: true                                     # set false to keep it installed but inert
```

| Option | Type | Default | Meaning |
|---|---|---|---|
| `placeholder` | string | explanatory sentence | Text injected so the assistant message is never empty |
| `includeFailedTurns` | boolean | `false` | Also inject on `error` / `aborted` finishes |
| `enabled` | boolean | `true` | Turn the guard off without uninstalling |

## Verify it is active

```bash
dsh --profile web --dump-config | grep reasoning-only-guard
```

The plugin appears as its own node. Its effect is easiest to see in a stream you control: the guard
only ever adds `block-start` / `text-delta` / `block-end` for a text block immediately before the
terminal `finish` chunk, and only when the turn carried nothing visible.

To watch it fire on a real turn, point DSH at the reasoning-only stub and read the persisted session
log — the full recipe, with a reader for the multi-frame session container, is in
[EVIDENCE.md](./EVIDENCE.md#reproducing-this-yourself):

```bash
node test/reasoning-only-server.mjs --port 8137
DEEPSEEK_BASE_URL=http://127.0.0.1:8137/v1 DEEPSEEK_API_KEY=stub-key dsh --profile headless "say hi"
```

## Design notes

Why the seams are what they are — the questions a reviewer would otherwise have to ask.

**Why `llm/stream` and not `agent/request`.** `agent/request` resolves to an `LlmCallConfig`, which
carries `provider` / `model` / sampling parameters — **no messages**. It cannot affect what is
persisted.

**Why not sanitize the messages directly.** `GenerateOptions.messages` is exactly what we would want
to rewrite, and the listener does receive it — but the request is **deep-frozen before dispatch**
(`deepFreeze(structuredClone(...))` in `packages/llm/llm/src/index.ts`; `request-freeze.spec.ts`
asserts *"freezes nested messages at dispatch"*). `llm/stream`'s `next()` also takes no arguments,
so the options cannot be replaced either. In-place mutation of a frozen object is not a fix, it is a
bug waiting for a strict-mode boundary.

**Why the return value is the way in.** `llm/stream` is a waterfall whose listener **returns** the
chunk `AsyncIterable` the caller consumes. Wrapping that iterable is therefore a supported seam, and
it is the one place where the turn's content can still be influenced.

**Why inject before `finish`.** The accumulator records chunks as they stream: injecting after the
terminal `finish` risks never being read. The guard buffers nothing — it passes every chunk through
immediately and only emits its three chunks when it sees `finish`.

**Why `next()` is called exactly once, unconditionally.** A waterfall listener that skips or
double-calls `next()` silently swallows the agent's default behaviour — the one red line for
waterfall listeners. A unit check asserts the single call, and the runtime verifier checks the
chain end to end.

**Why failed turns are left alone by default.** Writing text into an `error` or `aborted` turn would
misrepresent what happened. The reported defect is a normal reasoning-only turn.

**Why zero dependencies.** This plugin sits in the request path of every turn. One file, Node
built-ins only, nothing else to audit.

## Security

**Installing a DSH plugin grants it process-level access.** A plugin is loaded into the host process
and is not sandboxed.

This plugin is written to be auditable rather than trusted:

- **No dependencies.** The implementation is `lib/index.js` (~180 lines) with no imports at all.
- **No process, filesystem, or network access.** It never spawns, reads, writes, or fetches.
- **No timers.** It only wraps an async iterable that it is handed.
- **It cannot invent content for a real turn:** it emits its placeholder only when the turn carried
  no visible text and no tool call, and it never modifies or drops a chunk it was given.
- Read it in one sitting: [`lib/index.js`](./lib/index.js).

## Relationship to existing plugins

The plugin catalog had **no entry covering this failure mode** when this was published (searched for
`reasoning-only`, empty-content and session-brick descriptions). Adjacent plugins guard other wire
problems — `dsh-tool-call-guard` neutralizes tool calls with invalid JSON arguments, for example —
and this one follows that same shape for a different defect.

## Compatibility

- DSH `0.1.x` (peer: `@deepseek-ai/cordis ^4.0.1`)
- Node.js 20+
- Registers exactly one waterfall listener (`llm/stream`) and contributes no tools.

## License

MIT
