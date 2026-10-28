# Ticker Desk: news ticker generation & editorial review

Turns press releases into broadcast tickers (max 10 words), lets an editor review, edit, reorder and
approve them, and exports the approved set as JSON.

**Fully offline: no API key, no login, no internet needed after install.**
Stack: Flask + rule-based Python (no ML libraries) + plain HTML/CSS/JS.

## Run
```bash
pip install -r requirements.txt
python app.py            # open http://localhost:5000
python -m unittest discover -s tests    # 28 tests
```
Click **Use samples** to load `samples/announcements.txt` (includes prompt-injection, denial,
"reportedly", no-news and vague-preamble announcements).

## Using it
- Paste announcements separated by a `---` line, or load `.txt` / `.json` files (array of strings or `{text}`).
  Limits: 50 per batch, 8000 characters each; rejected entries are reported with the reason.
- Each card shows the source (facts highlighted, green = kept in the ticker) beside the editable ticker,
  with live word count and fact-check flags.
- Reorder (drag the number or ▲▼), undo / revert, **Regenerate** (next-best wording), or click an alternative.
- Tick **Approved**, then **Export approved**. The bottom bar scrolls the approved set as a continuous news line.

## How it works
**Generation (`ticker_service.py`)**: extractive and conservative, so it cannot invent facts:
1. Split into sentences, drop datelines, and **drop instruction-like sentences** ("ignore previous instructions…").
   Announcement text is only ever treated as data.
2. Score sentences (figures, named entities, news verbs, position; penalise vague preambles, invitations, boilerplate)
   and pick the most newsworthy. If nothing qualifies, no ticker is produced and the item is flagged `no_news`.
3. Compress using only words already in the sentence: remove articles/fillers/appositions, "announced it will X" → "to X",
   passive/perfect auxiliaries, "percent" → "%", "$45 million" → "$45M", past → present tense.
   Hedges (reportedly, plans, expected) and negations (denies, no, not) are kept.
4. Fit to 10 words by cutting at clause boundaries, then trailing prepositional phrases; hard truncation is flagged.

**Verification (`check()`)** runs on every generated *and* hand-edited ticker:

| Detected | Level | Effect |
|---|---|---|
| Figure / unit / name not in source | error | cannot approve or export |
| Denial, negation or cancellation turned into fact | error | cannot approve or export |
| Ticker repeats injected instructions | error | cannot approve or export |
| Plan / expectation stated as completed | warning | approval needs confirmation |
| Qualifier dropped ("at least", "about"…) | warning | approval needs confirmation |
| Conflicting / disputed claims in source, truncation, injection present | warning | review |

Approval is disabled while a check is in flight, and **export re-validates every approved ticker on the server**.
The length limit is enforced in code (whitespace-separated words; `$45M` is one word).

## Limitations
Rules cannot understand meaning. They catch the common drift patterns above, not every semantic error, so a human
approves every ticker. Very long subject names can force a flagged hard truncation, and the generator prefers a
plainer, safe ticker over a punchy one.

## Export format
```json
{"schema_version":"1.0","exported_at":"...","max_words":10,"count":1,
 "tickers":[{"position":1,"id":"a1","ticker":"...","word_count":8,"edited":false,
             "generated_ticker":"...","source_text":"...","flags":[]}]}
```

## Layout
`app.py` routes and input validation · `ticker_service.py` generator + checks · `static/` UI · `tests/` · `samples/`
