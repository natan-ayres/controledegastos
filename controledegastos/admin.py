from django.contrib import admin
from controledegastos.models import Lugares, Categorias, Despesas, Orcamentos, Previstas, CartoesCredito, DespesasCredito

@admin.register(Orcamentos)
class OrcamentosAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'valor', 'data')
    search_fields = ('nome',)

@admin.register(Lugares)
class LugaresAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'endereco')
    search_fields = ('nome', 'endereco')

@admin.register(Categorias)
class CategoriasAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome')
    search_fields = ('nome',)

@admin.register(Despesas)
class DespesasAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'valor', 'data')
    search_fields = ('nome',)

@admin.register(Previstas)
class PrevistasAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'valor', 'data_prevista', 'pagamento_automatico')
    search_fields = ('nome',)

@admin.register(CartoesCredito)
class CartoesCreditoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'limite_credito', 'dia_fechamento','dia_vencimento', 'ultimos_4_digitos', 'cor')
    search_fields = ('nome',)

@admin.register(DespesasCredito)
class DespesasCreditoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'valor_total', 'data', 'cartao')
    search_fields = ('nome',)
