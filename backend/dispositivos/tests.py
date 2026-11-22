import datetime
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from empresas.models import Empresa, TipoOperador, Usuario
from .models import DispositivoMovel


class DispositivosModuleTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(razao_social="Locadora D", schema_name="loc_d", subdominio="locd")
        self.gestor = Usuario.objects.create_user(
            username="gestor.d",
            email="d@locd.com",
            password="password123",
            empresa=self.empresa,
            tipo_operador=TipoOperador.GESTOR,
        )
        self.client = Client()
        self.client.force_login(self.gestor)

    def test_listagem_prioriza_pendentes_e_toggle_status(self):
        d_auth = DispositivoMovel.objects.create(
            empresa=self.empresa,
            usuario_responsavel=self.gestor,
            uuid_dispositivo='DEV-A',
            modelo='Aparelho A',
            status_autorizacao=DispositivoMovel.StatusAutorizacao.AUTORIZADO,
        )
        d_pend = DispositivoMovel.objects.create(
            empresa=self.empresa,
            usuario_responsavel=self.gestor,
            uuid_dispositivo='DEV-P',
            modelo='Aparelho P',
            status_autorizacao=DispositivoMovel.StatusAutorizacao.PENDENTE,
        )

        resp = self.client.get(reverse('dispositivo_list'))
        self.assertEqual(resp.status_code, 200)
        lista = list(resp.context['dispositivos'])
        self.assertEqual(lista[0].pk, d_pend.pk)

        resp_apr = self.client.post(
            reverse('dispositivo_status', kwargs={'pk': d_pend.pk}),
            {'acao': 'AUTORIZAR'},
        )
        self.assertRedirects(resp_apr, reverse('dispositivo_list'))
        d_pend.refresh_from_db()
        self.assertEqual(d_pend.status_autorizacao, DispositivoMovel.StatusAutorizacao.AUTORIZADO)

        d_auth.ultima_atuacao = timezone.now() - datetime.timedelta(days=35)
        d_auth.save(update_fields=['ultima_atuacao'])
        self.assertTrue(d_auth.inativo)
        self.assertGreaterEqual(d_auth.dias_sem_atuacao, 35)
