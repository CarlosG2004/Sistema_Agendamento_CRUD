import json
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Agendamento, Disponibilidade, Servico, Usuario


# ─── Helpers ──────────────────────────────────────────────────────────────────

def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False})


def requer_prestador(view_func):
    """Decorator: garante que o usuário autenticado é prestador."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_prestador:
            return json_response({'erro': 'Acesso restrito a prestadores.'}, 403)
        return view_func(request, *args, **kwargs)
    return _wrapped


def requer_cliente(view_func):
    """Decorator: garante que o usuário autenticado é cliente."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_cliente:
            return json_response({'erro': 'Acesso restrito a clientes.'}, 403)
        return view_func(request, *args, **kwargs)
    return _wrapped


# ─── Autenticação ─────────────────────────────────────────────────────────────

def pagina_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/login.html')


def pagina_registro(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/registro.html')


@csrf_exempt
@require_http_methods(['POST'])
def api_registro(request):
    """RF-01: Registro de novo usuário."""
    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return json_response({'erro': 'JSON inválido.'}, 400)

    campos_obrigatorios = ['email', 'password', 'tipo', 'first_name', 'last_name']
    for campo in campos_obrigatorios:
        if not dados.get(campo):
            return json_response({'erro': f'Campo obrigatório: {campo}'}, 400)

    tipo = dados['tipo']
    if tipo not in ('prestador', 'cliente'):
        return json_response({'erro': 'tipo deve ser "prestador" ou "cliente".'}, 400)

    if Usuario.objects.filter(email=dados['email']).exists():
        return json_response({'erro': 'E-mail já cadastrado.'}, 400)

    try:
        usuario = Usuario.objects.create_user(
            username=dados['email'],
            email=dados['email'],
            password=dados['password'],
            first_name=dados['first_name'],
            last_name=dados['last_name'],
            tipo=tipo,
            telefone=dados.get('telefone', ''),
            bio=dados.get('bio', ''),
        )
    except Exception as e:
        return json_response({'erro': str(e)}, 400)

    return json_response({
        'mensagem': 'Usuário criado com sucesso.',
        'usuario': {
            'id': usuario.id,
            'email': usuario.email,
            'nome': usuario.get_full_name(),
            'tipo': usuario.tipo,
        }
    }, 201)


@csrf_exempt
@require_http_methods(['POST'])
def api_login(request):
    """RF-01: Login com retorno de token de sessão."""
    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return json_response({'erro': 'JSON inválido.'}, 400)

    email = dados.get('email', '')
    password = dados.get('password', '')

    usuario = authenticate(request, username=email, password=password)
    if usuario is None:
        return json_response({'erro': 'E-mail ou senha inválidos.'}, 401)

    login(request, usuario)
    return json_response({
        'mensagem': 'Login realizado com sucesso.',
        'usuario': {
            'id': usuario.id,
            'email': usuario.email,
            'nome': usuario.get_full_name(),
            'tipo': usuario.tipo,
        }
    })


@login_required
def api_logout(request):
    """RF-01: Logout."""
    logout(request)
    return json_response({'mensagem': 'Logout realizado com sucesso.'})


# ─── Dashboard (HTML) ─────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    usuario = request.user

    if usuario.is_prestador:
        servicos = Servico.objects.filter(prestador=usuario)
        disponibilidades = Disponibilidade.objects.filter(prestador=usuario)
        agendamentos = Agendamento.objects.filter(
            servico__prestador=usuario
        ).select_related('cliente', 'servico')

        ctx = {
            'servicos': servicos,
            'disponibilidades': disponibilidades,
            'agendamentos': agendamentos,
            'total_pendentes': agendamentos.filter(status='pendente').count(),
            'total_confirmados': agendamentos.filter(status='confirmado').count(),
            'total_cancelados': agendamentos.filter(status='cancelado').count(),
        }
        return render(request, 'core/dashboard_prestador.html', ctx)

    # Cliente
    meus_agendamentos = Agendamento.objects.filter(
        cliente=usuario
    ).select_related('servico', 'servico__prestador')

    prestadores = Usuario.objects.filter(tipo='prestador')

    ctx = {
        'meus_agendamentos': meus_agendamentos,
        'prestadores': prestadores,
    }
    return render(request, 'core/dashboard_cliente.html', ctx)


# ─── RF-02: Serviços (Prestador) ──────────────────────────────────────────────

@login_required
@require_http_methods(['GET'])
def api_servicos_list(request):
    """Lista serviços do prestador autenticado."""
    if not request.user.is_prestador:
        return json_response({'erro': 'Acesso restrito a prestadores.'}, 403)
    servicos = Servico.objects.filter(prestador=request.user).values(
        'id', 'nome', 'descricao', 'duracao_minutos', 'preco', 'ativo'
    )
    return json_response(list(servicos))


@csrf_exempt
@login_required
@require_http_methods(['POST'])
def api_servicos_criar(request):
    """RF-02: Criar serviço."""
    if not request.user.is_prestador:
        return json_response({'erro': 'Acesso restrito a prestadores.'}, 403)
    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return json_response({'erro': 'JSON inválido.'}, 400)

    for campo in ['nome', 'duracao_minutos', 'preco']:
        if not dados.get(campo):
            return json_response({'erro': f'Campo obrigatório: {campo}'}, 400)

    servico = Servico.objects.create(
        prestador=request.user,
        nome=dados['nome'],
        descricao=dados.get('descricao', ''),
        duracao_minutos=int(dados['duracao_minutos']),
        preco=dados['preco'],
        ativo=dados.get('ativo', True),
    )
    return json_response({
        'mensagem': 'Serviço criado.',
        'servico': {
            'id': servico.id,
            'nome': servico.nome,
            'duracao_minutos': servico.duracao_minutos,
            'preco': str(servico.preco),
            'ativo': servico.ativo,
        }
    }, 201)


@csrf_exempt
@login_required
@require_http_methods(['PUT', 'PATCH'])
def api_servicos_editar(request, servico_id):
    """RF-02: Editar serviço."""
    if not request.user.is_prestador:
        return json_response({'erro': 'Acesso restrito a prestadores.'}, 403)

    servico = get_object_or_404(Servico, pk=servico_id, prestador=request.user)

    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return json_response({'erro': 'JSON inválido.'}, 400)

    for campo in ['nome', 'descricao', 'duracao_minutos', 'preco', 'ativo']:
        if campo in dados:
            setattr(servico, campo, dados[campo])
    servico.save()

    return json_response({'mensagem': 'Serviço atualizado.', 'id': servico.id})


@csrf_exempt
@login_required
@require_http_methods(['DELETE'])
def api_servicos_deletar(request, servico_id):
    """RF-02: Deletar serviço (apenas se não há agendamentos futuros confirmados)."""
    if not request.user.is_prestador:
        return json_response({'erro': 'Acesso restrito a prestadores.'}, 403)

    servico = get_object_or_404(Servico, pk=servico_id, prestador=request.user)

    if not servico.pode_ser_deletado():
        return json_response({
            'erro': 'Não é possível deletar: existem agendamentos futuros confirmados. Desative o serviço.'
        }, 400)

    servico.delete()
    return json_response({'mensagem': 'Serviço removido.'})


# ─── RF-03: Disponibilidade (Prestador) ───────────────────────────────────────

@login_required
@require_http_methods(['GET'])
def api_disponibilidade_list(request):
    if not request.user.is_prestador:
        return json_response({'erro': 'Acesso restrito a prestadores.'}, 403)
    disps = Disponibilidade.objects.filter(prestador=request.user).values(
        'id', 'dia_semana', 'hora_inicio', 'hora_fim'
    )
    result = []
    dias = dict(Disponibilidade.DIA_SEMANA_CHOICES)
    for d in disps:
        d['dia_semana_nome'] = dias[d['dia_semana']]
        d['hora_inicio'] = str(d['hora_inicio'])[:5]
        d['hora_fim'] = str(d['hora_fim'])[:5]
        result.append(d)
    return json_response(result)


@csrf_exempt
@login_required
@require_http_methods(['POST'])
def api_disponibilidade_criar(request):
    """RF-03: Cadastrar janela de disponibilidade."""
    if not request.user.is_prestador:
        return json_response({'erro': 'Acesso restrito a prestadores.'}, 403)

    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return json_response({'erro': 'JSON inválido.'}, 400)

    for campo in ['dia_semana', 'hora_inicio', 'hora_fim']:
        if dados.get(campo) is None:
            return json_response({'erro': f'Campo obrigatório: {campo}'}, 400)

    disp = Disponibilidade(
        prestador=request.user,
        dia_semana=int(dados['dia_semana']),
        hora_inicio=dados['hora_inicio'],
        hora_fim=dados['hora_fim'],
    )

    try:
        disp.full_clean()
        disp.save()
    except ValidationError as e:
        return json_response({'erro': e.message_dict if hasattr(e, 'message_dict') else str(e)}, 400)

    dias = dict(Disponibilidade.DIA_SEMANA_CHOICES)
    return json_response({
        'mensagem': 'Disponibilidade cadastrada.',
        'disponibilidade': {
            'id': disp.id,
            'dia_semana': disp.dia_semana,
            'dia_semana_nome': dias[disp.dia_semana],
            'hora_inicio': str(disp.hora_inicio)[:5],
            'hora_fim': str(disp.hora_fim)[:5],
        }
    }, 201)


@csrf_exempt
@login_required
@require_http_methods(['DELETE'])
def api_disponibilidade_deletar(request, disp_id):
    if not request.user.is_prestador:
        return json_response({'erro': 'Acesso restrito a prestadores.'}, 403)
    disp = get_object_or_404(Disponibilidade, pk=disp_id, prestador=request.user)
    disp.delete()
    return json_response({'mensagem': 'Disponibilidade removida.'})


# ─── RF-04: Agendamentos ──────────────────────────────────────────────────────

@login_required
@require_http_methods(['GET'])
def api_agendamentos_list(request):
    """RF-05: Listar agendamentos."""
    usuario = request.user

    if usuario.is_prestador:
        qs = Agendamento.objects.filter(servico__prestador=usuario)
    else:
        qs = Agendamento.objects.filter(cliente=usuario)

    # Filtros opcionais
    status_filtro = request.GET.get('status')
    if status_filtro:
        qs = qs.filter(status=status_filtro)

    data_filtro = request.GET.get('data')
    if data_filtro:
        qs = qs.filter(data_hora__date=data_filtro)

    result = []
    for ag in qs.select_related('cliente', 'servico', 'servico__prestador'):
        result.append({
            'id': ag.id,
            'servico': ag.servico.nome,
            'servico_id': ag.servico.id,
            'prestador': ag.servico.prestador.get_full_name() or ag.servico.prestador.email,
            'cliente': ag.cliente.get_full_name() or ag.cliente.email,
            'data_hora': ag.data_hora.strftime('%Y-%m-%d %H:%M'),
            'status': ag.status,
            'observacao': ag.observacao,
        })

    return json_response(result)


@csrf_exempt
@login_required
@require_http_methods(['POST'])
def api_agendamentos_criar(request):
    """RF-04: Cliente cria agendamento."""
    if not request.user.is_cliente:
        return json_response({'erro': 'Acesso restrito a clientes.'}, 403)

    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return json_response({'erro': 'JSON inválido.'}, 400)

    for campo in ['servico_id', 'data_hora']:
        if not dados.get(campo):
            return json_response({'erro': f'Campo obrigatório: {campo}'}, 400)

    servico = get_object_or_404(Servico, pk=dados['servico_id'], ativo=True)

    from django.utils.dateparse import parse_datetime
    data_hora = parse_datetime(dados['data_hora'])
    if data_hora is None:
        return json_response({'erro': 'Formato de data_hora inválido. Use: YYYY-MM-DD HH:MM'}, 400)

    if timezone.is_naive(data_hora):
        data_hora = timezone.make_aware(data_hora)

    agendamento = Agendamento(
        cliente=request.user,
        servico=servico,
        data_hora=data_hora,
        observacao=dados.get('observacao', ''),
    )

    try:
        agendamento.full_clean()
        agendamento.save()
    except ValidationError as e:
        msgs = []
        if hasattr(e, 'message_dict'):
            for field_msgs in e.message_dict.values():
                msgs.extend(field_msgs)
        else:
            msgs = list(e.messages)
        return json_response({'erro': msgs[0] if msgs else str(e)}, 400)

    return json_response({
        'mensagem': 'Agendamento criado com sucesso.',
        'agendamento': {
            'id': agendamento.id,
            'servico': agendamento.servico.nome,
            'data_hora': agendamento.data_hora.strftime('%Y-%m-%d %H:%M'),
            'status': agendamento.status,
        }
    }, 201)


@csrf_exempt
@login_required
@require_http_methods(['PATCH'])
def api_agendamentos_acao(request, agendamento_id):
    """RF-04: Confirmar / cancelar agendamento."""
    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return json_response({'erro': 'JSON inválido.'}, 400)

    nova_acao = dados.get('acao')  # 'confirmar' | 'cancelar'
    usuario = request.user

    # Localizar o agendamento com base no perfil
    if usuario.is_prestador:
        agendamento = get_object_or_404(Agendamento, pk=agendamento_id, servico__prestador=usuario)
    else:
        agendamento = get_object_or_404(Agendamento, pk=agendamento_id, cliente=usuario)

    if agendamento.status == 'cancelado':
        return json_response({'erro': 'Agendamentos cancelados não podem ser alterados.'}, 400)

    if nova_acao == 'confirmar':
        if not usuario.is_prestador:
            return json_response({'erro': 'Apenas prestadores podem confirmar agendamentos.'}, 403)
        agendamento.status = 'confirmado'

    elif nova_acao == 'cancelar':
        # Cliente só pode cancelar pendentes
        if usuario.is_cliente and agendamento.status != 'pendente':
            return json_response({'erro': 'Clientes só podem cancelar agendamentos pendentes.'}, 400)
        agendamento.status = 'cancelado'

    else:
        return json_response({'erro': 'Ação inválida. Use "confirmar" ou "cancelar".'}, 400)

    agendamento.save()
    return json_response({
        'mensagem': f'Agendamento {nova_acao}do com sucesso.',
        'status': agendamento.status,
    })


# ─── RF-05: Listagem pública de prestadores ───────────────────────────────────

@require_http_methods(['GET'])
def api_prestadores(request):
    """Listagem pública de prestadores (sem autenticação)."""
    prestadores = Usuario.objects.filter(tipo='prestador').values(
        'id', 'first_name', 'last_name', 'email', 'bio', 'telefone'
    )
    result = []
    for p in prestadores:
        servicos_ativos = list(
            Servico.objects.filter(prestador_id=p['id'], ativo=True).values(
                'id', 'nome', 'descricao', 'duracao_minutos', 'preco'
            )
        )
        result.append({
            **p,
            'nome_completo': f"{p['first_name']} {p['last_name']}".strip() or p['email'],
            'servicos_ativos': servicos_ativos,
        })
    return json_response(result)


@require_http_methods(['GET'])
def api_servicos_prestador(request, prestador_id):
    """RF-04: Cliente visualiza serviços ativos de um prestador."""
    prestador = get_object_or_404(Usuario, pk=prestador_id, tipo='prestador')
    servicos = Servico.objects.filter(prestador=prestador, ativo=True).values(
        'id', 'nome', 'descricao', 'duracao_minutos', 'preco'
    )
    return json_response({
        'prestador': {
            'id': prestador.id,
            'nome': prestador.get_full_name() or prestador.email,
            'bio': prestador.bio,
        },
        'servicos': list(servicos),
    })


# ─── Views HTML auxiliares ────────────────────────────────────────────────────

def pagina_inicial(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    prestadores = Usuario.objects.filter(tipo='prestador')[:6]
    return render(request, 'core/index.html', {'prestadores': prestadores})