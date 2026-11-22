from decimal import Decimal

from empresas.models import TipoOperador
from .models import RegraOperacionalMobile


def obter_regras_empresa(empresa):
    """Garante e retorna as regras de Funcionário e Terceirizado da empresa."""
    regra_func, _ = RegraOperacionalMobile.objects.get_or_create(
        empresa=empresa,
        tipo_operador_alvo=TipoOperador.FUNCIONARIO,
        defaults={
            'limite_edicao_manual_pct': Decimal('20.0'),
            'tolerancia_erro_ia_pct': Decimal('10.0'),
            'exige_justificativa': True,
            'versao': 1,
        },
    )
    regra_terc, _ = RegraOperacionalMobile.objects.get_or_create(
        empresa=empresa,
        tipo_operador_alvo=TipoOperador.TERCEIRIZADO,
        defaults={
            'limite_edicao_manual_pct': Decimal('5.0'),
            'tolerancia_erro_ia_pct': Decimal('10.0'),
            'exige_justificativa': True,
            'versao': 1,
        },
    )
    return regra_func, regra_terc
