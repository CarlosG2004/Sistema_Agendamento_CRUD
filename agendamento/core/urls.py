from django.urls import path

from . import views

urlpatterns = [
    # ── Páginas HTML ──────────────────────────────────────────────────────────
    path('', views.pagina_inicial, name='index'),
    path('login/', views.pagina_login, name='login'),
    path('registro/', views.pagina_registro, name='registro'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # ── API: Autenticação ─────────────────────────────────────────────────────
    path('api/auth/registro/', views.api_registro, name='api_registro'),
    path('api/auth/login/', views.api_login, name='api_login'),
    path('api/auth/logout/', views.api_logout, name='api_logout'),

    # ── API: Serviços ─────────────────────────────────────────────────────────
    path('api/servicos/', views.api_servicos_list, name='api_servicos_list'),
    path('api/servicos/criar/', views.api_servicos_criar, name='api_servicos_criar'),
    path('api/servicos/<int:servico_id>/editar/', views.api_servicos_editar, name='api_servicos_editar'),
    path('api/servicos/<int:servico_id>/deletar/', views.api_servicos_deletar, name='api_servicos_deletar'),

    # ── API: Disponibilidade ──────────────────────────────────────────────────
    path('api/disponibilidade/', views.api_disponibilidade_list, name='api_disponibilidade_list'),
    path('api/disponibilidade/criar/', views.api_disponibilidade_criar, name='api_disponibilidade_criar'),
    path('api/disponibilidade/<int:disp_id>/deletar/', views.api_disponibilidade_deletar, name='api_disponibilidade_deletar'),

    # ── API: Agendamentos ─────────────────────────────────────────────────────
    path('api/agendamentos/', views.api_agendamentos_list, name='api_agendamentos_list'),
    path('api/agendamentos/criar/', views.api_agendamentos_criar, name='api_agendamentos_criar'),
    path('api/agendamentos/<int:agendamento_id>/acao/', views.api_agendamentos_acao, name='api_agendamentos_acao'),

    # ── API: Públicas ─────────────────────────────────────────────────────────
    path('api/prestadores/', views.api_prestadores, name='api_prestadores'),
    path('api/prestadores/<int:prestador_id>/servicos/', views.api_servicos_prestador, name='api_servicos_prestador'),
]
