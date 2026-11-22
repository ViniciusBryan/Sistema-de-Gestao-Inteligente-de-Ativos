import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class Empresa(models.Model):
    """Locadora cliente do sistema (isolamento lógico multi-tenant)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    razao_social = models.CharField(max_length=255)
    schema_name = models.CharField(
        max_length=63,
        unique=True,
        help_text="Identificador único para schema/tenant",
    )
    subdominio = models.CharField(max_length=63, unique=True)
    status_ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.razao_social} ({self.subdominio})"


class TipoOperador(models.TextChoices):
    """Perfis operacionais previstos no domínio do SIGA."""

    GESTOR = 'GESTOR', 'Gestor'
    FUNCIONARIO = 'FUNCIONARIO', 'Funcionário'
    TERCEIRIZADO = 'TERCEIRIZADO', 'Terceirizado'


class Usuario(AbstractUser):
    """Usuário autenticado vinculado a uma Empresa."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='usuarios',
        null=True,
        blank=True,
    )
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    tipo_operador = models.CharField(
        max_length=20,
        choices=TipoOperador.choices,
        default=TipoOperador.FUNCIONARIO,
    )
    status_ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} [{self.get_tipo_operador_display()}]"


class Funcionario(models.Model):
    """Especialização 1:1 para funcionários internos da locadora."""

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='perfil_funcionario',
    )
    matricula = models.CharField(max_length=50, unique=True)
    departamento = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Matrícula: {self.matricula} - {self.usuario.username}"


class Terceirizado(models.Model):
    """Especialização 1:1 para operadores terceirizados com controle de contrato."""

    class TipoContrato(models.TextChoices):
        DIARIA = 'DIARIA', 'Por Diária / Evento'
        TEMPORARIO = 'TEMPORARIO', 'Temporário (Meses)'
        ANUAL = 'ANUAL', 'Contrato Anual'

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='perfil_terceirizado',
    )
    empresa_prestadora = models.CharField(max_length=150)
    tipo_contrato = models.CharField(
        max_length=20,
        choices=TipoContrato.choices,
        default=TipoContrato.TEMPORARIO,
    )
    dias_acesso_ano = models.PositiveIntegerField(
        default=365,
        help_text="Limite de dias de acesso/ano autorizados",
    )
    data_fim_contrato = models.DateField()

    def __str__(self):
        return f"{self.usuario.username} ({self.empresa_prestadora} - {self.get_tipo_contrato_display()})"
