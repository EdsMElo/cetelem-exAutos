from flask import Blueprint, jsonify, request, render_template, Response
from datetime import datetime
import logging
from .service import FraudeService
from .fraud_recertification import FraudRecertificationService
import os
import getpass

# Configurar logging
logger = logging.getLogger(__name__)

# Criar o Blueprint para o módulo de fraude
fraude_bp = Blueprint('fraude', __name__, 
                     url_prefix='/fraudeCheck',
                     template_folder='templates')

@fraude_bp.route('/')
def index():
    """Rota principal do módulo de avaliação de fraude"""
    return render_template('fraude_check.html')

@fraude_bp.route('/api/search', methods=['POST'])
def search():
    try:
        filters = request.json
        service = FraudeService()
        results = service.get_processos_suspeitos(filters)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Erro na busca: {str(e)}")
        return jsonify({'error': str(e)}), 500

@fraude_bp.route('/api/details/<string:id>')
def get_details(id):
    """Obtém os detalhes de um processo específico"""
    try:
        service = FraudeService()
        processo = service.get_processo_by_id(id)
        
        if not processo:
            return jsonify({'error': 'Processo não encontrado'}), 404
        
        return jsonify(processo)
    
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do processo: {str(e)}")
        return jsonify({'error': 'Erro ao buscar detalhes'}), 500

@fraude_bp.route('/api/assessment/<string:external_id>', methods=['POST'])
def save_assessment(external_id):
    try:
        assessment_data = request.json
        service = FraudeService()
        result = service.save_assessment(external_id, assessment_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Erro ao salvar avaliação: {str(e)}")
        return jsonify({'error': str(e)}), 500

@fraude_bp.route('/api/assessment/<string:id>/history')
def get_assessment_history(id):
    """Obtém o histórico de avaliações de um processo"""
    try:
        service = FraudeService()
        historico = service.get_historico_avaliacoes(id)
        return jsonify(historico)
    
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {str(e)}")
        return jsonify({'error': 'Erro ao buscar histórico'}), 500

@fraude_bp.route('/api/export/<format>')
def export(format):
    """Exporta os dados em diferentes formatos"""
    try:
        service = FraudeService()
        
        # Mapeia o formato para o content type correto
        content_type_map = {
            'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'csv': 'text/csv',
            'word': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        
        if format not in content_type_map:
            return jsonify({'error': 'Formato inválido'}), 400
            
        # Gera o arquivo
        output = service.export_data(format)
        
        if not output:
            return jsonify({'error': 'Nenhum dado para exportar'}), 404
            
        # Define o nome do arquivo baseado no formato
        filename_map = {
            'excel': 'avaliacoes_fraude.xlsx',
            'csv': 'avaliacoes_fraude.csv',
            'word': 'avaliacoes_fraude.docx'
        }
        
        # Retorna o arquivo
        return Response(
            output,
            mimetype=content_type_map[format],
            headers={
                'Content-Disposition': f'attachment; filename={filename_map[format]}'
            }
        )
        
    except Exception as e:
        print(f'Erro ao exportar: {str(e)}')
        return jsonify({'error': str(e)}), 500

@fraude_bp.route('/api/current_user')
def get_current_user():
    """Retorna o usuário atual da estação de trabalho"""
    try:
        # Obtém o usuário do sistema operacional
        username = os.getenv('USERNAME') or getpass.getuser()
        return jsonify({'username': username})
    except Exception as e:
        print(f'Erro ao obter usuário: {str(e)}')
        return jsonify({'error': str(e)}), 500

@fraude_bp.route('/api/recertify', methods=['POST'])
def recertify_fraud():
    """Recertifica as avaliações de fraude para todos os processos na base de dados"""
    try:
        # Executa a recertificação
        service = FraudRecertificationService()
        result = service.recertify_fraud_assessments()
        
        return jsonify({
            'success': True,
            'message': 'Recertificação concluída com sucesso',
            'stats': result
        })
    except Exception as e:
        logger.error(f"Erro na recertificação de fraudes: {str(e)}")
        return jsonify({'error': str(e)}), 500
