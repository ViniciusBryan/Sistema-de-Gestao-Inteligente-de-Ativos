from decimal import Decimal
from django.db import models

from empresas.models import Empresa, TipoOperador


class RegraOperacionalMobile(models.Model):
    """Parâmetros de tolerância da IA e limite de ajuste manual por perfil."""

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='regras_operacionais',
    )
    tipo_operador_alvo = models.CharField(
        max_length=20,
        choices=[
            (TipoOperador.FUNCIONARIO, 'Funcionário'),
            (TipoOperador.TERCEIRIZADO, 'Terceirizado'),
        ],
    )
    limite_edicao_manual_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('20.0'),
        help_text="Percentual máximo de variação manual tolerado sem bloqueio (ex: 20%)",
    )
    tolerancia_erro_ia_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.0'),
        help_text="Margem para auditoria da IA (padrão 10%)",
    )
    exige_justificativa = models.BooleanField(default=True)
    horario_inicio = models.TimeField(null=True, blank=True)
    horario_fim = models.TimeField(null=True, blank=True)
    versao = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('empresa', 'tipo_operador_alvo')

    def __str__(self):
        return f"Regra {self.tipo_operador_alvo} - {self.empresa.razao_social}"
