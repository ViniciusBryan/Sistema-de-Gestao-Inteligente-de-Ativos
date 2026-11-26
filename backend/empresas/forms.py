from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Empresa, Terceirizado, TipoOperador, Usuario


class CadastroEmpresaForm(forms.Form):
    """Formulário de onboarding criando Locadora e o primeiro Gestor."""

    razao_social = forms.CharField(max_length=255, label="Razão social")
    subdominio = forms.SlugField(
        max_length=63,
        label="Identificador (subdomínio)",
        help_text="Apenas letras minúsculas, números e hífen",
    )
    first_name = forms.CharField(max_length=150, label="Nome")
    last_name = forms.CharField(max_length=150, label="Sobrenome")
    email = forms.EmailField(label="E-mail")
    username = forms.CharField(max_length=150, label="Usuário de acesso")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Senha")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmar senha")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_subdominio(self):
        sub = self.cleaned_data['subdominio'].lower()
        if Empresa.objects.filter(subdominio=sub).exists():
            raise ValidationError("Este identificador já está em uso.")
        return sub

    def clean_username(self):
        username = self.cleaned_data['username']
        if Usuario.objects.filter(username__iexact=username).exists():
            raise ValidationError("Este nome de usuário já existe.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "As senhas não conferem.")
        elif p1:
            try:
                validate_password(
                    p1,
                    user=Usuario(
                        username=cleaned.get('username', ''),
                        email=cleaned.get('email', ''),
                        first_name=cleaned.get('first_name', ''),
                        last_name=cleaned.get('last_name', ''),
                    ),
                )
            except ValidationError as exc:
                self.add_error('password1', exc)
        return cleaned


class UsuarioCreateForm(forms.Form):
    """Formulário para cadastrar Gestor, Funcionário ou Terceirizado na equipe."""

    first_name = forms.CharField(max_length=150, label="Nome")
    last_name = forms.CharField(max_length=150, label="Sobrenome")
    username = forms.CharField(max_length=150, label="Nome de Usuário")
    email = forms.EmailField(label="E-mail")
    password = forms.CharField(widget=forms.PasswordInput, label="Senha para login")
    tipo_operador = forms.ChoiceField(
        choices=[
            (TipoOperador.FUNCIONARIO, 'Funcionário'),
            (TipoOperador.TERCEIRIZADO, 'Terceirizado'),
            (TipoOperador.GESTOR, 'Gestor / Administrador'),
        ],
        label="Tipo de Operador / Perfil",
    )

    # Campos específicos para Funcionário
    matricula = forms.CharField(max_length=50, required=False, label="Matrícula")
    departamento = forms.CharField(max_length=100, required=False, label="Departamento")

    # Campos específicos para Terceirizado
    empresa_prestadora = forms.CharField(max_length=150, required=False, label="Empresa Prestadora")
    tipo_contrato = forms.ChoiceField(
        choices=Terceirizado.TipoContrato.choices,
        required=False,
        label="Tipo de Contrato",
    )
    dias_acesso_ano = forms.IntegerField(
        required=False,
        initial=365,
        label="Limite de Dias de Acesso / Ano",
    )
    data_fim_contrato = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="Data Fim do Contrato",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_username(self):
        username = self.cleaned_data['username']
        if Usuario.objects.filter(username__iexact=username).exists():
            raise ValidationError("Este nome de usuário já está em uso.")
        return username
