import unittest
from unittest import mock

from src import localizations as L


class FakeReq:
    def __init__(self, fn): self.fn = fn
    def execute(self): return self.fn()


class FakeYT:
    def __init__(self, fail=False):
        self.fail, self.updates = fail, []
    def videos(self): return self
    def update(self, part, body):
        def run():
            if self.fail:
                raise RuntimeError("boom")
            self.updates.append((part, body))
        return FakeReq(run)


SNIP = {"title": "Octane Rent vs DubiCars", "description": "Golden Horse tips",
        "tags": ["a"], "categoryId": "2"}


class Localizations(unittest.TestCase):
    def test_original_text_in_all_languages(self):
        locs = L.build_localizations("Octane Rent", "desc")
        self.assertEqual(set(locs), set(L.DEFAULT_LANGS))
        self.assertTrue(all(v == {"title": "Octane Rent", "description": "desc"} for v in locs.values()))

    def test_update_body(self):
        yt = FakeYT()
        self.assertTrue(L.apply_localizations(yt, "vid1", SNIP))
        part, body = yt.updates[0]
        self.assertEqual(part, "snippet,localizations")
        self.assertEqual(body["snippet"]["defaultLanguage"], "en")
        self.assertEqual(body["localizations"]["ru"]["title"], SNIP["title"])
        self.assertEqual(body["id"], "vid1")

    def test_error_is_swallowed(self):
        self.assertFalse(L.apply_localizations(FakeYT(fail=True), "vid1", SNIP))

    def test_disabled_by_env(self):
        yt = FakeYT()
        with mock.patch.dict("os.environ", {"YOUTUBE_LOCALIZATIONS": "false"}):
            self.assertFalse(L.apply_localizations(yt, "vid1", SNIP))
        self.assertEqual(yt.updates, [])

    def test_lang_override_skips_en(self):
        with mock.patch.dict("os.environ", {"YOUTUBE_LOCALIZATION_LANGS": "en, ru"}):
            self.assertEqual(L.languages(), ["ru"])


if __name__ == "__main__":
    unittest.main()
