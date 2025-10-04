from app.services import song_metadata


class DummyResponse:
    def __init__(self, *, json_data=None, text: str = "") -> None:
        self._json_data = json_data
        self.text = text

    def raise_for_status(self) -> None:  # pragma: no cover - nothing to raise
        return None

    def json(self) -> dict:
        if self._json_data is None:
            raise RuntimeError("No JSON payload defined")
        return self._json_data


class DummyClient:
    def __init__(self, responses):
        self._responses = responses

    def get(self, url, params=None, **kwargs):
        if params is not None:
            key = (url, tuple(sorted(params.items())))
        else:
            key = url

        if key not in self._responses:
            raise AssertionError(f"Unexpected request: {key}")

        payload = self._responses[key]
        return DummyResponse(**payload)


def test_enrich_spotify_metadata_extracts_artist_and_title():
    oembed_payload = {
        "title": "Zitti e Buoni",
        "html": '<iframe src="https://open.spotify.com/embed/track/123?utm_source=oembed"></iframe>',
        "thumbnail_url": "https://i.scdn.co/image/abc",
    }

    spotify_html = (
        '{"type":"track","name":"Zitti e Buoni","artists":[{"name":"M\\u00e5neskin"}]}'
    )

    responses = {
        "https://open.spotify.com/embed/track/123?utm_source=oembed": {
            "text": spotify_html
        },
    }

    client = DummyClient(responses)
    title, artist = song_metadata._enrich_spotify_metadata(  # pylint: disable=protected-access
        client, oembed_payload, "https://open.spotify.com/track/123"
    )

    assert title == "Zitti e Buoni"
    assert artist == "Måneskin"


def test_build_song_prefers_overrides():
    result = {"title": "Fallback", "author_name": "Unknown", "thumbnail_url": None}
    created = song_metadata._build_song(  # pylint: disable=protected-access
        result,
        "https://example.com",
        title="Actual Title",
        artist="Actual Artist",
    )

    assert created.title == "Actual Title"
    assert created.artist == "Actual Artist"
