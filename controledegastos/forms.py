from controledegastos.models import Despesas, Lugares, Categorias, Orcamentos, Previstas, CartoesCredito, DespesasCredito
from django import forms
import re
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            "class": "input",
            "placeholder": "Digite sua senha"
        })
    )

    confirm_password = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={
            "class": "input",
            "placeholder": "Repita sua senha"
        })
    )

    class Meta:
        model = User
        fields = ["username", "email", "password"]
        labels = {
            "username": "Usuário",
            "email": "E-mail",
        }
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Digite seu nome de usuário"
            }),
            "email": forms.EmailInput(attrs={
                "class": "input",
                "placeholder": "Digite seu e-mail"
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este e-mail já está em uso.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise ValidationError("As senhas não coincidem.")

        return cleaned_data

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuário",
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Digite seu usuário"
        })
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            "class": "input",
            "placeholder": "Digite sua senha"
        })
    )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                "Sua conta ainda não foi verificada. Verifique seu e-mail.",
                code="inactive",
            )

        

class EditarUsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este e-mail já está em uso por outro usuário.")
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este nome de usuário já está em uso por outro usuário.")
        return username

class OrcamentosForm(forms.ModelForm):
    class Meta:
        model = Orcamentos
        fields = ['nome', 'valor', 'descricao', 'data']
        labels = {
            'nome': 'Nome do Orçamento',
            'valor': 'Valor',
            'descricao': 'Descrição',
            'data': 'Data',
        }
        
    def clean_valor(self):
        valor = self.cleaned_data.get('valor')
        if valor is not None and valor < 0:
            raise ValidationError("O valor do orçamento não pode ser negativo.")
        return valor
    
    def clean_data(self):
        data = self.cleaned_data.get('data')
        if data is not None and data > forms.fields.datetime.date.today():
            raise ValidationError("A data do orçamento não pode ser no futuro.")
        return data

class LugaresForm(forms.ModelForm):
    class Meta:
        model = Lugares
        fields = ['nome', 'endereco']
        labels = {
            'nome': 'Nome do Lugar',
            'endereco': 'Endereço',
        }

class CategoriasForm(forms.ModelForm):
    class Meta:
        model = Categorias
        fields = ['nome', 'descricao']
        labels = {
            'nome': 'Nome da Categoria',
            'descricao': 'Descrição',
        }

class DespesasForm(forms.ModelForm):
    class Meta:
        model = Despesas
        fields = ['nome', 'descricao', 'valor', 'data', 'lugar', 'categoria']
        labels = {
            'nome': 'Nome da Despesa',
            'descricao': 'Descrição',
            'valor': 'Valor',
            'data': 'Data',
            'lugar': 'Lugar',
            'categoria': 'Categoria',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        self.fields['lugar'].queryset = Lugares.objects.filter(usuario=user)
        self.fields['categoria'].queryset = Categorias.objects.filter(usuario=user)
        
    def clean_valor(self):
        valor = self.cleaned_data.get('valor')
        if valor is not None and valor < 0:
            raise ValidationError("O valor da despesa não pode ser negativo.")
        return valor
    
    def clean_data(self):
        data = self.cleaned_data.get('data')
        if data is not None and data > forms.fields.datetime.date.today():
            raise ValidationError("A data da despesa não pode ser no futuro.")
        return data
    
class PrevistasForm(forms.ModelForm):
    class Meta:
        model = Previstas
        fields = ['nome', 'descricao', 'valor', 'data_prevista', 'pagamento_automatico', 'lugar', 'categoria']
        labels = {
            'nome': 'Nome da Despesa Prevista',
            'descricao': 'Descrição',
            'valor': 'Valor',
            'data_prevista': 'Data Prevista',
            'pagamento_automatico': 'Adicionar ao dashboard após data de pagamento?',
            'lugar': 'Lugar',
            'categoria': 'Categoria',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        self.fields['lugar'].queryset = Lugares.objects.filter(usuario=user)
        self.fields['categoria'].queryset = Categorias.objects.filter(usuario=user)

    def clean_valor(self):
        valor = self.cleaned_data.get('valor')
        if valor is not None and valor < 0:
            raise ValidationError("O valor não pode ser negativo.")
        return valor
    
    def clean_data_prevista(self):
        data_prevista = self.cleaned_data.get('data_prevista')
        if data_prevista is not None and data_prevista < forms.fields.datetime.date.today():
            raise ValidationError("A data prevista não pode ser no passado.")
        return data_prevista
    
class CartoesCreditoForm(forms.ModelForm):
    class Meta:
        model = CartoesCredito
        fields = ['nome', 'limite_credito', 'dia_fechamento','dia_vencimento', 'ultimos_4_digitos','cor']
        labels = {
            'nome': 'Nome do Cartão de Crédito',
            'limite_credito': 'Limite de Crédito',
            'dia_fechamento': 'Dia de Fechamento da Fatura',
            'dia_vencimento': 'Dia de Vencimento da Fatura',
            'ultimos_4_digitos': 'Últimos 4 Dígitos',
            'cor': 'Cor do Cartão',
        }

    def clean_dia_fechamento(self):
        dia_fechamento = self.cleaned_data.get('dia_fechamento')
        if dia_fechamento is not None and (dia_fechamento < 1 or dia_fechamento > 31):
            raise ValidationError("O dia de fechamento deve estar entre 1 e 31.")
        return dia_fechamento
    
    def clean_limite_credito(self):
        limite_credito = self.cleaned_data.get('limite_credito')
        if limite_credito is not None and limite_credito < 0:
            raise ValidationError("O limite de crédito não pode ser negativo.")
        return limite_credito
    
    def clean_dia_vencimento(self):
        dia_vencimento = self.cleaned_data.get('dia_vencimento')
        if dia_vencimento is not None and (dia_vencimento < 1 or dia_vencimento > 31):
            raise ValidationError("O dia de vencimento deve estar entre 1 e 31.")
        return dia_vencimento
    
    def clean_ultimos_4_digitos(self):
        ultimos_4_digitos = self.cleaned_data.get('ultimos_4_digitos')
        if ultimos_4_digitos and not re.match(r'^\d{4}$', ultimos_4_digitos):
            raise ValidationError("Os últimos 4 dígitos devem conter exatamente 4 números.")
        return ultimos_4_digitos
    
class DespesasCreditoForm(forms.ModelForm):
    class Meta:
        model = DespesasCredito
        fields = ['cartao', 'nome', 'data', 'valor_total', 'descricao', 'parcelas_totais', 'lugar', 'categoria']
        labels = {
            'cartao': 'Cartão de Crédito',
            'nome': 'Nome da Despesa no Crédito',
            'data': 'Data',
            'valor_total': 'Valor Total',
            'descricao': 'Descrição',
            'parcelas_totais': 'Parcelas Totais',
            'lugar': 'Lugar',
            'categoria': 'Categoria',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        self.fields['cartao'].queryset = CartoesCredito.objects.filter(usuario=user)
        self.fields['lugar'].queryset = Lugares.objects.filter(usuario=user)
        self.fields['categoria'].queryset = Categorias.objects.filter(usuario=user)
        
    def clean_valor_total(self):
        valor_total = self.cleaned_data.get('valor_total')
        if valor_total is not None and valor_total < 0:
            raise ValidationError("O valor total da despesa não pode ser negativo.")
        return valor_total
    
    def clean_data(self):
        data = self.cleaned_data.get('data')
        if data is not None and data > forms.fields.datetime.date.today():
            raise ValidationError("A data da despesa não pode ser no futuro.")
        return data
    
    def clean_parcelas_totais(self):
        parcelas_totais = self.cleaned_data.get('parcelas_totais')
        if parcelas_totais is not None and parcelas_totais < 1:
            raise ValidationError("O número de parcelas restantes deve ser pelo menos 1.")
        return parcelas_totais
    
    def clean_cartao(self):
        cartao = self.cleaned_data.get('cartao')
        if cartao is None:
            raise ValidationError("O cartão de crédito deve ser selecionado.")
        return cartao
    
    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if not nome:
            raise ValidationError("O nome da despesa no crédito não pode estar vazio.")
        return nome 
    
    def clean_utilizado_limite(self):
        if self.cleaned_data.get('cartao') and self.cleaned_data.get('valor_total'):
            limite = self.cleaned_data['cartao'].limite_credito
            utilizado = self.cleaned_data['cartao'].utilizado
            valor_total = self.cleaned_data.get('valor_total', 0)
            if valor_total > limite - utilizado:
                raise ValidationError("O valor total da despesa excede o limite do cartão de crédito.")
        return True

    def save(self, commit=True):
        despesa_credito = super().save(commit=False)
        cartao = despesa_credito.cartao
        if commit:
            cartao.utilizado += despesa_credito.valor_total
            cartao.save()
        return despesa_credito

    

    
    


