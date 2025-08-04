# -*- coding: utf-8 -*-
# Remodelações e Pinturas - Aplicação Flask com Firebase Firestore
#
# Este script cria uma aplicação web usando o framework Flask e o Firebase Firestore.
# A aplicação tem duas rotas: a página inicial com um formulário de pedido
# e um painel de administração protegido por palavra-passe para visualizar,
# aceitar e apagar os pedidos submetidos.
#
# Para executar, guarde o código como um ficheiro .py e instale as dependências:
#   pip install Flask firebase-admin
#
# Depois, execute no terminal:
#   python nome_do_seu_ficheiro.py
#
# A aplicação estará disponível em http://127.0.0.1:5000/
#
# INSTRUÇÕES DE CONFIGURAÇÃO DO FIREBASE:
# 1. Crie um projeto no Firebase Console (https://console.firebase.google.com/).
# 2. Ative o Firestore no modo nativo.
# 3. Vá a "Configurações do Projeto" -> "Contas de Serviço" -> "Gerir todas as chaves privadas de conta de serviço".
# 4. Crie uma nova chave privada em formato JSON.
# 5. Guarde o ficheiro JSON na mesma pasta que este script e renomeie-o para 'firebase-service-account.json'.

import os
import json
import base64
import webbrowser
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, session, make_response
import firebase_admin
from firebase_admin import credentials, firestore

# ==================== INICIALIZAÇÃO DO FIREBASE ====================
# Certifique-se de que o ficheiro 'firebase-service-account.json' está na mesma pasta.
cred = credentials.Certificate('firebase-service-account.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# ==================== INICIALIZAÇÃO DO FLASK ====================
app = Flask(__name__)
# A chave secreta é necessária para usar sessões (para a autenticação do admin)
app.secret_key = os.urandom(24)

# Palavra-passe simples para o admin.
# AVISO: NÃO USE ISTO EM PRODUÇÃO. Apenas para fins de demonstração.
ADMIN_PASSWORD = "admin"


# ==================== Templates HTML ====================
# Os templates são definidos como strings para manter o código num único ficheiro.
# A diferença agora é que os loops para o admin panel irão usar dados do Firestore.

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PROBUILDER</title>
    <!-- Favicon para a aba do navegador, idealmente uma imagem quadrada de 32x32 pixels para evitar distorção -->
    <link rel="icon" href="{{ url_for('static', filename='logo_sem_fun.png') }}" type="image/png">
    <!-- Ícone para dispositivos móveis (Apple touch icon) -->
    <link rel="apple-touch-icon" href="{{ url_for('static', filename='logo_sem_fun.png') }}">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #ffffff;
            color: #1f2937;
        }
        .container {
            max-width: 900px;
        }
    </style>
</head>
<body class="bg-white min-h-screen flex flex-col items-center">
    <!-- Header -->
    <header class="w-full bg-white text-indigo-900 shadow-lg">
        <div class="container mx-auto p-4 flex justify-center items-center">
            <!-- Logo centralizado -->
            <a href="/" class="rounded-lg px-2 py-1">
                <img src="/static/logo_sem_fun.png" alt="Logo PROBUILDER" class="h-40">
            </a>
        </div>
    </header>

    <!-- Hero Section -->
    <main class="w-full">
        <section class="bg-indigo-600 text-white py-24 text-center shadow-inner">
            <div class="container mx-auto px-4">
                <h1 class="text-5xl md:text-6xl font-extrabold mb-4 animate-pulse">Transforme a Sua Casa</h1>
                <p class="text-xl md:text-2xl font-light mb-8">Serviços de remodelação e pintura de alta qualidade.</p>
                <a href="#solicitar" class="bg-yellow-400 text-indigo-900 font-bold py-3 px-8 rounded-full text-lg shadow-xl hover:bg-yellow-300 transition-all duration-300 transform hover:scale-105">
                    Comece Já!
                </a>
            </div>
        </section>

        <!-- Services Section -->
        <section class="py-16 bg-white shadow-md">
            <div class="container mx-auto px-4 text-center">
                <h2 class="text-4xl font-bold mb-12 text-gray-800">Nossos Serviços</h2>
                <div class="grid md:grid-cols-2 gap-8">
                    <a href="/remodelacao" class="p-6 bg-gray-50 rounded-xl shadow-lg border border-gray-200 transform hover:scale-105 transition-transform duration-300">
                        <h3 class="text-2xl font-semibold text-indigo-700 mb-2">Remodelação</h3>
                        <p class="text-gray-600">Desde pequenas remodelações a projetos completos, fazemos o seu sonho de casa tornar-se realidade.</p>
                    </a>
                    <a href="/pintura" class="p-6 bg-gray-50 rounded-xl shadow-lg border border-gray-200 transform hover:scale-105 transition-transform duration-300">
                        <h3 class="text-2xl font-semibold text-indigo-700 mb-2">Pintura</h3>
                        <p class="text-gray-600">Acabamentos perfeitos para interiores e exteriores, com uma vasta gama de cores e texturas.</p>
                    </a>
                </div>
            </div>
        </section>

        <!-- Quote Request Section -->
        <section id="solicitar" class="py-20 bg-white">
            <div class="container mx-auto px-4">
                <h2 class="text-4xl font-bold text-center text-gray-800 mb-10">Solicite um Orçamento</h2>
                <div class="bg-white p-8 md:p-12 rounded-3xl shadow-2xl border border-gray-200 max-w-2xl mx-auto">
                    {% if message %}
                        <div class="mb-4 p-4 rounded-xl bg-green-100 text-green-700 border border-green-200 fade-in">
                            <p class="font-semibold">{{ message }}</p>
                        </div>
                    {% endif %}
                    <form action="/" method="post" class="space-y-6">
                        <div>
                            <label for="service" class="block text-sm font-medium text-gray-700">Tipo de Serviço</label>
                            <select id="service" name="service" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-3">
                                <option value="pintura">Pintura</option>
                                <option value="remodelacao">Remodelação</option>
                                <option value="ambos">Ambos</option>
                            </select>
                        </div>
                        <div>
                            <label for="description" class="block text-sm font-medium text-gray-700">Detalhes do Projeto</label>
                            <textarea id="description" name="description" rows="4" required placeholder="Descreva o seu projeto em detalhe: número de divisões, área em m², estado atual, etc." class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-3"></textarea>
                        </div>
                        <div>
                            <label for="contact_name" class="block text-sm font-medium text-gray-700">Nome</label>
                            <input type="text" id="contact_name" name="contact_name" required placeholder="O seu nome" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-3">
                        </div>
                        <div>
                            <label for="contact_email" class="block text-sm font-medium text-gray-700">Email</label>
                            <input type="email" id="contact_email" name="contact_email" required placeholder="o-seu-email@exemplo.com" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-3">
                        </div>
                        
                        <div class="flex justify-center">
                            <button type="submit" class="w-full md:w-auto bg-indigo-600 text-white font-bold py-3 px-6 rounded-full shadow-lg hover:bg-indigo-700 transition-colors duration-300">
                                Enviar Pedido
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="w-full bg-gray-800 text-white py-6 mt-auto shadow-inner">
        <div class="container mx-auto px-4 text-center">
            <p>&copy; 2025 PROBUILDER. Todos os direitos reservados.</p>
        </div>
    </footer>
</body>
</html>
"""

REMODELACAO_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PROBUILDER</title>
    <!-- Favicon para a aba do navegador, idealmente uma imagem quadrada de 32x32 pixels para evitar distorção -->
    <link rel="icon" href="{{ url_for('static', filename='logo_sem_fun.png') }}" type="image/png">
    <!-- Ícone para dispositivos móveis (Apple touch icon) -->
    <link rel="apple-touch-icon" href="{{ url_for('static', filename='logo_sem_fun.png') }}">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #ffffff;
            color: #1f2937;
        }
        .container {
            max-width: 900px;
        }
    </style>
</head>
<body class="bg-white min-h-screen flex flex-col items-center">
    <!-- Header -->
    <header class="w-full bg-white text-indigo-900 shadow-lg">
        <div class="container mx-auto p-4 flex justify-between items-center">
            <a href="/" class="rounded-lg px-2 py-1">
                <img src="/static/logo_sem_fun.png" alt="Logo PROBUILDER" class="h-40">
            </a>
            <nav>
                <a href="/" class="text-lg font-medium text-indigo-900 hover:text-indigo-600 transition-colors">Voltar</a>
            </nav>
        </div>
    </header>

    <main class="container mx-auto px-4 py-12">
        <h1 class="text-4xl font-bold text-center text-indigo-800 mb-8">Remodelações</h1>
        
        <div class="bg-white p-8 rounded-3xl shadow-2xl border border-gray-200">
            <p class="text-gray-700 text-lg mb-6 leading-relaxed">
                Transforme o seu espaço. Desde a conceção inicial à execução final, a nossa equipa especializada cuida de todos os detalhes para criar a casa dos seus sonhos. Trabalhamos com materiais de alta qualidade e com um foco inabalável na atenção ao detalhe, para garantir que o resultado final excede as suas expectativas.
            </p>
            <p class="text-gray-700 text-lg mb-8 leading-relaxed">
                Seja uma remodelação de cozinha, casa de banho ou uma renovação completa de todo o apartamento, estamos prontos para assumir o desafio.
            </p>

            <div class="grid md:grid-cols-2 gap-8">
                <div class="flex flex-col items-center">
                    <h3 class="text-xl font-semibold text-gray-800 mb-4">Antes</h3>
                    <!-- Exemplo de como usar a função url_for para ir buscar imagens de uma pasta -->
                    <!-- Basta alterar 'imagem1.jpg' para o nome da sua foto real -->
                    <img src="{{ url_for('static', filename='remodelacoes/antes/imagem1.jpg') }}" alt="Imagem Antes da Remodelação" class="rounded-xl shadow-md" />
                </div>
                <div class="flex flex-col items-center">
                    <h3 class="text-xl font-semibold text-gray-800 mb-4">Depois</h3>
                    <!-- Exemplo de como usar a função url_for para ir buscar imagens de uma pasta -->
                    <!-- Basta alterar 'imagem2.jpg' para o nome da sua foto real -->
                    <img src="{{ url_for('static', filename='remodelacoes/depois/imagem2.jpg') }}" alt="Imagem Depois da Remodelação" class="rounded-xl shadow-md" />
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="w-full bg-gray-800 text-white py-6 mt-auto shadow-inner">
        <div class="container mx-auto px-4 text-center">
            <p>&copy; 2025 PROBUILDER. Todos os direitos reservados.</p>
        </div>
    </footer>
</body>
</html>
"""

PINTURA_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PROBUILDER</title>
    <!-- Favicon para a aba do navegador, idealmente uma imagem quadrada de 32x32 pixels para evitar distorção -->
    <link rel="icon" href="{{ url_for('static', filename='logo_sem_fun.png') }}" type="image/png">
    <!-- Ícone para dispositivos móveis (Apple touch icon) -->
    <link rel="apple-touch-icon" href="{{ url_for('static', filename='logo_sem_fun.png') }}">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #ffffff;
            color: #1f2937;
        }
        .container {
            max-width: 900px;
        }
    </style>
</head>
<body class="bg-white min-h-screen flex flex-col items-center">
    <!-- Header -->
    <header class="w-full bg-white text-indigo-900 shadow-lg">
        <div class="container mx-auto p-4 flex justify-between items-center">
            <a href="/" class="rounded-lg px-2 py-1">
                <img src="/static/logo_sem_fun.png" alt="Logo PROBUILDER" class="h-40">
            </a>
            <nav>
                <a href="/" class="text-lg font-medium text-indigo-900 hover:text-indigo-600 transition-colors">Voltar</a>
            </nav>
        </div>
    </header>

    <main class="container mx-auto px-4 py-12">
        <h1 class="text-4xl font-bold text-center text-indigo-800 mb-8">Serviços de Pintura</h1>
        
        <div class="bg-white p-8 rounded-3xl shadow-2xl border border-gray-200">
            <p class="text-gray-700 text-lg mb-6 leading-relaxed">
                Dê uma nova vida às suas paredes com a nossa vasta gama de cores e acabamentos de alta qualidade. Oferecemos pintura interior e exterior, garantindo um trabalho limpo e um resultado impecável. Utilizamos tintas de alta durabilidade e técnicas de aplicação profissionais para um acabamento perfeito e duradouro.
            </p>
            <p class="text-gray-700 text-lg mb-8 leading-relaxed">
                Quer se trate de uma única divisão ou de toda a casa, a nossa equipa está pronta para transformar o seu espaço com cor.
            </p>

            <div class="grid md:grid-cols-2 gap-8">
                <div class="flex flex-col items-center">
                    <h3 class="text-xl font-semibold text-gray-800 mb-4">Antes</h3>
                    <!-- Exemplo de como usar a função url_for para ir buscar imagens de uma pasta -->
                    <!-- Basta alterar 'imagem3.jpg' para o nome da sua foto real -->
                    <img src="{{ url_for('static', filename='pintura/antes/imagem3.jpg') }}" alt="Imagem Antes da Pintura" class="rounded-xl shadow-md" />
                </div>
                <div class="flex flex-col items-center">
                    <h3 class="text-xl font-semibold text-gray-800 mb-4">Depois</h3>
                    <!-- Exemplo de como usar a função url_for para ir buscar imagens de uma pasta -->
                    <!-- Basta alterar 'imagem4.jpg' para o nome da sua foto real -->
                    <img src="{{ url_for('static', filename='pintura/depois/imagem4.jpg') }}" alt="Imagem Depois da Pintura" class="rounded-xl shadow-md" />
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="w-full bg-gray-800 text-white py-6 mt-auto shadow-inner">
        <div class="container mx-auto px-4 text-center">
            <p>&copy; 2025 PROBUILDER. Todos os direitos reservados.</p>
        </div>
    </footer>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PROBUILDER - Admin</title>
    <!-- Favicon para a aba do navegador, idealmente uma imagem quadrada de 32x32 pixels para evitar distorção -->
    <link rel="icon" href="{{ url_for('static', filename='logo_sem_fun.png') }}" type="image/png">
    <!-- Ícone para dispositivos móveis (Apple touch icon) -->
    <link rel="apple-touch-icon" href="{{ url_for('static', filename='logo_sem_fun.png') }}">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #ffffff;
            color: #1f2937;
        }
        .container {
            max-width: 900px;
        }
        .preview-image {
            max-width: 100%;
            max-height: 200px;
            object-fit: contain;
            border-radius: 8px;
            margin-top: 10px;
            display: block;
        }
    </style>
</head>
<body class="bg-white min-h-screen flex flex-col items-center">
    <!-- Header -->
    <header class="w-full bg-white text-indigo-900 shadow-lg">
        <div class="container mx-auto p-4 flex justify-between items-center">
            <!-- Logo centralizado -->
            <a href="/" class="rounded-lg px-2 py-1">
                <img src="/static/logo_sem_fun.png" alt="Logo PROBUILDER" class="h-40">
            </a>
            <nav>
                <a href="/" class="text-lg font-medium hover:text-indigo-600 transition-colors">Home</a>
                <a href="/logout" class="ml-4 text-lg font-medium hover:text-indigo-600 transition-colors">Terminar Sessão</a>
            </nav>
        </div>
    </header>

    <main class="container mx-auto px-4 py-8">
        <h1 class="text-4xl font-bold text-center text-gray-800 mb-8">Painel de Administração</h1>

        {% if not authenticated %}
            <div class="bg-white p-8 rounded-3xl shadow-2xl max-w-md mx-auto">
                <form action="/admin" method="post" class="space-y-4">
                    <div class="text-center">
                        <label for="password" class="block text-lg font-medium text-gray-700">Palavra-passe de Admin</label>
                        <input type="password" id="password" name="password" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-3">
                        {% if error %}
                            <p class="mt-2 text-sm text-red-600">{{ error }}</p>
                        {% endif %}
                    </div>
                    <div class="flex justify-center">
                        <button type="submit" class="w-full bg-indigo-600 text-white font-bold py-3 px-6 rounded-full shadow-lg hover:bg-indigo-700 transition-colors duration-300">
                            Entrar
                        </button>
                    </div>
                </form>
            </div>
        {% else %}
            <div class="bg-white p-8 rounded-3xl shadow-2xl">
                <h2 class="text-2xl font-bold text-gray-800 mb-4">Pedidos de Orçamento</h2>
                {% if requests %}
                    <div class="space-y-6">
                    {% for req in requests %}
                        <div class="p-6 bg-gray-50 rounded-xl shadow-inner border border-gray-200">
                            <h3 class="text-xl font-semibold text-indigo-700">Pedido #{{ loop.index }}</h3>
                            <p class="text-gray-600 mt-2"><strong>Nome:</strong> {{ req.contact_name }}</p>
                            <p class="text-gray-600"><strong>Email:</strong> {{ req.contact_email }}</p>
                            <p class="text-gray-600"><strong>Serviço:</strong> {{ req.service }}</p>
                            <p class="text-gray-600"><strong>Descrição:</strong> {{ req.description }}</p>
                            {% if req.project_image_data %}
                                <p class="text-gray-600"><strong>Imagem:</strong> <a href="{{ url_for('serve_image', image_id=loop.index0) }}" target="_blank" class="text-indigo-500 hover:underline">Ver Imagem</a></p>
                            {% endif %}
                            <p class="text-gray-600"><strong>Estado:</strong> <span class="font-bold text-{{ 'green' if req.status == 'Aceite' else 'yellow' }}-600">{{ req.status }}</span></p>
                            <p class="text-gray-600 text-sm mt-2"><strong>Submetido em:</strong> {{ req.timestamp }}</p>
                            
                            <!-- Botões de Ação -->
                            <div class="flex space-x-4 mt-4">
                                <form action="{{ url_for('accept_request', doc_id=req.id) }}" method="post">
                                    <button type="submit" class="bg-green-500 text-white font-bold py-2 px-4 rounded-full shadow-lg hover:bg-green-600 transition-colors duration-300">
                                        Aceitar Pedido
                                    </button>
                                </form>
                                <form action="{{ url_for('delete_request', doc_id=req.id) }}" method="post">
                                    <button type="submit" class="bg-red-500 text-white font-bold py-2 px-4 rounded-full shadow-lg hover:bg-red-600 transition-colors duration-300">
                                        Excluir Pedido
                                    </button>
                                </form>
                            </div>
                        </div>
                    {% endfor %}
                    </div>
                {% else %}
                    <p class="text-gray-500">Nenhum pedido de orçamento submetido ainda.</p>
                {% endif %}
            </div>
        {% endif %}
    </main>

    <!-- Footer -->
    <footer class="w-full bg-gray-800 text-white py-6 mt-auto shadow-inner">
        <div class="container mx-auto px-4 text-center">
            <p>&copy; 2025 PROBUILDER. Todos os direitos reservados.</p>
        </div>
    </footer>
</body>
</html>
"""

# ==================== Rotas da Aplicação ====================

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Rota principal da aplicação.
    - Método GET: Mostra o formulário para submeter um pedido.
    - Método POST: Processa os dados do formulário e guarda o pedido no Firestore.
    """
    message = None
    if request.method == "POST":
        # Processa a submissão do formulário
        contact_name = request.form.get("contact_name")
        contact_email = request.form.get("contact_email")
        service = request.form.get("service")
        description = request.form.get("description")
        
        # Cria um dicionário com os dados do pedido
        new_request = {
            "contact_name": contact_name,
            "contact_email": contact_email,
            "service": service,
            "description": description,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Pendente"
        }
        
        # Adiciona o pedido à coleção 'requests' no Firestore
        db.collection('requests').add(new_request)
        message = "Obrigado! O seu pedido de orçamento foi enviado com sucesso. Entraremos em contacto brevemente."

    return render_template_string(INDEX_TEMPLATE, message=message)

@app.route("/remodelacao")
def remodelacao():
    """
    Rota para a página de detalhes do serviço de remodelação.
    """
    return render_template_string(REMODELACAO_TEMPLATE)

@app.route("/pintura")
def pintura():
    """
    Rota para a página de detalhes do serviço de pintura.
    """
    return render_template_string(PINTURA_TEMPLATE)


@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    """
    Rota para o painel de administração.
    - Requer uma palavra-passe para aceder.
    - Uma vez autenticado, mostra a lista de pedidos do Firestore.
    """
    authenticated = session.get("authenticated", False)
    error = None
    requests_list = []

    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["authenticated"] = True
            authenticated = True
            # Redireciona para evitar re-submissão do formulário
            return redirect(url_for("admin_panel"))
        else:
            error = "Palavra-passe incorreta."
            authenticated = False

    if authenticated:
        # Se autenticado, obtém os pedidos do Firestore e adiciona o ID do documento
        requests_ref = db.collection('requests').stream()
        for doc in requests_ref:
            request_data = doc.to_dict()
            request_data['id'] = doc.id
            requests_list.append(request_data)
        
    return render_template_string(ADMIN_TEMPLATE, authenticated=authenticated, requests=requests_list, error=error)

@app.route("/logout")
def logout():
    """
    Rota para terminar a sessão do administrador.
    """
    session.pop("authenticated", None)
    return redirect(url_for("admin_panel"))

@app.route("/accept_request/<string:doc_id>", methods=["POST"])
def accept_request(doc_id):
    """
    Rota para aceitar um pedido.
    - Apenas funciona se o admin estiver autenticado.
    - Altera o estado do pedido no Firestore para 'Aceite'.
    """
    if session.get("authenticated"):
        doc_ref = db.collection('requests').document(doc_id)
        doc_ref.update({'status': 'Aceite'})
    return redirect(url_for("admin_panel"))

@app.route("/delete_request/<string:doc_id>", methods=["POST"])
def delete_request(doc_id):
    """
    Rota para excluir um pedido.
    - Apenas funciona se o admin estiver autenticado.
    - Remove o pedido do Firestore.
    """
    if session.get("authenticated"):
        db.collection('requests').document(doc_id).delete()
    return redirect(url_for("admin_panel"))


if __name__ == "__main__":
    # URL da sua aplicação
    url = "http://127.0.0.1:5000"
    
    # Abrir o URL no navegador padrão automaticamente
    webbrowser.open(url)
    
    # Inicia a aplicação Flask
    app.run(debug=True)
