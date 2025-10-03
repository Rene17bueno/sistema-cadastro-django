from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Cliente, CustomUser

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['unidade', 'data_cadastro', 'codigo_cliente', 'latitude', 'longitude']
        widgets = {
            'data_cadastro': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'step': '0.000000001', 'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'step': '0.000000001', 'class': 'form-control'}),
            'unidade': forms.Select(attrs={'class': 'form-select'}),
            'codigo_cliente': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_codigo_cliente(self):
        codigo_cliente = self.cleaned_data.get('codigo_cliente')
        if not codigo_cliente.isdigit():
            raise forms.ValidationError("O código do cliente deve conter apenas números.")
        return codigo_cliente
    
    def clean_latitude(self):
        latitude = self.cleaned_data.get('latitude')
        if latitude and (latitude < -90 or latitude > 90):
            raise forms.ValidationError("A latitude deve estar entre -90 e 90 graus.")
        return latitude
    
    def clean_longitude(self):
        longitude = self.cleaned_data.get('longitude')
        if longitude and (longitude < -180 or longitude > 180):
            raise forms.ValidationError("A longitude deve estar entre -180 e 180 graus.")
        return longitude

# ✅ FORMS PARA USUÁRIOS PERSONALIZADOS - CORRIGIDOS para email como username
class CustomUserCreationForm(UserCreationForm):
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a senha'
        }),
        help_text="A senha deve ter pelo menos 8 caracteres."
    )
    password2 = forms.CharField(
        label="Confirmação de Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Confirme a senha'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['email', 'nome_completo', 'unidade', 'cargo', 'tipo_acesso']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemplo@email.com'
            }),
            'nome_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo do usuário'
            }),
            'unidade': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cargo/função do usuário'
            }),
            'tipo_acesso': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'email': 'E-mail *',
            'nome_completo': 'Nome Completo *',
            'unidade': 'Unidade *',
            'cargo': 'Cargo',
            'tipo_acesso': 'Tipo de Acesso *',
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)
        
        # Define choices para tipo_acesso baseado no usuário logado
        if self.request_user and self.request_user.tipo_acesso == 'responsavel':
            self.fields['tipo_acesso'].choices = [
                ('operador', 'Operador'),
                ('responsavel', 'Responsável')
            ]
        else:
            self.fields['tipo_acesso'].choices = [
                ('admin', 'Administrador'),
                ('responsavel', 'Responsável'),
                ('operador', 'Operador')
            ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("O e-mail é obrigatório.")
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email

    def clean_tipo_acesso(self):
        tipo_acesso = self.cleaned_data.get('tipo_acesso')
        
        if (self.request_user and 
            self.request_user.tipo_acesso == 'responsavel' and 
            tipo_acesso == 'admin'):
            raise forms.ValidationError("Responsáveis não podem criar administradores.")
        
        return tipo_acesso

    def save(self, commit=True):
        user = super().save(commit=False)
        # Gera um username automaticamente baseado no email
        if not user.username:
            user.username = user.email.split('@')[0]
            # Garante que o username seja único
            base_username = user.username
            counter = 1
            while CustomUser.objects.filter(username=user.username).exists():
                user.username = f"{base_username}{counter}"
                counter += 1
                
        if commit:
            user.save()
        return user

class CustomUserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['email', 'nome_completo', 'unidade', 'cargo', 'tipo_acesso', 'is_active']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'  # Email não pode ser alterado (é o username)
            }),
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'unidade': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_acesso': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'email': 'E-mail',
            'nome_completo': 'Nome Completo',
            'unidade': 'Unidade',
            'cargo': 'Cargo',
            'tipo_acesso': 'Tipo de Acesso',
            'is_active': 'Usuário Ativo',
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)
        
        if self.request_user and self.request_user.tipo_acesso == 'responsavel':
            self.fields['tipo_acesso'].choices = [
                ('operador', 'Operador'),
                ('responsavel', 'Responsável')
            ]
        else:
            self.fields['tipo_acesso'].choices = [
                ('admin', 'Administrador'),
                ('responsavel', 'Responsável'),
                ('operador', 'Operador')
            ]

    def clean_email(self):
        # Permite edição mas mantém a verificação de unicidade
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email

    def clean_tipo_acesso(self):
        tipo_acesso = self.cleaned_data.get('tipo_acesso')
        
        if (self.request_user and 
            self.request_user.tipo_acesso == 'responsavel' and 
            tipo_acesso == 'admin'):
            raise forms.ValidationError("Responsáveis não podem criar administradores.")
        
        return tipo_acesso

# ✅ NOVO FORM PARA EDIÇÃO DO PRÓPRIO PERFIL (Meu Perfil)
class CustomUserProfileForm(forms.ModelForm):
    """Form simplificado para o usuário editar seu próprio perfil"""
    
    class Meta:
        model = CustomUser
        fields = ['nome_completo', 'email', 'unidade', 'cargo']
        widgets = {
            'nome_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Seu nome completo'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'seu@email.com'
            }),
            'unidade': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Seu cargo/função'
            }),
        }
        labels = {
            'nome_completo': 'Nome Completo',
            'email': 'E-mail',
            'unidade': 'Unidade',
            'cargo': 'Cargo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Torna o email readonly para evitar conflitos
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['email'].help_text = "O e-mail não pode ser alterado."

    def clean_email(self):
        # Mantém o email original, não permite alteração
        return self.instance.email

# ✅ FORM PARA ALTERAÇÃO DE SENHA DO PRÓPRIO USUÁRIO
class CustomPasswordChangeForm(forms.Form):
    senha_atual = forms.CharField(
        label="Senha Atual",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua senha atual'
        }),
        required=True
    )
    
    nova_senha = forms.CharField(
        label="Nova Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a nova senha'
        }),
        min_length=8,
        help_text="A senha deve ter pelo menos 8 caracteres."
    )
    
    confirmar_senha = forms.CharField(
        label="Confirmar Nova Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme a nova senha'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_senha_atual(self):
        senha_atual = self.cleaned_data.get('senha_atual')
        if not self.user.check_password(senha_atual):
            raise forms.ValidationError("A senha atual está incorreta.")
        return senha_atual

    def clean(self):
        cleaned_data = super().clean()
        nova_senha = cleaned_data.get("nova_senha")
        confirmar_senha = cleaned_data.get("confirmar_senha")

        if nova_senha and confirmar_senha and nova_senha != confirmar_senha:
            raise forms.ValidationError("As novas senhas não coincidem.")
        
        return cleaned_data

    def save(self):
        nova_senha = self.cleaned_data.get('nova_senha')
        self.user.set_password(nova_senha)
        self.user.save()

class PasswordResetForm(forms.Form):
    nova_senha = forms.CharField(
        label="Nova Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a nova senha'
        }),
        min_length=8,
        help_text="A senha deve ter pelo menos 8 caracteres."
    )
    confirmar_senha = forms.CharField(
        label="Confirmar Nova Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme a nova senha'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        nova_senha = cleaned_data.get("nova_senha")
        confirmar_senha = cleaned_data.get("confirmar_senha")

        if nova_senha and confirmar_senha and nova_senha != confirmar_senha:
            raise forms.ValidationError("As senhas não coincidem.")
        
        return cleaned_data

# ✅ FORM SIMPLIFICADO para criação rápida de usuários
class QuickUserCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Senha para o novo usuário."
    )

    class Meta:
        model = CustomUser
        fields = ['email', 'nome_completo', 'unidade', 'tipo_acesso']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'unidade': forms.Select(attrs={'class': 'form-select'}),
            'tipo_acesso': forms.Select(attrs={'class': 'form-select'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        # Gera username automaticamente
        if not user.username:
            user.username = user.email.split('@')[0]
            base_username = user.username
            counter = 1
            while CustomUser.objects.filter(username=user.username).exists():
                user.username = f"{base_username}{counter}"
                counter += 1
        if commit:
            user.save()
        return user