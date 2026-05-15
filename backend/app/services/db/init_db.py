from app.services.db.session import Base, get_engine


def init_db() -> None:
    engine = get_engine()
    dialect = engine.dialect.name
    if dialect == "sqlite":
        # SQLite does not support schema-qualified tables (e.g. `app.screening_answers`).
        # Filter them out so create_all does not fail with "unknown database app".
        tables_for_sqlite = [t for t in Base.metadata.sorted_tables if not t.schema]
        Base.metadata.create_all(bind=engine, tables=tables_for_sqlite)
    else:
        Base.metadata.create_all(bind=engine)

