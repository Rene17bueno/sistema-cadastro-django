import csv
import json
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import re
import os
import tempfile
import chardet
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.db import models
from .models import Cliente, CustomUser
from .forms import ClienteForm, CustomUserCreationForm, CustomUserEditForm, PasswordResetForm, CustomUserProfileForm, CustomPasswordChangeForm
from django.utils import timezone
from datetime import datetime

# DECORATORS PARA CONTROLE DE ACESSO
def admin_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.tipo_acesso == 'admin',
        login_url='/cadastro/acesso-negado/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def responsavel_ou_admin_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.tipo_acesso in ['admin', 'responsavel'],
        login_url='/cadastro/acesso-negado/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def operador_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.tipo_acesso in ['admin', 'responsavel', 'operador'],
        login_url='/cadastro/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def pode_criar_usuarios_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (
            u.tipo_acesso == 'admin' or 
            (u.tipo_acesso == 'responsavel' and u.has_perm('cadastro.pode_criar_usuarios'))
        ),
        login_url='/cadastro/acesso-negado/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

# VIEWS DE AUTENTICAÇÃO
class CustomLoginView(LoginView):
    template_name = 'cadastro/login.html'
    
    def get_success_url(self):
        return '/cadastro/cadastrar-cliente/'

# VIEW PARA PÁGINA INICIAL DO APP CADASTRO
@login_required
def home(request):
    return redirect('cadastro:cadastrar_cliente')

# =============================================
# VIEWS DE GERENCIAMENTO DE USUÁRIOS - CORRIGIDAS
# =============================================

@login_required
@admin_required
def gerenciar_usuarios(request):
    """Página principal de gerenciamento de usuários"""
    usuarios = CustomUser.objects.all().order_by('-date_joined')
    
    # Estatísticas
    total_usuarios = usuarios.count()
    admins = usuarios.filter(tipo_acesso='admin').count()
    responsaveis = usuarios.filter(tipo_acesso='responsavel').count()
    operadores = usuarios.filter(tipo_acesso='operador').count()
    usuarios_ativos = usuarios.filter(is_active=True).count()
    usuarios_inativos = usuarios.filter(is_active=False).count()
    
    context = {
        'usuarios': usuarios,
        'total_usuarios': total_usuarios,
        'admins': admins,
        'responsaveis': responsaveis,
        'operadores': operadores,
        'usuarios_ativos': usuarios_ativos,
        'usuarios_inativos': usuarios_inativos,
    }
    return render(request, 'cadastro/gerenciar_usuarios.html', context)

@login_required
@admin_required
def listar_usuarios(request):
    """Lista completa de usuários com opções de filtro"""
    usuarios = CustomUser.objects.all().order_by('-date_joined')
    
    # Filtros
    tipo_acesso_filtro = request.GET.get('tipo_acesso', '')
    status_filtro = request.GET.get('status', '')
    
    if tipo_acesso_filtro:
        usuarios = usuarios.filter(tipo_acesso=tipo_acesso_filtro)
    
    if status_filtro:
        if status_filtro == 'ativo':
            usuarios = usuarios.filter(is_active=True)
        elif status_filtro == 'inativo':
            usuarios = usuarios.filter(is_active=False)
    
    context = {
        'usuarios': usuarios,
        'tipo_acesso_filtro': tipo_acesso_filtro,
        'status_filtro': status_filtro,
    }
    return render(request, 'cadastro/listar_usuarios.html', context)

@login_required
def criar_usuario(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        form.request_user = request.user
        
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.criado_por = request.user
            usuario.save()
            
            messages.success(request, f'Usuário {usuario.nome_completo} criado com sucesso!')
            return redirect('cadastro:gerenciar_usuarios')
    else:
        form = CustomUserCreationForm()
        if request.user.tipo_acesso == 'responsavel':
            form.fields['tipo_acesso'].choices = [('operador', 'Operador')]
    
    context = {
        'form': form,
        'pode_criar_admin': request.user.tipo_acesso == 'admin'
    }
    return render(request, 'cadastro/criar_usuario.html', context)

@login_required
def editar_usuario(request, usuario_id):
    usuario = get_object_or_404(CustomUser, id=usuario_id)
    
    if (request.user.tipo_acesso == 'responsavel' and 
        usuario.unidade != request.user.unidade and 
        usuario.criado_por != request.user):
        messages.error(request, 'Você não tem permissão para editar este usuário.')
        return redirect('cadastro:gerenciar_usuarios')
    
    if request.method == 'POST':
        form = CustomUserEditForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuário {usuario.nome_completo} atualizado com sucesso!')
            return redirect('cadastro:gerenciar_usuarios')
    else:
        form = CustomUserEditForm(instance=usuario)
        if request.user.tipo_acesso == 'responsavel':
            form.fields['tipo_acesso'].choices = [
                ('responsavel', 'Responsável'),
                ('operador', 'Operador')
            ]
    
    context = {'form': form, 'usuario': usuario}
    return render(request, 'cadastro/editar_usuario.html', context)

@login_required
@admin_required
def ativar_desativar_usuario(request, usuario_id):
    """Ativar/desativar usuário"""
    usuario = get_object_or_404(CustomUser, id=usuario_id)
    
    if request.method == 'POST':
        usuario.is_active = not usuario.is_active
        usuario.save()
        
        acao = "ativado" if usuario.is_active else "desativado"
        messages.success(request, f'Usuário {usuario.nome_completo} {acao} com sucesso!')
    
    return redirect('cadastro:gerenciar_usuarios')

@login_required
@admin_required
def alterar_tipo_acesso(request, usuario_id):
    """Alterar tipo de acesso do usuário"""
    usuario = get_object_or_404(CustomUser, id=usuario_id)
    
    if request.method == 'POST':
        novo_tipo = request.POST.get('tipo_acesso')
        if novo_tipo in ['admin', 'responsavel', 'operador']:
            usuario.tipo_acesso = novo_tipo
            usuario.save()
            messages.success(request, f'Tipo de acesso de {usuario.nome_completo} alterado para {novo_tipo.title()}!')
    
    return redirect('cadastro:gerenciar_usuarios')

@login_required
@admin_required
def excluir_usuario(request, usuario_id):
    """Excluir usuário"""
    usuario = get_object_or_404(CustomUser, id=usuario_id)
    
    if request.method == 'POST':
        if usuario.id == request.user.id:
            messages.error(request, 'Você não pode excluir sua própria conta!')
        else:
            nome_usuario = usuario.nome_completo
            usuario.delete()
            messages.success(request, f'Usuário {nome_usuario} excluído com sucesso!')
    
    return redirect('cadastro:gerenciar_usuarios')

@login_required
def redefinir_senha(request, usuario_id):
    usuario = get_object_or_404(CustomUser, id=usuario_id)
    
    if (request.user.tipo_acesso == 'responsavel' and 
        usuario.unidade != request.user.unidade and 
        usuario.criado_por != request.user):
        messages.error(request, 'Você não tem permissão para redefinir senha deste usuário.')
        return redirect('cadastro:gerenciar_usuarios')
    
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            nova_senha = form.cleaned_data['nova_senha']
            usuario.set_password(nova_senha)
            usuario.save()
            
            messages.success(request, f'Senha do usuário {usuario.nome_completo} redefinida com sucesso!')
            return redirect('cadastro:gerenciar_usuarios')
    else:
        form = PasswordResetForm()
    
    context = {'form': form, 'usuario': usuario}
    return render(request, 'cadastro/redefinir_senha.html', context)

# =============================================
# VIEW MEU PERFIL - ATUALIZADA
# =============================================

@login_required
def meu_perfil(request):
    usuario = request.user
    
    if request.method == 'POST':
        # Verifica se é alteração de senha
        if 'alterar_senha' in request.POST:
            senha_form = CustomPasswordChangeForm(usuario, request.POST)
            perfil_form = CustomUserProfileForm(instance=usuario)
            
            if senha_form.is_valid():
                senha_form.save()
                messages.success(request, 'Senha alterada com sucesso!')
                return redirect('cadastro:meu_perfil')
        else:
            # É alteração de perfil normal
            perfil_form = CustomUserProfileForm(request.POST, instance=usuario)
            senha_form = CustomPasswordChangeForm(usuario)
            
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, 'Perfil atualizado com sucesso!')
                return redirect('cadastro:meu_perfil')
    else:
        perfil_form = CustomUserProfileForm(instance=usuario)
        senha_form = CustomPasswordChangeForm(usuario)
    
    context = {
        'perfil_form': perfil_form,
        'senha_form': senha_form,
        'usuario': usuario
    }
    return render(request, 'cadastro/meu_perfil.html', context)

@login_required
def acesso_negado(request):
    return render(request, 'cadastro/acesso_negado.html')

# =============================================
# VIEWS EXISTENTES (PROTEGIDAS)
# =============================================

@login_required
@operador_required
def cadastrar_cliente(request):
    unidade_atual = request.POST.get('unidade', '')
    data_atual = request.POST.get('data_cadastro', '')
    
    if not data_atual:
        data_atual = timezone.now().strftime('%Y-%m-%d')
    
    clientes = Cliente.objects.none()
    
    total_clientes = Cliente.objects.count()
    hoje = timezone.now().date()
    clientes_hoje = Cliente.objects.filter(data_cadastro=hoje).count()
    
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form = ClienteForm(request.POST)
            if form.is_valid():
                cliente = form.save()
                return JsonResponse({
                    'success': True,
                    'message': f'Cliente {cliente.codigo_cliente} cadastrado com sucesso!'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
        
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, f'Cliente {cliente.codigo_cliente} cadastrado com sucesso!')
            
            unidade_atual = cliente.unidade
            data_atual = cliente.data_cadastro.strftime('%Y-%m-%d')
            
            form = ClienteForm(initial={
                'unidade': unidade_atual,
                'data_cadastro': data_atual
            })
        else:
            messages.error(request, 'Erro ao cadastrar cliente. Verifique os dados.')
    else:
        form = ClienteForm(initial={
            'data_cadastro': timezone.now().strftime('%Y-%m-%d')
        })
    
    return render(request, 'cadastro/cadastro.html', {
        'form': form,
        'clientes': clientes,
        'unidade_atual': unidade_atual,
        'data_atual': data_atual,
        'total_clientes': total_clientes,
        'clientes_hoje': clientes_hoje
    })

@login_required
@responsavel_ou_admin_required
def novos_clientes(request):
    context = {}
    
    if request.method == 'POST' and request.FILES.get('arquivo_csv'):
        arquivo_csv = request.FILES['arquivo_csv']
        
        try:
            resultado = processar_clientes_csv(arquivo_csv)
            
            if resultado:
                with open(resultado['caminho_arquivo'], 'rb') as f:
                    response = HttpResponse(f.read(), content_type='text/plain')
                    response['Content-Disposition'] = f'attachment; filename="{resultado["nome_arquivo"]}"'
                
                messages.success(request, f'Arquivo processado com sucesso! {resultado["registros_processados"]} registros.')
                
                os.remove(resultado['caminho_arquivo'])
                
                return response
            else:
                messages.error(request, 'Erro ao processar o arquivo.')
                
        except Exception as e:
            messages.error(request, f'Erro: {str(e)}')
    
    return render(request, 'cadastro/novos_clientes.html', context)

@login_required
@operador_required
def exportar_dados(request):
    unidade_filtro = request.GET.get('unidade', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    formato = request.GET.get('formato', '')
    
    clientes = Cliente.objects.all().order_by('-data_cadastro')
    
    if unidade_filtro:
        clientes = clientes.filter(unidade=unidade_filtro)
    
    if data_inicio:
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            clientes = clientes.filter(data_cadastro__gte=data_inicio_obj)
        except ValueError:
            pass
    
    if data_fim:
        try:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
            clientes = clientes.filter(data_cadastro__lte=data_fim_obj)
        except ValueError:
            pass
    
    if formato:
        if formato == 'excel':
            return exportar_excel(clientes, unidade_filtro)
        elif formato == 'csv':
            return exportar_csv(clientes, unidade_filtro)
        elif formato == 'pdf':
            return exportar_pdf(clientes, unidade_filtro)
        elif formato == 'txt':
            return exportar_txt(clientes, unidade_filtro)
        else:
            return HttpResponseBadRequest(f"Formato de exportação '{formato}' não suportado.")
    
    context = {
        'unidade_selecionada': unidade_filtro,
        'data_inicio_selecionada': data_inicio,
        'data_fim_selecionada': data_fim,
        'clientes_filtrados': clientes,
        'total_registros': clientes.count(),
        'unidades': ['Maringá', 'Guarapuava', 'Ponta Grossa', 'Norte Pioneiro']
    }
    
    return render(request, 'cadastro/exportar.html', context)

# =============================================
# APIs (PROTEGIDAS)
# =============================================

@login_required
@require_http_methods(["GET"])
def lista_clientes(request):
    unidade_filtro = request.GET.get('unidade', '')
    data_filtro = request.GET.get('data', '')
    
    clientes = Cliente.objects.all().order_by('-id')
    
    if unidade_filtro:
        clientes = clientes.filter(unidade=unidade_filtro)
    
    if data_filtro:
        try:
            data_obj = datetime.strptime(data_filtro, '%Y-%m-%d').date()
            clientes = clientes.filter(data_cadastro=data_obj)
        except ValueError:
            pass
    
    data = []
    for cliente in clientes:
        data.append({
            'id': cliente.id,
            'unidade': cliente.unidade,
            'codigo_cliente': cliente.codigo_cliente,
            'latitude': str(cliente.latitude),
            'longitude': str(cliente.longitude),
            'data_cadastro': cliente.data_cadastro.strftime('%Y-%m-%d'),
        })
    
    return JsonResponse({'clientes': data})

@login_required
@require_http_methods(["GET"])
def detalhe_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    data = {
        'id': cliente.id,
        'unidade': cliente.unidade,
        'codigo_cliente': cliente.codigo_cliente,
        'latitude': str(cliente.latitude),
        'longitude': str(cliente.longitude),
        'data_cadastro': cliente.data_cadastro.strftime('%Y-%m-%d'),
    }
    
    return JsonResponse(data)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    try:
        data = json.loads(request.body)
        form = ClienteForm(data, instance=cliente)
        
        if form.is_valid():
            cliente = form.save()
            return JsonResponse({
                'success': True,
                'message': f'Cliente {cliente.codigo_cliente} atualizado com sucesso!',
                'cliente': {
                    'id': cliente.id,
                    'unidade': cliente.unidade,
                    'codigo_cliente': cliente.codigo_cliente,
                    'latitude': str(cliente.latitude),
                    'longitude': str(cliente.longitude),
                    'data_cadastro': cliente.data_cadastro.strftime('%Y-%m-%d'),
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def excluir_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    try:
        codigo_cliente = cliente.codigo_cliente
        cliente.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Cliente {codigo_cliente} excluído com sucesso!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def validar_cliente(request):
    try:
        data = json.loads(request.body)
        form = ClienteForm(data)
        
        if form.is_valid():
            return JsonResponse({
                'valid': True,
                'message': 'Dados válidos!'
            })
        else:
            return JsonResponse({
                'valid': False,
                'errors': form.errors
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'error': str(e)
        }, status=500)

# =============================================
# FUNÇÕES AUXILIARES
# =============================================

def processar_clientes_csv(arquivo_csv):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            for chunk in arquivo_csv.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        with open(temp_path, 'rb') as f:
            raw_data = f.read()
            encoding_result = chardet.detect(raw_data)
            file_encoding = encoding_result['encoding'] or 'latin1'
        
        print(f"Encoding detectado: {file_encoding}")
        
        encodings_to_try = [file_encoding, 'latin1', 'iso-8859-1', 'cp1252', 'utf-8']
        
        geo = None
        for encoding in encodings_to_try:
            try:
                print(f"Tentando ler com encoding: {encoding}")
                geo = pd.read_csv(temp_path, sep=';', encoding=encoding)
                print(f"Sucesso com encoding: {encoding}")
                break
            except UnicodeDecodeError as e:
                print(f"Falha com {encoding}: {e}")
                continue
            except Exception as e:
                print(f"Erro com {encoding}: {e}")
                continue
        
        os.unlink(temp_path)
        
        if geo is None:
            print("Nao foi possível ler o arquivo com nenhum encoding")
            return None
        
        print(f"Colunas encontradas: {list(geo.columns)}")
        if not geo.empty:
            print(f"Primeira linha - Filial: {geo.iloc[0]['Filial']}, Cliente: {geo.iloc[0]['Cliente']}, Coordenadas: {geo.iloc[0]['Coordenadas']}")
        
        filial_mapping = {
            '0001': 'Maringá',
            '0002': 'Guarapuava', 
            '0003': 'Ponta_Grossa',
            '0004': 'Norte_Pioneiro',
            '1': 'Maringá',
            '2': 'Guarapuava',
            '3': 'Ponta_Grossa',
            '4': 'Norte_Pioneiro'
        }
        
        geo['Filial'] = geo['Filial'].astype(str).str.strip()
        geo['Filial_Nome'] = geo['Filial'].map(filial_mapping)
        
        geo['Cliente_Codigo'] = geo['Cliente'].astype(str).str.strip()
        
        resultados = []
        
        for index, row in geo.iterrows():
            try:
                coordenadas = str(row['Coordenadas']).strip()
                cliente_codigo = row['Cliente_Codigo']
                filial_nome = row['Filial_Nome']
                
                data_col = None
                for col in geo.columns:
                    if 'data' in col.lower() or 'inclus' in col.lower():
                        data_col = col
                        break
                
                data_inclusao = row[data_col] if data_col else 'Data não encontrada'
                
                if (not coordenadas or coordenadas == 'nan' or 
                    '000,000000' in coordenadas or coordenadas == '0' or
                    pd.isna(filial_nome) or pd.isna(cliente_codigo)):
                    continue
                
                coord_sem_espacos = coordenadas.replace(' ', '')
                
                partes = coord_sem_espacos.split(',')
                
                if len(partes) >= 4:
                    lat_parte1 = partes[0]
                    lat_parte2 = partes[1]
                    
                    lon_parte1 = partes[2]
                    lon_parte2 = partes[3]
                    
                    latitude = re.sub(r'^(-)0+', r'\1', lat_parte1) + '.' + lat_parte2
                    
                    longitude = re.sub(r'^(-)0+', r'\1', lon_parte1) + '.' + lon_parte2
                    
                    resultados.append({
                        'cliente': cliente_codigo,
                        'latitude': latitude,
                        'longitude': longitude,
                        'filial': filial_nome,
                        'data_inclusao': data_inclusao
                    })
                    print(f"Processado: {cliente_codigo} -> {latitude}, {longitude}")
                    
            except Exception as e:
                print(f"Erro na linha {index}: {e}")
                continue
        
        if not resultados:
            print("Nenhum registro válido encontrado")
            return None
        
        print(f"Total de registros processados: {len(resultados)}")
        
        filial = resultados[0]['filial']
        data_inclusao = resultados[0]['data_inclusao']
        
        try:
            data_obj = datetime.strptime(data_inclusao, '%d/%m/%Y')
            data_formatada = data_obj.strftime('%d-%m-%Y')
        except Exception as e:
            print(f"Erro ao converter data '{data_inclusao}': {e}")
            data_formatada = datetime.now().strftime('%d-%m-%Y')
        
        nome_arquivo = f"{filial}-{data_formatada}.txt"
        
        temp_dir = tempfile.gettempdir()
        caminho_arquivo = os.path.join(temp_dir, nome_arquivo)
        
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            for resultado in resultados:
                linha = f"{resultado['cliente']};{resultado['latitude']};{resultado['longitude']}\n"
                f.write(linha)
        
        print(f"Arquivo gerado: {nome_arquivo} com {len(resultados)} registros")
        
        return {
            'caminho_arquivo': caminho_arquivo,
            'nome_arquivo': nome_arquivo,
            'registros_processados': len(resultados)
        }
        
    except Exception as e:
        print(f"Erro geral no processamento: {e}")
        import traceback
        traceback.print_exc()
        return None

# =============================================
# FUNÇÕES DE EXPORTAÇÃO
# =============================================

def exportar_excel(clientes, unidade_filtro):
    if unidade_filtro:
        filename = f"geolocalizacao-{unidade_filtro.lower()}-{timezone.now().strftime('%d-%m-%Y')}.xlsx"
    else:
        filename = f"geolocalizacao-todas-unidades-{timezone.now().strftime('%d-%m-%Y')}.xlsx"
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clientes Geolocalização"
    
    headers = ['ID', 'Unidade', 'Código Cliente', 'Latitude', 'Longitude', 'Data Cadastro']
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    
    for row_num, cliente in enumerate(clientes, 2):
        ws.cell(row=row_num, column=1, value=cliente.id)
        ws.cell(row=row_num, column=2, value=cliente.unidade)
        ws.cell(row=row_num, column=3, value=cliente.codigo_cliente)
        ws.cell(row=row_num, column=4, value=str(cliente.latitude))
        ws.cell(row=row_num, column=5, value=str(cliente.longitude))
        ws.cell(row=row_num, column=6, value=cliente.data_cadastro.strftime('%d/%m/%Y'))
    
    column_widths = {
        'A': 8,   # ID
        'B': 15,  # Unidade
        'C': 18,  # Código Cliente
        'D': 20,  # Latitude
        'E': 20,  # Longitude
        'F': 12   # Data Cadastro
    }
    
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width
    
    ws.freeze_panes = 'A2'
    
    if len(clientes) > 0:
        ws.auto_filter.ref = f"A1:F{len(clientes) + 1}"
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb.save(response)
    
    return response

def exportar_csv(clientes, unidade_filtro):
    if unidade_filtro:
        filename = f"{unidade_filtro.lower()}-{timezone.now().strftime('%d-%m-%Y')}.csv"
    else:
        filename = f"todas-unidades-{timezone.now().strftime('%d-%m-%Y')}.csv"
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    response.write('ID,Unidade,Código Cliente,Latitude,Longitude,Data Cadastro\n')
    
    for cliente in clientes:
        linha = f"{cliente.id},{cliente.unidade},{cliente.codigo_cliente},{cliente.latitude},{cliente.longitude},{cliente.data_cadastro.strftime('%d/%m/%Y')}\n"
        response.write(linha)
    
    return response

def exportar_pdf(clientes, unidade_filtro):
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from io import BytesIO
        
        if unidade_filtro:
            filename = f"geolocalizacao-{unidade_filtro.lower()}-{timezone.now().strftime('%d-%m-%Y')}.pdf"
        else:
            filename = f"geolocalizacao-todas-unidades-{timezone.now().strftime('%d-%m-%Y')}.pdf"
        
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=1,
            textColor=colors.HexColor('#366092')
        )
        
        if unidade_filtro:
            title_text = f"Relatório de Geolocalização - {unidade_filtro}"
        else:
            title_text = "Relatório de Geolocalização - Todas as Unidades"
            
        title = Paragraph(title_text, title_style)
        elements.append(title)
        
        date_style = ParagraphStyle(
            'CustomDate',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=20,
            alignment=1,
        )
        date_text = f"Emitido em: {timezone.now().strftime('%d/%m/%Y às %H:%M')}"
        date_para = Paragraph(date_text, date_style)
        elements.append(date_para)
        
        elements.append(Spacer(1, 0.2*inch))
        
        data = [['Código Cliente', 'Latitude', 'Longitude', 'Unidade', 'Data Cadastro']]
        
        for cliente in clientes:
            data.append([
                str(cliente.codigo_cliente),
                f"{cliente.latitude:.10f}" if cliente.latitude else "N/A",
                f"{cliente.longitude:.10f}" if cliente.longitude else "N/A",
                cliente.unidade,
                cliente.data_cadastro.strftime('%d/%m/%Y')
            ])
        
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        
        elements.append(Spacer(1, 0.3*inch))
        footer_style = ParagraphStyle(
            'CustomFooter',
            parent=styles['Normal'],
            fontSize=9,
            alignment=1,
        )
        footer_text = f"Total de registros: {len(clientes)}"
        footer = Paragraph(footer_text, footer_style)
        elements.append(footer)
        
        doc.build(elements)
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except ImportError:
        return HttpResponseBadRequest(
            "Biblioteca ReportLab não instalada. Execute: pip install reportlab"
        )
    except Exception as e:
        return HttpResponseBadRequest(f"Erro ao gerar PDF: {str(e)}")

def exportar_txt(clientes, unidade_filtro):
    if unidade_filtro:
        filename = f"{unidade_filtro.lower()}-{timezone.now().strftime('%d-%m-%Y')}.txt"
    else:
        filename = f"todas-unidades-{timezone.now().strftime('%d-%m-%Y')}.txt"
    
    response = HttpResponse(content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    for cliente in clientes:
        latitude = f"{cliente.latitude:.15f}".rstrip('0').rstrip('.') if cliente.latitude else "0"
        longitude = f"{cliente.longitude:.15f}".rstrip('0').rstrip('.') if cliente.longitude else "0"
        
        linha = f"{cliente.codigo_cliente};{latitude};{longitude}\n"
        response.write(linha)
    
    return response