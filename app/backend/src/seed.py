from datetime import datetime, timedelta, timezone

from .models import *
from .security import *
from .database import *


_SEED_USERS = [
    {"name": "Alice Souza", "email": "alice@example.com", "password": "Senha123"},
    {"name": "Bob Lima",    "email": "bob@example.com",   "password": "Senha123"},
]


def _seed_requests(db, alice_id: int, bob_id: int) -> None:
    now = utcnow()
    
    db.add_all([
        ServiceRequest(
            title="Problema com login no portal",
            description="Não consigo acessar o portal há dois dias. Erro genérico ao tentar entrar.",
            priority=RequestPriority.ALTA, status=RequestStatus.ABERTA,
            created_at=now - timedelta(hours=1), owner_id=alice_id,
        ),
        ServiceRequest(
            title="Solicitação de novo equipamento",
            description="Gostaria de solicitar um monitor adicional para a estação de trabalho.",
            priority=RequestPriority.BAIXA, status=RequestStatus.EM_ANALISE,
            created_at=now - timedelta(days=1), owner_id=alice_id,
        ),
        ServiceRequest(
            title="Erro intermitente no sistema financeiro",
            description="Ao gerar relatório mensal o sistema retorna erro 500 em horários de pico.",
            priority=RequestPriority.MEDIA, status=RequestStatus.FINALIZADA,
            created_at=now - timedelta(days=5), owner_id=alice_id,
        ),
        ServiceRequest(
            title="Atualização do certificado SSL",
            description="Renovar o certificado do domínio interno antes do vencimento previsto.",
            priority=RequestPriority.MEDIA, status=RequestStatus.CANCELADA,
            created_at=now - timedelta(days=10), owner_id=alice_id,
            cancelled_at=now - timedelta(days=9),
        ),
        ServiceRequest(
            title="Configurar VPN corporativa",
            description="Preciso de acesso à VPN para trabalho remoto durante a próxima semana.",
            priority=RequestPriority.ALTA, status=RequestStatus.ABERTA,
            created_at=now - timedelta(hours=3), owner_id=bob_id,
        ),
        ServiceRequest(
            title="Treinamento sobre nova plataforma",
            description="Solicito agendamento de treinamento da equipe sobre a nova plataforma interna.",
            priority=RequestPriority.BAIXA, status=RequestStatus.EM_ANALISE,
            created_at=now - timedelta(days=2), owner_id=bob_id,
        ),
    ])
    db.commit()


def reset_and_seed() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user_ids: dict[str, int] = {}
        for u in _SEED_USERS:
            user = User(name=u["name"], email=u["email"], password_hash=hash_password(u["password"]))
            db.add(user)
            db.flush()
            user_ids[u["email"]] = user.id
        db.commit()
        _seed_requests(db, user_ids["alice@example.com"], user_ids["bob@example.com"])
    finally:
        db.close()
