from decimal import Decimal
import uuid
from django.db import models

from ativos.models import ClasseAtivo
from dispositivos.models import DispositivoMovel
from empresas.models import Empresa, Usuario
from regras.models import RegraOperacionalMobile


class Inventario(models.Model):
    """Lote de contagem sincronizado pelo app mobile para auditoria web."""

    class StatusAuditoria(models.TextChoices):
        APROVADO = 'APROVADO', 'Aprovado'
        REJEITADO = 'REJEITADO', 'Rejeitado'
        EM_ANALISE = 'EM_ANALISE', 'Em Análise'
        DIVERGENTE = 'DIVERGENTE', 'Divergente'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='inventarios')
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='inventarios')
    dispositivo = models.ForeignKey(DispositivoMovel, on_delete=models.SET_NULL, null=True, blank=True)
    regra_operacional = models.ForeignKey(RegraOperacionalMobile, on_delete=models.SET_NULL, null=True, blank=True)
    data_hora_inicio = models.DateTimeField()
    data_hora_fim = models.DateTimeField()
    status_auditoria = models.CharField(
        max_length=30,
        choices=StatusAuditoria.choices,
        default=StatusAuditoria.EM_ANALISE,
    )
    lat_long = models.CharField(max_length=100, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inventário {str(self.id)[:8]} - {self.usuario.username} ({self.status_auditoria})"


class ItemInventario(models.Model):
    """Item individual de um lote de inventário com contagem IA vs. Operador."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name='itens')
    classe_ativo = models.ForeignKey(
        ClasseAtivo,
        on_delete=models.PROTECT,
        related_name='itens_inventariados',
    )
    qtd_detectada_ia = models.PositiveIntegerField(default=0, help_text="Contagem detectada pela IA")
    qtd_confirmada_humano = models.PositiveIntegerField(default=0, help_text="Contagem ajustada pelo operador")
    justificativa = models.TextField(blank=True, null=True, help_text="Opcional caso haja divergência")
    foto = models.ImageField(upload_to='contagens_fotos/', null=True, blank=True)
    detections_json = models.JSONField(default=list, blank=True, help_text="Bounding boxes [x, y, w, h, conf, class]")

    @property
    def divergencia_absoluta(self):
        return abs(self.qtd_confirmada_humano - self.qtd_detectada_ia)

    @property
    def divergencia_percentual(self):
        if self.qtd_detectada_ia == 0:
            return Decimal('0.0') if self.qtd_confirmada_humano == 0 else Decimal('100.0')
        return (Decimal(self.divergencia_absoluta) / Decimal(self.qtd_detectada_ia)) * Decimal('100.0')

    def __str__(self):
        return f"{self.classe_ativo.nome_classe}: IA={self.qtd_detectada_ia} | Humano={self.qtd_confirmada_humano}"


class LogAuditoria(models.Model):
    """Registro append-only dos pareceres emitidos pelo auditor web."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name='logs_auditoria')
    usuario_auditor = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='auditorias_realizadas',
    )
    parecer = models.TextField()
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_hora']

    def __str__(self):
        return f"Parecer por {self.usuario_auditor.username} em {self.data_hora:%d/%m/%Y %H:%M}"
