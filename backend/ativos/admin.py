from django.contrib import admin

from .models import ClasseAtivo


class ClasseAtivoAdmin(admin.ModelAdmin):
    list_display = ('nome_classe', 'codigo_yolo', 'categoria', 'empresa')


admin.site.register(ClasseAtivo, ClasseAtivoAdmin)
