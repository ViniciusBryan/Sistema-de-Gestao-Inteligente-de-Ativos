import hashlib
from django.utils import timezone

from .models import DispositivoMovel


def registrar_e_verificar_dispositivo(usuario, device_uuid, device_model=''):
    """
    Registra ou atualiza um DispositivoMovel vinculado ao usuário e à empresa:
    - 1º dispositivo do usuário -> nasce AUTORIZADO.
    - 2º+ dispositivo do usuário -> nasce PENDENTE (exige homologação).
    - Dispositivo existente -> atualiza ultima_atuacao (e vincula responsável/modelo se vazio).
    """
    empresa = getattr(usuario, 'empresa', None)
    device_uuid = (device_uuid or '').strip()
    if not empresa or not device_uuid:
        return None, False

    modelo_limpo = (device_model or '').strip() or 'Dispositivo Mobile/Web'
    agora = timezone.now()

    dispositivo = (
        DispositivoMovel.objects.filter(
            empresa=empresa,
            usuario_responsavel=usuario,
            uuid_dispositivo=device_uuid,
        ).first()
        or DispositivoMovel.objects.filter(
            empresa=empresa,
            usuario_responsavel__isnull=True,
            uuid_dispositivo=device_uuid,
        ).first()
    )

    if dispositivo:
        campos_update = ['ultima_atuacao']
        dispositivo.ultima_atuacao = agora
        if not dispositivo.usuario_responsavel:
            dispositivo.usuario_responsavel = usuario
            campos_update.append('usuario_responsavel')
        if device_model and (not dispositivo.modelo or dispositivo.modelo == 'Desconhecido'):
            dispositivo.modelo = modelo_limpo
            campos_update.append('modelo')
        dispositivo.save(update_fields=campos_update)
        return dispositivo, False

    ja_possui = DispositivoMovel.objects.filter(
        empresa=empresa,
        usuario_responsavel=usuario,
    ).exists()

    status_inicial = (
        DispositivoMovel.StatusAutorizacao.PENDENTE
        if ja_possui
        else DispositivoMovel.StatusAutorizacao.AUTORIZADO
    )

    dispositivo = DispositivoMovel.objects.create(
        empresa=empresa,
        usuario_responsavel=usuario,
        uuid_dispositivo=device_uuid,
        modelo=modelo_limpo,
        status_autorizacao=status_inicial,
        ultima_atuacao=agora,
    )
    return dispositivo, True


def identificar_dispositivo_web(request, usuario):
    """Extrai ou gera (device_uuid, device_model) durante o login no navegador."""
    header_uuid = (request.headers.get('X-Device-UUID') or '').strip()
    post_uuid = (request.POST.get('device_uuid') or '').strip()
    device_model = (
        request.POST.get('device_model')
        or request.headers.get('X-Device-Model')
        or ''
    ).strip()

    if not device_model:
        ua = request.META.get('HTTP_USER_AGENT', '')
        device_model = ua[:80] if ua else 'Navegador Web'

    if header_uuid:
        return header_uuid, device_model

    if post_uuid:
        return post_uuid, device_model

    ua = request.META.get('HTTP_USER_AGENT', 'web')
    ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    hash_curto = hashlib.sha256(f"{ua}:{ip}:{usuario.username}".encode()).hexdigest()[:8].upper()
    return f"WEB-{hash_curto}", device_model
