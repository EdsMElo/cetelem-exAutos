from flask import Flask, render_template, request, jsonify, url_for
from legal_scraper import LegalScraper
import logging
import os
import shutil
from datetime import datetime, timedelta
import random

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure static directories exist
static_dir = os.path.join(os.path.dirname(__file__), 'static')
images_dir = os.path.join(static_dir, 'images')
os.makedirs(images_dir, exist_ok=True)

# Move favicon if it doesn't exist in static folder
favicon_source = os.path.join(os.path.dirname(__file__), 'templates', 'images', 'favicon.png')
favicon_dest = os.path.join(images_dir, 'favicon.png')
if os.path.exists(favicon_source) and not os.path.exists(favicon_dest):
    shutil.copy2(favicon_source, favicon_dest)

# Ensure the screenshots and logs directories exist
for dir_path in ['screenshots', 'html_logs']:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# Variável global para manter a instância do scraper
scraper = None

def generate_test_data():
    """Gera dados simulados para teste que correspondem exatamente à estrutura real"""
    status_options = ["Ativo", "Suspenso", "Encerrado", "Em Recurso"]
    escritorios = ["LUCHESI", "FARO", "FARO-SP", "FARO-RJ", "QUEIROZ"]
    tipos_processo = ["Busca e Apreensão", "Execução", "Monitória", "Conhecimento"]
    raw_data = {}
    grid_data = []
    
    for i in range(10):
        # Gera dados básicos do processo
        data_base = datetime.now() - timedelta(days=random.randint(0, 365))
        processo_id = str(random.randint(100000, 999999))
        numero_processo = f"{random.randint(1000000, 9999999)}-{random.randint(10, 99)}.{random.randint(2020, 2024)}.8.26.0100"
        
        # Gera CPF/CNPJ aleatório
        cpf = f"{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)}-{random.randint(10, 99)}"
        
        # Dados para o grid (mantendo a ordem exata das colunas)
        row_data = [
            processo_id,              # ID do processo
            numero_processo,          # Número do Processo
            f"Adverso Teste {i+1}",   # Adverso
            cpf,                      # CPF/CNPJ
            f"Comarca {i+1}",         # Comarca
            "SP",                     # Estado
            random.choice(tipos_processo),  # Tipo
            random.choice(status_options),  # Status
            random.choice(escritorios)      # Escritório
        ]
        grid_data.append(row_data)
        
        # Dados brutos detalhados
        raw_data[processo_id] = {
            'processo': {
                'numero': numero_processo,
                'escritorio_celula': row_data[8],  # Escritório
                'comarca': row_data[4],  # Comarca
                'estado': row_data[5],   # Estado
                'status': row_data[7],   # Status
                'fase': "Em Andamento",
                'tipo': row_data[6],     # Tipo
                'valor_causa': random.randint(10000, 100000),
                'data_distribuicao': data_base.strftime("%d/%m/%Y")
            },
            'partes': {
                'parte_interessada': "Banco Cetelem",
                'parte_adversa': row_data[2],  # Nome do Adverso
                'cpf_cnpj_parte_adverso': row_data[3],  # CPF/CNPJ
                'advogados_adversos': [
                    {
                        'nome': f"Advogado Adverso {j+1}",
                        'oab': f"OAB/SP {random.randint(10000, 99999)}",
                        'fonte': 'accordion'
                    }
                    for j in range(random.randint(1, 3))
                ],
                'polo_ativo': [
                    {
                        'nome': "Banco Cetelem",
                        'tipo': "Autor"
                    }
                ],
                'polo_passivo': [
                    {
                        'nome': row_data[2],  # Nome do Adverso
                        'tipo': "Réu"
                    }
                ],
                'terceiros_interessados': [],
                'advogado_interno': f"Advogado Interno {random.randint(1, 5)}"
            },
            'financeiro': {
                'lancamentos': [
                    {
                        'classificacao': random.choice(['CUSTAS', 'HONORÁRIOS', 'ACORDO']),
                        'tipo_lancamento': random.choice(['ACORDO', 'CUSTAS', 'HONORÁRIOS', 'DEPÓSITO']),
                        'valor': str(random.randint(1000, 10000)),
                        'natureza': random.choice(['CRÉDITO', 'DÉBITO']),
                        'data_pagamento': (data_base + timedelta(days=random.randint(1, 30))).strftime("%d/%m/%Y"),
                        'usuario_cadastro': f"Usuario {random.randint(1, 5)}"
                    }
                    for j in range(random.randint(2, 5))
                ],
                'resumo': {
                    'total_debito': str(random.randint(5000, 15000)),
                    'total_credito': str(random.randint(15000, 25000)),
                    'saldo': str(random.randint(-5000, 5000))
                }
            },
            'detalhes_acordo': [
                {
                    'nome_titular': row_data[2],  # Nome do Adverso
                    'cpf_titular': row_data[3],  # CPF/CNPJ
                    'valor_acordo': f"R$ {random.randint(10000, 50000)},00",
                    'forma_pagamento': random.choice(['À Vista', 'Parcelado'])
                }
                for _ in range(random.randint(0, 2)) if random.random() < 0.7  # 70% de chance de ter acordo
            ],
            'movimentacoes': [
                {
                    'data': (data_base + timedelta(days=idx)).strftime("%d/%m/%Y"),
                    'descricao': f"Movimentação {idx+1}",
                    'tipo': random.choice([
                        "DESPACHO",
                        "DECISÃO",
                        "SENTENÇA",
                        "PETIÇÃO",
                        "CERTIDÃO"
                    ])
                }
                for idx in range(random.randint(5, 10))
            ]
        }
    
    return {
        "raw_data": raw_data,
        "grid_data": grid_data
    }

@app.route('/')
def index():
    global scraper
    try:
        # Inicializa o scraper se ainda não existir
        if scraper is None:
            scraper = LegalScraper(headless=True)
            scraper.initialize()
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Erro ao inicializar o scraper: {str(e)}")
        return render_template('index.html', error="Erro ao inicializar o sistema")

@app.route('/api/initialize', methods=['POST'])
def initialize():
    global scraper
    try:
        if scraper is None:
            logger.info("Iniciando novo scraper...")
            scraper = LegalScraper()
            logger.info("Chrome iniciado com sucesso")
            
            logger.info("Configurando Selenium...")
            scraper.initialize()
            logger.info("Selenium configurado com sucesso")
            
            logger.info("Realizando login...")
            if not scraper.ensure_logged_in():
                raise Exception("Falha ao realizar login")
            logger.info("Login realizado com sucesso")
        
        return jsonify({
            'status': 'success',
            'message': 'Sistema inicializado com sucesso'
        })
    except Exception as e:
        logger.error(f"Erro durante a inicialização: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/extract', methods=['POST'])
def extract():
    try:
        if scraper is None:
            return jsonify({
                'success': False,
                'message': 'Sistema não inicializado'
            }), 500

        if not scraper.ensure_logged_in():
            return jsonify({
                'success': False,
                'message': 'Sessão expirada. Por favor, recarregue a página.'
            }), 401

        process_numbers = request.json.get('process_numbers', [])
        if not process_numbers:
            return jsonify({
                'success': False,
                'message': 'Nenhum número de processo fornecido'
            }), 400

        # Busca os processos usando o método correto
        data = scraper.search_processes(process_number=process_numbers[0])
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Erro durante a extração: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/stop', methods=['POST'])
def stop_extraction():
    global scraper
    try:
        if scraper:
            scraper.stop_extraction()
        return jsonify({"status": "success", "message": "Extração interrompida"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/screenshots')
def get_screenshots():
    try:
        screenshots_dir = os.path.join(os.getcwd(), 'screenshots')
        screenshots = []
        
        if os.path.exists(screenshots_dir):
            for file in os.listdir(screenshots_dir):
                if file.endswith(('.png', '.jpg', '.jpeg')):
                    screenshots.append({
                        'filename': file,
                        'url': f'/screenshots/{file}',
                        'timestamp': datetime.fromtimestamp(os.path.getctime(os.path.join(screenshots_dir, file))).strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
        return jsonify({
            'success': True,
            'screenshots': sorted(screenshots, key=lambda x: x['timestamp'], reverse=True)
        })
        
    except Exception as e:
        logger.error(f"Error getting screenshots: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting screenshots: {str(e)}"
        })

if __name__ == '__main__':
    app.run(debug=True, port=7860)
