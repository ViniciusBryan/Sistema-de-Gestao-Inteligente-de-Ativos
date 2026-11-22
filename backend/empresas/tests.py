from datetime import date
from django.test import Client, TestCase
from django.urls import reverse

from ativos.models import ClasseAtivo
from dispositivos.models import DispositivoMovel
from regras.models import RegraOperacionalMobile
from .models import Empresa, Funcionario, Terceirizado, TipoOperador, Usuario


class EmpresasModuleTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            razao_social="Locadora Alfa Ltda",
            schema_name="alfa",
            subdominio="alfa",
        )
        self.gestor = Usuario.objects.create_user(
            username="gestor.alfa",
            email="gestor@alfa.com",
            password="password123",
            empresa=self.empresa,
            tipo_operador=TipoOperador.GESTOR,
        )
        self.operador = Usuario.objects.create_user(
            username="op.alfa",
            email="op@alfa.com",
            password="password123",
            empresa=self.empresa,
            tipo_operador=TipoOperador.FUNCIONARIO,
        )

    def test_cadastro_empresa_semeia_regras_e_ativos_padrao(self):
        client = Client()
        resp = client.post(
            reverse('cadastro_empresa'),
            {
                'razao_social': 'Beta Eventos S/A',
                'subdominio': 'beta-eventos',
                'first_name': 'Ana',
                'last_name': 'Souza',
                'email': 'ana@beta.com',
                'username': 'ana.gestora',
                'password1': 'SenhaForte@2026',
                'password2': 'SenhaForte@2026',
            },
        )
        self.assertRedirects(resp, reverse('login'))
        nova = Empresa.objects.get(subdominio='beta-eventos')
        self.assertEqual(RegraOperacionalMobile.objects.filter(empresa=nova).count(), 2)
        self.assertEqual(ClasseAtivo.objects.filter(empresa=nova).count(), 2)
        self.assertTrue(Usuario.objects.filter(username='ana.gestora', empresa=nova, tipo_operador=TipoOperador.GESTOR).exists())

    def test_governanca_dispositivo_no_login_web(self):
        c1 = Client()
        resp1 = c1.post(
            reverse('login'),
            {'username': 'op.alfa', 'password': 'password123', 'device_uuid': 'WEB-DEV-1', 'device_model': 'Chrome Win'},
        )
        self.assertEqual(resp1.status_code, 302)
        self.assertEqual(
            DispositivoMovel.objects.get(uuid_dispositivo='WEB-DEV-1').status_autorizacao,
            DispositivoMovel.StatusAutorizacao.AUTORIZADO,
        )

        # 2º aparelho do mesmo usuário nasce PENDENTE e bloqueia login
        c2 = Client()
        resp2 = c2.post(
            reverse('login'),
            {'username': 'op.alfa', 'password': 'password123', 'device_uuid': 'WEB-DEV-2', 'device_model': 'Edge Win'},
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, 'PENDENTE')

    def test_bloqueio_dispositivo_no_login_web(self):
        DispositivoMovel.objects.create(
            empresa=self.empresa,
            usuario_responsavel=self.operador,
            uuid_dispositivo='WEB-BLOQ',
            status_autorizacao=DispositivoMovel.StatusAutorizacao.BLOQUEADO,
        )
        client = Client()
        resp = client.post(
            reverse('login'),
            {'username': 'op.alfa', 'password': 'password123', 'device_uuid': 'WEB-BLOQ'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'BLOQUEADO')

    def test_uc01_crud_usuarios_funcionario_terceirizado_e_toggle(self):
        client = Client()
        client.force_login(self.gestor)

        resp_list = client.get(reverse('usuario_list'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertTemplateUsed(resp_list, 'usuarios/usuario_list.html')

        resp_func = client.post(
            reverse('usuario_novo'),
            {
                'first_name': 'Lucas',
                'last_name': 'Lima',
                'username': 'lucas.func',
                'email': 'lucas@alfa.com',
                'password': 'password123',
                'tipo_operador': TipoOperador.FUNCIONARIO,
                'matricula': 'MAT-999',
                'departamento': 'Galpão',
            },
        )
        self.assertRedirects(resp_func, reverse('usuario_list'))
        self.assertTrue(Funcionario.objects.filter(matricula='MAT-999').exists())

        resp_terc = client.post(
            reverse('usuario_novo'),
            {
                'first_name': 'Pedro',
                'last_name': 'Costa',
                'username': 'pedro.terc',
                'email': 'pedro@terc.com',
                'password': 'password123',
                'tipo_operador': TipoOperador.TERCEIRIZADO,
                'empresa_prestadora': 'Montagens Sul',
                'tipo_contrato': Terceirizado.TipoContrato.DIARIA,
                'dias_acesso_ano': 30,
                'data_fim_contrato': date(2027, 6, 30).isoformat(),
            },
        )
        self.assertRedirects(resp_terc, reverse('usuario_list'))
        terc = Terceirizado.objects.get(usuario__username='pedro.terc')
        self.assertEqual(terc.empresa_prestadora, 'Montagens Sul')

        resp_toggle = client.post(reverse('usuario_status', kwargs={'pk': terc.usuario.pk}))
        self.assertRedirects(resp_toggle, reverse('usuario_list'))
        terc.usuario.refresh_from_db()
        self.assertFalse(terc.usuario.status_ativo)
