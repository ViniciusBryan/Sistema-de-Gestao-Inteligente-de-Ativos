from django.test import Client, TestCase
from django.urls import reverse

from empresas.models import Empresa, TipoOperador, Usuario
from .models import ClasseAtivo


class AtivosModuleTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(razao_social="Locadora A", schema_name="loc_a", subdominio="loca")
        self.outra_empresa = Empresa.objects.create(razao_social="Locadora B", schema_name="loc_b", subdominio="locb")
        self.gestor = Usuario.objects.create_user(
            username="gestor.a",
            email="a@loca.com",
            password="password123",
            empresa=self.empresa,
            tipo_operador=TipoOperador.GESTOR,
        )
        self.client = Client()
        self.client.force_login(self.gestor)

    def test_auto_slug_e_crud_ativo_com_isolamento_tenant(self):
        resp_create = self.client.post(
            reverse('ativo_novo'),
            {
                'nome_classe': 'Palete Madeira Padrão PBR',
                'categoria': 'Logística',
                'descricao': 'Estrutura para transporte.',
            },
        )
        self.assertRedirects(resp_create, reverse('ativo_list'))
        ativo = ClasseAtivo.objects.get(empresa=self.empresa, nome_classe='Palete Madeira Padrão PBR')
        self.assertEqual(ativo.codigo_yolo, 'palete_madeira_padrao_pbr')

        resp_list = self.client.get(reverse('ativo_list'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, 'Palete Madeira Padrão PBR')

        resp_edit = self.client.post(
            reverse('ativo_editar', kwargs={'pk': ativo.pk}),
            {
                'nome_classe': 'Palete PBR',
                'categoria': 'Armazém',
                'descricao': 'Atualizado',
            },
        )
        self.assertRedirects(resp_edit, reverse('ativo_list'))
        ativo.refresh_from_db()
        self.assertEqual(ativo.nome_classe, 'Palete PBR')

        ativo_outro = ClasseAtivo.objects.create(empresa=self.outra_empresa, nome_classe='Cadeira')
        resp_404 = self.client.get(reverse('ativo_editar', kwargs={'pk': ativo_outro.pk}))
        self.assertEqual(resp_404.status_code, 404)
