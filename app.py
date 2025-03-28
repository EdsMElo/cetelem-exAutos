from flask import Flask, render_template, jsonify, request, session
from legal_scraper import LegalScraper
import logging
import uuid
from datetime import datetime, timedelta
import threading
from flask_session import Session
import os
import tempfile
from flask_cors import CORS
from scraper_store import scrapers, scrapers_lock
from database import DatabaseManager
import atexit
from fraudeCheck.routes import fraude_bp
from config import DEBUG_ENABLED, CustomFilter, get_logger
from werkzeug.serving import WSGIRequestHandler

# Configurar logging - usar o logger do config.py
logger = get_logger(__name__)

# Configurar o logger do Werkzeug - já configurado no config.py
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(CustomFilter())

app = Flask(__name__)

# Configuração do CORS
CORS(app, 
     supports_credentials=True,
     resources={
         r"/*": {
             "origins": ["http://localhost:7860"],
             "methods": ["GET", "POST", "OPTIONS"],
             "allow_headers": ["Content-Type"],
             "expose_headers": ["Set-Cookie"],
         }
     })

# Configuração da sessão
app.config.update(
    SECRET_KEY='your-secret-key-here',  # Chave fixa para desenvolvimento
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR=os.path.join(tempfile.gettempdir(), 'flask_session'),
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),  # Aumentado para 8 horas
    SESSION_COOKIE_NAME='scraper_session',
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_PATH='/'
)

# Inicializa a extensão de sessão
Session(app)

# Variável para controlar o thread de verificação de sessão
session_checker_thread = None
session_checker_running = True

# Inicializa o gerenciador de banco de dados
db_manager = DatabaseManager()

def check_sessions():
    """Thread para verificar periodicamente as sessões ativas"""
    while session_checker_running:
        with scrapers_lock:
            current_time = datetime.now()
            sessions_to_remove = []
            
            for user_id, scraper_data in scrapers.items():
                # Se a última atividade foi há mais de 30 minutos
                if (current_time - scraper_data['last_activity']) > timedelta(minutes=30):
                    try:
                        logger.info(f"Removendo sessão inativa {user_id}")
                        scraper = scraper_data['scraper']
                        if hasattr(scraper, 'driver'):
                            scraper.driver.quit()
                        sessions_to_remove.append(user_id)
                    except Exception as e:
                        logger.error(f"Erro ao limpar sessão {user_id}: {str(e)}")
                else:
                    # Verifica se o scraper ainda está ativo
                    try:
                        scraper = scraper_data['scraper']
                        if hasattr(scraper, 'driver'):
                            # Tenta acessar uma propriedade do driver para verificar se está ativo
                            _ = scraper.driver.current_url
                    except Exception as e:
                        logger.error(f"Sessão {user_id} inválida, será removida: {str(e)}")
                        sessions_to_remove.append(user_id)
            
            # Remove as sessões inválidas
            for user_id in sessions_to_remove:
                del scrapers[user_id]
        
        # Aguarda 5 minutos antes da próxima verificação
        threading.Event().wait(300)

@app.route('/')
def index():
    return render_template('index.html')

@app.before_request
def before_request():
    # Log da requisição
    logger.debug(f"Recebida requisição para {request.path}")
    logger.debug(f"Session ID atual: {session.get('user_id')}")
    logger.debug(f"Cookies da requisição: {request.cookies}")
    logger.debug(f"Scrapers ativos: {list(scrapers.keys())}")
    
    # Gera um ID de sessão se não existir
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        logger.info(f"Novo Session ID gerado: {session['user_id']}")
    
    # Atualiza timestamp da última atividade
    user_id = session['user_id']
    with scrapers_lock:
        if user_id in scrapers:
            scrapers[user_id]['last_activity'] = datetime.now()
            logger.debug(f"Atualizado timestamp da sessão {user_id}")

@app.route('/api/initialize', methods=['POST'])
def initialize():
    try:
        user_id = session['user_id']
        logger.info(f"Inicializando scraper para sessão {user_id}")
        logger.debug(f"Scrapers antes da inicialização: {list(scrapers.keys())}")
        
        with scrapers_lock:
            # Verifica se já existe um scraper ativo e válido para esta sessão
            if user_id in scrapers:
                try:
                    existing_scraper = scrapers[user_id]['scraper']
                    if hasattr(existing_scraper, 'driver'):
                        # Tenta acessar uma propriedade do driver para verificar se está ativo
                        _ = existing_scraper.driver.current_url
                        # Se chegou aqui, o scraper está ativo e válido
                        scrapers[user_id]['last_activity'] = datetime.now()
                        logger.debug(f"Scraper existente ainda válido para sessão {user_id}")
                        return jsonify({
                            'status': 'success',
                            'message': 'Scraper já inicializado e válido'
                        })
                except Exception as e:
                    logger.error(f"Scraper existente inválido: {str(e)}")
                    # Se chegou aqui, o scraper está inválido e precisamos criar um novo
                    try:
                        if hasattr(existing_scraper, 'driver'):
                            existing_scraper.driver.quit()
                    except:
                        pass
                    del scrapers[user_id]
            
            # Cria novo scraper
            logger.debug(f"Criando novo scraper para sessão {user_id}")
            scraper = LegalScraper(headless=True)
            
            try:
                # Inicializa o scraper
                scraper.initialize()
                
                # Armazena o scraper no dicionário
                scrapers[user_id] = {
                    'scraper': scraper,
                    'last_activity': datetime.now()
                }
                
                logger.debug(f"Scraper inicializado com sucesso para sessão {user_id}")
                logger.debug(f"Scrapers após inicialização: {list(scrapers.keys())}")
                
                return jsonify({
                    'status': 'success',
                    'message': 'Inicialização bem-sucedida'
                })
                
            except Exception as e:
                logger.error(f"Erro ao inicializar scraper: {str(e)}")
                if hasattr(scraper, 'driver'):
                    try:
                        scraper.driver.quit()
                    except:
                        pass
                raise
                
    except Exception as e:
        logger.error(f"Erro durante a inicialização: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Erro durante a inicialização: {str(e)}'
        }), 500

@app.route('/api/extract', methods=['POST'])
def extract():
    try:
        logger.debug(f"Recebida requisição de extração. Session ID: {session.get('user_id')}")
        logger.debug(f"Dados da requisição: {request.json}")
        logger.debug(f"Scrapers ativos no momento da extração: {list(scrapers.keys())}")
        
        # Verifica se há um ID de sessão
        if 'user_id' not in session:
            logger.error("Sessão não encontrada")
            return jsonify({
                'status': 'error',
                'message': 'Sessão não encontrada. Por favor, recarregue a página.'
            }), 401
        
        user_id = session['user_id']
        logger.debug(f"Verificando scraper para sessão {user_id}")
        
        # Verifica se existe um scraper para esta sessão
        with scrapers_lock:
            if user_id not in scrapers:
                logger.error(f"Scraper não encontrado para sessão {user_id}")
                return jsonify({
                    'status': 'error',
                    'message': 'Sessão expirada. Por favor, recarregue a página.'
                }), 401
            
            # Atualiza o timestamp de última atividade
            scrapers[user_id]['last_activity'] = datetime.now()
            scraper = scrapers[user_id]['scraper']
            logger.debug(f"Scraper encontrado para sessão {user_id}")
        
        # Limpa os dados anteriores
        all_results = []
        session['process_details'] = {}
        session['grid_data'] = []
        logger.debug("Dados anteriores limpos com sucesso")
        
        # Extrai os dados da requisição
        data = request.json
        process_numbers = data.get('process_numbers', [])
        data_inicial = data.get('data_inicial', '')
        data_final = data.get('data_final', '')
        status = data.get('status', 'Todos')
        acordo = data.get('acordo', 'Todos')
        suspeita_fraude = data.get('suspeita_fraude', 'Todos')
        
        # Se não houver números de processo, faz uma busca geral
        if not process_numbers:
            process_numbers = ['']
        
        # Realiza a extração
        for process_number in process_numbers:
            try:
                logger.debug(f"Iniciando busca do processo {process_number}")
                results = scraper.search_processes(
                    process_number=process_number,
                    start_date=data_inicial if data_inicial else None,
                    end_date=data_final if data_final else None,
                    status='-1' if status == 'Todos' else status,
                    acordo=None if acordo == 'Todos' else acordo,
                    suspeita_fraude=None if suspeita_fraude == 'Todos' else suspeita_fraude
                )
                
                # Debug dos resultados
                logger.debug(f"Resultado bruto da busca: {results}")
                
                # Se a busca retornou resultados, processa e formata
                if results:
                    if isinstance(results, dict):
                        # Salva grid_data na sessão
                        if 'grid_data' in results:
                            session['grid_data'] = results['grid_data']
                        
                        # Converte resultado único em lista
                        results = [results]
                    
                    # Processa cada resultado
                    for result in results:
                        if 'raw_data' in result:
                            for process_id, process_data in result['raw_data'].items():

                                acordo_details = []
                                if process_data.get('detalhes_acordo'):
                                    acordo = process_data.get('detalhes_acordo', [])
                                    acordo_details = [{
                                        'id':process_id,
                                        'valor': acordo.get('valor', ''),
                                        'status': acordo.get('status', ''),
                                        'data_pagamento': acordo.get('data_pagamento', ''),
                                        'nome_titular': acordo.get('nome_titular', ''),
                                        'cpf_titular': acordo.get('cpf_titular', ''),
                                        'cpf_cnpj_titular': acordo.get('cpf_cnpj_titular', ''),
                                        'is_acordo': acordo.get('is_acordo', False),
                                        'suspeita_fraude': acordo.get('suspeita_fraude', False),
                                        'documentos': acordo.get('documentos', []),
                                        'historico': acordo.get('historico', [])
                                    }]

                                formatted_result = {
                                    'processo': {
                                        'id': process_id,
                                        'numero': process_data.get('processo').get('numero'),
                                        'escritorio': process_data['processo'].get('escritorio_celula', ''),
                                        'comarca': process_data['processo'].get('comarca', ''),
                                        'estado': process_data['processo'].get('estado', ''),
                                        'status': process_data['processo'].get('status', ''),
                                        'fase': process_data['processo'].get('fase', '')
                                    },
                                    'partes': process_data.get('partes', {}),
                                    'acordo': acordo_details
                                }
                                all_results.append(formatted_result)
                        else:
                            all_results.append(result)
                        
                logger.debug(f"Processo {process_number} extraído com sucesso")
                logger.debug(f"Resultados encontrados: {len(all_results)}")
                
            except Exception as e:
                logger.error(f"Erro ao extrair processo {process_number}: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f'Erro ao extrair processo {process_number}: {str(e)}'
                }), 500
        
        # Debug da resposta final
        response_data = {
            'status': 'success',
            'data': all_results if all_results else [],
            'grid_data': session.get('grid_data', []) if session else []
        }
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Erro geral na extração: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Erro na extração: {str(e)}'
        }), 500

@app.route('/api/healthcheck', methods=['GET'])
def healthcheck():
    """Endpoint para verificar o status da sessão"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'status': 'invalid', 'message': 'Sessão não encontrada'})
        
        with scrapers_lock:
            if user_id not in scrapers:
                return jsonify({'status': 'invalid', 'message': 'Scraper não inicializado'})
            
            scraper_data = scrapers[user_id]
            scraper = scraper_data['scraper']
            
            try:
                if hasattr(scraper, 'driver'):
                    # Tenta acessar uma propriedade do driver para verificar se está ativo
                    _ = scraper.driver.current_url
                    scraper_data['last_activity'] = datetime.now()
                    return jsonify({'status': 'active', 'message': 'Sessão ativa'})
                else:
                    return jsonify({'status': 'invalid', 'message': 'Driver não inicializado'})
            except Exception as e:
                return jsonify({'status': 'invalid', 'message': f'Erro na sessão: {str(e)}'})
                
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/config/debug', methods=['POST'])
def toggle_debug():
    try:
        data = request.get_json()
        if 'enabled' not in data:
            return jsonify({
                'status': 'error',
                'message': 'O parâmetro enabled é obrigatório'
            }), 400

        # Atualiza a configuração de debug
        global DEBUG_ENABLED
        DEBUG_ENABLED = data['enabled']
        
        return jsonify({
            'status': 'success',
            'message': f'Modo debug {"ativado" if DEBUG_ENABLED else "desativado"}'
        })
    except Exception as e:
        logger.error(f"Erro ao atualizar configuração de debug: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Erro ao atualizar configuração de debug: {str(e)}'
        }), 500

@app.after_request
def after_request(response):
    # Log da resposta
    logger.info(f"Enviando resposta com status {response.status_code}")
    logger.info(f"Cookies da resposta: {response.headers.get('Set-Cookie')}")
    return response

@app.teardown_appcontext
def cleanup_session(exception=None):
    """Limpa recursos quando a aplicação é encerrada"""
    try:
        if 'user_id' in session:
            user_id = session['user_id']
            with scrapers_lock:
                if user_id in scrapers:
                    try:
                        if scrapers[user_id]['scraper'].driver:
                            scrapers[user_id]['scraper'].driver.quit()
                    except:
                        pass
                    del scrapers[user_id]
    except:
        pass

def start_session_checker():
    """Inicia o thread de verificação de sessões"""
    global session_checker_thread
    if session_checker_thread is None:
        session_checker_thread = threading.Thread(target=check_sessions, daemon=True)
        session_checker_thread.start()

@atexit.register
def stop_session_checker():
    """Para o thread de verificação de sessões quando a aplicação é encerrada"""
    global session_checker_running
    session_checker_running = False

# Inicia o verificador de sessões quando a aplicação iniciar
start_session_checker()

# Registrar o blueprint do módulo de fraude antes do if __name__ == '__main__'
app.register_blueprint(fraude_bp)

if __name__ == '__main__':
    app.run(debug=True, port=7860)
