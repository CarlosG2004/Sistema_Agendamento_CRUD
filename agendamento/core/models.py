from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Usuario(AbstractUser):
    TIPO_CHOICES = [
        ('prestador', 'Prestador de Serviço'),
        ('cliente', 'Cliente'),
    ]
    email = models.EmailField(unique=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    telefone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'tipo']

    @property
    def is_prestador(self):
        return self.tipo == 'prestador'

    @property
    def is_cliente(self):
        return self.tipo == 'cliente'

    def __str__(self):
        return f'{self.get_full_name() or self.email} ({self.get_tipo_display()})'


class Servico(models.Model):
    prestador = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='servicos',
        limit_choices_to={'tipo': 'prestador'}
    )
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    duracao_minutos = models.PositiveIntegerField()
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} - {self.prestador.get_full_name() or self.prestador.email}'

    def pode_ser_deletado(self):
        """Verifica se não há agendamentos futuros confirmados."""
        agora = timezone.now()
        return not self.agendamentos.filter(
            status='confirmado',
            data_hora__gt=agora
        ).exists()


class Disponibilidade(models.Model):
    DIA_SEMANA_CHOICES = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    prestador = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='disponibilidades',
        limit_choices_to={'tipo': 'prestador'}
    )
    dia_semana = models.IntegerField(choices=DIA_SEMANA_CHOICES)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()

    class Meta:
        ordering = ['dia_semana', 'hora_inicio']

    def __str__(self):
        return (
            f'{self.get_dia_semana_display()} '
            f'{self.hora_inicio.strftime("%H:%M")}-{self.hora_fim.strftime("%H:%M")} '
            f'({self.prestador.get_full_name() or self.prestador.email})'
        )

    def clean(self):
        if self.hora_inicio >= self.hora_fim:
            raise ValidationError('O horário de início deve ser anterior ao horário de fim.')

        # Verificar sobreposição com outras janelas do mesmo prestador no mesmo dia
        qs = Disponibilidade.objects.filter(
            prestador=self.prestador,
            dia_semana=self.dia_semana
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        for disp in qs:
            if self.hora_inicio < disp.hora_fim and self.hora_fim > disp.hora_inicio:
                raise ValidationError(
                    f'Conflito com janela existente: '
                    f'{disp.hora_inicio.strftime("%H:%M")}-{disp.hora_fim.strftime("%H:%M")}'
                )


class Agendamento(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('confirmado', 'Confirmado'),
        ('cancelado', 'Cancelado'),
    ]

    cliente = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='agendamentos_como_cliente',
        limit_choices_to={'tipo': 'cliente'}
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.PROTECT,
        related_name='agendamentos'
    )
    data_hora = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_hora']

    def __str__(self):
        return (
            f'{self.servico.nome} - '
            f'{self.cliente.get_full_name() or self.cliente.email} - '
            f'{self.data_hora.strftime("%d/%m/%Y %H:%M")} - '
            f'{self.get_status_display()}'
        )

    @property
    def data_hora_fim(self):
        from datetime import timedelta
        return self.data_hora + timedelta(minutes=self.servico.duracao_minutos)

    def clean(self):
        prestador = self.servico.prestador

        # Verificar se o horário cai em uma janela de disponibilidade
        dia_semana = self.data_hora.weekday()
        hora = self.data_hora.time()

        disponivel = Disponibilidade.objects.filter(
            prestador=prestador,
            dia_semana=dia_semana,
            hora_inicio__lte=hora,
            hora_fim__gte=hora
        ).exists()

        if not disponivel:
            raise ValidationError(
                'O horário selecionado não está dentro da disponibilidade do prestador.'
            )

        # Verificar conflito com outros agendamentos do mesmo prestador
        from datetime import timedelta
        data_fim = self.data_hora + timedelta(minutes=self.servico.duracao_minutos)

        conflitos = Agendamento.objects.filter(
            servico__prestador=prestador,
            status__in=['pendente', 'confirmado'],
            data_hora__lt=data_fim,
        ).exclude(pk=self.pk)

        for ag in conflitos:
            if ag.data_hora_fim > self.data_hora:
                raise ValidationError(
                    f'Conflito com agendamento existente: '
                    f'{ag.servico.nome} às {ag.data_hora.strftime("%H:%M")}.'
                )
