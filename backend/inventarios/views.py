from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from ativos.models import ClasseAtivo
from dispositivos.models import DispositivoMovel
from empresas.models import Usuario
from .models import Inventario, LogAuditoria


@login_required
def dashboard(request):
    """Painel inicial com indicadores e últimos inventários da empresa."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return render(request, 'core/dashboard.html', {'sem_empresa': True})

    inventarios_qs = Inventario.objects.filter(empresa=empresa)
    total_inventarios = inventarios_qs.count()
    total_divergentes = inventarios_qs.filter(
        status_auditoria=Inventario.StatusAuditoria.DIVERGENTE,
    ).count()
    total_em_analise = inventarios_qs.filter(
        status_auditoria=Inventario.StatusAuditoria.EM_ANALISE,
    ).count()
    total_aprovados = inventarios_qs.filter(
        status_auditoria=Inventario.StatusAuditoria.APROVADO,
    ).count()

    conformidade_ia = 100.0
    if total_inventarios > 0:
        conformidade_ia = ((total_inventarios - total_divergentes) / total_inventarios) * 100.0

    contexto = {
        'empresa': empresa,
        'total_inventarios': total_inventarios,
        'total_divergentes': total_divergentes,
        'total_em_analise': total_em_analise,
        'total_aprovados': total_aprovados,
        'conformidade_ia': conformidade_ia,
        'total_ativos': ClasseAtivo.objects.filter(empresa=empresa).count(),
        'total_dispositivos': DispositivoMovel.objects.filter(empresa=empresa).count(),
        'total_usuarios': Usuario.objects.filter(empresa=empresa).count(),
        'ultimos_inventarios': inventarios_qs.select_related('usuario', 'dispositivo').order_by('-data_hora_fim')[:5],
    }
    return render(request, 'core/dashboard.html', contexto)


@login_required
def listar_inventarios(request):
    """Lista os lotes de inventário da empresa com filtro por status e paginação."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return render(
            request,
            'inventarios/inventario_list.html',
            {'inventarios': [], 'status_atual': 'TODOS', 'total_divergentes': 0},
        )

    qs = (
        Inventario.objects.filter(empresa=empresa)
        .select_related('usuario', 'dispositivo')
        .prefetch_related('itens__classe_ativo')
        .order_by('-data_hora_fim')
    )

    status_filtro = request.GET.get('status')
    if status_filtro and status_filtro in Inventario.StatusAuditoria.values:
        qs = qs.filter(status_auditoria=status_filtro)

    page_obj = Paginator(qs, 15).get_page(request.GET.get('page'))
    total_divergentes = Inventario.objects.filter(
        empresa=empresa,
        status_auditoria=Inventario.StatusAuditoria.DIVERGENTE,
    ).count()

    return render(
        request,
        'inventarios/inventario_list.html',
        {
            'inventarios': page_obj,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'status_atual': status_filtro or 'TODOS',
            'status_choices': Inventario.StatusAuditoria.choices,
            'total_divergentes': total_divergentes,
        },
    )


@login_required
def auditar_inventario(request, inventario_id):
    """Exibe os detalhes da auditoria (UC04) e registra parecer do auditor."""
    inventario = get_object_or_404(
        Inventario.objects.select_related('usuario', 'dispositivo', 'empresa', 'regra_operacional'),
        id=inventario_id,
        empresa=request.user.empresa,
    )

    if request.method == 'POST':
        acao = request.POST.get('acao')
        parecer = (request.POST.get('parecer') or '').strip()

        if not parecer:
            messages.error(request, "O parecer do auditor é obrigatório para registrar a avaliação.")
            return redirect('inventario_auditar', inventario_id=inventario.id)

        novo_status = (
            Inventario.StatusAuditoria.APROVADO
            if acao == 'APROVAR'
            else Inventario.StatusAuditoria.REJEITADO
        )
        with transaction.atomic():
            inventario.status_auditoria = novo_status
            inventario.save(update_fields=['status_auditoria'])
            LogAuditoria.objects.create(
                inventario=inventario,
                usuario_auditor=request.user,
                parecer=parecer,
            )

        status_label = "APROVADO" if novo_status == Inventario.StatusAuditoria.APROVADO else "REJEITADO"
        messages.success(request, f"Inventário avaliado com sucesso! Status alterado para: {status_label}.")
        return redirect('inventario_auditar', inventario_id=inventario.id)

    itens = inventario.itens.select_related('classe_ativo').all()
    logs = inventario.logs_auditoria.select_related('usuario_auditor').all()
    return render(
        request,
        'inventarios/auditoria_detalhe.html',
        {'inventario': inventario, 'itens': itens, 'logs': logs},
    )
