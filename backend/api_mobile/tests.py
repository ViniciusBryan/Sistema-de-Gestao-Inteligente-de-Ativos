import base64
import json
import uuid
from decimal import Decimal
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from ativos.models import ClasseAtivo
from dispositivos.models import DispositivoMovel
from empresas.models import Empresa, TipoOperador, Usuario
from inventarios.models import Inventario, ItemInventario
from regras.models import RegraOperacionalMobile


def _basic_auth(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode('ascii')
    return f"Basic {token}"


class ApiMobileTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(razao_social="Empresa API", subdominio="empapi")
        self.gestor = Usuario.objects.create_user(
            username="gestor.api",
            email="gestor@api.com",
            password="password123",
            empresa=self.empresa,
            tipo_operador=TipoOperador.GESTOR,
        )
        self.operador = Usuario.objects.create_user(
            username="funcionario1",
            email="func1@api.com",
            password="senha123",
            empresa=self.empresa,
            tipo_operador=TipoOperador.FUNCIONARIO,
        )
        RegraOperacionalMobile.objects.create(
            empresa=self.empresa,
            tipo_operador_alvo=TipoOperador.FUNCIONARIO,
            limite_edicao_manual_pct=Decimal('20.0'),
            tolerancia_erro_ia_pct=Decimal('10.0'),
            exige_justificativa=True,
        )
        ClasseAtivo.objects.create(
            empresa=self.empresa,
            nome_classe="Grade de Isolamento",
            categoria="Segurança",
        )
        ClasseAtivo.objects.create(
            empresa=self.empresa,
            nome_classe="Gradil",
            codigo_yolo="gradil",
            categoria="Estruturas",
        )

    def test_catalogo_api_autenticada(self):
        self.client.force_login(self.gestor)
        response = self.client.get(reverse('api_catalogo'))
        self.assertEqual(response.status_code, 200)
        codigos = {item['codigo_yolo'] for item in response.json()}
        self.assertIn('grade_de_isolamento', codigos)
        self.assertIn('gradil', codigos)

    def test_login_mobile_e_governanca_dispositivo(self):
        r1 = self.client.post(
            reverse('api_login'),
            data=json.dumps({'username': 'funcionario1', 'password': 'senha123'}),
            content_type='application/json',
            HTTP_X_DEVICE_UUID='MOB-01',
            HTTP_X_DEVICE_MODEL='Pixel 8',
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['dispositivo']['status_autorizacao'], 'AUTORIZADO')

        r2 = self.client.post(
            reverse('api_login'),
            data=json.dumps({'username': 'funcionario1', 'password': 'senha123'}),
            content_type='application/json',
            HTTP_X_DEVICE_UUID='MOB-02',
        )
        self.assertEqual(r2.status_code, 403)
        self.assertEqual(r2.json()['status_autorizacao'], 'PENDENTE')

    def test_sincronizar_regras_v1_e_divergencia(self):
        auth = _basic_auth('funcionario1', 'senha123')
        agora = timezone.now().isoformat()

        def post_sync(ia, humano, justificativa=''):
            payload = {
                'id': str(uuid.uuid4()),
                'data_hora_inicio': agora,
                'data_hora_fim': agora,
                'lat_long': '-23.55,-46.63',
                'itens': [
                    {
                        'classe_codigo': 'gradil',
                        'qtd_detectada_ia': ia,
                        'qtd_confirmada_humano': humano,
                        'justificativa': justificativa,
                    }
                ],
            }
            return self.client.post(
                reverse('api_sincronizar'),
                data=json.dumps(payload),
                content_type='application/json',
                HTTP_AUTHORIZATION=auth,
                HTTP_X_DEVICE_UUID='MOB-SYNC-1',
            )

        # Sem divergência -> 201 EM_ANALISE
        r_ok = post_sync(10, 10)
        self.assertEqual(r_ok.status_code, 201)
        self.assertEqual(r_ok.json()['status'], Inventario.StatusAuditoria.EM_ANALISE)

        # > 10% sem justificativa -> 422
        r_sem_just = post_sync(10, 12, '')
        self.assertEqual(r_sem_just.status_code, 422)
        self.assertIn('justificativa', r_sem_just.json()['detalhes'])

        # 15% (>10% e <=20%) com justificativa -> 201 DIVERGENTE
        r_div = post_sync(20, 23, 'Três gradis atrás do palco')
        self.assertEqual(r_div.status_code, 201)
        self.assertEqual(r_div.json()['status'], Inventario.StatusAuditoria.DIVERGENTE)

        # > 20% mesmo com justificativa -> 422 limite_operacional (contrato v1.0)
        r_excesso = post_sync(10, 15, 'Cinco extras')
        self.assertEqual(r_excesso.status_code, 422)
        self.assertIn('limite_operacional', r_excesso.json()['detalhes'])

        # Aparelho bloqueado recebe 403
        DispositivoMovel.objects.filter(uuid_dispositivo='MOB-SYNC-1').update(
            status_autorizacao=DispositivoMovel.StatusAutorizacao.BLOQUEADO
        )
        r_bloq = post_sync(10, 10)
        self.assertEqual(r_bloq.status_code, 403)

    def test_regras_api_autenticada_e_dispositivo(self):
        r_anon = self.client.get(reverse('api_regras'))
        self.assertEqual(r_anon.status_code, 403)

        auth = _basic_auth('funcionario1', 'senha123')
        r_ok = self.client.get(
            reverse('api_regras'),
            HTTP_AUTHORIZATION=auth,
            HTTP_X_DEVICE_UUID='MOB-REGRA-1',
            HTTP_X_DEVICE_MODEL='Pixel 8',
        )
        self.assertEqual(r_ok.status_code, 200)
        payload = r_ok.json()
        self.assertEqual(payload['tipo_operador_alvo'], 'FUNCIONARIO')
        self.assertEqual(payload['tolerancia_erro_ia_pct'], 10.0)
        self.assertEqual(payload['limite_edicao_manual_pct'], 20.0)
        self.assertTrue(payload['exige_justificativa'])
        self.assertTrue(payload['bloquear_excesso_edicao'])
        self.assertEqual(payload['versao'], 1)
        self.assertIn('servidor_hora_local', payload)
        self.assertTrue(payload['dentro_horario_permitido'])

        DispositivoMovel.objects.filter(uuid_dispositivo='MOB-REGRA-1').update(
            status_autorizacao=DispositivoMovel.StatusAutorizacao.BLOQUEADO
        )
        r_bloq = self.client.get(
            reverse('api_regras'),
            HTTP_AUTHORIZATION=auth,
            HTTP_X_DEVICE_UUID='MOB-REGRA-1',
        )
        self.assertEqual(r_bloq.status_code, 403)

        r_login = self.client.post(
            reverse('api_login'),
            data=json.dumps({'username': 'funcionario1', 'password': 'senha123'}),
            content_type='application/json',
            HTTP_X_DEVICE_UUID='MOB-REGRA-1',
        )
        self.assertEqual(r_login.status_code, 403)

        DispositivoMovel.objects.filter(uuid_dispositivo='MOB-REGRA-1').update(
            status_autorizacao=DispositivoMovel.StatusAutorizacao.AUTORIZADO
        )
        r_login_ok = self.client.post(
            reverse('api_login'),
            data=json.dumps({'username': 'funcionario1', 'password': 'senha123'}),
            content_type='application/json',
            HTTP_X_DEVICE_UUID='MOB-REGRA-1',
        )
        self.assertEqual(r_login_ok.status_code, 200)
        login_json = r_login_ok.json()
        self.assertIn('regra_operacional', login_json)
        self.assertEqual(login_json['regra_operacional']['tipo_operador_alvo'], 'FUNCIONARIO')
        self.assertTrue(login_json['dentro_horario_permitido'])

    def test_sincronizar_alias_table_joint_para_mesa_bistro(self):
        mesa = ClasseAtivo.objects.create(
            empresa=self.empresa,
            nome_classe="Mesa Bistrô",
            codigo_yolo="mesa_bistro",
            categoria="Mobiliário",
        )
        auth = _basic_auth('funcionario1', 'senha123')
        agora = timezone.now().isoformat()
        inv_id = str(uuid.uuid4())

        r_ok = self.client.post(
            reverse('api_sincronizar'),
            data=json.dumps({
                'id': inv_id,
                'data_hora_inicio': agora,
                'data_hora_fim': agora,
                'lat_long': '-23.55,-46.63',
                'itens': [
                    {
                        'classe_codigo': 'table_joint',
                        'qtd_detectada_ia': 6,
                        'qtd_confirmada_humano': 6,
                        'justificativa': '',
                    }
                ],
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=auth,
            HTTP_X_DEVICE_UUID='MOB-ALIAS-1',
        )
        self.assertEqual(r_ok.status_code, 201)
        self.assertEqual(ItemInventario.objects.get(inventario_id=inv_id).classe_ativo, mesa)

        r_desconhecida = self.client.post(
            reverse('api_sincronizar'),
            data=json.dumps({
                'id': str(uuid.uuid4()),
                'data_hora_inicio': agora,
                'data_hora_fim': agora,
                'lat_long': '-23.55,-46.63',
                'itens': [
                    {
                        'classe_codigo': 'desconhecida',
                        'qtd_detectada_ia': 2,
                        'qtd_confirmada_humano': 2,
                        'justificativa': '',
                    }
                ],
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=auth,
            HTTP_X_DEVICE_UUID='MOB-ALIAS-1',
        )
        self.assertEqual(r_desconhecida.status_code, 422)

    def test_regras_api_fallback_padrao_quando_sem_regra_no_banco(self):
        RegraOperacionalMobile.objects.filter(empresa=self.empresa).delete()
        auth = _basic_auth('funcionario1', 'senha123')

        r_fallback = self.client.get(
            reverse('api_regras'),
            HTTP_AUTHORIZATION=auth,
            HTTP_X_DEVICE_UUID='MOB-FALLBACK-1',
        )
        self.assertEqual(r_fallback.status_code, 200)
        payload = r_fallback.json()
        self.assertEqual(payload['tipo_operador_alvo'], 'FUNCIONARIO')
        self.assertEqual(payload['tolerancia_erro_ia_pct'], 10.0)
        self.assertEqual(payload['limite_edicao_manual_pct'], 20.0)
        self.assertTrue(payload['exige_justificativa'])
        self.assertTrue(payload['bloquear_excesso_edicao'])
        self.assertEqual(payload['versao'], 1)
        self.assertTrue(payload['dentro_horario_permitido'])
