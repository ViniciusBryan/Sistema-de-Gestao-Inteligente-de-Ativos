from decimal import Decimal
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from ativos.models import ClasseAtivo
from dispositivos.models import DispositivoMovel
from empresas.models import Empresa, TipoOperador, Usuario
from .models import Inventario, ItemInventario, LogAuditoria


class InventariosModuleTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(razao_social="Locadora I", schema_name="loc_i", subdominio="loci")
        self.gestor = Usuario.objects.create_user(
            username="gestor.i",
            email="i@loci.com",
            password="password123",
            empresa=self.empresa,
            tipo_operador=TipoOperador.GESTOR,
        )
        self.ativo = ClasseAtivo.objects.create(empresa=self.empresa, nome_classe="Gradil", codigo_yolo="gradil")
        self.disp = DispositivoMovel.objects.create(empresa=self.empresa, uuid_dispositivo="DEV-INV-1")
        agora = timezone.now()
        self.inv = Inventario.objects.create(
            empresa=self.empresa,
            usuario=self.gestor,
            dispositivo=self.disp,
            data_hora_inicio=agora,
            data_hora_fim=agora,
            status_auditoria=Inventario.StatusAuditoria.DIVERGENTE,
        )
        self.item = ItemInventario.objects.create(
            inventario=self.inv,
            classe_ativo=self.ativo,
            qtd_detectada_ia=10,
            qtd_confirmada_humano=12,
            justificativa="Duas peças fora da foto",
        )
        self.client = Client()
        self.client.force_login(self.gestor)

    def test_calculo_divergencia_e_fluxo_dashboard_auditoria(self):
        self.assertEqual(self.item.divergencia_absoluta, 2)
        self.assertEqual(self.item.divergencia_percentual, Decimal('20.0'))

        resp_dash = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_dash.status_code, 200)
        self.assertTemplateUsed(resp_dash, 'core/dashboard.html')
        self.assertEqual(resp_dash.context['total_divergentes'], 1)

        resp_list = self.client.get(reverse('inventario_list') + '?status=DIVERGENTE')
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, 'Gradil: 12')

        # POST sem parecer é rejeitado com redirect + erro
        self.client.post(
            reverse('inventario_auditar', kwargs={'inventario_id': self.inv.id}),
            {'acao': 'APROVAR', 'parecer': '   '},
        )
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.status_auditoria, Inventario.StatusAuditoria.DIVERGENTE)

        # POST com parecer aprova e cria LogAuditoria
        resp_apr = self.client.post(
            reverse('inventario_auditar', kwargs={'inventario_id': self.inv.id}),
            {'acao': 'APROVAR', 'parecer': 'Recontagem física conferida.'},
        )
        self.assertRedirects(resp_apr, reverse('inventario_auditar', kwargs={'inventario_id': self.inv.id}))
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.status_auditoria, Inventario.StatusAuditoria.APROVADO)
        self.assertEqual(LogAuditoria.objects.filter(inventario=self.inv).count(), 1)
