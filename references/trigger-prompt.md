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

CHECKER — use the forked script in the cch-krs/Flight repo, NOT the skill's own copy.
The fork prices main cabin (the skill's copy prices basic economy, which the trip
rules exclude), links to specific flights, and decides BOOK_NOW vs HOLD on whether
the fare still has room to fall. It lives on the branch
`claude/flight-watch-daily-check-gm7lou`, NOT on main — a plain clone gets the old
script. In order:
  1. if /home/user/Flight is a git repo:
     cd /home/user/Flight && git fetch origin claude/flight-watch-daily-check-gm7lou \
       && git checkout claude/flight-watch-daily-check-gm7lou
     then use /home/user/Flight/scripts/flight_watch.py;
  2. else: git clone --depth 1 -b claude/flight-watch-daily-check-gm7lou \
       https://github.com/cch-krs/Flight /tmp/fw
     and use /tmp/fw/scripts/flight_watch.py;
  3. confirm you have the fork before running it — `grep -c drop_outlook <path>` must
     be non-zero. If it is zero, or neither checkout worked, fall back to the skill's
     copy AND say plainly in both the notification and the session reply that the fork
     was unreachable, so the page is showing basic-economy fares against main-cabin
     ceilings.

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
