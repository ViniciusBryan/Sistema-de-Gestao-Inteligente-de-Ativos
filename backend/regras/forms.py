from django import forms
from django.core.validators import MinValueValidator, StepValueValidator

from .models import RegraOperacionalMobile


class RegraOperacionalForm(forms.ModelForm):
    class Meta:
        model = RegraOperacionalMobile
        fields = [
            'tolerancia_erro_ia_pct',
            'limite_edicao_manual_pct',
            'exige_justificativa',
            'horario_inicio',
            'horario_fim',
        ]
        labels = {
            'tolerancia_erro_ia_pct': 'Margem para Auditoria (%)',
            'limite_edicao_manual_pct': 'Limite Máximo de Edição Manual (%)',
            'exige_justificativa': 'Exigir Justificativa em Divergências',
            'horario_inicio': 'Horário Inicial Permitido',
            'horario_fim': 'Horário Limite',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('tolerancia_erro_ia_pct', 'limite_edicao_manual_pct'):
            field = self.fields[name]
            field.widget.attrs.update(step=1, min=0)
            field.validators.extend([
                MinValueValidator(0, message='Informe um percentual maior ou igual a zero.'),
                StepValueValidator(1, message='Informe um percentual inteiro.'),
            ])

        for field in self.fields.values():
            css = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'
            field.widget.attrs.setdefault('class', css)
