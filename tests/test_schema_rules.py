"""AC-1, AC-2: the scope rules, on synthetic table descriptions."""

from tests.schema_rules import TableDescription, scope_violations


def a_table(
    name: str,
    scope: str | None,
    columns: set[str] | None = None,
    foreign_key_targets: set[str] | None = None,
) -> TableDescription:
    return TableDescription(
        name=name,
        columns=frozenset({"id"} | (columns or set())),
        foreign_key_targets=frozenset(foreign_key_targets or set()),
        scope=scope,
    )


CLEAN_SCHEMA = [
    a_table("alembic_version", "app", {"version_num"}),
    a_table("reader", "reader", {"name"}),
    a_table("plugin", "reader", {"reader_id"}, {"reader"}),
    a_table("channel", "channel", {"reader_id"}, {"reader"}),
    a_table("channel_revision", "channel", {"reader_id", "channel_id"}, {"reader", "channel"}),
]


def test_a_clean_schema_has_no_violations() -> None:
    assert scope_violations(CLEAN_SCHEMA) == []


def test_no_tables_have_no_violations() -> None:
    assert scope_violations([]) == []


def test_a_reader_table_without_a_reader_id_is_a_violation() -> None:
    assert scope_violations([a_table("style", "reader", {"text"})]) == [
        "style: declared reader but has no reader_id"
    ]


def test_the_reader_table_passes_on_its_own_id() -> None:
    assert scope_violations([a_table("reader", "reader")]) == []


def test_the_reader_table_without_an_id_is_a_violation() -> None:
    reader = TableDescription("reader", frozenset({"name"}), frozenset(), "reader")

    assert scope_violations([reader]) == ["reader: declared reader but has no reader_id"]


def test_a_channel_table_without_a_channel_id_is_a_violation() -> None:
    assert scope_violations([a_table("article", "channel", {"reader_id"})]) == [
        "article: declared channel but has no channel_id"
    ]


def test_the_channel_table_passes_on_its_own_id() -> None:
    assert scope_violations([a_table("channel", "channel", {"reader_id"})]) == []


def test_the_channel_table_without_an_id_is_a_violation() -> None:
    channel = TableDescription("channel", frozenset({"reader_id"}), frozenset(), "channel")

    assert scope_violations([channel]) == ["channel: declared channel but has no channel_id"]


def test_a_channel_table_without_a_reader_id_is_a_violation() -> None:
    """Channel rows belong to the Channel's Reader too (ADR 0007)."""
    assert scope_violations([a_table("article", "channel", {"channel_id"})]) == [
        "article: declared channel but has no reader_id"
    ]


def test_an_undeclared_table_is_a_violation() -> None:
    assert scope_violations([a_table("stray", None)]) == ["stray: no declared scope"]


def test_an_unknown_scope_is_a_violation() -> None:
    assert scope_violations([a_table("stray", "global")]) == ["stray: unknown scope 'global'"]


def test_a_foreign_key_to_a_channel_table_from_a_reader_table_is_a_violation() -> None:
    tables = [
        a_table("channel", "channel", {"reader_id"}),
        a_table("note", "reader", {"reader_id", "channel_id"}, {"channel"}),
    ]

    assert scope_violations(tables) == [
        "note: references channel table channel but is declared reader"
    ]


def test_a_foreign_key_to_a_channel_table_from_an_app_table_is_a_violation() -> None:
    tables = [
        a_table("channel_revision", "channel", {"reader_id", "channel_id"}),
        a_table("audit", "app", set(), {"channel_revision"}),
    ]

    assert scope_violations(tables) == [
        "audit: references channel table channel_revision but is declared app"
    ]


def test_a_foreign_key_to_a_reader_table_from_a_channel_table_is_allowed() -> None:
    tables = [
        a_table("plugin_revision", "reader", {"reader_id"}),
        a_table("plugin_binding", "channel", {"reader_id", "channel_id"}, {"plugin_revision"}),
    ]

    assert scope_violations(tables) == []


def test_every_violation_in_a_schema_is_reported() -> None:
    tables = [
        a_table("stray", None),
        a_table("style", "reader"),
        a_table("article", "channel", {"reader_id"}),
    ]

    assert scope_violations(tables) == [
        "stray: no declared scope",
        "style: declared reader but has no reader_id",
        "article: declared channel but has no channel_id",
    ]
