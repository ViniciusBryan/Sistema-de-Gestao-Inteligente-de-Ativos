from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ClasseAtivoForm
from .models import ClasseAtivo


@login_required
def listar_ativos(request):
    empresa = request.user.empresa
    ativos = ClasseAtivo.objects.filter(empresa=empresa).order_by('nome_classe') if empresa else ClasseAtivo.objects.none()
    return render(request, 'ativos/ativo_list.html', {'ativos': ativos})


@login_required
def adicionar_ativo(request):
    form = ClasseAtivoForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        ativo = form.save(commit=False)
        ativo.empresa = request.user.empresa
        ativo.save()
        messages.success(request, f"Ativo '{ativo.nome_classe}' cadastrado com sucesso!")
        return redirect('ativo_list')

    return render(request, 'ativos/ativo_form.html', {'form': form})


@login_required
def editar_ativo(request, pk):
    ativo = get_object_or_404(ClasseAtivo, pk=pk, empresa=request.user.empresa)
    form = ClasseAtivoForm(request.POST or None, request.FILES or None, instance=ativo)
    if form.is_valid():
        form.save()
        messages.success(request, f"Ativo '{ativo.nome_classe}' atualizado com sucesso!")
        return redirect('ativo_list')

    return render(request, 'ativos/ativo_form.html', {'form': form})
