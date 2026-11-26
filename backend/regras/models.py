from decimal import Decimal
from django.db import models

from empresas.models import Empresa, TipoOperador


class RegraOperacionalMobile(models.Model):
    """Parâmetros de tolerância da IA e limite de ajuste manual por perfil."""

    DEFAULT_LIMITE_EDICAO_MANUAL_PCT = Decimal('20.0')
    DEFAULT_TOLERANCIA_ERRO_IA_PCT = Decimal('10.0')

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
        default=DEFAULT_LIMITE_EDICAO_MANUAL_PCT,
        help_text="Percentual máximo de variação manual tolerado sem bloqueio (ex: 20%)",
    )
    tolerancia_erro_ia_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_TOLERANCIA_ERRO_IA_PCT,
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

    @staticmethod
    def resolver_tipo_alvo(usuario) -> str:
        """Determina o perfil de regra aplicável ao usuário (Funcionário ou Terceirizado)."""
        tipo_operador = getattr(usuario, 'tipo_operador', None)
        if tipo_operador in (TipoOperador.FUNCIONARIO, TipoOperador.TERCEIRIZADO):
            return tipo_operador
        return TipoOperador.FUNCIONARIO

    @classmethod
    def para_usuario(cls, usuario):
        """Retorna a regra operacional vigente para a empresa e perfil do usuário."""
        empresa = getattr(usuario, 'empresa', None)
        if not empresa:
            return None
        return cls.objects.filter(
            empresa=empresa,
            tipo_operador_alvo=cls.resolver_tipo_alvo(usuario),
        ).first()

    def horario_permitido(self, hora_local) -> bool:
        """Verifica se o horário local está dentro da janela configurada."""
        if not self.horario_inicio or not self.horario_fim:
            return True
        if self.horario_inicio <= self.horario_fim:
            return self.horario_inicio <= hora_local <= self.horario_fim
        return hora_local >= self.horario_inicio or hora_local <= self.horario_fim
