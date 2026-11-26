from datetime import date
from django.core.management.base import BaseCommand
from django.utils import timezone

from ativos.models import ClasseAtivo, criar_ativos_padrao
from dispositivos.models import DispositivoMovel
from empresas.models import Empresa, Funcionario, Terceirizado, TipoOperador, Usuario
from inventarios.models import Inventario, ItemInventario
from regras.utils import obter_regras_empresa


class Command(BaseCommand):
    help = "Popula o banco de dados com dados iniciais v1.0 para demonstração."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando carga inicial do SIGA Web v1.0..."))

        empresa, _ = Empresa.objects.get_or_create(
            subdominio="prime",
            defaults={
                "razao_social": "Locadora Prime Eventos Ltda",
                "status_ativo": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Empresa: {empresa.razao_social}"))

        for su in Usuario.objects.filter(is_superuser=True, empresa__isnull=True):
            su.empresa = empresa
            su.tipo_operador = TipoOperador.GESTOR
            su.save(update_fields=["empresa", "tipo_operador"])
            self.stdout.write(self.style.SUCCESS(f"[OK] Superusuário '{su.username}' vinculado à empresa"))

        criar_ativos_padrao(empresa)
        obter_regras_empresa(empresa)
        self.stdout.write(self.style.SUCCESS("[OK] Catálogo padrão e regras operacionais garantidos"))

        user_gestor, created = Usuario.objects.get_or_create(
            username="gestor",
            defaults={
                "email": "gestor@prime.com",
                "first_name": "Mariana",
                "last_name": "Gestora",
                "empresa": empresa,
                "tipo_operador": TipoOperador.GESTOR,
                "status_ativo": True,
            },
        )
        if created:
            user_gestor.set_password("senha123")
            user_gestor.save()
            self.stdout.write(self.style.SUCCESS("[OK] Usuário 'gestor' (senha123) criado"))

        user_func, created = Usuario.objects.get_or_create(
            username="funcionario1",
            defaults={
                "email": "funcionario1@prime.com",
                "first_name": "Carlos",
                "last_name": "Silva",
                "empresa": empresa,
                "tipo_operador": TipoOperador.FUNCIONARIO,
                "status_ativo": True,
            },
        )
        if created:
            user_func.set_password("senha123")
            user_func.save()
            Funcionario.objects.create(
                usuario=user_func,
                matricula="MAT-1042",
                departamento="Operações e Logística",
            )
            self.stdout.write(self.style.SUCCESS("[OK] Usuário 'funcionario1' (senha123) criado"))

        user_terc, created = Usuario.objects.get_or_create(
            username="terceirizado1",
            defaults={
                "email": "terceirizado1@prime.com",
                "first_name": "João",
                "last_name": "Montador",
                "empresa": empresa,
                "tipo_operador": TipoOperador.TERCEIRIZADO,
                "status_ativo": True,
            },
        )
        if created:
            user_terc.set_password("senha123")
            user_terc.save()
            Terceirizado.objects.create(
                usuario=user_terc,
                empresa_prestadora="Staff Montagens Terceirizadas Eireli",
                tipo_contrato=Terceirizado.TipoContrato.TEMPORARIO,
                dias_acesso_ano=180,
                data_fim_contrato=date(2027, 12, 31),
            )
            self.stdout.write(self.style.SUCCESS("[OK] Usuário 'terceirizado1' (senha123) criado"))

        disp, _ = DispositivoMovel.objects.get_or_create(
            empresa=empresa,
            uuid_dispositivo="SAMSUNG-TAB-001",
            defaults={
                "usuario_responsavel": user_func,
                "modelo": "Samsung Galaxy Tab Active 3",
                "status_autorizacao": DispositivoMovel.StatusAutorizacao.AUTORIZADO,
            },
        )

        ativo_mesa = ClasseAtivo.objects.filter(empresa=empresa, nome_classe="Mesa Bistrô").first()
        ativo_gradil = ClasseAtivo.objects.filter(empresa=empresa, nome_classe="Gradil").first()

        inv_ok, inv_ok_created = Inventario.objects.get_or_create(
            empresa=empresa,
            usuario=user_func,
            status_auditoria=Inventario.StatusAuditoria.APROVADO,
            defaults={
                "dispositivo": disp,
                "data_hora_inicio": timezone.now(),
                "data_hora_fim": timezone.now(),
                "lat_long": "-23.5505,-46.6333",
            },
        )
        if inv_ok_created and ativo_mesa:
            ItemInventario.objects.create(
                inventario=inv_ok,
                classe_ativo=ativo_mesa,
                qtd_detectada_ia=15,
                qtd_confirmada_humano=15,
            )
            self.stdout.write(self.style.SUCCESS("[OK] Inventário sem divergência criado"))

        inv_div, inv_div_created = Inventario.objects.get_or_create(
            empresa=empresa,
            usuario=user_terc,
            status_auditoria=Inventario.StatusAuditoria.DIVERGENTE,
            defaults={
                "dispositivo": disp,
                "data_hora_inicio": timezone.now(),
                "data_hora_fim": timezone.now(),
                "lat_long": "-23.5510,-46.6340",
            },
        )
        if inv_div_created and ativo_gradil:
            ItemInventario.objects.create(
                inventario=inv_div,
                classe_ativo=ativo_gradil,
                qtd_detectada_ia=8,
                qtd_confirmada_humano=10,
                justificativa="Duas peças estavam no depósito dos fundos fora do alcance da câmera.",
            )
            self.stdout.write(self.style.SUCCESS("[OK] Inventário divergente criado"))

        self.stdout.write(self.style.SUCCESS("\n==> Carga inicial SIGA v1.0 concluída!"))
