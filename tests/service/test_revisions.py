import uuid

from news.service.revisions import creator_of, next_revision_number


def test_first_revision_is_number_one() -> None:
    assert next_revision_number(None) == 1


def test_next_revision_follows_the_latest() -> None:
    assert next_revision_number(7) == 8


def test_reader_creator_is_the_readers_id() -> None:
    reader_id = uuid.uuid7()

    assert creator_of(reader_id) == str(reader_id)
