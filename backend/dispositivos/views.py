from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404, redirect, render

from .models import DispositivoMovel


@login_required
def listar_dispositivos(request):
    empresa = request.user.empresa
    if not empresa:
        dispositivos = DispositivoMovel.objects.none()
    else:
        dispositivos = (
            DispositivoMovel.objects.filter(empresa=empresa)
            .select_related('usuario_responsavel')
            .annotate(
                ordem_pendente=Case(
                    When(status_autorizacao=DispositivoMovel.StatusAutorizacao.PENDENTE, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by('ordem_pendente', '-ultima_atuacao')
        )
    return render(request, 'dispositivos/dispositivo_list.html', {'dispositivos': dispositivos})


@login_required
def alternar_status_dispositivo(request, pk):
    if request.method == 'POST':
        disp = get_object_or_404(DispositivoMovel, pk=pk, empresa=request.user.empresa)
        acao = request.POST.get('acao')

        if acao == 'BLOQUEAR':
            disp.status_autorizacao = DispositivoMovel.StatusAutorizacao.BLOQUEADO
        elif acao == 'AUTORIZAR':
            disp.status_autorizacao = DispositivoMovel.StatusAutorizacao.AUTORIZADO
        elif disp.status_autorizacao == DispositivoMovel.StatusAutorizacao.AUTORIZADO:
            disp.status_autorizacao = DispositivoMovel.StatusAutorizacao.BLOQUEADO
        else:
            disp.status_autorizacao = DispositivoMovel.StatusAutorizacao.AUTORIZADO

        disp.save(update_fields=['status_autorizacao'])
        messages.info(
            request,
            f"Dispositivo '{disp.modelo or disp.uuid_dispositivo}' agora está {disp.status_autorizacao}.",
        )
    return redirect('dispositivo_list')
