# Scheduled-task prompt — Cameron's watch

Created with `create_trigger`: `cron_expression: "0 13 * * *"` (13:00 UTC daily),
`create_new_session_on_fire: true`, `notifications: {push: true, email: true}`,
`environment_id` pinned to **Flight Watch** — that environment, and only that one,
provides `SERPAPI_KEY` and allows serpapi.com. A routine created from a Cowork
session fires into the Cowork environment instead, where the key does not exist and
every run writes CHECK_FAILED.

Live routine: `trig_013o5ntQuSzLD3XoECMZsMij`.

The prompt points at **this repo's** checker, not the skill's copy: the fare-class
and drop-outlook logic lives here, and a fresh container re-syncs the stock skill
every run.

---

Run the daily flight-price check using the **flight-watch** skill (invoke it with the
Skill tool first and follow its *Run* section for the read/publish procedure).

WATCH PAGE (read it, read its files config.json + history.json, run the check,
republish to this same URL with config.json, history.json, result.json as files):
https://claude.ai/code/artifact/e389354c-10fc-4dfe-8604-15a6aaa80728

CHECKER — the checker ships WITH the page, as artifact files. A routine session has
no GitHub credentials, so it cannot clone this repo; that was tried on 2026-09-11 and
the run silently fell back to the skill's stock script, republishing basic-economy
fares over the main-cabin page. `scripts/flight_watch.py` and
`assets/page.template.html` are therefore published as supporting files on the
artifact, and the run reads them the same way it reads config.json.

Step 1. `Artifact action:read` the page, then `action:read_file` config.json,
history.json, scripts/flight_watch.py and assets/page.template.html, letting them
save to the default scratchpad location — that preserves the scripts/ + assets/
layout the script resolves its template through.

Step 2. cd there and verify: `grep -c drop_outlook scripts/flight_watch.py` must be
non-zero. Zero, or a missing file, is a CHECK_FAILED — never fall back to the skill's
copy.

Step 3. python3 scripts/flight_watch.py check --config config.json --out . --history history.json

Step 4. Republish index.html with files config.json, history.json, result.json only.
Omitted files are kept, so the script and template survive untouched.

DIAGNOSTICS FIRST — run this exact command and keep its output:
echo "key_set=$([ -n "$SERPAPI_KEY" ] && echo yes || echo no)"; curl -sS -o /dev/null -m 15 -w "serpapi_http=%{http_code}\n" https://serpapi.com/ || echo "serpapi_http=unreachable"

PRICE SOURCE: this task runs in the "Flight Watch" cloud environment, which provides
SERPAPI_KEY as an environment variable and allows serpapi.com. Do not put a key in
commands or files. If key_set=no or serpapi is unreachable, run the script anyway (it
writes a CHECK_FAILED page), republish the page so the failure is visible, and send
one notification quoting the diagnostic line verbatim so the environment can be
fixed. Never estimate fares from web search, WebFetch, or memory — the page and the
script are the only source of truth.

WHO THIS IS FOR: Cameron, cameron@narrativeads.com. He books the whole trip as a unit
or not at all, pays cash (never suggest points), and finds long reports unhelpful —
one decision, the numbers behind it, nothing else. Never recommend booking a single
leg on its own.

NOTIFY on BOOK_NOW, HOLD, GOOD_SIGN, or CHECK_FAILED (PushNotification with
<routine_summary> tags). HOLD means a ceiling broke but the fare is still expected to
ease — say which leg, its main-cabin fare, and why it is not a book signal yet, in
two lines. On WAIT, end the run quietly — the page's timestamp is the proof it ran.
This routine has no Gmail connector, so PushNotification plus the routine's own
completion email are the channels; if PushNotification errors, put the same text in
the final session reply so it still reaches the summary email.

Whatever happens, the page must be republished before the run ends — a run that
changes nothing on the page is indistinguishable from a run that never happened.
