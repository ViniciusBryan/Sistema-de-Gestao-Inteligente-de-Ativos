from django import forms

from .models import ClasseAtivo


class ClasseAtivoForm(forms.ModelForm):
    class Meta:
        model = ClasseAtivo
        fields = ['nome_classe', 'categoria', 'descricao', 'imagem_referencia']
        labels = {
            'nome_classe': 'Nome do Ativo',
            'categoria': 'Categoria',
            'descricao': 'Descrição do Ativo (Opcional)',
            'imagem_referencia': 'Foto de Referência (Opcional)',
        }
        widgets = {
            'descricao': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Detalhes, dimensões ou observações sobre o ativo...'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
