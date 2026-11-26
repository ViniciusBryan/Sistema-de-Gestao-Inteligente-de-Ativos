from decimal import Decimal
from django.db.models import Q
from rest_framework import serializers

from ativos.models import ClasseAtivo
from inventarios.models import Inventario, ItemInventario
from regras.models import RegraOperacionalMobile

# Mapeamento temporário 
ALIASES_CODIGO_YOLO_DEV = {
    'table_joint': ('mesa_bistro', 'Mesa Bistrô'),
}


class RegraOperacionalMobileSerializer(serializers.ModelSerializer):
    """Serializa a regra operacional vigente para o contrato JSON do App Mobile."""

    tolerancia_erro_ia_pct = serializers.FloatField()
    limite_edicao_manual_pct = serializers.FloatField()
    bloquear_excesso_edicao = serializers.SerializerMethodField()
    horario_inicio = serializers.TimeField(format='%H:%M', allow_null=True)
    horario_fim = serializers.TimeField(format='%H:%M', allow_null=True)

    class Meta:
        model = RegraOperacionalMobile
        fields = [
            'tipo_operador_alvo',
            'tolerancia_erro_ia_pct',
            'limite_edicao_manual_pct',
            'exige_justificativa',
            'bloquear_excesso_edicao',
            'horario_inicio',
            'horario_fim',
            'versao',
        ]

    def get_bloquear_excesso_edicao(self, obj) -> bool:
        return True


def serializar_regra_mobile(usuario, regra=None, fallback_padrao=False):
    """Serializa a regra operacional ou retorna o payload padrão quando solicitado."""
    if regra is None:
        if not fallback_padrao:
            return None
        regra = RegraOperacionalMobile(
            tipo_operador_alvo=RegraOperacionalMobile.resolver_tipo_alvo(usuario),
        )
    return RegraOperacionalMobileSerializer(regra).data


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
    """Valida e prepara o lote offline-first"""

    itens = ItemInventarioSyncSerializer(many=True)
    id = serializers.UUIDField()

    class Meta:
        model = Inventario
        fields = ['id', 'data_hora_inicio', 'data_hora_fim', 'lat_long', 'itens']

    def _calcular_divergencia_pct(self, ia, humano):
        if ia == 0:
            return Decimal('0.0') if humano == 0 else Decimal('100.0')
        return (Decimal(abs(humano - ia)) / Decimal(ia)) * Decimal('100.0')

    def _resolver_classe_ativo(self, empresa, codigo_raw):
        """Localiza a ClasseAtivo no catálogo da empresa, aplicando aliases de desenvolvimento."""
        codigo_limpo = (codigo_raw or '').strip()
        codigo_norm = codigo_limpo.lower().replace('-', '_').replace(' ', '_')

        classe_ativo = (
            ClasseAtivo.objects.filter(empresa=empresa)
            .filter(
                Q(codigo_yolo__iexact=codigo_norm)
                | Q(codigo_yolo__iexact=codigo_limpo)
                | Q(nome_classe__iexact=codigo_limpo)
            )
            .first()
        )
        if not classe_ativo and codigo_norm in ALIASES_CODIGO_YOLO_DEV:
            codigo_alias, nome_alias = ALIASES_CODIGO_YOLO_DEV[codigo_norm]
            classe_ativo = (
                ClasseAtivo.objects.filter(empresa=empresa)
                .filter(Q(codigo_yolo__iexact=codigo_alias) | Q(nome_classe__iexact=nome_alias))
                .first()
            )
        return classe_ativo

    def _validar_item(self, item, empresa, usuario, tolerancia_ia, limite_edicao, exige_justificativa):
        """Valida classe de ativo, obrigatoriedade de justificativa e limite de edição de um item."""
        codigo_raw = (item.get('classe_codigo') or '').strip()
        classe_ativo = self._resolver_classe_ativo(empresa, codigo_raw)
        if not classe_ativo:
            raise serializers.ValidationError(
                f"Classe de ativo '{codigo_raw}' não encontrada no catálogo da empresa {empresa.razao_social}."
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

    def validate(self, attrs):
        request = self.context.get('request')
        usuario = request.user if request else None

        if not usuario or not usuario.is_authenticated:
            raise serializers.ValidationError("Usuário não autenticado.")

        empresa = usuario.empresa
        if not empresa:
            raise serializers.ValidationError("Usuário não está vinculado a nenhuma Empresa.")

        itens_data = attrs.get('itens', [])
        if not itens_data:
            raise serializers.ValidationError("O lote de inventário deve conter ao menos um item.")

        regra = RegraOperacionalMobile.para_usuario(usuario)
        tolerancia_ia = regra.tolerancia_erro_ia_pct if regra else RegraOperacionalMobile.DEFAULT_TOLERANCIA_ERRO_IA_PCT
        limite_edicao = regra.limite_edicao_manual_pct if regra else RegraOperacionalMobile.DEFAULT_LIMITE_EDICAO_MANUAL_PCT
        exige_justificativa = regra.exige_justificativa if regra else True

        for item in itens_data:
            self._validar_item(item, empresa, usuario, tolerancia_ia, limite_edicao, exige_justificativa)

        attrs['_regra_aplicada'] = regra
        attrs['_empresa'] = empresa
        return attrs
