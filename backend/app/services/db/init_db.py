from app.services.db.session import Base, get_engine

def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    
