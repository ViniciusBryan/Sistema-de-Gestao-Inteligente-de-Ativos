from decimal import Decimal
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
from .serializers import InventarioSyncSerializer


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
    if not dispositivo:
        return None, None

    if dispositivo.status_autorizacao == DispositivoMovel.StatusAutorizacao.BLOQUEADO:
        return dispositivo, Response(
            {'error': 'Dispositivo bloqueado pela administração.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    if dispositivo.status_autorizacao == DispositivoMovel.StatusAutorizacao.PENDENTE:
        return dispositivo, Response(
            {'error': 'Novo dispositivo pendente de homologação pela administração.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return dispositivo, None


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

        if dispositivo and dispositivo.status_autorizacao == DispositivoMovel.StatusAutorizacao.BLOQUEADO:
            return Response(
                {
                    'error': 'Dispositivo bloqueado pela administração.',
                    'status_autorizacao': dispositivo.status_autorizacao,
                    'uuid_dispositivo': dispositivo.uuid_dispositivo,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if dispositivo and dispositivo.status_autorizacao == DispositivoMovel.StatusAutorizacao.PENDENTE:
            return Response(
                {
                    'error': 'Novo dispositivo registrado como PENDENTE. Aguarde a homologação do gestor.',
                    'status_autorizacao': dispositivo.status_autorizacao,
                    'uuid_dispositivo': dispositivo.uuid_dispositivo,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

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
            return Response(
                {'error': 'Violação de regra operacional', 'detalhes': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        validated = serializer.validated_data
        regra = validated['_regra_aplicada']
        tolerancia = regra.tolerancia_erro_ia_pct if regra else Decimal('10.0')

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
                item_obj, _ = ItemInventario.objects.update_or_create(
                    id=item.get('id') or uuid.uuid4(),
                    inventario=inventario,
                    defaults={
                        'classe_ativo': item['classe_ativo_instancia'],
                        'qtd_detectada_ia': item.get('qtd_detectada_ia', 0),
                        'qtd_confirmada_humano': item.get('qtd_confirmada_humano', 0),
                        'justificativa': item.get('justificativa', ''),
                        'detections_json': item.get('detections_json', []),
                        'foto': item.get('foto'),
                    },
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
