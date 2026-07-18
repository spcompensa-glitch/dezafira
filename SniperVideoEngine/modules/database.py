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


class DeliverableApp(Base):
    __tablename__ = "deliverable_apps"

    id = Column(String(50), primary_key=True, index=True)
    channel_id = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, index=True)
    nicho = Column(String(100), nullable=False)
    app_type = Column(String(50), default="quiz_diagnostico")
    config_json = Column(JSON, nullable=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class AppPayment(Base):
    __tablename__ = "app_payments"

    id = Column(String(50), primary_key=True, index=True)
    app_id = Column(String(50), nullable=False)
    gateway = Column(String(50), nullable=False)
    transaction_id = Column(String(100), unique=True, index=True)
    status = Column(String(20), default="pending")
    amount = Column(Integer, nullable=False)
    customer_email = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BlogChannel(Base):
    __tablename__ = "blog_channels"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    nicho = Column(String(100), default="Geral")
    lang = Column(String(10), default="PT")
    platform = Column(String(50), default="wordpress")
    site_url = Column(String(500), nullable=True)
    api_endpoint = Column(String(500), nullable=True)
    api_token = Column(String(2000), nullable=True)
    username = Column(String(100), nullable=True)
    app_password = Column(String(500), nullable=True)
    status = Column(String(20), default="active")
    frequency = Column(String(20), default="daily")
    created_at = Column(DateTime, default=datetime.utcnow)


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(String(50), primary_key=True, index=True)
    channel_id = Column(String(50), ForeignKey("blog_channels.id"), nullable=True)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    excerpt = Column(String(1000), nullable=True)
    keywords = Column(String(1000), nullable=True)
    featured_image_url = Column(String(1000), nullable=True)
    status = Column(String(30), default="draft")
    platform_status = Column(String(30), nullable=True)
    platform_post_id = Column(String(100), nullable=True)
    platform_url = Column(String(1000), nullable=True)
    word_count = Column(Integer, default=0)
    topic = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)


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


def create_db_deliverable_app(channel_id: str, name: str, slug: str, nicho: str, app_type: str, config_json: dict):
    db = SessionLocal()
    try:
        new_app = DeliverableApp(
            id=f"app_{uuid.uuid4().hex[:6]}",
            channel_id=channel_id,
            name=name,
            slug=slug,
            nicho=nicho,
            app_type=app_type,
            config_json=config_json,
            status="active"
        )
        db.add(new_app)
        db.commit()
        return {
            "id": new_app.id,
            "channel_id": new_app.channel_id,
            "name": new_app.name,
            "slug": new_app.slug,
            "nicho": new_app.nicho,
            "app_type": new_app.app_type,
            "config_json": new_app.config_json,
            "status": new_app.status,
            "created_at": new_app.created_at.isoformat() if new_app.created_at else None
        }
    finally:
        db.close()

def get_db_deliverable_app_by_slug(slug: str):
    db = SessionLocal()
    try:
        app = db.query(DeliverableApp).filter(DeliverableApp.slug == slug).first()
        if app:
            return {
                "id": app.id,
                "channel_id": app.channel_id,
                "name": app.name,
                "slug": app.slug,
                "nicho": app.nicho,
                "app_type": app.app_type,
                "config_json": app.config_json,
                "status": app.status,
                "created_at": app.created_at.isoformat() if app.created_at else None
            }
        return None
    finally:
        db.close()

def get_db_deliverable_apps():
    db = SessionLocal()
    try:
        apps = db.query(DeliverableApp).order_by(DeliverableApp.created_at.desc()).all()
        return [
            {
                "id": app.id,
                "channel_id": app.channel_id,
                "name": app.name,
                "slug": app.slug,
                "nicho": app.nicho,
                "app_type": app.app_type,
                "config_json": app.config_json,
                "status": app.status,
                "created_at": app.created_at.isoformat() if app.created_at else None
            } for app in apps
        ]
    finally:
        db.close()

def create_db_app_payment(app_id: str, gateway: str, transaction_id: str, amount: int, customer_email: str = None):
    db = SessionLocal()
    try:
        payment = AppPayment(
            id=f"pay_{uuid.uuid4().hex[:6]}",
            app_id=app_id,
            gateway=gateway,
            transaction_id=transaction_id,
            status="pending",
            amount=amount,
            customer_email=customer_email
        )
        db.add(payment)
        db.commit()
        return {
            "id": payment.id,
            "app_id": payment.app_id,
            "gateway": payment.gateway,
            "transaction_id": payment.transaction_id,
            "status": payment.status,
            "amount": payment.amount,
            "customer_email": payment.customer_email
        }
    finally:
        db.close()

def update_db_app_payment(transaction_id: str, status: str):
    db = SessionLocal()
    try:
        pay = db.query(AppPayment).filter(AppPayment.transaction_id == transaction_id).first()
        if pay:
            pay.status = status
            db.commit()
            return True
        return False
    finally:
        db.close()


# ─── Blog CRUD ─────────────────────────────────────────────────────────

def create_db_blog_channel(name: str, nicho: str, lang: str, platform: str = "wordpress",
                           site_url: str = "", api_endpoint: str = "", api_token: str = "") -> dict:
    db = SessionLocal()
    try:
        new_chan = BlogChannel(
            id=f"blg_{uuid.uuid4().hex[:6]}",
            name=name,
            nicho=nicho,
            lang=lang,
            platform=platform,
            site_url=site_url,
            api_endpoint=api_endpoint,
            api_token=api_token,
            status="active",
        )
        db.add(new_chan)
        db.commit()
        return {
            "id": new_chan.id,
            "name": new_chan.name,
            "nicho": new_chan.nicho,
            "lang": new_chan.lang,
            "platform": new_chan.platform,
            "site_url": new_chan.site_url,
            "status": new_chan.status,
        }
    finally:
        db.close()

def get_db_blog_channels() -> list:
    db = SessionLocal()
    try:
        channels = db.query(BlogChannel).order_by(BlogChannel.created_at.desc()).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "nicho": c.nicho,
                "lang": c.lang,
                "platform": c.platform,
                "site_url": c.site_url,
                "status": c.status,
                "frequency": c.frequency,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            } for c in channels
        ]
    finally:
        db.close()

def delete_db_blog_channel(channel_id: str) -> bool:
    db = SessionLocal()
    try:
        db.query(BlogPost).filter(BlogPost.channel_id == channel_id).delete(synchronize_session=False)
        chan = db.query(BlogChannel).filter(BlogChannel.id == channel_id).first()
        if chan:
            db.delete(chan)
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"[Database] Erro ao deletar blog channel: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def create_db_blog_post(channel_id: str, title: str, slug: str, content: str,
                        excerpt: str = "", keywords: str = "", topic: str = "") -> dict:
    db = SessionLocal()
    try:
        new_post = BlogPost(
            id=f"post_{uuid.uuid4().hex[:8]}",
            channel_id=channel_id,
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            keywords=keywords,
            topic=topic,
            status="draft",
            word_count=len(content.split()),
        )
        db.add(new_post)
        db.commit()
        return {
            "id": new_post.id,
            "title": new_post.title,
            "slug": new_post.slug,
            "status": new_post.status,
            "word_count": new_post.word_count,
            "created_at": new_post.created_at.isoformat() if new_post.created_at else None,
        }
    finally:
        db.close()

def get_db_blog_posts(channel_id: str = None, limit: int = 50) -> list:
    db = SessionLocal()
    try:
        q = db.query(BlogPost).order_by(BlogPost.created_at.desc())
        if channel_id:
            q = q.filter(BlogPost.channel_id == channel_id)
        posts = q.limit(limit).all()
        return [
            {
                "id": p.id,
                "channel_id": p.channel_id,
                "title": p.title,
                "slug": p.slug,
                "excerpt": p.excerpt,
                "keywords": p.keywords,
                "status": p.status,
                "platform_status": p.platform_status,
                "platform_url": p.platform_url,
                "word_count": p.word_count,
                "topic": p.topic,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "published_at": p.published_at.isoformat() if p.published_at else None,
            } for p in posts
        ]
    finally:
        db.close()

def get_db_blog_post(post_id: str) -> dict:
    db = SessionLocal()
    try:
        p = db.query(BlogPost).filter(BlogPost.id == post_id).first()
        if p:
            return {
                "id": p.id,
                "channel_id": p.channel_id,
                "title": p.title,
                "slug": p.slug,
                "content": p.content,
                "excerpt": p.excerpt,
                "keywords": p.keywords,
                "featured_image_url": p.featured_image_url,
                "status": p.status,
                "platform_status": p.platform_status,
                "platform_post_id": p.platform_post_id,
                "platform_url": p.platform_url,
                "word_count": p.word_count,
                "topic": p.topic,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "published_at": p.published_at.isoformat() if p.published_at else None,
            }
        return None
    finally:
        db.close()

def update_db_blog_post(post_id: str, **kwargs) -> bool:
    db = SessionLocal()
    try:
        post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
        if post:
            for key, value in kwargs.items():
                if hasattr(post, key):
                    setattr(post, key, value)
            db.commit()
            return True
        return False
    finally:
        db.close()

def get_db_blog_channel(channel_id: str) -> dict:
    db = SessionLocal()
    try:
        c = db.query(BlogChannel).filter(BlogChannel.id == channel_id).first()
        if c:
            return {
                "id": c.id,
                "name": c.name,
                "nicho": c.nicho,
                "lang": c.lang,
                "platform": c.platform,
                "site_url": c.site_url,
                "api_endpoint": c.api_endpoint,
                "api_token": c.api_token,
                "username": c.username,
                "app_password": c.app_password,
                "status": c.status,
                "frequency": c.frequency,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
        return None
    finally:
        db.close()

