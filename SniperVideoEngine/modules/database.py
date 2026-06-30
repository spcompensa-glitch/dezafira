import os
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Determinar URL do banco de dados (Railway Postgres ou SQLite local)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback para banco SQLite local em desenvolvimento
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATABASE_URL = f"sqlite:///{os.path.join(project_dir, 'dezafira.db')}"

# 2. Configurar o Engine e Sessão com Fallback Resiliente
try:
    # Ajuste de compatibilidade para postgresql:// no SQLAlchemy 1.4+
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    # Testar conexão
    with engine.connect() as conn:
        pass
except Exception as db_err:
    print(f"[Database] ⚠️ Erro ao conectar no banco original: {str(db_err)}")
    print("[Database] Acionando fallback resiliente: banco SQLite em memória (sqlite:///:memory:)")
    DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. Modelos ORM
class Channel(Base):
    __tablename__ = "channels"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    nicho = Column(String(100), default="Geral")
    lang = Column(String(10), default="PT")
    status = Column(String(20), default="active")
    monetization_step = Column(String(30), default="setup")
    youtube_refresh_token = Column(String(500), nullable=True)

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String(50), primary_key=True, index=True)
    status = Column(String(30), default="starting")
    prompt = Column(String(500), nullable=False)
    error = Column(String(1000), nullable=True)
    video_url = Column(String(500), nullable=True)
    channel_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Criar tabelas se não existirem com tratamento de erro
try:
    Base.metadata.create_all(bind=engine)
except Exception as table_err:
    print(f"[Database] ⚠️ Falha ao criar tabelas no banco original: {str(table_err)}")
    print("[Database] Recaindo para banco em memória (sqlite:///:memory:) para tabelas")
    DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

# 4. Funções auxiliares de compatibilidade para o server.py
def get_db_channels():
    db = SessionLocal()
    try:
        channels = db.query(Channel).all()
        # Se o banco estiver vazio, cria os canais de teste iniciais
        if not channels:
            initial_channels = [
                Channel(id="ch_1", name="Dropshipping Prático", nicho="Dropshipping", lang="PT", status="active", monetization_step="publishing"),
                Channel(id="ch_2", name="Global Tech Trends", nicho="Geral", lang="EN", status="active", monetization_step="setup"),
                Channel(id="ch_3", name="Finanzas & Cripto", nicho="Cripto", lang="ES", status="active", monetization_step="viral")
            ]
            for c in initial_channels:
                db.add(c)
            db.commit()
            channels = db.query(Channel).all()
            
        return [
            {
                "id": c.id,
                "name": c.name,
                "nicho": c.nicho,
                "lang": c.lang,
                "status": c.status,
                "monetization_step": c.monetization_step,
                "has_token": c.youtube_refresh_token is not None
            } for c in channels
        ]
    finally:
        db.close()

def save_db_channel_token(channel_id: str, refresh_token: str) -> bool:
    db = SessionLocal()
    try:
        chan = db.query(Channel).filter(Channel.id == channel_id).first()
        if chan:
            chan.youtube_refresh_token = refresh_token
            chan.monetization_step = "publishing"  # Marca o canal como pronto/vinculado
            db.commit()
            return True
        return False
    finally:
        db.close()

def create_db_channel(name: str, nicho: str, lang: str):
    db = SessionLocal()
    try:
        new_chan = Channel(
            id=f"ch_{uuid.uuid4().hex[:6]}",
            name=name,
            nicho=nicho,
            lang=lang,
            status="active",
            monetization_step="setup"
        )
        db.add(new_chan)
        db.commit()
        return {
            "id": new_chan.id,
            "name": new_chan.name,
            "nicho": new_chan.nicho,
            "lang": new_chan.lang,
            "status": new_chan.status,
            "monetization_step": new_chan.monetization_step
        }
    finally:
        db.close()

def delete_db_channel(channel_id: str) -> bool:
    db = SessionLocal()
    try:
        chan = db.query(Channel).filter(Channel.id == channel_id).first()
        if chan:
            db.delete(chan)
            db.commit()
            return True
        return False
    finally:
        db.close()

def save_db_prediction(pred_id: str, prompt: str, channel_id: str = "default"):
    db = SessionLocal()
    try:
        pred = Prediction(
            id=pred_id,
            status="starting",
            prompt=prompt,
            channel_id=channel_id
        )
        db.add(pred)
        db.commit()
    finally:
        db.close()

def update_db_prediction(pred_id: str, status: str, video_url: str = None, error: str = None):
    db = SessionLocal()
    try:
        pred = db.query(Prediction).filter(Prediction.id == pred_id).first()
        if pred:
            pred.status = status
            if video_url:
                pred.video_url = video_url
            if error:
                pred.error = error
            db.commit()
    finally:
        db.close()

def get_db_prediction(pred_id: str):
    db = SessionLocal()
    try:
        pred = db.query(Prediction).filter(Prediction.id == pred_id).first()
        if pred:
            return {
                "id": pred.id,
                "status": pred.status,
                "prompt": pred.prompt,
                "error": pred.error,
                "url": pred.video_url
            }
        return None
    finally:
        db.close()
