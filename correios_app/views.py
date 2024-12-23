import requests
from termcolor import colored
from datetime import datetime, timedelta
import os
from django.shortcuts import render, redirect
from django.http import JsonResponse

# Função para obter o token de autorização e salvar em um arquivo
def obter_token_autorizacao(usuario, senha):
    url_login = "https://api.grupohne.com.br/api/login"  # URL de login
    dados_login = {
        "usuario": usuario,  
        "password": senha     
    }

    headers = {
        "Content-Type": "application/json" 
    }

    try:
        # Realiza a requisição de login
        response = requests.post(url_login, headers=headers, json=dados_login)

        if response.ok:
            data = response.json()
            if "token" in data:
                token = data["token"]
                print("Token obtido com sucesso.")
                # Salva o token
                with open("token.txt", "w", encoding="utf-8") as token_file:
                    token_file.write(token)
                return token
            else:
                print("Token não encontrado na resposta.")
                return None
        else:
            print(f"Erro ao fazer login: {response.status_code}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisição: {e}")
        return None

# Função para ler o token de um arquivo
def ler_token_do_arquivo():
    if os.path.exists("token.txt"):
        with open("token.txt", "r", encoding="utf-8") as token_file:
            return token_file.read().strip()
    else:
        return None

# Função para fazer a requisição ao endpoint e filtrar os dados com a nota 'EMITIDA'
def enviar_livros(token, unidade, data_inicial, data_final):
    url = "https://api.grupohne.com.br/api/v1/aluno/enviar-livros?page=1&pageSize=10"
    headers = {
        "Authorization": f"Bearer {token}",  
        "Content-Type": "application/json"   
    }

    payload = {
        "filtro": {
            "tipo": "pacsedex",
            "tipo_curso": "",
            "cidade": "",
            "unidade": unidade,  # Unidade baseada no Centro de Custo
            "status_inscricao": "",
            "material_entrega": {"pac": True, "sedex": True},
            "data_inicial": data_inicial,  # API espera no formato yyyy-mm-dd
            "data_final": data_final       # API espera no formato yyyy-mm-dd
        },
        "page": 1,
        "pageSize": 10
    }

    # Enviar requisição POST
    response = requests.post(url, json=payload, headers=headers)

    # Verificar se a requisição foi bem-sucedida
    if response.status_code == 200:
        data = response.json()
        
        # Filtrar os itens com "nota" == "EMITIDA" e coletar ID, Nome e Curso
        ids_nomes_cursos_emitidos = [(item['id'], item['nome'], item.get('curso', 'Curso não disponível')) for item in data['data'] if item['nota'] == "EMITIDA"]
        
        return ids_nomes_cursos_emitidos
    else:
        return []

# Função para enviar os IDs para o endpoint de exportação e salvar o arquivo CSV
# Importa a função exportar_correios para usar nela
def exportar_correios(token, ids):
    url = "https://api.grupohne.com.br/api/v1/aluno/exportar_correios"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "ids": ids
    }

    # Enviar requisição POST para exportar os correios
    response = requests.post(url, json=payload, headers=headers)

    # Verificar se a requisição foi bem-sucedida
    if response.status_code == 200:
        # Obter a data de hoje no formato ddmmaaaa para nomear o arquivo
        data_hoje = datetime.today().strftime("%d%m%Y")
        
        # O conteúdo da resposta será em formato CSV
        linhas = response.content.decode('utf-8').splitlines()
        
        if len(linhas) > 1:
            # Verificar se a pasta 'EXPORTADOS' existe, caso contrário, criar
            pasta_exportados = 'EXPORTADOS'
            if not os.path.exists(pasta_exportados):
                os.makedirs(pasta_exportados)  # Cria a pasta

            # Caminho completo do arquivo
            caminho_arquivo = os.path.join(pasta_exportados, f"CORREIOS_{data_hoje}.csv")
            
            # Ignorar a primeira linha e escrever o restante no arquivo
            with open(caminho_arquivo, "wb") as f:
                # Definir o cabeçalho
                cabecalho = "SERVICO;DESTINATARIO;CEP;LOGRADOURO;NUMERO;COMPLEMENTO;BAIRRO;EMAIL;;;CPF/CNPJ;VALOR_DECLARADO;;TIPO_OBJETO;;;;;AR;MP;;;OBSERVACAO\n"
                f.write(cabecalho.encode('utf-8'))
                
                # Escrever todas as linhas, ignorando a primeira
                for linha in linhas[1:]:
                    f.write(linha.encode('utf-8') + b"\n")
        
            return JsonResponse({"message": f"Arquivo CSV exportado com sucesso como '{caminho_arquivo}'."})
        else:
            return JsonResponse({"message": "Resposta da API não contém dados válidos."}, status=400)
    else:
        return JsonResponse({"message": f"Erro ao exportar correios: {response.status_code}"}, status=500)


# Função que será chamada quando o usuário clicar em "exportar"
def exportar(request):
    if request.method == "POST":
        # Recuperar token e IDs do request POST (como um exemplo)
        token = request.POST.get('token')
        ids = request.POST.getlist('ids')  # Lista de IDs
        
        # Verificar se o token e os IDs estão presentes
        if not token or not ids:
            return JsonResponse({"message": "Token ou IDs não fornecidos."}, status=400)

        # Chamar a função de exportação
        return exportar_correios(token, ids)
    
    return JsonResponse({"message": "Método não permitido."}, status=405)

# Função para o login
def login_view(request):
    if request.method == "POST":
        usuario = request.POST["usuario"]
        senha = request.POST["senha"]

        # Aqui você deve adicionar sua lógica de autenticação
        token = obter_token_autorizacao(usuario, senha)

        if token:
            # Salve o token no session ou em outro lugar se necessário
            request.session['token'] = token  # Salva o token na sessão, por exemplo
            return redirect('home')  # Redireciona para a página principal após login bem-sucedido
        else:
            return render(request, 'login.html', {'erro': 'Credenciais inválidas'})

    return render(request, 'login.html')  # Exibe a página de login

# Função de logoff
def logout_view(request):
    # Remove o token da sessão
    if 'token' in request.session:
        del request.session['token']
    return redirect('login')  # Redireciona para a página de login

# Função para a página principal
def home(request):
    token = request.session.get('token', None)

    if not token:
        return redirect('login')  # Se não houver token, redireciona para login

    if request.method == "POST":
        centro_custo = request.POST.get("centro_custo")
        data_inicial = request.POST.get("data_inicial")
        data_final = request.POST.get("data_final")

        # Verifique se os campos de data foram fornecidos
        if not data_inicial or not data_final:
            return JsonResponse({"error": "Data inicial e/ou data final não fornecidas."}, status=400)

        unidade = []
        if centro_custo == "BH":
            unidade = [29, 27, 18, 1, 30, 19, 20, 28, 12, 7, 8, 21, 22, 10, 25, 4, 26, 9, 11, 23, 13, 24]
        elif centro_custo == "GO":
            unidade = [14]
        elif centro_custo == "ES":
            unidade = [3]
        else:
            return JsonResponse({"error": "Centro de Custo inválido"}, status=400)

        # Converter as datas de string para datetime
        try:
            data_inicial_api = datetime.strptime(data_inicial, "%Y-%m-%d").strftime("%Y-%m-%d")
            data_final_api = datetime.strptime(data_final, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return JsonResponse({"error": "Formato de data inválido"}, status=400)

        # Chamar a função para enviar os livros e filtrar os resultados
        ids_nomes_cursos_emitidos = enviar_livros(token, unidade, data_inicial_api, data_final_api)

        if ids_nomes_cursos_emitidos:
            return render(request, "home.html", {"ids_nomes_cursos_emitidos": ids_nomes_cursos_emitidos})

        return JsonResponse({"message": "Nenhum ID encontrado para envio."}, status=404)

    return render(request, "home.html")