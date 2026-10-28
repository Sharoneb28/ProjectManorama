import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ticker_service as ts


def codes(flags, level=None):
    return {f["code"] for f in flags if level is None or f["level"] == level}


ACCIDENT = (
    "ചേരാനല്ലൂരിൽ വാഹനമിടിച്ച് കടയുടമ മരിച്ച കേസിൽ പ്രതിയായ 17കാരന്റെ "
    "അച്ഛനായ ജഡ്ജിക്കെതിരെ നടപടി ശുപാർശ. "
    "ജഡ്ജിയെ സസ്പെൻഡ് ചെയ്യണമെന്ന് ആവശ്യപ്പെട്ട് പോർട്ട്‌ഫോളിയോ ജഡ്ജി "
    "ജസ്റ്റിസ് പി.വി. കുഞ്ഞികൃഷ്ണൻ ഹൈക്കോടതി ചീഫ് ജസ്റ്റിസിന് റിപ്പോർട്ട് നൽകി. "
    "കേസിൽ കൂടുതൽ അന്വേഷണം നടക്കുന്നു."
)
WEATHER = (
    "ബംഗാൾ ഉൾക്കടലിൽ രൂപപ്പെടുന്ന കാലാവസ്ഥാ സംവിധാനം കാരണം അടുത്ത "
    "ദിവസങ്ങളിൽ വടക്കേ ഇന്ത്യയിലും മഴയ്ക്ക് സാധ്യതയെന്ന് കാലാവസ്ഥാ വകുപ്പ്. "
    "ആദ്യം ആന്ധ്ര, ഒഡീഷ തീരങ്ങളിൽ ശക്തമായ മഴയ്ക്ക് സാധ്യത. "
    "മത്സ്യത്തൊഴിലാളികൾ കടലിൽ പോകരുതെന്ന് മുന്നറിയിപ്പ്."
)


class MalayalamGenerationTests(unittest.TestCase):
    def test_short_news(self):
        source = "കേരള സർക്കാർ പുതിയ വിദ്യാഭ്യാസ പദ്ധതി പ്രഖ്യാപിച്ചു."
        result = ts.generate(source)
        self.assertEqual(result["ticker"], source.rstrip("."))
        self.assertEqual(ts.word_count(result["ticker"]), 6)

    def test_denial_remains_denial(self):
        result = ts.generate("പോലീസ് മൂന്ന് പേരെ അറസ്റ്റ് ചെയ്തെന്ന റിപ്പോർട്ടുകൾ നിഷേധിച്ചു.")
        self.assertIn("നിഷേധിച്ചു", result["ticker"])

    def test_uncertainty_remains_uncertain(self):
        result = ts.generate("ആന്ധ്ര തീരത്ത് ശക്തമായ മഴയ്ക്ക് സാധ്യത.")
        self.assertIn("സാധ്യത", result["ticker"])

    def test_numbers_are_preserved(self):
        result = ts.generate("തിരുവനന്തപുരം ജില്ലയിൽ 38 പുതിയ ഡെങ്കിപ്പനി കേസുകൾ സ്ഥിരീകരിച്ചു.")
        self.assertIn("38", result["ticker"])

    def test_ten_word_limit(self):
        result = ts.generate(WEATHER)
        self.assertTrue(0 < ts.word_count(result["ticker"]) <= 10)

    def test_accident_source_based(self):
        result = ts.generate(ACCIDENT)
        self.assertTrue(0 < ts.word_count(result["ticker"]) <= 10)
        self.assertNotIn("ജസ്റ്റിസ് പി.വി", result["ticker"])
        self.assertNotIn("error", {f["level"] for f in result["flags"]})

    def test_initials_not_split(self):
        sentences = ts._sentences(ACCIDENT)
        self.assertTrue(any("പി.വി. കുഞ്ഞികൃഷ്ണൻ" in s for s in sentences))
        self.assertFalse(any(s.endswith("പി.വി") for s in sentences))

    def test_no_arbitrary_truncation(self):
        source = " ".join(["വിവരം"] * 12) + "."
        result = ts.generate(source)
        self.assertEqual(result["ticker"], "")
        self.assertIn("manual_review", codes(result["flags"]))

    def test_empty_source(self):
        self.assertEqual(ts.generate("")["ticker"], "")
        self.assertIn("empty", codes(ts.generate("")["flags"]))

    def test_alternatives_and_avoid(self):
        source = ("കേരള സർക്കാർ പദ്ധതി പ്രഖ്യാപിച്ചു. "
                  "മന്ത്രിസഭ പുതിയ പദ്ധതിക്ക് അംഗീകാരം നൽകി.")
        first = ts.generate(source)
        second = ts.generate(source, avoid=[first["ticker"]])
        self.assertTrue(second["ticker"])
        self.assertNotEqual(first["ticker"], second["ticker"])

    def test_unicode_normalization(self):
        self.assertEqual(ts._clean("  മലയാളം  "), "മലയാളം")

    def test_metadata_ignored(self):
        source = ("കേരള സർക്കാർ പുതിയ പദ്ധതി പ്രഖ്യാപിച്ചു.\n"
                  "ഡെസ്കിൽ പരിശോധിക്കേണ്ടത്: ഔദ്യോഗിക രേഖകൾ പരിശോധിക്കണം.")
        result = ts.generate(source)
        self.assertNotIn("ഡെസ്കിൽ", result["ticker"])


class MalayalamValidationTests(unittest.TestCase):
    def test_empty_ticker(self):
        self.assertIn("empty", codes(ts.check("", "കേരളത്തിൽ മഴ."), "error"))

    def test_missing_source(self):
        self.assertIn("missing_source", codes(ts.check("കേരളത്തിൽ മഴ", ""), "error"))

    def test_over_ten_words(self):
        ticker = " ".join(["മഴ"] * 11)
        self.assertIn("length", codes(ts.check(ticker, ticker), "error"))

    def test_non_malayalam(self):
        self.assertIn("language", codes(ts.check("Rain expected", "കേരളത്തിൽ മഴ."), "error"))

    def test_unsupported_number(self):
        flags = ts.check("ജില്ലയിൽ 99 കേസുകൾ", "ജില്ലയിൽ 38 കേസുകൾ സ്ഥിരീകരിച്ചു.")
        self.assertIn("number", codes(flags, "error"))

    def test_exact_source_excerpt(self):
        source = "കേരള സർക്കാർ പുതിയ വിദ്യാഭ്യാസ പദ്ധതി പ്രഖ്യാപിച്ചു."
        self.assertNotIn("paraphrase", codes(ts.check(source.rstrip("."), source)))

    def test_paraphrase_flag(self):
        flags = ts.check("കേരള സർക്കാർ പദ്ധതി പിൻവലിച്ചു", "കേരള സർക്കാർ പദ്ധതി പ്രഖ്യാപിച്ചു.")
        self.assertIn("paraphrase", codes(flags, "warn"))

    def test_denial_warning(self):
        source = "പോലീസ് മൂന്ന് പേരെ അറസ്റ്റ് ചെയ്തെന്ന റിപ്പോർട്ടുകൾ നിഷേധിച്ചു."
        flags = ts.check("പോലീസ് മൂന്ന് പേരെ അറസ്റ്റ് ചെയ്തെന്ന", source)
        self.assertIn("denial", codes(flags, "warn"))

    def test_uncertainty_warning(self):
        source = "ആന്ധ്ര തീരത്ത് ശക്തമായ മഴയ്ക്ക് സാധ്യത."
        flags = ts.check("ആന്ധ്ര തീരത്ത് ശക്തമായ മഴയ്ക്ക്", source)
        self.assertIn("uncertainty", codes(flags, "warn"))


if __name__ == "__main__":
    unittest.main()
