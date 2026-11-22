import uuid
from django.db import models
from django.utils import timezone

from empresas.models import Empresa, Usuario


class DispositivoMovel(models.Model):
    """Aparelho móvel/terminal vinculado ao operador e homologado pelo gestor."""

    class StatusAutorizacao(models.TextChoices):
        AUTORIZADO = 'AUTORIZADO', 'Autorizado'
        BLOQUEADO = 'BLOQUEADO', 'Bloqueado'
        PENDENTE = 'PENDENTE', 'Pendente'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='dispositivos',
    )
    usuario_responsavel = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispositivos',
        verbose_name="Usuário Responsável",
    )
    uuid_dispositivo = models.CharField(max_length=100, unique=True)
    modelo = models.CharField(max_length=100, blank=True)
    status_autorizacao = models.CharField(
        max_length=20,
        choices=StatusAutorizacao.choices,
        default=StatusAutorizacao.AUTORIZADO,
    )
    data_registro = models.DateTimeField(default=timezone.now, verbose_name="Data de Registro")
    ultima_atuacao = models.DateTimeField(default=timezone.now, verbose_name="Última Atuação")

    @property
    def dias_sem_atuacao(self):
        if not self.ultima_atuacao:
            return 0
        return max(0, (timezone.now() - self.ultima_atuacao).days)

    @property
    def inativo(self):
        return self.dias_sem_atuacao >= 30

    def __str__(self):
        return f"{self.modelo or 'Dispositivo'} ({self.uuid_dispositivo[:8]}...)"
