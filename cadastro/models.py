from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _

# =============================================
# CONSTANTES GLOBAIS
# =============================================

# Constante de escolhas para Unidade
UNIDADE_CHOICES = [
    ('Maringá', 'Maringá'),
    ('Guarapuava', 'Guarapuava'),
    ('Ponta Grossa', 'Ponta Grossa'),
    ('Norte Pioneiro', 'Norte Pioneiro'),
]

# =============================================
# MODELO DE USUÁRIO PERSONALIZADO
# =============================================

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('tipo_acesso', 'admin')
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    TIPO_ACESSO_CHOICES = [
        ('admin', 'Administrador'),
        ('responsavel', 'Responsável'),
        ('operador', 'Operador'),
    ]
    
    # Unidade usa a constante global UNIDADE_CHOICES
    unidade = models.CharField('Unidade', max_length=100, choices=UNIDADE_CHOICES, default='Maringá')

    # Mantemos o username, mas permitimos que seja nulo/opcional
    username = models.CharField(
        'Nome de usuário', 
        max_length=150, 
        unique=True, 
        blank=True, 
        null=True,
        help_text='Opcional. Pode ser deixado em branco.'
    )
    
    email = models.EmailField('Email', unique=True)
    nome_completo = models.CharField('Nome Completo', max_length=100)
    cargo = models.CharField('Cargo', max_length=100, blank=True)
    tipo_acesso = models.CharField('Tipo de Acesso', max_length=20, choices=TIPO_ACESSO_CHOICES, default='operador')
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    
    criado_por = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='usuarios_criados'
    )

    # Configura para usar email como campo de login
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome_completo', 'unidade']

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        # Se username estiver vazio, usa parte do email para preenchimento automático
        if not self.username and self.email:
            # Garantimos que seja um username único, adicionando o ID se necessário (embora não seja estritamente necessário no save)
            base_username = self.email.split('@')[0].lower()
            self.username = base_username
            # O AbstractUser já tem uma lógica para garantir a unicidade, 
            # mas essa linha simples já ajuda a preencher o campo.

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome_completo} - {self.unidade}"

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        permissions = [
            ("pode_criar_usuarios", "Pode criar novos usuários"),
            ("acesso_total", "Acesso total ao sistema"),
            ("acesso_cadastro", "Acesso apenas ao cadastro"),
        ]

# =============================================
# MODELO CLIENTE
# =============================================
class Cliente(models.Model):
    
    # Unidade usa a constante global UNIDADE_CHOICES
    unidade = models.CharField(max_length=100, choices=UNIDADE_CHOICES)
    data_cadastro = models.DateField()
    codigo_cliente = models.CharField(max_length=50)
    
    # ✅ Padronização: 18 dígitos no total, 15 casas decimais é uma precisão comum e segura
    # (Por exemplo, um DecimalField(max_digits=20, decimal_places=15) já é mais que o suficiente)
    latitude = models.DecimalField(max_digits=18, decimal_places=15)
    longitude = models.DecimalField(max_digits=18, decimal_places=15)
    
    def __str__(self):
        return f"{self.codigo_cliente} - {self.unidade}"
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        # Adiciona um índice composto para consultas rápidas
        # constraints = [
        #     models.UniqueConstraint(fields=['codigo_cliente', 'unidade', 'data_cadastro'], name='unique_cliente_unidade_data')
        # ]