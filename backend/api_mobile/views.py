import uuid
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dispositivos.models import DispositivoMovel
from dispositivos.utils import registrar_e_verificar_dispositivo
from inventarios.models import Inventario, ItemInventario
from regras.models import RegraOperacionalMobile
from .serializers import InventarioSyncSerializer, serializar_regra_mobile


def _resposta_dispositivo_nao_autorizado(dispositivo, incluir_detalhes=False):
    """Retorna Response 403 quando o dispositivo estiver bloqueado ou pendente."""
    if not dispositivo:
        return None

    status_disp = dispositivo.status_autorizacao
    if status_disp == DispositivoMovel.StatusAutorizacao.BLOQUEADO:
        mensagem = 'Dispositivo bloqueado pela administração.'
    elif status_disp == DispositivoMovel.StatusAutorizacao.PENDENTE:
        mensagem = (
            'Novo dispositivo registrado como PENDENTE. Aguarde a homologação do gestor.'
            if incluir_detalhes
            else 'Novo dispositivo pendente de homologação pela administração.'
        )
    else:
        return None

    payload = {'error': mensagem}
    if incluir_detalhes:
        payload['status_autorizacao'] = status_disp
        payload['uuid_dispositivo'] = dispositivo.uuid_dispositivo
    return Response(payload, status=status.HTTP_403_FORBIDDEN)


def _verificar_dispositivo_header(request):
    """Verifica o header X-Device-UUID e retorna (dispositivo, erro_response)."""
    device_uuid = request.headers.get('X-Device-UUID')
    if not device_uuid:
        return None, None

    dispositivo, _ = registrar_e_verificar_dispositivo(
        request.user,
        device_uuid,
        request.headers.get('X-Device-Model', 'Desconhecido'),
    )
    return dispositivo, _resposta_dispositivo_nao_autorizado(dispositivo)


class LoginMobileAPIView(APIView):
    """Autentica operador mobile e valida status do dispositivo."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        usuario = authenticate(
            request,
            username=request.data.get('username'),
            password=request.data.get('password'),
        )
        if not usuario:
            return Response({'error': 'Credenciais inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not usuario.status_ativo or not usuario.is_active:
            return Response({'error': 'Usuário inativo.'}, status=status.HTTP_403_FORBIDDEN)

        device_uuid = request.headers.get('X-Device-UUID') or request.data.get('device_uuid')
        device_model = request.headers.get('X-Device-Model') or request.data.get('device_model', 'Smartphone Mobile')
        dispositivo, _ = registrar_e_verificar_dispositivo(usuario, device_uuid, device_model)

        erro_disp = _resposta_dispositivo_nao_autorizado(dispositivo, incluir_detalhes=True)
        if erro_disp:
            return erro_disp

        regra = RegraOperacionalMobile.para_usuario(usuario)
        hora_atual = timezone.localtime().time()

        return Response(
            {
                'usuario': usuario.username,
                'nome': usuario.get_full_name() or usuario.username,
                'tipo_operador': usuario.tipo_operador,
                'dispositivo': {
                    'uuid': dispositivo.uuid_dispositivo if dispositivo else None,
                    'modelo': dispositivo.modelo if dispositivo else None,
                    'status_autorizacao': dispositivo.status_autorizacao if dispositivo else None,
                    'data_registro': dispositivo.data_registro.isoformat() if dispositivo else None,
                    'ultima_atuacao': dispositivo.ultima_atuacao.isoformat() if dispositivo else None,
                },
                'regra_operacional': serializar_regra_mobile(usuario, regra),
                'dentro_horario_permitido': regra.horario_permitido(hora_atual) if regra else True,
                'message': 'Login realizado e dispositivo verificado com sucesso.',
            },
            status=status.HTTP_200_OK,
        )


class SincronizacaoAPIView(APIView):
    """Sincronização idempotente de inventários offline-first do App Mobile."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return Response({'error': 'Usuário não vinculado a uma Empresa.'}, status=status.HTTP_400_BAD_REQUEST)

        dispositivo, erro_disp = _verificar_dispositivo_header(request)
        if erro_disp:
            return erro_disp

        serializer = InventarioSyncSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            regra_atual = RegraOperacionalMobile.para_usuario(request.user)
            return Response(
                {
                    'error': 'Violação de regra operacional',
                    'detalhes': serializer.errors,
                    'regra_operacional': serializar_regra_mobile(request.user, regra_atual),
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        validated = serializer.validated_data
        regra = validated['_regra_aplicada']
        tolerancia = (
            regra.tolerancia_erro_ia_pct
            if regra
            else RegraOperacionalMobile.DEFAULT_TOLERANCIA_ERRO_IA_PCT
        )

        with transaction.atomic():
            inventario, _ = Inventario.objects.update_or_create(
                id=validated['id'],
                defaults={
                    'empresa': empresa,
                    'usuario': request.user,
                    'dispositivo': dispositivo,
                    'regra_operacional': regra,
                    'data_hora_inicio': validated['data_hora_inicio'],
                    'data_hora_fim': validated['data_hora_fim'],
                    'lat_long': validated.get('lat_long', ''),
                    'status_auditoria': Inventario.StatusAuditoria.EM_ANALISE,
                },
            )

            houve_divergencia = False
            for item in validated['itens']:
                foto_upload = item.get('foto_arquivo') or item.get('foto')
                item_defaults = {
                    'classe_ativo': item['classe_ativo_instancia'],
                    'qtd_detectada_ia': item.get('qtd_detectada_ia', 0),
                    'qtd_confirmada_humano': item.get('qtd_confirmada_humano', 0),
                    'justificativa': item.get('justificativa', ''),
                    'detections_json': item.get('detections_json', []),
                }
                if foto_upload:
                    item_defaults['foto'] = foto_upload

                item_obj, _ = ItemInventario.objects.update_or_create(
                    id=item.get('id') or uuid.uuid4(),
                    inventario=inventario,
                    defaults=item_defaults,
                )
                if item_obj.divergencia_percentual > tolerancia:
                    houve_divergencia = True

            if houve_divergencia:
                inventario.status_auditoria = Inventario.StatusAuditoria.DIVERGENTE
                inventario.save(update_fields=['status_auditoria'])

        return Response(
            {
                'id': str(inventario.id),
                'status': inventario.status_auditoria,
                'timestamp': timezone.now().isoformat(),
                'regra_operacional': serializar_regra_mobile(request.user, regra),
                'message': 'Inventário sincronizado com sucesso.',
            },
            status=status.HTTP_201_CREATED,
        )


class CatalogoAtivosAPIView(APIView):
    """Lista as classes de ativos da empresa para o aplicativo móvel."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return Response([], status=status.HTTP_200_OK)

        _, erro_disp = _verificar_dispositivo_header(request)
        if erro_disp:
            return erro_disp

        ativos = empresa.classes_ativos.all().values('id', 'nome_classe', 'codigo_yolo', 'categoria')
        return Response(list(ativos), status=status.HTTP_200_OK)


class RegraOperacionalMobileAPIView(APIView):
    """Retorna a regra operacional vigente do operador para sincronização do app móvel."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        _, erro_disp = _verificar_dispositivo_header(request)
        if erro_disp:
            return erro_disp

        regra = RegraOperacionalMobile.para_usuario(request.user)
        hora_atual = timezone.localtime().time()
        payload = serializar_regra_mobile(request.user, regra, fallback_padrao=True)
        payload['servidor_hora_local'] = hora_atual.strftime('%H:%M')
        payload['dentro_horario_permitido'] = regra.horario_permitido(hora_atual) if regra else True
        return Response(payload, status=status.HTTP_200_OK)
