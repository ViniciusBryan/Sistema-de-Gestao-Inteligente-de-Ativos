from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from ativos.models import criar_ativos_padrao
from dispositivos.models import DispositivoMovel
from dispositivos.utils import identificar_dispositivo_web, registrar_e_verificar_dispositivo
from regras.utils import obter_regras_empresa
from .forms import CadastroEmpresaForm, UsuarioCreateForm
from .models import Empresa, Funcionario, Terceirizado, TipoOperador, Usuario


def entrar(request):
    """Autentica o usuário web e valida governança do dispositivo."""
    form = AuthenticationForm(request, data=request.POST or None)
    next_url = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST' and form.is_valid():
        usuario = form.get_user()
        if not usuario.status_ativo:
            form.add_error(None, "Este usuário está desativado pelo gestor.")
            return render(request, 'auth/login.html', {'form': form, 'next': next_url})

        if usuario.empresa:
            device_uuid, device_model = identificar_dispositivo_web(request, usuario)
            dispositivo, _ = registrar_e_verificar_dispositivo(usuario, device_uuid, device_model)

            if dispositivo and dispositivo.status_autorizacao == DispositivoMovel.StatusAutorizacao.BLOQUEADO:
                form.add_error(
                    None,
                    f"Acesso negado: este dispositivo ({dispositivo.uuid_dispositivo}) está BLOQUEADO pela administração.",
                )
                return render(request, 'auth/login.html', {'form': form, 'next': next_url})

            if dispositivo and dispositivo.status_autorizacao == DispositivoMovel.StatusAutorizacao.PENDENTE:
                form.add_error(
                    None,
                    f"Novo dispositivo detectado ({dispositivo.uuid_dispositivo}). "
                    "O pedido de homologação foi registrado como PENDENTE e aguarda liberação do gestor.",
                )
                return render(request, 'auth/login.html', {'form': form, 'next': next_url})

        login(request, usuario)
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect('dashboard')

    return render(request, 'auth/login.html', {'form': form, 'next': next_url})


def sair(request):
    """Encerra a sessão atual via POST e redireciona para o login."""
    if request.method == 'POST':
        logout(request)
    return redirect('login')


def cadastrar_empresa(request):
    """Onboarding de uma nova locadora, seu primeiro gestor, regras e ativos iniciais."""
    form = CadastroEmpresaForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        subdominio = data['subdominio']

        with transaction.atomic():
            empresa = Empresa.objects.create(
                razao_social=data['razao_social'],
                subdominio=subdominio,
                status_ativo=True,
            )
            Usuario.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password1'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                empresa=empresa,
                tipo_operador=TipoOperador.GESTOR,
                status_ativo=True,
            )
            obter_regras_empresa(empresa)
            criar_ativos_padrao(empresa)

        messages.success(
            request,
            f"Locadora '{empresa.razao_social}' cadastrada com sucesso! Faça login com o usuário criado.",
        )
        return redirect('login')

    return render(request, 'auth/cadastro_empresa.html', {'form': form})


@login_required
def listar_usuarios(request):
    empresa = request.user.empresa
    if not empresa:
        usuarios = Usuario.objects.none()
    else:
        usuarios = (
            Usuario.objects.filter(empresa=empresa)
            .select_related('perfil_funcionario', 'perfil_terceirizado')
            .order_by('-date_joined')
        )
    return render(request, 'usuarios/usuario_list.html', {'usuarios': usuarios})


@login_required
def adicionar_usuario(request):
    form = UsuarioCreateForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            user = Usuario.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                empresa=request.user.empresa,
                tipo_operador=data['tipo_operador'],
                status_ativo=True,
            )

            if data['tipo_operador'] == TipoOperador.FUNCIONARIO:
                Funcionario.objects.create(
                    usuario=user,
                    matricula=data.get('matricula') or f"MAT-{user.username}",
                    departamento=data.get('departamento', ''),
                )
            elif data['tipo_operador'] == TipoOperador.TERCEIRIZADO:
                Terceirizado.objects.create(
                    usuario=user,
                    empresa_prestadora=data.get('empresa_prestadora') or 'Prestadora Externa',
                    tipo_contrato=data.get('tipo_contrato') or Terceirizado.TipoContrato.TEMPORARIO,
                    dias_acesso_ano=data.get('dias_acesso_ano') or 365,
                    data_fim_contrato=data.get('data_fim_contrato') or timezone.now().date(),
                )

        messages.success(request, f"Usuário '{user.username}' adicionado à equipe com sucesso!")
        return redirect('usuario_list')

    return render(request, 'usuarios/usuario_form.html', {'form': form})


@login_required
def alternar_status_usuario(request, pk):
    if request.method == 'POST':
        user = get_object_or_404(Usuario, pk=pk, empresa=request.user.empresa)
        user.status_ativo = not user.status_ativo
        user.save(update_fields=['status_ativo'])
        status_txt = "ativado" if user.status_ativo else "desativado"
        messages.info(request, f"Usuário '{user.username}' {status_txt}.")
    return redirect('usuario_list')
