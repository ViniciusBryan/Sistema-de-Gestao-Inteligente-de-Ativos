from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import RegraOperacionalForm
from .utils import obter_regras_empresa


@login_required
def configurar_regras(request):
    regra_func, regra_terc = obter_regras_empresa(request.user.empresa)
    form_func = RegraOperacionalForm(request.POST or None, instance=regra_func, prefix='func')
    form_terc = RegraOperacionalForm(request.POST or None, instance=regra_terc, prefix='terc')

    if request.method == 'POST' and form_func.is_valid() and form_terc.is_valid():
        with transaction.atomic():
            for form in (form_func, form_terc):
                regra = form.save(commit=False)
                regra.versao += 1
                regra.save()

        messages.success(request, "Regras operacionais da IA e limites de perfil atualizados com sucesso!")
        return redirect('regras_config')

    return render(
        request,
        'regras/regras_form.html',
        {'form_func': form_func, 'form_terc': form_terc},
    )
