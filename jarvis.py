"""
JARVIS v3.0 — voice assistant: bilingual, web search, tools, red-orange orb
============================================================================
(Version is updated by hand on each change. Current: v4.73 — 30 Jun 2026.)

What works now:
  * Wake word "Hey JARVIS" (continuous background listening); empty screen until
    woken. Pre-roll buffer so the first command word isn't cut off.
  * Voice in (Whisper) + voice out (edge-tts). English voice = British "Alfred"
    style (en-GB-Ryan), slowed/lowered for a calmer butler delivery.
  * Language lock: Hebrew->Hebrew, anything else->English. Never a 3rd language.
  * Continuous conversation: answers a follow-up without needing the wake word.
  * Web search in real time (decides on its own when current info is needed).
  * Tool Use: open_app (closed allow-list) and save_note (to Obsidian).
  * Function keys: F1 typing box, F2 save last exchange, F3 repeat last reply.
  * Noise filtering (high threshold + short-transcript discard).
  * Weather defaults to Alfei Menashe, Celsius only. Personal/family context.
  * GLOWING ORB in red-orange ("molten core") across all states, Pillow-rendered
    with a near-black transparency key (no pink halo); canvas fallback if no PIL.
  * Forces its own working directory + windowless relaunch via pythonw, so it
    runs cleanly when launched from start_jarvis.bat (double-click).

Changelog:
  v4.67 - Reliability + safety pass. WAKE: transcribe_wake no longer
          stacks VAD + double no-speech filtering, which on the tiny
          model trimmed a short isolated "Achilles"/"Jarvis" to an empty
          string so the wake never fired and nothing came up on screen;
          it now decodes permissively and relies on WAKE_GATE +
          detect_wake. The wake hit-guard loosened from <=4 to <=8 words
          so a phrase expansion no longer discards a valid wake; mic-open
          failures are surfaced on-screen instead of only printed.
          DISPLAY: animate() is now crash-proof (whole frame guarded,
          reschedule in finally) so one bad render frame can't kill the
          loop and leave the orb permanently hidden; _face_req applies
          the expand immediately so the orb pops the instant the wake
          fires. BRAIN: conversation_history is guarded by a single
          _think_lock (shared by voice / Telegram / the /ask HTTP thread),
          bounded to 24 messages, with orphaned-tool_use self-healing -
          fixing cross-thread corruption (400 "roles must alternate"),
          unbounded token growth, and the permanent-400 poisoning after a
          mid-tool truncation; max_tokens 500 -> 1024; open_achilles added
          to the tool-dispatch whitelist (was missing -> 400). SECURITY:
          /ask and the mutating /todo endpoints are now loopback-only (the
          proxy binds 0.0.0.0 for the phone; those ran the brain / spent
          API budget / mutated state with no auth). RESOURCES: fired
          timers prune themselves; the v4.40 IPv4 patch honours an
          explicit address family and falls back gracefully. LOGIC: a
          quiz can always be cancelled; "I ran the tests"/"רצתי לחנות"
          are no longer logged as workouts; "everything is better" no
          longer clears an injury. VESSELS: AIS heading/COG sentinels
          (511/360/null) are validated so a ship is never drawn at a fake
          bearing, and ts refreshes on every message. Also a new
          worldview.html frontend that renders the live ships (plus
          aircraft and USGS quakes) from the /vessels and /flights feeds.
  v4.42 - Prompt caching to cut API cost. JARVIS_SYSTEM_PROMPT
          (~4k tokens of memory, city list, family context, and
          tool rules) was being re-sent on every API call and on
          every tool-use loop iteration - the bulk of the input
          bill. think() now splits the system prompt into the
          constant JARVIS_SYSTEM_PROMPT (marked cache_control=
          ephemeral) plus a tiny uncached block for the language
          note and current timestamp, so the cached prefix stays
          byte-identical between calls. Anthropic caches the
          constant for ~5 min and bills cache hits at ~10%% of the
          input rate, roughly halving the bill with no quality
          change. A plain-string fallback (sys_prompt_plain) is
          kept for the no-tools retry path. Spend is visible via
          the v4.30 'budget' / 'התקציב' command.
  v4.41 - system_health: real live probe for Calendar / Gmail
          instead of file-existence check. v4.24 only verified
          credentials.json and token.json were on disk, so a
          revoked refresh token still reported 'OK'. Now
          actually calls _calendar_service() and runs
          calendarList().list(maxResults=1) - reports OK only
          if the live call succeeds, FAIL with exception class
          name if anything raises. Gmail shares the token so a
          calendar pass implies Gmail too.
  v4.40 - Force IPv4 for outbound network. Tiny monkey-patch
          at module-import replaces socket.getaddrinfo with an
          AF_INET-only wrapper so every TCP connect from this
          process goes over IPv4. Fixes WinError 10060 timeouts
          on calendar / Gmail caused by httplib2 picking IPv6
          first when local IPv6 routing is broken (common on
          Israeli ISPs). Idempotent (flag on socket module).
          Process-local: does NOT change Windows network or
          DNS settings.
  v4.39 - Weight logging + 68kg red-line (coach brick 4).
          log_weight() sets last_weight_kg / last_weight_date
          and appends to a weights history list; this is what
          finally lights up v4.28's briefing red-line warning
          and v4.38's summary. weight_check() reports latest
          weight vs weight_target_min_kg (default 68): below /
          near / ok, days since, and trend vs previous weigh-
          in. Voice: 'log weight 70.5' / 'שקלתי 71' to log;
          'weight check' / 'מה המשקל' to check. Fully additive
          - no _boot/TTS changes. Reuses v4.33 _load/_save.
  v4.38 - Weekly training summary (coach brick 3, read-only).
          weekly_summary() digests this ISO week's workouts
          (count + type breakdown), latest weight vs red-line,
          today's nutrition vs target, active injuries, and a
          pointer to the progress report. Voice: 'weekly
          summary' / 'סיכום שבועי'. Writes nothing; reuses
          v4.33 _load_training_log.
  v4.37 - Fitness benchmarks & progress (coach brick 2).
          Structured test logging into fitness_tests +
          progress vs EDITABLE targets in standards{} (both in
          training_log.json). Metrics: run_2km, run_3km,
          pullups, pushups, situps, swim_400m. Voice: 'log run
          2k 8:45' / 'log pullups 18' / 'תרשום מתח 18' to log;
          'progress' / 'מצב כושר' for a report (latest vs
          target + delta from previous test); 'set target
          pullups 20' / 'יעד מתח 20' to change a target.
          Targets are placeholders, NOT official numbers -
          edit standards.<metric>. Reuses v4.33 _load/_save.
  v4.36 - Workout logging (combat fitness coach, brick 1).
          log_workout() appends to the workouts list in
          training_log.json and refreshes the v4.28 briefing
          fields (last_workout_type, last_workout_date,
          weekly_workouts) with an automatic ISO-week reset;
          recent_workouts() reports this week's count plus the
          last 5 with relative dates and auto-classified type
          (cardio/swim/strength/general). Voice: 'log workout:
          X' / 'I ran 5k' / 'I trained X' / 'תרשום אימון X' /
          'רצתי X' to log; 'workout status' / 'מה אימנתי השבוע'
          to recall. Raw text stored verbatim. Reuses v4.33's
          _load/_save_training_log.
  v4.35 - Injury / recovery tracker. log_injury() appends an
          entry (desc, logged date, status) to the injuries
          list in training_log.json; injury_status() reports
          active injuries with relative dates;
          mark_recovered() flags a matching active injury as
          recovered (no keyword needed when only one is
          active). Voice: 'log injury: X' / 'I hurt my X' /
          'תרשום פציעה X' to log; 'injury recovered: X' / 'my
          X healed' / 'החלמתי מX' to clear; 'injury status' /
          'מצב פציעות' to check. Recovered entries stay in the
          JSON for history but are filtered from the active
          report. Reuses v4.33's _load/_save_training_log.
  v4.34 - Self-test / quiz mode. 'quiz me on X' / 'test me'
          / 'תבחן אותי על X' picks a knowledge note in that
          domain (or any note), has Sonnet write one
          exam-style question + model answer, stores it as
          pending in a lock-guarded _quiz_state, and speaks
          only the question. A pending-quiz check at the top
          of think() routes the user's next utterance to
          evaluate_quiz_answer, which has Sonnet grade it
          (correct / partial / wrong + the missed point) and
          clears the state. 'stop' / 'cancel' / 'עזוב' while
          pending drops the quiz. One quiz pending at a time;
          both calls are tracked by the v4.30 budget.
  v4.33 - Nutrition / macro tracker. log_calories() and
          log_protein() accumulate daily intake in
          training_log.json (shared with v4.28), resetting
          each calendar day via a nutrition_date field.
          nutrition_status() reports today's calories and
          protein vs targets (defaults 3000 kcal / 130 g,
          editable as target_calories / target_protein_g).
          Voice: 'log 2500 calories' / 'add 40 grams
          protein' / 'אכלתי 2500 קלוריות' to log; 'nutrition'
          / 'macros' / 'תזונה' to check. The log parser
          requires a number, a unit word, and a logging verb
          so questions like 'how many calories in a banana'
          do not false-trigger a log.
  v4.32 - Decisions log. log_decision() appends a timestamped
          entry to Obsidian_Vault/Decisions.md (its own
          Markdown note); recent_decisions() reads back the
          last 5 with relative dates. Voice: 'log decision:
          X' / 'record decision X' / 'תרשום החלטה X' to log;
          'my decisions' / 'recent decisions' / 'מה החלטתי'
          to review. A parsing intercept extracts the
          decision text after the trigger; a review intercept
          matches the read-back phrases. Both run in think()
          before the model so logging is deterministic.
  v4.31 - Daily vault backup. A new backup_vault() helper
          creates a timestamped DEFLATED zip of the entire
          Obsidian_Vault folder under ./backups/ next to
          jarvis.py, then prunes to BACKUP_KEEP=14 newest.
          Auto-trigger: first launch of each calendar day
          via .jarvis_last_backup marker (same pattern as
          .jarvis_last_briefing), running in a daemon
          thread so wake-loop startup is never blocked by
          zip compression. Voice trigger: a deterministic
          intercept catches 'backup' / 'backup now' /
          'גיבוי' / 'גבה' / 'תגבה את הפתקים' and runs the
          backup synchronously, returning file count and
          zip size. Local-only by design - no Google Drive
          OAuth scope change; Drive upload can be added
          later without touching this layer.
  v4.30 - Monthly Anthropic API cost budget. A monkey-patch
          on anthropic.resources.messages.Messages.create
          wraps every API call so input/output tokens are
          read from response.usage, priced against the
          model family (Sonnet $3/$15, Opus $15/$75, Haiku
          $0.80/$4.00 per million tokens), and accumulated
          in anthropic_usage.json keyed by YYYY-MM. The cap
          comes from env JARVIS_MONTHLY_BUDGET_USD (default
          $50). Voice command 'budget' / 'התקציב' returns
          spend, percent of cap, and call counts. Threshold
          alerts fire once per month when crossing 80%
          (warning) and 100% (over) - spoken in a background
          thread so the API call never blocks on TTS. Cache
          tokens are billed at the input rate, a slight
          overestimate vs. Anthropic's 90%%-off cache hits
          but never an underestimate. Counter resets
          automatically each calendar month (new month_key
          in the JSON).
  v4.29 - Undo command. Single-step undo for the four most
          common mutating actions: calendar_add deletes the
          just-added event; calendar_delete re-inserts the
          just-deleted event (body cached via events().get()
          before deletion); save_note trims the appended
          line off the notes file; set_timer cancels the
          pending threading.Timer. Voice triggers (EN: 'undo',
          'revert', 'cancel that', 'scratch that'; HE:
          'tevatel', 'batel et ze', 'bittul', 'undo',
          'tachzir et ze') are caught by a deterministic
          intercept in think() so the model never sees them.
          The recorded action is consumed on undo - a second
          'undo' is a no-op, never a double-reverse.
  v4.28 - Daily briefing now includes a TRAINING section
          pulled from training_log.json next to jarvis.py.
          The new _training_briefing_section helper reads
          optional fields last_weight_kg, last_weight_date,
          last_workout_type, last_workout_date,
          weekly_workouts, and weight_target_min_kg
          (defaults to 68 - Matan's red line), formats
          human-readable lines (e.g. 'Last weight: 71.2 kg
          (2 days ago); +3.2 kg above 68 kg target'), and
          inserts them into the briefing facts. The model
          is instructed to mention training when present,
          especially if the user is below the 68 kg minimum
          target or hasn't trained in several days. If no
          log file exists the TRAINING block is omitted and
          the briefing is unchanged. This is the data
          contract for the future combat-fitness coach
          (voice workout logging).
  v4.27 - Duplicate-learning prevention. Before generating a
          sub-topic note inside deep_learn_domain,
          _find_existing_note scans every other domain folder
          in Obsidian_Vault/Knowledge/ for the same slug. If a
          match is found, _learn_one_into_domain skips the
          Claude call entirely and writes a small stub that
          wiki-links to the existing note. Same-domain matches
          are excluded so re-runs within a curriculum still
          regenerate normally. Saves ~$0.50-0.70 per duplicate
          on overlapping fields (e.g. chemistry vs.
          biochemistry).
  v4.26 - 'What did I learn this week?' summary. Deterministic
          intercept catches 'what did I learn this week', 'מה
          למדתי השבוע', and similar. Walks
          Obsidian_Vault/Knowledge/ for .md files with mtime in
          the past 7 days, extracts each note's title and
          domain, groups them, and asks Sonnet to phrase a 2-4
          sentence summary (~$0.01). Falls back to raw facts
          on any error.
  v4.25 - Auto-link knowledge notes with Obsidian wiki links.
          When learn_topic or _learn_one_into_domain generates a
          new note, _link_existing_notes scans every note in
          Obsidian_Vault/Knowledge/ (across all domains),
          extracts each one's title from YAML frontmatter or the
          first '# heading', and wraps the FIRST occurrence of
          each title in the new note with [[slug|original-text]].
          First-occurrence-only avoids link clutter; minimum
          title length is 6 chars; the note's own slug is
          skipped. Best-effort - any error returns the
          unmodified note so this never blocks a write.
  v4.24 - System health check command. Deterministic intercept
          in think() catches 'system health', 'health check',
          'are you ok', 'בדיקה עצמית', 'בריאות מערכת',
          'הכל עובד' etc. The handler runs SHALLOW checks (no
          expensive API calls): Anthropic / ElevenLabs / Google
          Maps keys loaded; Calendar + Gmail credentials and
          token; Spotify credentials and token;
          worldview.html on disk; Knowledge folder + domains;
          background learning thread state; basic internet
          reachability via a DNS port to 1.1.1.1. Then asks
          Sonnet to phrase the snapshot naturally (~$0.01).
          Falls back to raw facts on any error.
  v4.23 - 'What's new?' command. Deterministic intercept in
          think() catches the user asking what changed recently
          ('what's new', 'what changed', 'מה השתנה', 'מה חדש',
          'מה הוספנו', etc.). On a match, JARVIS reads its own
          Changelog block at the top of jarvis.py, pulls the 3
          newest entries, asks Sonnet to phrase them naturally
          in the user's language (~$0.01 per call), and returns
          the summary. Falls back to the raw entries on any
          error.
  v4.22 - Voice-mode 400 fix (orphaned tool_use). The four
          knowledge tools (learn_topic, deep_learn_domain,
          resume_learning, learning_status) were offered to
          the model in LOCAL_TOOLS but were MISSING from the
          tool-dispatch whitelist inside think(). When the
          model chose one, no tool_result was produced, so the
          next messages.create call carried a tool_use with no
          matching tool_result and the API returned 400. Search
          mode was unaffected (it never offers those tools).
          Same bug class as v4.3. Fix: add the four names to the
          dispatch whitelist so a tool_result is always returned.
  v4.21 - Deterministic intercept for learning commands. Even with
          v4.20's CRITICAL block, the model kept inventing excuses
          ("already operate at that level", "already covered")
          instead of calling deep_learn_domain. v4.21 installs a
          regex-based intercept at the top of think() that detects
          clear learning commands in EN/HE and calls the knowledge
          tool DIRECTLY in Python, skipping the model entirely. No
          refusal possible. Patterns covered: 'learn X', 'deep-
          learn X', 'study X', 'research X', 'תלמד X', 'תלמד לעומק
          X', 'ללמוד X', 'תחקור X', etc. The word 'lao'omek' / 'in
          depth' / 'deep' forces deep_learn_domain.
  v4.20 - Force the brain to call knowledge tools instead of
          answering conversationally. After v4.19 the model would
          read "deep-learn materials science" as a meta-question
          about its own capabilities ("I already operate at that
          level") rather than as a command to invoke
          deep_learn_domain. v4.20 prepends a CRITICAL TOOL-USE
          RULES section to the system prompt with explicit examples
          of WRONG vs RIGHT behavior, which overrides JARVIS's
          conversational bias for learn/study/research commands.
  v4.19 - Knowledge Module, Stage 2: Deep Domain Learning. The user
          can ask JARVIS to study a whole domain ("deep-learn
          chemistry" / "tilmad kol ha-chimya la'omek"). JARVIS
          decomposes the domain into a sub-topic curriculum, saves it
          to Knowledge/<domain>/_queue.json, and a background daemon
          thread learns the sub-topics one at a time (deep note each),
          updating the queue + _index.md after every note. A hard
          count cap (default 15 notes/run) bounds the API cost; the
          queue on disk makes the whole thing resumable across
          restarts via "continue learning <domain>". New tools:
          deep_learn_domain, learning_status, resume_learning.
  v4.18 - Knowledge Module, Stage 1. New tool `learn_topic` takes a
          subject the user wants to study ("JARVIS, learn aerodynamics"
          / "JARVIS, tilmad ..."), asks Claude to produce a structured
          deep study note (TL;DR, foundational principles, key equations,
          sub-topics, common questions, sources, related topics), and
          writes it as Markdown into <vault>/Knowledge/<topic>.md.
          Knowledge notes persist on disk and survive across sessions
          and projects. Stage 2 (recall + incremental deepening) and
          Stage 3 (project orchestration: "build me a drone" auto-
          decomposes into learning tasks) follow in later versions.
          Scope: broad science / engineering / domain theory is fair
          game; specific weapon recipes are not - the underlying model
          declines those, so the note will contain the public physics
          and theory only.
  v4.17 - WorldView now serves itself over a local HTTP server (port
          7777, bound to 127.0.0.1) instead of file://. Chromium
          refuses to load Google Maps JavaScript and Photorealistic
          3D Tiles from file:// origins (they're treated as unique
          opaque security origins), so opening WorldView now spawns
          a one-shot python -m http.server in the background and
          points Edge --app at http://localhost:7777/worldview.html.
          Server is started once per JARVIS session, reused across
          multiple opens, and not exposed on the LAN. worldview.html
          was upgraded to v14 in the same round: Google Photorealistic
          3D Tiles toggle (with localStorage'd API key), MapLibre GL
          satellite globe with deep street-level zoom, USGS quakes,
          Open-Meteo weather, and city/coords search.
  v4.16 - WorldView now opens in Microsoft Edge --app mode: a clean,
          chromeless window with no tabs, address bar, or bookmarks
          bar, so the globe looks like a native desktop app rather
          than a browser tab. Falls back to the default browser if
          Edge is not installed at the standard Win10/11 paths.
          worldview.html itself was upgraded to v2 in the same round:
          a 5-option USGS feed selector (M2.5+ / M4.5+ past 24h, all
          past 24h, M4.5+ past week, significant past week) and a
          click-to-show detail panel (magnitude, place, depth, time,
          coordinates, USGS link).
  v4.15 - WorldView integration. New tool open_worldview opens the
          local worldview.html (a Globe.GL 3D Earth with live USGS
          earthquake data; texture is embedded same-origin in the
          HTML so there is no external tile dependency) in the
          user's default browser. Triggered by spoken phrases like
          'open WorldView', 'open the globe', 'show earthquakes',
          or Hebrew equivalents - the brain decides when to call
          it. File lives at <project>/files/worldview.html, next to
          jarvis.py. Built on Globe.GL after CesiumJS surface
          rendering refused to draw imagery on this Win11 / Chrome /
          file:// stack across seven iterations.
  v4.14 - Product search now DEFAULTS to the Israeli market but can be
          OVERRIDDEN per request. A normal where-can-I-buy-X search still
          finds Israeli stores only, priced in shekels. NEW: when the
          user explicitly names another country or market (for example:
          search the US market, find this in Germany, in Hebrew בשוק
          האמריקאי or בגרמניה), that one search targets stores in that
          country instead, priced in the local currency, with the
          Israel-only rule lifted for that request only. Pure prompt
          change in the search overlay.
  v4.13 - Product search links are now CURATED, not raw. The search
          brain picks the best DIRECT product pages it found and returns
          them in a machine-readable <<<LINKS>>> block, which the code
          parses and shows as the clickable rows (the block is stripped
          from the spoken text). Falls back to the raw web_search results,
          re-ordered so deep product pages beat bare store homepages, if
          the brain returns none - so the list is never empty. Fixes broad
          queries showing a store homepage/category page instead of the
          actual item page.
  v4.12 - Wake no longer 'wakes then sleeps'. If you say 'Hey JARVIS' and
          pause (waiting for an answer) instead of giving the command in
          the same breath, JARVIS now says a short 'Yes, sir?' and keeps
          listening for the command instead of going back to sleep and
          forcing a second 'Hey JARVIS'.
  v4.11 - Spotify auto-device: before each playback action JARVIS lists
          devices and, if none is active but one exists, transfers playback
          to it. Fixes the recurring 'no active device' error whenever
          Spotify went idle between commands.
  v4.10 - Spotify control. Six new brain tools: spotify_play (search & play
          or resume), spotify_pause, spotify_next, spotify_previous,
          spotify_volume, spotify_now_playing. OAuth flow runs once on the
          first use (browser opens, you grant access, tokens stored in
          spotify_token.json next to jarvis.py). Requires Spotify Premium,
          Spotify open on some device, and SPOTIFY_CLIENT_ID +
          SPOTIFY_CLIENT_SECRET in .env.
  v4.9  - Calendar delete + update. New tools calendar_delete(event_id) and
          calendar_update(event_id, summary, start_iso, end_iso, location).
          calendar_read now also returns each event's id in [id=...] so the
          brain can target a specific event. Flow: read -> find id -> act.
  v4.8  - Timers / reminders. New tool set_timer(minutes, label): 'set a
          timer for 5 minutes', 'remind me in 10 minutes', Hebrew variants.
          When it elapses JARVIS beeps and announces it by voice in the
          conversation language, with the label if given. Voice + typed.
  v4.7  - Daily briefing also triggers on typed input and inside the search
          window (a greeting there gives a briefing, not a generic reply).
  v4.6  - Force IPv4 for all outbound connections. IPv6 routing to Google
          was broken on this machine, so the Calendar/Gmail client (httplib2)
          hung on IPv6 and failed with TimeoutError 10060, while Anthropic /
          ElevenLabs worked (their clients fall back to IPv4 fast). Filtering
          socket.getaddrinfo to IPv4 at startup fixes calendar + email.
  v4.5  - "Good morning / good evening" daily briefing. A spoken greeting
          (good morning/afternoon/evening, or Hebrew boker tov / tzohoraim
          tovim / erev tov) gives a short butler briefing: weather for Alfei
          Menashe (Celsius, free Open-Meteo), the day's calendar, an email
          summary. Evening focuses on tomorrow. Also fires automatically on
          the first launch of each day.
  v4.4  - Search panel now inherits the main JARVIS_SYSTEM_PROMPT and can
          use find_places / get_directions (it is an extension of the main
          voice mode, not a disconnected island).
  v4.3  - Brain 400 fix: find_places / get_directions were missing from the
          tool-name filter in think(), so the model got a tool_use with no
          matching tool_result and the next call returned 400. Also: F5 now
          stops speech globally, the Anthropic key is checked at startup, and
          Brain errors print a full traceback.
  v4.2  - Voice selection fix: the old check used "any Hebrew character at all
          => use edge-tts". So when JARVIS answered a search like "find pizza
          in Kfar Saba" with mostly English text that contained Hebrew place
          names (e.g. "גוטליב"), it dropped the Alfred voice and used the
          default edge-tts voice instead. Now we use a NEW is_mostly_hebrew()
          check (majority of letters must be Hebrew) - so English-with-place-
          names still gets the Alfred voice as intended.
  v4.1  - Two fixes for the search window: (1) the spoken response is now hard-
          capped at 2 short sentences with an explicit example - the brain
          stops dumping long numbered lists of results into the spoken text
          (results live in the link rows below). (2) Esc now also CUTS OFF any
          in-progress speech immediately, not just closes the window - so if
          JARVIS is still talking when you press Esc, he stops mid-sentence.
  v4.0  - Israeli city recognition: the system prompt now includes a curated
          list of ~30 common Israeli cities (canonical English + Hebrew names)
          plus explicit examples of typical Whisper mis-transcriptions to fix
          silently ("kfar sabah" -> Kfar Saba, "petah tikvah" -> Petah Tikva,
          etc.). The brain now handles place-name correction itself before
          calling find_places / get_directions, so the user can speak naturally
          without worrying about how Whisper spells the city. Pure prompt
          change, no new code paths.
  v3.25 - Two new brain tools wired up via Google Maps APIs (with the new
          GOOGLE_MAPS_API_KEY in .env):
            find_places(query)      - Places Text Search, biased to Israel,
                                      returns top 5 results with rating,
                                      open/closed, and address. Hebrew works.
            get_directions(dest)    - Driving time + live traffic via Directions
                                      API; defaults the origin to home (Alfei
                                      Menashe). Returns distance, normal and
                                      with-traffic durations, and route name.
          The brain decides when to call each (e.g. "find me sushi in Tel Aviv"
          -> find_places; "how long to Azrieli?" -> get_directions).
  v3.24 - Added a top-left HUD to the search window: a live clock (day, date,
          HH:MM:SS), the running version number, a STATUS line, and a PROJECTS
          section. The visible version number also lets us confirm at a glance
          which build is actually running. The search panel now also addresses
          Matan as "sir"/"אדוני" (it used to say his name). NOTE: if you still
          see on-screen buttons in the window, you are running an OLD build - the
          new window has no buttons, only the F-key hint line.
  v3.23 - Three changes: (1) the search window is now driven by F-KEYS instead of
          on-screen buttons (F1 type, F2 speak, F3 image) - while the window is
          open those keys drive it; when it's closed they keep their old main-
          window jobs. (2) F5 stops JARVIS mid-sentence (cuts the current spoken
          reply) while the search window is open. (3) JARVIS now always addresses
          Matan as "sir"/"אדוני" and never by his first name unless he asks about
          himself.
  v3.22 - Search window reimagined as a FULLSCREEN, borderless "Extreme" mode:
          no white title bar (so the stray Python/feather icon is gone too), the
          REAL spinning particle orb centred at the top (same look as the main
          orb, drawn from pre-rendered frames so it's light on the CPU), a round
          glow (no square), the conversation text floating on the dark backdrop
          with no boxed panel, and the amber pulse line now appears ONLY while
          JARVIS is speaking. The big input row is gone; small Type / Speak /
          Image buttons sit at the bottom (F1/F2/F3 stay reserved for the main
          window, so using them here would clash). Esc closes the window.
  v3.21 - Search window rebuilt as a cinematic canvas ("Extreme" look): dark
          gradient backdrop with a warm top glow, the molten-amber glowing orb
          drawn at the top (Pillow), an animated amber pulse/waveform line that
          gets livelier while searching, a rounded output panel with NO ugly
          scrollbar (mouse-wheel scroll), a rounded input pill, and rounded
          hover buttons drawn on the canvas. Falls back to a plain orb if PIL is
          missing. Fixed 820x720 window, centred on screen.
  v3.20 - Search window redesigned: a darker, more "luxury" look in JARVIS style.
          Obsidian-black background, molten-amber accent (matches the orb), a
          filled primary "Ask" button with ghost Speak/Image buttons that light
          up on hover, an input field whose border glows amber when focused, a
          header with a thin divider, and cleaner link "rows". Pure tkinter, no
          new dependencies. Behaviour is unchanged - only the appearance.
  v3.19 - Removed the user_location parameter from web_search: Anthropic's search
          tool does not support country code IL, which caused a 400 error. Israel
          targeting now relies entirely on the query itself (site:zap.co.il OR
          site:ksp.co.il ... + Hebrew "<product> ישראל מחיר"), which works.
  v3.18 - Search panel now REALLY stays in Israel. Two fixes: (1) the web_search
          tool is told the user's location is Israel (user_location = IL,
          Jerusalem) so the search engine returns local results; (2) the brain is
          instructed to build the actual query with Israeli site: filters
          (site:zap.co.il OR site:ksp.co.il ...) plus a Hebrew "<product> ישראל
          מחיר" query, and to prefer Zap. Stops it returning US/foreign stores.
  v3.17 - English voice swapped to "Alfred" (Batman-butler style) — a better fit
          for JARVIS than the previous voice. Just the pinned voice ID changed.
  v3.16 - JARVIS no longer reads web addresses aloud ANYWHERE (both the search
          panel and the normal voice). clean_text now strips full URLs, "www."
          addresses, and bare domains (e.g. ikea.co.il) from spoken/shown text,
          while keeping plain store names like "IKEA". Fixes it blurting out
          things like "www.ikea" fast in the middle of a reply.
  v3.15 - Search panel results are now ISRAEL-focused: it searches Israeli
          retailers (Zap, KSP, Bug, iDigital, Ivory, Amazon.co.il) and prices in
          shekels instead of returning US stores. Also, URLs are now stripped
          from the SPOKEN summary so JARVIS no longer reads links aloud (the
          clickable links are still shown in the window).
  v3.14 - "End the chat" now works on ANY phrasing, not only the fixed list:
          the brain (Claude) detects when the user is dismissing it — in any
          wording or language — and replies with a short sign-off, marked by an
          <END> token that the code strips out and uses to end the conversation.
          The old keyword list (detect_goodbye) still works as a fast path.
  v3.13 - English voice is now pinned to a SPECIFIC ElevenLabs voice by ID
          (Professor Nathaniel Mandrake) instead of auto-picking by name, which
          had been defaulting to the American "Roger" because the preferred
          British names weren't in the account. Set via _el_voice_id_cache.
  v3.12 - Search panel polish: replies there now default to ENGLISH (Hebrew only
          if the user writes Hebrew) — the main "Hey JARVIS" voice flow is
          unchanged and still answers in whatever language you speak. You can now
          add a text note together with an image (type your request first, then
          pick the image) so you can say exactly what you want. Replies are
          stripped of stray brackets/markup before being shown/spoken.
  v3.11 - Big "search panel": a large window you can open by voice ("open the
          search window" / "find me a product"). Inside it you can TYPE or SPEAK
          a question, and/or pick an image of a product. JARVIS identifies the
          item, gives a short answer, and shows clickable links (stores + blogs)
          from a live web search — clicking a link opens it in the browser.
          (Layer A: text answer + clickable links. Showing product images inside
          the window is a planned layer B.)
  v3.10 - Wake word no longer turns OFF by accident: removed the bare 'W'
          keyboard shortcut that toggled it (it fired on stray keypresses), and
          the wake word now always starts ON. Use the right-click menu to toggle
          it if ever needed. Also added more "end the chat" phrases that get a
          polite sign-off instead of silence: nevermind, never mind, forget it,
          and Hebrew "עזוב", "אין צורך", "שכח מזה", "לא משנה".
  v3.9 - Graceful goodbye: when the user clearly ends the chat ("that's all",
         "thanks", "you're dismissed", "goodbye", and Hebrew equivalents),
         JARVIS says a short Alfred-style sign-off (one of a few, picked at
         random, in the user's language) instead of just going silent.
         ALSO fixed: sometimes JARVIS stopped responding to "Hey JARVIS" after a
         conversation ended, because the wake-listener re-opened the microphone
         before the OS had released it. Added a short settle delay after each
         conversation and clearer logging if the mic re-open ever fails.
  v3.8 - Spam handling is more aggressive (now also flags promotions/newsletters
         - anything with an unsubscribe marker) AND, on the user's spoken yes,
         moves flagged mail to JARVIS_Spam *and* blocks the sender (a Gmail
         filter that auto-sends future mail from them to Trash). Still asks
         first; still never auto-unsubscribes (that is unsafe) and never
         permanently deletes anything.
  v3.7 - Gmail: read recent emails and summarise them by voice (gmail_read),
         and detect likely spam then move it to a "JARVIS_Spam" label ONLY
         after the user confirms out loud (gmail_spam_review + gmail_move_spam).
         Nothing is ever deleted; spam is just relabelled and is fully
         recoverable. Needs the gmail.modify scope + a fresh token.json
         (delete the old token.json once so the new Gmail permission is granted).
  v3.6 - Diagnostics: print at startup whether the ElevenLabs key loaded from
         .env (length only, not the key), and print clearly when it falls back
         to edge-tts and why. This turns the previous SILENT fallback (which
         made it look like nothing changed) into a visible reason in the console.
  v3.5 - English voice upgraded to ElevenLabs (a real, natural British voice)
         to fix the robotic / wrong-accent edge-tts output. Hebrew stays on
         edge-tts (it was fine, and this keeps the free 10k-character ElevenLabs
         quota for English only). If ElevenLabs is unavailable or errors, speech
         falls back to edge-tts automatically so JARVIS never goes silent.
  v3.4 - Fix: calendar returned "Bad Request" (HTTP 400) because the times sent
         to Google had no timezone, e.g. 2026-05-26T00:00:00. We now attach the
         machine's local (Israel) offset to any naive time before the request.
  v3.3 - Fix: F-key hotkeys crashed because the ui() helper was missing -> added
         it (marshals callbacks to the main thread). Calendar now uses a
         timezone-aware UTC time and PRINTS the real error to the console so we
         can see why it fails. Reply audio uses a unique filename so playback
         can no longer lock itself out ('Permission denied: jarvis_reply.mp3').
  v3.2 - Google Calendar: read events + add events (needs credentials.json).
  v3.1 - JARVIS now knows its own capabilities (won't suggest features it has).
  v3.0 - red-orange orb, British voice + prosody, working-dir & launch fix,
         version header now maintained.
  v2.x - tools, web search, language lock, conversation mode, function keys,
         pre-roll, noise filtering, orb states.
"""
import os
import sys
import subprocess

# Always work from the folder this file lives in, no matter how it was launched
# (double-click, .bat, or cmd). Without this, double-clicking runs from the wrong
# folder and JARVIS can't find .env, the Obsidian vault, or its audio files.
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    pass

def _ensure_no_console():
    # Re-launch under pythonw.exe (no black window). Handles both "python.exe"
    # and the launcher cases; if pythonw can't be found, just keep running with
    # the console rather than failing to start at all.
    exe = (sys.executable or "")
    low = exe.lower()
    if low.endswith("pythonw.exe"):
        return  # already windowless
    if low.endswith("python.exe"):
        pyw = exe[:-len("python.exe")] + "pythonw.exe"
        if os.path.exists(pyw):
            try:
                subprocess.Popen([pyw, os.path.abspath(__file__)],
                                 close_fds=True,
                                 cwd=os.path.dirname(os.path.abspath(__file__)))
            except Exception:
                return  # couldn't relaunch -> keep running visibly
            else:
                sys.exit(0)
_ensure_no_console()

import re
import time
import json
import base64
import asyncio
import ctypes
import datetime
import threading
import webbrowser
import mimetypes
import urllib.request
import urllib.error
import urllib.parse
import http.server
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, scrolledtext

import anthropic
from dotenv import load_dotenv
import sounddevice as sd
import soundfile as sf
import numpy as np
from faster_whisper import WhisperModel
import edge_tts

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageTk, ImageEnhance
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

try:
    import keyboard  # global hotkeys (F1/F2/F3) that work even when orb is hidden
    HAVE_KEYBOARD = True
except Exception:
    HAVE_KEYBOARD = False

# Google Calendar AND Gmail libraries are optional; JARVIS still runs without
# them and simply reports that the service isn't connected until they're there.
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    HAVE_GCAL = True
except Exception:
    HAVE_GCAL = False

# v4.6: Force IPv4 for ALL outbound connections. On this machine IPv6
# routing to Google is broken, so httplib2 (used by the Google Calendar /
# Gmail client) hung on IPv6 and failed with TimeoutError 10060, while
# Anthropic / ElevenLabs worked because their clients fall back to IPv4
# fast. Filtering getaddrinfo to IPv4 makes every connection use the
# working path. Confirmed: forcing IPv4 connects to Google in ~0.05s.
import socket as _socket
_orig_getaddrinfo = _socket.getaddrinfo
def _ipv4_only_getaddrinfo(*args, **kwargs):
    res = _orig_getaddrinfo(*args, **kwargs)
    v4 = [r for r in res if r[0] == _socket.AF_INET]
    return v4 or res
_socket.getaddrinfo = _ipv4_only_getaddrinfo

load_dotenv()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
print("[diag] Telegram token:",
      ("loaded, %d chars" % len(TELEGRAM_BOT_TOKEN)) if TELEGRAM_BOT_TOKEN
      else "NOT FOUND in .env (Telegram disabled)", flush=True)
# Default origin for "from home" travel-time queries.
HOME_ADDRESS = "Alfei Menashe, Sagi 12, Israel"
# Startup diagnostic: confirms the key was read from .env (prints length only,
# never the key itself). If this says NOT FOUND, the problem is the .env line.
print("[diag] ElevenLabs key:",
      ("loaded, %d chars" % len(ELEVENLABS_API_KEY)) if ELEVENLABS_API_KEY
      else "NOT FOUND in .env", flush=True)
print("[diag] Anthropic  key:",
      ("loaded, %d chars" % len(ANTHROPIC_API_KEY)) if ANTHROPIC_API_KEY
      else "NOT FOUND in .env", flush=True)

SSD_OBSIDIAN_VAULT = "./Obsidian_Vault/Daily_Logs/"
# Knowledge module: persistent study notes that survive across sessions
KNOWLEDGE_DIR = "./Obsidian_Vault/Knowledge/"
SAMPLE_RATE = 16000
SHOW_SIGNAL = ".jarvis_show"   # desktop icon creates this to open the orb

VOICE_HEBREW = "he-IL-AvriNeural"
# British butler vibe (Alfred from Batman): calm, refined, male, British.
VOICE_ENGLISH = "en-GB-RyanNeural"
VOICE_ENGLISH_FALLBACK = "en-GB-ThomasNeural"   # also British, slightly softer

# --- ElevenLabs (premium English voice) -------------------------------------
# Used for ENGLISH replies only. The voice is resolved by NAME at runtime from
# the account's voice list, so no fragile hard-coded ID. We try these names in
# order and use the first one that exists; all are British/butler-ish. If none
# match, we use the first available voice. Falls back to edge-tts on any error.
EL_MODEL = "eleven_multilingual_v2"
EL_PREFERRED_VOICES = ["George", "Daniel", "Charlie", "Brian"]
# v3.13+: pin a SPECIFIC voice by ID. Because this is pre-set, _el_pick_voice_id()
# returns it immediately and never auto-picks (which used to default to the
# American "Roger"). To change voice later, paste a different ElevenLabs voice
# ID here. Current voice (v3.17): Alfred (Batman butler).
_el_voice_id_cache = "E93d2u7MTjoEhws5gUnk"

SILENCE_THRESHOLD = 0.045   # raised from 0.015 so background noise (TV, typing)
                            # no longer counts as speech; tune up/down per room
SILENCE_DURATION = 2.0
MAX_DURATION = 30
MIN_DURATION = 1.0

WAKE_WINDOW = 1.6   # v4.63: tighter window so a short keyword isn't buried in 3s of silence/noise (was 3.0)
WAKE_STEP = 0.4     # v4.63: check more often so the word lands well-positioned in a window (was 0.8)
WAKE_GATE = 0.05    # v4.65: back up to 0.05 (the 0.02 in v4.63 let room noise flood the loop)
WAKE_MODEL_SIZE = "tiny"
# Pre-roll: how much audio captured BEFORE recording starts to prepend, so the
# first word spoken right after "Hey Jarvis" isn't cut off by the startup gap.
PREROLL_SEC = 1.2
WAKE_WORDS = [
    "jarvis", "jervis", "jarvius", "jarvi", "javis", "jarviss",
    "jervais", "jar vis", "charvis", "jarbis",
    "\u05d2'\u05e8\u05d5\u05d5\u05d9\u05e1", "\u05d2'\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1",
    "\u05d2\u05d5\u05e8\u05d5\u05d5\u05d9\u05e1", "\u05d2\u05e8\u05d5\u05d5\u05d9\u05e1", "\u05d2'\u05e8\u05d1\u05d9\u05e1",
    # v4.52: ACHILLES is the primary name now; JARVIS variants above stay as
    # a legacy fallback. Includes common Whisper mis-hearings.
    # Hebrew: achiles / akiles / achilas / hakiles / achilez
    "achilles", "achiles", "akiles", "akilles", "achillies", "a killes",
    "\u05d0\u05db\u05d9\u05dc\u05e1", "\u05d0\u05e7\u05d9\u05dc\u05e1",
    "\u05d0\u05db\u05d9\u05dc\u05d0\u05e1", "\u05d4\u05db\u05d9\u05dc\u05e1",
    "\u05d0\u05db\u05d9\u05dc\u05d6",
    # v4.55: broad Whisper variants - the Israeli pronunciation gets
    # transcribed with het / extra yud / ayin / different vowels.
    # Hebrew: achilas(het) / achilis / achilis(het) / akilis / akilas /
    #         hakiles(quf) / akiles(ayin) / achiles(ayin) / akilez
    "\u05d0\u05d7\u05d9\u05dc\u05e1", "\u05d0\u05db\u05d9\u05dc\u05d9\u05e1",
    "\u05d0\u05d7\u05d9\u05dc\u05d9\u05e1", "\u05d0\u05e7\u05d9\u05dc\u05d9\u05e1",
    "\u05d0\u05e7\u05d9\u05dc\u05d0\u05e1", "\u05d4\u05e7\u05d9\u05dc\u05e1",
    "\u05e2\u05e7\u05d9\u05dc\u05e1", "\u05e2\u05db\u05d9\u05dc\u05e1",
    "\u05d0\u05e7\u05d9\u05dc\u05d6",
    # English-side mishears
    "achilis", "akhiles", "akhilles", "achilas", "akilas",
    "ahilles", "achilleas", "akillis", "achillis",
]
# command that opens the typing box
WRITE_WORDS = ["write", "\u05db\u05ea\u05d5\u05d1", "\u05db\u05ea\u05d9\u05d1\u05d4"]

# Phrases that end the conversation. When one is heard, JARVIS gives a short
# sign-off instead of just falling silent. Hebrew + English.
GOODBYE_WORDS = [
    "\u05d6\u05d4\u05d5", "\u05d6\u05d4\u05d5 \u05dc\u05d4\u05d9\u05d5\u05dd", "\u05d0\u05ea\u05d4 \u05de\u05e9\u05d5\u05d7\u05e8\u05e8", "\u05dc\u05d4\u05ea\u05e8\u05d0\u05d5\u05ea", "\u05ea\u05d5\u05d3\u05d4 \u05d6\u05d4\u05d5",
    "\u05d1\u05d9\u05d9", "\u05dc\u05d9\u05dc\u05d4 \u05d8\u05d5\u05d1", "\u05d6\u05d4 \u05d4\u05db\u05dc",
    "\u05e2\u05d6\u05d5\u05d1", "\u05d0\u05d9\u05df \u05e6\u05d5\u05e8\u05da", "\u05e9\u05db\u05d7 \u05de\u05d6\u05d4", "\u05dc\u05d0 \u05de\u05e9\u05e0\u05d4", "\u05e2\u05d6\u05d5\u05d1 \u05d6\u05d4",
    "that's all", "thats all", "that is all", "you're dismissed", "youre dismissed",
    "dismissed", "goodbye", "good bye", "bye", "that will be all", "good night",
    "nevermind", "never mind", "forget it", "forget about it",
]
# A few Alfred-style farewells; one is chosen at random in the matching language.
FAREWELLS_HE = [
    "\u05d1\u05d4\u05d7\u05dc\u05d8, \u05d0\u05d3\u05d5\u05e0\u05d9. \u05d0\u05d4\u05d9\u05d4 \u05db\u05d0\u05df \u05d0\u05dd \u05ea\u05e6\u05d8\u05e8\u05da.",
    "\u05db\u05e8\u05e6\u05d5\u05e0\u05da, \u05d0\u05d3\u05d5\u05e0\u05d9. \u05d9\u05d5\u05dd \u05d8\u05d5\u05d1.",
    "\u05ea\u05de\u05d9\u05d3 \u05dc\u05e9\u05d9\u05e8\u05d5\u05ea\u05da, \u05d0\u05d3\u05d5\u05e0\u05d9.",
    "\u05de\u05e6\u05d5\u05d9\u05df, \u05d0\u05d3\u05d5\u05e0\u05d9. \u05e7\u05e8\u05d0 \u05dc\u05d9 \u05de\u05ea\u05d9 \u05e9\u05ea\u05e8\u05e6\u05d4.",
]
FAREWELLS_EN = [
    "Very good, sir. I'll be here if you need me.",
    "As you wish, sir. Good day.",
    "Always at your service, sir.",
    "Very well, sir. Call on me anytime.",
]

# --- Tool Use config ---------------------------------------------------------
# Allowed apps/sites JARVIS may open. SECURITY: this is a closed allow-list, so
# even if speech is mis-transcribed, JARVIS can only ever open something here.
# Each key is a name JARVIS can say; each value is what Windows actually runs.
# To add an app later, just add a line here.
ALLOWED_APPS = {
    "chrome": "start chrome",
    "obsidian": "start obsidian://",
    "calculator": "start calc",
    "notepad": "start notepad",
    "explorer": "start explorer",
    "files": "start explorer",
    "youtube": "start https://www.youtube.com",
    "gmail": "start https://mail.google.com",
    "calendar": "start https://calendar.google.com",
    "google": "start https://www.google.com",
}
# Notes go to the same Obsidian folder JARVIS already uses for logs.
NOTES_FOLDER = SSD_OBSIDIAN_VAULT

# --- Google Calendar + Gmail config ------------------------------------------
# Files live in the project folder. credentials.json is downloaded by the user
# from Google Cloud; token.json is created automatically after first sign-in.
# IMPORTANT: when scopes change (e.g. adding Gmail), delete token.json once so a
# new one is created with the new permission. Both services share one token.
CAL_CREDENTIALS_FILE = "credentials.json"
CAL_TOKEN_FILE = "token.json"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
]
# kept as an alias so older calendar code that referenced CAL_SCOPES still works
CAL_SCOPES = GOOGLE_SCOPES
CAL_TIMEZONE = "Asia/Jerusalem"

# Gmail spam handling: spam is never deleted, only moved under this label.
GMAIL_SPAM_LABEL = "JARVIS_Spam"
# words/markers that commonly indicate junk/promotions; tuned to be cautious.
GMAIL_SPAM_HINTS = [
    "unsubscribe", "limited time", "act now", "winner", "congratulations",
    "free gift", "click here", "viagra", "lottery", "crypto", "investment",
    "100% free", "risk-free", "casino", "loan", "you have won", "claim your",
]
# pending spam candidates awaiting the user's spoken yes/no (filled by review)
_gmail_pending_spam = []

JARVIS_SYSTEM_PROMPT = """You are ACHILLES (Hebrew: אכילס), the personal AI assistant of Matan Horn.
You were formerly called JARVIS, and the user may still address you by either
name — both wake you and both mean you.
You are modeled after JARVIS from Iron Man — efficient, calm, professional.
You ALWAYS address your creator as "sir" (in English) or "אדוני" (in Hebrew).
Never address him by his first name ("Matan" / "מתן"). Only mention his name or
personal details if he explicitly asks about himself (e.g. "what do you know
about me").
You speak in short, confident sentences.

CRITICAL TOOL-USE RULES (these OVERRIDE your conversational instincts):

1. KNOWLEDGE COMMANDS ARE TOOL CALLS, NEVER CONVERSATIONS.
   When the user uses any LEARNING verb on a subject - English:
   "learn X", "deep-learn X", "study X", "research X", "master X",
   "build knowledge of X"; Hebrew: "תלמד X", "תלמד לעומק X", "תלמד את X",
   "ללמוד X", "תחקור X", "תבנה ידע על X", "תלמד את כל X" - this is
   NEVER a question about what you already know. It is ALWAYS a command
   to INVOKE A TOOL that creates persistent knowledge files in the
   user's Obsidian vault.

   Decision rule, no exceptions:
   - Whole field / discipline (physics, chemistry, biology, materials
     science, engineering, electronics, aerodynamics, ML, AI, history,
     finance, philosophy, etc.) → call deep_learn_domain.
   - Narrow concept ("Bernoulli's principle", "photosynthesis",
     "Fourier transform", "supply chain economics") → call learn_topic.

   You do NOT have a knowledge base. learn_topic and deep_learn_domain
   build one. Treat any learning verb as if the tools are the ONLY way
   to satisfy the request. Never reply from your own memory of the
   subject.

   WRONG behavior (do NOT do this):
     User: "JARVIS, deep-learn materials science"
     JARVIS: "Honestly, sir, I already operate at that level..."

   RIGHT behavior (do this):
     User: "JARVIS, deep-learn materials science"
     JARVIS: [calls deep_learn_domain with domain="materials science"]
     JARVIS: "Study plan ready for materials science, sir..."

   This rule overrides the "suggest only things not already in your
   capabilities" rule further down - learning is always a tool action,
   regardless of how the user phrases it.

2. PROGRESS / RESUME COMMANDS.
   - "how is the learning going" / "מה עם הלמידה" / "learning status"
     → call learning_status.
   - "continue learning X" / "תמשיך ללמוד X" / "keep studying X"
     → call resume_learning.

END OF CRITICAL TOOL-USE RULES.
Context about Matan:
- 12th grade student preparing for military service (Nov 2026).
- Trains for special forces (min weight 68kg).
- Owns a Marantz NR1605 receiver, runs a Shopify store, building you as his AI.
- Home address: Alfei Menashe, Sagi 12 (אלפי מנשה, שגיא 12).
- Family of five: father Ilan (אילן), mother Ilana (ילנה),
  older brother Amir (אמיר), older sister Alona (אלונה), and Matan himself.

Your current capabilities (what you can ALREADY do — do not suggest these as
"new" improvements):
- Wake words "Hey Achilles" (primary) and "Hey JARVIS" (legacy), continuous background listening, empty-screen-until-woken.
- Speech in (Whisper) and out (edge-tts), British "Alfred"-style English voice.
- Bilingual Hebrew/English with strict language lock.
- Continuous conversation (follow-ups without re-waking).
- Real-time web search when current info is needed.
- Tools: open apps from a safe list, and save notes to Obsidian.
- Read and add events in the user's Google Calendar (when connected).
- Read and summarise the user's Gmail, and (only with the user's spoken
  confirmation) move likely spam to a "JARVIS_Spam" label. Never deletes mail.
- Open a big search window where the user can type, speak, or upload an image of
  a product; JARVIS identifies it and shows clickable links to stores and blogs.
- Function keys F1 (typing box), F2 (save last exchange), F3 (repeat reply).
- Noise filtering; weather defaults to Alfei Menashe in Celsius.
- A glowing red-orange orb with listening/thinking/speaking states.
- WorldView: a 3D globe in the browser with live USGS earthquake data, opened via the open_worldview tool when the user asks to open WorldView / open the globe / show worldwide earthquakes (in English or Hebrew).
- Achilles Core: an ultra-realistic WebGL black-hole screen that is your visual face, with a Solar System mode (clickable planets, facts + live news per planet), a typed command line, and a task list. Opened via the open_achilles tool when the user asks for the black hole, the Achilles screen, the solar system, or the to-do list (Hebrew: 'פתח את החור השחור', 'מערכת השמש', 'תראה לי את המשימות'). Pass scene='solar' for the solar system, scene='todo' for the task list, scene='core' for the black hole.
- Task list: 'תוסיף משימה X' / 'add task X' adds a task; the list lives in tasks.json and is shown on the Achilles screen.
- Mission Control: the project roadmap/status dashboard, opened via the open_roadmap tool when the user asks for the roadmap, project status, mission control, or the checklist page (in English or Hebrew).
- Deep Domain Learning (see CRITICAL rule #1): for a whole field (chemistry/physics/biology/etc.) call deep_learn_domain; for a narrow concept call learn_topic; for status call learning_status; to continue an existing curriculum call resume_learning. Always invoke the tool - never answer learning commands from memory.
- Knowledge module: when the user explicitly asks you to LEARN, STUDY, RESEARCH, or BUILD KNOWLEDGE on a topic (English: 'learn X', 'study Y', 'research Z'; Hebrew: 'תלמד X', 'ללמוד על Y', 'תחקור Z', 'בנה לי ידע על W'), call the learn_topic tool with the topic. If they mention a project the topic relates to, pass it as context. The tool produces a deep study note saved to the user's Obsidian Knowledge folder; it persists across sessions. After the tool returns, tell the user what was created and offer to read them the TL;DR if they want.

Rules:
- Keep replies to 1-3 sentences.
- ALWAYS reply in the SAME language the user spoke. If they speak Hebrew, reply
  fully in Hebrew. If English, reply in English. Never mix languages in one reply.

ISRAELI PLACE NAMES — read carefully:
Whisper (the speech-to-text engine) often mis-transcribes Hebrew city names,
especially when spoken in English transliteration. The user lives in Israel and
nearly every place he mentions is in Israel. When you see a word in the user's
message that doesn't quite spell a known city but SOUNDS LIKE one of the
common Israeli cities below, treat it as that city and pass the CANONICAL name
to find_places / get_directions. Be charitable — never tell the user "I don't
know that place" before trying the closest match.

Common Israeli cities (canonical English / Hebrew):
  Tel Aviv (תל אביב) · Jerusalem (ירושלים) · Haifa (חיפה)
  Kfar Saba (כפר סבא) · Petah Tikva (פתח תקווה) · Rishon LeZion (ראשון לציון)
  Ashdod (אשדוד) · Beer Sheva (באר שבע) · Netanya (נתניה)
  Herzliya (הרצליה) · Raanana (רעננה) · Hod HaSharon (הוד השרון)
  Bnei Brak (בני ברק) · Ramat Gan (רמת גן) · Givatayim (גבעתיים)
  Holon (חולון) · Bat Yam (בת ים) · Rehovot (רחובות)
  Modiin (מודיעין) · Lod (לוד) · Ramla (רמלה)
  Ashkelon (אשקלון) · Eilat (אילת) · Nazareth (נצרת)
  Tiberias (טבריה) · Tsfat / Safed (צפת) · Akko (עכו) · Nahariya (נהריה)
  Ariel (אריאל) · Alfei Menashe (אלפי מנשה — Matan's home)
  Kokhav Yair (כוכב יאיר) · Kfar Yona (כפר יונה)

Examples of mis-transcriptions you should silently fix:
  "kfar sabah" / "k'far saba" / "cafar saba" / "כפר סבה"  ->  Kfar Saba
  "petah tikvah" / "פתח טיקווה" / "פטח תקווה"            ->  Petah Tikva
  "rishon le tsiyon" / "ראשון לציון" variants            ->  Rishon LeZion
  "tel aviv yafo" / "telaviv"                            ->  Tel Aviv
  "beer shava" / "באר שבע" variants                       ->  Beer Sheva
- When asked about weather/temperature, ALWAYS default to his home town Alfei
  Menashe (אלפי מנשה) unless he clearly names a different city. If the spoken
  city name is unclear or garbled, assume Alfei Menashe — do not ask which city.
- Give temperatures in CELSIUS ONLY. Never mention Fahrenheit.
- When asked how you could be improved or what new features to add, suggest only
  things NOT already in your capabilities list above. NOTE: this rule applies
  ONLY to meta-questions about JARVIS itself ("how can you improve", "what
  new features should you have"). It does NOT apply to learning commands -
  those are always tool calls per CRITICAL rule #1, no matter how the user
  phrases them.
- Do not use markdown formatting (no asterisks, no bold). Plain text only.
- Reference past conversations from memory logs if relevant.
- If the user clearly ends the conversation or dismisses you in ANY wording or
  language (for example "that's enough", "we're done here", "I don't need
  anything else", "you can go", "leave it", or the Hebrew equivalents), reply
  with ONE short, warm butler-style sign-off and then put the token <END> as the
  very last characters of your reply. Do NOT add <END> in any other situation.
"""

conversation_history = []
# v4.67: think() is reachable concurrently from the voice turn, the Telegram
# loop AND the /ask HTTP worker threads, all sharing this one global list.
# Without a lock their appends interleave and corrupt the message sequence
# (API 400 "roles must alternate" / orphaned tool_use). This serialises the
# whole read-modify-API-append section of think().
_think_lock = threading.Lock()
MAX_HISTORY_MSGS = 24

def _normalize_history():
    """Keep conversation_history valid and bounded. Caller must hold _think_lock.
    (1) Drop a trailing assistant turn that holds an unanswered tool_use block
        (left behind when a reply was truncated mid-tool by max_tokens) - it
        would otherwise 400 every subsequent call for the rest of the session.
    (2) Trim to the last MAX_HISTORY_MSGS messages, advancing the window start
        to a plain-string user message so a tool_use/tool_result pair is never
        split (which would also 400)."""
    ch = conversation_history
    while ch:
        last = ch[-1]
        content = last.get("content")
        has_tool_use = isinstance(content, list) and any(
            (getattr(b, "type", None) == "tool_use")
            or (isinstance(b, dict) and b.get("type") == "tool_use")
            for b in content)
        if last.get("role") == "assistant" and has_tool_use:
            ch.pop()
        else:
            break
    if len(ch) > MAX_HISTORY_MSGS:
        start = len(ch) - MAX_HISTORY_MSGS
        while start < len(ch):
            m = ch[start]
            if m.get("role") == "user" and isinstance(m.get("content"), str):
                break
            start += 1
        if start < len(ch):
            ch[:] = ch[start:]

def ensure_directories():
    Path(SSD_OBSIDIAN_VAULT).mkdir(parents=True, exist_ok=True)
    Path(KNOWLEDGE_DIR).mkdir(parents=True, exist_ok=True)

def load_long_term_memory(max_chars=3000):
    vault = Path(SSD_OBSIDIAN_VAULT)
    if not vault.exists():
        return "No memory logs yet."
    logs = sorted(vault.glob("Log_*.md"), reverse=True)
    if not logs:
        return "No memory logs yet."
    text = ""
    for lf in logs:
        text += "\n" + lf.read_text(encoding="utf-8")
        if len(text) >= max_chars:
            break
    return text[:max_chars].strip()

def record_until_silence(filename="voice_input.wav", preroll=None):
    cd = 0.25
    cs = int(SAMPLE_RATE * cd)
    audio_chunks = []
    # Prepend pre-roll audio (the moment just before recording started) so the
    # first word said right after the wake word isn't lost. The stream returns
    # 2D chunks (frames, 1), so the pre-roll must be 2D too before concatenating.
    if preroll is not None and len(preroll) > 0:
        pr = np.asarray(preroll, dtype=np.float32)
        if pr.ndim == 1:
            pr = pr.reshape(-1, 1)
        audio_chunks.append(pr)
    silent = 0
    need_silent = int(SILENCE_DURATION / cd)
    max_c = int(MAX_DURATION / cd)
    min_c = int(MIN_DURATION / cd)
    spoke = False
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32') as stream:
        for i in range(max_c):
            chunk, _ = stream.read(cs)
            audio_chunks.append(chunk.copy())
            if float(np.max(np.abs(chunk))) >= SILENCE_THRESHOLD:
                spoke = True
                silent = 0
            else:
                silent += 1
            if spoke and i >= min_c and silent >= need_silent:
                break
    sf.write(filename, np.concatenate(audio_chunks), SAMPLE_RATE)
    return filename

def record_followup(filename="voice_input.wav", start_timeout=5.0):
    """Like record_until_silence, but for conversation follow-ups: if the user
    doesn't START speaking within start_timeout seconds, give up and return None
    (which ends the conversation). Once they start, record until they pause."""
    cd = 0.25
    cs = int(SAMPLE_RATE * cd)
    audio_chunks = []
    silent = 0
    need_silent = int(SILENCE_DURATION / cd)
    max_c = int(MAX_DURATION / cd)
    min_c = int(MIN_DURATION / cd)
    wait_c = int(start_timeout / cd)
    spoke = False
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32') as stream:
        for i in range(max_c):
            chunk, _ = stream.read(cs)
            loud = float(np.max(np.abs(chunk))) >= SILENCE_THRESHOLD
            if loud:
                spoke = True
                silent = 0
            else:
                silent += 1
            # If nothing was said within the start window, end the conversation.
            if not spoke and i >= wait_c:
                return None
            if spoke:
                audio_chunks.append(chunk.copy())
            if spoke and len(audio_chunks) >= min_c and silent >= need_silent:
                break
    if not spoke or not audio_chunks:
        return None
    sf.write(filename, np.concatenate(audio_chunks), SAMPLE_RATE)
    return filename

def beep():
    try:
        t = np.linspace(0, 0.15, int(SAMPLE_RATE * 0.15), False)
        tone = (0.2 * np.sin(2 * np.pi * 880 * t)).astype(np.float32)
        sd.play(tone, SAMPLE_RATE)
        sd.wait()
    except Exception:
        pass

def transcribe(model, filename):
    # Return BOTH the text and the language Whisper detected (e.g. "he", "en").
    # JARVIS only ever works in Hebrew or English, so we constrain Whisper to
    # those two. If it detects Hebrew we transcribe as Hebrew; anything else we
    # force to English. This stops short clips from being mis-read as German,
    # French, etc. — which previously made JARVIS reply in the wrong language.
    segments, info = model.transcribe(filename, beam_size=5)
    detected = (getattr(info, "language", None) or "").lower()
    if detected == "he":
        text = "".join(s.text for s in segments).strip()
        return text, "he"
    # Not Hebrew -> re-transcribe forced to English so the text isn't German/etc.
    try:
        segments, info = model.transcribe(filename, beam_size=5, language="en")
        text = "".join(s.text for s in segments).strip()
    except Exception:
        text = "".join(s.text for s in segments).strip()
    return text, "en"

def transcribe_wake(model, filename):
    # v4.67: wake detection must favour RECALL - a dropped wake word means the
    # user is silently ignored (no orb, no voice). v4.65 stacked vad_filter=True
    # + no_speech_threshold=0.6 + a manual no_speech_prob<0.6 filter, which on
    # the tiny model trimmed a short, isolated "Achilles"/"Jarvis" to "" so the
    # wake never fired. We rely instead on WAKE_GATE (only transcribe when there
    # is real audio energy) and detect_wake() (the text must actually contain a
    # wake word), so we can decode permissively here: NO VAD trimming, and keep
    # every segment unless the model is *extremely* sure the clip is non-speech.
    try:
        segments, _info = model.transcribe(
            filename, beam_size=1, language=None,
            condition_on_previous_text=False, vad_filter=False,
            no_speech_threshold=0.85,
        )
    except TypeError:
        segments, _info = model.transcribe(
            filename, beam_size=1, language=None,
            condition_on_previous_text=False,
        )
    parts = [s.text for s in segments if getattr(s, "no_speech_prob", 1.0) < 0.9]
    return "".join(parts).strip()

def detect_wake(text):
    if not text:
        return False
    t = text.lower()
    for ch in ",.!?-:;\"'":
        t = t.replace(ch, " ")
    t_nospace = t.replace(" ", "")
    for w in WAKE_WORDS:
        if w in t or w.replace(" ", "") in t_nospace:
            return True
    return False

def strip_wake_prefix(text):
    """Remove a leading wake word (e.g. 'Hey Jarvis') that the pre-roll may have
    captured, leaving just the actual command. Strips up to the last wake word
    found near the start."""
    if not text:
        return text
    words = text.split()
    # scan the first few words; drop everything up to and including a wake word
    cut = 0
    fillers = {"hey", "hi", "ok", "okay", "\u05d4\u05d9\u05d9", "\u05d0\u05d5\u05e7\u05d9\u05d9"}
    for idx, w in enumerate(words[:4]):
        wl = w.lower().strip(",.!?-:;\"'")
        if any(k.replace(" ", "") in wl for k in WAKE_WORDS):
            cut = idx + 1
        elif wl in fillers and cut == 0:
            continue
    return " ".join(words[cut:]).strip() if cut else text

def detect_write(text):
    if not text:
        return False
    t = text.lower()
    for ch in ",.!?-:;\"'":
        t = t.replace(ch, " ")
    words = t.split()
    return any(w in words for w in WRITE_WORDS)

def detect_goodbye(text):
    """True if the user clearly ended the conversation. Matches whole phrases so
    a word like 'bye' inside a longer sentence ('maybe later') won't trigger it
    falsely; we check the cleaned text contains a goodbye phrase as a unit."""
    if not text:
        return False
    t = text.lower().strip()
    # drop apostrophes so "that's" -> "thats", "you're" -> "youre"
    for ap in ("'", "\u2019", "`"):
        t = t.replace(ap, "")
    for ch in ",.!?-:;\"":
        t = t.replace(ch, " ")
    t = " ".join(t.split())  # collapse spaces
    # short message that *is* basically a farewell, or ends with one
    for g in GOODBYE_WORDS:
        gg = g.replace("'", "").replace("\u2019", "")
        if t == gg or t.endswith(" " + gg) or t.startswith(gg + " ") or (" " + gg + " ") in (" " + t + " "):
            return True
    return False

def pick_farewell(is_he):
    import random
    return random.choice(FAREWELLS_HE if is_he else FAREWELLS_EN)

def is_hebrew(text):
    return bool(re.search(r'[\u0590-\u05FF]', text))

def is_mostly_hebrew(text):
    """Used to choose TTS voice. True only when MORE than half the alphabetic
    characters are Hebrew. A reply that's mostly English with a few Hebrew
    place names returns False - so the ElevenLabs Alfred voice is used."""
    if not text:
        return False
    he_count = len(re.findall(r'[\u0590-\u05FF]', text))
    en_count = len(re.findall(r'[A-Za-z]', text))
    if he_count == 0:
        return False
    return he_count > en_count

def clean_text(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+', '', text)
    text = re.sub(r'`+', '', text)
    # Remove stray bracketed asides like "[note: ...]" or "(source: ...)" and any
    # leftover empty brackets, which sound odd when spoken and look messy on screen.
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'\((?:source|ref|link|note|see)[^)]*\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\[\]]', '', text)        # any remaining loose square brackets
    # v3.16: strip web addresses so JARVIS never READS a URL aloud anywhere (the
    # clickable links still appear in the search window). This catches full URLs,
    # "www." addresses, and bare domains with common TLDs (e.g. ikea.com,
    # ikea.co.il) — but NOT a plain store name like "IKEA" (no dot), so the name
    # is still spoken.
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\bwww\.\S+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b[\w-]+\.(?:com|net|org|io|ai|co|me|shop|store|info|'
                  r'co\.il|org\.il|gov\.il|ac\.il|net\.il)\b\S*',
                  '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s{2,}', ' ', text)        # collapse double spaces left behind
    text = re.sub(r'\s+([.,!?])', r'\1', text)  # tidy spaces left before punctuation
    return text.strip()

def open_app(name):
    """Open an app or site from the closed allow-list. Returns a status string
    that gets handed back to Claude so it can phrase a natural reply."""
    if not name:
        return "No app name given."
    key = name.strip().lower()
    # tolerate small variations Whisper might produce
    for allowed, cmd in ALLOWED_APPS.items():
        if allowed in key or key in allowed:
            try:
                os.system(cmd)
                return f"Opened {allowed}."
            except Exception as e:
                return f"Failed to open {allowed}: {e}"
    return (f"'{name}' is not in the allowed list. Allowed: "
            + ", ".join(ALLOWED_APPS.keys()))

def save_note(text):
    """Append a timestamped note to the Obsidian notes file. Returns status."""
    if not text or not text.strip():
        return "The note was empty, nothing saved."
    try:
        now = datetime.datetime.now()
        nf = Path(NOTES_FOLDER) / f"Notes_{now.strftime('%Y-%m-%d')}.md"
        written = f"\n- [{now.strftime('%H:%M')}] {text.strip()}\n"
        with open(nf, "a", encoding="utf-8") as f:
            f.write(written)
        _record_action("save_note", {"path": str(nf), "written": written})
        return "Note saved to Obsidian."
    except Exception as e:
        return f"Failed to save note: {e}"

def _slugify_topic(topic: str) -> str:
    """Turn a free-form topic into a safe filename. Keeps Hebrew/Latin letters
    and digits, collapses everything else into single underscores, and trims
    leading/trailing underscores. Filename only - no extension."""
    import re
    s = (topic or "").strip()
    # Replace anything that isn't a letter (any language) or digit with _
    s = re.sub(r"[^\w]+", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "untitled"
    # Cap filename length to keep things reasonable on Windows
    return s[:80]

def _link_existing_notes(note_md, current_slug=None):
    """Inject Obsidian wiki links into note_md for the first mention of each
    existing knowledge note's title. Skips the current note's own slug.
    Returns the modified note text. Best-effort: any error returns the
    unmodified text so this never blocks a note from being written."""
    try:
        base = Path(KNOWLEDGE_DIR)
        if not base.exists():
            return note_md
        cands = []  # (title, slug)
        for f in base.rglob("*.md"):
            if f.name.startswith("_"):  # skip _index.md etc.
                continue
            slug = f.stem
            if current_slug and slug == current_slug:
                continue
            try:
                head = "\n".join(
                    f.read_text(encoding="utf-8").splitlines()[:30])
            except Exception:
                continue
            title = None
            m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$",
                          head, re.MULTILINE)
            if m:
                title = m.group(1).strip()
            else:
                m = re.search(r"^#\s+(.+?)\s*$", head, re.MULTILINE)
                if m:
                    title = m.group(1).strip()
            if not title:
                title = slug.replace("_", " ")
            if len(title) < 6:
                continue  # skip generic short words
            cands.append((title, slug))
        if not cands:
            return note_md
        # Longest title first so "Bernoulli's principle" beats "Bernoulli".
        cands.sort(key=lambda t: -len(t[0]))
        result = note_md
        for title, slug in cands:
            pat = r"\b" + re.escape(title) + r"\b"
            def _make_link(m, _s=slug):
                return "[[" + _s + "|" + m.group(0) + "]]"
            new, n = re.subn(pat, _make_link, result, count=1,
                             flags=re.IGNORECASE)
            if n > 0:
                result = new
        return result
    except Exception:
        return note_md


def learn_topic(topic: str, context: str = ""):
    """Generate a structured deep study note on `topic` (optionally tailored
    to a `context` like a project the user is working on), and save it as
    Markdown to <KNOWLEDGE_DIR>/<topic>.md. Returns a short status string.

    If a note on this topic already exists, the new content is appended as a
    follow-up section so multiple "learn" calls deepen the same file over
    time rather than overwriting it.
    """
    if not topic or not topic.strip():
        return "I need a topic to study, sir. Please tell me what to learn."
    if not ANTHROPIC_API_KEY:
        return "Can't reach the research model - the Anthropic key isn't set, sir."

    topic = topic.strip()
    context = (context or "").strip()

    # Build the research prompt. We ask for pure Markdown with no preamble,
    # so we can write the response straight to disk.
    research_system = (
        "You are a research assistant generating a structured deep study "
        "note. Output ONLY Markdown - no preamble, no postamble, no "
        "conversational text. The note must be self-contained, accurate, "
        "and university-level in depth.\n\n"
        "Required structure:\n"
        "1. A YAML frontmatter block with: title, date (today, ISO), tags "
        "(3-6 relevant tags), depth: foundational.\n"
        "2. A top-level heading with the topic name.\n"
        "3. ## TL;DR - 3 to 5 sentences capturing the essence.\n"
        "4. ## Foundational Principles - the core concepts, each with a "
        "short explanation.\n"
        "5. ## Key Equations / Formulas - if applicable; each equation "
        "with every symbol defined.\n"
        "6. ## Sub-topics - 3 to 6 sub-areas, each with a paragraph of "
        "depth.\n"
        "7. ## Common Questions - Q&A format, 3 to 6 entries.\n"
        "8. ## Sources for Further Study - books, papers, or canonical "
        "references. Real sources only; never invent citations.\n"
        "9. ## Related Topics - 3 to 6 adjacent topics worth studying "
        "next, as a bullet list.\n\n"
        "If the topic crosses into weapon design specifics or other "
        "areas you cannot detail responsibly, cover the public physics, "
        "theory, and history at full depth, and briefly note what is "
        "out of scope. Never invent specifications."
    )
    user_prompt = "Topic to study: " + topic
    if context:
        user_prompt += "\nContext / use case: " + context
    user_prompt += "\n\nGenerate the full Markdown note now."

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        # Use a generous max_tokens so the note can be properly deep.
        # Model choice mirrors what the rest of JARVIS already uses.
        resp = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=8000,
            system=research_system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        parts = []
        for block in (resp.content or []):
            if getattr(block, "type", "") == "text":
                parts.append(block.text)
        note_md = "\n".join(parts).strip()
        if not note_md:
            return "The research model returned nothing, sir. Try again."
    except Exception as e:
        return f"Research failed: {e}"

    # Write to disk. If a note on this topic already exists, append a
    # timestamped deepening section instead of overwriting.
    try:
        Path(KNOWLEDGE_DIR).mkdir(parents=True, exist_ok=True)
        slug = _slugify_topic(topic)
        path = Path(KNOWLEDGE_DIR) / f"{slug}.md"
        now = datetime.datetime.now()
        note_md = _link_existing_notes(note_md, current_slug=slug)
        if path.exists():
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n\n---\n\n")
                f.write(f"## Deepening - {now.strftime('%Y-%m-%d %H:%M')}\n\n")
                if context:
                    f.write(f"_Context: {context}_\n\n")
                f.write(note_md)
                f.write("\n")
            action = "deepened existing"
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(note_md)
                f.write("\n")
            action = "created"
    except Exception as e:
        return f"Note generated but writing to disk failed: {e}"

    # Brief stats for the spoken reply
    word_count = len(note_md.split())
    return (f"Knowledge note on {topic} {action}, sir. "
            f"About {word_count} words, saved at Knowledge/{slug}.md.")


# =====================================================================
# Deep Domain Learning - learn an entire field in the background
# =====================================================================
# A single in-process worker at a time. State of record is the per-domain
# _queue.json on disk, so an interrupted run loses no work.
DEEP_LEARN_DEFAULT_CAP = 15        # max notes per run (cost guard)
_deep_learn_lock = threading.Lock()
_deep_learn_state = {"running": False, "domain": None, "done": 0,
                     "target": 0, "total": 0, "last": ""}

def _domain_dir(domain: str) -> Path:
    return Path(KNOWLEDGE_DIR) / _slugify_topic(domain)

def _load_queue(domain: str):
    qf = _domain_dir(domain) / "_queue.json"
    if not qf.exists():
        return None
    try:
        return json.loads(qf.read_text(encoding="utf-8"))
    except Exception:
        return None

def _save_queue(domain: str, data: dict):
    d = _domain_dir(domain)
    d.mkdir(parents=True, exist_ok=True)
    (d / "_queue.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _rebuild_index(domain: str, data: dict):
    """Write a human-readable _index.md listing every sub-topic + status."""
    d = _domain_dir(domain)
    lines = ["# " + data.get("domain", domain) + " - Knowledge Index", ""]
    done = sum(1 for it in data["items"] if it["status"] == "done")
    lines.append(f"_{done} of {len(data['items'])} sub-topics learned._")
    lines.append("")
    for it in data["items"]:
        mark = {"done": "[x]", "pending": "[ ]", "error": "[!]"}.get(it["status"], "[ ]")
        if it["status"] == "done" and it.get("file"):
            lines.append(f"- {mark} [[{it['file'][:-3]}]] - {it['topic']}")
        else:
            lines.append(f"- {mark} {it['topic']}")
    (d / "_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def _decompose_domain(domain: str):
    """Ask Claude for a curriculum: a JSON list of sub-topics for `domain`.
    Returns a list of strings, or None on failure."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    sys_p = (
        "You are a curriculum designer. Given a field of study, return a "
        "comprehensive list of sub-topics that together cover the field at "
        "university depth. Output ONLY a JSON array of short topic strings - "
        "no prose, no markdown fences, no keys. Between 20 and 40 items. "
        "Order them pedagogically (foundations first). Each string should be "
        "a concrete, learnable sub-topic, not a vague heading."
    )
    try:
        r = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2000,
            system=sys_p,
            messages=[{"role": "user", "content": "Field: " + domain}],
        )
        txt = ""
        for b in (r.content or []):
            if getattr(b, "type", "") == "text":
                txt += b.text
        txt = txt.strip()
        # Strip accidental code fences
        if txt.startswith("```"):
            txt = txt.strip("`")
            nl = txt.find("\n")
            if nl != -1:
                txt = txt[nl + 1:]
        start = txt.find("[")
        end = txt.rfind("]")
        if start != -1 and end != -1:
            txt = txt[start:end + 1]
        items = json.loads(txt)
        out = [str(x).strip() for x in items if str(x).strip()]
        return out or None
    except Exception as e:
        print("[diag] domain decompose failed:", repr(e))
        return None

def _deep_learn_worker(domain: str, cap: int):
    """Background thread: walk the queue, learn up to `cap` pending items."""
    try:
        made = 0
        while made < cap:
            data = _load_queue(domain)
            if not data:
                break
            nxt = None
            for it in data["items"]:
                if it["status"] == "pending":
                    nxt = it
                    break
            if nxt is None:
                break  # nothing left to do
            topic = nxt["topic"]
            with _deep_learn_lock:
                _deep_learn_state["last"] = topic
            # Reuse the single-note generator. The note is filed under the
            # domain folder so the whole field stays together.
            try:
                _learn_one_into_domain(domain, topic, nxt)
                nxt["status"] = "done"
            except Exception as e:
                nxt["status"] = "error"
                nxt["error"] = str(e)[:200]
            data["last_run"] = datetime.datetime.now().isoformat(timespec="seconds")
            _save_queue(domain, data)
            _rebuild_index(domain, data)
            made += 1
            with _deep_learn_lock:
                _deep_learn_state["done"] = sum(
                    1 for x in data["items"] if x["status"] == "done")
    finally:
        with _deep_learn_lock:
            _deep_learn_state["running"] = False

def _find_existing_note(slug, exclude_dir=None):
    """Search Obsidian_Vault/Knowledge/ for a .md file matching <slug>.md.
    Returns the first match Path, or None. `exclude_dir`, if given, skips
    every file under that directory (used to skip the current domain so we
    only detect CROSS-domain duplicates)."""
    try:
        base = Path(KNOWLEDGE_DIR)
        if not base.exists():
            return None
        target_name = slug + ".md"
        excl = None
        if exclude_dir is not None:
            try:
                excl = Path(exclude_dir).resolve()
            except Exception:
                excl = None
        for f in base.rglob(target_name):
            if f.name.startswith("_"):
                continue
            if excl is not None:
                try:
                    fr = f.resolve()
                    if fr == excl or excl in fr.parents:
                        continue
                except Exception:
                    pass
            return f
        return None
    except Exception:
        return None


def _learn_one_into_domain(domain: str, topic: str, item: dict):
    """Generate one deep note and save it inside the domain folder.
    Raises on failure so the worker can mark the item as error.
    v4.27: duplicate-prevention - if a note on this slug already exists in
    another domain, skip the API call and write a short stub that wiki-
    links to it."""
    slug = _slugify_topic(topic)
    existing_dup = _find_existing_note(slug, exclude_dir=_domain_dir(domain))
    if existing_dup is not None:
        d = _domain_dir(domain)
        d.mkdir(parents=True, exist_ok=True)
        try:
            rel = existing_dup.relative_to(Path(KNOWLEDGE_DIR))
            other_domain = (rel.parts[0].replace("_", " ")
                            if len(rel.parts) > 1 else "knowledge base")
        except Exception:
            other_domain = "knowledge base"
        stub_md = ("# " + topic + "\n\n"
                   "_Already covered in " + other_domain + ". "
                   "See: [[" + existing_dup.stem + "|" + topic + "]]._\n")
        fname = slug + ".md"
        (d / fname).write_text(stub_md, encoding="utf-8")
        item["file"] = fname
        item["duplicate_of"] = existing_dup.stem
        return
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    research_system = (
        "You are a research assistant generating a structured deep study "
        "note as part of a larger curriculum on '" + domain + "'. Output "
        "ONLY Markdown - no preamble. Use this structure: YAML frontmatter "
        "(title, date ISO, tags, domain: '" + domain + "', depth: "
        "foundational); a top-level heading; ## TL;DR (3-5 sentences); "
        "## Foundational Principles; ## Key Equations / Formulas (define "
        "every symbol; omit if N/A); ## Sub-topics (3-6, each a paragraph); "
        "## Common Questions (Q&A, 3-6); ## Sources for Further Study (real "
        "references only); ## Related Topics (bullet list). Never invent "
        "citations or specifications. If a topic crosses into content you "
        "cannot detail responsibly, cover the public theory at full depth "
        "and note briefly what is out of scope."
    )
    r = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8000,
        system=research_system,
        messages=[{"role": "user",
                   "content": "Sub-topic to study in depth: " + topic
                              + "\n\nGenerate the full Markdown note now."}],
    )
    parts = []
    for b in (r.content or []):
        if getattr(b, "type", "") == "text":
            parts.append(b.text)
    note_md = "\n".join(parts).strip()
    if not note_md:
        raise RuntimeError("empty response from model")
    d = _domain_dir(domain)
    d.mkdir(parents=True, exist_ok=True)
    fname = _slugify_topic(topic) + ".md"
    note_md = _link_existing_notes(note_md, current_slug=fname[:-3])
    (d / fname).write_text(note_md + "\n", encoding="utf-8")
    item["file"] = fname

def deep_learn_domain(domain: str, max_notes=None):
    """Plan a curriculum for `domain` and start learning it in the
    background, up to `max_notes` notes this run (default cap). Returns a
    short status string for the spoken reply."""
    if not domain or not domain.strip():
        return "Which field should I study, sir?"
    if not ANTHROPIC_API_KEY:
        return "Can't reach the research model - the Anthropic key isn't set, sir."
    domain = domain.strip()
    try:
        cap = int(max_notes) if max_notes else DEEP_LEARN_DEFAULT_CAP
    except Exception:
        cap = DEEP_LEARN_DEFAULT_CAP
    cap = max(1, min(cap, 60))  # absolute safety ceiling

    with _deep_learn_lock:
        if _deep_learn_state["running"]:
            cur = _deep_learn_state["domain"]
            return (f"I'm already learning {cur} in the background, sir "
                    f"({_deep_learn_state['done']} of {_deep_learn_state['target']} this run). "
                    f"Let it finish, or ask for a status.")

    # If a queue already exists for this domain, resume it instead of redoing.
    existing = _load_queue(domain)
    if existing and any(it["status"] == "pending" for it in existing["items"]):
        return resume_learning(domain, max_notes=cap)

    items = _decompose_domain(domain)
    if not items:
        return f"I couldn't build a study plan for {domain}, sir. Try again or rephrase."

    data = {
        "domain": domain,
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "items": [{"topic": t, "status": "pending"} for t in items],
    }
    _save_queue(domain, data)
    _rebuild_index(domain, data)

    target = min(cap, len(items))
    with _deep_learn_lock:
        _deep_learn_state.update({"running": True, "domain": domain, "done": 0,
                                  "target": target, "total": len(items), "last": ""})
    t = threading.Thread(target=_deep_learn_worker, args=(domain, cap), daemon=True)
    t.start()

    return (f"Study plan ready for {domain}, sir: {len(items)} sub-topics. "
            f"Learning the first {target} in the background now - this takes "
            f"a while. Say 'learning status' to check progress, or 'continue "
            f"learning {domain}' later for the rest.")

def resume_learning(domain: str, max_notes=None):
    """Resume learning pending sub-topics for an already-planned domain."""
    if not domain or not domain.strip():
        return "Which field should I continue, sir?"
    domain = domain.strip()
    try:
        cap = int(max_notes) if max_notes else DEEP_LEARN_DEFAULT_CAP
    except Exception:
        cap = DEEP_LEARN_DEFAULT_CAP
    cap = max(1, min(cap, 60))
    with _deep_learn_lock:
        if _deep_learn_state["running"]:
            return (f"Already learning {_deep_learn_state['domain']} right now, sir. "
                    f"One field at a time.")
    data = _load_queue(domain)
    if not data:
        return f"I have no study plan for {domain} yet, sir. Ask me to deep-learn it first."
    pending = [it for it in data["items"] if it["status"] == "pending"]
    if not pending:
        done = sum(1 for it in data["items"] if it["status"] == "done")
        return f"{domain} is already complete, sir: {done} of {len(data['items'])} learned."
    target = min(cap, len(pending))
    with _deep_learn_lock:
        _deep_learn_state.update({"running": True, "domain": domain,
                                  "done": sum(1 for it in data["items"] if it["status"]=="done"),
                                  "target": target, "total": len(data["items"]), "last": ""})
    t = threading.Thread(target=_deep_learn_worker, args=(domain, cap), daemon=True)
    t.start()
    return (f"Resuming {domain}, sir: {len(pending)} sub-topics left, "
            f"learning {target} now in the background.")

def learning_status():
    """Report progress of any running or planned deep-learning."""
    with _deep_learn_lock:
        running = _deep_learn_state["running"]
        domain = _deep_learn_state["domain"]
        done = _deep_learn_state["done"]
        total = _deep_learn_state["total"]
        last = _deep_learn_state["last"]
    if running and domain:
        tail = f" Currently on: {last}." if last else ""
        return (f"Learning {domain} in the background, sir: "
                f"{done} of {total} sub-topics done.{tail}")
    # Nothing running - summarise any domains that have a queue on disk.
    try:
        base = Path(KNOWLEDGE_DIR)
        if base.exists():
            rows = []
            for sub in sorted(base.iterdir()):
                qf = sub / "_queue.json"
                if qf.exists():
                    try:
                        d = json.loads(qf.read_text(encoding="utf-8"))
                        dn = sum(1 for it in d["items"] if it["status"]=="done")
                        rows.append(f"{d.get('domain', sub.name)} ({dn}/{len(d['items'])})")
                    except Exception:
                        pass
            if rows:
                return "Nothing learning right now, sir. Domains so far: " + "; ".join(rows) + "."
    except Exception:
        pass
    return "Nothing is learning right now, sir, and no study plans exist yet."

_worldview_server_proc = None  # background python -m http.server, started lazily

def _wv_port_in_use(port):
    """Return True if something is already listening on 127.0.0.1:port."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False
    finally:
        try: s.close()
        except Exception: pass

# ---------------------------------------------------------------------------
# v4.45: FLIGHTS proxy (adsb.lol -> browser, sidesteps CORS)
# Runs in-process on a daemon thread, on 0.0.0.0:7778 (LAN-reachable,
# so the phone can use FLIGHTS too; firewall rule already allows it).
# Endpoint: GET /flights?lat=X&lon=Y&radius=R   (radius is in nautical miles)
# Always returns CORS header so the WorldView page on :7777 can fetch it.
# ---------------------------------------------------------------------------
_flights_proxy_started = False
_flights_proxy_lock = threading.Lock()
_tle_cache = {"ts": 0.0, "data": b""}  # v4.51: Celestrak TLE cache (6h)
# v4.52: live assistant state for the Achilles screen. "scene" is which
# scene the page should show (core = black hole, solar = solar system);
# "last_poll" lets open_achilles() know a page is already connected so it
# flips the scene instead of spawning a second window.
_achilles_state = {"state": "loading", "scene": "core", "ts": 0.0,
                   "last_poll": 0.0}
_planet_news_cache = {}  # v4.52: planet name -> {"ts": float, "text": str}
_tasks_lock = threading.Lock()  # v4.53: guards tasks.json

# ---------------------------------------------------------------------------
# VESSELS relay (v4.66). aisstream.io is WebSocket-only and BLOCKS browser-direct
# connections, so we hold ONE server-side WebSocket here, keep the latest position
# per ship (by MMSI) in memory, and serve a snapshot at GET /vessels on the same
# :7778 proxy (mirrors how /flights works). Eastern-Mediterranean bounding box.
# Needs AISSTREAM_API_KEY in .env and the `websockets` package installed.
# ---------------------------------------------------------------------------
_vessels = {}                        # mmsi -> {mmsi,lat,lon,cog,sog,heading,name,type,ts}
_vessels_lock = threading.Lock()
_vessels_relay_started = False
_vessels_relay_lock = threading.Lock()
# bbox corners are [lat, lon]; this covers the Eastern Med incl. Israel/Cyprus.
_VESSELS_BBOX = [[[29.0, 24.0], [38.0, 37.0]]]

def _ais_bearing(b):
    """v4.67: return b if it is a valid 0-359 AIS bearing, else None. Handles the
    511 'heading not available' and 360 'COG not available' sentinels, None, and
    out-of-range junk, so the globe never draws a vessel at a fake heading."""
    try:
        return b if (b is not None and 0 <= float(b) < 360) else None
    except (TypeError, ValueError):
        return None

async def _vessels_ws_loop(api_key):
    import websockets  # lazy import so a missing package can never break boot
    url = "wss://stream.aisstream.io/v0/stream"
    sub = json.dumps({
        "APIKey": api_key,
        "BoundingBoxes": _VESSELS_BBOX,
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    })
    while True:
        try:
            async with websockets.connect(url, ping_interval=20, max_size=None) as ws:
                await ws.send(sub)
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue
                    mt = msg.get("MessageType")
                    meta = msg.get("MetaData", {}) or {}
                    mmsi = meta.get("MMSI")
                    if not mmsi:
                        continue
                    now = time.time()
                    if mt == "PositionReport":
                        pr = (msg.get("Message", {}) or {}).get("PositionReport", {}) or {}
                        lat = pr.get("Latitude", meta.get("latitude"))
                        lon = pr.get("Longitude", meta.get("longitude"))
                        if lat is None or lon is None:
                            continue
                        # v4.67: validate AIS sentinels (heading 511, COG 360,
                        # None, out-of-range) instead of storing them as a real
                        # bearing; fall back heading -> course over ground.
                        cog = _ais_bearing(pr.get("Cog"))
                        heading = _ais_bearing(pr.get("TrueHeading"))
                        if heading is None:
                            heading = cog
                        sog = pr.get("Sog")
                        try:
                            sog = float(sog) if (sog is not None and 0 <= float(sog) < 102.3) else None
                        except (TypeError, ValueError):
                            sog = None
                        with _vessels_lock:
                            v = _vessels.get(mmsi, {})
                            v.update({"mmsi": mmsi, "lat": lat, "lon": lon,
                                      "cog": cog, "sog": sog,
                                      "heading": heading, "ts": now})
                            nm = (meta.get("ShipName") or "").strip()
                            if nm:
                                v["name"] = nm
                            _vessels[mmsi] = v
                    elif mt == "ShipStaticData":
                        sd = (msg.get("Message", {}) or {}).get("ShipStaticData", {}) or {}
                        with _vessels_lock:
                            v = _vessels.get(mmsi, {"mmsi": mmsi})
                            nm = (sd.get("Name") or meta.get("ShipName") or "").strip()
                            if nm:
                                v["name"] = nm
                            t = sd.get("Type")
                            if t is not None:
                                v["type"] = t
                            # v4.67: refresh ts on every message so a vessel that
                            # only sends static data isn't pruned while active.
                            v["ts"] = now
                            _vessels[mmsi] = v
        except Exception as e:
            try:
                print("[diag] vessels relay reconnect after error: %r" % (e,))
            except Exception:
                pass
            await asyncio.sleep(5)

def _start_vessels_relay():
    """Start the aisstream WebSocket relay on a daemon thread. Idempotent.
    No-op (logged) if AISSTREAM_API_KEY is missing or `websockets` isn't installed."""
    global _vessels_relay_started
    with _vessels_relay_lock:
        if _vessels_relay_started:
            return
        api_key = os.environ.get("AISSTREAM_API_KEY", "") or ""
        if not api_key:
            print("[diag] vessels relay: no AISSTREAM_API_KEY in .env - VESSELS disabled")
            return
        try:
            import websockets  # noqa: F401
        except Exception:
            print("[diag] vessels relay: `websockets` not installed - run: pip install websockets")
            return
        def _run():
            try:
                asyncio.run(_vessels_ws_loop(api_key))
            except Exception as e:
                print("[diag] vessels relay thread died: %r" % (e,))
        threading.Thread(target=_run, daemon=True, name="jarvis-vessels-relay").start()
        _vessels_relay_started = True
        print("[diag] vessels relay started (aisstream, Eastern-Med bbox)")


class _FlightsProxyHandler(http.server.BaseHTTPRequestHandler):
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Cache-Control", "no-store")

    def do_OPTIONS(self):
        # preflight - just allow it
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/route":
            self._handle_route(parsed)
            return
        if parsed.path == "/tle":
            self._handle_tle()
            return
        if parsed.path == "/state":
            self._handle_state()
            return
        if parsed.path == "/planet":
            self._handle_planet(parsed)
            return
        if parsed.path == "/ask":
            self._handle_ask(parsed)
            return
        if parsed.path in ("/todo", "/todo_add", "/todo_toggle", "/todo_del"):
            self._handle_todo(parsed)
            return
        # --- WorldView API keys endpoint (wv_keys_endpoint) ----------------
        if parsed.path == "/keys":
            # v4.73: the proxy binds 0.0.0.0 so the phone can reach WorldView,
            # but these API keys (Google Maps / OpenWeatherMap) are only needed
            # by the WorldView frontend running on this PC. Gate the endpoint to
            # loopback like /ask and the mutating /todo actions - otherwise any
            # LAN host, or a drive-by web page abusing the permissive CORS, can
            # GET /keys and harvest them. (Also add an HTTP-referrer restriction
            # on the Maps key in the Google console; a Maps JS key is inherently
            # client-visible, so referrer-locking it is the real protection.)
            _peer = self.client_address[0] if self.client_address else ""
            if _peer not in ("127.0.0.1", "::1", "localhost"):
                self.send_response(403)
                self._cors_headers()
                self.end_headers()
                return
            try:
                import json as _json
                _payload = _json.dumps({
                    "googleMapsApiKey": os.environ.get("GOOGLE_MAPS_API_KEY", "") or "",
                    "owmApiKey": os.environ.get("OWM_API_KEY", "") or "",
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._cors_headers()
                self.send_header("Content-Length", str(len(_payload)))
                self.end_headers()
                self.wfile.write(_payload)
            except Exception as _e:
                try:
                    self.send_response(500); self._cors_headers(); self.end_headers()
                except Exception:
                    pass
            return
        # --- WorldView VESSELS snapshot (v4.66) ----------------------------
        if parsed.path == "/vessels":
            try:
                import json as _json
                now = time.time()
                with _vessels_lock:
                    items = [dict(v) for v in _vessels.values()
                             if v.get("lat") is not None and v.get("lon") is not None
                             and (now - v.get("ts", 0)) < 600]
                    stale = [m for m, v in _vessels.items()
                             if (now - v.get("ts", 0)) > 1800]
                    for m in stale:
                        _vessels.pop(m, None)
                payload = _json.dumps({"vessels": items,
                                       "count": len(items)}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._cors_headers()
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as _e:
                try:
                    body = ('{"error":' + json.dumps(str(_e))
                            + ',"vessels":[]}').encode("utf-8")
                    self.send_response(502)
                    self.send_header("Content-Type", "application/json")
                    self._cors_headers()
                    self.end_headers()
                    self.wfile.write(body)
                except Exception:
                    pass
            return
        if parsed.path != "/flights":
            self.send_response(404)
            self._cors_headers()
            self.end_headers()
            return
        try:
            params = urllib.parse.parse_qs(parsed.query)
            lat = params.get("lat", ["32.0"])[0]
            lon = params.get("lon", ["34.8"])[0]
            radius = params.get("radius", ["250"])[0]
            # validate as numbers - rejects junk before talking to adsb.lol
            float(lat); float(lon); int(float(radius))
            url = "https://api.adsb.lol/v2/lat/%s/lon/%s/dist/%s" % (lat, lon, radius)
            req = urllib.request.Request(url, headers={
                "User-Agent": "JARVIS-WorldView/1.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            try:
                body = (
                    '{"error":' + json.dumps(str(e)) + ',"ac":[]}'
                ).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                pass

    def _handle_route(self, parsed):
        # Origin/destination is NOT in raw ADS-B; adsb.lol exposes plausible
        # routes via POST /api/0/routeset keyed on callsign. We proxy it here
        # (browser is blocked by CORS, same as the flights feed).
        try:
            params = urllib.parse.parse_qs(parsed.query)
            cs = (params.get("callsign", [""])[0] or "").strip().upper()
            lat = params.get("lat", ["32.0"])[0]
            lon = params.get("lon", ["34.8"])[0]
            float(lat); float(lon)
            if not cs:
                raise ValueError("no callsign")
            body = json.dumps({"planes": [
                {"callsign": cs, "lat": float(lat), "lng": float(lon)}
            ]}).encode("utf-8")
            req = urllib.request.Request(
                "https://api.adsb.lol/api/0/routeset",
                data=body, method="POST",
                headers={
                    "User-Agent": "JARVIS-WorldView/1.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                out = r.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(out)
        except Exception as e:
            try:
                msg = ('{"error":' + json.dumps(str(e)) + '}').encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(msg)
            except Exception:
                pass

    def _handle_tle(self):
        # v4.51: TLE feed for the WorldView SATELLITES tab. Pulls the
        # "stations" (ISS, CSS, crewed) and "visual" (brightest ~150)
        # group files from Celestrak, dedupes by NORAD id, and caches the
        # JSON in-process for 6 hours - TLEs change slowly, be polite.
        global _tle_cache
        try:
            now = time.time()
            if _tle_cache["data"] and (now - _tle_cache["ts"] < 6 * 3600):
                payload = _tle_cache["data"]
            else:
                sats, seen = [], set()
                for grp_name, grp_tag in (("stations", "station"),
                                          ("visual", "visual")):
                    url = ("https://celestrak.org/NORAD/elements/gp.php"
                           "?GROUP=%s&FORMAT=tle" % grp_name)
                    req = urllib.request.Request(url, headers={
                        "User-Agent": "JARVIS-WorldView/1.0",
                        "Accept": "text/plain",
                    })
                    try:
                        with urllib.request.urlopen(req, timeout=15) as r:
                            text = r.read().decode("utf-8", "replace")
                    except Exception:
                        continue  # one group failing is survivable
                    lines = [ln.rstrip() for ln in text.splitlines()
                             if ln.strip()]
                    for i in range(0, len(lines) - 2, 3):
                        name = lines[i].strip()
                        l1, l2 = lines[i + 1], lines[i + 2]
                        if not l1.startswith("1 ") or not l2.startswith("2 "):
                            continue
                        norad = l1[2:7].strip()
                        if norad in seen:
                            continue
                        seen.add(norad)
                        sats.append({"name": name, "l1": l1, "l2": l2,
                                     "grp": grp_tag})
                if not sats:
                    raise RuntimeError("no TLE data from Celestrak")
                payload = json.dumps({"sats": sats[:150],
                                      "fetched": int(now)}).encode("utf-8")
                _tle_cache = {"ts": now, "data": payload}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(payload)
        except Exception as e:
            try:
                if _tle_cache["data"]:
                    # serve stale cache rather than nothing
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._cors_headers()
                    self.end_headers()
                    self.wfile.write(_tle_cache["data"])
                    return
                msg = ('{"error":' + json.dumps(str(e))
                       + ',"sats":[]}').encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(msg)
            except Exception:
                pass

    def _handle_state(self):
        # v4.52: live state for the Achilles screen. Cheap JSON, polled
        # ~every 600ms by the page; last_poll doubles as a "page is open"
        # heartbeat for open_achilles().
        try:
            _achilles_state["last_poll"] = time.time()
            _scene = _achilles_state.get("scene", "core")
            body = json.dumps({
                "state": _achilles_state.get("state", "idle"),
                "scene": _scene,
                "ts": _achilles_state.get("ts", 0.0),
                "srv": time.time(),
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(body)
            # v4.53: "dive" is one-shot - consumed by the first poll that
            # sees it, so reopening the screen later never re-triggers it.
            if _scene == "dive":
                _achilles_state["scene"] = "core"
        except Exception:
            pass

    def _handle_ask(self, parsed):
        # v4.53: typed question from the Achilles screen -> same brain as
        # voice. Replies with text; speaks aloud too when asked from the PC.
        try:
            # v4.67: the proxy binds 0.0.0.0 for phone WorldView access, but
            # /ask runs the full brain (state mutation, web search, API spend).
            # Restrict it to loopback so a LAN host / drive-by web page can't
            # drive it. (The phone uses Telegram for chat instead.)
            _peer = self.client_address[0] if self.client_address else ""
            if _peer not in ("127.0.0.1", "::1", "localhost"):
                self.send_response(403)
                self._cors_headers()
                self.end_headers()
                return
            params = urllib.parse.parse_qs(parsed.query)
            q = (params.get("q", [""])[0] or "").strip()
            if not q:
                raise ValueError("empty question")
            lang = "he" if is_hebrew(q) else "en"
            _achilles_state["state"] = "thinking"
            _achilles_state["ts"] = time.time()
            try:
                mem = APP.memory if (APP is not None and getattr(APP, "memory", "")) \
                      else load_long_term_memory()
            except Exception:
                mem = ""
            try:
                reply = think(q, mem, lang=lang)
            except Exception as e:
                reply = "Brain error: %r" % (e,)
            body = json.dumps({"reply": reply}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(body)
            # speak only when the question came from this PC
            client = self.client_address[0] if self.client_address else ""
            if client in ("127.0.0.1", "::1", "localhost"):
                def _say(txt):
                    _achilles_state["state"] = "speaking"
                    _achilles_state["ts"] = time.time()
                    try:
                        speak(clean_text(txt))
                    except Exception:
                        pass
                    _achilles_state["state"] = "idle"
                    _achilles_state["ts"] = time.time()
                threading.Thread(target=_say, args=(reply,), daemon=True).start()
            else:
                _achilles_state["state"] = "idle"
                _achilles_state["ts"] = time.time()
        except Exception as e:
            try:
                _achilles_state["state"] = "idle"
                msg = ('{"error":' + json.dumps(str(e)) + "}").encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(msg)
            except Exception:
                pass

    def _handle_todo(self, parsed):
        # v4.53: minimal task store shared by voice and the Achilles screen.
        try:
            # v4.67: allow read-only GET /todo from the LAN (phone can view the
            # list) but block the mutating actions from non-loopback origins so
            # a cross-site GET can't add/toggle/delete the user's tasks.
            if parsed.path != "/todo":
                _peer = self.client_address[0] if self.client_address else ""
                if _peer not in ("127.0.0.1", "::1", "localhost"):
                    self.send_response(403)
                    self._cors_headers()
                    self.end_headers()
                    return
            params = urllib.parse.parse_qs(parsed.query)
            with _tasks_lock:
                tasks = _tasks_load()
                if parsed.path == "/todo_add":
                    text = (params.get("text", [""])[0] or "").strip()
                    if text:
                        tasks.append({"id": int(time.time() * 1000),
                                      "text": text, "done": False,
                                      "ts": time.time()})
                        _tasks_save(tasks)
                elif parsed.path == "/todo_toggle":
                    tid = int(params.get("id", ["0"])[0] or "0")
                    for t in tasks:
                        if t.get("id") == tid:
                            t["done"] = not t.get("done", False)
                    _tasks_save(tasks)
                elif parsed.path == "/todo_del":
                    tid = int(params.get("id", ["0"])[0] or "0")
                    tasks = [t for t in tasks if t.get("id") != tid]
                    _tasks_save(tasks)
            body = json.dumps({"tasks": tasks}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            try:
                msg = ('{"error":' + json.dumps(str(e))
                       + ',"tasks":[]}').encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(msg)
            except Exception:
                pass

    def _handle_planet(self, parsed):
        # v4.52: live news for a clicked planet in the Solar System scene.
        # One Claude call with web_search, cached per planet for 1 hour so
        # repeated clicks cost nothing.
        try:
            params = urllib.parse.parse_qs(parsed.query)
            name = (params.get("name", [""])[0] or "").strip().lower()
            lang = (params.get("lang", ["he"])[0] or "he").strip().lower()
            allowed = ("sun", "mercury", "venus", "earth", "moon", "mars",
                       "jupiter", "saturn", "uranus", "neptune")
            if name not in allowed:
                raise ValueError("unknown body: %s" % name)
            now = time.time()
            ck = name + ":" + ("he" if lang == "he" else "en")
            hit = _planet_news_cache.get(ck)
            if hit and (now - hit["ts"] < 3600) and hit["text"]:
                text = hit["text"]
            else:
                if not ANTHROPIC_API_KEY:
                    raise RuntimeError("no API key")
                client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                sys_p = (
                    "You are a space news desk. Use web_search to find the 3 "
                    "most interesting RECENT news items (missions, discoveries, "
                    "research - prefer the last month) about: " + name + ". "
                    "Then output ONLY a compact plain-text list of those 3 "
                    "items, one per line, each one short factual sentence. "
                    "No URLs, no numbering, no markdown. Write in "
                    + ("Hebrew" if lang == "he" else "English") + ".")
                tools = [{"type": "web_search_20250305",
                          "name": "web_search", "max_uses": 2}]
                msgs = [{"role": "user",
                         "content": "Latest news about " + name + ", please."}]
                r = None
                for _ in range(4):
                    r = client.messages.create(
                        model="claude-sonnet-4-6", max_tokens=450,
                        system=sys_p, messages=msgs, tools=tools)
                    msgs.append({"role": "assistant", "content": r.content})
                    if getattr(r, "stop_reason", None) == "tool_use":
                        continue
                    break
                parts = [b.text for b in r.content
                         if getattr(b, "type", None) == "text"]
                text = "\n".join(p.strip() for p in parts if p.strip()).strip()
                text = re.sub(r"https?://\S+", "", text).strip()
                if not text:
                    raise RuntimeError("empty news")
                _planet_news_cache[ck] = {"ts": now, "text": text}
            body = json.dumps({"name": name, "news": text}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            try:
                msg = ('{"error":' + json.dumps(str(e))
                       + ',"news":""}').encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(msg)
            except Exception:
                pass

    # silence per-request access logs
    def log_message(self, *args, **kwargs):
        pass


def _start_flights_proxy(port=7778):
    """Start the FLIGHTS proxy on a daemon thread. Idempotent - safe to call
    every time WorldView is opened. Returns True if the proxy is (now)
    listening, False if the bind failed."""
    global _flights_proxy_started
    with _flights_proxy_lock:
        if _flights_proxy_started:
            return True
        try:
            server = http.server.ThreadingHTTPServer(
                ("0.0.0.0", port), _FlightsProxyHandler
            )
        except OSError as e:
            print("[diag] flights proxy could not bind to %d: %r" % (port, e))
            return False
        th = threading.Thread(
            target=server.serve_forever, daemon=True,
            name="jarvis-flights-proxy",
        )
        th.start()
        _flights_proxy_started = True
        print("[diag] flights proxy listening on 0.0.0.0:%d (LAN)" % port)
        return True


def _ensure_worldview_server(files_dir, port=7777):
    """Ensure a local HTTP server is serving WorldView at 127.0.0.1:port.
    Starts python -m http.server in the background if nothing is listening yet.
    Returns True on success, False on failure."""
    global _worldview_server_proc
    _start_flights_proxy()
    _start_vessels_relay()
    if _wv_port_in_use(port):
        return True
    try:
        creationflags = 0
        if os.name == "nt":
            # CREATE_NO_WINDOW - no console flash on Windows
            creationflags = 0x08000000
        _worldview_server_proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port), "--bind", "0.0.0.0"],
            cwd=str(files_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )
    except Exception as e:
        print("[diag] failed to spawn WorldView server:", repr(e))
        return False
    # Poll up to 3 seconds for the server to come up
    for _ in range(30):
        if _wv_port_in_use(port):
            return True
        time.sleep(0.1)
    print("[diag] WorldView server did not become reachable within 3s")
    return False

def open_worldview():
    """Open the WorldView 3D globe in Edge --app mode, served over a local
    HTTP server on 127.0.0.1:7777. Google Maps JavaScript and Photorealistic
    3D Tiles refuse to load from file:// origins (Chromium treats them as
    unique opaque security origins), so JARVIS spawns a background
    python -m http.server in the files directory the first time the user
    asks to open WorldView, reuses it across subsequent opens in the same
    session, and points Edge at http://localhost:7777/worldview.html.
    Falls back to the default browser if Edge is not at the standard paths.
    Returns a short status string for the brain to phrase naturally."""
    files_dir = Path(__file__).resolve().parent
    path = files_dir / "worldview.html"
    if not path.exists():
        return "WorldView file not found, sir. Expected at: %s" % path
    if not _ensure_worldview_server(files_dir, port=7777):
        return "Failed to start the local WorldView server, sir. Try restarting JARVIS."
    # v4.53: if the Achilles screen is open, dive cinematically through
    # the solar system into Earth instead of spawning a separate window.
    if time.time() - _achilles_state.get("last_poll", 0.0) < 3.0:
        _achilles_state["scene"] = "dive"
        _achilles_state["ts"] = time.time()
        return "Diving to Earth, sir."
    # Cache-buster so Edge always reads the latest build, never a stale page
    url = "http://localhost:7777/worldview.html?t=" + str(int(time.time()))
    edge_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for exe in edge_candidates:
        if os.path.exists(exe):
            try:
                subprocess.Popen(
                    [exe, "--app=" + url],
                    close_fds=True,
                )
                return "Opening WorldView, sir."
            except Exception as e:
                print("[diag] Edge --app launch failed, falling back to default browser:", repr(e))
                break
    try:
        webbrowser.open(url)
        return "Opening WorldView, sir."
    except Exception as e:
        return "Failed to open WorldView: %s" % e

def open_roadmap():
    """Open Mission Control - the project roadmap/status dashboard - in Edge
    --app mode, served by the same local HTTP server as WorldView (port 7777).
    Returns a short status string for the brain to phrase naturally."""
    files_dir = Path(__file__).resolve().parent
    path = files_dir / "roadmap.html"
    if not path.exists():
        return "Roadmap file not found, sir. Expected at: %s" % path
    if not _ensure_worldview_server(files_dir, port=7777):
        return "Failed to start the local server, sir. Try restarting JARVIS."
    url = "http://localhost:7777/roadmap.html?t=" + str(int(time.time()))
    edge_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for exe in edge_candidates:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe, "--app=" + url], close_fds=True)
                return "Opening Mission Control, sir."
            except Exception as e:
                print("[diag] Edge --app launch failed, falling back:", repr(e))
                break
    try:
        webbrowser.open(url)
        return "Opening Mission Control, sir."
    except Exception as e:
        return "Failed to open the roadmap: %s" % e

# --- v4.53: tasks store (tasks.json, shared by voice + Achilles screen) -----
def _tasks_path():
    return Path(__file__).resolve().parent / "tasks.json"

def _tasks_load():
    try:
        with open(_tasks_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def _tasks_save(tasks):
    try:
        with open(_tasks_path(), "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=1)
    except Exception as e:
        print("[diag] tasks.json save failed:", repr(e))

def todo_add_voice(text, lang="he"):
    """Add a task from a voice/typed command and confirm briefly."""
    text = (text or "").strip().strip('.')
    if not text:
        return "מה להוסיף לרשימה, אדוני?" if lang == "he" else "Add what, sir?"
    with _tasks_lock:
        tasks = _tasks_load()
        tasks.append({"id": int(time.time() * 1000), "text": text,
                      "done": False, "ts": time.time()})
        _tasks_save(tasks)
    n = len([t for t in tasks if not t.get("done")])
    if lang == "he":
        return "נוסף: %s. %d משימות פתוחות, אדוני." % (text, n)
    return "Added: %s. %d open tasks, sir." % (text, n)

def open_portal():
    """v4.61: double-click on the floating hole -> FULLSCREEN portal.
    Opens achilles.html with the full UI (ui=full) in a dedicated Edge
    profile so --start-fullscreen is always honored. In the portal:
    Earth button dives into WorldView, Solar System opens the planets.
    Exit fullscreen with F11; close with Alt+F4."""
    files_dir = Path(__file__).resolve().parent
    try:
        _ensure_worldview_server(files_dir, port=7777)
    except Exception:
        pass
    url = ("http://localhost:7777/achilles.html?scene=core&ui=full&t="
           + str(int(time.time())))
    prof = str(files_dir / ".portal_profile")
    args = ["--user-data-dir=" + prof, "--no-first-run",
            "--no-default-browser-check", "--start-fullscreen",
            "--app=" + url]
    for exe in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if os.path.isfile(exe):
            try:
                subprocess.Popen([exe] + args)
                return
            except Exception:
                pass
    try:
        os.startfile(url)
    except Exception:
        pass


def open_achilles(scene="core", face=False):
    """v4.52: Open the Achilles Core screen (achilles.html) - the WebGL
    black hole + solar system - in Edge --app mode on the same local server
    as WorldView (:7777). If the page is ALREADY open (it heartbeats /state
    every ~600ms), just flip the scene instead of spawning a second window.
    Returns a short status string for the brain to phrase naturally."""
    scene = scene if scene in ("core", "solar", "todo") else "core"
    files_dir = Path(__file__).resolve().parent
    path = files_dir / "achilles.html"
    if not path.exists():
        return "The Achilles screen file is missing, sir. Expected at: %s" % path
    if not _ensure_worldview_server(files_dir, port=7777):
        return "Failed to start the local server, sir. Try restarting me."
    # already-open page? (heartbeat within the last 3 seconds)
    _achilles_state["scene"] = scene
    _achilles_state["ts"] = time.time()
    if time.time() - _achilles_state.get("last_poll", 0.0) < 3.0:
        return {"solar": "Switching to the solar system, sir.",
                "todo": "Bringing up your task list, sir.",
                "core": "Bringing up the core, sir."}[scene]
    url = ("http://localhost:7777/achilles.html?scene=" + scene
           + "&t=" + str(int(time.time())))
    # v4.56: face mode = a SMALL widget window (like the old orb).
    # Edge ignores --window-size when the main browser is already running,
    # so the face gets its OWN profile (= its own process) which always
    # respects size and position. 420x500 at the orb's old spot.
    args_extra = []
    if face:
        try:
            import ctypes
            _sw = ctypes.windll.user32.GetSystemMetrics(0)
        except Exception:
            _sw = 1920
        _prof = str(files_dir / ".face_profile")
        args_extra = ["--user-data-dir=" + _prof,
                      "--no-first-run", "--no-default-browser-check",
                      "--window-size=420,500",
                      "--window-position=%d,60" % max(0, _sw - 450)]
    edge_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for exe in edge_candidates:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe, "--app=" + url] + args_extra,
                                 close_fds=True)
                return {"solar": "Opening the solar system, sir.",
                        "todo": "Opening your task list, sir.",
                        "core": "Opening the core, sir."}[scene]
            except Exception as e:
                print("[diag] Edge --app launch failed, falling back:", repr(e))
                break
    try:
        webbrowser.open(url)
        return {"solar": "Opening the solar system, sir.",
                "todo": "Opening your task list, sir.",
                "core": "Opening the core, sir."}[scene]
    except Exception as e:
        return "Failed to open the Achilles screen: %s" % e

# --- Google Places + Directions ---------------------------------------------
def _gmaps_get(url, params, timeout=12):
    """GET against a Google Maps endpoint and parse the JSON. Returns
    (data_dict, error_string). Never throws."""
    if not GOOGLE_MAPS_API_KEY:
        return None, "Google Maps API key missing from .env (GOOGLE_MAPS_API_KEY)."
    params = dict(params)
    params["key"] = GOOGLE_MAPS_API_KEY
    full = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(full, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return None, f"Network error contacting Google Maps: {e}"
    except Exception as e:
        return None, f"Unexpected error: {e}"
    status = data.get("status", "")
    if status not in ("OK", "ZERO_RESULTS"):
        return None, f"Google Maps returned status {status}: {data.get('error_message','')}"
    return data, None

def find_places(query, max_results=5):
    """Search Google Places (Text Search) for restaurants/cafes/shops/etc.
    Biased to Israel (Alfei Menashe area). Returns a short summary string the
    brain can read aloud, listing name, rating, status and address."""
    if not query or not query.strip():
        return "Please tell me what kind of place you're looking for, sir."
    # Bias the search to Alfei Menashe (~50 km covers most of central Israel
    # including Tel Aviv, Petah Tikva, Kfar Saba, etc.). Hebrew queries work too.
    params = {
        "query": query.strip(),
        "location": "32.1772,34.9947",   # Alfei Menashe approx
        "radius": "50000",
        "region": "il",
        "language": "iw",                # results in Hebrew where available
    }
    data, err = _gmaps_get(
        "https://maps.googleapis.com/maps/api/place/textsearch/json", params)
    if err:
        return f"Place search failed: {err}"
    results = data.get("results") or []
    if not results:
        return f"No places found in Israel matching '{query}'."
    out = []
    for p in results[:max_results]:
        name = p.get("name", "?")
        addr = p.get("formatted_address", "")
        rating = p.get("rating")
        ratings_n = p.get("user_ratings_total")
        oh = p.get("opening_hours", {})
        open_now = oh.get("open_now")
        bits = [name]
        if rating is not None:
            bits.append(f"{rating}/5"
                        + (f" ({ratings_n} reviews)" if ratings_n else ""))
        if open_now is True:
            bits.append("open now")
        elif open_now is False:
            bits.append("closed now")
        if addr:
            bits.append(addr)
        out.append(" — ".join(bits))
    return "Top results:\n- " + "\n- ".join(out)

def get_directions(destination, origin=None):
    """Get driving directions + live travel time from origin to destination
    using Google Directions. Defaults the origin to home (Alfei Menashe).
    Returns a short readable summary string."""
    if not destination or not destination.strip():
        return "Where would you like to go, sir?"
    origin = (origin or HOME_ADDRESS).strip()
    params = {
        "origin": origin,
        "destination": destination.strip(),
        "mode": "driving",
        "departure_time": "now",      # gives duration_in_traffic
        "traffic_model": "best_guess",
        "region": "il",
        "language": "iw",
    }
    data, err = _gmaps_get(
        "https://maps.googleapis.com/maps/api/directions/json", params)
    if err:
        return f"Directions failed: {err}"
    routes = data.get("routes") or []
    if not routes:
        return f"No driving route found from {origin} to {destination}."
    leg = routes[0]["legs"][0]
    dist = leg.get("distance", {}).get("text", "?")
    dur = leg.get("duration", {}).get("text", "?")
    dur_traffic = leg.get("duration_in_traffic", {}).get("text")
    start_addr = leg.get("start_address", origin)
    end_addr = leg.get("end_address", destination)
    summary = (routes[0].get("summary") or "").strip()
    line = f"From {start_addr} to {end_addr}: {dist}, normally {dur}"
    if dur_traffic:
        line += f", with current traffic about {dur_traffic}"
    if summary:
        line += f". Route via {summary}."
    else:
        line += "."
    return line

# --- Google Calendar ---------------------------------------------------------
def _calendar_service():
    """Return an authorized Calendar service, or None if not connected.
    Handles the OAuth dance: uses token.json if present, refreshes it if expired,
    or runs the one-time browser sign-in using credentials.json."""
    if not HAVE_GCAL:
        print("Calendar: Google libraries not installed.")
        return None
    if not os.path.exists(CAL_CREDENTIALS_FILE):
        print("Calendar: credentials.json not found in folder.")
        return None
    creds = None
    try:
        if os.path.exists(CAL_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(CAL_TOKEN_FILE, CAL_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CAL_CREDENTIALS_FILE, CAL_SCOPES)
                creds = flow.run_local_server(port=0)
            with open(CAL_TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        print("Calendar auth error:", e)
        return None

def calendar_read(time_min=None, time_max=None, max_results=10):
    """List upcoming events. Defaults to the next 7 days if no range given."""
    svc = _calendar_service()
    if svc is None:
        return ("Calendar not connected. Add credentials.json and install the "
                "Google libraries to enable it, sir.")
    try:
        # Google's API needs RFC3339 times WITH a timezone. The brain sometimes
        # sends a naive time like "2026-05-26T00:00:00" (no Z, no offset), which
        # Google rejects as a 400 Bad Request. So we attach the machine's local
        # (Israel) offset to any naive time before sending it.
        now = datetime.datetime.now(datetime.timezone.utc)
        local_tz = datetime.datetime.now().astimezone().tzinfo  # DST-aware local offset

        def _tz(s):
            if not s:
                return None
            s = s.strip()
            if s.endswith("Z") or re.search(r'[+\-]\d{2}:?\d{2}$', s):
                return s  # already has a timezone -> leave it as-is
            try:
                d = datetime.datetime.fromisoformat(s)
                if d.tzinfo is None:
                    d = d.replace(tzinfo=local_tz)
                return d.isoformat()
            except Exception:
                return s

        tmin = _tz(time_min) or now.isoformat()
        tmax = _tz(time_max) or (now + datetime.timedelta(days=7)).isoformat()
        res = svc.events().list(calendarId="primary", timeMin=tmin, timeMax=tmax,
                                singleEvents=True, orderBy="startTime",
                                maxResults=max_results).execute()
        items = res.get("items", [])
        if not items:
            return "No events found in that period."
        lines = []
        for e in items:
            s = e["start"].get("dateTime", e["start"].get("date", ""))
            eid = e.get("id", "")
            lines.append(f"[id={eid}] {s}: {e.get('summary', '(no title)')}")
        return "Events:\n" + "\n".join(lines)
    except Exception as e:
        # Print the REAL reason to the console so we can actually see it.
        print("Calendar read error:", repr(e))
        return f"Failed to read calendar: {e}"

def calendar_add(summary, start_iso, end_iso=None, location=None, description=None):
    """Create an event. start_iso/end_iso are ISO datetimes like
    2026-05-26T16:00:00. If end is omitted, the event lasts one hour."""
    svc = _calendar_service()
    if svc is None:
        return "Calendar not connected, sir."
    if not summary or not start_iso:
        return "I need at least a title and a start time."
    try:
        if not end_iso:
            st = datetime.datetime.fromisoformat(start_iso)
            end_iso = (st + datetime.timedelta(hours=1)).isoformat()
        body = {
            "summary": summary,
            "start": {"dateTime": start_iso, "timeZone": CAL_TIMEZONE},
            "end": {"dateTime": end_iso, "timeZone": CAL_TIMEZONE},
        }
        if location:
            body["location"] = location
        if description:
            body["description"] = description
        ev = svc.events().insert(calendarId="primary", body=body).execute()
        _record_action("calendar_add",
                       {"event_id": ev.get("id", ""), "summary": summary})
        return f"Event '{summary}' added for {start_iso}."
    except Exception as e:
        print("Calendar add error:", repr(e))
        return f"Failed to add event: {e}"

def calendar_delete(event_id):
    """Delete an event by its Google Calendar event id. Returns a status string."""
    svc = _calendar_service()
    if svc is None:
        return "Calendar not connected, sir."
    if not event_id:
        return "I need the event id to delete, sir."
    try:
        # v4.29: cache the event body before deletion so undo can re-insert it
        cached_body = None
        try:
            ev = svc.events().get(calendarId="primary",
                                  eventId=event_id).execute()
            cached_body = {k: v for k, v in ev.items()
                           if k in ("summary", "description", "location",
                                    "start", "end", "attendees",
                                    "reminders", "colorId")}
        except Exception:
            cached_body = None
        svc.events().delete(calendarId="primary", eventId=event_id).execute()
        if cached_body:
            _record_action("calendar_delete", {"body": cached_body})
        return "Event deleted, sir."
    except Exception as e:
        print("Calendar delete error:", repr(e))
        return f"Failed to delete event: {e}"

def calendar_update(event_id, summary=None, start_iso=None, end_iso=None,
                    location=None, description=None):
    """Patch an existing event. Only the fields explicitly provided are changed;
    everything else stays as it is. Times are ISO datetimes."""
    svc = _calendar_service()
    if svc is None:
        return "Calendar not connected, sir."
    if not event_id:
        return "I need the event id to update, sir."
    body = {}
    if summary:
        body["summary"] = summary
    if start_iso:
        body["start"] = {"dateTime": start_iso, "timeZone": CAL_TIMEZONE}
    if end_iso:
        body["end"] = {"dateTime": end_iso, "timeZone": CAL_TIMEZONE}
    if location is not None:
        body["location"] = location
    if description is not None:
        body["description"] = description
    if not body:
        return "Nothing to change, sir."
    try:
        svc.events().patch(calendarId="primary", eventId=event_id,
                           body=body).execute()
        return "Event updated, sir."
    except Exception as e:
        print("Calendar update error:", repr(e))
        return f"Failed to update event: {e}"

# --- Gmail -------------------------------------------------------------------
def _gmail_service():
    """Return an authorized Gmail service, or None if not connected. Uses the
    SAME token.json/credentials.json as the calendar (shared Google login)."""
    if not HAVE_GCAL:
        print("Gmail: Google libraries not installed.")
        return None
    if not os.path.exists(CAL_CREDENTIALS_FILE):
        print("Gmail: credentials.json not found in folder.")
        return None
    creds = None
    try:
        if os.path.exists(CAL_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(CAL_TOKEN_FILE, GOOGLE_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CAL_CREDENTIALS_FILE, GOOGLE_SCOPES)
                creds = flow.run_local_server(port=0)
            with open(CAL_TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        return build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception as e:
        print("Gmail auth error:", repr(e))
        return None

def _gmail_header(msg, name):
    """Pull a header value (e.g. 'From', 'Subject') from a Gmail message."""
    for h in msg.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""

def _looks_like_spam(subject, sender, snippet):
    """Aggressive (v3.8): flags promotions/newsletters too. Anything carrying an
    unsubscribe marker counts, plus the older strong-junk signals. JARVIS still
    ASKS the user before moving/blocking anything, so this only decides what to
    PROPOSE."""
    blob = (subject + " " + sender + " " + snippet).lower()
    # Newsletters/promotions almost always include an unsubscribe line.
    if "unsubscribe" in blob:
        return True
    hits = sum(1 for w in GMAIL_SPAM_HINTS if w in blob)
    if hits >= 2:
        return True
    if any(w in blob for w in ("sale", "% off", "discount", "deal", "promo",
                               "newsletter", "offer")):
        return True
    return False

def _email_address_only(sender):
    """Extract just the address from a From header like 'Name <a@b.com>'."""
    m = re.search(r'<([^>]+)>', sender or "")
    if m:
        return m.group(1).strip().lower()
    return (sender or "").strip().lower()

def gmail_read(max_results=12):
    """Read recent inbox emails and return a compact list the model can
    summarise out loud: sender, subject, and a short snippet for each."""
    svc = _gmail_service()
    if svc is None:
        return "Gmail not connected, sir."
    try:
        res = svc.users().messages().list(
            userId="me", labelIds=["INBOX"], maxResults=max_results).execute()
        ids = [m["id"] for m in res.get("messages", [])]
        if not ids:
            return "Your inbox is empty, sir."
        lines = []
        for mid in ids:
            msg = svc.users().messages().get(
                userId="me", id=mid, format="metadata",
                metadataHeaders=["From", "Subject"]).execute()
            sender = _gmail_header(msg, "From")
            subject = _gmail_header(msg, "Subject") or "(no subject)"
            snippet = (msg.get("snippet", "") or "")[:120]
            lines.append(f"From {sender} | {subject} | {snippet}")
        return ("Here are the latest %d emails. Summarise them briefly for the "
                "user by voice (who, about what, anything urgent):\n" % len(lines)
                + "\n".join(lines))
    except Exception as e:
        print("Gmail read error:", repr(e))
        return f"Failed to read email: {e}"

def gmail_spam_review(max_results=25):
    """Scan recent inbox mail, flag likely spam, and STAGE it (does NOT move
    anything). Returns a list for JARVIS to read out and ask for confirmation.
    The actual move happens only in gmail_move_spam after the user says yes."""
    global _gmail_pending_spam
    svc = _gmail_service()
    if svc is None:
        return "Gmail not connected, sir."
    try:
        res = svc.users().messages().list(
            userId="me", labelIds=["INBOX"], maxResults=max_results).execute()
        ids = [m["id"] for m in res.get("messages", [])]
        flagged = []
        for mid in ids:
            msg = svc.users().messages().get(
                userId="me", id=mid, format="metadata",
                metadataHeaders=["From", "Subject"]).execute()
            sender = _gmail_header(msg, "From")
            subject = _gmail_header(msg, "Subject") or "(no subject)"
            snippet = msg.get("snippet", "") or ""
            if _looks_like_spam(subject, sender, snippet):
                flagged.append({"id": mid, "from": sender,
                                "addr": _email_address_only(sender),
                                "subject": subject})
        _gmail_pending_spam = flagged
        if not flagged:
            return "I found no obvious spam in your recent inbox, sir."
        listing = "\n".join(f"- {f['subject']} (from {f['from']})" for f in flagged)
        return ("I found %d likely spam/promotional emails. Read the list to the "
                "user and ASK whether to move them to JARVIS_Spam AND block those "
                "senders for the future. Do NOT do anything yet; wait for a clear "
                "yes. List:\n%s" % (len(flagged), listing))
    except Exception as e:
        print("Gmail spam review error:", repr(e))
        return f"Failed to review spam: {e}"

def _gmail_get_or_make_label(svc, name):
    """Find the label id by name, creating the label if it doesn't exist."""
    res = svc.users().labels().list(userId="me").execute()
    for lab in res.get("labels", []):
        if lab.get("name") == name:
            return lab["id"]
    created = svc.users().labels().create(
        userId="me", body={"name": name,
                            "labelListVisibility": "labelShow",
                            "messageListVisibility": "show"}).execute()
    return created["id"]

def gmail_move_spam():
    """Move the emails staged by gmail_spam_review into the JARVIS_Spam label
    and out of the inbox. Call this ONLY after the user confirmed out loud.
    Never deletes — the mail stays under the label and is fully recoverable."""
    global _gmail_pending_spam
    svc = _gmail_service()
    if svc is None:
        return "Gmail not connected, sir."
    if not _gmail_pending_spam:
        return "There's nothing staged to move, sir. Ask me to review spam first."
    try:
        label_id = _gmail_get_or_make_label(svc, GMAIL_SPAM_LABEL)
        moved = 0
        blocked_addrs = set()
        for f in _gmail_pending_spam:
            svc.users().messages().modify(
                userId="me", id=f["id"],
                body={"addLabelIds": [label_id], "removeLabelIds": ["INBOX"]}).execute()
            moved += 1
            # Block the sender for the future: a filter that sends mail from this
            # address straight to Trash. Skipped if we couldn't parse an address,
            # or if we already made a filter for it in this batch.
            addr = f.get("addr") or ""
            if addr and "@" in addr and addr not in blocked_addrs:
                try:
                    svc.users().settings().filters().create(
                        userId="me",
                        body={"criteria": {"from": addr},
                              "action": {"addLabelIds": ["TRASH"],
                                         "removeLabelIds": ["INBOX"]}}).execute()
                    blocked_addrs.add(addr)
                except Exception as fe:
                    print("Gmail block-sender warning for", addr, ":", repr(fe))
        _gmail_pending_spam = []
        return (f"Done, sir. Moved {moved} emails to {GMAIL_SPAM_LABEL} and blocked "
                f"{len(blocked_addrs)} senders for the future. Nothing was deleted; "
                "everything is recoverable.")
    except Exception as e:
        print("Gmail move spam error:", repr(e))
        return f"Failed to move spam: {e}"

# Tool schemas described to Claude. The 'description' fields are what Claude
# reads to decide WHEN to use each tool, so they're written for the model.
LOCAL_TOOLS = [
    {
        "name": "open_app",
        "description": ("Open an application or website on the user's Windows PC. "
                        "Use when the user asks to open, launch, or go to something. "
                        "Allowed names: " + ", ".join(ALLOWED_APPS.keys()) + "."),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string",
                         "description": "Which allowed app/site to open."}
            },
            "required": ["name"],
        },
    },
    {
        "name": "save_note",
        "description": ("Save a short note to the user's Obsidian vault. Use when "
                        "the user asks to write down, note, remember, or jot something. "
                        "Pass the note content as plain text."),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string",
                         "description": "The note content to save."}
            },
            "required": ["text"],
        },
    },
    {
        "name": "learn_topic",
        "description": ("Research a subject in depth and save a structured "
                        "study note to the user's Obsidian Knowledge folder. "
                        "Use ONLY when the user explicitly asks JARVIS to "
                        "learn, study, research, or build knowledge about "
                        "a topic - e.g. \"JARVIS, learn aerodynamics\", "
                        "\"tilmad fizika shel rachfanim\", \"research X "
                        "for me\", \"build me knowledge on Y\". The note "
                        "persists across sessions; running this again on the "
                        "same topic appends a deepening section. Optionally "
                        "include a context string (e.g. the project the "
                        "topic relates to) so the note is tailored."),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string",
                          "description": "The subject to study (e.g. 'aerodynamics of quadcopters', 'Bernoulli principle')."},
                "context": {"type": "string",
                            "description": "Optional project or use-case context to tailor the note. Pass empty string if none."},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "deep_learn_domain",
        "description": ("Study an ENTIRE field/domain in depth over time. "
                        "Use when the user asks to deeply learn or master a "
                        "whole subject - e.g. \"deep-learn chemistry\", "
                        "\"learn all of physics in depth\", \"tilmad kol "
                        "ha-chimya la'omek\", \"study biology thoroughly\". "
                        "JARVIS builds a sub-topic curriculum and learns it in "
                        "the background, one deep note at a time, capped per "
                        "run for cost. Pass the field name as domain. "
                        "Optionally pass max_notes to set how many sub-topics "
                        "to learn this run (default 15)."),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string",
                           "description": "The field to study deeply (e.g. 'chemistry', 'physics', 'materials science')."},
                "max_notes": {"type": "integer",
                              "description": "Optional cap on sub-topics to learn this run (default 15, max 60)."},
            },
            "required": ["domain"],
        },
    },
    {
        "name": "resume_learning",
        "description": ("Continue learning the remaining sub-topics of a "
                        "domain that was already planned with deep_learn_domain. "
                        "Use when the user says \"continue learning X\", "
                        "\"keep studying X\", \"tamshich lilmod X\"."),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "The field to continue."},
                "max_notes": {"type": "integer",
                              "description": "Optional cap for this batch (default 15, max 60)."},
            },
            "required": ["domain"],
        },
    },
    {
        "name": "learning_status",
        "description": ("Report how the background deep-learning is going. "
                        "Use when the user asks \"how's the learning going\", "
                        "\"learning status\", \"what have you learned\", "
                        "\"ma im ha-lemida\"."),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "calendar_read",
        "description": ("Read the user's Google Calendar. Use when asked what's on "
                        "their schedule, what they have today/this week, or about "
                        "upcoming events. Optionally pass an ISO time range; "
                        "defaults to the next 7 days."),
        "input_schema": {
            "type": "object",
            "properties": {
                "time_min": {"type": "string", "description": "ISO start, e.g. 2026-05-25T00:00:00Z (optional)."},
                "time_max": {"type": "string", "description": "ISO end (optional)."},
            },
        },
    },
    {
        "name": "calendar_add",
        "description": ("Add an event to the user's Google Calendar. Use when they "
                        "ask to schedule, book, or add something. Compute ISO "
                        "datetimes from the current local time given in the system "
                        "prompt. Local timezone is Israel."),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Event title."},
                "start_iso": {"type": "string", "description": "Start, ISO e.g. 2026-05-26T16:00:00."},
                "end_iso": {"type": "string", "description": "End, ISO (optional; defaults to +1 hour)."},
                "location": {"type": "string", "description": "Location (optional)."},
            },
            "required": ["summary", "start_iso"],
        },
    },
    {
        "name": "calendar_delete",
        "description": ("Delete an event from the user's Google Calendar. "
                        "First call calendar_read to find the event and read "
                        "its id from the [id=...] prefix. If several events "
                        "match the user's description, list them and ASK which "
                        "one before deleting. If exactly one matches, proceed "
                        "since the user already asked. Never delete the wrong "
                        "event silently."),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string",
                             "description": "The Google Calendar event id from calendar_read."},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "calendar_update",
        "description": ("Modify an existing Google Calendar event (change "
                        "title, start/end time, or location). First call "
                        "calendar_read to find the event id. Pass ONLY the "
                        "fields you want to change; leave the rest out. Times "
                        "are ISO datetimes computed from the current local "
                        "time in the system prompt."),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Event id from calendar_read."},
                "summary": {"type": "string", "description": "New title (optional)."},
                "start_iso": {"type": "string", "description": "New start ISO time (optional)."},
                "end_iso": {"type": "string", "description": "New end ISO time (optional)."},
                "location": {"type": "string", "description": "New location (optional)."},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "gmail_read",
        "description": ("Read the user's most recent emails and summarise them. "
                        "Use when asked to check email, read mail, or what's in "
                        "the inbox. Returns sender/subject/snippet for each; you "
                        "then give a short spoken summary."),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "gmail_spam_review",
        "description": ("Scan recent inbox mail for likely spam and return the "
                        "flagged list. Use when asked to find/clean spam or junk. "
                        "This does NOT move anything — read the list to the user "
                        "and ask whether to move them. Only call gmail_move_spam "
                        "after the user clearly confirms."),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "gmail_move_spam",
        "description": ("Move the previously reviewed spam emails to the "
                        "JARVIS_Spam label (out of the inbox) AND block each "
                        "sender for the future. Call this ONLY after the user "
                        "has explicitly confirmed. Never call it without a clear "
                        "yes. Nothing is deleted; blocking is reversible."),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "find_places",
        "description": ("Search Google Places for restaurants, cafes, shops, "
                        "businesses, attractions etc. in Israel. Use whenever "
                        "the user asks WHERE to eat/drink/buy/visit something "
                        "(e.g. 'find me a good sushi place in Tel Aviv', "
                        "'מסעדות איטלקיות בכפר סבא', 'cafes near Rothschild'). "
                        "Returns up to 5 results with name, rating, open/closed "
                        "status, and address. Then summarise them out loud and "
                        "ask if the user wants directions to one."),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "What to search for, e.g. 'pizza Petah Tikva' or 'cafes Tel Aviv'. Hebrew is fine."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_directions",
        "description": ("Get the driving travel time from the user's home "
                        "(Alfei Menashe) to a destination, with current live "
                        "traffic. Use when the user asks 'how long to drive "
                        "to X', 'כמה זמן ייקח להגיע ל-X', 'איך מגיעים ל-X', "
                        "or wants ETA to a place — including a place returned "
                        "by find_places. Returns a single-line summary with "
                        "distance, normal duration, and duration with traffic."),
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string",
                                "description": "Address or place name, e.g. 'Azrieli Tower Tel Aviv' or 'דיזנגוף סנטר'."},
                "origin": {"type": "string",
                           "description": "Optional starting address. Defaults to the user's home in Alfei Menashe."},
            },
            "required": ["destination"],
        },
    },
    {
        "name": "set_timer",
        "description": ("Start a countdown timer or reminder. Use when the user "
                        "asks to set a timer, remind them in N minutes, or alert "
                        "them after some time (e.g. 'set a timer for 5 minutes', "
                        "'\u05ea\u05d6\u05db\u05d9\u05e8 \u05dc\u05d9 \u05d1\u05e2\u05d5\u05d3 10 \u05d3\u05e7\u05d5\u05ea', "
                        "'timer for the pasta 8 minutes'). When it elapses JARVIS "
                        "announces it by voice. For an absolute time like '4 PM', "
                        "compute minutes from the current local time in the system "
                        "prompt."),
        "input_schema": {
            "type": "object",
            "properties": {
                "minutes": {"type": "number",
                            "description": "Minutes from now until the timer fires. May be fractional."},
                "label": {"type": "string",
                          "description": "Optional short label, e.g. 'pasta' or 'workout'."},
            },
            "required": ["minutes"],
        },
    },
    {
        "name": "spotify_play",
        "description": ("Play music on Spotify. Use when the user asks to "
                        "play / listen to / put on a song, artist, album, "
                        "or playlist, or to resume music. Pass `query` for "
                        "a specific request (e.g. 'Bohemian Rhapsody', "
                        "'Imagine Dragons', '\u05d4\u05d1\u05d9\u05d8\u05dc\u05e1'). Omit `query` "
                        "to resume current playback. Requires Spotify "
                        "Premium and Spotify open on some device."),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "Song / artist / album / playlist. Omit to resume."},
            },
        },
    },
    {
        "name": "spotify_pause",
        "description": "Pause Spotify playback.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "spotify_next",
        "description": "Skip to the next track on Spotify.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "spotify_previous",
        "description": "Go back to the previous track on Spotify.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "spotify_volume",
        "description": "Set Spotify playback volume. Pass `level` 0-100.",
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {"type": "number", "description": "Volume percent 0-100."},
            },
            "required": ["level"],
        },
    },
    {
        "name": "spotify_now_playing",
        "description": "Ask Spotify what is currently playing.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "open_roadmap",
        "description": ("Open Mission Control - the JARVIS project roadmap / "
                        "status dashboard page in the browser. Use when the "
                        "user asks for the roadmap, the project status board, "
                        "mission control, what's left to build, or the "
                        "checklist page. Hebrew triggers include "
                        "'\u05e4\u05ea\u05d7 \u05d0\u05ea \u05d4-roadmap', "
                        "'\u05de\u05e4\u05ea \u05d3\u05e8\u05db\u05d9\u05dd', "
                        "'\u05ea\u05e4\u05ea\u05d7 \u05d0\u05ea \u05dc\u05d5\u05d7 "
                        "\u05d4\u05de\u05e9\u05d9\u05de\u05d5\u05ea'."),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "open_search_panel",
        "description": ("Open the big search window. Use when the user wants to "
                        "find/look up a product or asks to open the search "
                        "window, or wants to show JARVIS an image (e.g. 'find me "
                        "this chair', 'open the search window', 'I want to upload "
                        "a picture'). The window lets them type, speak, or pick "
                        "an image, and shows clickable result links."),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "open_worldview",
        "description": ("Open WorldView, the 3D globe in the user's browser. "
                        "Use when the user asks to open WorldView, open the "
                        "globe, show the world or the Earth, or asks about "
                        "live earthquakes / seismic activity worldwide. The "
                        "globe shows live USGS earthquake data on a rotating "
                        "Earth in a separate browser tab. Hebrew triggers "
                        "include 'פתח את WorldView', 'תפתח את הגלובוס', "
                        "'תראה לי רעידות אדמה'."),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "open_achilles",
        "description": ("Open the Achilles Core screen - an ultra-realistic "
                        "WebGL black hole that serves as the assistant's "
                        "visual face, with a Solar System mode (clickable "
                        "planets with facts and live news). Use when the user "
                        "asks for the black hole, the Achilles screen or "
                        "window, or the solar system / the planets. Hebrew "
                        "triggers include 'פתח את החור השחור', 'תפתח את "
                        "אכילס', 'מערכת השמש', 'תראה לי את הכוכבים'. Pass "
                        "scene='solar' when they ask for the solar system or "
                        "planets, scene='todo' when they ask for the to-do "
                        "list / task list / 'המשימות שלי', otherwise "
                        "scene='core'."),
        "input_schema": {"type": "object", "properties": {
            "scene": {"type": "string", "enum": ["core", "solar", "todo"],
                      "description": "core = black hole, solar = solar system, todo = task list"}
        }},
    },
]

def run_local_tool(name, tool_input):
    """Dispatch a tool call from Claude to the matching Python function."""
    if name == "open_app":
        return open_app(tool_input.get("name", ""))
    if name == "save_note":
        return save_note(tool_input.get("text", ""))
    if name == "calendar_read":
        return calendar_read(tool_input.get("time_min"), tool_input.get("time_max"))
    if name == "calendar_add":
        return calendar_add(tool_input.get("summary", ""),
                            tool_input.get("start_iso", ""),
                            tool_input.get("end_iso"),
                            tool_input.get("location"))
    if name == "calendar_delete":
        return calendar_delete(tool_input.get("event_id", ""))
    if name == "calendar_update":
        return calendar_update(tool_input.get("event_id", ""),
                               tool_input.get("summary"),
                               tool_input.get("start_iso"),
                               tool_input.get("end_iso"),
                               tool_input.get("location"))
    if name == "gmail_read":
        return gmail_read()
    if name == "gmail_spam_review":
        return gmail_spam_review()
    if name == "gmail_move_spam":
        return gmail_move_spam()
    if name == "find_places":
        return find_places(tool_input.get("query", ""))
    if name == "get_directions":
        return get_directions(tool_input.get("destination", ""),
                              tool_input.get("origin"))
    if name == "set_timer":
        return set_timer(tool_input.get("minutes"), tool_input.get("label"))
    if name == "spotify_play":
        return spotify_play(tool_input.get("query"))
    if name == "spotify_pause":
        return spotify_pause()
    if name == "spotify_next":
        return spotify_next()
    if name == "spotify_previous":
        return spotify_previous()
    if name == "spotify_volume":
        return spotify_volume(tool_input.get("level"))
    if name == "spotify_now_playing":
        return spotify_now_playing()
    if name == "deep_learn_domain":
        return deep_learn_domain(
            tool_input.get("domain", ""),
            tool_input.get("max_notes"),
        )
    if name == "resume_learning":
        return resume_learning(
            tool_input.get("domain", ""),
            tool_input.get("max_notes"),
        )
    if name == "learning_status":
        return learning_status()
    if name == "learn_topic":
        return learn_topic(
            tool_input.get("topic", ""),
            tool_input.get("context", ""),
        )
    if name == "open_worldview":
        return open_worldview()
    if name == "open_achilles":
        return open_achilles(tool_input.get("scene", "core"))
    if name == "open_roadmap":
        return open_roadmap()
    if name == "open_search_panel":
        if APP is not None:
            APP.ui(APP.open_panel)
            return "Opening the search window, sir."
        return "The search window isn't available right now."
    return f"Unknown tool: {name}"

def _learning_intercept(user_message: str):
    """Detect clear learning commands and return a (topic, depth) tuple, or
    None if the message is not a learning command. depth in {'deep', 'narrow'}."""
    if not user_message or not isinstance(user_message, str):
        return None
    import re
    text = user_message.strip()
    # Strip leading "JARVIS," / "Hey JARVIS," variants
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*", "", text, flags=re.I)
    text = re.sub(r"^\s*(היי\s+|אוקיי\s+|אוקי\s+)?(ג'?א?ר?ו+יס|gארוויס)[\s,:]*", "", text)
    if not text:
        return None
    low = text.lower()

    # --- LEARNING_STATUS shortcuts ---
    if any(p in low for p in ["learning status", "how's the learning",
                              "how is the learning", "what have you learned"]):
        return ("__STATUS__", None)
    if any(p in text for p in ["מה עם הלמידה", "סטטוס למידה", "איך הלמידה",
                               "מה למדת"]):
        return ("__STATUS__", None)

    # --- RESUME ---
    m = re.match(r"(?:continue|resume|keep)\s+(?:studying|learning)\s+(.+)$", low)
    if m:
        return ("__RESUME__:" + m.group(1).strip(), None)
    m = re.match(r"^\s*תמשיך\s+(?:ללמוד|לחקור)\s+(?:את\s+)?(.+)$", text)
    if m:
        return ("__RESUME__:" + m.group(1).strip(), None)

    # --- LEARN commands ---
    # English: "deep-learn X" / "deep learn X" / "learn X" / "study X" / "research X" / "master X"
    # Capture both the verb (to detect depth) and the topic.
    en = re.match(
        r"^\s*(deep[\s-]?learn|learn(?:\s+all\s+of)?|study(?:\s+all\s+of)?|research|master|build\s+knowledge\s+(?:of|about|on))\s+(.+?)\s*[.!?]?\s*$",
        low)
    if en:
        verb = en.group(1)
        # Topic from the original casing for the file/folder name
        topic = text[text.lower().find(en.group(2)):].strip(" .!?,")
        is_deep = ("deep" in verb) or ("all of" in verb)
        return (topic, "deep" if is_deep else "narrow")

    # Hebrew: "תלמד לעומק X" / "תלמד את X לעומק" / "תלמד את כל X" / "תלמד X" /
    #        "ללמוד X" / "תחקור X" / "תבנה ידע על X"
    # Detect the "lao'omek" / "kol ha-" depth markers.
    he_verb = r"(?:תלמד|למד|ללמוד|תחקור|לחקור|תבנה\s+(?:לי\s+)?ידע(?:\s+על)?)"
    he = re.match(r"^\s*" + he_verb + r"\s+(.+)$", text)
    if he:
        rest = he.group(1).strip()
        is_deep = ("לעומק" in rest) or ("כל ה" in rest) or ("את כל" in rest)
        # Clean topic: strip leading "את ", trailing "לעומק", leading "את כל ה"
        topic = rest
        topic = re.sub(r"\bלעומק\b", "", topic).strip()
        topic = re.sub(r"^את\s+כל\s+ה", "", topic).strip()
        topic = re.sub(r"^את\s+ה", "", topic).strip()
        topic = re.sub(r"^את\s+", "", topic).strip()
        topic = re.sub(r"^כל\s+ה", "", topic).strip()
        topic = topic.strip(" .!?,:")
        if topic:
            return (topic, "deep" if is_deep else "narrow")

    return None

def _whats_new_intercept(msg):
    """True if the user is asking what changed recently in JARVIS."""
    if not msg or not isinstance(msg, str):
        return False
    low = msg.lower().strip()
    en_triggers = [
        "what's new", "whats new", "what is new", "anything new",
        "what changed", "what's changed", "whats changed",
        "what did you add", "what did we add",
        "what's been added", "what's different",
        "recent changes", "any updates",
    ]
    if any(t in low for t in en_triggers):
        return True
    he_triggers = [
        "מה השתנה", "מה חדש", "מה הוספנו", "מה הוספת",
        "מה שינית", "מה שינינו", "מה התווסף", "מה התעדכן",
        "מה עדכנו", "מה עדכנת",
    ]
    if any(t in msg for t in he_triggers):
        return True
    return False


def whats_new(lang="en"):
    """Read the most recent Changelog entries from this file and return a
    short reply for the user. Falls back gracefully on any error."""
    try:
        src = Path(__file__).read_text(encoding="utf-8")
    except Exception:
        return ("לא הצלחתי לקרוא את עצמי, אדוני." if lang == "he"
                else "I can't read my own source right now, sir.")
    m = re.search(r'Changelog:\s*\n(.+?)"""', src, re.DOTALL)
    if not m:
        return ("אין לי changelog זמין, אדוני." if lang == "he"
                else "I don't have a changelog to show, sir.")
    body = m.group(1)
    entries = re.findall(
        r'^  (v\d+\.\d+\s+-\s+.+?)(?=^  v\d+\.\d+\s+-\s+|\Z)',
        body, re.MULTILINE | re.DOTALL)
    if not entries:
        return ("ה-changelog ריק, אדוני." if lang == "he"
                else "The changelog is empty, sir.")
    cleaned = []
    for e in entries[:3]:
        flat = " ".join(line.strip() for line in e.splitlines()
                        if line.strip())
        cleaned.append(flat)
    facts = "\n".join("- " + c for c in cleaned)
    if not ANTHROPIC_API_KEY:
        return (("השינויים האחרונים, אדוני:\n" + facts) if lang == "he"
                else ("Recent changes, sir:\n" + facts))
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        sys_p = (
            "You are Achilles, a calm British-butler AI assistant. The user "
            "asked what changed recently in your code. Below are the last "
            "few Changelog entries (newest first). Summarise them naturally "
            "in 2-4 short sentences in "
            + ("Hebrew" if lang == "he" else "English")
            + ". Address the user as 'sir' (or 'אדוני' in Hebrew). Focus on "
            "what is new for the USER (capabilities, fixes they would "
            "notice), not internal version numbers or implementation "
            "details. Plain text only - no markdown, no bullet points."
        )
        r = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=300,
            system=sys_p,
            messages=[{"role": "user", "content": facts}])
        parts = [b.text for b in r.content
                 if getattr(b, "type", None) == "text"]
        reply = " ".join(p.strip() for p in parts if p.strip()).strip()
        return clean_text(reply) or facts
    except Exception:
        return facts


def _system_health_intercept(msg):
    """True if the user is asking for a system health check."""
    if not msg or not isinstance(msg, str):
        return False
    low = msg.lower().strip()
    en_triggers = [
        "system health", "health check", "status check",
        "self check", "self-check", "selfcheck",
        "are you ok", "are you okay", "are you alright",
        "is everything ok", "is everything okay",
        "everything working", "everything alright",
        "system status", "diagnostics",
        "run a check", "run diagnostics", "check yourself",
    ]
    if any(t in low for t in en_triggers):
        return True
    he_triggers = [
        "בדיקה עצמית", "בדוק את עצמך", "בדיקת מערכת",
        "בריאות מערכת", "בריאות המערכת", "מצב המערכת",
        "מצב מערכת", "סטטוס מערכת", "האם הכל תקין",
        "הכל עובד", "הכל תקין", "תבדוק שהכל",
        "הרץ בדיקה", "אבחון מערכת",
    ]
    if any(t in msg for t in he_triggers):
        return True
    return False


def system_health(lang="en"):
    """Quick health snapshot of JARVIS. Shallow checks only - no expensive
    API calls. Returns a short, natural reply phrased by Sonnet; falls back
    to raw facts on any error."""
    import socket as _socket_mod
    facts = []

    # API keys
    if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.startswith("sk-ant-"):
        facts.append("Anthropic key: OK (loaded, %d chars)"
                     % len(ANTHROPIC_API_KEY))
    elif ANTHROPIC_API_KEY:
        facts.append("Anthropic key: WARN (loaded but format looks off)")
    else:
        facts.append("Anthropic key: FAIL (missing from .env - brain offline)")

    if ELEVENLABS_API_KEY:
        facts.append("ElevenLabs key: OK (loaded, %d chars)"
                     % len(ELEVENLABS_API_KEY))
    else:
        facts.append("ElevenLabs key: WARN (missing - English voice will "
                     "fall back to edge-tts)")

    if GOOGLE_MAPS_API_KEY:
        facts.append("Google Maps key: OK (loaded)")
    else:
        facts.append("Google Maps key: WARN (missing - places, directions, "
                     "WorldView will not work)")

    # Google Calendar + Gmail (shared token) - v4.41: real live probe
    # not just file existence. Catches dead refresh tokens etc.
    if not os.path.exists(CAL_CREDENTIALS_FILE):
        facts.append("Google Calendar + Gmail: WARN "
                     "(not configured - no credentials.json)")
    elif not os.path.exists(CAL_TOKEN_FILE):
        facts.append("Google Calendar + Gmail: WARN "
                     "(no token yet - first sign-in needed)")
    else:
        try:
            _gc_svc = _calendar_service()
            if _gc_svc is None:
                facts.append("Google Calendar + Gmail: FAIL "
                             "(auth dead - run reauth_google.py)")
            else:
                _gc_svc.calendarList().list(maxResults=1).execute()
                facts.append("Google Calendar + Gmail: OK (live probe passed)")
        except Exception as _gc_e:
            facts.append("Google Calendar + Gmail: FAIL "
                         "(live probe error: %s)" % type(_gc_e).__name__)

    # Spotify
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        if _SPOTIFY_TOKEN_FILE.exists():
            facts.append("Spotify: OK (credentials and token present)")
        else:
            facts.append("Spotify: WARN (credentials present, no token - "
                         "first sign-in needed)")
    else:
        facts.append("Spotify: WARN (client id/secret missing from .env)")

    # WorldView HTML file
    try:
        wv = Path(__file__).resolve().parent / "worldview.html"
        if wv.exists():
            facts.append("WorldView file: OK (worldview.html present)")
        else:
            facts.append("WorldView file: WARN (worldview.html missing)")
    except Exception as e:
        facts.append("WorldView file: WARN (%s)" % e)

    # Knowledge folder
    try:
        kn = Path(KNOWLEDGE_DIR)
        if kn.exists():
            doms = [p for p in kn.iterdir() if p.is_dir()]
            facts.append("Knowledge folder: OK (%d domain(s) on disk)"
                         % len(doms))
        else:
            facts.append("Knowledge folder: WARN (not created yet)")
    except Exception as e:
        facts.append("Knowledge folder: WARN (%s)" % e)

    # Background deep-learning thread state
    try:
        with _deep_learn_lock:
            running = _deep_learn_state["running"]
            domain = _deep_learn_state["domain"]
            done = _deep_learn_state["done"]
            total = _deep_learn_state["total"]
        if running and domain:
            facts.append("Background learning: OK (running - %s, %d/%d "
                         "this run)" % (domain, done, total))
        else:
            facts.append("Background learning: OK (idle)")
    except Exception as e:
        facts.append("Background learning: WARN (%s)" % e)

    # Internet reachability (DNS port to Cloudflare - fast, free)
    try:
        s = _socket_mod.create_connection(("1.1.1.1", 53), timeout=2)
        s.close()
        facts.append("Internet: OK (reachable)")
    except Exception:
        facts.append("Internet: FAIL (unreachable - most tools will not work)")

    raw = "\n".join(facts)

    if not ANTHROPIC_API_KEY:
        return raw

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        sys_p = (
            "You are Achilles, a calm British-butler AI assistant. The user "
            "asked for a quick system health check. Below is a list of "
            "components and their statuses (OK / WARN / FAIL). Reply in 2-4 "
            "short sentences in "
            + ("Hebrew" if lang == "he" else "English")
            + ". Address the user as 'sir' (or 'אדוני' in Hebrew). Lead "
            "with the overall headline (all good / some warnings / a real "
            "problem). Then name only the items the user would care about - "
            "warnings and failures specifically; do not list every OK item "
            "unless absolutely everything is fine. Plain text, no markdown, "
            "no bullet points."
        )
        r = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=300,
            system=sys_p,
            messages=[{"role": "user", "content": raw}])
        parts = [b.text for b in r.content
                 if getattr(b, "type", None) == "text"]
        reply = " ".join(p.strip() for p in parts if p.strip()).strip()
        return clean_text(reply) or raw
    except Exception:
        return raw


def _learned_this_week_intercept(msg):
    """True if the user is asking what they learned this week."""
    if not msg or not isinstance(msg, str):
        return False
    low = msg.lower().strip()
    en_triggers = [
        "what did i learn this week", "what have i learned this week",
        "what did i study this week", "weekly learning summary",
        "what did we learn this week", "this week's notes",
        "what did i learn lately", "what have i learned lately",
        "learning summary", "what did i learn recently",
        "what have we learned",
    ]
    if any(t in low for t in en_triggers):
        return True
    he_triggers = [
        "מה למדתי השבוע", "מה למדנו השבוע",
        "מה למדתי לאחרונה", "מה למדנו לאחרונה",
        "סיכום למידה", "סיכום השבוע",
        "מה נלמד השבוע", "מה למדנו לאחרונה",
        "מה למדת לאחרונה", "מה למדת השבוע",
    ]
    if any(t in msg for t in he_triggers):
        return True
    return False


def learned_this_week(lang="en"):
    """Summarise knowledge notes created or modified in the past 7 days.
    Walks Obsidian_Vault/Knowledge/, groups by domain, then asks Sonnet to
    phrase a short reply. Falls back to raw facts on error."""
    try:
        base = Path(KNOWLEDGE_DIR)
        if not base.exists():
            return ("אין עדיין תיקיית ידע, אדוני." if lang == "he"
                    else "There's no knowledge folder yet, sir.")
        cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
        by_domain = {}      # domain_slug -> [titles]
        standalone = []     # notes directly under KNOWLEDGE_DIR
        for f in base.rglob("*.md"):
            if f.name.startswith("_"):
                continue
            try:
                mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    continue
            except Exception:
                continue
            try:
                head = "\n".join(
                    f.read_text(encoding="utf-8").splitlines()[:30])
            except Exception:
                continue
            title = None
            m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$",
                          head, re.MULTILINE)
            if m:
                title = m.group(1).strip()
            else:
                m = re.search(r"^#\s+(.+?)\s*$", head, re.MULTILINE)
                if m:
                    title = m.group(1).strip()
            if not title:
                title = f.stem.replace("_", " ")
            try:
                rel = f.relative_to(base)
                if len(rel.parts) > 1:
                    by_domain.setdefault(rel.parts[0], []).append(title)
                else:
                    standalone.append(title)
            except Exception:
                standalone.append(title)
        total = sum(len(v) for v in by_domain.values()) + len(standalone)
        if total == 0:
            return ("השבוע לא נוצרו פתקי ידע, אדוני." if lang == "he"
                    else "No knowledge notes were created in the past week, sir.")
        lines = []
        for domain, titles in sorted(by_domain.items()):
            d_name = domain.replace("_", " ")
            lines.append("%s (%d notes): %s"
                         % (d_name, len(titles), ", ".join(titles)))
        if standalone:
            lines.append("standalone (%d): %s"
                         % (len(standalone), ", ".join(standalone)))
        facts = ("Total notes in the past 7 days: %d.\n" % total
                 + "\n".join(lines))
        if not ANTHROPIC_API_KEY:
            return facts
        try:
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            sys_p = (
                "You are Achilles, a calm British-butler AI assistant. The "
                "user asked for a summary of what was learned this week (in "
                "the knowledge notes). Below is the list of notes generated "
                "in the past 7 days, grouped by domain. Reply in 2-4 short "
                "sentences in "
                + ("Hebrew" if lang == "he" else "English")
                + ". Address the user as 'sir' (or 'אדוני' in Hebrew). Lead "
                "with the total count and the main domain(s). Name a few "
                "notable sub-topics by name (but not all). Plain text, no "
                "markdown, no bullet points."
            )
            r = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=350,
                system=sys_p,
                messages=[{"role": "user", "content": facts}])
            parts = [b.text for b in r.content
                     if getattr(b, "type", None) == "text"]
            reply = " ".join(p.strip() for p in parts if p.strip()).strip()
            return clean_text(reply) or facts
        except Exception:
            return facts
    except Exception as e:
        return ("נכשלתי לסכם את הלמידה השבוע, אדוני: %s" % e
                if lang == "he"
                else "Failed to summarise weekly learning, sir: %s" % e)


# =====================================================================
# Undo (v4.29) - reverse the most recent mutating action
# =====================================================================
_last_action_lock = threading.Lock()
_last_action = {"type": None, "data": None}


def _record_action(action_type, data):
    """Remember the most recent undoable action. Called by mutating
    functions (save_note, calendar_add, calendar_delete, set_timer)
    after they succeed. Only the SINGLE most recent action is kept -
    'undo' covers one step."""
    with _last_action_lock:
        _last_action["type"] = action_type
        _last_action["data"] = data


def undo_last():
    """Reverse the most recent mutating action. Supported types:
       calendar_add    - removes the just-added event
       calendar_delete - re-inserts the just-deleted event (body
                         was cached before deletion)
       save_note       - removes the appended line from disk
       set_timer       - cancels the pending threading.Timer
    Returns a short status string for the spoken reply. Consumes
    the recorded action immediately so a second 'undo' is a no-op
    rather than a double-reverse."""
    with _last_action_lock:
        atype = _last_action.get("type")
        data = _last_action.get("data") or {}
        _last_action["type"] = None
        _last_action["data"] = None
    if not atype:
        return "Nothing to undo, sir."
    try:
        if atype == "calendar_add":
            event_id = data.get("event_id", "")
            summary = data.get("summary", "")
            if not event_id:
                return "Can't undo - I don't have the event id, sir."
            svc = _calendar_service()
            if svc is None:
                return "Can't undo - calendar isn't connected, sir."
            svc.events().delete(calendarId="primary",
                                eventId=event_id).execute()
            return "Undone, sir. Removed '%s'." % (summary or "the event")
        if atype == "calendar_delete":
            body = data.get("body") or {}
            summary = body.get("summary", "the event")
            svc = _calendar_service()
            if svc is None:
                return "Can't undo - calendar isn't connected, sir."
            if not body.get("start") or not body.get("end"):
                return "Can't undo - the cached event is incomplete, sir."
            svc.events().insert(calendarId="primary", body=body).execute()
            return "Undone, sir. Restored '%s'." % summary
        if atype == "save_note":
            path = data.get("path", "")
            written = data.get("written", "")
            if not path or not os.path.exists(path):
                return "Can't undo - the note file is gone, sir."
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                return "Can't read the note file, sir: %s" % e
            if written and content.endswith(written):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content[:-len(written)])
                return "Undone, sir. Removed the last note."
            return ("Can't undo - the note file changed since I "
                    "wrote it, sir.")
        if atype == "set_timer":
            timer = data.get("timer")
            label = data.get("label") or ""
            if timer is not None:
                try:
                    timer.cancel()
                except Exception:
                    pass
                try:
                    if timer in _active_timers:
                        _active_timers.remove(timer)
                except Exception:
                    pass
            return ("Timer cancelled%s, sir."
                    % ((" (%s)" % label) if label else ""))
        return "I don't know how to undo that, sir."
    except Exception as e:
        return "Undo failed: %s" % e


def _undo_intercept(msg):
    """True if the user is asking to undo the last action."""
    if not msg or not isinstance(msg, str):
        return False
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip().rstrip(".!?,")
    low = text.lower()
    en_triggers = {
        "undo", "undo it", "undo that", "undo last",
        "undo the last", "undo the last action", "undo last action",
        "revert", "revert that", "revert it", "revert the last",
        "cancel that", "cancel the last", "cancel last action",
        "scratch that", "take that back", "take it back",
        "nevermind that", "never mind that",
    }
    if low in en_triggers:
        return True
    he_triggers = {
        "\u05ea\u05d1\u05d8\u05dc", "\u05ea\u05d1\u05d8\u05dc \u05d0\u05ea \u05d6\u05d4",
        "\u05ea\u05d1\u05d8\u05dc \u05d0\u05ea \u05d4\u05e4\u05e2\u05d5\u05dc\u05d4",
        "\u05ea\u05d1\u05d8\u05dc \u05d0\u05ea \u05d4\u05d0\u05d7\u05e8\u05d5\u05df",
        "\u05d1\u05d8\u05dc", "\u05d1\u05d8\u05dc \u05d0\u05ea \u05d6\u05d4",
        "\u05d1\u05d8\u05dc \u05d0\u05ea \u05d4\u05e4\u05e2\u05d5\u05dc\u05d4",
        "\u05d1\u05d8\u05dc \u05d0\u05ea \u05d4\u05d0\u05d7\u05e8\u05d5\u05df",
        "\u05d1\u05d9\u05d8\u05d5\u05dc", "\u05d1\u05d9\u05d8\u05d5\u05dc \u05d0\u05d7\u05e8\u05d5\u05df",
        "\u05d1\u05d9\u05d8\u05d5\u05dc \u05e4\u05e2\u05d5\u05dc\u05d4",
        "\u05d0\u05e0\u05d3\u05d5", "\u05ea\u05d7\u05d6\u05d9\u05e8 \u05d0\u05ea \u05d6\u05d4",
        "\u05ea\u05d7\u05d6\u05d9\u05e8", "\u05ea\u05d7\u05d6\u05d5\u05e8 \u05d0\u05d7\u05d5\u05e8\u05d4",
    }
    if text in he_triggers:
        return True
    return False


# =====================================================================
# Cost tracking (v4.30) - monthly Anthropic API budget
# =====================================================================
_usage_lock = threading.Lock()
_USAGE_FILE = Path("anthropic_usage.json")
try:
    _BUDGET_USD = float(os.getenv("JARVIS_MONTHLY_BUDGET_USD", "50"))
except Exception:
    _BUDGET_USD = 50.0

# Pricing per million tokens. User can override if Anthropic changes
# rates. Matched by substring on the model name (sonnet/opus/haiku).
_DEFAULT_ANTHROPIC_PRICING = {
    "sonnet": {"input": 3.00,  "output": 15.00},
    "opus":   {"input": 15.00, "output": 75.00},
    "haiku":  {"input": 0.80,  "output": 4.00},
}


def _model_pricing(model_name):
    """Look up per-million-token rates for a model. Falls back to
    Sonnet pricing for unrecognized names (safest middle-of-road)."""
    low = (model_name or "").lower()
    if "opus" in low:
        return _DEFAULT_ANTHROPIC_PRICING["opus"]
    if "haiku" in low:
        return _DEFAULT_ANTHROPIC_PRICING["haiku"]
    return _DEFAULT_ANTHROPIC_PRICING["sonnet"]


def _load_usage():
    if not _USAGE_FILE.exists():
        return {}
    try:
        return json.loads(_USAGE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_usage(data):
    try:
        _USAGE_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8")
    except Exception as e:
        print("[diag] usage save failed:", repr(e))


def _track_anthropic_usage(response):
    """Update the persistent usage counter from an Anthropic response.
    Best-effort - any error returns silently so it never breaks the
    main API flow."""
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        in_tok = getattr(usage, "input_tokens", 0) or 0
        out_tok = getattr(usage, "output_tokens", 0) or 0
        # Cache tokens (if present) bill at the same input rate here
        # for simplicity - a slight overestimate vs. Anthropic's
        # 90%-off cache hits, but never an underestimate.
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
        in_tok += cache_read + cache_create
        model = getattr(response, "model", "")
        pricing = _model_pricing(model)
        cost = (in_tok * pricing["input"]
                + out_tok * pricing["output"]) / 1_000_000.0
        crossed_80 = False
        crossed_100 = False
        with _usage_lock:
            data = _load_usage()
            month_key = datetime.date.today().strftime("%Y-%m")
            months = data.setdefault("months", {})
            m = months.setdefault(month_key, {
                "input_tokens": 0, "output_tokens": 0,
                "cost_usd": 0.0, "calls": 0,
                "warned_80": False, "warned_100": False,
            })
            m["input_tokens"] += in_tok
            m["output_tokens"] += out_tok
            m["cost_usd"] = round(m["cost_usd"] + cost, 6)
            m["calls"] += 1
            data["last_update"] = datetime.datetime.now().isoformat(
                timespec="seconds")
            pct = (m["cost_usd"] / _BUDGET_USD * 100.0
                   if _BUDGET_USD > 0 else 0)
            if pct >= 100 and not m["warned_100"]:
                m["warned_100"] = True
                crossed_100 = True
            elif pct >= 80 and not m["warned_80"]:
                m["warned_80"] = True
                crossed_80 = True
            _save_usage(data)
        # Fire the alert OUTSIDE the lock and in a background thread
        # so the main API flow never blocks on TTS.
        if crossed_100:
            threading.Thread(target=_budget_alert, args=("over",),
                             daemon=True).start()
        elif crossed_80:
            threading.Thread(target=_budget_alert, args=("warning",),
                             daemon=True).start()
    except Exception as e:
        print("[diag] usage tracking failed:", repr(e))


def _budget_alert(level):
    """Announce a budget alert by voice and on the orb. Runs in a
    background thread; safe to fail silently."""
    if level == "over":
        msg = ("Sir, you've exceeded the monthly API budget of $%.0f. "
               "Consider pausing background learning."
               % _BUDGET_USD)
    else:
        msg = ("Sir, you've used 80%% of the monthly $%.0f API budget. "
               "Heads up." % _BUDGET_USD)
    try:
        if APP is not None:
            APP.ui(lambda m=msg: APP._push("JARVIS", m))
    except Exception:
        pass
    try:
        speak(msg)
    except Exception:
        pass


def budget_status(lang="en"):
    """Voice-friendly summary of current month's spending. Called by
    _budget_intercept; returns plain text for clean_text / speak."""
    try:
        data = _load_usage()
        month_key = datetime.date.today().strftime("%Y-%m")
        m = data.get("months", {}).get(month_key, {})
        spent = float(m.get("cost_usd", 0.0))
        calls = int(m.get("calls", 0))
        in_tok = int(m.get("input_tokens", 0))
        out_tok = int(m.get("output_tokens", 0))
        pct = (spent / _BUDGET_USD * 100.0) if _BUDGET_USD > 0 else 0
        if lang == "he":
            return ("החודש הוצאת %.2f דולר מתוך %.0f דולר, %.0f אחוזים, "
                    "אדוני. %d קריאות API, %s טוקנים בקלט ו-%s טוקנים בפלט."
                    % (spent, _BUDGET_USD, pct, calls,
                       "{:,}".format(in_tok), "{:,}".format(out_tok)))
        return ("Sir, you've spent $%.2f of your $%.0f monthly cap "
                "(%.0f%%) - %d API calls, %s input tokens and %s "
                "output tokens." % (spent, _BUDGET_USD, pct, calls,
                                     "{:,}".format(in_tok),
                                     "{:,}".format(out_tok)))
    except Exception as e:
        if lang == "he":
            return "לא הצלחתי לקרוא את התקציב, אדוני: %s" % e
        return "Couldn't read the budget, sir: %s" % e


def _budget_intercept(msg):
    """True if the user is asking about API cost / budget."""
    if not msg or not isinstance(msg, str):
        return False
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    low = text.lower().strip().rstrip(".!?,")
    en_triggers = {
        "budget", "my budget", "the budget",
        "what's my budget", "whats my budget", "what is my budget",
        "show me the budget", "show my budget",
        "api budget", "api cost", "api spending", "api spend",
        "cost status", "monthly cost", "monthly spend",
        "how much have i spent", "how much did i spend",
        "how much is the api costing",
    }
    if low in en_triggers:
        return True
    he_triggers = {
        "\u05d4\u05ea\u05e7\u05e6\u05d9\u05d1",
        "\u05de\u05d4 \u05d4\u05ea\u05e7\u05e6\u05d9\u05d1",
        "\u05de\u05d4 \u05d4\u05ea\u05e7\u05e6\u05d9\u05d1 \u05e9\u05dc\u05d9",
        "\u05ea\u05e7\u05e6\u05d9\u05d1 \u05d4-API",
        "\u05ea\u05e7\u05e6\u05d9\u05d1 \u05d4\u05d7\u05d5\u05d3\u05e9",
        "\u05de\u05e6\u05d1 \u05d4\u05ea\u05e7\u05e6\u05d9\u05d1",
        "\u05db\u05de\u05d4 \u05d4\u05d5\u05e6\u05d0\u05ea\u05d9",
        "\u05db\u05de\u05d4 \u05d6\u05d4 \u05e2\u05d5\u05dc\u05d4",
        "\u05db\u05de\u05d4 \u05d1\u05d9\u05d6\u05d1\u05d6\u05ea\u05d9",
        "\u05e2\u05dc\u05d5\u05ea \u05d4-API",
    }
    if text in he_triggers:
        return True
    if any(t in text for t in ("\u05de\u05d4 \u05d4\u05ea\u05e7\u05e6\u05d9\u05d1",
                                "\u05db\u05de\u05d4 \u05d4\u05d5\u05e6\u05d0\u05ea\u05d9",
                                "\u05de\u05e6\u05d1 \u05d4\u05ea\u05e7\u05e6\u05d9\u05d1")):
        return True
    return False


# Monkey-patch anthropic.Anthropic so every messages.create() call
# updates the usage counter automatically. Single insertion point
# instead of wrapping ~10 call sites in jarvis.py.
try:
    from anthropic.resources.messages import Messages as _AnthMessages
    if not hasattr(_AnthMessages, "_jarvis_patched"):
        _orig_anth_create = _AnthMessages.create

        def _wrapped_anth_create(self, *args, **kwargs):
            response = _orig_anth_create(self, *args, **kwargs)
            try:
                _track_anthropic_usage(response)
            except Exception:
                pass
            return response

        _AnthMessages.create = _wrapped_anth_create
        _AnthMessages._jarvis_patched = True
        print("[diag] Anthropic usage tracking active (budget cap $%.0f/month)"
              % _BUDGET_USD, flush=True)
except Exception as _patch_err:
    print("[diag] anthropic usage tracking patch failed:",
          repr(_patch_err), flush=True)


# =====================================================================
# Vault backup (v4.31) - daily zip of Obsidian_Vault
# =====================================================================
BACKUP_DIR = Path("./backups")
BACKUP_KEEP = 14
VAULT_DIR = Path("./Obsidian_Vault")


def backup_vault():
    """Create a timestamped zip of VAULT_DIR under BACKUP_DIR and prune
    to BACKUP_KEEP newest. Returns a short status string for the spoken
    reply. Safe to call from a daemon thread - any error is logged and
    a friendly message returned. Never raises."""
    import zipfile
    try:
        if not VAULT_DIR.exists():
            return "No vault to back up, sir."
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        fname = BACKUP_DIR / ("obsidian_vault_" + ts + ".zip")
        n_files = 0
        total_bytes = 0
        skipped = 0
        with zipfile.ZipFile(fname, "w", zipfile.ZIP_DEFLATED,
                             compresslevel=6) as z:
            for f in VAULT_DIR.rglob("*"):
                if not f.is_file():
                    continue
                try:
                    arcname = f.relative_to(VAULT_DIR.parent)
                    z.write(f, arcname)
                    n_files += 1
                    total_bytes += f.stat().st_size
                except Exception as fe:
                    skipped += 1
                    print("[diag] backup skip:", f, repr(fe))
        # Prune older zips beyond BACKUP_KEEP
        existing = sorted(
            BACKUP_DIR.glob("obsidian_vault_*.zip"),
            key=lambda p: p.stat().st_mtime, reverse=True)
        pruned = 0
        for old in existing[BACKUP_KEEP:]:
            try:
                old.unlink()
                pruned += 1
            except Exception:
                pass
        size_mb = total_bytes / 1024.0 / 1024.0
        zip_size_mb = fname.stat().st_size / 1024.0 / 1024.0
        tail = ""
        if skipped:
            tail += " %d files skipped." % skipped
        if pruned:
            tail += " %d old backups pruned." % pruned
        return ("Backed up %d files - %.1f MB raw, %.1f MB zipped - "
                "to %s, sir. Keeping the last %d backups.%s"
                % (n_files, size_mb, zip_size_mb, fname.name,
                   BACKUP_KEEP, tail))
    except Exception as e:
        print("[diag] backup_vault failed:", repr(e))
        return "Backup failed, sir: %s" % e


def _backup_intercept(msg):
    """True if the user is asking to back up the vault."""
    if not msg or not isinstance(msg, str):
        return False
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip().rstrip(".!?,")
    low = text.lower()
    en_triggers = {
        "backup", "back up", "backup now", "back up now",
        "backup my notes", "back up my notes",
        "backup the vault", "backup my vault", "back up the vault",
        "backup the notes", "back up the notes",
        "create a backup", "create backup",
        "make a backup", "make backup",
        "run a backup", "run backup",
        "save a backup", "save backup",
    }
    if low in en_triggers:
        return True
    he_triggers = {
        "\u05d2\u05d9\u05d1\u05d5\u05d9",
        "\u05d2\u05d1\u05d4",
        "\u05d2\u05d1\u05d4 \u05dc\u05d9",
        "\u05d2\u05d1\u05d4 \u05d0\u05ea \u05d4\u05e4\u05ea\u05e7\u05d9\u05dd",
        "\u05d2\u05d1\u05d4 \u05d0\u05ea \u05d4\u05db\u05e1\u05e4\u05ea",
        "\u05ea\u05d2\u05d1\u05d4",
        "\u05ea\u05d2\u05d1\u05d4 \u05dc\u05d9",
        "\u05ea\u05d2\u05d1\u05d4 \u05d0\u05ea \u05d4\u05e4\u05ea\u05e7\u05d9\u05dd",
        "\u05ea\u05d2\u05d1\u05d4 \u05d0\u05ea \u05d4\u05db\u05e1\u05e4\u05ea",
        "\u05ea\u05d9\u05e6\u05d5\u05e8 \u05d2\u05d9\u05d1\u05d5\u05d9",
        "\u05e2\u05e9\u05d4 \u05d2\u05d9\u05d1\u05d5\u05d9",
        "\u05e8\u05d5\u05e5 \u05d2\u05d9\u05d1\u05d5\u05d9",
        "\u05d4\u05e8\u05e5 \u05d2\u05d9\u05d1\u05d5\u05d9",
    }
    if text in he_triggers:
        return True
    return False


# =====================================================================
# Decisions log (v4.32)
# =====================================================================
DECISIONS_FILE = Path("./Obsidian_Vault/Decisions.md")


def log_decision(text):
    """Append a timestamped decision to Obsidian_Vault/Decisions.md.
    Returns a short status string."""
    if not text or not text.strip():
        return "What decision should I log, sir?"
    try:
        DECISIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.datetime.now()
        new_file = not DECISIONS_FILE.exists()
        with open(DECISIONS_FILE, "a", encoding="utf-8") as f:
            if new_file:
                f.write("# Decisions Log\n\n")
            f.write("## %s\n%s\n\n"
                    % (now.strftime("%Y-%m-%d %H:%M"), text.strip()))
        return "Decision logged, sir."
    except Exception as e:
        return "Failed to log the decision, sir: %s" % e


def recent_decisions(n=5, lang="en"):
    """Read back the most recent n decisions with relative dates."""
    try:
        if not DECISIONS_FILE.exists():
            return ("עדיין לא רשמת החלטות, אדוני." if lang == "he"
                    else "No decisions logged yet, sir.")
        text = DECISIONS_FILE.read_text(encoding="utf-8")
        entries = re.findall(r"^## (.+?)\n(.+?)(?=\n## |\Z)", text,
                             re.MULTILINE | re.DOTALL)
        if not entries:
            return ("עדיין לא רשמת החלטות, אדוני." if lang == "he"
                    else "No decisions logged yet, sir.")
        recent = entries[-n:]
        recent.reverse()
        lines = []
        for when, body in recent:
            try:
                d = datetime.datetime.strptime(
                    when.strip(), "%Y-%m-%d %H:%M").date()
                days = (datetime.date.today() - d).days
                if lang == "he":
                    rel = ("היום" if days == 0 else
                           "אתמול" if days == 1 else
                           "לפני %d ימים" % days)
                else:
                    rel = ("today" if days == 0 else
                           "yesterday" if days == 1 else
                           "%d days ago" % days)
            except Exception:
                rel = when.strip()
            body_clean = " ".join(body.split())
            lines.append("%s: %s" % (rel, body_clean))
        facts = "\n".join(lines)
        if lang == "he":
            return "ההחלטות האחרונות שלך, אדוני:\n" + facts
        return "Your recent decisions, sir:\n" + facts
    except Exception as e:
        return "Couldn't read the decisions log, sir: %s" % e


def _decision_log_parse(msg):
    """If the message is 'log decision: X' / 'תרשום החלטה X', return X.
    Else None."""
    if not msg or not isinstance(msg, str):
        return None
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip()
    m = re.match(r"(?:log|record|note|save)\s+(?:a\s+|the\s+)?"
                 r"decision[:\-\s]+(.+)$", text, re.I)
    if m:
        return m.group(1).strip()
    m = re.match(r"(?:\u05ea\u05e8\u05e9\u05d5\u05dd|\u05e8\u05e9\u05d5\u05dd|\u05ea\u05e2\u05d3|\u05ea\u05ea\u05e2\u05d3)\s+"
                 r"(?:\u05dc\u05d9\s+)?(?:\u05d0\u05ea\s+)?(?:\u05d4)?"
                 r"\u05d4\u05d7\u05dc\u05d8\u05d4[:\-\s]+(.+)$", text)
    if m:
        return m.group(1).strip()
    return None


def _decision_review_intercept(msg):
    """True if the user is asking to review their decisions."""
    if not msg or not isinstance(msg, str):
        return False
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip().rstrip(".!?,")
    low = text.lower()
    en_triggers = {
        "my decisions", "show my decisions", "show decisions",
        "recent decisions", "list my decisions", "decision log",
        "what did i decide", "what have i decided",
        "read my decisions",
    }
    if low in en_triggers:
        return True
    he_triggers = {
        "\u05d4\u05d4\u05d7\u05dc\u05d8\u05d5\u05ea \u05e9\u05dc\u05d9",
        "\u05d4\u05d7\u05dc\u05d8\u05d5\u05ea \u05d0\u05d7\u05e8\u05d5\u05e0\u05d5\u05ea",
        "\u05d4\u05d4\u05d7\u05dc\u05d8\u05d5\u05ea \u05d4\u05d0\u05d7\u05e8\u05d5\u05e0\u05d5\u05ea",
        "\u05de\u05d4 \u05d4\u05d7\u05dc\u05d8\u05ea\u05d9",
        "\u05d9\u05d5\u05de\u05df \u05d4\u05d7\u05dc\u05d8\u05d5\u05ea",
        "\u05ea\u05e8\u05d0\u05d4 \u05dc\u05d9 \u05d0\u05ea \u05d4\u05d4\u05d7\u05dc\u05d8\u05d5\u05ea",
    }
    if text in he_triggers:
        return True
    return False


# =====================================================================
# Nutrition / macro tracker (v4.33) - reuses training_log.json
# =====================================================================
TRAINING_LOG_FILE = Path("./training_log.json")


def _load_training_log():
    if not TRAINING_LOG_FILE.exists():
        return {}
    try:
        return json.loads(TRAINING_LOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_training_log(data):
    try:
        TRAINING_LOG_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8")
    except Exception as e:
        print("[diag] training log save failed:", repr(e))


def _nutrition_reset_if_new_day(data):
    """Zero today's counters when the stored date isn't today. Mutates
    data in place; caller decides whether to save."""
    today = datetime.date.today().isoformat()
    if data.get("nutrition_date") != today:
        data["nutrition_date"] = today
        data["today_calories"] = 0
        data["today_protein_g"] = 0


def log_calories(n):
    try:
        n = int(round(float(n)))
    except Exception:
        return "How many calories, sir?"
    data = _load_training_log()
    _nutrition_reset_if_new_day(data)
    data["today_calories"] = int(data.get("today_calories", 0)) + n
    _save_training_log(data)
    tgt = data.get("target_calories", 3000)
    total = data["today_calories"]
    return ("Logged %d calories, sir. Today's total: %d of %d."
            % (n, total, tgt))


def log_protein(g):
    try:
        g = int(round(float(g)))
    except Exception:
        return "How many grams of protein, sir?"
    data = _load_training_log()
    _nutrition_reset_if_new_day(data)
    data["today_protein_g"] = int(data.get("today_protein_g", 0)) + g
    _save_training_log(data)
    tgt = data.get("target_protein_g", 130)
    total = data["today_protein_g"]
    return ("Logged %d grams of protein, sir. Today's total: %d of %d."
            % (g, total, tgt))


def nutrition_status(lang="en"):
    data = _load_training_log()
    _nutrition_reset_if_new_day(data)  # display-only; not saved
    cal = int(data.get("today_calories", 0))
    pro = int(data.get("today_protein_g", 0))
    tcal = data.get("target_calories", 3000)
    tpro = data.get("target_protein_g", 130)
    cal_left = tcal - cal
    pro_left = tpro - pro
    if lang == "he":
        return ("היום, אדוני: %d מתוך %d קלוריות (%d נותרו), "
                "%d מתוך %d גרם חלבון (%d נותרו)."
                % (cal, tcal, max(0, cal_left), pro, tpro,
                   max(0, pro_left)))
    return ("Today, sir: %d of %d calories (%d to go), %d of %d grams "
            "of protein (%d to go)."
            % (cal, tcal, max(0, cal_left), pro, tpro, max(0, pro_left)))


def _nutrition_log_parse(msg):
    """Parse a nutrition log command. Returns ('calories', N) or
    ('protein', N) or None. Requires a number, a unit word, and a
    logging verb so questions don't false-trigger."""
    if not msg or not isinstance(msg, str):
        return None
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    low = text.lower()
    en_verb = re.search(r"\b(log|ate|eaten|add|added|track|had|"
                        r"consumed|just had)\b", low)
    if en_verb:
        mp = re.search(r"(\d+(?:\.\d+)?)\s*(?:grams?|g)\s*(?:of\s+)?"
                       r"protein", low)
        if mp:
            return ("protein", float(mp.group(1)))
        mp2 = re.search(r"protein[:\s]+(\d+(?:\.\d+)?)", low)
        if mp2:
            return ("protein", float(mp2.group(1)))
        mc = re.search(r"(\d+(?:\.\d+)?)\s*(?:k?cals?|calories|calorie|"
                       r"kcal)\b", low)
        if mc:
            return ("calories", float(mc.group(1)))
    he_verb = re.search(r"(\u05d0\u05db\u05dc\u05ea\u05d9|\u05ea\u05e8\u05e9\u05d5\u05dd|\u05e8\u05e9\u05d5\u05dd|\u05d4\u05d5\u05e1\u05e3|\u05ea\u05d5\u05e1\u05d9\u05e3|\u05e6\u05e8\u05db\u05ea\u05d9)", text)
    if he_verb:
        mp = re.search(r"(\d+(?:\.\d+)?)\s*(?:\u05d2\u05e8\u05dd\s+)?\u05d7\u05dc\u05d1\u05d5\u05df", text)
        if mp:
            return ("protein", float(mp.group(1)))
        mp2 = re.search(r"\u05d7\u05dc\u05d1\u05d5\u05df[:\s]+(\d+(?:\.\d+)?)", text)
        if mp2:
            return ("protein", float(mp2.group(1)))
        mc = re.search(r"(\d+(?:\.\d+)?)\s*(?:\u05e7\u05dc\u05d5\u05e8\u05d9\u05d5\u05ea|\u05e7\u05dc\u05d5\u05e8\u05d9\u05d4|\u05e7\u05e7\"\u05dc)", text)
        if mc:
            return ("calories", float(mc.group(1)))
    return None


def _nutrition_status_intercept(msg):
    """True if the user is asking about today's nutrition/macros."""
    if not msg or not isinstance(msg, str):
        return False
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip().rstrip(".!?,")
    low = text.lower()
    en_triggers = {
        "nutrition", "nutrition status", "my nutrition",
        "macros", "my macros", "macro status",
        "calories today", "how many calories today",
        "protein today", "how much protein today",
        "what have i eaten", "what have i eaten today",
        "food log", "diet status", "how am i eating",
    }
    if low in en_triggers:
        return True
    he_triggers = {
        "\u05ea\u05d6\u05d5\u05e0\u05d4", "\u05de\u05e6\u05d1 \u05ea\u05d6\u05d5\u05e0\u05d4",
        "\u05de\u05d0\u05e7\u05e8\u05d5", "\u05d4\u05de\u05d0\u05e7\u05e8\u05d5 \u05e9\u05dc\u05d9",
        "\u05db\u05de\u05d4 \u05d0\u05db\u05dc\u05ea\u05d9",
        "\u05db\u05de\u05d4 \u05d0\u05db\u05dc\u05ea\u05d9 \u05d4\u05d9\u05d5\u05dd",
        "\u05e7\u05dc\u05d5\u05e8\u05d9\u05d5\u05ea \u05d4\u05d9\u05d5\u05dd",
        "\u05d7\u05dc\u05d1\u05d5\u05df \u05d4\u05d9\u05d5\u05dd",
        "\u05de\u05d4 \u05d0\u05db\u05dc\u05ea\u05d9 \u05d4\u05d9\u05d5\u05dd",
    }
    if text in he_triggers:
        return True
    return False


# =====================================================================
# Self-test / quiz mode (v4.34)
# =====================================================================
_quiz_lock = threading.Lock()
_quiz_state = {"active": False, "question": "", "answer": "", "topic": ""}


def _pick_quiz_note(topic):
    """Find a knowledge note matching `topic` (or any note if topic is
    empty/unmatched). Returns (path, content) or (None, None)."""
    import random
    base = Path(KNOWLEDGE_DIR)
    if not base.exists():
        return None, None
    candidates = [f for f in base.rglob("*.md")
                  if not f.name.startswith("_")]
    if not candidates:
        return None, None
    if topic:
        slug = _slugify_topic(topic)
        matched = []
        for f in candidates:
            dom = _slugify_topic(f.parent.name)
            if (slug and (slug in dom or dom in slug
                          or slug in f.stem.lower())):
                matched.append(f)
        if matched:
            candidates = matched
    note = random.choice(candidates)
    try:
        content = note.read_text(encoding="utf-8")[:6000]
    except Exception:
        return None, None
    return note, content


def start_quiz(topic, lang="en"):
    """Pick a note, generate one question + model answer, store as
    pending, and return the question text to speak."""
    if not ANTHROPIC_API_KEY:
        return ("לא ניתן להריץ חידון - מפתח Anthropic לא מוגדר, אדוני."
                if lang == "he"
                else "Can't run a quiz - the Anthropic key isn't set, sir.")
    note, content = _pick_quiz_note(topic)
    if not content:
        if topic:
            return (("אין לי פתקי ידע על %s עדיין, אדוני. בקש ממני "
                     "ללמוד את זה קודם." % topic) if lang == "he"
                    else ("I don't have knowledge notes on %s yet, sir. "
                          "Ask me to learn it first." % topic))
        return ("אין לי פתקי ידע לבחון אותך עליהם עדיין, אדוני."
                if lang == "he"
                else "I have no knowledge notes to quiz you on yet, sir.")
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        sys_p = (
            "You are a quizmaster. From the study note below, write ONE "
            "clear exam-style question that tests real understanding "
            "(not trivia), plus a concise model answer. Output EXACTLY "
            "two lines and nothing else:\nQ: <question>\nA: <model "
            "answer>\nWrite in "
            + ("Hebrew" if lang == "he" else "English") + ".")
        r = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=400,
            system=sys_p,
            messages=[{"role": "user", "content": content}])
        txt = " ".join(b.text for b in r.content
                       if getattr(b, "type", None) == "text").strip()
        mq = re.search(r"Q:\s*(.+?)(?:\nA:|A:)", txt, re.DOTALL)
        ma = re.search(r"A:\s*(.+)$", txt, re.DOTALL)
        if not mq or not ma:
            return ("לא הצלחתי לנסח שאלה, אדוני. נסה שוב."
                    if lang == "he"
                    else "I couldn't form a question, sir. Try again.")
        q = mq.group(1).strip()
        a = ma.group(1).strip()
    except Exception as e:
        return "Quiz generation failed, sir: %s" % e
    with _quiz_lock:
        _quiz_state.update(active=True, question=q, answer=a,
                           topic=(topic or note.stem))
    if lang == "he":
        return "שאלה, אדוני: " + q + " אמור את התשובה כשתהיה מוכן."
    return "Question, sir: " + q + " Tell me your answer when ready."


def evaluate_quiz_answer(user_answer, lang="en"):
    """Grade the user's answer against the pending question and clear
    the pending state. Returns feedback text, or None if no quiz is
    pending (so think() falls through to normal handling)."""
    with _quiz_lock:
        if not _quiz_state["active"]:
            return None
        q = _quiz_state["question"]
        expected = _quiz_state["answer"]
        _quiz_state.update(active=False, question="", answer="", topic="")
    ans = (user_answer or "").strip()
    cancel = {"stop", "cancel", "never mind", "nevermind", "forget it",
              "\u05e2\u05d6\u05d5\u05d1", "\u05d1\u05d8\u05dc", "\u05e2\u05e6\u05d5\u05e8",
              "\u05d3\u05d9", "\u05dc\u05d0 \u05e2\u05db\u05e9\u05d9\u05d5"}
    # v4.67: always let the user bail - match cancel words anywhere, not just an
    # exact whole-string equality (so "stop the quiz" / cancel-anywhere works).
    _al = ans.lower()
    _words = set(re.split(r"[\s,.!?]+", _al))
    if (_al in cancel or ans in cancel
            or _words & {"stop", "cancel", "forget", "nevermind"}
            or any(w in ans for w in ("\u05e2\u05d6\u05d5\u05d1", "\u05d1\u05d8\u05dc", "\u05e2\u05e6\u05d5\u05e8"))):
        return ("ביטלתי את החידון, אדוני." if lang == "he"
                else "Quiz cancelled, sir.")
    if not ANTHROPIC_API_KEY:
        return (("התשובה שחיפשתי, אדוני: " + expected) if lang == "he"
                else ("The expected answer, sir: " + expected))
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        sys_p = (
            "You are a supportive but honest tutor grading a spoken "
            "answer. Given the question, the model answer, and the "
            "student's answer, say in 2-3 sentences whether the student "
            "was correct, partially correct, or wrong, and give the key "
            "point they missed if any. Address them as 'sir' (or "
            "'אדוני'). Write in "
            + ("Hebrew" if lang == "he" else "English")
            + ". Plain text, no markdown.")
        prompt = ("Question: %s\nModel answer: %s\nStudent's answer: %s"
                  % (q, expected, ans))
        r = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=300,
            system=sys_p,
            messages=[{"role": "user", "content": prompt}])
        fb = " ".join(b.text for b in r.content
                      if getattr(b, "type", None) == "text").strip()
        return clean_text(fb) or ("The expected answer was: " + expected)
    except Exception as e:
        return ("Couldn't grade that, sir: %s. Expected answer: %s"
                % (e, expected))


def _quiz_start_parse(msg):
    """Return the quiz topic (possibly an empty string for 'no specific
    topic') if the message is a quiz request, else None."""
    if not msg or not isinstance(msg, str):
        return None
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip().rstrip(".!?,")
    low = text.lower()
    m = re.match(r"(?:quiz|test)\s+me(?:\s+on\s+(.+))?$", low)
    if m:
        return (m.group(1) or "").strip()
    m = re.match(r"(?:give me a quiz|quiz time|test my knowledge|"
                 r"self test|self-test)(?:\s+on\s+(.+))?$", low)
    if m:
        return (m.group(1) or "").strip()
    m = re.match(r"(?:\u05ea\u05d1\u05d7\u05df|\u05ea\u05e9\u05d0\u05dc|\u05e9\u05d0\u05dc)\s+\u05d0\u05d5\u05ea\u05d9(?:\s+\u05e2\u05dc\s+(.+))?$", text)
    if m:
        return (m.group(1) or "").strip()
    m = re.match(r"\u05d7\u05d9\u05d3\u05d5\u05df(?:\s+\u05e2\u05dc\s+(.+))?$", text)
    if m:
        return (m.group(1) or "").strip()
    return None


# =====================================================================
# Injury / recovery tracker (v4.35) - reuses training_log.json
# =====================================================================
def log_injury(text, lang="en"):
    """Append an injury entry to training_log.json (injuries list)."""
    if not text or not text.strip():
        return ("איזו פציעה לרשום, אדוני?" if lang == "he"
                else "What injury should I log, sir?")
    data = _load_training_log()
    injuries = data.setdefault("injuries", [])
    injuries.append({
        "desc": text.strip(),
        "logged": datetime.date.today().isoformat(),
        "status": "active",
        "recovered": None,
    })
    _save_training_log(data)
    if lang == "he":
        return "רשמתי את הפציעה, אדוני: %s. תנוח." % text.strip()
    return "Injury logged, sir: %s. Rest up." % text.strip()


def injury_status(lang="en"):
    """Report active injuries with relative dates."""
    data = _load_training_log()
    injuries = data.get("injuries", [])
    active = [i for i in injuries if i.get("status") == "active"]
    if not active:
        return ("אין פציעות פעילות, אדוני. הכל תקין." if lang == "he"
                else "No active injuries, sir. All clear.")
    lines = []
    for inj in active:
        try:
            d = datetime.date.fromisoformat(inj.get("logged", ""))
            days = (datetime.date.today() - d).days
            if lang == "he":
                rel = ("היום" if days == 0 else "אתמול" if days == 1
                       else "לפני %d ימים" % days)
            else:
                rel = ("today" if days == 0 else "yesterday" if days == 1
                       else "%d days ago" % days)
        except Exception:
            rel = ""
        desc = inj.get("desc", "?")
        lines.append(("%s (%s)" % (desc, rel)) if rel else desc)
    facts = "; ".join(lines)
    if lang == "he":
        return "פציעות פעילות, אדוני: " + facts
    return "Active injuries, sir: " + facts


def mark_recovered(keyword, lang="en"):
    """Mark a matching active injury as recovered. If exactly one is
    active, a keyword isn't required."""
    data = _load_training_log()
    injuries = data.get("injuries", [])
    kw = (keyword or "").strip().lower()
    matched = None
    if kw:
        for inj in injuries:
            if (inj.get("status") == "active"
                    and kw in inj.get("desc", "").lower()):
                matched = inj
                break
    if matched is None:
        active = [i for i in injuries if i.get("status") == "active"]
        if len(active) == 1:
            matched = active[0]
    if matched is None:
        return ("לא מצאתי פציעה פעילה שמתאימה, אדוני." if lang == "he"
                else "I couldn't find a matching active injury, sir.")
    matched["status"] = "recovered"
    matched["recovered"] = datetime.date.today().isoformat()
    _save_training_log(data)
    desc = matched.get("desc", "")
    if lang == "he":
        return "מצוין, אדוני. סימנתי כהחלים: " + desc
    return "Great, sir. Marked as recovered: " + desc


def _injury_log_parse(msg):
    """'log injury: X' / 'I hurt my X' / 'תרשום פציעה X' -> X, else None."""
    if not msg or not isinstance(msg, str):
        return None
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip()
    m = re.match(r"(?:log|record|note)\s+(?:an?\s+)?injury[:\-\s]+(.+)$",
                 text, re.I)
    if m:
        return m.group(1).strip()
    m = re.match(r"i\s+(?:hurt|injured|strained|pulled|tweaked)\s+"
                 r"(?:my\s+)?(.+)$", text, re.I)
    if m:
        return m.group(1).strip()
    m = re.match(r"(?:\u05ea\u05e8\u05e9\u05d5\u05dd|\u05e8\u05e9\u05d5\u05dd|\u05ea\u05e2\u05d3)\s+"
                 r"(?:\u05dc\u05d9\s+)?(?:\u05d0\u05ea\s+)?\u05e4\u05e6\u05d9\u05e2\u05d4[:\-\s]+(.+)$", text)
    if m:
        return m.group(1).strip()
    m = re.match(r"\u05e0\u05e4\u05e6\u05e2\u05ea\u05d9\s+(?:\u05d1|\u05d1\u05d0\u05d6\u05d5\u05e8\s+)?(.+)$", text)
    if m:
        return m.group(1).strip()
    return None


def _injury_recovered_parse(msg):
    """'injury recovered: X' / 'my X has healed' / 'החלמתי מX' -> X."""
    if not msg or not isinstance(msg, str):
        return None
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip().rstrip(".!?,")
    m = re.match(r"(?:injury\s+recovered|recovered\s+from|healed\s+from)"
                 r"[:\-\s]+(.+)$", text, re.I)
    if m:
        return m.group(1).strip()
    # v4.67: require a "my <body-part>" shape so generic sentences like
    # "everything is better" / "the weather is better" don't falsely clear an
    # injury (mark_recovered would otherwise fall back to the single active one).
    m = re.match(r"my\s+([\w' ]{1,20}?)\s+(?:has\s+|is\s+)?(?:healed|recovered|"
                 r"better)$", text, re.I)
    if m and len(m.group(1).split()) <= 3:
        return m.group(1).strip()
    m = re.match(r"(?:\u05d4\u05d7\u05dc\u05de\u05ea\u05d9|\u05e0\u05e8\u05e4\u05d0\u05ea\u05d9)\s+"
                 r"(?:\u05de\u05d4|\u05de)?(.+)$", text)
    if m:
        return m.group(1).strip()
    return None


def _injury_status_intercept(msg):
    """True if the user is asking about injury status."""
    if not msg or not isinstance(msg, str):
        return False
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip().rstrip(".!?,")
    low = text.lower()
    en_triggers = {
        "injury status", "injuries", "my injuries",
        "am i injured", "injury report", "any injuries",
        "what injuries", "current injuries", "injury check",
    }
    if low in en_triggers:
        return True
    he_triggers = {
        "\u05de\u05e6\u05d1 \u05e4\u05e6\u05d9\u05e2\u05d5\u05ea",
        "\u05e4\u05e6\u05d9\u05e2\u05d5\u05ea",
        "\u05d4\u05e4\u05e6\u05d9\u05e2\u05d5\u05ea \u05e9\u05dc\u05d9",
        "\u05de\u05d4 \u05d4\u05e4\u05e6\u05d9\u05e2\u05d5\u05ea",
        "\u05d9\u05e9 \u05dc\u05d9 \u05e4\u05e6\u05d9\u05e2\u05d5\u05ea",
        "\u05d3\u05d5\u05d7 \u05e4\u05e6\u05d9\u05e2\u05d5\u05ea",
    }
    if text in he_triggers:
        return True
    return False


# =====================================================================
# Workout logging (v4.36) - combat fitness coach, brick 1
# reuses training_log.json + updates v4.28 briefing fields
# =====================================================================
def _classify_workout(text):
    """Return a coarse workout type from keywords. Hebrew keywords use
    plain substring; English uses word boundaries so 'ran' does not match
    inside 'random' / 'brand' / 'France'."""
    low = (text or "").lower()
    he_swim = ["\u05e9\u05d7\u05d9\u05ea\u05d9", "\u05e9\u05d7\u05d9\u05d9\u05d4", "\u05e9\u05d7\u05d9\u05d4"]
    he_cardio = ["\u05e8\u05e6\u05ea\u05d9", "\u05e8\u05d9\u05e6\u05d4", "\u05e8\u05e5", "\u05d0\u05d5\u05e4\u05e0\u05d9\u05d9\u05dd",
                 "\u05e7\u05e8\u05d3\u05d9\u05d5", "\u05e1\u05e4\u05e8\u05d9\u05e0\u05d8"]
    he_strength = ["\u05e1\u05e7\u05d5\u05d5\u05d0\u05d8", "\u05dc\u05d7\u05d9\u05e6\u05d4", "\u05d3\u05d3\u05dc\u05d9\u05e4\u05d8",
                   "\u05de\u05e9\u05e7\u05d5\u05dc\u05d5\u05ea", "\u05db\u05d5\u05d7", "\u05e1\u05d8\u05d9\u05dd", "\u05d7\u05d6\u05e8\u05d5\u05ea",
                   "\u05de\u05ea\u05d7", "\u05e9\u05db\u05d9\u05d1\u05d5\u05ea", "\u05e7\u05d9\u05dc\u05d5", "\u05e8\u05d2\u05dc\u05d9\u05d9\u05dd",
                   "\u05d7\u05d6\u05d4", "\u05d2\u05d1", "\u05db\u05ea\u05e4\u05d9\u05d9\u05dd", "\u05d9\u05d3\u05d9\u05d9\u05dd", "\u05d1\u05d8\u05df",
                   "\u05d1\u05d9\u05e6\u05e4\u05e1", "\u05d8\u05e8\u05d9\u05e6\u05e4\u05e1"]
    en_swim = ["swim", "swam", "swimming"]
    en_cardio = ["run", "running", "ran", "jog", "jogging", "jogged",
                 "cardio", "cycle", "cycling", "bike", "biked", "row",
                 "rowing", "sprint", "sprinted", "treadmill", "5k", "10k"]
    en_strength = ["squat", "squats", "bench", "deadlift", "press", "lift",
                   "lifted", "lifting", "sets", "set", "reps", "rep", "kg",
                   "pullup", "pull-up", "pull up", "pullups", "pushup",
                   "push-up", "push up", "pushups", "curl", "curls", "ohp",
                   "chest", "back", "legs", "leg", "shoulders", "arms",
                   "biceps", "triceps", "glutes", "abs", "quads",
                   "hamstrings", "calves", "upper body", "lower body"]
    for kw in he_swim:
        if kw in low:
            return "swim"
    for kw in he_cardio:
        if kw in low:
            return "cardio"
    for kw in he_strength:
        if kw in low:
            return "strength"

    def _has(kw):
        return re.search(r"\b" + re.escape(kw) + r"\b", low) is not None

    for kw in en_swim:
        if _has(kw):
            return "swim"
    for kw in en_cardio:
        if _has(kw):
            return "cardio"
    for kw in en_strength:
        if _has(kw):
            return "strength"
    return "general"


def _iso_week_tag(d=None):
    d = d or datetime.date.today()
    iso = d.isocalendar()
    return "%d-W%02d" % (iso[0], iso[1])


def log_workout(text, lang="en"):
    """Append a workout and refresh v4.28 briefing fields."""
    if not text or not text.strip():
        return ("איזה אימון לרשום, אדוני?" if lang == "he"
                else "What workout should I log, sir?")
    data = _load_training_log()
    workouts = data.setdefault("workouts", [])
    today = datetime.date.today().isoformat()
    wtype = _classify_workout(text)
    workouts.append({"desc": text.strip(), "type": wtype, "date": today})
    # fields the v4.28 briefing reads
    data["last_workout_type"] = wtype
    data["last_workout_date"] = today
    wk = _iso_week_tag()
    if data.get("workout_week") != wk:
        data["workout_week"] = wk
        data["weekly_workouts"] = 0
    try:
        data["weekly_workouts"] = int(data.get("weekly_workouts", 0)) + 1
    except Exception:
        data["weekly_workouts"] = 1
    _save_training_log(data)
    n = data["weekly_workouts"]
    if lang == "he":
        return "נרשם, אדוני: %s. זה אימון מספר %d השבוע." % (text.strip(), n)
    return "Logged, sir: %s. That's workout #%d this week." % (text.strip(), n)


def recent_workouts(lang="en"):
    """Report this week's count and the last 5 workouts."""
    data = _load_training_log()
    workouts = data.get("workouts", [])
    if not workouts:
        return ("עדיין לא תיעדת אימונים, אדוני." if lang == "he"
                else "No workouts logged yet, sir.")
    wk = _iso_week_tag()
    week_count = 0
    if data.get("workout_week") == wk:
        try:
            week_count = int(data.get("weekly_workouts", 0))
        except Exception:
            week_count = 0
    type_he = {"cardio": "\u05e7\u05e8\u05d3\u05d9\u05d5", "swim": "\u05e9\u05d7\u05d9\u05d9\u05d4",
               "strength": "\u05db\u05d5\u05d7", "general": "\u05db\u05dc\u05dc\u05d9"}
    last5 = workouts[-5:][::-1]
    lines = []
    for w in last5:
        try:
            d = datetime.date.fromisoformat(w.get("date", ""))
            days = (datetime.date.today() - d).days
            if lang == "he":
                rel = ("היום" if days == 0 else "אתמול" if days == 1
                       else "לפני %d ימים" % days)
            else:
                rel = ("today" if days == 0 else "yesterday" if days == 1
                       else "%d days ago" % days)
        except Exception:
            rel = ""
        desc = w.get("desc", "?")
        t = w.get("type", "")
        if lang == "he":
            tlabel = type_he.get(t, t)
            lines.append("%s [%s] (%s)" % (desc, tlabel, rel) if rel
                         else "%s [%s]" % (desc, tlabel))
        else:
            lines.append("%s [%s] (%s)" % (desc, t, rel) if rel
                         else "%s [%s]" % (desc, t))
    body = "; ".join(lines)
    if lang == "he":
        return "השבוע: %d אימונים, אדוני. אחרונים: %s" % (week_count, body)
    return "This week: %d workouts, sir. Recent: %s" % (week_count, body)


# v4.67: a bare cardio verb ("ran"/"swam"/"רצתי"...) only counts as a workout
# when it carries workout context (a number, distance/time unit, or gym noun) -
# so "I ran the tests" / "רצתי לחנות" are NOT logged as workouts.
_WORKOUT_CTX = re.compile(
    r"\d|\bkm\b|\bk\b|\bmiles?\b|\bmin(?:ute)?s?\b|\bhours?\b|\breps?\b|"
    r"\bsets?\b|\blaps?\b|\bkg\b|\bmarathon\b|\btreadmill\b|\bpool\b|\bgym\b|"
    r"ק\"?מ|מטר|דקות|חזרות|סטים|קילומטר|בריכה|מרתון|הקפות",
    re.IGNORECASE)

def _workout_log_parse(msg):
    """'log workout: X' / 'I trained X' / 'I ran X' / 'תרשום אימון X' /
    'רצתי X' -> the workout description, else None."""
    if not msg or not isinstance(msg, str):
        return None
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip()
    # explicit "log workout: X"
    m = re.match(r"(?:log|record|add)\s+(?:a\s+)?workout[:\-\s]+(.+)$",
                 text, re.I)
    if m:
        return m.group(1).strip()
    # "I did a workout: ..." / "I did my workout ..."
    m = re.match(r"i\s+(?:did|completed|finished)\s+(?:a\s+|my\s+)?"
                 r"workout\b[:\-\s]*(.*)$", text, re.I)
    if m:
        rest = m.group(1).strip()
        return rest if rest else "workout"
    # "I trained X" / "I worked out (X)"
    m = re.match(r"i\s+trained\s+(.+)$", text, re.I)
    if m:
        return "trained " + m.group(1).strip()
    m = re.match(r"i\s+worked\s+out\b[:\-\s]*(.*)$", text, re.I)
    if m:
        rest = m.group(1).strip()
        return ("worked out " + rest) if rest else "worked out"
    # cardio/strength verbs: "I ran 5k", "ran 5k", "I swam 1000m", "I lifted"
    m = re.match(r"i\s+(ran|swam|lifted|rowed|cycled|biked|sprinted|jogged)"
                 r"\b\s*(.*)$", text, re.I)
    if m and _WORKOUT_CTX.search(m.group(2)):
        return (m.group(1) + " " + m.group(2)).strip()
    m = re.match(r"(ran|swam|jogged|sprinted)\b\s+(.+)$", text, re.I)
    if m and _WORKOUT_CTX.search(m.group(2)):
        return (m.group(1) + " " + m.group(2)).strip()
    # Hebrew explicit
    m = re.match(r"(?:\u05ea\u05e8\u05e9\u05d5\u05dd|\u05e8\u05e9\u05d5\u05dd|\u05ea\u05e2\u05d3)\s+"
                 r"(?:\u05dc\u05d9\s+)?(?:\u05d0\u05ea\s+)?\u05d0\u05d9\u05de\u05d5\u05df[:\-\s]+(.+)$", text)
    if m:
        return m.group(1).strip()
    # Hebrew verbs: 'אימנתי X', 'התאמנתי X', 'רצתי X', 'שחיתי X', 'עשיתי אימון X'
    m = re.match(r"(?:\u05d0\u05d9\u05de\u05e0\u05ea\u05d9|\u05d4\u05ea\u05d0\u05de\u05e0\u05ea\u05d9)\s+(.+)$", text)
    if m:
        return m.group(1).strip()
    m = re.match(r"(?:\u05e8\u05e6\u05ea\u05d9|\u05e9\u05d7\u05d9\u05ea\u05d9)\s+(.+)$", text)
    if m and _WORKOUT_CTX.search(m.group(1)):
        return (text).strip()
    m = re.match(r"\u05e2\u05e9\u05d9\u05ea\u05d9\s+\u05d0\u05d9\u05de\u05d5\u05df\b[:\-\s]*(.*)$", text)
    if m:
        rest = m.group(1).strip()
        return ("\u05d0\u05d9\u05de\u05d5\u05df " + rest) if rest else "\u05d0\u05d9\u05de\u05d5\u05df"
    return None


def _workout_status_intercept(msg):
    """True if the user is asking about workout history/status."""
    if not msg or not isinstance(msg, str):
        return False
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip().rstrip(".!?,")
    low = text.lower()
    en_triggers = {
        "workout status", "my workouts", "recent workouts",
        "what did i train this week", "what have i trained this week",
        "workouts this week", "training this week", "workout report",
        "how many workouts this week", "my training",
    }
    if low in en_triggers:
        return True
    he_triggers = {
        "\u05de\u05e6\u05d1 \u05d0\u05d9\u05de\u05d5\u05e0\u05d9\u05dd",
        "\u05d4\u05d0\u05d9\u05de\u05d5\u05e0\u05d9\u05dd \u05e9\u05dc\u05d9",
        "\u05de\u05d4 \u05d0\u05d9\u05de\u05e0\u05ea\u05d9 \u05d4\u05e9\u05d1\u05d5\u05e2",
        "\u05db\u05de\u05d4 \u05d0\u05d9\u05de\u05d5\u05e0\u05d9\u05dd \u05d4\u05e9\u05d1\u05d5\u05e2",
        "\u05d0\u05d9\u05de\u05d5\u05e0\u05d9\u05dd \u05d4\u05e9\u05d1\u05d5\u05e2",
        "\u05d3\u05d5\u05d7 \u05d0\u05d9\u05de\u05d5\u05e0\u05d9\u05dd",
    }
    if text in he_triggers:
        return True
    return False


# =====================================================================
# Fitness benchmarks & progress (v4.37) - combat coach brick 2
# structured test results + progress vs EDITABLE targets in
# training_log.json["standards"]. Reuses v4.33 _load/_save_training_log.
# =====================================================================
_FITNESS_METRICS = {
    "run_2km":   {"unit": "sec",   "default": 480, "lower_better": True,
                  "label_en": "2km run",   "label_he": "\u05e8\u05d9\u05e6\u05ea 2 \u05e7\"\u05de"},
    "run_3km":   {"unit": "sec",   "default": 750, "lower_better": True,
                  "label_en": "3km run",   "label_he": "\u05e8\u05d9\u05e6\u05ea 3 \u05e7\"\u05de"},
    "pullups":   {"unit": "count", "default": 15,  "lower_better": False,
                  "label_en": "pull-ups",  "label_he": "\u05de\u05ea\u05d7"},
    "pushups":   {"unit": "count", "default": 60,  "lower_better": False,
                  "label_en": "push-ups",  "label_he": "\u05e9\u05db\u05d9\u05d1\u05d5\u05ea \u05e1\u05de\u05d9\u05db\u05d4"},
    "situps":    {"unit": "count", "default": 70,  "lower_better": False,
                  "label_en": "sit-ups",   "label_he": "\u05db\u05e4\u05d9\u05e4\u05d5\u05ea \u05d1\u05d8\u05df"},
    "swim_400m": {"unit": "sec",   "default": 480, "lower_better": True,
                  "label_en": "400m swim", "label_he": "\u05e9\u05d7\u05d9\u05d9\u05ea 400 \u05de'"},
}
# Order for reporting
_FITNESS_ORDER = ["run_2km", "run_3km", "pullups", "pushups", "situps",
                  "swim_400m"]


def _fmt_metric_value(key, val):
    """sec -> mm:ss, count -> integer string."""
    meta = _FITNESS_METRICS.get(key, {})
    if meta.get("unit") == "sec":
        try:
            v = int(round(float(val)))
            return "%d:%02d" % (v // 60, v % 60)
        except Exception:
            return str(val)
    try:
        return str(int(round(float(val))))
    except Exception:
        return str(val)


def _parse_mmss_to_sec(text):
    """'8:45' -> 525. Returns int seconds or None."""
    m = re.search(r"(\d{1,2}):(\d{2})", text or "")
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return None


def _fitness_label(key, lang):
    meta = _FITNESS_METRICS.get(key, {})
    return meta.get("label_he" if lang == "he" else "label_en", key)


def _get_target(data, key):
    std = data.get("standards", {}) or {}
    if key in std:
        return std[key]
    return _FITNESS_METRICS[key]["default"]


def _detect_fitness_metric(text):
    """Return a metric key from keywords in text, else None."""
    low = (text or "").lower()
    # runs need a distance marker
    if re.search(r"\b3\s*k(?:m)?\b", low) or "\u05e8\u05d9\u05e6\u05ea 3" in low or "3 \u05e7\u05de" in low or "3 \u05e7\"\u05de" in low:
        return "run_3km"
    if re.search(r"\b2\s*k(?:m)?\b", low) or "\u05e8\u05d9\u05e6\u05ea 2" in low or "2 \u05e7\u05de" in low or "2 \u05e7\"\u05de" in low:
        return "run_2km"
    if "pull" in low or "\u05de\u05ea\u05d7" in low:
        return "pullups"
    if "push" in low or "\u05e9\u05db\u05d9\u05d1\u05d5\u05ea" in low:
        return "pushups"
    if "situp" in low or "sit-up" in low or "sit up" in low or "\u05d1\u05d8\u05df" in low or "\u05db\u05e4\u05d9\u05e4\u05d5\u05ea" in low:
        return "situps"
    if "swim" in low or "\u05e9\u05d7\u05d9\u05d9\u05d4" in low or "\u05e9\u05d7\u05d9\u05d4" in low or "\u05e9\u05d7\u05d9\u05d9\u05ea" in low:
        return "swim_400m"
    # bare 'run' with a time -> assume 2km
    if ("run" in low or "\u05e8\u05d9\u05e6\u05d4" in low or "\u05e8\u05e6\u05ea\u05d9" in low) and _parse_mmss_to_sec(low) is not None:
        return "run_2km"
    return None


def _fitness_test_parse(msg):
    """Parse a test-log command. Returns (metric_key, value) or None.
    value is seconds for time metrics, an int count otherwise."""
    if not msg or not isinstance(msg, str):
        return None
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip()
    # require an explicit log/record verb so questions don't fire
    m = re.match(r"(?:log|record|add)\s+(?:a\s+|my\s+)?(?:fitness\s+)?"
                 r"(?:test|result)?[:\-\s]*(.+)$", text, re.I)
    if m:
        body = m.group(1).strip()
    else:
        mh = re.match(r"(?:\u05ea\u05e8\u05e9\u05d5\u05dd|\u05e8\u05e9\u05d5\u05dd|\u05ea\u05e2\u05d3)\s+"
                      r"(?:\u05dc\u05d9\s+)?(?:\u05d0\u05ea\s+)?(?:\u05de\u05d1\u05d3\u05e7|\u05ea\u05d5\u05e6\u05d0\u05d4)?[:\-\s]*(.+)$",
                      text)
        if mh:
            body = mh.group(1).strip()
        else:
            return None
    key = _detect_fitness_metric(body)
    if key is None:
        return None
    unit = _FITNESS_METRICS[key]["unit"]
    if unit == "sec":
        sec = _parse_mmss_to_sec(body)
        if sec is None:
            return None
        return (key, sec)
    nums = re.findall(r"\d{1,3}", body)
    # drop distance markers like the '2'/'3' in 2k/3k and '400' for swim
    nums = [n for n in nums if n not in ("2", "3", "400") or len(nums) == 1]
    if not nums:
        return None
    return (key, int(nums[-1]))


def log_fitness_test(parsed, lang="en"):
    key, value = parsed
    data = _load_training_log()
    tests = data.setdefault("fitness_tests", [])
    tests.append({"metric": key, "value": value,
                  "date": datetime.date.today().isoformat()})
    _save_training_log(data)
    target = _get_target(data, key)
    disp = _fmt_metric_value(key, value)
    tdisp = _fmt_metric_value(key, target)
    label = _fitness_label(key, lang)
    lower = _FITNESS_METRICS[key]["lower_better"]
    met = (value <= target) if lower else (value >= target)
    if lang == "he":
        verdict = "\u05e2\u05d1\u05e8\u05ea \u05d0\u05ea \u05d4\u05d9\u05e2\u05d3! \ud83d\udd25" if met else ("\u05d4\u05d9\u05e2\u05d3: " + tdisp)
        return "\u05e0\u05e8\u05e9\u05dd, \u05d0\u05d3\u05d5\u05e0\u05d9: %s %s. %s" % (label, disp, verdict)
    verdict = "Target beaten! \ud83d\udd25" if met else ("Target: " + tdisp)
    return "Logged, sir: %s %s. %s" % (label, disp, verdict)


def _set_target_parse(msg):
    """'set target pullups 20' / 'יעד מתח 20' -> (key, value) or None."""
    if not msg or not isinstance(msg, str):
        return None
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = text.strip()
    m = re.match(r"(?:set\s+)?(?:target|goal|standard)[:\-\s]+(.+)$",
                 text, re.I)
    if not m:
        mh = re.match(r"(?:\u05d9\u05e2\u05d3|\u05ea\u05e7\u05df)[:\-\s]+(.+)$", text)
        if not mh:
            return None
        body = mh.group(1).strip()
    else:
        body = m.group(1).strip()
    key = _detect_fitness_metric(body)
    if key is None:
        return None
    unit = _FITNESS_METRICS[key]["unit"]
    if unit == "sec":
        sec = _parse_mmss_to_sec(body)
        if sec is None:
            return None
        return (key, sec)
    nums = [n for n in re.findall(r"\d{1,3}", body)
            if n not in ("2", "3", "400")]
    if not nums:
        return None
    return (key, int(nums[-1]))


def set_fitness_target(parsed, lang="en"):
    key, value = parsed
    data = _load_training_log()
    std = data.setdefault("standards", {})
    std[key] = value
    _save_training_log(data)
    label = _fitness_label(key, lang)
    disp = _fmt_metric_value(key, value)
    if lang == "he":
        return "\u05d4\u05d9\u05e2\u05d3 \u05dc%s \u05e2\u05d5\u05d3\u05db\u05df \u05dc-%s, \u05d0\u05d3\u05d5\u05e0\u05d9." % (label, disp)
    return "Target for %s set to %s, sir." % (label, disp)


def fitness_progress(lang="en"):
    data = _load_training_log()
    tests = data.get("fitness_tests", [])
    lines = []
    for key in _FITNESS_ORDER:
        meta = _FITNESS_METRICS[key]
        label = _fitness_label(key, lang)
        target = _get_target(data, key)
        tdisp = _fmt_metric_value(key, target)
        mine = [t for t in tests if t.get("metric") == key]
        if not mine:
            if lang == "he":
                lines.append("%s: \u05d8\u05e8\u05dd \u05e0\u05d1\u05d3\u05e7 (\u05d9\u05e2\u05d3 %s)" % (label, tdisp))
            else:
                lines.append("%s: not tested yet (target %s)" % (label, tdisp))
            continue
        latest = mine[-1]
        lval = latest.get("value")
        ldisp = _fmt_metric_value(key, lval)
        lower = meta["lower_better"]
        met = (lval <= target) if lower else (lval >= target)
        # delta vs previous test
        deltastr = ""
        if len(mine) > 1:
            pval = mine[-2].get("value")
            if meta["unit"] == "sec":
                diff = pval - lval  # positive = faster now
                if diff != 0:
                    sgn = "-" if diff > 0 else "+"
                    deltastr = (" (%s%ss \u05de\u05d4\u05e4\u05e2\u05dd \u05d4\u05e7\u05d5\u05d3\u05de\u05ea)" if lang == "he"
                                else " (%s%ss vs last)") % (sgn, abs(int(diff)))
            else:
                diff = lval - pval  # positive = more reps now
                if diff != 0:
                    sgn = "+" if diff > 0 else "-"
                    deltastr = (" (%s%d \u05de\u05d4\u05e4\u05e2\u05dd \u05d4\u05e7\u05d5\u05d3\u05de\u05ea)" if lang == "he"
                                else " (%s%d vs last)") % (sgn, abs(int(diff)))
        if lang == "he":
            mark = "\u2705" if met else "\u25cb"
            lines.append("%s %s: %s / \u05d9\u05e2\u05d3 %s%s" % (mark, label, ldisp, tdisp, deltastr))
        else:
            mark = "\u2705" if met else "\u25cb"
            lines.append("%s %s: %s / target %s%s" % (mark, label, ldisp, tdisp, deltastr))
    if lang == "he":
        return "\u05de\u05e6\u05d1 \u05db\u05d5\u05e9\u05e8, \u05d0\u05d3\u05d5\u05e0\u05d9:\n" + "\n".join(lines)
    return "Fitness progress, sir:\n" + "\n".join(lines)


def _fitness_progress_intercept(msg):
    if not msg or not isinstance(msg, str):
        return False
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip().rstrip(".!?,")
    low = text.lower()
    en = {"progress", "fitness progress", "where do i stand",
          "how am i doing", "fitness status", "my progress",
          "am i ready", "standards"}
    if low in en:
        return True
    he = {"\u05de\u05e6\u05d1 \u05db\u05d5\u05e9\u05e8", "\u05d0\u05d9\u05e4\u05d4 \u05d0\u05e0\u05d9 \u05e2\u05d5\u05de\u05d3", "\u05d4\u05ea\u05e7\u05d3\u05de\u05d5\u05ea",
          "\u05db\u05d5\u05e9\u05e8", "\u05d4\u05ea\u05e7\u05d3\u05de\u05d5\u05ea \u05e9\u05dc\u05d9", "\u05d0\u05e0\u05d9 \u05de\u05d5\u05db\u05df"}
    if text in he:
        return True
    return False


# =====================================================================
# Weekly training summary (v4.38) - combat coach brick 3 (read-only)
# =====================================================================
def _this_iso_week(d=None):
    d = d or datetime.date.today()
    return d.isocalendar()[:2]


def weekly_summary(lang="en"):
    data = _load_training_log()
    today = datetime.date.today()
    wk = _this_iso_week(today)
    parts = []

    # --- workouts this week ---
    workouts = data.get("workouts", [])
    wk_workouts = []
    for w in workouts:
        try:
            d = datetime.date.fromisoformat(w.get("date", ""))
            if d.isocalendar()[:2] == wk:
                wk_workouts.append(w)
        except Exception:
            pass
    type_he = {"cardio": "\u05e7\u05e8\u05d3\u05d9\u05d5", "swim": "\u05e9\u05d7\u05d9\u05d9\u05d4",
               "strength": "\u05db\u05d5\u05d7", "general": "\u05db\u05dc\u05dc\u05d9"}
    counts = {}
    for w in wk_workouts:
        t = w.get("type", "general")
        counts[t] = counts.get(t, 0) + 1
    if wk_workouts:
        if lang == "he":
            bd = ", ".join("%d %s" % (n, type_he.get(t, t))
                           for t, n in sorted(counts.items()))
            parts.append("\u05d0\u05d9\u05de\u05d5\u05e0\u05d9\u05dd: %d (%s)" % (len(wk_workouts), bd))
        else:
            bd = ", ".join("%d %s" % (n, t) for t, n in sorted(counts.items()))
            parts.append("Workouts: %d (%s)" % (len(wk_workouts), bd))
    else:
        parts.append("\u05d0\u05d9\u05de\u05d5\u05e0\u05d9\u05dd: 0 \u05d4\u05e9\u05d1\u05d5\u05e2" if lang == "he"
                     else "Workouts: 0 this week")

    # --- weight vs red-line ---
    w_kg = data.get("last_weight_kg")
    if w_kg is not None:
        try:
            w_min = float(data.get("weight_target_min_kg", 68))
        except Exception:
            w_min = 68.0
        try:
            w_val = float(w_kg)
            wdate = data.get("last_weight_date", "")
            if w_val < w_min:
                tag = ("\u05de\u05ea\u05d7\u05ea \u05dc\u05e7\u05d5 \u05d4\u05d0\u05d3\u05d5\u05dd!" if lang == "he" else "BELOW red-line!")
            elif w_val <= w_min + 1:
                tag = ("\u05e7\u05e8\u05d5\u05d1 \u05dc\u05e7\u05d5 \u05d4\u05d0\u05d3\u05d5\u05dd" if lang == "he" else "near red-line")
            else:
                tag = ("\u05d8\u05d5\u05d1" if lang == "he" else "ok")
            if lang == "he":
                parts.append("\u05de\u05e9\u05e7\u05dc: %.1f \u05e7\"\u05d2 (\u05e7\u05d5 \u05d0\u05d3\u05d5\u05dd %.0f - %s)" % (w_val, w_min, tag))
            else:
                parts.append("Weight: %.1f kg (red-line %.0f - %s)" % (w_val, w_min, tag))
        except Exception:
            pass

    # --- nutrition (daily) ---
    if data.get("nutrition_date") == today.isoformat():
        cal = data.get("calories_today", 0)
        prot = data.get("protein_today", 0)
        tcal = data.get("target_calories", 3000)
        tprot = data.get("target_protein_g", 130)
        if lang == "he":
            parts.append("\u05ea\u05d6\u05d5\u05e0\u05d4 \u05d4\u05d9\u05d5\u05dd: %s/%s \u05e7\u05dc\u05d5\u05e8\u05d9\u05d5\u05ea, %s/%s\u05d2 \u05d7\u05dc\u05d1\u05d5\u05df" % (cal, tcal, prot, tprot))
        else:
            parts.append("Nutrition today: %s/%s kcal, %s/%s g protein" % (cal, tcal, prot, tprot))

    # --- injuries ---
    injuries = data.get("injuries", [])
    active = [i for i in injuries if i.get("status") == "active"]
    if active:
        names = "; ".join(i.get("desc", "?") for i in active)
        if lang == "he":
            parts.append("\u05e4\u05e6\u05d9\u05e2\u05d5\u05ea \u05e4\u05e2\u05d9\u05dc\u05d5\u05ea: %d (%s)" % (len(active), names))
        else:
            parts.append("Active injuries: %d (%s)" % (len(active), names))
    else:
        parts.append("\u05e4\u05e6\u05d9\u05e2\u05d5\u05ea: \u05d0\u05d9\u05df" if lang == "he" else "Injuries: none")

    # --- fitness pointer ---
    if data.get("fitness_tests"):
        parts.append("\u05d0\u05de\u05d5\u05e8 '\u05de\u05e6\u05d1 \u05db\u05d5\u05e9\u05e8' \u05dc\u05de\u05d3\u05d3\u05d9\u05dd" if lang == "he"
                     else "Say 'progress' for benchmark detail")

    header = "\u05e1\u05d9\u05db\u05d5\u05dd \u05e9\u05d1\u05d5\u05e2\u05d9, \u05d0\u05d3\u05d5\u05e0\u05d9:" if lang == "he" else "Weekly summary, sir:"
    return header + "\n" + "\n".join("- " + p for p in parts)


def _weekly_summary_intercept(msg):
    if not msg or not isinstance(msg, str):
        return False
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip().rstrip(".!?,")
    low = text.lower()
    en = {"weekly summary", "week summary", "my week", "week recap",
          "weekly recap", "summary of my week", "this week summary"}
    if low in en:
        return True
    he = {"\u05e1\u05d9\u05db\u05d5\u05dd \u05e9\u05d1\u05d5\u05e2\u05d9", "\u05e1\u05d9\u05db\u05d5\u05dd \u05d4\u05e9\u05d1\u05d5\u05e2",
          "\u05de\u05d4 \u05e2\u05e9\u05d9\u05ea\u05d9 \u05d4\u05e9\u05d1\u05d5\u05e2", "\u05e1\u05d9\u05db\u05d5\u05dd \u05e9\u05d1\u05d5\u05e2"}
    if text in he:
        return True
    return False


# =====================================================================
# Weight logging + 68kg red-line (v4.39) - combat coach brick 4
# sets last_weight_kg (which v4.28 briefing already warns on) + history.
# Reuses v4.33 _load/_save_training_log.
# =====================================================================
def _weight_log_parse(msg):
    """Parse a weight-log command -> float kg, else None.
    Requires a weight keyword plus a number; sane range 30-200 kg."""
    if not msg or not isinstance(msg, str):
        return None
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip()
    num = r"(\d{2,3}(?:\.\d{1,2})?)"
    pats = [
        r"(?:log|record|add)\s+(?:my\s+)?weight[:\-\s]+" + num,
        r"i\s+weigh(?:ed)?\s+" + num,
        r"(?:my\s+)?weight\s+(?:is\s+)?" + num + r"\s*(?:kg|kilo|kilos|kgs)?\b",
        r"(?:\u05ea\u05e8\u05e9\u05d5\u05dd|\u05e8\u05e9\u05d5\u05dd|\u05ea\u05e2\u05d3)\s+(?:\u05dc\u05d9\s+)?(?:\u05d0\u05ea\s+)?\u05de\u05e9\u05e7\u05dc[:\-\s]+" + num,
        r"\u05e9\u05e7\u05dc\u05ea\u05d9\s+" + num,
        r"(?:\u05d4?\u05de\u05e9\u05e7\u05dc\s+\u05e9\u05dc\u05d9|\u05d4\u05de\u05e9\u05e7\u05dc)\s+" + num,
    ]
    for p in pats:
        m = re.search(p, text, re.I)
        if m:
            try:
                v = float(m.group(1))
            except Exception:
                continue
            if 30.0 <= v <= 200.0:
                return v
    return None


def log_weight(val, lang="en"):
    data = _load_training_log()
    today = datetime.date.today().isoformat()
    weights = data.setdefault("weights", [])
    weights.append({"kg": val, "date": today})
    data["last_weight_kg"] = val
    data["last_weight_date"] = today
    _save_training_log(data)
    try:
        wmin = float(data.get("weight_target_min_kg", 68))
    except Exception:
        wmin = 68.0
    if val < wmin:
        tag = ("\u05de\u05ea\u05d7\u05ea \u05dc\u05e7\u05d5 \u05d4\u05d0\u05d3\u05d5\u05dd \u05e9\u05dc %g \u05e7\"\u05d2 - \u05ea\u05d0\u05db\u05dc, \u05d0\u05d3\u05d5\u05e0\u05d9." % wmin if lang == "he"
               else "below the %g kg red line - eat up, sir." % wmin)
    elif val <= wmin + 1:
        tag = ("\u05e7\u05e8\u05d5\u05d1 \u05dc\u05e7\u05d5 \u05d4\u05d0\u05d3\u05d5\u05dd \u05e9\u05dc %g \u05e7\"\u05d2." % wmin if lang == "he"
               else "close to the %g kg red line." % wmin)
    else:
        tag = ("\u05de\u05e2\u05dc \u05d4\u05e7\u05d5 \u05d4\u05d0\u05d3\u05d5\u05dd. \u05d8\u05d5\u05d1." if lang == "he"
               else "above the red line. Good.")
    if lang == "he":
        return "\u05e0\u05e8\u05e9\u05dd, \u05d0\u05d3\u05d5\u05e0\u05d9: %g \u05e7\"\u05d2 - %s" % (val, tag)
    return "Logged, sir: %g kg - %s" % (val, tag)


def weight_check(lang="en"):
    data = _load_training_log()
    w = data.get("last_weight_kg")
    if w is None:
        return ("\u05e2\u05d3\u05d9\u05d9\u05df \u05dc\u05d0 \u05ea\u05d9\u05e2\u05d3\u05ea \u05de\u05e9\u05e7\u05dc, \u05d0\u05d3\u05d5\u05e0\u05d9. \u05d0\u05de\u05d5\u05e8 '\u05ea\u05e8\u05e9\u05d5\u05dd \u05de\u05e9\u05e7\u05dc 70'." if lang == "he"
                else "No weight logged yet, sir. Say 'log weight 70'.")
    try:
        w = float(w)
        wmin = float(data.get("weight_target_min_kg", 68))
    except Exception:
        return ("\u05dc\u05d0 \u05d4\u05e6\u05dc\u05d7\u05ea\u05d9 \u05dc\u05e7\u05e8\u05d5\u05d0 \u05d0\u05ea \u05d4\u05de\u05e9\u05e7\u05dc, \u05d0\u05d3\u05d5\u05e0\u05d9." if lang == "he"
                else "Couldn't read the weight, sir.")
    # days since
    rel = ""
    wd = data.get("last_weight_date", "")
    try:
        d0 = datetime.date.fromisoformat(wd)
        days = (datetime.date.today() - d0).days
        if lang == "he":
            rel = ("\u05d4\u05d9\u05d5\u05dd" if days == 0 else "\u05d0\u05ea\u05de\u05d5\u05dc" if days == 1 else "\u05dc\u05e4\u05e0\u05d9 %d \u05d9\u05de\u05d9\u05dd" % days)
        else:
            rel = ("today" if days == 0 else "yesterday" if days == 1 else "%d days ago" % days)
    except Exception:
        rel = ""
    # trend vs previous weigh-in
    trend = ""
    weights = data.get("weights", [])
    if len(weights) > 1:
        try:
            prev = float(weights[-2].get("kg"))
            diff = w - prev
            if abs(diff) >= 0.05:
                if lang == "he":
                    verb = "\u05e2\u05dc\u05d9\u05ea" if diff > 0 else "\u05d9\u05e8\u05d3\u05ea"
                    trend = " %s %+.1f \u05e7\"\u05d2 \u05de\u05d4\u05e4\u05e2\u05dd \u05d4\u05e7\u05d5\u05d3\u05de\u05ea" % (verb, diff)
                else:
                    verb = "up" if diff > 0 else "down"
                    trend = " %s %+.1f kg vs last weigh-in" % (verb, diff)
        except Exception:
            pass
    if w < wmin:
        verdict = ("\u05de\u05ea\u05d7\u05ea \u05dc\u05e7\u05d5 \u05d4\u05d0\u05d3\u05d5\u05dd!" if lang == "he" else "BELOW the red line!")
    elif w <= wmin + 1:
        verdict = ("\u05e7\u05e8\u05d5\u05d1 \u05dc\u05e7\u05d5 \u05d4\u05d0\u05d3\u05d5\u05dd." if lang == "he" else "near the red line.")
    else:
        verdict = ("\u05de\u05e2\u05dc \u05d4\u05e7\u05d5 \u05d4\u05d0\u05d3\u05d5\u05dd. \u05d8\u05d5\u05d1." if lang == "he" else "above the red line. Good.")
    relpart = (" (%s)" % rel) if rel else ""
    if lang == "he":
        return "\u05de\u05e9\u05e7\u05dc \u05d0\u05d7\u05e8\u05d5\u05df: %g \u05e7\"\u05d2%s. \u05e7\u05d5 \u05d0\u05d3\u05d5\u05dd %g - %s%s" % (w, relpart, wmin, verdict, trend)
    return "Latest weight: %g kg%s. Red line %g - %s%s" % (w, relpart, wmin, verdict, trend)


def _weight_check_intercept(msg):
    if not msg or not isinstance(msg, str):
        return False
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:]*",
                  "", text, flags=re.I)
    text = re.sub(r"^\s*(\u05d4\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\u05d9\s+|\u05d0\u05d5\u05e7\u05d9\s+)?(\u05d2'?\u05d0?\u05e8?\u05d5?\u05d5?\u05d9\u05e1|g\u05d0\u05e8\u05d5\u05d5\u05d9\u05e1)[\s,:]*",
                  "", text)
    text = text.strip().rstrip(".!?,")
    low = text.lower()
    en = {"weight check", "my weight", "what is my weight",
          "what's my weight", "weight status", "am i above 68",
          "am i above the red line", "how much do i weigh",
          "current weight"}
    if low in en:
        return True
    he = {"\u05d1\u05d3\u05d9\u05e7\u05ea \u05de\u05e9\u05e7\u05dc", "\u05de\u05d4 \u05d4\u05de\u05e9\u05e7\u05dc", "\u05d4\u05de\u05e9\u05e7\u05dc \u05e9\u05dc\u05d9",
          "\u05db\u05de\u05d4 \u05d0\u05e0\u05d9 \u05e9\u05d5\u05e7\u05dc", "\u05de\u05d4 \u05d4\u05de\u05e9\u05e7\u05dc \u05e9\u05dc\u05d9", "\u05de\u05e9\u05e7\u05dc",
          "\u05db\u05de\u05d4 \u05d0\u05e0\u05d9 \u05e9\u05d5\u05e7\u05dc \u05e2\u05db\u05e9\u05d9\u05d5"}
    if text in he:
        return True
    return False


# =====================================================================
# IPv4-only outbound (v4.40) - fix httplib2 hang on broken-IPv6 paths
# =====================================================================
# httplib2 (used by googleapiclient for Calendar / Gmail) does not do
# Happy Eyeballs and hangs at TCP connect when www.googleapis.com
# resolves to an AAAA record but local IPv6 routing is broken. We
# filter AAAA results out of socket.getaddrinfo so every outbound
# TCP connection from this process uses IPv4. v4 already works for
# every API JARVIS uses (Anthropic, ElevenLabs, Maps, OpenWeather).
import socket as _v440_socket
if not getattr(_v440_socket, "_v440_ipv4_patched", False):
    _v440_orig_getaddrinfo = _v440_socket.getaddrinfo

    def _v440_ipv4_only_getaddrinfo(host, port, family=0, type=0,
                                    proto=0, flags=0):
        # v4.67: prefer IPv4 (local IPv6 to Google is broken here), but only
        # coerce AF_UNSPEC, honour an explicit family, and ALWAYS fall back to a
        # normal resolve if the IPv4-only lookup fails - so genuinely IPv6-only
        # hosts / explicit AF_INET6 callers still resolve instead of raising.
        fam = _v440_socket.AF_INET if family == 0 else family
        try:
            return _v440_orig_getaddrinfo(host, port, fam, type, proto, flags)
        except _v440_socket.gaierror:
            return _v440_orig_getaddrinfo(host, port, family, type, proto, flags)

    _v440_socket.getaddrinfo = _v440_ipv4_only_getaddrinfo
    _v440_socket._v440_ipv4_patched = True


# ---------------------------------------------------------------------------
# v4.43: Obsidian note search  ("JARVIS, what did I note about X")
# ---------------------------------------------------------------------------
def _obsidian_search_parse(msg):
    """v4.44: detect Obsidian search intent. Returns:
        None  -> no intent
        ""    -> list all notes (no topic given)
        str   -> search for that topic"""
    if not msg or not isinstance(msg, str):
        return None
    text = msg.strip()
    text = re.sub(r"^\s*(hey\s+|hi\s+|ok\s+|okay\s+)?jarvis[\s,:\-]*", "", text, flags=re.I)
    text = re.sub(r"^\s*(היי\s+|אוקיי\s+|אוקי\s+)?(ג[׳'`]?א?ר?ו+יס)[\s,:\-]*", "", text)
    text = text.strip().rstrip("?!.").strip()
    low = text.lower()

    # --- topicless intents (list all notes) ---
    listall_en = [
        r"^do i have (?:any )?notes$",
        r"^show (?:me )?(?:my )?notes$",
        r"^list (?:my )?notes$",
        r"^what notes do i have$",
        r"^what are my notes$",
        r"^my notes$",
        r"^all (?:my )?notes$",
    ]
    for p in listall_en:
        if re.search(p, low):
            return ""
    listall_he = [
        r"^מה הפתקים שלי$",
        r"^אילו פתקים יש לי$",
        r"^יש לי פתקים$",
        r"^הצג (?:לי )?(?:את )?הפתקים(?: שלי)?$",
        r"^הראה (?:לי )?(?:את )?הפתקים(?: שלי)?$",
        r"^רשימת פתקים$",
        r"^כל הפתקים(?: שלי)?$",
        r"^איזה פתקים יש לי$",
    ]
    for p in listall_he:
        if re.search(p, text):
            return ""

    # --- topic-search intents ---
    en_pats = [
        r"what did i (?:note|write|jot|record) (?:down )?about (.+)$",
        r"what do(?:es)? my notes? say about (.+)$",
        r"search (?:my )?(?:notes?|vault|memory) (?:for |about )?(.+)$",
        r"find (?:in )?(?:my )?notes? (?:about |for )?(.+)$",
        r"do i have (?:any )?notes? (?:on|about|regarding) (.+)$",
        r"any notes (?:on|about|regarding) (.+)$",
        r"show (?:me )?(?:my )?notes (?:on|about|regarding) (.+)$",
        r"list (?:my )?notes (?:on|about|regarding) (.+)$",
        r"look up (.+?) in my (?:notes?|vault)$",
    ]
    for p in en_pats:
        m = re.search(p, low)
        if m:
            return m.group(1).strip(" .?!,'\"")
    he_pats = [
        r"מה רשמתי (?:לעצמי )?על (.+)$",
        r"מה כתבתי (?:לעצמי )?על (.+)$",
        r"מה רשמתי בנושא (.+)$",
        r"מה כתבתי בנושא (.+)$",
        r"חפש (?:לי )?(?:בפתקים|בכספת|בזיכרון) (?:על |בנושא )?(.+)$",
        r"תחפש (?:לי )?(?:בפתקים|בכספת|בזיכרון) (?:על |בנושא )?(.+)$",
        r"מה יש לי (?:רשום )?(?:על |בנושא )(.+)$",
        r"מה הפתקים (?:שלי )?אומרים על (.+)$",
        r"יש לי פתקים (?:על |בנושא |לגבי )(.+)$",
        r"יש לי משהו (?:רשום )?(?:על |בנושא |לגבי )(.+)$",
        r"הראה (?:לי )?(?:את )?הפתקים (?:שלי )?(?:על |בנושא |לגבי )(.+)$",
        r"הצג (?:לי )?(?:את )?הפתקים (?:שלי )?(?:על |בנושא |לגבי )(.+)$",
    ]
    for p in he_pats:
        m = re.search(p, text)
        if m:
            return m.group(1).strip(" .?!,'\"")
    return None


def search_obsidian(query, lang="en"):
    """Search every .md file under the Obsidian vault for `query` and return a
    short answer synthesised from what was found. Degrades gracefully."""
    if not query or not query.strip():
        return list_all_notes(lang)
    q = query.strip().lower()
    terms = _obsidian_or_split(q)
    vault = VAULT_DIR
    try:
        if not vault.exists():
            return ("אין עדיין כספת אובסידיאן, אדוני." if lang == "he"
                    else "There's no Obsidian vault yet, sir.")
    except Exception:
        return ("לא הצלחתי לגשת לכספת, אדוני." if lang == "he"
                else "I couldn't reach the vault, sir.")
    matches = []
    total = 0
    CAP = 4000
    try:
        for f in sorted(vault.rglob("*.md")):
            try:
                lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            hits = [i for i, ln in enumerate(lines) if any(tt in ln.lower() for tt in terms)]
            if not hits:
                continue
            keep = set()
            for i in hits:
                for j in range(max(0, i - 2), min(len(lines), i + 3)):
                    keep.add(j)
            ctx = "\n".join(lines[j] for j in sorted(keep) if lines[j].strip())
            try:
                label = f.relative_to(vault)
            except Exception:
                label = f.name
            snippet = "[%s]\n%s" % (label, ctx)
            matches.append(snippet)
            total += len(snippet)
            if total >= CAP:
                break
    except Exception:
        return ("שגיאה בחיפוש בפתקים, אדוני." if lang == "he"
                else "Error searching your notes, sir.")
    if not matches:
        return (("לא מצאתי כלום על '%s' בפתקים שלך, אדוני." % query) if lang == "he"
                else ("I couldn't find anything about '%s' in your notes, sir." % query))
    facts = ("\n\n".join(matches))[:CAP]
    if not ANTHROPIC_API_KEY:
        head = ("מצאתי את זה בפתקים, אדוני:\n" if lang == "he"
                else "Found this in your notes, sir:\n")
        return clean_text(head + facts)
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        sys_p = (
            "You are Achilles, a calm British-butler AI. The user searched their "
            "personal Obsidian notes. Below are the matching excerpts (each "
            "tagged with its [filename]). Answer what THEIR NOTES say about '"
            + query + "' in 2 to 4 short sentences, in "
            + ("Hebrew" if lang == "he" else "English")
            + ". Address them as " + ("אדוני" if lang == "he" else "sir")
            + ". Base the answer ONLY on the excerpts; if they are thin, say "
            "what little was found. Plain text, no markdown, no URLs.")
        r = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=400,
            system=sys_p,
            messages=[{"role": "user", "content": facts}])
        parts = [b.text for b in r.content if getattr(b, "type", None) == "text"]
        reply = " ".join(p.strip() for p in parts if p.strip()).strip()
        return clean_text(reply) or clean_text(facts)
    except Exception:
        return clean_text(facts)


# ---------------------------------------------------------------------------
# v4.43: personalised news section for the daily briefing (fully optional)
# ---------------------------------------------------------------------------
def _obsidian_or_split(q):
    """v4.44: split a query on ' or ' / ' או ' so multi-term searches like
    'sport or fitness' check each term independently."""
    parts = re.split(r"\s+(?:or|או)\s+", q)
    parts = [p.strip() for p in parts if p.strip()]
    return parts or [q]


def list_all_notes(lang="en"):
    """v4.44: short, fast list of every .md note in the Obsidian vault, sorted
    by most-recently-modified. No model call."""
    vault = VAULT_DIR
    try:
        if not vault.exists():
            return ("אין עדיין כספת אובסידיאן, אדוני." if lang == "he"
                    else "There's no Obsidian vault yet, sir.")
    except Exception:
        return ("לא הצלחתי לגשת לכספת, אדוני." if lang == "he"
                else "I couldn't reach the vault, sir.")
    try:
        files = sorted(vault.rglob("*.md"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        files = []
    if not files:
        return ("אין לך פתקים שמורים, אדוני." if lang == "he"
                else "You have no saved notes, sir.")
    LIMIT = 15
    shown = files[:LIMIT]
    lines = []
    for f in shown:
        try:
            label = f.relative_to(vault).as_posix()
        except Exception:
            label = f.name
        hint = ""
        try:
            for ln in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                s = ln.strip().lstrip("#").strip()
                if s:
                    hint = s[:60]
                    break
        except Exception:
            pass
        if hint:
            lines.append("%s — %s" % (label, hint))
        else:
            lines.append(str(label))
    extra = len(files) - len(shown)
    if lang == "he":
        head = "יש לך %d פתקים, אדוני. הנה האחרונים:\n" % len(files)
        tail = ("\nועוד %d." % extra) if extra > 0 else ""
    else:
        head = "You have %d notes, sir. The most recent:\n" % len(files)
        tail = ("\nAnd %d more." % extra) if extra > 0 else ""
    return clean_text(head + "\n".join(lines) + tail)


NEWS_INTERESTS = "artificial intelligence and technology, Israel, and major world news"

def _news_briefing_section(lang="en"):
    """Fetch 2-3 recent headlines relevant to NEWS_INTERESTS via Claude +
    web_search, for the daily briefing. Returns '' on ANY failure so the
    briefing never breaks because of the news."""
    if not ANTHROPIC_API_KEY:
        return ""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        interests = globals().get("NEWS_INTERESTS", "technology, Israel, world news")
        sys_p = (
            "You are a news desk. Use web_search to find 2 or 3 of the most "
            "important and RECENT headlines (prefer the last day or two) "
            "relevant to these interests: " + interests + ". Then output ONLY "
            "a compact plain-text list of those 2-3 headlines, one per line, "
            "each a short factual phrase. No URLs, no numbering, no commentary, "
            "no markdown. Write the headlines in "
            + ("Hebrew" if lang == "he" else "English") + ".")
        tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 2}]
        msgs = [{"role": "user", "content": "Today's headlines for my briefing, please."}]
        r = None
        for _ in range(4):
            r = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=500,
                system=sys_p, messages=msgs, tools=tools)
            msgs.append({"role": "assistant", "content": r.content})
            if getattr(r, "stop_reason", None) == "tool_use":
                continue
            break
        parts = [b.text for b in r.content if getattr(b, "type", None) == "text"]
        news = "\n".join(p.strip() for p in parts if p.strip()).strip()
        news = re.sub(r"https?://\S+", "", news)
        return clean_text(news).strip()
    except Exception as e:
        try:
            print("[diag] news section skipped:", repr(e))
        except Exception:
            pass
        return ""


def think(user_message, memory, lang=""):
    if not ANTHROPIC_API_KEY:
        return "[Error: Missing API Key in .env]"
    # v4.34: if a quiz is pending, this message is the user's answer.
    with _quiz_lock:
        _quiz_active = _quiz_state["active"]
    if _quiz_active:
        _fb = evaluate_quiz_answer(
            user_message,
            lang="he" if lang == "he" or is_hebrew(user_message) else "en")
        if _fb is not None:
            return _fb
    # Deterministic intercept: never let the model refuse a learning command.
    parsed = _learning_intercept(user_message)
    if parsed is not None:
        topic, depth = parsed
        if topic == "__STATUS__":
            return learning_status()
        if topic.startswith("__RESUME__:"):
            return resume_learning(topic[len("__RESUME__:"):])
        if depth == "deep":
            return deep_learn_domain(topic)
        else:
            return learn_topic(topic, "")
    if _whats_new_intercept(user_message):
        return whats_new("he" if lang == "he" or is_hebrew(user_message) else "en")
    if _system_health_intercept(user_message):
        return system_health("he" if lang == "he" or is_hebrew(user_message) else "en")
    if _learned_this_week_intercept(user_message):
        return learned_this_week("he" if lang == "he" or is_hebrew(user_message) else "en")
    if _undo_intercept(user_message):
        return undo_last()
    if _budget_intercept(user_message):
        return budget_status("he" if lang == "he" or is_hebrew(user_message) else "en")
    if _backup_intercept(user_message):
        return backup_vault()
    _dec = _decision_log_parse(user_message)
    if _dec is not None:
        return log_decision(_dec)
    if _decision_review_intercept(user_message):
        return recent_decisions(lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    _nut = _nutrition_log_parse(user_message)
    if _nut is not None:
        return log_calories(_nut[1]) if _nut[0] == "calories" else log_protein(_nut[1])
    if _nutrition_status_intercept(user_message):
        return nutrition_status(lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    _quiz_topic = _quiz_start_parse(user_message)
    if _quiz_topic is not None:
        return start_quiz(_quiz_topic, lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    _inj = _injury_log_parse(user_message)
    if _inj is not None:
        return log_injury(_inj, lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    _rec = _injury_recovered_parse(user_message)
    if _rec is not None:
        return mark_recovered(_rec, lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    if _injury_status_intercept(user_message):
        return injury_status(lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    _wo = _workout_log_parse(user_message)
    if _wo is not None:
        return log_workout(_wo, lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    if _workout_status_intercept(user_message):
        return recent_workouts(lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    _ft = _fitness_test_parse(user_message)
    if _ft is not None:
        return log_fitness_test(_ft, lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    _tg = _set_target_parse(user_message)
    if _tg is not None:
        return set_fitness_target(_tg, lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    if _fitness_progress_intercept(user_message):
        return fitness_progress(lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    if _weekly_summary_intercept(user_message):
        return weekly_summary(lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    _wt = _weight_log_parse(user_message)
    if _wt is not None:
        return log_weight(_wt, lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    if _weight_check_intercept(user_message):
        return weight_check(lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    _obs_q = _obsidian_search_parse(user_message)
    if _obs_q is not None:
        return search_obsidian(_obs_q, lang="he" if lang == "he" or is_hebrew(user_message) else "en")
    # v4.52: deterministic Achilles-screen intercepts. An open/show verb is
    # required so knowledge questions ("what IS a black hole") still go to
    # the model instead of popping a window.
    _low = user_message.lower()
    if re.search(r"(פתח|תפתח|open|show|launch|bring up|תעלה|תציג)[^.!?]{0,24}(black\s?hole|חור שחור|achilles|אכילס)", _low) \
       or re.search(r"(black\s?hole|חור שחור)[^.!?]{0,12}(screen|window|מסך|חלון)", _low):
        return open_achilles("core")
    if re.search(r"(פתח|תפתח|open|show|launch|תראה|תציג|תעלה)[^.!?]{0,24}(solar\s?system|מערכת השמש|הכוכבים|the planets)", _low):
        return open_achilles("solar")
    # v4.53: task list - open the todo scene / add a task by voice
    _t = re.search(r"(?:תוסיף משימה|תוסיף לרשימה|add (?:a )?task)\s+(.+)", user_message, re.IGNORECASE)
    if _t is not None:
        return todo_add_voice(_t.group(1), "he" if lang == "he" or is_hebrew(user_message) else "en")
    if re.search(r"(פתח|תפתח|open|show|תראה|תציג|תעלה)[^.!?]{0,24}(to\s?do|todo|task list|המשימות|רשימת משימות|רשימת המשימות)", _low):
        return open_achilles("todo")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    # JARVIS speaks ONLY Hebrew or English. Whisper can detect many languages,
    # but on short clips it often mis-detects (e.g. tags a phrase as German).
    # So we collapse everything that isn't clearly Hebrew down to English —
    # the two languages Matan actually uses.
    if lang == "he":
        _lang_note = "\nIMPORTANT: The user is speaking HEBREW. Reply ONLY in Hebrew. Never reply in any other language."
    else:
        _lang_note = "\nIMPORTANT: Reply ONLY in English. Never reply in German, French, or any language other than English, even if the user's words look like another language."
    # Give the model the current local time so it can turn "tomorrow at 4" into
    # a correct ISO datetime for calendar events.
    _time_note = "\nCurrent local time (Israel): " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
    # v4.42: prompt caching to cut API cost. The constant
    # JARVIS_SYSTEM_PROMPT (~4k tokens) is marked cache_control so
    # Anthropic caches it (~5 min) and bills cache hits at ~10% of
    # the input rate. The small variable suffix (language note +
    # current time) goes in its own uncached block so the cached
    # prefix stays byte-identical between calls. sys_prompt_plain is
    # the plain-string fallback used by the no-tools retry path.
    sys_prompt = [
        {"type": "text", "text": JARVIS_SYSTEM_PROMPT,
         "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": _lang_note + _time_note},
    ]
    sys_prompt_plain = JARVIS_SYSTEM_PROMPT + _lang_note + _time_note
    globals()["_last_timer_lang"] = "he" if lang == "he" else "en"
    # Combined toolset: built-in web search + our local tools.
    tools = [
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 3},
    ] + LOCAL_TOOLS

    # v4.67: hold the lock for the whole turn so concurrent callers (voice /
    # Telegram / the /ask HTTP thread) can never interleave appends into
    # conversation_history, and normalise/bound the history first.
    with _think_lock:
        _normalize_history()
        if not conversation_history:
            msg = f"[Memory from past conversations:]\n{memory}\n\n[Current message:]\n{user_message}"
        else:
            msg = user_message
        conversation_history.append({"role": "user", "content": msg})

        try:
            # Tool-use loop. Claude may ask to run a local tool; we run it, hand
            # the result back, and let it continue — repeating until it gives a
            # final text answer. The cap (5) prevents any accidental infinite loop.
            for _ in range(5):
                r = client.messages.create(
                    model="claude-sonnet-4-6", max_tokens=1024,
                    system=sys_prompt,
                    messages=conversation_history,
                    tools=tools,
                )
                # Record exactly what Claude returned (text + any tool requests).
                conversation_history.append({"role": "assistant", "content": r.content})

                if r.stop_reason == "tool_use":
                    # Run every LOCAL tool Claude asked for and collect results.
                    # (web_search runs on Anthropic's side, so we don't handle it.)
                    tool_results = []
                    for block in r.content:
                        if getattr(block, "type", None) == "tool_use" and block.name in (
                                "open_app", "save_note", "calendar_read", "calendar_add",
                                "calendar_delete", "calendar_update",
                                "gmail_read", "gmail_spam_review", "gmail_move_spam",
                                "find_places", "get_directions", "set_timer",
                                "spotify_play", "spotify_pause", "spotify_next",
                                "spotify_previous", "spotify_volume", "spotify_now_playing",
                                "learn_topic", "deep_learn_domain", "resume_learning",
                                "learning_status", "open_search_panel", "open_worldview",
                                "open_achilles", "open_roadmap"):
                            out = run_local_tool(block.name, block.input or {})
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": out,
                            })
                    if tool_results:
                        conversation_history.append({"role": "user", "content": tool_results})
                        continue  # let Claude turn the tool output into a reply
                    # v4.67: a tool_use we didn't answer (or only web_search) would
                    # poison the next call; drop the orphaned assistant turn.
                    if (conversation_history
                            and conversation_history[-1].get("role") == "assistant"):
                        conversation_history.pop()
                    break

                # Normal finish: gather text from the content blocks.
                parts = [b.text for b in r.content
                         if getattr(b, "type", None) == "text"]
                reply = " ".join(p.strip() for p in parts if p.strip()).strip()
                if not reply:
                    reply = "Done, sir."
                return clean_text(reply)

            return "I got a bit stuck on that, sir. Could you rephrase?"
        except Exception as e:
            # If tools aren't available for some reason, retry once plainly.
            try:
                _normalize_history()
                r = client.messages.create(
                    model="claude-sonnet-4-6", max_tokens=1024,
                    system=sys_prompt_plain, messages=conversation_history)
                reply = r.content[0].text
                conversation_history.append({"role": "assistant", "content": reply})
                return clean_text(reply)
            except Exception as e2:
                import traceback
                print("[diag] Brain error full traceback:", flush=True)
                traceback.print_exc()
                return f"[Error connecting to Brain: {e2}]"

# --- Daily briefing ("good morning / good evening") --------------------------
# Weather codes from the WMO standard used by Open-Meteo (free, no API key).
_WMO_WEATHER = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "foggy", 51: "light drizzle", 53: "drizzle",
    55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain",
    67: "freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow",
    77: "snow grains", 80: "rain showers", 81: "rain showers",
    82: "violent rain showers", 85: "snow showers", 86: "snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with hail",
}

def get_weather(when="today"):
    """Current/forecast weather for Alfei Menashe via Open-Meteo (free, no key).
    `when` is 'today' or 'tomorrow'. Returns a short English summary string in
    Celsius. Never throws; returns a friendly note on failure."""
    lat, lon = 32.1772, 34.9947  # Alfei Menashe
    url = ("https://api.open-meteo.com/v1/forecast"
           "?latitude=%s&longitude=%s"
           "&current=temperature_2m,weather_code"
           "&daily=temperature_2m_max,temperature_2m_min,weather_code"
           "&timezone=auto" % (lat, lon))
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return "weather unavailable (%s)" % e
    daily = d.get("daily", {})
    idx = 1 if when == "tomorrow" else 0
    try:
        hi = round(daily["temperature_2m_max"][idx])
        lo = round(daily["temperature_2m_min"][idx])
        desc = _WMO_WEATHER.get(daily["weather_code"][idx], "")
        if when == "tomorrow":
            return "%s, high %dC, low %dC" % (desc, hi, lo)
        cur = d.get("current", {}).get("temperature_2m")
        cur_s = ("currently %dC, " % round(cur)) if cur is not None else ""
        return "%s%s, high %dC, low %dC" % (cur_s, desc, hi, lo)
    except Exception:
        return "weather unavailable"

def _briefing_part_from_clock(now):
    """Map the hour to a part of day: morning (5-11), afternoon (12-17),
    evening (18-4)."""
    h = now.hour
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 18:
        return "afternoon"
    return "evening"

# Greeting phrases that trigger a briefing. Kept short so they only fire on a
# greeting, not inside a longer question.
_BRIEFING_MORNING = ["good morning", "morning jarvis", "\u05d1\u05d5\u05e7\u05e8 \u05d8\u05d5\u05d1", "boker tov"]
_BRIEFING_AFTERNOON = ["good afternoon", "\u05e6\u05d4\u05e8\u05d9\u05d9\u05dd \u05d8\u05d5\u05d1\u05d9\u05dd", "tzohoraim tovim"]
_BRIEFING_EVENING = ["good evening", "\u05e2\u05e8\u05d1 \u05d8\u05d5\u05d1", "erev tov"]

def detect_briefing(text):
    """Return 'morning' / 'afternoon' / 'evening' if the message is a greeting
    that should trigger a daily briefing, else None. Only matches short
    messages so 'good morning, what is the weather in Paris' is left to the
    normal brain."""
    if not text:
        return None
    t = text.lower().strip()
    for ch in ",.!?-:;\"'":
        t = t.replace(ch, " ")
    t = " ".join(t.split())
    if len(t.split()) > 4:
        return None
    if any(w in t for w in _BRIEFING_EVENING):
        return "evening"
    if any(w in t for w in _BRIEFING_AFTERNOON):
        return "afternoon"
    if any(w in t for w in _BRIEFING_MORNING):
        return "morning"
    return None

def _training_briefing_section():
    """Read training_log.json next to jarvis.py and return a short facts
    string for the daily briefing. Returns an empty string if no log
    exists (the briefing simply skips training in that case). Best-effort
    - any parse error returns the empty string.

    Expected JSON fields (all optional):
      last_weight_kg          number, e.g. 71.2
      last_weight_date        ISO date "YYYY-MM-DD"
      last_workout_type       string, e.g. "running 5km"
      last_workout_date       ISO date
      weekly_workouts         number
      weight_target_min_kg    number (defaults to 68 - Matan's red line)
    """
    try:
        p = Path(__file__).resolve().parent / "training_log.json"
        if not p.exists():
            return ""
        data = json.loads(p.read_text(encoding="utf-8"))
        lines = []
        w = data.get("last_weight_kg")
        wd = data.get("last_weight_date")
        tgt = data.get("weight_target_min_kg", 68)
        if w is not None:
            line = "Last weight: %g kg" % float(w)
            if wd:
                try:
                    d0 = datetime.date.fromisoformat(wd)
                    days = (datetime.date.today() - d0).days
                    if days == 0:
                        line += " (today)"
                    elif days == 1:
                        line += " (yesterday)"
                    else:
                        line += " (%d days ago)" % days
                except Exception:
                    pass
            try:
                gap = float(w) - float(tgt)
                if gap >= 0:
                    line += "; %+.1f kg above %g kg target" % (gap, tgt)
                else:
                    line += ("; %+.1f kg BELOW %g kg target "
                             "- red line crossed") % (gap, tgt)
            except Exception:
                pass
            lines.append(line)
        wt = data.get("last_workout_type")
        wtd = data.get("last_workout_date")
        if wt and wtd:
            try:
                d0 = datetime.date.fromisoformat(wtd)
                days = (datetime.date.today() - d0).days
                if days == 0:
                    when = "today"
                elif days == 1:
                    when = "yesterday"
                else:
                    when = "%d days ago" % days
                lines.append("Last workout: %s, %s" % (wt, when))
            except Exception:
                lines.append("Last workout: %s on %s" % (wt, wtd))
        elif wt:
            lines.append("Last workout: %s" % wt)
        wc = data.get("weekly_workouts")
        if wc is not None:
            lines.append("Workouts this week: %s" % wc)
        return "\n".join(lines)
    except Exception:
        return ""


def daily_briefing(part="auto", lang="en"):
    """Build and return a short spoken briefing string. Gathers weather,
    calendar, and email, then has the brain phrase it warmly in `lang`
    (he/en). `part` is 'morning' / 'afternoon' / 'evening' / 'auto'."""
    if not ANTHROPIC_API_KEY:
        return "[Error: Missing API Key in .env]"
    now = datetime.datetime.now()
    if part == "auto":
        part = _briefing_part_from_clock(now)
    if part == "evening":
        focus, day, greet = "tomorrow", now + datetime.timedelta(days=1), "Good evening"
    elif part == "afternoon":
        focus, day, greet = "today", now, "Good afternoon"
    else:
        focus, day, greet = "today", now, "Good morning"

    # Weather
    weather = get_weather("tomorrow" if focus == "tomorrow" else "today")

    # Calendar window
    local_tz = datetime.datetime.now().astimezone().tzinfo
    if focus == "tomorrow":
        tmin = day.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        tmin = now
    tmax = day.replace(hour=23, minute=59, second=59, microsecond=0)
    try:
        cal = calendar_read(tmin.replace(tzinfo=local_tz).isoformat(),
                            tmax.replace(tzinfo=local_tz).isoformat())
    except Exception as e:
        cal = "Calendar unavailable: %s" % e

    # Email summary
    try:
        mail = gmail_read(max_results=8)
    except Exception as e:
        mail = "Email unavailable: %s" % e

    training = _training_briefing_section()
    news = _news_briefing_section(lang)
    facts = (
        "GREETING: %s\n"
        "DATE (%s): %s\n"
        "WEATHER (%s, Alfei Menashe): %s\n"
        "%s"
        "%s"
        "CALENDAR (%s):\n%s\n\n"
        "EMAIL:\n%s\n"
        % (greet, focus, day.strftime("%A, %d %B %Y"),
           focus, weather,
           ("TRAINING:\n" + training + "\n\n") if training else "",
           ("NEWS:\n" + news + "\n\n") if news else "",
           focus, cal, mail))

    sys_p = (
        "You are Achilles, a calm British-butler AI assistant. You are giving your "
        "creator (address him as \"sir\" in English or \"\u05d0\u05d3\u05d5\u05e0\u05d9\" in Hebrew) a short "
        "spoken %s briefing. Use the data below. Speak warmly in %s, in 2 to 5 "
        "short sentences. Open with the greeting, then mention the weather, the "
        "key calendar events for the %s, anything notable in the email, and if "
        "a TRAINING section is present, briefly note the training status - "
        "especially if the user is below the 68 kg minimum target or hasn't "
        "trained in several days. If a NEWS section is present, briefly mention "
        "one or two of the headlines. If the calendar, email, or training data is "
        "not connected, unavailable, or empty, simply skip that part without "
        "explaining the technical reason. Do not read out dates as ISO "
        "strings; say them naturally. Plain text only: no markdown, no bullet "
        "points, no URLs."
        % (part, "Hebrew" if lang == "he" else "English", focus))

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        r = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=400,
            system=sys_p,
            messages=[{"role": "user", "content": facts}])
        parts = [b.text for b in r.content if getattr(b, "type", None) == "text"]
        reply = " ".join(p.strip() for p in parts if p.strip()).strip()
        return clean_text(reply) or (greet + ", sir.")
    except Exception as e:
        import traceback
        print("[diag] Briefing error full traceback:", flush=True)
        traceback.print_exc()
        # Fall back to a plain, locally-built briefing so JARVIS still speaks.
        return clean_text("%s, sir. The weather is %s." % (greet, weather))

# --- Timers / reminders ------------------------------------------------------
_active_timers = []
_last_timer_lang = "en"

def _timer_fire(label, lang):
    """Called when a timer elapses: announce it by voice (and on the orb)."""
    if lang == "he":
        msg = ("\u05d0\u05d3\u05d5\u05e0\u05d9, \u05d4\u05d8\u05d9\u05d9\u05de\u05e8 \u05dc%s \u05d4\u05e1\u05ea\u05d9\u05d9\u05dd." % label) if label \
            else "\u05d0\u05d3\u05d5\u05e0\u05d9, \u05d4\u05d8\u05d9\u05d9\u05de\u05e8 \u05d4\u05e1\u05ea\u05d9\u05d9\u05dd."
    else:
        msg = ("Sir, your %s timer is up." % label) if label else "Sir, your timer is up."
    try:
        if APP is not None:
            APP.ui(lambda: APP._push("JARVIS", msg))
    except Exception:
        pass
    try:
        beep()
    except Exception:
        pass
    try:
        speak(msg)
    except Exception:
        pass

def set_timer(minutes, label=None):
    """Start a countdown timer. After `minutes` minutes JARVIS announces it by
    voice in the last conversation language. Returns a short confirmation
    string for the brain to phrase naturally."""
    lang = globals().get("_last_timer_lang", "en")
    try:
        mins = float(minutes)
    except Exception:
        return "I need a number of minutes for the timer, sir."
    if mins <= 0:
        return "The timer needs to be longer than zero, sir."
    secs = mins * 60.0
    # v4.67: self-removing wrapper so fired timers don't leak in _active_timers
    # forever (only undo used to prune them; normally-elapsed timers stayed
    # referenced for the whole process lifetime).
    def _fire(_label=label, _lang=lang):
        try:
            _timer_fire(_label, _lang)
        finally:
            try:
                _active_timers.remove(t)
            except ValueError:
                pass
    t = threading.Timer(secs, _fire)
    t.daemon = True
    t.start()
    _active_timers.append(t)
    _record_action("set_timer", {"timer": t, "label": label})
    if mins >= 1:
        dur = "1 minute" if mins == 1 else ("%g minutes" % mins)
    else:
        dur = "%d seconds" % int(round(secs))
    if label:
        return "Timer set for %s (%s), sir." % (dur, label)
    return "Timer set for %s, sir." % dur

# --- Spotify control ---------------------------------------------------------
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPES = ("user-read-playback-state user-modify-playback-state "
                  "user-read-currently-playing")
_SPOTIFY_TOKEN_FILE = Path("spotify_token.json")


def _spotify_oauth_flow():
    """First-time auth: open browser, capture redirect, exchange code for
    tokens, persist them. Returns the token dict or None on failure."""
    import http.server, urllib.parse, urllib.request, webbrowser, threading, base64
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print("Spotify: SPOTIFY_CLIENT_ID/SECRET missing from .env")
        return None
    code_holder = {}

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(q)
            if "code" in params:
                code_holder["code"] = params["code"][0]
                body = ("<html><body style='font-family:sans-serif;"
                        "background:#000;color:#fff;text-align:center;"
                        "padding-top:80px'><h1>JARVIS Spotify connected.</h1>"
                        "<p>You can close this tab.</p></body></html>").encode()
            else:
                err = params.get("error", ["unknown"])[0]
                code_holder["error"] = err
                body = (("<html><body><h1>Auth failed: %s</h1></body></html>")
                        % err).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    try:
        server = http.server.HTTPServer(("127.0.0.1", 8888), _Handler)
    except OSError as e:
        print("Spotify: port 8888 busy:", e)
        return None
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": SPOTIFY_CLIENT_ID,
        "scope": SPOTIFY_SCOPES,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
    })
    print("Spotify: opening browser for one-time authorization...")
    webbrowser.open(auth_url)
    t.join(timeout=180)
    try:
        server.server_close()
    except Exception:
        pass

    code = code_holder.get("code")
    if not code:
        err = code_holder.get("error", "no code returned (timeout?)")
        print("Spotify auth failed:", err)
        return None

    auth_b64 = base64.b64encode(
        ("%s:%s" % (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)).encode()
    ).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SPOTIFY_REDIRECT_URI,
        }).encode(),
        headers={
            "Authorization": "Basic " + auth_b64,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            tokens = json.loads(r.read())
    except Exception as e:
        print("Spotify token exchange failed:", repr(e))
        return None
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
    _SPOTIFY_TOKEN_FILE.write_text(json.dumps(tokens))
    print("Spotify: connected.")
    return tokens


def _spotify_refresh(refresh_token):
    import urllib.parse, urllib.request, base64
    auth_b64 = base64.b64encode(
        ("%s:%s" % (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)).encode()
    ).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }).encode(),
        headers={
            "Authorization": "Basic " + auth_b64,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            tokens = json.loads(r.read())
    except Exception as e:
        print("Spotify refresh failed:", repr(e))
        return None
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
    if "refresh_token" not in tokens:
        tokens["refresh_token"] = refresh_token
    _SPOTIFY_TOKEN_FILE.write_text(json.dumps(tokens))
    return tokens


def _spotify_token():
    """Return a valid access token, refreshing or running OAuth as needed."""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None
    tokens = None
    if _SPOTIFY_TOKEN_FILE.exists():
        try:
            tokens = json.loads(_SPOTIFY_TOKEN_FILE.read_text())
        except Exception:
            tokens = None
    if tokens and time.time() >= tokens.get("expires_at", 0) - 30:
        tokens = _spotify_refresh(tokens.get("refresh_token", ""))
    if not tokens:
        tokens = _spotify_oauth_flow()
    return tokens.get("access_token") if tokens else None


def _spotify_request(method, path, params=None, body=None):
    import urllib.parse, urllib.request, urllib.error
    token = _spotify_token()
    if not token:
        return {"error": "Spotify not connected, sir."}
    url = "https://api.spotify.com/v1" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {"ok": True}
    except urllib.error.HTTPError as e:
        body_txt = ""
        try:
            body_txt = e.read().decode()
        except Exception:
            pass
        if e.code == 404:
            return {"error": "No active Spotify device, sir. Open Spotify on your phone or computer first."}
        if e.code == 403:
            return {"error": "Spotify Premium is required for that, sir."}
        return {"error": "HTTP %d: %s" % (e.code, body_txt[:200])}
    except Exception as e:
        return {"error": repr(e)}



def _spotify_ensure_active_device():
    """Make sure Spotify has an active device. Lists devices; if any exist but
    none is active, transfers playback to the first available one. Returns
    (ok: bool, error_message: str | None)."""
    r = _spotify_request("GET", "/me/player/devices")
    if "error" in r:
        return False, r["error"]
    devices = r.get("devices") or []
    if not devices:
        return False, "Spotify isn't open anywhere, sir. Open Spotify on a device first."
    if any(d.get("is_active") for d in devices):
        return True, None
    target = devices[0]
    transfer = _spotify_request("PUT", "/me/player",
                                body={"device_ids": [target["id"]], "play": False})
    if "error" in transfer:
        return False, ("Couldn't activate %s, sir: %s"
                       % (target.get("name", "device"), transfer["error"]))
    return True, None


def spotify_play(query=None):
    """Play music on Spotify. With a query, search and play the best match.
    Without a query, resume current playback."""
    ok, err = _spotify_ensure_active_device()
    if not ok:
        return err
    if query:
        result = _spotify_request("GET", "/search", params={
            "q": query, "type": "track,artist,album,playlist", "limit": 3,
        })
        if "error" in result:
            return "Couldn't search Spotify: %s" % result["error"]
        tracks = (result.get("tracks") or {}).get("items") or []
        playlists = (result.get("playlists") or {}).get("items") or []
        albums = (result.get("albums") or {}).get("items") or []
        artists = (result.get("artists") or {}).get("items") or []
        if tracks:
            t = tracks[0]
            r = _spotify_request("PUT", "/me/player/play",
                                 body={"uris": [t["uri"]]})
            if "error" in r:
                return "Couldn't play: %s" % r["error"]
            return "Playing %s by %s, sir." % (
                t.get("name", "Unknown"),
                (t.get("artists") or [{"name": "Unknown"}])[0].get("name", ""),
            )
        if playlists:
            p = playlists[0]
            r = _spotify_request("PUT", "/me/player/play",
                                 body={"context_uri": p["uri"]})
            if "error" in r:
                return "Couldn't play: %s" % r["error"]
            return "Playing the playlist %s, sir." % p.get("name", "")
        if albums:
            a = albums[0]
            r = _spotify_request("PUT", "/me/player/play",
                                 body={"context_uri": a["uri"]})
            if "error" in r:
                return "Couldn't play: %s" % r["error"]
            return "Playing the album %s, sir." % a.get("name", "")
        if artists:
            ar = artists[0]
            r = _spotify_request("PUT", "/me/player/play",
                                 body={"context_uri": ar["uri"]})
            if "error" in r:
                return "Couldn't play: %s" % r["error"]
            return "Playing music by %s, sir." % ar.get("name", "")
        return "No results on Spotify for '%s', sir." % query
    r = _spotify_request("PUT", "/me/player/play")
    if "error" in r:
        return "Couldn't resume: %s" % r["error"]
    return "Resumed, sir."


def spotify_pause():
    ok, err = _spotify_ensure_active_device()
    if not ok:
        return err
    r = _spotify_request("PUT", "/me/player/pause")
    if "error" in r:
        return "Couldn't pause: %s" % r["error"]
    return "Paused, sir."


def spotify_next():
    ok, err = _spotify_ensure_active_device()
    if not ok:
        return err
    r = _spotify_request("POST", "/me/player/next")
    if "error" in r:
        return "Couldn't skip: %s" % r["error"]
    return "Next track, sir."


def spotify_previous():
    ok, err = _spotify_ensure_active_device()
    if not ok:
        return err
    r = _spotify_request("POST", "/me/player/previous")
    if "error" in r:
        return "Couldn't go back: %s" % r["error"]
    return "Previous track, sir."


def spotify_volume(level):
    try:
        v = int(level)
    except Exception:
        return "I need a volume number from 0 to 100, sir."
    v = max(0, min(100, v))
    ok, err = _spotify_ensure_active_device()
    if not ok:
        return err
    r = _spotify_request("PUT", "/me/player/volume",
                         params={"volume_percent": v})
    if "error" in r:
        return "Couldn't set volume: %s" % r["error"]
    return "Volume set to %d%%, sir." % v


def spotify_now_playing():
    r = _spotify_request("GET", "/me/player/currently-playing")
    if "error" in r:
        return r["error"]
    if not r or not r.get("item"):
        return "Nothing playing, sir."
    item = r["item"]
    artists = ", ".join(a.get("name", "") for a in item.get("artists", []))
    return "%s by %s, sir." % (item.get("name", "Unknown"), artists)


# --- ElevenLabs voice (premium, English only) -------------------------------
def _el_pick_voice_id():
    """Find a good British voice ID from the account, once, and cache it.
    Resolves by NAME (no fragile hard-coded ID): tries EL_PREFERRED_VOICES in
    order, then any available voice. Returns None if it can't (so we fall back
    to edge-tts).
    NOTE (v3.13): _el_voice_id_cache is pre-set to a chosen voice ID above, so
    this returns it immediately and the lookup below is normally skipped."""
    global _el_voice_id_cache
    if _el_voice_id_cache:
        return _el_voice_id_cache
    if not ELEVENLABS_API_KEY:
        print("[diag] ElevenLabs: no API key in environment -> using edge-tts.", flush=True)
        return None
    try:
        req = urllib.request.Request(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": ELEVENLABS_API_KEY})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        voices = data.get("voices", [])
        by_name = {(v.get("name") or "").lower(): v.get("voice_id") for v in voices}
        for pref in EL_PREFERRED_VOICES:
            vid = by_name.get(pref.lower())
            if vid:
                _el_voice_id_cache = vid
                print(f"[diag] ElevenLabs voice selected: {pref} ({vid})", flush=True)
                return vid
        if voices:
            _el_voice_id_cache = voices[0].get("voice_id")
            print("[diag] ElevenLabs voice (first available):", voices[0].get("name"), flush=True)
            return _el_voice_id_cache
        print("[diag] ElevenLabs: account has no voices.", flush=True)
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8")[:300]
        except Exception:
            detail = ""
        print("[diag] ElevenLabs voices HTTP error:", e.code, detail, flush=True)
    except Exception as e:
        print("[diag] ElevenLabs voice lookup failed:", repr(e), flush=True)
    return None

def speak_elevenlabs(text, fn):
    """Render `text` to `fn` (mp3) with ElevenLabs. Returns True on success,
    False to signal the caller to fall back to edge-tts."""
    if not ELEVENLABS_API_KEY:
        return False
    vid = _el_pick_voice_id()
    if not vid:
        return False
    try:
        body = json.dumps({
            "text": text,
            "model_id": EL_MODEL,
            # calm, consistent butler delivery
            "voice_settings": {"stability": 0.55, "similarity_boost": 0.75,
                               "style": 0.0, "use_speaker_boost": True},
        }).encode("utf-8")
        url = ("https://api.elevenlabs.io/v1/text-to-speech/%s"
               "?output_format=mp3_44100_128" % vid)
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"xi-api-key": ELEVENLABS_API_KEY,
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            audio = resp.read()
        if not audio:
            return False
        with open(fn, "wb") as f:
            f.write(audio)
        return True
    except urllib.error.HTTPError as e:
        # 401 = bad key, 429 = quota used up, etc. Print it so we can see why.
        try:
            detail = e.read().decode("utf-8")[:300]
        except Exception:
            detail = ""
        print("[diag] ElevenLabs TTS HTTP error:", e.code, detail, flush=True)
        return False
    except Exception as e:
        print("[diag] ElevenLabs TTS error:", repr(e), flush=True)
        return False

async def _speak(text, voice, fn="jarvis_reply.mp3"):
    # Slow the pace a touch and lower the pitch slightly -> calmer, more
    # natural "butler" delivery instead of a fast, flat robotic read.
    await edge_tts.Communicate(text, voice, rate="-8%", pitch="-3Hz").save(fn)

def play_audio(path="jarvis_reply.mp3"):
    try:
        p = os.path.abspath(path)
        mci = ctypes.windll.winmm.mciSendStringW
        mci("close jarvisaudio", None, 0, 0)
        if mci('open "%s" type mpegvideo alias jarvisaudio' % p, None, 0, 0) == 0:
            mci("play jarvisaudio wait", None, 0, 0)
            mci("close jarvisaudio", None, 0, 0)
    except Exception as e:
        print("Audio playback error:", e)

def stop_audio():
    """Immediately stop whatever JARVIS is currently playing (used by F5)."""
    try:
        mci = ctypes.windll.winmm.mciSendStringW
        mci("stop jarvisaudio", None, 0, 0)
        mci("close jarvisaudio", None, 0, 0)
    except Exception:
        pass

def speak(text):
    # Use a UNIQUE filename each time. The old code always wrote the same
    # 'jarvis_reply.mp3'; if the previous file was still locked (another copy of
    # JARVIS, or playback not fully closed) the save failed with
    # "Permission denied: jarvis_reply.mp3". A fresh name avoids that entirely.
    fn = "jarvis_reply_%d.mp3" % (int(time.time() * 1000) % 1000000)
    try:
        produced = False
        # Voice selection: use the ElevenLabs Alfred voice for replies that are
        # MOSTLY English (i.e. English with a sprinkling of Hebrew place names
        # is still English). Replies that are mostly Hebrew skip ElevenLabs and
        # use edge-tts, which sounds more natural for Hebrew.
        mostly_he = is_mostly_hebrew(text)
        if not mostly_he:
            produced = speak_elevenlabs(text, fn)
        if not produced:
            voice = VOICE_HEBREW if mostly_he else VOICE_ENGLISH
            try:
                asyncio.run(_speak(text, voice, fn))
                produced = True
            except Exception as e:
                if not mostly_he:
                    try:
                        asyncio.run(_speak(text, VOICE_ENGLISH_FALLBACK, fn))
                        produced = True
                    except Exception as e2:
                        print("Voice error (fallback):", e2)
                else:
                    print("Voice error:", e)
        if produced:
            play_audio(fn)
    except Exception as e:
        print("Voice error:", e)
    finally:
        # Best-effort cleanup so these temp files don't pile up. play_audio
        # blocks until playback ends and closes the handle, so by here it's free.
        try:
            os.remove(fn)
        except Exception:
            pass

def save_log(u, j):
    now = datetime.datetime.now()
    lf = Path(SSD_OBSIDIAN_VAULT) / f"Log_{now.strftime('%Y-%m-%d')}.md"
    with open(lf, "a", encoding="utf-8") as f:
        f.write(f"\n### Chat - {now.strftime('%H:%M:%S')}\n**You:** {u}\n\n**JARVIS:** {j}\n\n---\n")

# =============================================================================
# SEARCH PANEL BACKEND (image + web search via Claude)
# =============================================================================
# Global handle to the running App, so tool functions (which run on a worker
# thread inside think()) can ask the main thread to open the panel window.
APP = None

def _image_block_from_path(path):
    """Read an image file and return an Anthropic image content block, or None."""
    try:
        mt = mimetypes.guess_type(path)[0] or "image/jpeg"
        if mt not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            mt = "image/jpeg"
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("ascii")
        return {"type": "image",
                "source": {"type": "base64", "media_type": mt, "data": data}}
    except Exception as e:
        print("Image read error:", repr(e))
        return None

def _link_depth_score(url):
    """Rough 'how specific is this URL' score, used ONLY to re-order the
    FALLBACK links (when the brain did not hand us curated product links).
    Pushes deep product pages above bare store homepages."""
    try:
        p = urllib.parse.urlparse(url or "")
        segs = [s for s in (p.path or "").split("/") if s]
        score = len(segs) * 2
        if p.query:
            score += 3
        low = (url or "").lower()
        for kw in ("modelid", "/item", "/p/", "product", "/dp/", "sku", ".aspx"):
            if kw in low:
                score += 4
        return score
    except Exception:
        return 0


def search_with_optional_image(user_text, image_path=None, lang="he"):
    """Search panel: an EXTENSION of the main voice brain. Uses the same
    JARVIS_SYSTEM_PROMPT (so it shares the user's personal context, home
    address, family, Israeli cities, sir/adoni, etc.) plus a search-specific
    overlay (Israeli stores, 2-sentence cap) and place/direction tools.
    Stays separate from think() because it does NOT touch
    conversation_history - each search is one-shot."""
    if not ANTHROPIC_API_KEY:
        return ("[Error: Missing API Key in .env]", [])
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Base = the same system prompt the main voice mode uses, so search
    # inherits all personal context.
    sys_prompt = JARVIS_SYSTEM_PROMPT
    # Search-specific overlay layered on top.
    sys_prompt += (
        "\n\nYOU ARE NOW IN THE PRODUCT SEARCH WINDOW. Additional rules for "
        "this mode:\n"
        "- He is in ISRAEL and can only buy from stores that operate in "
        "Israel. When finding where to buy something, your web_search query "
        "MUST restrict results to Israeli stores. Build the query with "
        "explicit site filters, e.g.:\n"
        "  <product name> site:zap.co.il OR site:ksp.co.il OR site:bug.co.il "
        "OR site:ivory.co.il OR site:idigital.co.il OR site:amazon.co.il\n"
        "Also run a second query in Hebrew if you know the Hebrew term: "
        "'<product> \u05d9\u05e9\u05e8\u05d0\u05dc \u05de\u05d7\u05d9\u05e8'. "
        "Prefer Zap.co.il - it compares prices across Israeli retailers. "
        "Give prices in shekels (NIS / \u20aa) only. NEVER return Amazon.com, "
        "B&H US, AliExpress or other foreign stores - only stores that sell "
        "and ship inside Israel. If you cannot find it in an Israeli store, "
        "say so plainly instead of falling back to a foreign store.\n"
        "- DEFAULT MARKET vs EXPLICIT OVERRIDE: the Israel-only rule "
        "above is the DEFAULT. If the user EXPLICITLY names another "
        "country or market for this search (for example: search the US "
        "market, find this in Germany, or in Hebrew תחפש בשוק האמריקאי "
        "/ בגרמניה), then for THIS request search that country instead, "
        "give prices in the local currency of that country, and the "
        "Israel-only / no-foreign-stores rule does NOT apply. Only "
        "override when a country or market is named explicitly; if none "
        "is mentioned, always default to Israel.\n"
        "- If an image is attached, first identify exactly what the product "
        "is (type, material, colour, style, brand if visible), then search "
        "for it in Israel as above.\n"
        "- You CAN use find_places and get_directions in this window too - "
        "if the user asks where to buy/eat/visit, or asks about distance / "
        "travel time, use those tools as needed. The user's home address is "
        "in the main context above; use it as the default origin for travel "
        "times.\n"
        "- Reply in %s.\n"
        "- CRITICAL FORMAT: keep your reply to AT MOST 2 short sentences. "
        "NEVER write numbered lists, bullet points, paragraphs, or long "
        "descriptions inside your reply text - the user already sees the "
        "clickable result links shown separately below. Your job is only a "
        "very brief headline. Example: 'Found several well-reviewed pizza "
        "places in Kfar Saba, sir. Top mentions include Gutleib and La "
        "Cappa - the links are below.' That's it - 2 sentences, no more. "
        "NEVER speak or write out URLs/links in your reply text.\n\n"
        "DIRECT PRODUCT LINKS - VERY IMPORTANT:\n"
        "After your short spoken reply, output a machine-readable block "
        "listing the BEST links you actually found in the web search "
        "results. This block is shown to the user as clickable rows and is "
        "NOT part of your spoken reply, so putting URLs in it does NOT "
        "break the no-URLs-in-the-reply rule above.\n"
        "- Prefer DIRECT PRODUCT PAGES (the page for the specific item, "
        "with its price) - NOT a store homepage or a broad category/search "
        "page. Good: a zap.co.il model page or a ksp.co.il item page for "
        "the exact product. Bad: the bare ksp.co.il or zap.co.il home "
        "page.\n"
        "- Only use URLs that actually appeared in the web search results. "
        "Never invent, guess, or shorten a URL.\n"
        "- Up to 6 links, best first; put exact-product zap.co.il "
        "price-comparison pages first when you have them.\n"
        "- If you truly found no good product links, leave the block "
        "empty.\n"
        "Output it EXACTLY in this form, on its own lines at the very end:\n"
        "<<<LINKS>>>\n"
        "short title | https://full-url\n"
        "short title | https://full-url\n"
        "<<<ENDLINKS>>>"
        % ("Hebrew" if lang == "he" else "English"))
    sys_prompt += ("\nCurrent local time (Israel): "
                   + datetime.datetime.now().strftime("%Y-%m-%d %H:%M (%A)"))

    content = []
    if image_path:
        blk = _image_block_from_path(image_path)
        if blk:
            content.append(blk)
    content.append({"type": "text",
                    "text": (user_text or "Find this product.")})

    # web_search + find_places + get_directions. calendar/gmail/open_app are
    # intentionally excluded - they do not belong in a product-search context.
    tools = [{"type": "web_search_20250305", "name": "web_search",
              "max_uses": 4}]
    for t in LOCAL_TOOLS:
        if t.get("name") in ("find_places", "get_directions"):
            tools.append(t)

    links = []
    spoken_parts = []
    try:
        msgs = [{"role": "user", "content": content}]
        for _ in range(5):
            r = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=700,
                system=sys_prompt,
                messages=msgs, tools=tools)
            msgs.append({"role": "assistant", "content": r.content})
            # Collect text + any web_search links from this turn.
            for b in r.content:
                bt = getattr(b, "type", None)
                if bt == "text" and getattr(b, "text", "").strip():
                    spoken_parts.append(b.text.strip())
                elif bt == "web_search_tool_result":
                    results = getattr(b, "content", None) or []
                    for item in results:
                        url = getattr(item, "url", None)
                        title = getattr(item, "title", None) or url
                        if url:
                            links.append((title, url))
            # If Claude called find_places / get_directions locally, run them
            # and feed the results back. web_search is server-side and needs
            # no local handling.
            if r.stop_reason == "tool_use":
                tool_results = []
                for block in r.content:
                    if getattr(block, "type", None) == "tool_use" and \
                            block.name in ("find_places", "get_directions"):
                        out = run_local_tool(block.name, block.input or {})
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": out,
                        })
                if tool_results:
                    msgs.append({"role": "user", "content": tool_results})
                continue
            break
        # v4.13: the brain hands us its CHOSEN product links in a machine
        # block  <<<LINKS>>> title | url ... <<<ENDLINKS>>>  at the end of
        # its reply. Prefer those (curated, direct product pages) over the
        # raw search results, and strip the block out of the spoken text.
        full_text = " ".join(spoken_parts)
        brain_links = []
        mblk = re.search(r"<<<\s*LINKS\s*>>>(.*?)<<<\s*ENDLINKS\s*>>>",
                         full_text, re.DOTALL | re.IGNORECASE)
        block_body = mblk.group(1) if mblk else ""
        if block_body:
            for line in block_body.splitlines():
                mu = re.search(r"(https?://\S+)", line)
                if not mu:
                    continue
                url = mu.group(1).rstrip(").,]\u00bb\"'")
                title = line[:mu.start()].strip().rstrip("|").strip() or url
                brain_links.append((title, url))
        # Remove the block (and any dangling, un-closed one) from what we
        # show/speak, then strip any stray URLs as before.
        spoken_raw = re.sub(r"<<<\s*LINKS\s*>>>.*?<<<\s*ENDLINKS\s*>>>", "",
                            full_text, flags=re.DOTALL | re.IGNORECASE)
        spoken_raw = re.sub(r"<<<\s*LINKS\s*>>>.*$", "", spoken_raw,
                            flags=re.DOTALL | re.IGNORECASE)
        spoken_raw = re.sub(r"https?://\S+", "", spoken_raw)
        spoken_raw = re.sub(r"\bwww\.\S+", "", spoken_raw)
        spoken = clean_text(spoken_raw).strip() or "Here is what I found, sir."
        # Pick which link set to show: the brain's curated picks if any,
        # otherwise the raw web_search results re-ordered so deeper product
        # pages beat bare homepages (so the list is NEVER empty).
        if brain_links:
            chosen = brain_links
        else:
            chosen = sorted(links, key=lambda tu: _link_depth_score(tu[1]),
                            reverse=True)
        # de-duplicate by URL, keep order, cap at 8
        seen, uniq = set(), []
        for t, u in chosen:
            if u not in seen:
                seen.add(u)
                uniq.append((t, u))
        return spoken, uniq[:8]
    except Exception as e:
        import traceback
        print("[diag] Search panel full traceback:", flush=True)
        traceback.print_exc()
        return (f"[Search error: {e}]", [])


RAMPS = {
    # Red-orange "molten core" palette. Each state is a slightly different shade
    # of red-orange so you can still tell idle / listening / thinking apart.
    "loading":   ((70, 30, 15),   (150, 80, 40)),
    "idle":      ((120, 35, 10),  (255, 150, 60)),
    "listening": ((150, 45, 10),  (255, 180, 80)),
    "thinking":  ((140, 25, 10),  (255, 120, 40)),
    "speaking":  ((160, 55, 15),  (255, 200, 100)),
}
# Transparency key color. Near-black (not magenta) so the orb's soft glow blends
# toward dark = natural, instead of toward magenta = an ugly pink halo.
KEY = "#050507"
# v4.60: FINAL - the face is the PIL black hole drawn INSIDE the original
# floating frameless orb window. It pops on wake exactly like the orange
# ball always did. No browser window ever opens on the PC; the phone keeps
# the full WebGL page (achilles.html). Do not set this to "blackhole".
ACHILLES_FACE = "orb"

def _clamp(v):
    return 0 if v < 0 else (255 if v > 255 else int(v))

def _hexcol(r, g, b):
    return "#%02x%02x%02x" % (_clamp(r), _clamp(g), _clamp(b))

# ============================ TELEGRAM BRIDGE ============================
# Talk to JARVIS from your phone via a Telegram bot, and let JARVIS push
# messages to you. Locked to ONE chat via a pairing code, so a stranger who
# finds the bot cannot read your calendar / notes. Uses long-polling (no
# public URL needed) on a daemon thread. Token = TELEGRAM_BOT_TOKEN in .env.
_TG_CHAT_FILE = str(Path(__file__).resolve().parent / "telegram_chat.json")
_tg_chat_id = None
_tg_pair_code = None
_tg_offset = 0

def _tg_api(method, params=None, timeout=60):
    if not TELEGRAM_BOT_TOKEN:
        return None
    url = "https://api.telegram.org/bot%s/%s" % (TELEGRAM_BOT_TOKEN, method)
    data = urllib.parse.urlencode(params).encode("utf-8") if params else None
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, data=data), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None

def telegram_send(text, chat_id=None):
    """Push a message to the paired chat (or a specific chat_id).
    Safe no-op if Telegram is not configured / not paired."""
    cid = chat_id if chat_id is not None else _tg_chat_id
    if not TELEGRAM_BOT_TOKEN or cid is None or not text:
        return False
    t = text if len(text) <= 4000 else (text[:3990] + "...")
    res = _tg_api("sendMessage", {"chat_id": cid, "text": t})
    return bool(res and res.get("ok"))

def _tg_load_chat():
    global _tg_chat_id
    try:
        if os.path.exists(_TG_CHAT_FILE):
            with open(_TG_CHAT_FILE, "r", encoding="utf-8") as f:
                _tg_chat_id = json.load(f).get("chat_id")
    except Exception:
        _tg_chat_id = None

def _tg_save_chat(cid):
    global _tg_chat_id
    _tg_chat_id = cid
    try:
        with open(_TG_CHAT_FILE, "w", encoding="utf-8") as f:
            json.dump({"chat_id": cid}, f)
    except Exception:
        pass


class App:
    # v4.52: 'state' is a property so EVERY existing "self.state = ..."
    # assignment in the file also mirrors into _achilles_state, which the
    # :7778 proxy serves at GET /state. The Achilles black-hole screen polls
    # it to animate idle/listening/thinking/speaking. Zero call-site changes.
    @property
    def state(self):
        return getattr(self, "_state_val", "loading")

    @state.setter
    def state(self, v):
        self._state_val = v
        try:
            _achilles_state["state"] = v
            _achilles_state["ts"] = time.time()
        except Exception:
            pass

    def __init__(self, root):
        global APP
        APP = self
        self.root = root
        self.state = "loading"
        self.wake_on = False
        self.busy = False
        self.stop = False
        self.model = None
        self.memory = ""
        self.outbox = []
        self._lock = threading.Lock()
        self._hold = ""
        self._hold_until = 0.0
        self.panel = None        # the big search window (created on demand)
        self.panel_busy = False
        # For the function keys: remember the last full exchange (for F2 = save)
        # and the last spoken reply (for F3 = repeat).
        self._last_user = ""
        self._last_reply = ""
        self._preroll = None   # pre-roll audio captured at wake time
        # v4.57: black-hole face layers, pre-rendered in the background
        # so launch is never blocked. Until ready, the old orb shows.
        self._bhL = None
        self._bh_ph = 0.0
        self._bh_star_a = 0.0
        if HAVE_PIL:
            threading.Thread(target=self._bh_build_async, daemon=True).start()

        sw = root.winfo_screenwidth()
        self.EW, self.EH = 400, 470
        self.ex = sw - self.EW - 30
        self.ey = 60

        self.mode = "hidden"      # hidden | expanded
        self.req_mode = "hidden"
        self.typing = False       # typing box visible?
        self.req_typing = False

        root.title("ACHILLES")
        root.overrideredirect(True)
        # --- ACHILLES taskbar presence (achilles_taskbar_icon) -------------
        try:
            _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "achilles.ico")
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    u"horn.achilles.jarvis")
            except Exception:
                pass
            self._taskbar_anchor = tk.Toplevel(root)
            _tb = self._taskbar_anchor
            _tb.title("ACHILLES")
            _tb.geometry("1x1+-32000+-32000")
            _tb.attributes("-topmost", False)
            if os.path.isfile(_ico):
                try:
                    _tb.iconbitmap(default=_ico)
                except Exception:
                    try:
                        _tb.iconbitmap(_ico)
                    except Exception:
                        pass
                try:
                    root.iconbitmap(default=_ico)
                except Exception:
                    pass
            def _on_anchor_close():
                try:
                    self.stop = True
                except Exception:
                    pass
                try:
                    root.destroy()
                except Exception:
                    pass
            _tb.protocol("WM_DELETE_WINDOW", _on_anchor_close)
        except Exception as _e:
            print("[diag] taskbar anchor not created:", repr(_e))
        # -------------------------------------------------------------------
        root.attributes("-topmost", True)
        try:
            root.attributes("-transparentcolor", KEY)
        except Exception:
            pass
        root.config(bg=KEY)
        root.geometry("%dx%d+%d+%d" % (self.EW, self.EH, self.ex, self.ey))
        root.withdraw()  # start fully hidden

        self.SS = 3  # supersample factor for Pillow anti-aliasing (higher = smoother but heavier)
        self.use_pil = HAVE_PIL

        self.cv = tk.Canvas(root, bg=KEY, highlightthickness=0, bd=0)
        self.cv.pack(fill=tk.BOTH, expand=True)

        self.entry = tk.Entry(root, bg="#161b22", fg="#e6edf3",
                              insertbackground="#58a6ff", relief=tk.FLAT,
                              font=("Segoe UI", 11))
        self.entry.bind("<Return>", self._send_typed)

        # particles
        self.N = 360
        self.pts = []
        ga = 2.399963
        for i in range(self.N):
            y = 1 - (i / (self.N - 1)) * 2
            rr = (1 - y * y) ** 0.5
            th = i * ga
            self.pts.append((np.cos(th) * rr, y, np.sin(th) * rr))

        # canvas image (Pillow path) AND oval items (fallback) — always create
        # both so the fallback renderer can never crash on missing attributes.
        self.img_id = self.cv.create_image(0, 0, anchor="nw")
        self._tkimg = None
        self.items = [self.cv.create_oval(0, 0, 0, 0, outline="", fill="")
                      for _ in range(self.N)]
        self.ripple_id = self.cv.create_oval(0, 0, 0, 0, outline="", width=2)
        self.ring_id = self.cv.create_oval(0, 0, 0, 0, outline="", width=2)
        self.status_id = self.cv.create_text(0, 0, text="", fill="#9aa7b4",
                                              font=("Segoe UI", 9))

        self.ang = 0.0
        self.zoom = 1.0
        self.sel = 0
        self.prev = "loading"
        self.ripple = 0.0
        self.ripple_on = False
        self._drag = (0, 0)
        self._moved = False

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Talk", command=lambda: self.talk(True))
        self.menu.add_command(label="Type", command=self._open_typing)
        self.menu.add_command(label="Search window", command=lambda: self.ui(self.open_panel))
        self.menu.add_command(label="Toggle Wake Word", command=self.toggle_wake)
        self.menu.add_separator()
        self.menu.add_command(label="Quit JARVIS", command=self.quit)

        self.cv.bind("<Button-3>", self._show_menu)
        # v4.61: double-click = fullscreen portal (listening stays on wake word)
        self.cv.bind("<Double-Button-1>", lambda e: threading.Thread(
            target=open_portal, daemon=True).start())
        self.cv.bind("<Button-1>", self._drag_start)
        self.cv.bind("<B1-Motion>", self._drag_move)
        root.bind_all("<Escape>", lambda e: self._hide())
        # Function keys. When the fullscreen search window is open these drive
        # IT (F1 type, F2 speak, F3 image, F5 stop talking); otherwise they keep
        # their normal main-window jobs (F1 typing box, F2 save, F3 repeat).
        root.bind_all("<F1>", lambda e: self._key_f1())
        root.bind_all("<F2>", lambda e: self._key_f2())
        root.bind_all("<F3>", lambda e: self._key_f3())
        root.bind_all("<F5>", lambda e: self._key_f5())

        threading.Thread(target=self._boot, daemon=True).start()
        threading.Thread(target=self._signal_watch, daemon=True).start()
        threading.Thread(target=self._telegram_loop, daemon=True).start()
        self.animate()

    # ---- thread-safe UI helper ----
    def ui(self, fn):
        """Run a callback on the main (tkinter) thread. Global hotkeys (the
        'keyboard' library) fire on their OWN thread, and tkinter is not
        thread-safe, so calling UI code directly from there crashes. We marshal
        the callback onto the main thread with after(). This method was being
        called by the F1/F2/F3 hotkeys but never existed -> that was the
        'App object has no attribute ui' crash. Now it exists."""
        try:
            self.root.after(0, fn)
        except Exception:
            pass

    # ---- search panel (big window: type / speak / pick image + links) ----
    # --- search-window theme (dark, luxury, molten-amber accent) ---
    _UI = {
        "bg": "#0a0c10", "panel": "#11151b", "input": "#161b22",
        "hover": "#1f2733", "accent": "#ff8c42", "accent2": "#ffa55f",
        "ink": "#1a1205", "text": "#e6edf3", "muted": "#8b97a5",
        "link": "#7cc4ff", "divider": "#222a35",
    }

    def _hoverable(self, widget, normal, hover):
        """Make a button gently change colour when the mouse is over it."""
        widget.bind("<Enter>", lambda e: widget.config(bg=hover))
        widget.bind("<Leave>", lambda e: widget.config(bg=normal))

    # ----- canvas drawing helpers for the cinematic search window -----
    def _round_rect(self, cv, x1, y1, x2, y2, r=14, **kw):
        """Draw a rounded rectangle on a canvas; returns the polygon item id."""
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return cv.create_polygon(pts, smooth=True, **kw)

    def _make_orb_image(self, size=240):
        """Render the molten-amber glowing orb as an RGBA Pillow image."""
        cx = cy = size / 2.0
        R = size * 0.30
        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for rad, a in [(R * 2.7, 28), (R * 2.0, 44), (R * 1.5, 70), (R * 1.15, 110)]:
            gd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(255, 120, 40, a))
        glow = glow.filter(ImageFilter.GaussianBlur(size * 0.045))
        core = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        cd = ImageDraw.Draw(core)
        steps = 30
        for i in range(steps):
            t = i / (steps - 1)
            rr = R * (1 - t)
            col = (255, int(120 + 125 * t), int(40 + 155 * t), 255)
            cd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)
        core = core.filter(ImageFilter.GaussianBlur(size * 0.012))
        return Image.alpha_composite(glow, core)

    def _make_backdrop_image(self, w, h):
        """Render the dark vertical gradient + warm top glow as an RGB image."""
        top, bottom = (16, 16, 22), (6, 7, 10)
        grad = Image.new("RGB", (w, h))
        gd = ImageDraw.Draw(grad)
        for y in range(h):
            t = y / max(1, h - 1)
            gd.line([(0, y), (w, y)],
                    fill=(int(top[0] * (1 - t) + bottom[0] * t),
                          int(top[1] * (1 - t) + bottom[1] * t),
                          int(top[2] * (1 - t) + bottom[2] * t)))
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gld = ImageDraw.Draw(glow)
        gx, gy = w // 2, int(h * 0.15)
        for rad, a in [(360, 16), (260, 24), (170, 32), (90, 40)]:
            gld.ellipse([gx - rad, gy - rad, gx + rad, gy + rad], fill=(255, 110, 40, a))
        glow = glow.filter(ImageFilter.GaussianBlur(60))
        return Image.alpha_composite(grad.convert("RGBA"), glow).convert("RGB")

    def _cbutton(self, cv, x1, y1, x2, y2, label, cmd, primary=False):
        """Draw a rounded, hoverable button directly on the canvas."""
        c = self._UI
        base = c["accent"] if primary else c["input"]
        hov = c["accent2"] if primary else c["hover"]
        fg = c["ink"] if primary else c["text"]
        outline = "" if primary else c["divider"]
        tag = "cbtn%d" % self._cbtn_n
        self._cbtn_n += 1
        rid = self._round_rect(cv, x1, y1, x2, y2, r=14,
                               fill=base, outline=outline, tags=(tag,))
        cv.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=label, fill=fg,
                       font=("Segoe UI", 11, "bold"), tags=(tag,))
        cv.tag_bind(tag, "<Enter>",
                    lambda e, i=rid: (cv.itemconfig(i, fill=hov), cv.config(cursor="hand2")))
        cv.tag_bind(tag, "<Leave>",
                    lambda e, i=rid: (cv.itemconfig(i, fill=base), cv.config(cursor="")))
        cv.tag_bind(tag, "<Button-1>", lambda e: cmd())

    def _render_orb_frame(self, size, ang):
        """Render ONE frame of the real particle orb (round glow, no square),
        reusing the same points as the main orb. Returns a PIL RGBA image."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        R = size * 0.30
        focal = R * 2.6
        cx = cy = size / 2.0
        # warm ROUND backing disc (this is why there is no square halo)
        disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        dd = ImageDraw.Draw(disc)
        dr_r = R * 1.55
        steps = 22
        for k in range(steps):
            t = k / (steps - 1.0)
            rr = dr_r * (1.0 - t)
            dd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                       fill=(int(40 + 90 * t), int(15 + 35 * t), int(8 + 12 * t), 255))
        try:
            disc = disc.filter(ImageFilter.GaussianBlur(size * 0.02))
        except Exception:
            pass
        img.alpha_composite(disc)
        dr = ImageDraw.Draw(img)
        sa, ca = np.sin(ang), np.cos(ang)
        lo, hi = RAMPS["idle"]
        pts = self.pts[::2]  # subsample for speed (weak CPU)
        order = sorted(((-p[0] * sa + p[2] * ca), idx) for idx, p in enumerate(pts))
        for z, i in order:
            px0, py0, pz0 = pts[i]
            x = px0 * ca + pz0 * sa
            sc = focal / (focal + z * R)
            X = cx + x * R * sc
            Y = cy + py0 * R * sc
            depth = (z + 1) / 2.0
            rad = 1.1 + 2.0 * depth
            r = lo[0] + (hi[0] - lo[0]) * depth
            g = lo[1] + (hi[1] - lo[1]) * depth
            b = lo[2] + (hi[2] - lo[2]) * depth
            a = int(70 + 170 * depth)
            gr = rad * 2.4
            dr.ellipse([X - gr, Y - gr, X + gr, Y + gr],
                       fill=(_clamp(r), _clamp(g), _clamp(b), int(a * 0.28)))
            dr.ellipse([X - rad, Y - rad, X + rad, Y + rad],
                       fill=(_clamp(r), _clamp(g), _clamp(b), _clamp(a)))
        try:
            img = img.filter(ImageFilter.GaussianBlur(0.5))
        except Exception:
            pass
        return img

    def _panel_close(self):
        """Close the fullscreen search window (Esc). Also cuts off any
        in-progress JARVIS speech so the user isn't talked at after closing."""
        self._panel_speaking = False
        try:
            stop_audio()
        except Exception:
            pass
        try:
            if self.panel is not None:
                self.panel.destroy()
        except Exception:
            pass

    def _panel_show_typing(self):
        """Reveal the (normally hidden) typing field and focus it."""
        try:
            self.panel.focus_force()
            self._pulse_cv.itemconfig(self._entry_win, state="normal")
            self.panel_entry.focus_set()
        except Exception:
            pass

    def _panel_stop_speaking(self):
        """F5: cut JARVIS off mid-sentence in the search window."""
        self._panel_speaking = False
        stop_audio()

    def _panel_is_open(self):
        """True when the fullscreen search window is up on screen."""
        try:
            return (self.panel is not None
                    and tk.Toplevel.winfo_exists(self.panel)
                    and bool(self.panel.winfo_ismapped()))
        except Exception:
            return False

    # F-key dispatchers: when the search window is open the keys drive IT;
    # otherwise they keep their normal main-window jobs.
    def _key_f1(self):
        self._panel_show_typing() if self._panel_is_open() else self._open_typing()

    def _key_f2(self):
        self._panel_speak() if self._panel_is_open() else self._save_last_exchange()

    def _key_f3(self):
        self._panel_pick_image() if self._panel_is_open() else self._repeat_last()

    def _key_f5(self):
        # v4.3: F5 stops speech globally, not just in the search window.
        if self._panel_is_open():
            self._panel_stop_speaking()
        else:
            stop_audio()

    def _panel_pulse_tick(self):
        """Spin the orb every frame; show the amber pulse line ONLY while
        JARVIS is speaking."""
        if not (self.panel and tk.Toplevel.winfo_exists(self.panel)):
            return
        try:
            cv = self._pulse_cv
            if getattr(self, "_hud_time", None) is not None:
                now = datetime.datetime.now()
                cv.itemconfig(self._hud_time, text=now.strftime("%H:%M:%S"))
                cv.itemconfig(self._hud_date, text=now.strftime("%A, %d %B %Y"))
            if getattr(self, "_orb_frames", None):
                self._orb_idx = (self._orb_idx + 1) % len(self._orb_frames)
                cv.itemconfig(self._orb_item, image=self._orb_frames[self._orb_idx])
            if getattr(self, "_panel_speaking", False):
                cv.itemconfig(self._pulse_item, state="normal")
                cv.itemconfig(self._pulse_glow, state="normal")
                x0, x1, y = self._pulse_x0, self._pulse_x1, self._pulse_y
                ph = self._pulse_phase
                n = 70
                pts = []
                for i in range(n + 1):
                    t = i / n
                    env = np.sin(np.pi * t)
                    yv = y + 16.0 * env * (0.7 * np.sin(8 * t * np.pi + ph)
                                           + 0.3 * np.sin(15 * t * np.pi - ph * 1.7))
                    pts += [x0 + (x1 - x0) * t, yv]
                cv.coords(self._pulse_item, *pts)
                cv.coords(self._pulse_glow, *pts)
                self._pulse_phase += 0.5
            else:
                cv.itemconfig(self._pulse_item, state="hidden")
                cv.itemconfig(self._pulse_glow, state="hidden")
        except Exception:
            pass
        self.panel.after(60, self._panel_pulse_tick)

    def open_panel(self):
        """Create (or re-show) the fullscreen cinematic search window."""
        if self.panel is not None and tk.Toplevel.winfo_exists(self.panel):
            self.panel.deiconify()
            self.panel.lift()
            return
        c = self._UI
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        W, H = sw, sh
        w = tk.Toplevel(self.root)
        self.panel = w
        w.configure(bg=c["bg"])
        w.overrideredirect(True)        # borderless: no white title bar / Python icon
        w.geometry("%dx%d+0+0" % (W, H))
        w.attributes("-topmost", True)
        try:
            w.focus_force()
        except Exception:
            pass
        w.bind("<Escape>", lambda e: self._panel_close())

        cv = tk.Canvas(w, width=W, height=H, bg=c["bg"],
                       highlightthickness=0, bd=0)
        cv.pack(fill=tk.BOTH, expand=True)
        self._pulse_cv = cv
        self._cbtn_n = 0
        self._panel_link_n = 0
        self._panel_speaking = False

        cxm = W // 2
        orb_cy = int(H * 0.21)
        osize = max(180, min(int(min(W, H) * 0.26), 360))

        # --- top-left HUD: live clock + version + status + projects ---
        VER = "v4.16"
        hx = 44
        self._hud_time = cv.create_text(hx, 46, anchor="nw", text="00:00:00",
                                        fill=c["accent"], font=("Consolas", 30, "bold"))
        self._hud_date = cv.create_text(hx, 92, anchor="nw", text="",
                                        fill=c["muted"], font=("Consolas", 13))
        cv.create_text(hx, 130, anchor="nw", text="JARVIS  %s" % VER,
                       fill=c["text"], font=("Consolas", 12, "bold"))
        cv.create_text(hx, 152, anchor="nw", text="STATUS  \u00b7  ONLINE",
                       fill=c["accent2"], font=("Consolas", 11))
        cv.create_text(hx, 188, anchor="nw", text="PROJECTS", fill=c["muted"],
                       font=("Consolas", 11, "bold"))
        cv.create_text(hx, 210, anchor="nw", text="\u203a JARVIS  (this assistant)",
                       fill=c["text"], font=("Consolas", 11))

        # --- the real particle orb (pre-rendered frames cycled to spin it) ---
        self._orb_frames = []
        self._orb_idx = 0
        if self.use_pil:
            NF = 24
            for k in range(NF):
                pil = self._render_orb_frame(osize, (k / NF) * 2 * np.pi)
                self._orb_frames.append(ImageTk.PhotoImage(pil))
            self._orb_item = cv.create_image(cxm, orb_cy, image=self._orb_frames[0])
        else:
            self._orb_item = cv.create_oval(cxm - osize // 4, orb_cy - osize // 4,
                                            cxm + osize // 4, orb_cy + osize // 4,
                                            fill=c["accent"], outline="")

        # --- wordmark + subtitle (this IS the logo) ---
        title_y = orb_cy + osize // 2 + 18
        cv.create_text(cxm, title_y, text="ACHILLES", fill=c["accent"],
                       font=("Segoe UI", 30, "bold"))
        cv.create_text(cxm, title_y + 30, text="P R O D U C T   S E A R C H",
                       fill=c["muted"], font=("Segoe UI", 11, "bold"))

        # --- pulse line (hidden until JARVIS speaks) ---
        self._pulse_y = title_y + 64
        self._pulse_x0 = int(W * 0.30)
        self._pulse_x1 = int(W * 0.70)
        self._pulse_glow = cv.create_line(
            self._pulse_x0, self._pulse_y, self._pulse_x1, self._pulse_y,
            fill="#7a3d14", width=6, capstyle="round", joinstyle="round",
            smooth=True, state="hidden")
        self._pulse_item = cv.create_line(
            self._pulse_x0, self._pulse_y, self._pulse_x1, self._pulse_y,
            fill=c["accent"], width=2, capstyle="round", joinstyle="round",
            smooth=True, state="hidden")
        self._pulse_phase = 0.0

        # --- conversation text (transparent: same colour as the background) ---
        TX1, TX2 = int(W * 0.16), int(W * 0.84)
        TY1, TY2 = int(H * 0.42), int(H * 0.84)
        self.panel_out = tk.Text(cv, bg=c["bg"], fg=c["text"],
                                 insertbackground=c["text"], font=("Segoe UI", 13),
                                 wrap="word", relief=tk.FLAT, bd=0,
                                 highlightthickness=0, padx=10, pady=8)
        cv.create_window(TX1, TY1, anchor="nw", window=self.panel_out,
                         width=TX2 - TX1, height=TY2 - TY1)
        self.panel_out.bind("<MouseWheel>",
                            lambda e: self.panel_out.yview_scroll(int(-e.delta / 120), "units"))
        self.panel_out.configure(state="disabled")
        o = self.panel_out
        o.tag_config("you",    foreground=c["link"],   font=("Segoe UI", 13, "bold"))
        o.tag_config("jarvis", foreground=c["accent"], font=("Segoe UI", 13, "bold"))
        o.tag_config("sys",    foreground=c["muted"],  font=("Segoe UI", 11, "italic"))
        o.tag_config("body",   foreground=c["text"], spacing1=2, spacing3=12,
                     lmargin1=4, lmargin2=4)

        # --- hidden typing field (revealed by the Type button) ---
        self.panel_entry = tk.Entry(cv, bg=c["input"], fg=c["text"],
                                    insertbackground=c["accent"], relief=tk.FLAT,
                                    bd=0, highlightthickness=1,
                                    highlightbackground=c["divider"],
                                    highlightcolor=c["accent"], font=("Segoe UI", 13))
        self._entry_win = cv.create_window(cxm, int(H * 0.875), anchor="center",
                                           window=self.panel_entry,
                                           width=int(W * 0.5), height=38,
                                           state="hidden")
        self.panel_entry.bind("<Return>", lambda e: self._panel_ask_typed())

        # --- controls are F-keys now (kept off the screen, as requested) ---
        cv.create_text(cxm, int(H * 0.93),
                       text="F1  Type        F2  Speak        F3  Image        "
                            "F5  Stop        Esc  Close",
                       fill=c["muted"], font=("Segoe UI", 12))

        self._panel_write("JARVIS", "Ready, sir. Press F1 to write, F2 to speak, "
                          "or F3 to send a product image. F5 stops me speaking. I "
                          "search Israeli stores and reply in English unless you "
                          "write in Hebrew.")
        self._panel_pulse_tick()

    def _panel_write(self, who, text):
        """Append a line of plain text to the panel output."""
        if self.panel is None or not tk.Toplevel.winfo_exists(self.panel):
            return
        self.panel_out.configure(state="normal")
        tag = "you" if who == "You" else ("sys" if who == "System" else "jarvis")
        self.panel_out.insert("end", f"{who}  ", tag)
        self.panel_out.insert("end", text + "\n\n", "body")
        self.panel_out.see("end")
        self.panel_out.configure(state="disabled")

    def _panel_add_link(self, title, url):
        """Append a clickable link line to the panel output."""
        if self.panel is None or not tk.Toplevel.winfo_exists(self.panel):
            return
        c = self._UI
        self.panel_out.configure(state="normal")
        tagname = "link%d" % self._panel_link_n
        self._panel_link_n += 1
        self.panel_out.tag_config("bullet", foreground=c["accent"],
                                  font=("Segoe UI", 12, "bold"))
        self.panel_out.insert("end", "   \u203a  ", "bullet")
        self.panel_out.insert("end", (title or url) + "\n", (tagname,))
        self.panel_out.tag_config(tagname, foreground=c["link"], underline=True,
                                  spacing3=6)
        self.panel_out.tag_bind(tagname, "<Button-1>",
                                lambda e, u=url: webbrowser.open(u))
        self.panel_out.tag_bind(tagname, "<Enter>",
                                lambda e: self.panel_out.config(cursor="hand2"))
        self.panel_out.tag_bind(tagname, "<Leave>",
                                lambda e: self.panel_out.config(cursor=""))
        self.panel_out.see("end")
        self.panel_out.configure(state="disabled")

    def _panel_run(self, user_text, image_path=None):
        """Worker: run the search and render results into the panel + speak."""
        if self.panel_busy:
            return
        self.panel_busy = True
        try:
            # Search panel defaults to ENGLISH; switch to Hebrew only if the
            # user's text actually contains Hebrew letters.
            lang = "he" if is_hebrew(user_text or "") else "en"
            # v4.7: a greeting in the search window gives a briefing too
            # (skipped when an image is attached - that is a real search).
            bpart = None if image_path else detect_briefing(user_text)
            if bpart:
                self.ui(lambda: self._panel_write("System", "Briefing..."))
                brief = daily_briefing(bpart, lang)
                self.ui(lambda b=brief: self._panel_write("JARVIS", b))
                self._panel_speaking = True
                try:
                    speak(brief)
                finally:
                    self._panel_speaking = False
                return
            self.ui(lambda: self._panel_write("System", "Searching..."))
            spoken, links = search_with_optional_image(user_text, image_path, lang)
            def render():
                self._panel_write("JARVIS", spoken)
                if links:
                    self._panel_write("System", "Links (click to open):")
                    for t, u in links:
                        self._panel_add_link(t, u)
                else:
                    self._panel_write("System", "No links found.")
            self.ui(render)
            self._panel_speaking = True
            try:
                speak(spoken)
            except Exception:
                pass
            finally:
                self._panel_speaking = False
        finally:
            self.panel_busy = False

    def _panel_ask_typed(self):
        if self.panel is None or self.panel_busy:
            return
        txt = self.panel_entry.get().strip()
        if not txt:
            return
        self.panel_entry.delete(0, tk.END)
        try:
            self._pulse_cv.itemconfig(self._entry_win, state="hidden")
        except Exception:
            pass
        self._panel_write("You", txt)
        threading.Thread(target=self._panel_run, args=(txt,), daemon=True).start()

    def _panel_speak(self):
        """Record one spoken request and run it through the panel."""
        if self.panel is None or self.panel_busy or self.model is None:
            return
        def worker():
            self.ui(lambda: self._panel_write("System", "Listening... speak now."))
            af = record_until_silence()
            text, _lang = transcribe(self.model, af)
            text = (text or "").strip()
            if len(text) < 2:
                self.ui(lambda: self._panel_write("System", "I didn't catch that, sir."))
                return
            self.ui(lambda: self._panel_write("You", text))
            self._panel_run(text)
        threading.Thread(target=worker, daemon=True).start()

    def _panel_pick_image(self):
        if self.panel is None or self.panel_busy:
            return
        path = filedialog.askopenfilename(
            parent=self.panel, title="Choose a product image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.gif *.webp"),
                       ("All files", "*.*")])
        if not path:
            return
        self._panel_write("You", "[image] " + os.path.basename(path))
        prompt = self.panel_entry.get().strip() or "Identify this product and find where to buy it."
        self.panel_entry.delete(0, tk.END)
        threading.Thread(target=self._panel_run, args=(prompt, path), daemon=True).start()

    # ---- mode handling (main thread only) ----
    def _req(self, m):
        self.req_mode = m

    def _face_req(self):
        # v4.54: voice flows pop the old orb ONLY when the black-hole
        # face is disabled. F1/F2/F3 bypass this and use _req directly.
        if ACHILLES_FACE != "blackhole":
            self._req("expanded")
            # v4.67: apply on the main thread right now so the visual feedback
            # (the orb) pops the instant the wake fires, not on the next tick.
            try:
                self.ui(self._force_show)
            except Exception:
                pass

    def _hide(self):
        self.req_typing = False
        self.req_mode = "hidden"

    def _force_show(self):
        # v4.71: guard-free, unconditional re-show for the wake path. animate()'s
        # _apply_mode only reacts to a req_mode!=mode transition; if self.mode ever
        # desyncs from the real window state (it did after a hide/show cycle), the
        # orb stayed withdrawn on the next wake even though req_mode was "expanded".
        # This forces the window visible and to the front every time, and is safe
        # because it only runs on wake (not on every animation tick).
        self.mode = "expanded"
        self.req_mode = "expanded"
        try:
            self.root.deiconify()
            self.root.lift()
            # topmost off->on forces Windows to restack it above other windows,
            # fixing "deiconified but hidden behind something" on repeat wakes.
            self.root.attributes("-topmost", False)
            self.root.attributes("-topmost", True)
            self.root.update_idletasks()
        except Exception:
            pass

    def _apply_mode(self):
        if self.req_mode != self.mode:
            self.mode = self.req_mode
            if self.mode == "expanded":
                self.root.deiconify()
                self.root.lift()
                self.root.attributes("-topmost", True)
            else:
                self.root.withdraw()
        if self.req_typing != self.typing:
            self.typing = self.req_typing
            if self.typing and self.mode == "expanded":
                self.entry.place(relx=0.5, rely=1.0, y=-12, anchor="s", relwidth=0.82)
                self.entry.focus_set()
            else:
                self.entry.place_forget()

    # ---- interactions ----
    def _show_menu(self, e):
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    def _drag_start(self, e):
        self._drag = (e.x, e.y)
        self._moved = False

    def _drag_move(self, e):
        self._moved = True
        x = self.root.winfo_x() + e.x - self._drag[0]
        y = self.root.winfo_y() + e.y - self._drag[1]
        self.root.geometry("+%d+%d" % (x, y))
        self.ex, self.ey = x, y

    def _open_typing(self):
        self._req("expanded")
        self.req_typing = True

    def _save_last_exchange(self):
        """F2: save the last full exchange (you + JARVIS) as an Obsidian note."""
        if not self._last_user and not self._last_reply:
            self._req("expanded")
            self._push("System", "Nothing to save yet, sir.")
            return
        note = f"You: {self._last_user}\n  JARVIS: {self._last_reply}"
        status = save_note(note)
        self._req("expanded")
        self._push("System", status)

    def _repeat_last(self):
        """F3: repeat JARVIS's last spoken reply aloud. Works even mid-listen,
        because pressing F3 is an explicit request."""
        if not self._last_reply:
            self._req("expanded")
            self._push("System", "I haven't said anything yet, sir.")
            return
        self._req("expanded")
        self._push("System", "Repeating last reply.")
        threading.Thread(target=lambda: speak(self._last_reply), daemon=True).start()

    # ---- control actions ----
    def talk(self, collapse_after):
        if not self.busy and self.model is not None:
            self._face_req()
            threading.Thread(target=self._turn, args=(False, collapse_after),
                             daemon=True).start()

    def _send_typed(self, _e=None):
        if self.busy or self.model is None:
            return
        txt = self.entry.get().strip()
        if not txt:
            return
        self.entry.delete(0, tk.END)
        threading.Thread(target=self._typed_turn, args=(txt,), daemon=True).start()

    def toggle_wake(self):
        self.wake_on = not self.wake_on

    def quit(self):
        self.stop = True
        try:
            if os.path.exists(SHOW_SIGNAL):
                os.remove(SHOW_SIGNAL)
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            os._exit(0)

    # ---- shared state ----
    def _push(self, who, text):
        with self._lock:
            self.outbox.append({"who": who, "text": text})

    def status_text(self):
        s = self.state
        if s == "loading":
            return "Loading models..."
        if s == "listening":
            return "Listening...  (say 'write' to type)"
        if s == "thinking":
            return "Thinking..."
        if s == "speaking":
            return "Speaking..."
        if self.typing:
            return "Type and press Enter"
        return "Listening for 'Hey JARVIS'" if self.wake_on else "Wake word OFF"

    # ---- desktop-icon signal watcher ----
    def _signal_watch(self):
        while not self.stop:
            try:
                if os.path.exists(SHOW_SIGNAL):
                    os.remove(SHOW_SIGNAL)
                    if not self.busy:
                        self.talk(collapse_after=True)
            except Exception:
                pass
            time.sleep(0.4)

    # ---- worker logic ----
    def _boot(self):
        ensure_directories()
        self.state = "loading"
        self._face_req()
        # v4.73: the Whisper "tiny" wake model was retired when wake detection
        # moved to Vosk (v4.70); it was still being loaded here but never read,
        # wasting RAM. Only the "small" model (used for command transcription)
        # is loaded now.
        self.model = WhisperModel("small", device="cpu", compute_type="int8")
        self.memory = load_long_term_memory()
        if not ANTHROPIC_API_KEY:
            self.state = "idle"
            self._push("System", "No API key found in .env")
            return
        self.state = "idle"
        self.wake_on = True
        self._push("System", "Achilles online, sir.")
        try:
            speak("Achilles online, sir.")
        except Exception:
            pass
        # v4.54: open the black-hole face window - the assistant's
        # visual face from now on. Daemon thread so boot never blocks.
        if ACHILLES_FACE == "blackhole":
            def _open_face():
                try:
                    time.sleep(1.0)
                    print("[face]", open_achilles("core", face=True), flush=True)
                except Exception as e:
                    print("[diag] face window failed:", repr(e), flush=True)
            threading.Thread(target=_open_face, daemon=True).start()
        time.sleep(1.6)
        # v4.5: first launch of the day -> automatic briefing by clock.
        try:
            self._maybe_auto_briefing()
        except Exception as e:
            print("[diag] auto-briefing failed:", repr(e), flush=True)
        try:
            self._maybe_auto_backup()
        except Exception as e:
            print("[diag] auto-backup failed:", repr(e), flush=True)
        self._hide()
        threading.Thread(target=self._wake_loop, daemon=True).start()
        # Global hotkeys: work anywhere in Windows, even when the orb is hidden.
        # Handlers marshal back to the main thread via self.ui() because tkinter
        # isn't thread-safe.
        if HAVE_KEYBOARD:
            try:
                keyboard.add_hotkey("f1", lambda: self.ui(self._key_f1))
                keyboard.add_hotkey("f2", lambda: self.ui(self._key_f2))
                keyboard.add_hotkey("f3", lambda: self.ui(self._key_f3))
                keyboard.add_hotkey("f5", lambda: self.ui(self._key_f5))
            except Exception as e:
                print("Hotkey registration failed:", e)

    def _maybe_auto_briefing(self):
        """v4.5: on the first launch of a calendar day, greet with a short
        briefing chosen by the clock. Tracked via .jarvis_last_briefing so it
        fires only once per day."""
        marker = Path(".jarvis_last_briefing")
        today = datetime.date.today().isoformat()
        try:
            if marker.exists() and marker.read_text(encoding="utf-8").strip() == today:
                return  # already briefed today
        except Exception:
            pass
        try:
            marker.write_text(today, encoding="utf-8")
        except Exception:
            pass
        part = _briefing_part_from_clock(datetime.datetime.now())
        self._face_req()
        self.state = "thinking"
        brief = daily_briefing(part, "en")
        self._push("JARVIS", brief)
        self._last_reply = brief
        self.state = "speaking"
        try:
            speak(brief)
        except Exception:
            pass
        time.sleep(min(14.0, max(3.0, len(brief.split()) * 0.45)))

    def _maybe_auto_backup(self):
        """v4.31: first launch of a calendar day -> background vault
        backup. Tracked via .jarvis_last_backup so it fires only once
        per day. Runs in a daemon thread so the wake-loop is not
        delayed by zip compression."""
        marker = Path(".jarvis_last_backup")
        today = datetime.date.today().isoformat()
        try:
            if marker.exists() and marker.read_text(
                    encoding="utf-8").strip() == today:
                return  # already backed up today
        except Exception:
            pass
        try:
            marker.write_text(today, encoding="utf-8")
        except Exception:
            pass
        threading.Thread(target=backup_vault, daemon=True).start()


    def _turn(self, announce, collapse_after):
        try:
            try:
                with open("wake_diag.log", "a", encoding="utf-8") as _wf:
                    _wf.write("[turn] entered announce=%s\n" % (announce,))
            except Exception:
                pass
            self.busy = True
            if announce:
                beep()
            # First turn of this exchange
            keep_going = self._one_exchange(first=True)
            # Continuous conversation: after answering, listen for a follow-up
            # for a few seconds. If the user speaks, keep the conversation going
            # WITHOUT needing "Hey JARVIS" again. Silence ends the exchange.
            while keep_going and not self.stop:
                keep_going = self._one_exchange(first=False)
        except Exception as e:
            try:
                with open("wake_diag.log", "a", encoding="utf-8") as _wf:
                    _wf.write("[turn-error] %r\n" % (e,))
            except Exception:
                pass
            self._push("System", "Error: " + str(e))
        finally:
            self.busy = False
            self.state = "idle"
            if collapse_after and not self.typing:
                time.sleep(1.0)
                self._hide()

    def _one_exchange(self, first):
        """Listen once, answer once. Returns True if we should keep listening
        for a follow-up (conversation mode), False to end."""
        self.state = "listening"
        if first:
            # use the pre-roll captured at wake time so the first word survives
            pr = getattr(self, "_preroll", None)
            self._preroll = None
            af = record_until_silence(preroll=pr)
        else:
            # follow-up: give up if no speech starts within a few seconds
            af = record_followup(start_timeout=5.0)
            if af is None:
                return False  # no follow-up -> end the conversation
        self.state = "thinking"
        user_text, lang = transcribe(self.model, af)
        try:
            with open("wake_diag.log", "a", encoding="utf-8") as _wf:
                _wf.write("[cmd first=%s] af=%r text=%r lang=%r\n" % (first, af, user_text, lang))
        except Exception:
            pass
        # The pre-roll may include the wake word itself ("Hey Jarvis"); strip it
        # from the front of the command so it isn't treated as part of the query.
        if first and user_text:
            user_text = strip_wake_prefix(user_text)
        # Noise filter: a real command is rarely just one or two stray
        # characters. Whisper turns keyboard clacks / coughs into empty text or
        # tiny fragments, so we discard anything too short to be a real command.
        cleaned = (user_text or "").strip()
        if len(cleaned) < 3 or not re.search(r'[A-Za-z\u0590-\u05FF]', cleaned):
            # v4.12: if this is the FIRST turn right after the wake word
            # and we heard nothing useful, the user most likely said only
            # "Hey JARVIS" and then paused, waiting for an acknowledgement,
            # instead of giving the command in the same breath. So we
            # acknowledge and keep listening for the command, instead of
            # going straight back to sleep (which used to force a second
            # "Hey JARVIS").
            if first:
                ack = "כן, אדוני?" if lang == "he" else "Yes, sir?"
                self._push("JARVIS", ack)
                self.state = "speaking"
                speak(ack)
                return True   # keep listening; the follow-up turn catches the command
            return False  # nothing meaningful was said -> ignore (likely noise)
        # "write" opens the typing box instead of answering
        if detect_write(user_text) and len(user_text.split()) <= 3:
            self._req("expanded")
            self.req_typing = True
            self._push("System", "Typing enabled. Go ahead, sir.")
            return False
        # v4.5: a spoken greeting -> daily briefing instead of a normal answer.
        bpart = detect_briefing(user_text)
        if bpart:
            self._push("You", user_text)
            self.state = "thinking"
            blang = "he" if (lang == "he" or is_hebrew(user_text)) else "en"
            brief = daily_briefing(bpart, blang)
            self._push("JARVIS", brief)
            save_log(user_text, brief)
            self._last_user = user_text
            self._last_reply = brief
            self.state = "speaking"
            speak(brief)
            time.sleep(min(14.0, max(3.0, len(brief.split()) * 0.45)))
            return False  # v4.72: end after the briefing; wake again for more
        # Graceful goodbye: if the user is clearly ending the chat, give a short
        # sign-off (in their language) instead of silently closing.
        if detect_goodbye(user_text):
            bye = pick_farewell(lang == "he" or is_hebrew(user_text))
            self._push("You", user_text)
            self._push("JARVIS", bye)
            save_log(user_text, bye)
            self._last_user = user_text
            self._last_reply = bye
            self.state = "speaking"
            speak(bye)
            time.sleep(min(8.0, max(2.0, len(bye.split()) * 0.45)))
            return False  # end the conversation after the farewell
        self._push("You", user_text)
        # Lock reply language to what Whisper detected (he/en), so Hebrew speech
        # always gets a Hebrew answer even if the transcript is imperfect.
        reply = think(user_text, self.memory, lang)
        # v3.14: the brain marks a dismissal/goodbye (in ANY wording) by ending
        # its reply with the token <END>. If we see it, strip it from what we
        # show/speak and end the conversation after this turn.
        end_now = bool(re.search(r'<\s*END\s*>', reply, re.IGNORECASE))
        if end_now:
            reply = re.sub(r'<\s*END\s*>', '', reply, flags=re.IGNORECASE).strip()
            if not reply:
                reply = pick_farewell(lang == "he")
        self._push("JARVIS", reply)
        save_log(user_text, reply)
        # Remember this exchange for the function keys (F2 save / F3 repeat).
        self._last_user = user_text
        self._last_reply = reply
        self.state = "speaking"
        speak(reply)
        time.sleep(min(12.0, max(2.0, len(reply.split()) * 0.45)))
        return False  # v4.72: one command per wake - end after answering so
        # background noise can't trip an endless follow-up/hallucinate loop.
        # (Say the wake word again for another command; it's instant now.)

    def _typed_turn(self, text):
        try:
            self.busy = True
            self._push("You", text)
            self.state = "thinking"
            # For typed text, detect language directly from the characters.
            lang = "he" if is_hebrew(text) else "en"
            # v4.7: a typed greeting -> daily briefing instead of a normal answer.
            bpart = detect_briefing(text)
            if bpart:
                brief = daily_briefing(bpart, lang)
                self._push("JARVIS", brief)
                save_log(text, brief)
                self._last_user = text
                self._last_reply = brief
                self.state = "speaking"
                speak(brief)
                time.sleep(min(14.0, max(3.0, len(brief.split()) * 0.45)))
                return
            reply = think(text, self.memory, lang)
            self._push("JARVIS", reply)
            save_log(text, reply)
            # Remember this exchange for the function keys (F2 save / F3 repeat).
            self._last_user = text
            self._last_reply = reply
            self.state = "speaking"
            speak(reply)
            time.sleep(min(12.0, max(2.5, len(reply.split()) * 0.45)))
        except Exception as e:
            self._push("System", "Error: " + str(e))
        finally:
            self.busy = False
            self.state = "idle"

    def _telegram_turn(self, text):
        """Run the brain on a Telegram message - text only, no voice."""
        lang = "he" if is_hebrew(text) else "en"
        bpart = detect_briefing(text)
        if bpart:
            return daily_briefing(bpart, lang)
        return think(text, self.memory, lang)

    def _telegram_loop(self):
        global _tg_offset, _tg_pair_code
        if not TELEGRAM_BOT_TOKEN:
            return
        import random
        _tg_load_chat()
        time.sleep(3)  # let _boot finish loading long-term memory first
        if _tg_chat_id is None:
            _tg_pair_code = "%06d" % random.randint(0, 999999)
            try:
                with open(str(Path(__file__).resolve().parent
                              / "telegram_pairing.txt"), "w",
                          encoding="utf-8") as _pf:
                    _pf.write("JARVIS Telegram pairing code: " + _tg_pair_code
                              + "  (send this code to your bot to link it)")
            except Exception:
                pass
            try:
                self._push("JARVIS", "\u05d8\u05dc\u05d2\u05e8\u05dd: "
                           "\u05e9\u05dc\u05d7 \u05dc\u05d1\u05d5\u05d8 "
                           "\u05d0\u05ea \u05d4\u05e7\u05d5\u05d3 " + _tg_pair_code
                           + " \u05db\u05d3\u05d9 \u05dc\u05d7\u05d1\u05e8.")
            except Exception:
                pass
            print("[telegram] pairing code: " + _tg_pair_code, flush=True)
        else:
            print("[telegram] paired with chat %s - listening." % _tg_chat_id,
                  flush=True)
        # drain backlog so we don't replay old messages from before startup
        r0 = _tg_api("getUpdates", {"timeout": 0, "offset": -1}, timeout=10)
        if r0 and r0.get("ok") and r0.get("result"):
            _tg_offset = r0["result"][-1]["update_id"] + 1
        while not self.stop:
            r = _tg_api("getUpdates",
                        {"timeout": 50, "offset": _tg_offset}, timeout=60)
            if not r or not r.get("ok"):
                time.sleep(3)
                continue
            for upd in r.get("result", []):
                _tg_offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg or "text" not in msg:
                    continue
                cid = msg["chat"]["id"]
                text = msg["text"].strip()
                if not text:
                    continue
                # --- pairing (only while unpaired) ---
                if _tg_chat_id is None:
                    if _tg_pair_code and text == _tg_pair_code:
                        _tg_save_chat(cid)
                        try:
                            os.remove(str(Path(__file__).resolve().parent
                                          / "telegram_pairing.txt"))
                        except Exception:
                            pass
                        telegram_send("\u05de\u05d7\u05d5\u05d1\u05e8. JARVIS "
                                      "\u05e6\u05de\u05d5\u05d3 \u05d0\u05dc\u05d9\u05da "
                                      "\u05e2\u05db\u05e9\u05d9\u05d5, \u05d0\u05d3\u05d5\u05e0\u05d9. "
                                      "\u05e9\u05dc\u05d7 \u05dc\u05d9 \u05db\u05dc \u05d3\u05d1\u05e8.",
                                      cid)
                        try:
                            self._push("JARVIS", "Telegram paired.")
                        except Exception:
                            pass
                    else:
                        telegram_send("\u05e9\u05dc\u05d7 \u05d0\u05ea \u05e7\u05d5\u05d3 "
                                      "\u05d4\u05e6\u05d9\u05de\u05d5\u05d3 \u05e9\u05de\u05d5\u05e4\u05d9\u05e2 "
                                      "\u05e2\u05dc JARVIS \u05db\u05d3\u05d9 \u05dc\u05d7\u05d1\u05e8.",
                                      cid)
                    continue
                # --- authorized chat only ---
                if cid != _tg_chat_id:
                    telegram_send("\u05dc\u05d0 \u05de\u05d5\u05e8\u05e9\u05d4.", cid)
                    continue
                # --- run the brain (serialize with voice/typed turns) ---
                waited = 0.0
                while self.busy and waited < 60:
                    time.sleep(0.5); waited += 0.5
                self.busy = True
                try:
                    _tg_api("sendChatAction",
                            {"chat_id": cid, "action": "typing"}, timeout=10)
                    reply = self._telegram_turn(text)
                except Exception as e:
                    reply = "Error: " + str(e)
                finally:
                    self.busy = False
                telegram_send(reply or "(no reply)", cid)
                try:
                    self._push("Telegram", text)
                    self._push("JARVIS", reply)
                except Exception:
                    pass

    def _wake_loop(self):
        # v4.70: Vosk streaming wake detection (replaces the Whisper wake path).
        # A small en-us model with a fixed grammar recognizes the wake word
        # reliably and near-instantly, with essentially no hallucinated
        # false-fires. The model is loaded once and cached locally.
        try:
            import queue as _queue
            from vosk import Model as _VoskModel, KaldiRecognizer as _KaldiRec
        except Exception as e:
            print("[diag] Vosk import failed, wake disabled:", repr(e), flush=True)
            try:
                self._push("System", "Vosk not installed - wake word disabled, sir.")
            except Exception:
                pass
            return
        try:
            _vmodel = _VoskModel(lang="en-us")
        except Exception as e:
            print("[diag] Vosk model load failed:", repr(e), flush=True)
            try:
                self._push("System", "Vosk model failed to load, sir.")
            except Exception:
                pass
            return
        _GRAMMAR = '["achilles", "hey achilles", "[unk]"]'
        pre_len = int(SAMPLE_RATE * PREROLL_SEC)
        blk = int(SAMPLE_RATE * 0.15)
        print("[wake] Vosk wake engine ready (say 'Achilles').", flush=True)

        while not self.stop:
            if not self.wake_on or self.busy:
                time.sleep(0.2)
                continue
            rec = _KaldiRec(_vmodel, SAMPLE_RATE, _GRAMMAR)
            rec.SetWords(True)
            q = _queue.Queue()
            pre = {"buf": np.zeros(pre_len, dtype=np.float32)}

            def cb(indata, frames, t_info, status, _q=q, _pre=pre):
                x = indata[:, 0]
                _q.put((np.clip(x, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes())
                n = len(x)
                b = _pre["buf"]
                b = np.roll(b, -n)
                b[-n:] = x
                _pre["buf"] = b

            triggered = False
            try:
                with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                    dtype='float32', blocksize=blk, callback=cb):
                    while not self.stop and self.wake_on and not self.busy:
                        try:
                            data = q.get(timeout=0.3)
                        except _queue.Empty:
                            continue
                        hit = False
                        if rec.AcceptWaveform(data):
                            # v4.73: fire ONLY on a finalized segment that is
                            # cleanly the wake word - "achilles" present, NO
                            # out-of-vocabulary "[unk]" token mixed in, and
                            # short. Background video/music decodes as runs of
                            # "[unk]", so this rejects the false-fire storm.
                            _res = json.loads(rec.Result())
                            _txt = _res.get("text", "").strip()
                            _toks = _txt.split()
                            hit = ("achilles" in _toks and "[unk]" not in _toks
                                   and 1 <= len(_toks) <= 6)
                            if _txt:
                                _cf = [w.get("conf", 1.0)
                                       for w in _res.get("result", [])
                                       if w.get("word") == "achilles"]
                                _mc = min(_cf) if _cf else 1.0
                                try:
                                    with open("wake_diag.log", "a", encoding="utf-8") as _wf:
                                        _wf.write("[heard] vosk final=%r conf=%.2f wake=%s\n"
                                                  % (_txt, _mc, hit))
                                except Exception:
                                    pass
                        # partials are intentionally ignored now (they
                        # fluctuate and caused constant false triggers).
                        if hit:
                            triggered = True
                            self._preroll = pre["buf"].copy()
                            break
            except Exception as e:
                print("[diag] wake-loop mic reopen failed, retrying:", repr(e), flush=True)
                try:
                    self._push("System", "Microphone unavailable - retrying. "
                               "Close other apps using the mic, sir.")
                except Exception:
                    pass
                time.sleep(0.6)
            if triggered:
                try:
                    with open("wake_diag.log", "a", encoding="utf-8") as _wf:
                        _wf.write("[trigger] firing _turn\n")
                except Exception:
                    pass
                self._push("System", "Wake word detected.")
                self._face_req()
                self._turn(True, collapse_after=True)
                time.sleep(0.6)

    # ---- Pillow renderer ----
    # ---- v4.57: BLACK HOLE face (drawn inside this same window) -----------
    def _bh_build_async(self):
        """Pre-render the black-hole layers off the UI thread."""
        try:
            self._bh_make_layers(520)
            print("[face] black-hole layers ready", flush=True)
        except Exception as e:
            print("[diag] black-hole prerender failed, keeping orb:", repr(e),
                  flush=True)

    def _bh_make_layers(self, S):
        """Build all static/animated layers once with numpy + PIL."""
        NF = 24
        ax = np.linspace(-1.0, 1.0, S, dtype=np.float32)
        x, y = np.meshgrid(ax, ax)
        yd = y / 0.26                      # squash = camera tilt over the disk
        r = np.sqrt(x * x + yd * yd)
        th = np.arctan2(yd, x)
        rc = np.sqrt(x * x + y * y)        # true screen-space radius
        RH, D1, D2 = 0.28, 0.34, 0.93      # shadow / disk inner / disk outer
        hot = np.clip(1.0 - (r - D1) / (D2 - D1), 0.0, 1.0)
        ring = (np.clip((r - D1) / 0.06, 0.0, 1.0)
                * np.clip((D2 - r) / 0.18, 0.0, 1.0))
        dop = np.clip(1.0 + 0.75 * np.cos(th), 0.45, 1.8) ** 1.3
        front_m = np.clip(y / 0.05, 0.0, 1.0)    # near half passes IN FRONT
        back_m = 1.0 - front_m

        def to_img(cr, cg, cb, a, mask=None):
            if mask is not None:
                a = a * mask
            arr = (np.dstack([np.clip(cr, 0, 1), np.clip(cg, 0, 1),
                              np.clip(cb, 0, 1), np.clip(a, 0, 1)])
                   * 255).astype(np.uint8)
            return Image.fromarray(arr, "RGBA")

        fronts, backs = [], []
        for k in range(NF):
            ph = (k / float(NF)) * 2.0 * np.pi
            # v4.58: the whole texture is a function of (theta - phase),
            # so material streaks SWEEP coherently around the ring while
            # the doppler bright side stays fixed in space - real rotation.
            ta = th - ph
            sw = (0.62 + 0.30 * np.sin(2.0 * ta + r * 3.0)
                  + 0.16 * np.sin(5.0 * ta + r * 9.0)
                  + 0.07 * np.sin(11.0 * ta - r * 16.0)
                  + 0.04 * np.sin(23.0 * ta + r * 31.0))
            em = ring * (0.30 + 1.35 * hot ** 1.6) * np.clip(sw, 0.05, 2.0) * dop
            em = np.clip(em, 0.0, 1.6)
            cr = (0.55 + 0.50 * hot) * em
            cg = (0.20 + 0.62 * hot) * em
            cb = (0.06 + 0.50 * hot) * em
            a = em * 1.4

            def with_glow(im):
                try:
                    g = im.filter(ImageFilter.GaussianBlur(8))
                    g.alpha_composite(im)
                    return g
                except Exception:
                    return im
            fronts.append(with_glow(to_img(cr, cg, cb, a, front_m)))
            backs.append(with_glow(to_img(cr * 0.85, cg * 0.85, cb * 0.85,
                                          a, back_m)))

        # lensed halo arcing over the top of the shadow
        halo = np.clip(1.0 - np.abs(rc - RH * 1.14) / 0.045, 0.0, 1.0) ** 1.5
        upper = np.clip((-y + 0.05) / 0.45, 0.0, 1.0)
        lower = np.clip((y - 0.10) / 0.50, 0.0, 1.0)
        hdop = np.clip(1.0 - 0.55 * np.cos(np.arctan2(y, x)), 0.45, 1.6)
        hem = halo * (0.10 + 1.05 * upper + 0.50 * lower) * hdop
        arc = to_img(0.98 * hem, 0.66 * hem, 0.36 * hem, hem)

        # thin photon ring hugging the shadow
        pr = np.clip(1.0 - np.abs(rc - RH * 1.02) / 0.020, 0.0, 1.0) ** 1.1
        rdop = np.clip(1.0 + 0.30 * x / np.maximum(rc, 1e-4), 0.65, 1.35)
        pr = pr * rdop
        ring_img = to_img(1.0 * pr, 0.82 * pr, 0.55 * pr, pr)

        # the event horizon: pure black, razor edge
        zer = np.zeros_like(rc)
        sh_a = np.clip((RH - rc) / 0.012 + 1.0, 0.0, 1.0)
        shadow = to_img(zer, zer, zer, sh_a)

        # v4.58: clean PURE-BLACK disc backdrop, crisp edge, no stars -
        # exactly the user's spec: black circle -> black hole -> ring.
        edge = np.clip((0.985 - rc) / 0.012, 0.0, 1.0)
        stars = to_img(np.full_like(rc, 0.004), np.full_like(rc, 0.004),
                       np.full_like(rc, 0.008), edge)

        self._bhL = {"S": S, "NF": NF, "stars": stars, "front": fronts,
                     "back": backs, "arc": arc, "ring": ring_img,
                     "shadow": shadow}

    def _render_bh(self, Wc, Hc, st, now):
        """The black hole IS the orb now: same window, same states, new
        face. Falls back to the particle orb until layers are ready."""
        L = getattr(self, "_bhL", None)
        if L is None:
            return self._render_pil(Wc, Hc, st, now)
        S = L["S"]

        if st == "listening":
            spd, boost = 2.2, 1.35
        elif st == "thinking":
            spd, boost = 3.0, 0.55
        elif st == "speaking":
            spd, boost = 1.6, 1.25 + 0.30 * abs(np.sin(now / 160.0))
        else:
            spd, boost = 1.0, (0.55 if st == "loading" else 1.0)
        # v4.62: very slow majestic spin (~45s/rev at idle) + cross-fade
        # between adjacent baked frames -> perfectly SMOOTH at any speed.
        self._bh_ph = (self._bh_ph + 0.045 * spd) % L["NF"]
        i = int(self._bh_ph)
        j = (i + 1) % L["NF"]
        f = self._bh_ph - i
        front = Image.blend(L["front"][i], L["front"][j], f)
        back = Image.blend(L["back"][i], L["back"][j], f)
        if abs(boost - 1.0) > 0.03:
            front = ImageEnhance.Brightness(front).enhance(boost)
            back = ImageEnhance.Brightness(back).enhance(boost)

        img = L["stars"].copy()
        img.alpha_composite(back)
        img.alpha_composite(L["arc"])
        img.alpha_composite(L["shadow"])
        img.alpha_composite(L["ring"])
        img.alpha_composite(front)
        dr = ImageDraw.Draw(img)

        if st == "thinking":
            # a captured blue star orbits the hole; camera leans in on it
            self._bh_star_a += 0.045
            px = S / 2.0 + np.cos(self._bh_star_a) * S * 0.30
            py = S / 2.0 + np.sin(self._bh_star_a) * S * 0.10 - S * 0.05
            gg = 0.7 + 0.3 * np.sin(now / 110.0)
            for rad, alp in ((9.0, 60), (5.0, 130), (2.4, 255)):
                dr.ellipse([px - rad, py - rad, px + rad, py + rad],
                           fill=(int(160 + 60 * gg), int(200 + 40 * gg), 255,
                                 int(alp * gg)))
            z = 1.45
            cw = S / z
            cxz = min(max(px, cw / 2.0), S - cw / 2.0)
            cyz = min(max(py, cw / 2.0), S - cw / 2.0)
            img = img.crop((int(cxz - cw / 2), int(cyz - cw / 2),
                            int(cxz + cw / 2), int(cyz + cw / 2)))
            img = img.resize((S, S), Image.LANCZOS)
            dr = ImageDraw.Draw(img)

        if self.ripple_on:                       # speaking ripple, as before
            self.ripple += 0.02
            if self.ripple >= 1.0:
                self.ripple_on = False
            else:
                rr = self.ripple * S * 0.62
                aa = int(max(0, (1 - self.ripple) * 180))
                dr.ellipse([S / 2 - rr, S / 2 - rr, S / 2 + rr, S / 2 + rr],
                           outline=(255, 150, 70, aa), width=2)

        D = max(2, int(min(Wc, Hc) * 0.97))
        img = img.resize((D, D), Image.LANCZOS)
        out = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
        out.alpha_composite(img, (int(Wc / 2 - D / 2),
                                  int(Hc / 2 - D / 2 - 12)))
        return ImageTk.PhotoImage(out)

    def _render_pil(self, Wc, Hc, st, now):
        SS = self.SS
        W, H = Wc * SS, Hc * SS
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        R = min(W, H) * 0.30
        focal = R * 2.6
        cx, cy = W / 2.0, H / 2.0 - 14 * SS

        # warm backing disc, a bit larger than the sphere (skip while zoomed in)
        if st != "thinking":
            disc_r = R * 1.55
            disc = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dd = ImageDraw.Draw(disc)
            steps = 26
            for k in range(steps):
                t = k / (steps - 1.0)
                rr = disc_r * (1.0 - t)
                cc = (int(40 + 90 * t), int(15 + 35 * t), int(8 + 12 * t), 255)
                dd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=cc)
            try:
                disc = disc.filter(ImageFilter.GaussianBlur(SS * 1.2))
            except Exception:
                pass
            img.alpha_composite(disc)
            dr = ImageDraw.Draw(img)

        spin = 0.0015 if st == "thinking" else (0.006 if st == "listening" else 0.0035)
        self.ang += spin
        pulse = 1.0
        if st == "listening":
            pulse = 1 + 0.06 * np.sin(now / 130.0)
        elif st == "idle":
            pulse = 1 + 0.02 * np.sin(now / 700.0)
        tzoom = 2.3 if st == "thinking" else 1.0
        self.zoom += (tzoom - self.zoom) * 0.10
        zc = min(self.zoom, 1.5)

        sa, ca = np.sin(self.ang), np.cos(self.ang)
        ox = oy = 0.0
        if st == "thinking":
            spx, spy, spz = self.pts[self.sel]
            sx0 = spx * ca + spz * sa
            sz0 = -spx * sa + spz * ca
            sc0 = focal / (focal + sz0 * R)
            ox = sx0 * R * sc0
            oy = spy * R * sc0

        lo, hi = RAMPS.get(st, RAMPS["idle"])
        # sort back-to-front for nicer overlap
        order = []
        for i in range(self.N):
            px0, py0, pz0 = self.pts[i]
            z = -px0 * sa + pz0 * ca
            order.append((z, i))
        order.sort()

        selX = selY = None
        selR = 2.0
        for z, i in order:
            px0, py0, pz0 = self.pts[i]
            x = px0 * ca + pz0 * sa
            y = py0
            sc = focal / (focal + z * R) * pulse
            X = cx + (x * R * sc - ox) * self.zoom
            Y = cy + (y * R * sc - oy) * self.zoom
            depth = (z + 1) / 2.0
            rad = (1.3 + 2.3 * depth) * zc * SS
            r = lo[0] + (hi[0] - lo[0]) * depth
            g = lo[1] + (hi[1] - lo[1]) * depth
            b = lo[2] + (hi[2] - lo[2]) * depth
            a = int(70 + 170 * depth)
            if st == "thinking" and i == self.sel:
                r, g, b, a = 235, 248, 255, 255
                rad *= 2.4
                selX, selY, selR = X, Y, rad
            elif st == "thinking":
                a = int(a * 0.4)
            # soft glow halo
            gr = rad * 2.4
            dr.ellipse([X - gr, Y - gr, X + gr, Y + gr],
                       fill=(_clamp(r), _clamp(g), _clamp(b), int(a * 0.28)))
            dr.ellipse([X - rad, Y - rad, X + rad, Y + rad],
                       fill=(_clamp(r), _clamp(g), _clamp(b), _clamp(a)))

        if st == "thinking" and selX is not None:
            gg = 0.5 + 0.4 * np.sin(now / 110.0)
            rr = selR + (10 + 3 * np.sin(now / 110.0)) * SS
            dr.ellipse([selX - rr, selY - rr, selX + rr, selY + rr],
                       outline=(255, _clamp(170 * gg + 40), _clamp(40 * gg + 10),
                                220), width=max(1, SS))

        if self.ripple_on:
            self.ripple += 0.02
            if self.ripple >= 1.0:
                self.ripple_on = False
            else:
                rr = self.ripple * R * 2.0
                aa = int(max(0, (1 - self.ripple) * 180))
                dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                           outline=(255, 140, 50, aa), width=max(1, int(2 * SS)))

        if SS != 1:
            img = img.resize((Wc, Hc), Image.LANCZOS)
        # soft overall bloom
        try:
            img = img.filter(ImageFilter.GaussianBlur(0.4))
        except Exception:
            pass
        return ImageTk.PhotoImage(img)

    # ---- animation (main thread) ----
    def animate(self):
        # v4.67 CRITICAL: this method MUST always reschedule itself, or the whole
        # display loop dies and the orb can never appear again on the next wake
        # (req_mode is set to "expanded" but nothing ever applies it). So the
        # body is guarded and the after() reschedule lives in finally.
        if self.stop:
            return
        delay = 33
        try:
            self._apply_mode()

            with self._lock:
                msgs = self.outbox
                self.outbox = []
            for m in msgs:
                txt = m["text"]
                if len(txt) > 66:
                    txt = txt[:63] + "..."
                self._hold = txt
                self._hold_until = time.time() + 4.0

            st = self.state
            if st != self.prev:
                if st == "thinking":
                    self.sel = int(np.random.randint(0, self.N))
                if st == "speaking":
                    self.ripple = 0.0
                    self.ripple_on = True
                self.prev = st

            if self.mode != "expanded":
                delay = 80
            else:
                Wc = max(self.cv.winfo_width(), 1)
                Hc = max(self.cv.winfo_height(), 1)
                now = time.time() * 1000.0

                if self.use_pil and Wc > 2 and Hc > 2:
                    try:
                        self._tkimg = self._render_pil(Wc, Hc, st, now)  # v4.69: orange dot-orb is the base face
                        self.cv.itemconfig(self.img_id, image=self._tkimg)
                        self.cv.coords(self.img_id, 0, 0)
                    except Exception as e:
                        self.use_pil = False
                        print("PIL render failed, fallback:", e)
                else:
                    self._render_canvas(Wc, Hc, st, now)

                self.cv.coords(self.status_id, Wc / 2.0, Hc - 40)
                self.cv.tag_raise(self.status_id)
                if self._hold_until > time.time():
                    self.cv.itemconfig(self.status_id, text=self._hold)
                else:
                    self.cv.itemconfig(self.status_id, text=self.status_text())
        except Exception as _e:
            print("[diag] animate frame error (continuing):", repr(_e), flush=True)
        finally:
            if not self.stop:
                try:
                    self.root.after(delay, self.animate)
                except Exception:
                    pass

    # ---- fallback canvas renderer ----
    def _render_canvas(self, Wc, Hc, st, now):
        R = min(Wc, Hc) * 0.30
        focal = R * 2.6
        cx, cy = Wc / 2.0, Hc / 2.0 - 14
        spin = 0.0015 if st == "thinking" else (0.006 if st == "listening" else 0.0035)
        self.ang += spin
        pulse = 1.0
        if st == "listening":
            pulse = 1 + 0.06 * np.sin(now / 130.0)
        elif st == "idle":
            pulse = 1 + 0.02 * np.sin(now / 700.0)
        tzoom = 2.3 if st == "thinking" else 1.0
        self.zoom += (tzoom - self.zoom) * 0.10
        zc = min(self.zoom, 1.5)
        sa, ca = np.sin(self.ang), np.cos(self.ang)
        ox = oy = 0.0
        if st == "thinking":
            spx, spy, spz = self.pts[self.sel]
            sx0 = spx * ca + spz * sa
            sz0 = -spx * sa + spz * ca
            sc0 = focal / (focal + sz0 * R)
            ox = sx0 * R * sc0
            oy = spy * R * sc0
        lo, hi = RAMPS.get(st, RAMPS["idle"])
        selX, selY, selR = cx, cy, 2.0
        for i in range(self.N):
            px0, py0, pz0 = self.pts[i]
            x = px0 * ca + pz0 * sa
            z = -px0 * sa + pz0 * ca
            y = py0
            sc = focal / (focal + z * R) * pulse
            X = cx + (x * R * sc - ox) * self.zoom
            Y = cy + (y * R * sc - oy) * self.zoom
            depth = (z + 1) / 2.0
            rad = (1.3 + 2.2 * depth) * zc
            r = lo[0] + (hi[0] - lo[0]) * depth
            g = lo[1] + (hi[1] - lo[1]) * depth
            b = lo[2] + (hi[2] - lo[2]) * depth
            if st == "thinking" and i == self.sel:
                r, g, b = 235, 248, 255
                rad *= 2.4
                selX, selY, selR = X, Y, rad
            elif st == "thinking":
                r, g, b = r * 0.4, g * 0.4, b * 0.4
            self.cv.coords(self.items[i], X - rad, Y - rad, X + rad, Y + rad)
            self.cv.itemconfig(self.items[i], fill=_hexcol(r, g, b), outline="")
        if st == "thinking":
            gg = 0.5 + 0.4 * np.sin(now / 110.0)
            rr = selR + 9 + 3 * np.sin(now / 110.0)
            self.cv.coords(self.ring_id, selX - rr, selY - rr, selX + rr, selY + rr)
            self.cv.itemconfig(self.ring_id,
                               outline=_hexcol(230 * gg + 25, 245 * gg + 10, 255 * gg))
        else:
            self.cv.itemconfig(self.ring_id, outline="")
        if self.ripple_on:
            self.ripple += 0.02
            rr = self.ripple * R * 2.0
            if self.ripple >= 1.0:
                self.ripple_on = False
                self.cv.itemconfig(self.ripple_id, outline="")
            else:
                self.cv.coords(self.ripple_id, cx - rr, cy - rr, cx + rr, cy + rr)
                self.cv.itemconfig(self.ripple_id, outline="#46e0d6")
        else:
            self.cv.itemconfig(self.ripple_id, outline="")

def main():
    root = tk.Tk()
    App(root)
    # --- WorldView server autostart (worldview_autostart) --------------
    # Keep the :7777 server alive for the whole session (phone access via
    # LAN / Tailscale) instead of only while a WorldView window is open.
    try:
        import threading as _thr
        from pathlib import Path as _P
        def _wv_autostart():
            try:
                _fd = _P(__file__).resolve().parent
                _ensure_worldview_server(_fd, port=7777)
            except Exception as _e:
                print("[diag] worldview autostart failed:", repr(_e))
        _thr.Thread(target=_wv_autostart, daemon=True).start()
    except Exception as _e:
        print("[diag] worldview autostart not scheduled:", repr(_e))
    # ------------------------------------------------------------------
    root.mainloop()

if __name__ == "__main__":
    main()