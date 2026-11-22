from django.contrib import admin

from .models import DispositivoMovel


class DispositivoMovelAdmin(admin.ModelAdmin):
    list_display = (
        'modelo',
        'uuid_dispositivo',
        'usuario_responsavel',
        'empresa',
        'status_autorizacao',
        'ultima_atuacao',
    )


admin.site.register(DispositivoMovel, DispositivoMovelAdmin)
