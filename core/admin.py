from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Servico, Disponibilidade, Agendamento


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'tipo', 'is_active']
    list_filter = ['tipo', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Perfil', {'fields': ('tipo', 'telefone', 'bio')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Perfil', {'fields': ('email', 'tipo', 'telefone')}),
    )


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'prestador', 'preco', 'duracao_minutos', 'ativo']
    list_filter = ['ativo', 'prestador']


@admin.register(Disponibilidade)
class DisponibilidadeAdmin(admin.ModelAdmin):
    list_display = ['prestador', 'dia_semana', 'hora_inicio', 'hora_fim']
    list_filter = ['prestador', 'dia_semana']


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ['servico', 'cliente', 'data_hora', 'status']
    list_filter = ['status', 'servico__prestador']
    date_hierarchy = 'data_hora'
