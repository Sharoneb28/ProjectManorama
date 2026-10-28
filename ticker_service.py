"""Offline Malayalam news ticker generator.

Conservative extractive approach: only contiguous source words are emitted.
Compatible with app.py: generate(text, avoid), check(ticker, source),
word_count(text), flag(level, code, message), MAX_WORDS.
"""
import re
import unicodedata

MAX_WORDS = 10

NEWS = (
    "ശുപാർശ", "നടപടി", "സസ്പെൻഡ്", "അറസ്റ്റ്", "അപകട", "മരണ", "മരിച്ച",
    "മുന്നറിയിപ്പ്", "മഴ", "ചുഴലിക്കാറ്റ", "ജാഗ്രത", "നിഷേധ",
    "പ്രഖ്യാപ", "അംഗീകര", "നിയമ", "അന്വേഷ", "കേസെടുത്ത",
    "രാജിവെ", "നിക്ഷേപ", "തീരുമാന", "റദ്ദ", "വിജയ", "ഉദ്ഘാട",
)
HIGH_VALUE = (
    "ശുപാർശ", "മുന്നറിയിപ്പ്", "സാധ്യത", "നിഷേധ", "അറസ്റ്റ്",
    "സസ്പെൻഡ്", "മരിച്ചു", "മരണം", "നടപടി", "പ്രഖ്യാപ",
)
NEG = ("നിഷേധ", "അല്ല", "ഇല്ല", "വ്യാജ", "തെറ്റ", "നിരസ")
UNCERTAIN = (
    "സാധ്യത", "സൂചന", "ആരോപ", "സംശയ", "പ്രതീക്ഷ", "ആയേക്ക",
    "ഉണ്ടായേക്ക", "എന്നാണ്", "റിപ്പോർട്ട്", "ശുപാർശ", "പ്രാഥമിക",
    "സ്ഥിരീകരിച്ചിട്ടില്ല", "പറയപ്പെട",
)
# A single word with a negation suffix can be vital.
CRITICAL_ENDINGS = ("രുത്", "ാത്ത", "ില്ല")
META = (
    "ഡെസ്കിൽ പരിശോധിക്കേണ്ടത്", "ഔദ്യോഗിക രേഖകളുമായി ഉറപ്പാക്കണം",
    "ഒത്തുനോക്കണം", "പരിശോധിക്കണം", "പരിശോധിക്കേണ്ട",
)
LEADING_LABEL = re.compile(r"^\s*(?:Raw Content\s*\d+\s*:|Raw content\s*\d+\s*:)\s*", re.I)
NUMBER = re.compile(r"(?<![\w])(?:[0-9\u0D66-\u0D6F]+(?:[.,][0-9\u0D66-\u0D6F]+)*)(?![\w])")
PUNCT = " \t\r\n.,;:!?।“”\"'‘’—–-"


def flag(level, code, message):
    return {"level": level, "code": code, "message": message}


def _clean(value):
    return unicodedata.normalize("NFC", str(value or "")).strip()


def word_count(value):
    return len(_clean(value).split())


def _tokens(value):
    return _clean(value).split()


def _normalize_token(token):
    return _clean(token).strip(PUNCT).casefold()


def _contains(text, roots):
    return any(root in text for root in roots)


def _sentences(text):
    """Separate paragraphs and Malayalam sentences; keep source order."""
    pieces = []
    for line in _clean(text).splitlines():
        line = LEADING_LABEL.sub("", line).strip()
        if not line:
            continue
        # Malayalam source often contains multiple sentences on one line.
        for part in re.split(r"(?<=[.!?।])\s+", line):
            part = part.strip()
            if part and not _contains(part, META):
                pieces.append(part)
    return pieces


def _source_span(ticker, source):
    """True only if all ticker words occur contiguously in the source.

    Punctuation differences are allowed, but words may not be rearranged,
    inflected, or inserted. This is deliberately stricter than paraphrasing.
    """
    wanted = [_normalize_token(x) for x in _tokens(ticker)]
    original = [_normalize_token(x) for x in _tokens(source)]
    if not wanted:
        return False
    return any(original[i:i + len(wanted)] == wanted
               for i in range(len(original) - len(wanted) + 1))


def _numbers(text):
    return NUMBER.findall(_clean(text))


def _qualifiers(text):
    """Report qualifiers that occur within a specific sentence."""
    return {
        name for name, roots in (
            ("denial", NEG), ("uncertainty", UNCERTAIN),
        ) if _contains(text, roots)
    }


def _risk_of_cut(sentence, ticker):
    """Avoid prefixes that lose the essential predicate or qualification."""
    if _qualifiers(sentence) - _qualifiers(ticker):
        return True
    # Do not end with grammatical connectors or incomplete report phrases.
    trailing = _normalize_token(_tokens(ticker)[-1]) if ticker else ""
    if trailing in {"എന്ന്", "എന്ന", "എന്നും", "ആണ്", "എന്നാണ്",
                    "എന്നാൽ", "കാരണം", "പ്രകാരം", "വേണ്ടി", "നിന്ന്",
                    "കുറിച്ച്", "തുടർന്ന്", "മൂലം", "ആയി"}:
        return True
    # If the predicate is after the cut, prefix alone is often misleading.
    predicates = (
        "നിഷേധിച്ചു", "ശുപാർശ", "പ്രഖ്യാപിച്ചു", "റിപ്പോർട്ട് നൽകി",
        "മുന്നറിയിപ്പ്", "സാധ്യത", "ആരോപിച്ചു", "മരിച്ചു",
        "കേസെടുത്തു", "ആവശ്യപ്പെട്ടു", "നൽകി", "പറഞ്ഞു",
    )
    for predicate in predicates:
        if predicate in sentence and predicate not in ticker:
            return True
    return False


def _score(sentence, index, shortened=False):
    score = 2.0 / (1 + index)
    if _contains(sentence, NEWS):
        score += 4
    if _contains(sentence, HIGH_VALUE):
        score += 3
    if _contains(sentence, UNCERTAIN):
        score += 1.5
    if _numbers(sentence):
        score += 0.6
    if shortened:
        score -= 3
    if word_count(sentence) <= 3:
        score -= 2
    # Titles are often useful, but prefer a substantive complete sentence.
    if index == 0 and word_count(sentence) <= 5:
        score -= 2
    return score


def _safe_chunks(sentence):
    """Return complete sentences and source-extracted short clauses.

    Never take an arbitrary first-ten-word prefix: that can reverse meaning.
    """
    cleaned = sentence.strip().strip(PUNCT)
    if not cleaned:
        return []
    chunks = []
    if word_count(cleaned) <= MAX_WORDS:
        chunks.append((cleaned, False))
    # Extract only clauses delimited in the original text.
    for chunk in re.split(r"[,;:–—]", cleaned):
        chunk = chunk.strip().strip(PUNCT)
        if (4 <= word_count(chunk) <= MAX_WORDS and chunk != cleaned
                and not re.match(r"^[0-9൦-൯]", chunk)):
            # A clause with a lost qualifier must not be auto-generated.
            if not _risk_of_cut(sentence, chunk):
                chunks.append((chunk, True))
    return chunks


def check(ticker, source):
    """Conservative validation. Flags cannot prove semantic correctness."""
    ticker, source = _clean(ticker), _clean(source)
    result = []
    if not ticker:
        return [flag("error", "empty", "Ticker is empty")]
    if not source:
        return [flag("error", "missing_source", "Source is missing")]
    if word_count(ticker) > MAX_WORDS:
        result.append(flag("error", "length", "Ticker exceeds 10 words"))
    if not re.search(r"[\u0D00-\u0D7F]", ticker):
        result.append(flag("error", "language", "Ticker must be in Malayalam"))
    if not _source_span(ticker, source):
        # Editors can paraphrase, but it must be checked before approval.
        result.append(flag("warn", "paraphrase",
                           "Ticker is not an exact source excerpt; review facts and wording"))
    for number in sorted(set(_numbers(ticker)) - set(_numbers(source))):
        result.append(flag("error", "number",
                           f"Number {number} does not occur in the source"))
    # Qualifier warnings only compare against the closest matching sentence,
    # not the whole article, to avoid unrelated paragraphs causing warnings.
    ticker_set = {_normalize_token(t) for t in _tokens(ticker)}
    best = None
    best_overlap = -1
    for sentence in _sentences(source):
        overlap = len(ticker_set & {_normalize_token(t) for t in _tokens(sentence)})
        if overlap > best_overlap:
            best, best_overlap = sentence, overlap
    if best:
        lost = _qualifiers(best) - _qualifiers(ticker)
        if "denial" in lost:
            result.append(flag("warn", "denial",
                               "Source sentence contains a denial; review carefully"))
        if "uncertainty" in lost:
            result.append(flag("warn", "uncertainty",
                               "Source sentence contains uncertainty or attribution"))
    return result


def _candidates(text):
    candidates, seen = [], set()
    for index, sentence in enumerate(_sentences(text)):
        for ticker, shortened in _safe_chunks(sentence):
            key = ticker.casefold()
            if key in seen:
                continue
            seen.add(key)
            flags = check(ticker, text)
            if shortened:
                flags.append(flag("warn", "extracted_clause",
                                  "Extracted a clause; check that context is complete"))
            if any(f["level"] == "error" for f in flags):
                continue
            candidates.append({
                "ticker": ticker,
                "flags": flags,
                "score": _score(sentence, index, shortened),
            })
    return sorted(candidates, key=lambda c: (
        any(f["code"] == "extracted_clause" for f in c["flags"]),
        -c["score"], len(c["flags"])))


def generate(text, avoid=()):
    """Return a ticker, alternatives, flags (Flask API-compatible).

    If no safely extractable <=10-word text exists, return no ticker instead
    of manufacturing a possibly misleading one. The editor can write one.
    """
    text = _clean(text)
    if not text:
        return {"ticker": "", "alternatives": [],
                "flags": [flag("error", "empty", "Announcement is empty")]}
    excluded = {_clean(x).casefold() for x in avoid}
    candidates = _candidates(text)
    remaining = [c for c in candidates if c["ticker"].casefold() not in excluded]
    if not remaining:
        return {
            "ticker": "",
            "alternatives": [],
            "flags": [flag("warn", "manual_review",
                           "No safe short excerpt found; write a ticker manually")],
            "exhausted": True,
        }
    best = remaining[0]
    return {
        "ticker": best["ticker"],
        "alternatives": [c["ticker"] for c in remaining[1:3]],
        "flags": best["flags"],
    }
