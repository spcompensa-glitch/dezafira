import os
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, JSON, ForeignKey, Integer, text, Text
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
    print(f"[Database]  Erro ao conectar no banco original: {str(db_err)}")
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
    cookies = Column(String(10000), nullable=True)
    connection_status = Column(String(30), default="idle")
    verification_code = Column(String(20), nullable=True)
    connection_error = Column(String(500), nullable=True)

class AiCreatedChannel(Base):
    __tablename__ = "ai_created_channels"

    id = Column(String(50), primary_key=True, index=True)
    channel_id = Column(String(50), nullable=False) # FK do Canal da conta Google
    name = Column(String(100), nullable=False)
    nicho = Column(String(100), default="Geral")
    lang = Column(String(10), default="PT")
    creation_reason = Column(String(2000), nullable=True)
    subscribers = Column(Integer, default=0)
    videos_posted = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String(50), primary_key=True, index=True)
    status = Column(String(30), default="starting")
    prompt = Column(String(500), nullable=False)
    error = Column(String(1000), nullable=True)
    video_url = Column(String(500), nullable=True)
    channel_id = Column(String(50), nullable=True)
    approval_status = Column(String(30), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

class AutomationTask(Base):
    __tablename__ = 'automation_tasks'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    channel_id = Column(String(50), ForeignKey('channels.id'), nullable=True)
    title_suggestion = Column(String(255), nullable=True)
    status = Column(String(50), default='triage') # triage, writing, SEO, production, ready, done, failed
    script_content = Column(Text, nullable=True)
    metadata_tags = Column(Text, nullable=True)
    video_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChannelKnowledge(Base):
    """Shared Memory / Shared Brain — agentes armazenam aprendizados aqui."""
    __tablename__ = 'channel_knowledge'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    channel_id = Column(String(50), ForeignKey('channels.id'), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # style_guide, seo_blacklist, pexels_fallback, audience_insight, growth_hack
    meta_key = Column(String(100), nullable=False, index=True)  # Ex: 'tom_de_voz', 'failed_keyword_X'
    meta_value = Column(Text, nullable=False)  # Ex: 'Sombrio e misterioso', 'Evitar buscar'
    source = Column(String(50), nullable=True)  # Quem escreveu: 'hermes', 'deepseek', 'user_feedback'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Criar tabelas se não existirem com tratamento de erro
try:
    Base.metadata.create_all(bind=engine)
    
    # Migrations manuais
    with engine.connect() as conn:
        # approval_status na tabela predictions
        try:
            conn.execute(text("ALTER TABLE predictions ADD COLUMN approval_status VARCHAR(30) DEFAULT 'pending';"))
            conn.commit()
            print("[Database] Coluna approval_status adicionada na tabela predictions.")
        except Exception:
            pass
        
        # channel_knowledge — se a migration falhar, a tabela já existe via create_all
        try:
            conn.execute(text("ALTER TABLE automation_tasks ADD COLUMN video_url VARCHAR(500);"))
            conn.commit()
        except Exception:
            pass
            
except Exception as table_err:
    print(f"[Database]  Falha ao criar tabelas no banco original: {str(table_err)}")
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
        # Se o banco estiver vazio, cria as contas Google e canais criados por IA de teste iniciais
        # Banco limpo
        pass
            
        return [
            {
                "id": c.id,
                "name": c.name,
                "nicho": c.nicho,
                "lang": c.lang,
                "status": c.status,
                "monetization_step": c.monetization_step,
                "has_token": c.cookies is not None,
                "connection_status": c.connection_status,
                "connection_error": c.connection_error
            } for c in channels
        ]
    finally:
        db.close()

def save_db_channel_cookies(channel_id: str, cookies_json: str) -> bool:
    db = SessionLocal()
    try:
        chan = db.query(Channel).filter(Channel.id == channel_id).first()
        if chan:
            chan.cookies = cookies_json
            chan.monetization_step = "publishing"  # Marca o canal como ativo/vinculado
            chan.connection_status = "connected"
            chan.verification_code = None
            chan.connection_error = None
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
        # Remover subcanais da IA em cascata
        db.query(AiCreatedChannel).filter(AiCreatedChannel.channel_id == channel_id).delete(synchronize_session=False)
        # Remover predições
        db.query(Prediction).filter(Prediction.channel_id == channel_id).delete(synchronize_session=False)
        
        chan = db.query(Channel).filter(Channel.id == channel_id).first()
        if chan:
            db.delete(chan)
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"[Database] Erro ao deletar em cascata: {e}")
        db.rollback()
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

def get_db_ai_created_channels() -> list:
    db = SessionLocal()
    try:
        channels = db.query(AiCreatedChannel).order_by(AiCreatedChannel.created_at.desc()).all()
        return [
            {
                "id": c.id,
                "channel_id": c.channel_id,
                "name": c.name,
                "nicho": c.nicho,
                "lang": c.lang,
                "creation_reason": c.creation_reason,
                "subscribers": c.subscribers,
                "videos_posted": c.videos_posted,
                "created_at": c.created_at.isoformat() if c.created_at else None
            } for c in channels
        ]
    finally:
        db.close()

def create_db_ai_created_channel(channel_id: str, name: str, nicho: str, lang: str, creation_reason: str):
    db = SessionLocal()
    try:
        import uuid
        new_sub = AiCreatedChannel(
            id=f"sub_{uuid.uuid4().hex[:6]}",
            channel_id=channel_id,
            name=name,
            nicho=nicho,
            lang=lang,
            creation_reason=creation_reason,
            subscribers=0,
            videos_posted=0
        )
        db.add(new_sub)
        db.commit()
        return {
            "id": new_sub.id,
            "name": new_sub.name,
            "nicho": new_sub.nicho,
            "lang": new_sub.lang
        }
    finally:
        db.close()

def delete_db_ai_created_channel(sub_id: str) -> bool:
    db = SessionLocal()
    try:
        sub = db.query(AiCreatedChannel).filter(AiCreatedChannel.id == sub_id).first()
        if sub:
            db.delete(sub)
            db.commit()
            return True
        return False
    finally:
        db.close()

def create_automation_task(title_suggestion: str, channel_id: str = None):
    db = SessionLocal()
    try:
        new_task = AutomationTask(
            title_suggestion=title_suggestion,
            channel_id=channel_id,
            status='triage'
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        return new_task.id
    finally:
        db.close()

def update_automation_task(task_id: int, **kwargs):
    db = SessionLocal()
    try:
        task = db.query(AutomationTask).filter(AutomationTask.id == task_id).first()
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            db.commit()
    finally:
        db.close()

def get_automation_task(task_id: int):
    db = SessionLocal()
    try:
        task = db.query(AutomationTask).filter(AutomationTask.id == task_id).first()
        if task:
            return {
                'id': task.id,
                'channel_id': task.channel_id,
                'title_suggestion': task.title_suggestion,
                'status': task.status,
                'script_content': task.script_content,
                'metadata_tags': task.metadata_tags,
                'video_url': task.video_url,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'updated_at': task.updated_at.isoformat() if task.updated_at else None
            }
        return None
    finally:
        db.close()
