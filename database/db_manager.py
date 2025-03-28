import logging
import os
from datetime import datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from database.models import Base, Process, Agreement, FraudAssessment
from config import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.Session = None
        self.session = None
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database connection based on environment configuration"""
        # Fallback to SQLite by default
        base_dir = os.path.dirname(os.path.dirname(__file__))
        data_dir = os.path.join(base_dir, 'database')
        sqlite_path = os.path.join(data_dir, 'processes.db')
        
        try:
            # Try Oracle connection first if configured
            oracle_connection = os.getenv('ORACLE_CONNECTION_STRING')
            if oracle_connection:
                self.engine = create_engine(oracle_connection)
                # Test connection
                self.engine.connect()
                logger.info("Successfully connected to Oracle database")
                return
                
        except Exception as e:
            logger.warning(f"Failed to connect to Oracle: {str(e)}")
        
        # If we get here, either there was no Oracle connection string or connection failed
        # Create data directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logger.info(f"Created data directory at {data_dir}")
        
        # Criar ou conectar ao banco SQLite existente
        self.engine = create_engine(f'sqlite:///{sqlite_path}')
        logger.info(f"Using SQLite database at {sqlite_path}")

        # Criar tabelas apenas se não existirem
        inspector = inspect(self.engine)
        if len(inspector.get_table_names()) == 0:
            Base.metadata.create_all(self.engine)
            logger.info("Created database tables")
            
            # Log das tabelas criadas
            tables = inspector.get_table_names()
            for table in tables:
                columns = [col['name'] for col in inspector.get_columns(table)]
                logger.info(f"Table {table} created with columns: {columns}")
        else:
            logger.info("Using existing database tables")
        
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def save_process_data(self, raw_data, grid_data, process_id):
        """Salva os dados completos de um processo"""
        try:
            logger.info("Iniciando salvamento dos dados do processo")
            logger.debug(f"Dados recebidos: {raw_data}")

            # Obtém os dados brutos do processo
            if not raw_data:
                logger.error("Dados brutos do processo não encontrados")
                return None

            # Pega o primeiro processo dos dados brutos (deve haver apenas um)
            process_details = raw_data[process_id]
            if not process_details:
                logger.error("Detalhes do processo não encontrados")
                return None

            logger.debug(f"ID do processo: {process_id}")
            logger.debug(f"Detalhes do processo: {process_details}")

            # Obtém o número do processo do grid_data
            if not grid_data:
                logger.error("Dados do grid não encontrados")
                return None

            # Obtém valores do processo
            processo_info = process_details.get('processo', {})
            detalhes_acordo = process_details.get('detalhes_acordo', {}).get('acordo', [])
            
            # Processa a data de cadastro
            data_cadastro_str = processo_info.get('data_cadastro', '').strip()
            data_cadastro = None
            if data_cadastro_str:
                try:
                    # Tenta fazer o parse da data no formato "DD/MM/YYYY HH:MM"
                    data_cadastro = datetime.strptime(data_cadastro_str, '%d/%m/%Y %H:%M')
                    logger.info(f"Data de cadastro processada: {data_cadastro}")
                except ValueError:
                    try:
                        # Tenta fazer o parse apenas da data no formato "DD/MM/YYYY"
                        data_cadastro = datetime.strptime(data_cadastro_str.split()[0], '%d/%m/%Y')
                        logger.info(f"Data de cadastro processada (apenas data): {data_cadastro}")
                    except ValueError:
                        logger.warning(f"Não foi possível processar a data de cadastro: {data_cadastro_str}")
            
            # Determina tem_acordo e suspeita_fraude do primeiro acordo se existir
            tem_acordo = False
            suspeita_fraude = False
            if detalhes_acordo:
                tem_acordo = detalhes_acordo.get('is_acordo') == 'Sim'
                suspeita_fraude = detalhes_acordo.get('suspeita_fraude') == 'Sim'

            # Cria ou atualiza o processo com os dados do grid
            process = self.session.query(Process).filter_by(external_id=process_id).first()
            if not process:
                process = Process(
                    external_id=process_id,
                    numero=grid_data[2],  # Número do processo
                    parte_adversa=grid_data[3],  # Nome da parte adversa
                    cpf_cnpj_parte_adverso=grid_data[4],  # CPF/CNPJ
                    comarca=grid_data[5],  # Comarca
                    estado=grid_data[6],  # Estado
                    escritorio_celula=processo_info.get('escritorio_celula'),  # Escritório
                    status=grid_data[8],  # Status
                    fase=processo_info.get('fase', ''),  # Fase do processo
                    advogados_adversos=', '.join([adv.get('nome', '') for adv in process_details.get('partes', {}).get('advogados_adversos', [])]), 
                    tem_acordo=tem_acordo,  # Acordo
                    suspeita_fraude=suspeita_fraude,  # Suspeita de Fraude
                    data_cadastro=data_cadastro  # Data de cadastro
                )
                self.session.add(process)
                logger.info(f"Novo processo criado: {process.numero}")
            else:
                # Atualiza os dados do processo
                process.numero = grid_data[2]
                process.parte_adversa = grid_data[3]
                process.cpf_cnpj_parte_adverso = grid_data[4]
                process.comarca = grid_data[5]
                process.estado = grid_data[6]
                process.escritorio_celula = processo_info.get('escritorio_celula')
                process.status = grid_data[8]
                process.fase = processo_info.get('fase', '')
                process.advogados_adversos = ', '.join([adv.get('nome', '') for adv in process_details.get('partes', {}).get('advogados_adversos', [])])
                process.tem_acordo = tem_acordo
                process.suspeita_fraude = suspeita_fraude
                process.data_cadastro = data_cadastro  # Data de cadastro
                logger.info(f"Processo atualizado: {process.numero}")

            # Salva o acordo
            if detalhes_acordo:
                acordo_data = detalhes_acordo
                # Verifica se já existe um acordo com os mesmos dados
                existing_agreement = self.session.query(Agreement)\
                    .filter_by(
                        external_id=process.external_id,
                        cpf_cnpj_titular=acordo_data.get('cpf_titular'),
                        valor=detalhes_acordo.get('valor')
                    ).first()

                if not existing_agreement:
                    # Cria um novo acordo
                    agreement = Agreement(
                external_id=process.external_id,
                        advogados_adversos=', '.join([adv.get('nome', '') for adv in process_details.get('partes', {}).get('advogados_adversos', [])]),
                        nome_titular=acordo_data.get('nome_titular'),
                        cpf_cnpj_titular=acordo_data.get('cpf_titular'),
                        valor=acordo_data.get('valor'),
                        data_pagamento=datetime.strptime(acordo_data.get('data_pagamento'), '%d/%m/%Y %H:%M') if acordo_data.get('data_pagamento') else None
                    )
                    self.session.add(agreement)
                    logger.info(f"Novo acordo criado para o processo {process.numero}")
                else:
                    # Atualiza o acordo existente
                    existing_agreement.advogados_adversos = ', '.join([adv.get('nome', '') for adv in process_details.get('partes', {}).get('advogados_adversos', [])])
                    existing_agreement.nome_titular = acordo_data.get('nome_titular')
                    existing_agreement.valor = acordo_data.get('valor')
                    existing_agreement.data_pagamento = datetime.strptime(acordo_data.get('data_pagamento'), '%d/%m/%Y %H:%M') if acordo_data.get('data_pagamento') else None
                    logger.info(f"Acordo atualizado para o processo {process.numero}")

            # Se houver suspeita de fraude, cria uma avaliação inicial
            if process.suspeita_fraude:
                self.create_initial_fraud_assessment(process)

            self.session.commit()
            logger.info(f"Dados do processo {process.numero} salvos com sucesso")
            return process

        except Exception as e:
            self.session.rollback()
            logger.error(f"Erro ao salvar dados do processo: {str(e)}")
            return None

    def create_initial_fraud_assessment(self, process):
        """Cria uma avaliação de fraude inicial para um processo"""
        try:
            # Verifica se já existe uma avaliação pendente
            existing_assessment = self.session.query(FraudAssessment)\
                .filter_by(external_id=process.external_id, assessment_result='Pendente')\
                .first()

            if not existing_assessment:
                assessment = FraudAssessment(
                    external_id=process.external_id,
                    process_number=process.numero,
                    assessment_result='Pendente'
                )
                self.session.add(assessment)
                self.session.commit()
                logger.info(f"Nova avaliação de fraude criada para o processo {process.numero}")
                return assessment
            return existing_assessment

        except Exception as e:
            self.session.rollback()
            logger.error(f"Erro ao criar avaliação de fraude: {str(e)}")
            return None

    def get_process_by_id(self, external_id):
        """
        Busca um processo pelo ID externo no banco de dados
        
        Args:
            external_id (str): ID externo do processo
            
        Returns:
            dict: Dados do processo ou None se não encontrado
        """
        try:
            session = self.Session()
            
            # Busca o processo e seus relacionamentos
            process = session.query(Process).filter(Process.external_id == external_id).first()
            
            if not process:
                return None
                
            # Converte para dicionário com todos os dados necessários
            process_data = {
                'id': process.id,
                'external_id': process.external_id,
                'numero': process.numero,
                'parte_adversa': process.parte_adversa,
                'cpf_cnpj_parte_adverso': process.cpf_cnpj_parte_adverso,
                'comarca': process.comarca,
                'estado': process.estado,
                'escritorio_celula': process.escritorio_celula,
                'status': process.status,
                'fase': process.fase,
                'advogados_adversos': [{'nome': adv.strip()} for adv in process.advogados_adversos.split(',')] if process.advogados_adversos else [],
                'tem_acordo': process.tem_acordo,
                'suspeita_fraude': process.suspeita_fraude,
                'data_cadastro': process.data_cadastro.isoformat() if process.data_cadastro else None,
                'created_at': process.created_at.isoformat() if process.created_at else None,
                'partes': {
                    'parte_adversa': process.parte_adversa,
                    'cpf_cnpj_parte_adverso': process.cpf_cnpj_parte_adverso,
                    'advogados_adversos': [{'nome': adv.strip()} for adv in process.advogados_adversos.split(',')] if process.advogados_adversos else []
                },
                'acordo': {}  # Lista vazia por padrão
            }
            
            # Adiciona dados do acordo se existir
            if process.agreements != []:
                agreement = process.agreements[0]
                process_data['acordo'] = {
                    'id': agreement.external_id,
                    'nome_titular': agreement.nome_titular,
                    'cpf_cnpj_titular': agreement.cpf_cnpj_titular,
                    'valor': agreement.valor,
                    'data_pagamento': agreement.data_pagamento.strftime('%d/%m/%Y %H:%M') if agreement.data_pagamento else None,
                    'advogados_adversos': [{'nome': adv.strip()} for adv in agreement.advogados_adversos.split(',')] if agreement.advogados_adversos else [],
                    'is_acordo': process.tem_acordo,
                    'suspeita_fraude': process.suspeita_fraude
                }
                
                # Atualiza a lista de advogados na seção 'partes' com os advogados do primeiro acordo
                if process.agreements[0].advogados_adversos:
                    process_data['partes']['advogados_adversos'] = [
                        {'nome': adv.strip()} 
                        for adv in process.agreements[0].advogados_adversos.split(',')
                    ]
            
            # Adiciona dados da avaliação de fraude mais recente se existir
            if process.fraud_assessments:
                latest_assessment = max(process.fraud_assessments, key=lambda x: x.assessment_date)
                process_data.update({
                    'assessment_result': latest_assessment.assessment_result,
                    'reason_conclusion': latest_assessment.reason_conclusion,
                    'assessment_date': latest_assessment.assessment_date.isoformat() if latest_assessment.assessment_date else None
                })
            
            return process_data
            
        except Exception as e:
            logger.error(f"Erro ao buscar processo no banco: {str(e)}")
            return None
        finally:
            session.close()
