from django.db import models
import datetime

class Orcamentos(models.Model):
    nome = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    descricao = models.CharField(max_length=255, null=True, blank=True)
    data = models.DateField(default=datetime.date.today)
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True)
    
    def verbose_name(self):
        return "Receita"
    
    def verbose_name_plural(self):
        return "Receitas"

    def __str__(self):
        return self.nome

class Lugares(models.Model):
    nome = models.CharField(max_length=100)
    lugar_pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sublugares')
    endereco = models.CharField(max_length=255, null=True, blank=True)
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.lugar_pai} - {self.nome}" if self.lugar_pai else self.nome
    
class Categorias(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, null=True, blank=True)
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True)
    categoria_pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategorias')
    meta_valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.categoria_pai} - {self.nome}" if self.categoria_pai else self.nome

class Despesas(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    data = models.DateField(default=datetime.date.today)
    lugar = models.ForeignKey(Lugares, on_delete=models.CASCADE, null=True, blank=True)
    categoria = models.ForeignKey(Categorias, on_delete=models.CASCADE, null=True, blank=True)
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.nome} - {self.valor}({self.data})"

class Previstas(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    data_prevista = models.DateField(default=datetime.date.today)
    pagamento_automatico = models.BooleanField(default=False)
    lugar = models.ForeignKey(Lugares, on_delete=models.CASCADE, null=True, blank=True)
    categoria = models.ForeignKey(Categorias, on_delete=models.CASCADE, null=True, blank=True)
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.nome} - {self.valor}({self.data_prevista})"
    
class CartoesCredito(models.Model):
    CORES = [
        ("#8B5CF6", "Roxo"),      # purple-500
        ("#FACC15", "Amarelo"),   # yellow-400
        ("#EF4444", "Vermelho"),  # red-500
        ("#000000", "Preto"),     # black
        ("#F97316", "Laranja"),   # orange-500
        ("#C0C0C0", "Prata"),     # silver
        ("#22C55E", "Verde"),     # green-500
    ]

    nome = models.CharField(max_length=100)
    limite_credito = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    dia_fechamento = models.IntegerField(null=False, blank=False)
    dia_vencimento = models.IntegerField(null=False, blank=False)
    ultimos_4_digitos = models.CharField(max_length=4, null=True, blank=True, default='****')
    cor = models.CharField(
        max_length=7,
        choices=CORES,
        default="#FFFFFF",
    )
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"Crédito: {self.nome} ({self.ultimos_4_digitos})"
    
class DespesasCredito(models.Model):
    cartao = models.ForeignKey(CartoesCredito, on_delete=models.CASCADE, null=True)
    nome = models.CharField(max_length=100)
    data = models.DateField(default=datetime.date.today)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False)
    descricao = models.CharField(max_length=255, null=True, blank=True)
    parcelas_totais = models.IntegerField(default=1)
    parcelas_restantes = models.IntegerField()
    lugar = models.ForeignKey(Lugares, on_delete=models.CASCADE, null=True, blank=True)
    categoria = models.ForeignKey(Categorias, on_delete=models.CASCADE, null=True, blank=True)
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.cartao.nome}: {self.nome}({self.valor_total})"
    
    def create_parcelas_restantes(self):
        if not self.pk:
            self.parcelas_restantes = self.parcelas_totais


