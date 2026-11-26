from django.contrib import admin

from .models import Empresa, Funcionario, Terceirizado, Usuario


class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('razao_social', 'subdominio', 'status_ativo', 'criado_em')


class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'empresa', 'tipo_operador', 'status_ativo')


class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'matricula', 'departamento')


class TerceirizadoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa_prestadora', 'tipo_contrato', 'dias_acesso_ano', 'data_fim_contrato')


admin.site.register(Empresa, EmpresaAdmin)
admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Funcionario, FuncionarioAdmin)
admin.site.register(Terceirizado, TerceirizadoAdmin)
