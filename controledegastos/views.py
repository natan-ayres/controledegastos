from django.core.paginator import Paginator
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from controledegastos.models import Lugares, Categorias, Despesas, Orcamentos, Previstas, CartoesCredito, DespesasCredito
from .forms import LugaresForm, CategoriasForm, DespesasForm, OrcamentosForm, EditarUsuarioForm, PrevistasForm, CartoesCreditoForm, DespesasCreditoForm, RegisterForm, LoginForm
from django.contrib import auth
import datetime
from datetime import date, timedelta
from calendar import monthrange
from django.db.models import Sum, F, Q
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model
from local_settings import API_KEY, EMAIL_OWNER
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.core.exceptions import ValidationError
from django.core.cache import cache
from decimal import Decimal
from collections import defaultdict


def mes_anterior(data_ref):
    ano = data_ref.year
    mes = data_ref.month - 1
    if mes == 0:
        mes = 12
        ano -= 1
    # garante dia válido no mês anterior
    ultimo = monthrange(ano, mes)[1]
    dia = min(data_ref.day, ultimo)
    return date(ano, mes, dia)

def mes_posterior(data_ref):
    ano = data_ref.year
    mes = data_ref.month + 1
    if mes == 13:
        mes = 1
        ano += 1
    # garante dia válido no mês posterior
    ultimo = monthrange(ano, mes)[1]
    dia = min(data_ref.day, ultimo)
    return date(ano, mes, dia)

def ative_seu_email(request, uid):
    User = get_user_model()

    # tentar recuperar o usuário
    try:
        uid_decoded = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=uid_decoded)
    except Exception:
        user = None

    if not user:
        return redirect('controledegastos:login')

    cooldown_key = f"reativar_email_cooldown_{request.user.id}"
    if request.method == 'POST':
        if cache.get(cooldown_key):
            messages.error(request, "Você já reenviou o e-mail recentemente. Aguarde 5 minutos.")
        enviar_email(user, uid)
        cache.set(cooldown_key, True, 300)  

    context = {
        'site_title': 'Ative seu email - ',
        'username': user.username,
        'email': user.email,
        'uid': uid,
    }

    return render(request, 'ative_seu_email.html', context)

def enviar_email(user, uid):
    token = default_token_generator.make_token(user)
    link_ativacao = f"http://construtora-gastos.onrender.com/ativar/{uid}/{token}/"
    assunto = "Ative sua conta"
    mensagem = f"""
        <!DOCTYPE html>
        <html lang="pt-BR" style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
        <body style="max-width: 600px; margin: auto; background: #ffffff; padding: 30px; border-radius: 8px; border: 1px solid #e5e5e5;">
            
            <h2 style="color: #333; text-align: center;">Ativação de Conta</h2>

            <p style="font-size: 16px; color: #555;">
                Olá <strong>{user.username}</strong>,
            </p>

            <p style="font-size: 16px; color: #555;">
                Obrigado por criar sua conta em nossa plataforma. Para começar a utilizá-la, precisamos confirmar seu endereço de e-mail.
            </p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{link_ativacao}" 
                style="background-color: #4CAF50; color: white; padding: 14px 24px; text-decoration: none; border-radius: 6px; font-size: 16px;">
                    Ativar Conta
                </a>
            </div>

            <p style="font-size: 16px; color: #555;">Ou, se preferir, copie e cole o link abaixo no seu navegador:</p>

            <p style="font-size: 14px; word-break: break-all; color: #777;">
                {link_ativacao}
            </p>

            <hr style="margin: 30px 0;">

            <p style="font-size: 14px; color: #999;">
                Se você não realizou este cadastro, basta ignorar este e-mail.
            </p>

            <p style="font-size: 14px; color: #999;">
                Atenciosamente,<br>
                Equipe de Suporte
            </p>
        </body>
        </html>
        """

    message = Mail(
        from_email= EMAIL_OWNER,
        to_emails= user.email,
        subject=assunto,
        html_content=mensagem)
    sg = SendGridAPIClient(API_KEY)
    sg.send(message)


def ativar_conta(request, uidb64, token):
    User = get_user_model()

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect('controledegastos:login')

    return redirect('controledegastos:login')

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.set_password(form.cleaned_data['password'])
            user.save()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            enviar_email(user, uid)
            return redirect('controledegastos:ative_email', uid)

    else:
        form = RegisterForm()

    return render(request, 'login_register.html', {
        'is_register': True,
        'form': form,
        'form_name': 'Registrar',
        'form_action': '',  # mantém ação padrão
    })

def login(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)

        try:
            if form.is_valid():
                user = form.get_user()
                auth.login(request, user)
                return redirect('controledegastos:index')

        except ValidationError as e:
            # Verifica se o erro é o de conta inativa
            if "inactive" in e.error_list[0].code:
                # Recupera o usuário do formulário
                username = form.cleaned_data.get("username")
                # Ou o nome do campo que você usa no LoginForm
                
                # Busca o usuário
                from django.contrib.auth import get_user_model
                User = get_user_model()

                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    user = None

                if user:
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    return redirect('controledegastos:ative_email', uid=uid)

            # Se não for erro de conta inativa, apenas exibe o erro no form
            form.add_error(None, e)

    else:
        form = LoginForm()

    return render(
        request,
        'login_register.html',
        {
            'is_register': False,
            'form': form,
            'form_name': 'Login',
            'form_action': reverse('controledegastos:login'),
        }
    )

def editperfil(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')

    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('controledegastos:perfil')
    else:
        form = EditarUsuarioForm(instance=request.user)

    context = {
        'form': form,
        'form_name': 'Editar Perfil',
        'username': request.user.username,
        'form_action': reverse('controledegastos:editperfil'),
        'site_title': 'Editar Perfil - '
    }

    return render(
        request,
        'form.html',
        context
    )

def perfil(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    

    context = {
        'logado': True,
        'username': request.user.username,
        'user': request.user,
        'site_title': 'Perfil - '
    }

    return render(
        request,
        'userinfo.html',
        context
    )

def logout(request):
    auth.logout(request)
    return redirect('controledegastos:login')

def indexmeses(request, mes, ano):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    

    ano_atual = ano
    mes_atual = mes

    MESES = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    mes_nome = MESES[mes_atual - 1]

    # 🔹 Consultas leves para filtros
    categorias = Categorias.objects.filter(usuario=request.user).values("id", "nome")
    lugares = Lugares.objects.filter(usuario=request.user).values("id", "nome")

    # 🔹 Filtra despesas do mês
    despesas = Despesas.objects.filter(
        usuario=request.user,
        data__year=ano_atual,
        data__month=mes_atual
    ).order_by('-data')

    # ---------- FILTROS GET ----------
    nome = request.GET.get("nome")
    categoria = request.GET.get("categoria")
    lugar = request.GET.get("lugar")
    dia = request.GET.get("dia")
    valor_min = request.GET.get("valor_min")

    if nome:
        despesas = despesas.filter(nome__icontains=nome)

    if categoria:
        despesas = despesas.filter(categoria=categoria)

    if lugar:
        despesas = despesas.filter(lugar=lugar)

    if dia:
        despesas = despesas.filter(data__day=dia)

    if valor_min:
        despesas = despesas.filter(valor__gte=valor_min)

    # ---------- CÁLCULOS OTIMIZADOS ----------
    total_gasto = sum(d.valor for d in despesas)

    # 🔸 Filtra orçamentos do mês de forma leve
    orcamentos_mes = Orcamentos.objects.filter(
        usuario=request.user,
        data__year=ano_atual,
        data__month=mes_atual
    ).values("valor")

    total_recebido = sum(o["valor"] for o in orcamentos_mes)

    # 🔸 Calcula saldo acumulado até o fim daquele mês
    next_month = (mes_atual % 12) + 1
    next_year = ano_atual + (mes_atual // 12)
    last_day = datetime.date(next_year, next_month, 1) - datetime.timedelta(days=1)

    todas_as_despesas = Despesas.objects.filter(
        usuario=request.user,
        data__lte=last_day
    ).values("valor")

    todos_os_orcamentos = Orcamentos.objects.filter(
        usuario=request.user,
        data__lte=last_day
    ).values("valor")

    total_pago = sum(d["valor"] for d in todas_as_despesas)
    total_orcado = sum(o["valor"] for o in todos_os_orcamentos)
    saldo_atual = total_orcado - total_pago

    # ---------- PAGINAÇÃO ----------
    paginator = Paginator(despesas, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # ---------- ANOS VÁLIDOS (mesma lógica da index) ----------
    year_month_qs_despesas = Despesas.objects.filter(usuario=request.user) \
        .values_list('data__year', 'data__month') \
        .distinct()

    year_month_qs_orcamentos = Orcamentos.objects.filter(usuario=request.user) \
        .values_list('data__year', 'data__month') \
        .distinct()

    anos_map = {}

    for ano_item, mes_item in year_month_qs_despesas:
        anos_map.setdefault(ano_item, set()).add(mes_item)

    for ano_item, mes_item in year_month_qs_orcamentos:
        anos_map.setdefault(ano_item, set()).add(mes_item)

    anos_validos = [
        {ano_item: sorted(list(meses))}
        for ano_item, meses in sorted(anos_map.items(), reverse=True)
    ]

    # ---------- CONTEXTO ----------
    context = {
        'total_gasto': total_gasto,
        'total_recebido': total_recebido,
        'saldo_atual': saldo_atual,
        'tipo_saldo': 'Final',
        'mes': mes_nome,
        'mes_atual': datetime.date.today().month,
        'ano': ano_atual,
        'numero_mes': mes_atual,
        'logado': True,
        'username': request.user.username,
        'despesas': despesas,
        'categorias': categorias,
        'lugares': lugares,
        'page_obj': page_obj,
        'anos_validos': anos_validos,
        'site_title': 'Despesas - ',
    }

    return render(request, 'index.html', context)


def index(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    

    hoje = datetime.date.today()
    ano_atual = hoje.year
    mes_atual = hoje.month

    MESES = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    mes_nome = MESES[mes_atual - 1]

    categorias = Categorias.objects.filter(usuario=request.user).values("id", "nome")
    lugares = Lugares.objects.filter(usuario=request.user).values("id", "nome")

    # Filtrar despesas do mês
    despesas = Despesas.objects.filter(
        usuario=request.user,
        data__year=ano_atual,
        data__month=mes_atual
    ).order_by('-data')

    total_gasto = sum(d.valor for d in despesas)

    nome = request.GET.get("nome")
    categoria = request.GET.get("categoria")
    lugar = request.GET.get("lugar")
    dia = request.GET.get("dia")
    valor_min = request.GET.get("valor_min")

    if nome:
        despesas = despesas.filter(nome__icontains=nome)

    if categoria:
        despesas = despesas.filter(categoria=categoria)

    if lugar:
        despesas = despesas.filter(lugar=lugar)

    if dia:
        despesas = despesas.filter(data__day=dia)

    if valor_min:
        despesas = despesas.filter(valor__gte=valor_min)

    todas_as_despesas = Despesas.objects.filter(usuario=request.user).values("valor")
    todos_os_orcamentos = Orcamentos.objects.filter(usuario=request.user).values("valor")
    total_pago = sum(d["valor"] for d in todas_as_despesas)
    total_orcado = sum(o["valor"] for o in todos_os_orcamentos)
    saldo_atual = total_orcado - total_pago

    fatura_nao_paga = DespesasCredito.objects.filter(
            usuario=request.user,
            parcelas_restantes__gt=0
        ).aggregate(
            total=Sum(F('valor_total') / F('parcelas_totais'))
        ) ['total'] or 0

    # Filtrar orçamentos do mês
    orcamentos_mes = Orcamentos.objects.filter(
        usuario=request.user,
        data__year=ano_atual,
        data__month=mes_atual
    ).values("valor")

    total_recebido = sum(o["valor"] for o in orcamentos_mes)

    paginator = Paginator(despesas, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        'total_gasto': total_gasto,
        'total_recebido': total_recebido,
        'saldo_atual': saldo_atual,
        'tipo_saldo': '',
        'mes': mes_nome,
        'mes_atual': datetime.date.today().month,
        'ano': ano_atual,
        'numero_mes': mes_atual,
        'logado': True,
        'username': request.user.username,
        'despesas': despesas,
        'categorias': categorias,
        'lugares': lugares,
        'page_obj': page_obj,
        'site_title': 'Despesas - ',
        'fatura_nao_paga': fatura_nao_paga
    }
    # construir lista de anos válidos a partir de despesas E orçamentos
    year_month_qs_despesas = Despesas.objects.filter(usuario=request.user) \
        .values_list('data__year', 'data__month') \
        .distinct()

    year_month_qs_orcamentos = Orcamentos.objects.filter(usuario=request.user) \
        .values_list('data__year', 'data__month') \
        .distinct()

    anos_map = {}
    # adicionar meses das despesas
    for ano, mes in year_month_qs_despesas:
        anos_map.setdefault(ano, set()).add(mes)
    # adicionar meses dos orçamentos (une os conjuntos)
    for ano, mes in year_month_qs_orcamentos:
        anos_map.setdefault(ano, set()).add(mes)

    # transformar em lista de dicionários, anos ordenados decrescentemente,
    # meses ordenados crescentemente
    anos_validos = [
        {ano: sorted(list(meses))}
        for ano, meses in sorted(anos_map.items(), reverse=True)
    ]

    context['anos_validos'] = anos_validos

    return render(request, 'index.html', context)

def orcamentos(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    

    # === LISTA BASE ===
    orcamentos = Orcamentos.objects.filter(
        usuario=request.user
    ).order_by('-data')

    # === FILTROS ===
    nome = request.GET.get("nome")
    descricao = request.GET.get("descricao")
    dia = request.GET.get("dia")
    valor_min = request.GET.get("valor_min")
    mes = request.GET.get("mes")
    ano = request.GET.get("ano")

    if nome:
        orcamentos = orcamentos.filter(nome__icontains=nome)

    if descricao:
        orcamentos = orcamentos.filter(descricao__icontains=descricao)

    if dia:
        orcamentos = orcamentos.filter(data__day=dia)

    if valor_min:
        orcamentos = orcamentos.filter(valor__gte=valor_min)

    if mes:
        orcamentos = orcamentos.filter(data__month=mes)

    if ano:
        orcamentos = orcamentos.filter(data__year=ano)

    # === PAGINAÇÃO ===
    paginator = Paginator(orcamentos, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # === MESES DISPONÍVEIS ===
    year_month_qs = Orcamentos.objects.filter(usuario=request.user) \
        .values_list('data__year', 'data__month') \
        .distinct()

    anos_map = {}
    for ano_found, mes_found in year_month_qs:
        anos_map.setdefault(ano_found, set()).add(mes_found)

    anos_validos = [
        {ano_found: sorted(list(meses))}
        for ano_found, meses in sorted(anos_map.items(), reverse=True)
    ]

    context = {
        "orcamentos": orcamentos,
        "page_obj": page_obj,
        "anos_validos": anos_validos,
        "logado": True,
        "username": request.user.username,
        "site_title": "Entradas - "
    }

    return render(request, "orcamentos.html", context)

def categorias(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    try:
        hoje = datetime.date.today()

        # apenas categorias raiz (sem categoria pai)
        categorias = Categorias.objects.filter(
            usuario=request.user,
            categoria_pai__isnull=True
        ).order_by('-id')

        # mapa de filhos para somar gastos de toda a árvore
        user_categories = Categorias.objects.filter(usuario=request.user).values('id', 'categoria_pai_id')
        children_map = defaultdict(list)
        for rel in user_categories:
            if rel['categoria_pai_id']:
                children_map[rel['categoria_pai_id']].append(rel['id'])

        # somatórios do mês por categoria (despesas comuns + crédito proporcional)
        totals = defaultdict(Decimal)

        despesas_mes = Despesas.objects.filter(
            usuario=request.user,
            data__year=hoje.year,
            data__month=hoje.month
        ).values('categoria_id').annotate(total=Sum('valor'))
        for row in despesas_mes:
            cat_id = row['categoria_id']
            if cat_id:
                totals[cat_id] += row['total'] or Decimal('0')

        despesas_credito_mes = DespesasCredito.objects.filter(
            usuario=request.user,
            data__year=hoje.year,
            data__month=hoje.month
        ).values('categoria_id').annotate(total=Sum(F('valor_total') / F('parcelas_totais')))
        for row in despesas_credito_mes:
            cat_id = row['categoria_id']
            if cat_id:
                totals[cat_id] += row['total'] or Decimal('0')

        subtree_cache = {}

        def subtree_total(cat_id):
            if cat_id in subtree_cache:
                return subtree_cache[cat_id]
            subtotal = totals.get(cat_id, Decimal('0'))
            for child_id in children_map.get(cat_id, []):
                subtotal += subtree_total(child_id)
            subtree_cache[cat_id] = subtotal
            return subtotal

        for c in categorias:
            valor_mes = subtree_total(c.id)
            c.valor_por_mes = valor_mes
            meta_valor = c.meta_valor or Decimal('0')
            c.meta_valor_calc = meta_valor
            if meta_valor > 0:
                # relação gasto/meta agora retorna apenas uma cor por faixa
                perc = (valor_mes / meta_valor) * Decimal('100')
                if perc < Decimal('80'):
                    c.percentual_meta_cor = 'green'
                elif perc < Decimal('100'):
                    c.percentual_meta_cor = 'yellow'
                else:
                    c.percentual_meta_cor = 'red'
            else:
                c.percentual_meta_cor = 'gray'

        paginator = Paginator(categorias, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            'logado': True,
            'categorias': categorias,
            'username': request.user.username,
            'page_obj': page_obj,
            'site_title': 'Categorias - '
        }

        return render(
            request,
            'categorias.html',
            context
        )
    except AttributeError:
        context = {
            'site_title': 'Despesas - ',
            'username': request.user.username,
        }

        return render(
            request,
            'categorias.html',
            context
        )

def lugares(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        hoje = datetime.date.today()

        lugares = Lugares.objects \
            .order_by('-id') \
            .filter(usuario=request.user, lugar_pai__isnull=True)
        
        # para cada categoria, calcular soma das despesas deste mês e anexar como atributo
        for c in lugares:
            # despesas comuns
            total = Despesas.objects.filter(
                usuario=request.user,
                lugar__exact=c,
                data__year=hoje.year,
                data__month=hoje.month
            ).aggregate(
                total=Sum('valor')
            )['total'] or 0

            # despesas do crédito considerando apenas parcela do mês
            total_credito = DespesasCredito.objects.filter(
                usuario=request.user,
                lugar__exact=c,
                data__year=hoje.year,
                data__month=hoje.month
            ).aggregate(
                total=Sum(F('valor_total') / F('parcelas_totais'))
            )['total'] or 0

            # somando gastos normais + crédito proporcional
            setattr(c, 'valor_por_mes', total + total_credito)


        paginator = Paginator(lugares, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            'logado': True,
            'lugares': lugares,
            'username': request.user.username,
            'page_obj': page_obj,
            'site_title': 'Lugares - '
        }

        return render(
            request,
            'lugares.html',
            context
        )
    except AttributeError:
        context = {
            'site_title': 'Lugares - ',
            'username': request.user.username,
        }

        return render(
            request,
            'lugares.html',
            context
        )
    
def previstas(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        previstas = Previstas.objects \
            .order_by('-id') \
            .filter(usuario=request.user)

        paginator = Paginator(previstas, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            'logado': True,
            'previstas': previstas,
            'username': request.user.username,
            'page_obj': page_obj,
            'site_title': 'Despesas Previstas - ',
        }

        return render(
            request,
            'previstas.html',
            context
        )
    except AttributeError:
        context = {
            'site_title': 'Despesas Previstas - ',
            'username': request.user.username,
        }

        return render(
            request,
            'previstas.html',
            context
        )

def creditos(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        creditos = CartoesCredito.objects.filter(usuario=request.user).order_by('-id')
        hoje = date.today()

        for c in creditos:
            dia_fech = c.dia_fechamento

            # Fechamento deste mês (tratando meses com menos dias)
            try:
                fechamento_candidato = date(hoje.year, hoje.month, dia_fech)
            except ValueError:
                ultimo_dia = monthrange(hoje.year, hoje.month)[1]
                fechamento_candidato = date(hoje.year, hoje.month, ultimo_dia)

            # 📌 Se HOJE JÁ PASSOU o fechamento → a fatura do mês FECHOU
            if hoje > fechamento_candidato:
                # FATURA FECHADA = ciclo do mês anterior até o fechamento deste mês
                fechamento_fechado = fechamento_candidato
                abertura_fechada = mes_anterior(fechamento_fechado)

                fatura_fechada = DespesasCredito.objects.filter(
                    usuario=request.user,
                    cartao=c,
                    data__gt=abertura_fechada,
                    data__lte=fechamento_fechado,
                ).aggregate(
                    total=Sum(F('valor_total') / F('parcelas_totais'))
                )['total'] or 0

                setattr(c, 'fatura_fechada', fatura_fechada)

                # 📌 FATURA ATUAL começa após o fechamento até o próximo fechamento
                abertura_atual = fechamento_candidato
                fechamento_prox = mes_posterior(fechamento_candidato)

                fatura_atual = DespesasCredito.objects.filter(
                    usuario=request.user,
                    cartao=c,
                    data__gt=abertura_atual,
                    data__lte=fechamento_prox,
                ).aggregate(
                    total=Sum(F('valor_total') / F('parcelas_totais'))
                )['total'] or 0

                setattr(c, 'fatura', fatura_atual)

            else:
                # 📌 FECHAMENTO AINDA NÃO CHEGOU — só existe FATURA ATUAL
                fechamento_atual = fechamento_candidato
                abertura_atual = mes_anterior(fechamento_atual)

                fatura_atual = DespesasCredito.objects.filter(
                    usuario=request.user,
                    cartao=c,
                    data__gt=abertura_atual,
                    data__lte=fechamento_atual,
                ).aggregate(
                    total=Sum(F('valor_total') / F('parcelas_totais'))
                )['total'] or 0

                setattr(c, 'fatura', fatura_atual)
                setattr(c, 'fatura_fechada', 0)  # não existe fatura fechada ainda

            # Total gasto geral no cartão
            setattr(c, 'utilizado', DespesasCredito.objects.filter(
                usuario=request.user,
                cartao=c
            ).aggregate(total=Sum('valor_total'))['total'] or 0)

            # Exibição
            setattr(c, 'data_fechamento', fechamento_candidato.strftime('%d/%m'))
            setattr(c, 'data_vencimento', (fechamento_candidato + timedelta(days=(c.dia_vencimento - c.dia_fechamento))).strftime('%d/%m'))

        paginator = Paginator(creditos, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        return render(request, 'creditos.html', {
            'logado': True,
            'creditos': creditos,
            'username': request.user.username,
            'page_obj': page_obj,
            'site_title': 'Cartões de Crédito - '
        })

    except AttributeError:
        return render(request, 'creditos.html', {
            'username': request.user.username,
            'site_title': 'Cartões de Crédito - '
        })


def despesascredito(request, credito_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    

    hoje = date.today()
    ano = int(request.GET.get("ano", hoje.year))
    mes = int(request.GET.get("mes", hoje.month))

    MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
             "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    mes_nome = MESES[mes - 1]


    try: 
        cartao = CartoesCredito.objects.get(id=credito_id, usuario=request.user)
    except CartoesCredito.DoesNotExist:
        return redirect('controledegastos:creditos')

    # ============================
    # LISTAGEM
    # ============================
    despesas_credito = DespesasCredito.objects.filter(
        usuario=request.user,
        cartao=cartao,
        data__year=ano,
        data__month=mes
    ).order_by('-data')

    # 🔥 adicionando valor da parcela em cada item
    for d in despesas_credito:
        parcela = d.valor_total / d.parcelas_totais
        setattr(d, 'valor_parcela', parcela)

    total_do_mes = sum(d.valor_total for d in despesas_credito)

    # ============================
    # MESES DISPONÍVEIS
    # ============================
    year_month_qs = DespesasCredito.objects.filter(
        usuario=request.user,
        cartao=cartao
    ).values_list('data__year', 'data__month').distinct()

    anos_map = {}
    for yr, mn in year_month_qs:
        anos_map.setdefault(yr, set()).add(mn)

    anos_validos = [
        {yr: sorted(list(meses))}
        for yr, meses in sorted(anos_map.items(), reverse=True)
    ]

    # ============================
    # FATURA ATUAL
    # ============================
    dia_fech = cartao.dia_fechamento

    try:
        fechamento_candidato = date(hoje.year, hoje.month, dia_fech)
    except ValueError:
        ultimo_dia = monthrange(hoje.year, hoje.month)[1]
        fechamento_candidato = date(hoje.year, hoje.month, ultimo_dia)

    if hoje <= fechamento_candidato:
        fechamento_atual = fechamento_candidato
        fechamento_anterior = mes_anterior(fechamento_atual)
    else:
        fechamento_anterior = fechamento_candidato
        fechamento_atual = mes_posterior(fechamento_candidato)

    total_fatura_atual = DespesasCredito.objects.filter(
        usuario=request.user,
        cartao=cartao
    ).filter(
        Q(data__gt=fechamento_anterior, data__lte=fechamento_atual) | Q(parcelas_restantes__gt=1)
    ).aggregate(
        total=Sum(F('valor_total') / F('parcelas_totais'))
    )['total'] or 0

    # paginação
    paginator = Paginator(despesas_credito, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'despesas_credito.html', {
        'nome': cartao.nome,
        'logado': True,
        'username': request.user.username,
        'despesas_credito': despesas_credito,
        'page_obj': page_obj,
        'mes_atual': mes == hoje.month and ano == hoje.year,
        'mes': mes_nome,
        'ano': ano,
        'mes_num': mes,
        'anos_validos': anos_validos,
        'total_do_mes': total_do_mes,
        'total_fatura_atual': total_fatura_atual,
        'site_title': f'Despesas de {cartao.nome} - ',
    })
    

def orcamento(request, orcamento_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        single_orcamento = Orcamentos.objects.get(pk=orcamento_id, usuario=request.user)
    except Orcamentos.DoesNotExist:
        return redirect('controledegastos:index')

    site_title = f'{single_orcamento.nome} - {single_orcamento.valor}({single_orcamento.data})'

    context = {
        'logado': True,
        'orcamento': single_orcamento,
        'username': request.user.username,
        'site_title': site_title
    }

    return render(
        request,
        'orcamento.html',
        context
    )

def despesa(request, despesa_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        single_despesa = Despesas.objects.get(pk=despesa_id, usuario=request.user)
    except Despesas.DoesNotExist:
        return redirect('controledegastos:index')

    site_title = f'{single_despesa.nome} - {single_despesa.valor}({single_despesa.data})'

    context = {
        'logado': True,
        'despesa': single_despesa,
        'username': request.user.username,
        'site_title': site_title
    }

    return render(
        request,
        'despesa.html',
        context
    )

def lugar(request, lugar_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        single_lugar = Lugares.objects.get(pk=lugar_id, usuario=request.user)
    except Lugares.DoesNotExist:
        return redirect('controledegastos:index')

    # preparar sublugares e totais do mês atual
    hoje = datetime.date.today()
    lugares_usuario = Lugares.objects.filter(usuario=request.user)
    children_map_lugares = defaultdict(list)
    for lg in lugares_usuario:
        if lg.lugar_pai_id:
            children_map_lugares[lg.lugar_pai_id].append(lg.id)

    totals_lugar_mes = defaultdict(Decimal)
    despesas_mes_lugar = Despesas.objects.filter(
        usuario=request.user,
        data__year=hoje.year,
        data__month=hoje.month
    ).values('lugar_id').annotate(total=Sum('valor'))
    for row in despesas_mes_lugar:
        lid = row['lugar_id']
        if lid:
            totals_lugar_mes[lid] += row['total'] or Decimal('0')

    despesas_credito_mes_lugar = DespesasCredito.objects.filter(
        usuario=request.user,
        data__year=hoje.year,
        data__month=hoje.month
    ).values('lugar_id').annotate(total=Sum(F('valor_total') / F('parcelas_totais')))
    for row in despesas_credito_mes_lugar:
        lid = row['lugar_id']
        if lid:
            totals_lugar_mes[lid] += row['total'] or Decimal('0')

    subtree_cache_lugares = {}

    def subtree_total_lugar(lid):
        if lid in subtree_cache_lugares:
            return subtree_cache_lugares[lid]
        subtotal = totals_lugar_mes.get(lid, Decimal('0'))
        for child_id in children_map_lugares.get(lid, []):
            subtotal += subtree_total_lugar(child_id)
        subtree_cache_lugares[lid] = subtotal
        return subtotal

    sublugares_qs = Lugares.objects.filter(lugar_pai=single_lugar, usuario=request.user).order_by('nome')
    sublugares = []
    for sl in sublugares_qs:
        sl.valor_por_mes = subtree_total_lugar(sl.id)
        sublugares.append(sl)

    site_title = f'Lugar: {single_lugar.nome}'

    year_month_qs_despesas = Despesas.objects.filter(usuario=request.user) \
        .values_list('data__year', 'data__month') \
        .distinct()

    year_month_qs_credito = DespesasCredito.objects.filter(usuario=request.user) \
        .values_list('data__year', 'data__month') \
        .distinct()

    anos_map = {}
    for ano, mes in year_month_qs_despesas:
        anos_map.setdefault(ano, set()).add(mes)

    for ano, mes in year_month_qs_credito:
        anos_map.setdefault(ano, set()).add(mes)

    anos_validos = [
        {ano: sorted(list(meses), reverse=True)}
        for ano, meses in sorted(anos_map.items(), reverse=True)
    ]

    gastos_lugar = {}
    for ano_dict in anos_validos:
        for ano, meses in ano_dict.items():
            for mes in meses:

                # despesas normais
                total_mes = Despesas.objects.filter(
                    usuario=request.user,
                    lugar=single_lugar,
                    data__year=ano,
                    data__month=mes
                ).aggregate(
                    total=Sum('valor')
                )['total'] or 0

                # despesas crédito (somente parcela do mês)
                total_credito_mes = DespesasCredito.objects.filter(
                    usuario=request.user,
                    lugar=single_lugar,
                    data__year=ano,
                    data__month=mes
                ).aggregate(
                    total=Sum(F('valor_total') / F('parcelas_totais'))
                )['total'] or 0

                # soma final
                total_geral = total_mes + total_credito_mes

                gastos_lugar.setdefault(ano, {})[mes] = total_geral

    MESES_EXTENSO = {
        1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
        7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"
    }

    gastos_formatados = []
    for ano, meses_dict in gastos_lugar.items():
        meses_ordenados = sorted(meses_dict.items(), key=lambda x: x[0], reverse=True)

        meses_lista = []
        for mes, total in meses_ordenados:
            meses_lista.append({"mes": MESES_EXTENSO.get(mes, mes),"total": total})

        gastos_formatados.append({"ano": ano,"meses": meses_lista})

    gastos_formatados.sort(key=lambda x: x["ano"], reverse=True)

    context = {
        'logado': True,
        'lugar': single_lugar,
        'username': request.user.username,
        'site_title': site_title,
        'gastos_formatados': gastos_formatados,
        'sublugares': sublugares,
    }

    return render(request, 'lugar.html', context)



def categoria(request, categoria_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        single_categoria = Categorias.objects.get(pk=categoria_id, usuario=request.user)
    except Categorias.DoesNotExist:
        return redirect('controledegastos:index')

    # incluir filhos na soma dos gastos
    categorias_filhas_qs = Categorias.objects.filter(
        categoria_pai=single_categoria,
        usuario=request.user
    )
    categoria_ids = [single_categoria.id] + list(categorias_filhas_qs.values_list('id', flat=True))

    # calcular totais do mês atual para cada categoria (inclui netos)
    hoje = datetime.date.today()
    categorias_usuario = Categorias.objects.filter(usuario=request.user)
    children_map = defaultdict(list)
    for cat in categorias_usuario:
        if cat.categoria_pai_id:
            children_map[cat.categoria_pai_id].append(cat.id)

    totals_mes = defaultdict(Decimal)
    despesas_mes = Despesas.objects.filter(
        usuario=request.user,
        data__year=hoje.year,
        data__month=hoje.month
    ).values('categoria_id').annotate(total=Sum('valor'))
    for row in despesas_mes:
        cid = row['categoria_id']
        if cid:
            totals_mes[cid] += row['total'] or Decimal('0')

    despesas_credito_mes = DespesasCredito.objects.filter(
        usuario=request.user,
        data__year=hoje.year,
        data__month=hoje.month
    ).values('categoria_id').annotate(total=Sum(F('valor_total') / F('parcelas_totais')))
    for row in despesas_credito_mes:
        cid = row['categoria_id']
        if cid:
            totals_mes[cid] += row['total'] or Decimal('0')

    subtree_cache = {}

    def subtree_total(cat_id):
        if cat_id in subtree_cache:
            return subtree_cache[cat_id]
        subtotal = totals_mes.get(cat_id, Decimal('0'))
        for child_id in children_map.get(cat_id, []):
            subtotal += subtree_total(child_id)
        subtree_cache[cat_id] = subtotal
        return subtotal

    site_title = f'Categoria: {single_categoria.nome}'

    # Capturar ano/mês onde existe despesa ou crédito
    year_month_qs_despesas = Despesas.objects.filter(usuario=request.user) \
        .values_list('data__year', 'data__month') \
        .distinct()

    year_month_qs_credito = DespesasCredito.objects.filter(usuario=request.user) \
        .values_list('data__year', 'data__month') \
        .distinct()

    anos_map = {}
    for ano, mes in year_month_qs_despesas:
        anos_map.setdefault(ano, set()).add(mes)

    for ano, mes in year_month_qs_credito:
        anos_map.setdefault(ano, set()).add(mes)

    # Montar estrutura ordenada
    anos_validos = [
        {ano: sorted(list(meses), reverse=True)}
        for ano, meses in sorted(anos_map.items(), reverse=True)
    ]

    gastos_categoria = {}

    for ano_dict in anos_validos:
        for ano, meses in ano_dict.items():
            for mes in meses:

                # despesas comuns
                total_mes = Despesas.objects.filter(
                    usuario=request.user,
                    categoria__in=categoria_ids,
                    data__year=ano,
                    data__month=mes
                ).aggregate(total=Sum('valor'))['total'] or 0

                # despesas crédito proporcional do mês
                total_credito_mes = DespesasCredito.objects.filter(
                    usuario=request.user,
                    categoria__in=categoria_ids,
                    data__year=ano,
                    data__month=mes
                ).aggregate(
                    total=Sum(F('valor_total') / F('parcelas_totais'))
                )['total'] or 0

                gastos_categoria.setdefault(ano, {})[mes] = total_mes + total_credito_mes

    MESES_EXTENSO = {
        1: "Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
        7: "Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"
    }

    gastos_formatados = []
    for ano, meses_dict in gastos_categoria.items():

        meses_ordenados = sorted(meses_dict.items(), key=lambda x: x[0], reverse=True)

        meses_lista = []
        for mes, total in meses_ordenados:
            meses_lista.append({
                "mes": MESES_EXTENSO.get(mes, mes),
                "total": total
            })

        gastos_formatados.append({
            "ano": ano,
            "meses": meses_lista
        })

    gastos_formatados.sort(key=lambda x: x["ano"], reverse=True)

    # Categorias filhas (caso existam)
    categorias_filhas = []
    for c in categorias_filhas_qs.order_by('nome'):
        valor_mes = subtree_total(c.id)
        c.valor_por_mes = valor_mes
        meta_valor = c.meta_valor or Decimal('0')
        if meta_valor > 0:
            perc = (valor_mes / meta_valor) * Decimal('100')
            if perc < Decimal('80'):
                c.percentual_meta_cor = 'verde'
            elif perc < Decimal('100'):
                c.percentual_meta_cor = 'amarelo'
            else:
                c.percentual_meta_cor = 'vermelho'
        else:
            c.percentual_meta_cor = None
        categorias_filhas.append(c)

    return render(request, 'categoria.html', {
        'logado': True,
        'categoria': single_categoria,
        'username': request.user.username,
        'site_title': site_title,
        'gastos_formatados': gastos_formatados,
        'categorias_filhas': categorias_filhas,
    })

def prevista(request, prevista_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        single_prevista = Previstas.objects.get(pk=prevista_id, usuario=request.user)
    except Previstas.DoesNotExist:
        return redirect('controledegastos:previstas')

    site_title = f'{single_prevista.nome} - {single_prevista.valor}({single_prevista.data_prevista})'

    context = {
        'logado': True,
        'prevista': single_prevista,
        'username': request.user.username,
        'site_title': site_title
    }

    return render(
        request,
        'prevista.html',
        context
    )

def despesacredito(request, despesa_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    # Busca a despesa do cartão associada ao usuário logado
    try:
        despesa = DespesasCredito.objects.get(pk=despesa_id, usuario=request.user)
    except DespesasCredito.DoesNotExist:
        return redirect('controledegastos:creditos')

    # Título da aba do navegador
    site_title = f"{despesa.nome} - R$ {despesa.valor_total} ({despesa.data.strftime('%d/%m/%Y')})"

    context = {
        'logado': True,
        'username': request.user.username,
        'site_title': site_title,
        'valor_parcela': despesa.valor_total / despesa.parcelas_totais,
        'despesa': despesa,
    }

    return render(request, 'despesa_credito.html', context)


def createorcamento(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    form_action = reverse('controledegastos:criarorcamento')

    if request.method == 'POST':
        form = OrcamentosForm(request.POST)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Receita',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            orcamento = form.save(commit=False)
            orcamento.usuario = request.user
            orcamento.save()
            return redirect('controledegastos:orcamentos')

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = OrcamentosForm()

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Receita',
        'username': request.user.username,
        'form_action': form_action,
    }

    return render(
        request,
        'form.html',
        context
    )

def createlugar(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    form_action = reverse('controledegastos:criarlugar')

    parent_id = request.GET.get('lugar_pai') if request.method == 'GET' else request.POST.get('lugar_pai')
    locked_parent = False
    parent_obj = None
    if parent_id:
        try:
            parent_obj = Lugares.objects.get(pk=parent_id, usuario=request.user, lugar_pai__isnull=True)
            locked_parent = True
        except Lugares.DoesNotExist:
            parent_obj = None
            locked_parent = False

    if request.method == 'POST':
        init = {'lugar_pai': parent_obj} if parent_obj else None
        form = LugaresForm(request.POST, usuario=request.user, initial=init)
        if locked_parent and 'lugar_pai' in form.fields:
            form.fields['lugar_pai'].widget.attrs['disabled'] = True

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Lugar',
            'username': request.user.username,
            'form_action': form_action,
            'lock_lugar_pai': locked_parent,
            'lugar_pai_id': parent_obj.id if parent_obj else None,
            'lugar_pai_nome': parent_obj.nome if parent_obj else None,
        }

        if form.is_valid():
            lugar = form.save(commit=False)
            lugar.usuario = request.user
            if locked_parent and parent_obj:
                lugar.lugar_pai = parent_obj
            lugar.save()
            return redirect('controledegastos:lugares')

        return render(
            request,
            'form.html',
            context
        )
    else:
        init = {'lugar_pai': parent_obj} if parent_obj else None
        form = LugaresForm(usuario=request.user, initial=init)
        if locked_parent and 'lugar_pai' in form.fields:
            form.fields['lugar_pai'].widget.attrs['disabled'] = True

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Lugar',
        'username': request.user.username,
        'form_action': form_action,
        'lock_lugar_pai': locked_parent,
        'lugar_pai_id': parent_obj.id if parent_obj else None,
        'lugar_pai_nome': parent_obj.nome if parent_obj else None,

    }

    return render(
        request,
        'form.html',
        context
    )

def createcategoria(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    form_action = reverse('controledegastos:criarcategoria')

    # bloqueia seleção de categoria_pai quando vier na querystring
    parent_id = request.GET.get('categoria_pai') if request.method == 'GET' else request.POST.get('categoria_pai')
    locked_parent = False
    parent_obj = None
    if parent_id:
        try:
            parent_obj = Categorias.objects.get(pk=parent_id, usuario=request.user, categoria_pai__isnull=True)
            locked_parent = True
        except Categorias.DoesNotExist:
            parent_obj = None
            locked_parent = False

    if request.method == 'POST':
        init = {'categoria_pai': parent_obj} if parent_obj else None
        form = CategoriasForm(request.POST, usuario=request.user, initial=init)
        if locked_parent and 'categoria_pai' in form.fields:
            form.fields['categoria_pai'].widget.attrs['disabled'] = True

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Categoria',
            'username': request.user.username,
            'form_action': form_action,
            'lock_categoria_pai': locked_parent,
            'categoria_pai_id': parent_obj.id if parent_obj else None,
            'categoria_pai_nome': parent_obj.nome if parent_obj else None,
        }

        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.usuario = request.user
            if locked_parent and parent_obj:
                categoria.categoria_pai = parent_obj
            categoria.save()
            return redirect('controledegastos:categorias')

        return render(
            request,
            'form.html',
            context
        )
    else:
        init = {'categoria_pai': parent_obj} if parent_obj else None
        form = CategoriasForm(usuario=request.user, initial=init)
        if locked_parent and 'categoria_pai' in form.fields:
            form.fields['categoria_pai'].widget.attrs['disabled'] = True

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Categoria',
        'username': request.user.username,
        'form_action': form_action,
        'lock_categoria_pai': locked_parent,
        'categoria_pai_id': parent_obj.id if parent_obj else None,
        'categoria_pai_nome': parent_obj.nome if parent_obj else None,

    }

    return render(
        request,
        'form.html',
        context
    )

def createdespesa(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    form_action = reverse('controledegastos:criardespesa')

    if request.method == 'POST':
        form = DespesasForm(request.POST, usuario=request.user)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Despesa',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            despesa = form.save(commit=False)
            despesa.usuario = request.user
            despesa.save()
            return redirect('controledegastos:index')

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = DespesasForm(usuario=request.user)

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Despesa',
        'username': request.user.username,
        'form_action': form_action,

    }

    return render(
        request,
        'form.html',
        context
    )

def createprevista(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    form_action = reverse('controledegastos:criarprevista')

    if request.method == 'POST':
        form = PrevistasForm(request.POST, usuario=request.user)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Despesa Prevista',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            prevista = form.save(commit=False)
            prevista.usuario = request.user
            prevista.save()
            return redirect('controledegastos:previstas')

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = PrevistasForm(usuario=request.user)

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Despesa Prevista',
        'username': request.user.username,
        'form_action': form_action,

    }

    return render(
        request,
        'form.html',
        context
    )

def createcredito(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    form_action = reverse('controledegastos:criarcartao')

    if request.method == 'POST':
        form = CartoesCreditoForm(request.POST)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Cartão de Crédito',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            credito = form.save(commit=False)
            credito.usuario = request.user
            credito.save()
            return redirect('controledegastos:creditos')

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = CartoesCreditoForm()

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Cartão de Crédito',
        'username': request.user.username,
        'form_action': form_action,

    }

    return render(
        request,
        'form.html',
        context
    )

def createdespesacredito(request):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    form_action = reverse('controledegastos:criardespesacredito')

    if request.method == 'POST':
        form = DespesasCreditoForm(request.POST, usuario=request.user)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Despesa de Cartão de Crédito',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            despesa = form.save(commit=False)
            despesa.usuario = request.user
            if despesa.parcelas_restantes is None:
                despesa.parcelas_restantes = despesa.parcelas_totais
            despesa.save()
            return redirect('controledegastos:creditos')

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = DespesasCreditoForm(usuario=request.user)

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Despesa de Cartão de Crédito',
        'username': request.user.username,
        'form_action': form_action,

    }

    return render(
        request,
        'form.html',
        context
    )

def deleteorcamento(request, orcamento_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    try:
        orcamento = Orcamentos.objects.get(pk=orcamento_id, usuario=request.user)
        orcamento.delete()
    except Orcamentos.DoesNotExist:
        return redirect('controledegastos:orcamentos')

    return redirect('controledegastos:orcamentos')

def deletedespesa(request, despesa_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        despesa = Despesas.objects.get(pk=despesa_id, usuario=request.user)
        despesa.delete()
    except Despesas.DoesNotExist:
        return redirect('controledegastos:index')

    return redirect('controledegastos:index')

def deletelugar(request, lugar_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        lugar = Lugares.objects.get(pk=lugar_id, usuario=request.user)
        lugar.delete()
    except Lugares.DoesNotExist:
        return redirect('controledegastos:lugares')

    return redirect('controledegastos:lugares')

def deletecategoria(request, categoria_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        categoria = Categorias.objects.get(pk=categoria_id, usuario=request.user)
        categoria.delete()
    except Categorias.DoesNotExist:
        return redirect('controledegastos:categorias')

    return redirect('controledegastos:categorias')

def deleteprevista(request, prevista_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        prevista = Previstas.objects.get(pk=prevista_id, usuario=request.user)
        prevista.delete()
    except Previstas.DoesNotExist:
        return redirect('controledegastos:previstas')

    return redirect('controledegastos:previstas')

def deletecartao(request, cartao_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        cartao = CartoesCredito.objects.get(pk=cartao_id, usuario=request.user)
        despesas_associadas = DespesasCredito.objects.filter(cartao=cartao)
        despesas_associadas.delete()
        cartao.delete()
    except CartoesCredito.DoesNotExist:
        return redirect('controledegastos:creditos')

    return redirect('controledegastos:creditos')

def deletedespesacredito(request, despesa_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')

    try:
        despesa = DespesasCredito.objects.get(pk=despesa_id, usuario=request.user)
        despesa.delete()
    except DespesasCredito.DoesNotExist:
        return redirect('controledegastos:creditos')

    return redirect('controledegastos:creditos')

def editorcamento(request, orcamento_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    try:
        orcamento = Orcamentos.objects.get(pk=orcamento_id, usuario=request.user)
    except Orcamentos.DoesNotExist:
        return redirect('controledegastos:orcamentos')

    form_action = reverse('controledegastos:editarorcamento', args=[orcamento_id])

    if request.method == 'POST':
        form = OrcamentosForm(request.POST, instance=orcamento)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Editar Orçamento',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            orcamento = form.save(commit=False)
            orcamento.save()
            return redirect('controledegastos:orcamento', orcamento_id=orcamento.id)

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = OrcamentosForm(instance=orcamento)

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Editar Orçamento',
        'username': request.user.username,
        'form_action': form_action,

    }

    return render(
        request,
        'form.html',
        context
    )

def editdespesa(request, despesa_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    try:
        despesa = Despesas.objects.get(pk=despesa_id, usuario=request.user)
    except Despesas.DoesNotExist:
        return redirect('controledegastos:index')

    form_action = reverse('controledegastos:editardespesa', args=[despesa_id])

    if request.method == 'POST':
        form = DespesasForm(request.POST, instance=despesa, usuario=request.user)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Editar Despesa',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            despesa = form.save(commit=False)
            despesa.save()
            return redirect('controledegastos:despesa', despesa_id=despesa.id)

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = DespesasForm(instance=despesa, usuario=request.user)

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Editar Despesa',
        'username': request.user.username,
        'form_action': form_action,

    }

    return render(
        request,
        'form.html',
        context
    )

def editcategoria(request, categoria_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        categoria = Categorias.objects.get(pk=categoria_id, usuario=request.user)
    except Categorias.DoesNotExist:
        return redirect('controledegastos:categorias')

    form_action = reverse('controledegastos:editarcategoria', args=[categoria_id])

    if request.method == 'POST':
        form = CategoriasForm(request.POST, instance=categoria)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Editar Categoria',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.save()
            return redirect('controledegastos:categorias')

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = CategoriasForm(instance=categoria)

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Editar Categoria',
        'username': request.user.username,
        'form_action': form_action,

    }

    return render(
        request,
        'form.html',
        context
    )

def editlugar(request, lugar_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        lugar = Lugares.objects.get(pk=lugar_id, usuario=request.user)
    except Lugares.DoesNotExist:
        return redirect('controledegastos:lugares')

    form_action = reverse('controledegastos:editarlugar', args=[lugar_id])

    if request.method == 'POST':
        form = LugaresForm(request.POST, instance=lugar, usuario=request.user)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Editar Lugar',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            lugar = form.save(commit=False)
            lugar.save()
            return redirect('controledegastos:lugares')

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = LugaresForm(instance=lugar, usuario=request.user)

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Editar Lugar',
        'username': request.user.username,
        'form_action': form_action,

    }

    return render(
        request,
        'form.html',
        context
    )

def editprevista(request, prevista_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        prevista = Previstas.objects.get(pk=prevista_id, usuario=request.user)
    except Previstas.DoesNotExist:
        return redirect('controledegastos:previstas')

    form_action = reverse('controledegastos:editarprevista', args=[prevista_id])

    if request.method == 'POST':
        form = PrevistasForm(request.POST, instance=prevista, usuario=request.user)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Editar Despesa Prevista',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            prevista = form.save(commit=False)
            prevista.save()
            return redirect('controledegastos:prevista', prevista_id=prevista.id)

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = PrevistasForm(instance=prevista, usuario=request.user)

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Editar Despesa Prevista',
        'username': request.user.username,
        'form_action': form_action,

    }

    return render(
        request,
        'form.html',
        context
    )

def editcredito(request, cartao_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        credito = CartoesCredito.objects.get(pk=cartao_id, usuario=request.user)
    except CartoesCredito.DoesNotExist:
        return redirect('controledegastos:creditos')

    form_action = reverse('controledegastos:editarcartao', args=[cartao_id])

    if request.method == 'POST':
        form = CartoesCreditoForm(request.POST, instance=credito)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Editar Cartão de Crédito',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            credito = form.save(commit=False)
            credito.save()
            return redirect('controledegastos:creditos')

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = CartoesCreditoForm(instance=credito)

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Editar Cartão de Crédito',
        'username': request.user.username,
        'form_action': form_action,

    }

    return render(
        request,
        'form.html',
        context
    )

def editdespesacredito(request, despesa_id):
    if not request.user.is_authenticated:
        return redirect('controledegastos:login')
    
    
    
    try:
        despesa = DespesasCredito.objects.get(pk=despesa_id, usuario=request.user)
    except DespesasCredito.DoesNotExist:
        return redirect('controledegastos:creditos')

    form_action = reverse('controledegastos:editardespesacredito', args=[despesa_id])

    if request.method == 'POST':
        form = DespesasCreditoForm(request.POST, instance=despesa, usuario=request.user)

        context = {
            'logado': True,
            'form': form,
            'form_name': 'Editar Despesa de Cartão de Crédito',
            'username': request.user.username,
            'form_action': form_action,
        }

        if form.is_valid():
            despesa = form.save(commit=False)
            if despesa.parcelas_restantes is None:
                despesa.parcelas_restantes = despesa.parcelas_totais
            despesa.save()
            return redirect('controledegastos:creditos')

        return render(
            request,
            'form.html',
            context
        )
    else:
        form = DespesasCreditoForm(instance=despesa, usuario=request.user)

    context = {
        'logado': True,
        'form': form,
        'form_name': 'Editar Despesa de Cartão de Crédito',
        'username': request.user.username,
        'form_action': form_action,

    }

    return render(
        request,
        'form.html',
        context
    )
