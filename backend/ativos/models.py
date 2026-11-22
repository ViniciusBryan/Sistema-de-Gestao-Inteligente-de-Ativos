from django.db import models
from django.utils.text import slugify

from empresas.models import Empresa


class ClasseAtivo(models.Model):
    """Classe de ativo locável homologada pela empresa para detecção por IA."""

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='classes_ativos',
    )
    nome_classe = models.CharField(max_length=100, help_text="Ex: Mesa Bistrô, Gradil")
    codigo_yolo = models.CharField(
        max_length=50,
        blank=True,
        help_text="Identificador interno para o modelo de IA",
    )
    categoria = models.CharField(max_length=100, blank=True)
    descricao = models.TextField(blank=True, default='', verbose_name="Descrição do Ativo")
    imagem_referencia = models.ImageField(upload_to='ativos_referencia/', null=True, blank=True)

    class Meta:
        unique_together = ('empresa', 'nome_classe')

    def save(self, *args, **kwargs):
        if not self.codigo_yolo and self.nome_classe:
            self.codigo_yolo = slugify(self.nome_classe).replace('-', '_')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome_classe} ({self.empresa.razao_social})"


def criar_ativos_padrao(empresa):
    """Garante as classes iniciais padrão no catálogo de uma nova locadora."""
    padroes = [
        ("Mesa Bistrô", "mesa_bistro", "Mobiliário"),
        ("Gradil", "gradil", "Estruturas e Segurança"),
    ]
    for nome, codigo, categoria in padroes:
        ClasseAtivo.objects.get_or_create(
            empresa=empresa,
            nome_classe=nome,
            defaults={'codigo_yolo': codigo, 'categoria': categoria},
        )
