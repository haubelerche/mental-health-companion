from app.services import voice_consent


class _Row:
    def __init__(self, user_id: str, profile: dict | None = None):
        self.user_id = user_id
        self.profile = profile or {}


class _FakeDb:
    def __init__(self):
        self.row = None
        self.committed = False

    def scalar(self, *_args, **_kwargs):
        return self.row

    def add(self, row):
        self.row = row

    def flush(self):
        return

    def commit(self):
        self.committed = True


def test_get_voice_consent_default_false():
    db = _FakeDb()
    assert voice_consent.get_voice_consent(db, "usr_x") is False


def test_set_voice_consent_persists_true():
    db = _FakeDb()
    out = voice_consent.set_voice_consent(db, "usr_x", True)
    assert out is True
    assert db.committed is True
    assert db.row.profile.get("voice_consent") is True
