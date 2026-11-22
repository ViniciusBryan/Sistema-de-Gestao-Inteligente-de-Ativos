from decimal import Decimal
from rest_framework import serializers

from ativos.models import ClasseAtivo
from empresas.models import TipoOperador
from inventarios.models import Inventario, ItemInventario
from regras.models import RegraOperacionalMobile


class ItemInventarioSyncSerializer(serializers.ModelSerializer):
    """Serializer para itens de inventário enviados pelo aplicativo móvel."""

    classe_codigo = serializers.CharField(write_only=True)
    id = serializers.UUIDField(required=False)

    class Meta:
        model = ItemInventario
        fields = [
            'id',
            'classe_codigo',
            'qtd_detectada_ia',
            'qtd_confirmada_humano',
            'justificativa',
            'detections_json',
            'foto',
        ]


class InventarioSyncSerializer(serializers.ModelSerializer):
    """Valida e prepara o lote offline-first segundo as regras operacionais v1.0."""

    itens = ItemInventarioSyncSerializer(many=True)
    id = serializers.UUIDField()

    class Meta:
        model = Inventario
        fields = ['id', 'data_hora_inicio', 'data_hora_fim', 'lat_long', 'itens']

    def _calcular_divergencia_pct(self, ia, humano):
        if ia == 0:
            return Decimal('0.0') if humano == 0 else Decimal('100.0')
        return (Decimal(abs(humano - ia)) / Decimal(ia)) * Decimal('100.0')

    def validate(self, attrs):
        request = self.context.get('request')
        usuario = request.user if request else None

        if not usuario or not usuario.is_authenticated:
            raise serializers.ValidationError("Usuário não autenticado.")

        empresa = usuario.empresa
        if not empresa:
            raise serializers.ValidationError("Usuário não está vinculado a nenhuma Empresa.")

        tipo_alvo = (
            usuario.tipo_operador
            if usuario.tipo_operador in [TipoOperador.FUNCIONARIO, TipoOperador.TERCEIRIZADO]
            else TipoOperador.FUNCIONARIO
        )
        regra = RegraOperacionalMobile.objects.filter(
            empresa=empresa,
            tipo_operador_alvo=tipo_alvo,
        ).first()

        tolerancia_ia = regra.tolerancia_erro_ia_pct if regra else Decimal('10.0')
        limite_edicao = regra.limite_edicao_manual_pct if regra else Decimal('20.0')
        exige_justificativa = regra.exige_justificativa if regra else True

        itens_data = attrs.get('itens', [])
        if not itens_data:
            raise serializers.ValidationError("O lote de inventário deve conter ao menos um item.")

        for item in itens_data:
            codigo = item.get('classe_codigo')
            classe_ativo = (
                ClasseAtivo.objects.filter(empresa=empresa, codigo_yolo__iexact=codigo).first()
                or ClasseAtivo.objects.filter(empresa=empresa, nome_classe__iexact=codigo).first()
            )
            if not classe_ativo:
                raise serializers.ValidationError(
                    f"Classe de ativo '{codigo}' não encontrada no catálogo da empresa {empresa.razao_social}."
                )

            item['classe_ativo_instancia'] = classe_ativo
            divergencia_pct = self._calcular_divergencia_pct(
                item.get('qtd_detectada_ia', 0),
                item.get('qtd_confirmada_humano', 0),
            )
            justificativa = (item.get('justificativa') or '').strip()

            if divergencia_pct > tolerancia_ia and exige_justificativa and not justificativa:
                raise serializers.ValidationError({
                    'justificativa': (
                        f"Justificativa obrigatória para '{classe_ativo.nome_classe}'. "
                        f"O ajuste manual foi de {divergencia_pct:.1f}% (margem para auditoria: {tolerancia_ia}%)."
                    )
                })

            if divergencia_pct > limite_edicao:
                raise serializers.ValidationError({
                    'limite_operacional': (
                        f"A alteração manual de {divergencia_pct:.1f}% em '{classe_ativo.nome_classe}' "
                        f"excede o limite de {limite_edicao}% configurado para operadores do tipo {usuario.get_tipo_operador_display()}."
                    )
                })

        attrs['_regra_aplicada'] = regra
        attrs['_empresa'] = empresa
        return attrs
