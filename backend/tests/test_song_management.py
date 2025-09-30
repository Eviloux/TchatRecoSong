import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import pytest

from app.crud import ban_rule as ban_crud
from app.crud import song as song_crud
from app.database.connection import Base
from app.models.song import Song

from app.schemas.ban_rule import BanRuleCreate, BanRuleUpdate

from app.schemas.song import SongCreate


@pytest.fixture()
def session(tmp_path) -> Session:
    db_path = tmp_path / "test.sqlite"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_add_ban_rule_removes_matching_songs(session: Session) -> None:
    song_crud.add_or_increment_song(
        session,
        SongCreate(
            title="Zitti e Buoni",
            artist="Måneskin",
            link="https://youtube.com/watch?v=maneskin",
        ),
    )
    song_crud.add_or_increment_song(
        session,
        SongCreate(
            title="Autre titre",
            artist="Autre artiste",
            link="https://youtube.com/watch?v=autre",
        ),
    )

    ban_crud.add_ban_rule(
        session,
        BanRuleCreate(title="zitti e buoni", artist="MANESKIN", link=None),
    )

    remaining = {song.link for song in session.query(Song).all()}
    assert "https://youtube.com/watch?v=maneskin" not in remaining
    assert "https://youtube.com/watch?v=autre" in remaining


def test_add_ban_rule_with_link_removes_song(session: Session) -> None:
    created = song_crud.add_or_increment_song(
        session,
        SongCreate(
            title="Song",
            artist="Artist",
            link="https://open.spotify.com/track/123",
        ),
    )

    assert session.query(Song).count() == 1

    ban_crud.add_ban_rule(
        session,
        BanRuleCreate(title=None, artist=None, link=created.link),
    )

    assert session.query(Song).count() == 0



def test_update_ban_rule_applies_new_filters(session: Session) -> None:
    first = song_crud.add_or_increment_song(
        session,
        SongCreate(
            title="Old title",
            artist="Same Artist",
            link="https://example.com/old",
        ),
    )
    song_crud.add_or_increment_song(
        session,
        SongCreate(
            title="New title",
            artist="Same Artist",
            link="https://example.com/new",
        ),
    )

    rule = ban_crud.add_ban_rule(
        session,
        BanRuleCreate(title="Old title", artist="Same Artist"),
    )

    remaining_links = {song.link for song in session.query(Song).all()}
    assert first.link not in remaining_links
    assert "https://example.com/new" in remaining_links

    updated = ban_crud.update_ban_rule(
        session,
        rule.id,
        BanRuleUpdate(title="New title", artist="Same Artist"),
    )

    assert updated is not None
    assert updated.title == "New title"
    assert {song.link for song in session.query(Song).all()} == set()


def test_update_ban_rule_returns_none_for_unknown_id(session: Session) -> None:
    assert ban_crud.update_ban_rule(session, 999, BanRuleUpdate(link="https://x")) is None


def test_delete_song(session: Session) -> None:
    created = song_crud.add_or_increment_song(
        session,
        SongCreate(
            title="Delete me",
            artist="Tester",
            link="https://example.com/delete",
        ),
    )

    assert song_crud.delete_song(session, created.id) is True
    assert session.query(Song).count() == 0
    assert song_crud.delete_song(session, created.id) is False



def test_delete_ban_rule(session: Session) -> None:
    rule = ban_crud.add_ban_rule(
        session,
        BanRuleCreate(title="To delete", artist=None, link=None),
    )

    assert ban_crud.delete_ban_rule(session, rule.id) is True
    assert ban_crud.delete_ban_rule(session, rule.id) is False



def test_increment_vote(session: Session) -> None:
    created = song_crud.add_or_increment_song(
        session,
        SongCreate(
            title="Vote me",
            artist="Tester",
            link="https://example.com/vote",
        ),
    )

    initial_votes = created.votes
    updated = song_crud.increment_vote(session, created.id)
    assert updated is not None
    assert updated.votes == initial_votes + 1


def test_duplicate_detection_ignores_diacritics(session: Session) -> None:
    first = song_crud.add_or_increment_song(
        session,
        SongCreate(
            title="Zitti e Buòni",
            artist="Måneskin",
            link="https://example.com/maneskin-1",
        ),
    )

    assert first.votes == 1

    second = song_crud.add_or_increment_song(
        session,
        SongCreate(
            title="Zitti e Buoni",
            artist="Maneskin",
            link="https://example.com/maneskin-2",
        ),
    )

    assert second.id == first.id
    assert second.votes == 2


def test_ban_rule_blocks_future_matches(session: Session) -> None:
    ban_crud.add_ban_rule(
        session,
        BanRuleCreate(title="Valentine", artist="Maneskin"),
    )

    result = song_crud.add_or_increment_song(
        session,
        SongCreate(
            title="VALENTINE",
            artist="MÅNESKIN",
            link="https://example.com/valentine",
        ),
    )

    assert result is None
    assert session.query(Song).count() == 0
