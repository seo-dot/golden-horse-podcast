"""Проверка загрузки без сети: подмена googleapiclient. Главное — запасной путь:
если YouTube отклонил publishAt, видео всё равно публикуется сразу."""
import sys
import types
import unittest
from unittest import mock


class FakeHttpError(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.resp = types.SimpleNamespace(status=status)
        self.content = b""


class FakeRequest:
    def __init__(self, owner, body):
        self.owner, self.body = owner, body

    def next_chunk(self):
        if self.owner.reject_publish_at and "publishAt" in self.body["status"]:
            raise FakeHttpError(self.owner.reject_status)
        self.owner.sent.append(self.body["status"])
        return None, {"id": "vid123"}


class FakeYT:
    def __init__(self, reject_publish_at=False, reject_status=400):
        self.reject_publish_at, self.reject_status = reject_publish_at, reject_status
        self.sent = []

    def videos(self):
        return self

    def insert(self, part, body, media_body):
        return FakeRequest(self, body)


def _install_fakes():
    pkg = types.ModuleType("googleapiclient")
    err = types.ModuleType("googleapiclient.errors")
    err.HttpError = FakeHttpError
    http = types.ModuleType("googleapiclient.http")
    http.MediaFileUpload = lambda *a, **k: object()
    sys.modules.update({"googleapiclient": pkg, "googleapiclient.errors": err,
                        "googleapiclient.http": http})


_install_fakes()
from src import config, youtube_upload  # noqa: E402


class UploadFallback(unittest.TestCase):
    def _run(self, yt, privacy="public"):
        with mock.patch.object(youtube_upload, "_service", return_value=yt), \
             mock.patch.object(config, "YOUTUBE_PRIVACY", privacy):
            return youtube_upload.upload("x.mp4", "T", "D", [], None)

    def test_scheduled_when_public(self):
        yt = FakeYT()
        res = self._run(yt)
        self.assertEqual(yt.sent[0]["privacyStatus"], "private")
        self.assertTrue(yt.sent[0]["publishAt"].endswith("Z"))
        self.assertEqual(res["publish_at"], yt.sent[0]["publishAt"])

    def test_rejected_publish_at_falls_back_to_immediate_public(self):
        yt = FakeYT(reject_publish_at=True)
        res = self._run(yt)
        self.assertEqual(yt.sent, [{"privacyStatus": "public", "selfDeclaredMadeForKids": False}])
        self.assertEqual(res["publish_at"], "")
        self.assertEqual(res["video_id"], "vid123")

    def test_other_errors_are_not_swallowed(self):
        with self.assertRaises(FakeHttpError):
            self._run(FakeYT(reject_publish_at=True, reject_status=500))

    def test_private_and_unlisted_untouched(self):
        for privacy in ("private", "unlisted"):
            yt = FakeYT()
            res = self._run(yt, privacy)
            self.assertEqual(yt.sent, [{"privacyStatus": privacy, "selfDeclaredMadeForKids": False}])
            self.assertEqual(res["publish_at"], "")

    def test_kill_switch(self):
        yt = FakeYT()
        with mock.patch.dict("os.environ", {"RANDOM_PUBLISH": "false"}):
            self._run(yt)
        self.assertNotIn("publishAt", yt.sent[0])
        self.assertEqual(yt.sent[0]["privacyStatus"], "public")


if __name__ == "__main__":
    unittest.main()
