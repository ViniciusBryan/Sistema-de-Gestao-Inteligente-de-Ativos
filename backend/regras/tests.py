from decimal import Decimal
from django.test import Client, TestCase
from django.urls import reverse

from empresas.models import Empresa, TipoOperador, Usuario
from .models import RegraOperacionalMobile


class RegrasModuleTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(razao_social="Locadora R", schema_name="loc_r", subdominio="locr")
        self.gestor = Usuario.objects.create_user(
            username="gestor.r",
            email="r@locr.com",
            password="password123",
            empresa=self.empresa,
            tipo_operador=TipoOperador.GESTOR,
        )
        self.client = Client()
        self.client.force_login(self.gestor)

    def test_configurar_regras_incrementa_versao_de_ambos_perfis(self):
        resp_get = self.client.get(reverse('regras_config'))
        self.assertEqual(resp_get.status_code, 200)
        self.assertTemplateUsed(resp_get, 'regras/regras_form.html')

        resp_post = self.client.post(
            reverse('regras_config'),
            {
                'func-tolerancia_erro_ia_pct': '12.00',
                'func-limite_edicao_manual_pct': '25.00',
                'func-exige_justificativa': 'on',
                'terc-tolerancia_erro_ia_pct': '8.00',
                'terc-limite_edicao_manual_pct': '5.00',
                'terc-exige_justificativa': 'on',
            },
        )
        self.assertRedirects(resp_post, reverse('regras_config'))

        r_func = RegraOperacionalMobile.objects.get(empresa=self.empresa, tipo_operador_alvo=TipoOperador.FUNCIONARIO)
        r_terc = RegraOperacionalMobile.objects.get(empresa=self.empresa, tipo_operador_alvo=TipoOperador.TERCEIRIZADO)
        self.assertEqual(r_func.limite_edicao_manual_pct, Decimal('25.00'))
        self.assertEqual(r_terc.tolerancia_erro_ia_pct, Decimal('8.00'))
        self.assertEqual(r_func.versao, 2)
        self.assertEqual(r_terc.versao, 2)
