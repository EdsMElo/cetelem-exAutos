import logging
from sqlalchemy.sql import text
from database.db_manager import DatabaseManager
from database.models import FraudAssessment
from scraper.process_details_scraper import ProcessDetailsScraper

logger = logging.getLogger(__name__)

class FraudRecertificationService:
    """Serviço para recertificar as avaliações de fraude nos processos existentes"""
    
    def __init__(self):
        self.db = DatabaseManager()
        # Inicializa o ProcessDetailsScraper com None como driver, pois não precisamos do driver para a função check_name_matches
        self.process_scraper = ProcessDetailsScraper(None)
    
    def recertify_fraud_assessments(self):
        """
        Recertifica todas as avaliações de fraude baseado nos dados existentes.
        Limpa a tabela de fraudes e adiciona apenas os casos suspeitos.
        
        Returns:
            dict: Estatísticas da recertificação
        """
        try:
            logger.info("Iniciando recertificação de fraudes")
            
            # Estatísticas para retornar
            stats = {
                "total_processos": 0,
                "total_fraudes": 0,
                "erros": 0
            }
            
            # Obtém todos os acordos com seus processos
            session = self.db.Session()
            try:
                # Primeiro, limpa a tabela de fraudes
                logger.info("Limpando tabela de avaliações de fraude")
                session.query(FraudAssessment).delete()
                
                # Busca todos os acordos com seus respectivos processos
                query = """
                    SELECT a.*, p.external_id, p.parte_adversa, p.advogados_adversos as proc_advogados_adversos,
                           p.numero
                    FROM agreements a
                    JOIN processes p ON a.external_id = p.external_id
                """
                
                agreements = session.execute(text(query)).fetchall()
                stats["total_processos"] = len(agreements)
                
                for agreement in agreements:
                    try:
                        # Verifica se o acordo deve ser marcado como suspeita de fraude
                        nome_titular = agreement.nome_titular
                        
                        # Prepara os dados para verificação de fraude
                        process_details = {
                            'partes': {
                                'parte_adversa': agreement.parte_adversa,
                                'advogados_adversos': self._parse_advogados_adversos(agreement.proc_advogados_adversos)
                            }
                        }
                        
                        # Grid data no formato esperado pelo check_name_matches
                        grid_data = [{
                            'grid_data': [None, None, None, agreement.parte_adversa, None]
                        }]
                        
                        # Verifica se é suspeita de fraude usando o método do ProcessDetailsScraper
                        # Nota: O método retorna True se NÃO houver match, então invertemos o resultado
                        is_fraud = self.process_scraper.check_name_matches(nome_titular, process_details, grid_data)
                        
                        # Obtém o número do processo da tabela processes
                        process_number = agreement.numero
                        
                        # Se for suspeita de fraude, adiciona à tabela
                        if is_fraud:
                            new_assessment = FraudAssessment(
                                external_id=agreement.external_id,
                                process_number=process_number,
                                assessment_result="Pendente"
                            )
                            session.add(new_assessment)
                            stats["total_fraudes"] += 1
                            logger.info(f"Adicionada avaliação de fraude para o processo {agreement.external_id} ({process_number})")
                    
                    except Exception as e:
                        logger.error(f"Erro ao recertificar processo {agreement.external_id}: {str(e)}")
                        stats["erros"] += 1
                
                # Commit das alterações
                session.commit()
                logger.info(f"Recertificação concluída. Estatísticas: {stats}")
                return stats
                
            except Exception as e:
                session.rollback()
                logger.error(f"Erro durante a recertificação: {str(e)}")
                raise
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Erro geral na recertificação: {str(e)}")
            raise
            
    def _parse_advogados_adversos(self, advogados_str):
        """Converte a string de advogados adversos para o formato esperado pelo check_name_matches"""
        if not advogados_str:
            return []
        
        advogados = []
        for adv in advogados_str.split(','):
            adv = adv.strip()
            if adv:
                advogados.append({'nome': adv})
        
        return advogados
