from django.contrib import admin

from .models import RegraOperacionalMobile


class RegraOperacionalMobileAdmin(admin.ModelAdmin):
    list_display = (
        'empresa',
        'tipo_operador_alvo',
        'tolerancia_erro_ia_pct',
        'limite_edicao_manual_pct',
        'exige_justificativa',
        'versao',
    )


admin.site.register(RegraOperacionalMobile, RegraOperacionalMobileAdmin)
