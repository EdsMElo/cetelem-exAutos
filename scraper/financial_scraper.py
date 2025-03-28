from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging
import json
import time
from config import get_logger

logger = get_logger(__name__)

class FinancialScraper:
    def __init__(self, driver):
        self.driver = driver
        self.financial_data = {'lancamentos': [], 'resumo': {}}

    def extract_financial_data(self, process_id):
        """Extrai dados financeiros de um processo específico"""
        start_time = time.time()
        try:
            if not process_id:
                logger.warning(f"ID do processo inválido: {process_id}")
                return None

            # Estrutura para armazenar os dados financeiros
            financial_data = {
                'lancamentos': [],
                'resumo': {}  # Mantido vazio para compatibilidade
            }

            # Aguarda o carregamento dos dados financeiros
            try:
                # Aguarda a tabela financeira carregar
                load_start = time.time()
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#financeiroList"))
                )
                
                # Aguarda um curto período para garantir que os dados foram carregados
                time.sleep(0.5)  # Reduzido de 2s para 0.5s
                logger.info(f"[TEMPO] Carregamento da tabela financeira: {time.time() - load_start:.2f} segundos")
                
                # Tenta diferentes seletores para a tabela principal
                financial_table = None
                table_selectors = [
                    "#financeiroList table.table-hover",
                    "#financeiroList table.paginate",
                    "table.table-hover",
                    "table.paginate"
                ]
                
                for selector in table_selectors:
                    try:
                        financial_table = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if financial_table:
                            break
                    except:
                        continue
                
                if financial_table:
                    # Verifica os cabeçalhos da tabela
                    headers = financial_table.find_elements(By.CSS_SELECTOR, "thead th")
                    header_texts = [h.text.strip() for h in headers]
                    logger.debug(f"Cabeçalhos encontrados: {header_texts}")
                    
                    # Verifica o índice da coluna tipo
                    tipo_index = next((i for i, h in enumerate(header_texts) if 'TIPO' in h.upper()), 4)
                    logger.debug(f"Índice da coluna tipo: {tipo_index}")
                    
                    # Extrai os dados financeiros
                    financial_rows = financial_table.find_elements(By.CSS_SELECTOR, "tbody tr")
                    logger.info(f"Encontradas {len(financial_rows)} linhas na tabela financeira")
                    
                    for row in financial_rows:
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 9:  # Ajustado para 9 colunas conforme HTML
                                # Primeiro verifica se é um acordo antes de extrair todos os dados
                                try:
                                    tipo_cell = cells[tipo_index].text.strip()
                                    if not ('ACORDO' in tipo_cell.upper() or tipo_cell.upper() in 'ACORDO'):
                                        logger.debug(f"Ignorando lançamento não-acordo: {tipo_cell}")
                                        continue
                                except Exception as e:
                                    logger.debug(f"Erro ao verificar tipo de lançamento: {str(e)}")
                                    continue
                                
                                lancamento = {}
                                
                                # Mapeamento dos índices das colunas conforme cabeçalhos
                                column_map = {
                                    'link': (0, 'href'),  # Link na primeira coluna
                                    'classificacao': (3, 'text'),  # Classificação
                                    'tipo': (tipo_index, 'text'),  # Tipo de Lançamento (índice dinâmico)
                                    'valor': (5, 'text'),  # Valor do Lançamento
                                    'natureza': (6, 'text'),  # Natureza
                                    'data_pagamento': (7, 'text'),  # Data Pagamento
                                    'usuario': (8, 'text'),  # Usuário Cadastro
                                    'suspeita_fraude': (None, False),  # Campo adicional para suspeita de fraude
                                    'is_acordo': (None, 'Sim')  # Já sabemos que é acordo neste ponto
                                }
                                
                                # Extrai cada campo com tratamento de erro
                                for field, (index, attr_type) in column_map.items():
                                    try:
                                        if field == 'link':
                                            try:
                                                links = cells[index].find_elements(By.TAG_NAME, "a")
                                                if links:
                                                    # Pega todos os links da célula
                                                    all_hrefs = [l.get_attribute('href') for l in links]
                                                    logger.debug(f"Links encontrados na célula: {all_hrefs}")
                                                    
                                                    # Procura primeiro por links de acordo
                                                    acordo_links = [l for l in links if 'acordo' in l.get_attribute('href').lower()]
                                                    if acordo_links:
                                                        value = acordo_links[0].get_attribute('href')
                                                        logger.info(f"Link de acordo encontrado: {value}")
                                                    else:
                                                        value = links[0].get_attribute('href')
                                                        logger.debug(f"Nenhum link de acordo encontrado, usando primeiro link: {value}")
                                                else:
                                                    logger.debug("Nenhum link encontrado na célula")
                                                    continue
                                            except Exception as e:
                                                logger.debug(f"Erro ao extrair link: {str(e)}")
                                                continue
                                        elif field == 'suspeita_fraude':
                                            value = False  # Valor padrão, será atualizado depois
                                        elif field == 'is_acordo':
                                            value = True  # Valor padrão, pois já sabemos que é acordo
                                        else:
                                            value = cells[index].text.strip()
                                            # Log especial para o campo tipo
                                            if field == 'tipo':
                                                logger.debug(f"Valor original do campo tipo na coluna {index}: '{value}'")
                                            
                                        if value:  # Só adiciona se tiver valor
                                            lancamento[field] = value
                                    except Exception as e:
                                        logger.debug(f"Erro ao extrair campo {field} da coluna {index}: {str(e)}")
                                        continue
                                
                                # Adiciona o lançamento se tiver informações relevantes
                                if lancamento:
                                    # Log específico para o tipo de lançamento
                                    if 'tipo' in lancamento:
                                        tipo = lancamento['tipo'].upper().strip()
                                        logger.info(f"Tipo de lançamento encontrado: '{tipo}' (original: '{lancamento['tipo']}')")
                                        if 'link' in lancamento:
                                            logger.info(f"Acordo encontrado com link: {json.dumps(lancamento, ensure_ascii=False)}")
                                        else:
                                            logger.warning(f"Acordo encontrado sem link: {json.dumps(lancamento, ensure_ascii=False)}")
                                    
                                    financial_data['lancamentos'].append(lancamento)
                                    logger.debug(f"Lançamento adicionado: {json.dumps(lancamento, ensure_ascii=False)}")
                        except Exception as e:
                            logger.warning(f"Erro ao processar linha da tabela: {str(e)}")
                            continue
                    
                    # Log do total de lançamentos e acordos encontrados
                    total_lancamentos = len(financial_data['lancamentos'])
                    logger.info(f"Total de acordos encontrados: {total_lancamentos}")
                    logger.info(f"[TEMPO] Extração dos dados financeiros: {time.time() - start_time:.2f} segundos")
                
                self.financial_data = financial_data
                return self.financial_data

            except TimeoutException:
                logger.warning(f"Timeout aguardando carregamento dos dados financeiros do processo {process_id}")
                self.financial_data = {'lancamentos': [], 'resumo': {}}
                return self.financial_data

        except Exception as e:
            logger.error(f"Erro ao extrair dados financeiros: {str(e)}")
            self.financial_data = {'lancamentos': [], 'resumo': {}}
            return self.financial_data

    def get_financial_data_as_json(self, process_id):
        """Retorna os dados financeiros em formato JSON"""
        financial_data = self.extract_financial_data(process_id)
        if financial_data:
            return json.dumps(financial_data, ensure_ascii=False, indent=2)
        return None

    def update_acordo_suspeita_fraude(self, acordo_link, valor):
        """Atualiza o campo suspeita_fraude de um acordo específico"""
        for lancamento in self.financial_data.get('lancamentos', []):
            if lancamento.get('link') == acordo_link:
                lancamento['suspeita_fraude'] = valor
                logger.info(f"Campo suspeita_fraude atualizado para '{valor}' no acordo {acordo_link}")
                return True
        return False
