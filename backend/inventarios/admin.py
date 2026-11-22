from django.contrib import admin

from .models import Inventario, ItemInventario, LogAuditoria


class InventarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'usuario', 'dispositivo', 'status_auditoria', 'data_hora_fim')


class ItemInventarioAdmin(admin.ModelAdmin):
    list_display = ('inventario', 'classe_ativo', 'qtd_detectada_ia', 'qtd_confirmada_humano')


class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('inventario', 'usuario_auditor', 'data_hora')


admin.site.register(Inventario, InventarioAdmin)
admin.site.register(ItemInventario, ItemInventarioAdmin)
admin.site.register(LogAuditoria, LogAuditoriaAdmin)
