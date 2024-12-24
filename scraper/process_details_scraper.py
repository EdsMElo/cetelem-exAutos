from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import logging
from .financial_scraper import FinancialScraper

logger = logging.getLogger(__name__)

def calculate_name_similarity(name1, name2):
    """
    Calcula a similaridade entre dois nomes usando distância de Levenshtein normalizada.
    Retorna um valor entre 0 e 1, onde 1 significa nomes idênticos.
    """
    if not name1 or not name2:
        return 0
        
    # Normaliza os nomes para comparação
    name1 = name1.lower().strip()
    name2 = name2.lower().strip()
    
    # Se os nomes são idênticos após normalização
    if name1 == name2:
        return 1.0
        
    # Implementação da distância de Levenshtein
    def levenshtein(s1, s2):
        if len(s1) < len(s2):
            return levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    # Calcula a distância
    distance = levenshtein(name1, name2)
    
    # Normaliza a distância para um valor entre 0 e 1
    max_length = max(len(name1), len(name2))
    if max_length == 0:
        return 0
        
    similarity = 1 - (distance / max_length)
    return similarity

class ProcessDetailsScraper:
    def __init__(self, driver):
        self.driver = driver
        self.financial_scraper = FinancialScraper(driver)
        
    def check_name_matches(self, nome_titular, process_details):
        """
        Verifica se o nome do titular tem correspondência com outras partes do processo.
        Retorna True se houver match com similaridade > 0.5
        """
        if not nome_titular:
            return False
            
        # Lista de nomes para comparar
        nomes_para_comparar = []
        
        # Adiciona partes do processo
        if 'partes' in process_details:
            partes = process_details['partes']
            if 'parte_interessada' in partes:
                nomes_para_comparar.append(partes['parte_interessada'].replace('REU - ', ''))
            if 'parte_adversa' in partes:
                nomes_para_comparar.append(partes['parte_adversa'].replace('AUTOR - ', ''))
            if 'advogado_interno' in partes:
                nomes_para_comparar.append(partes['advogado_interno'])
            if 'advogados_adversos' in partes:
                for adv in partes['advogados_adversos']:
                    if 'nome' in adv:
                        nomes_para_comparar.append(adv['nome'])
        
        # Compara o nome do titular com cada nome da lista
        for nome in nomes_para_comparar:
            similarity = calculate_name_similarity(nome_titular, nome)
            logger.info(f"Comparando '{nome_titular}' com '{nome}' - Similaridade: {similarity:.2f}")
            if similarity > 0.5:  # 50% de similaridade
                logger.warning(f"Match encontrado entre '{nome_titular}' e '{nome}' com {similarity:.2f} de similaridade")
                return True
                
        return False
        
    def extract_process_details(self, process_id, grid_data=None):
        """Extrai detalhes completos de um processo específico"""
        try:
            if not process_id:
                logger.warning(f"ID do processo não fornecido")
                return None
                
            # Navega para a página de detalhes do processo
            details_url = f"https://cetelem.djur.adv.br/processo/details/{process_id}"
            logger.info(f"Acessando detalhes do processo: {details_url}")
            self.driver.get(details_url)
            
            # Aguarda carregamento inicial
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "panel-body"))
                )
            except TimeoutException:
                logger.warning(f"Timeout aguardando carregamento da página de detalhes do processo {process_id}")
                return None
            
            process_details = {
                'processo': {},
                'partes': {},
                'financeiro': {},
                'detalhes_acordo': []
            }

            # Se temos dados do grid, usamos eles como fonte principal para alguns campos
            if grid_data:
                process_details['processo'] = {
                    'numero': grid_data[1],  # Numero do Processo
                    'escritorio_celula': grid_data[8],  # Escritório
                    'comarca': grid_data[4],  # Comarca
                    'status': grid_data[7],  # Status
                    'fase': self.safe_get_text("//td[strong[text()='Fase']]/following-sibling::td")
                }
            else:
                process_details['processo'] = {
                    'numero': self.safe_get_text("//td[strong[text()='Número do Processo:']]/following-sibling::td"),
                    'escritorio_celula': self.safe_get_text("//td[strong[text()='Escritório / Célula:']]/following-sibling::td"),
                    'comarca': self.safe_get_text("//td[strong[text()='Comarca:']]/following-sibling::td"),
                    'fase': self.safe_get_text("//td[strong[text()='Fase']]/following-sibling::td"),
                    'status': self.safe_get_text("//td[strong[text()='Status:']]/following-sibling::td")
                }

            # Extrai dados das partes primeiro para ter os nomes para comparação
            try:
                # Clica na aba Geral
                geral_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="#box-dadosprincipais"]'))
                )
                self.driver.execute_script("arguments[0].click();", geral_tab)
                
                # Aguarda o carregamento da aba
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "box-dadosprincipais"))
                )
                
                # Extrai dados das partes
                process_details['partes'] = self.extract_parties_data()
                
                # Popula polo ativo/passivo
                if 'parte_adversa' in process_details['partes']:
                    process_details['partes']['polo_ativo'] = [{
                        'nome': process_details['partes']['parte_adversa'].replace('AUTOR - ', ''),
                        'cpf_cnpj': process_details['partes'].get('cpf_cnpj_parte_adverso', ''),
                        'tipo': 'AUTOR'
                    }]
                
                if 'parte_interessada' in process_details['partes']:
                    process_details['partes']['polo_passivo'] = [{
                        'nome': process_details['partes']['parte_interessada'].replace('REU - ', ''),
                        'tipo': 'REU'
                    }]
            
            except Exception as e:
                logger.error(f"Erro ao extrair dados das partes: {str(e)}")
                process_details['partes'] = {}

            # Extrai dados financeiros
            try:
                # Aguarda e clica na aba financeira
                financial_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="#box-financeiro"]'))
                )
                self.driver.execute_script("arguments[0].click();", financial_tab)
                
                # Aguarda o carregamento da tabela financeira
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#financeiroList table.table-hover"))
                )
                
                # Extrai os dados financeiros
                process_details['financeiro'] = self.financial_scraper.extract_financial_data(process_id)
                
                # Verifica se há acordos nos lançamentos financeiros
                if process_details['financeiro'] and 'lancamentos' in process_details['financeiro']:
                    acordos = [
                        lanc for lanc in process_details['financeiro']['lancamentos']
                        if lanc.get('tipo', '').upper() == 'ACORDO'
                    ]
                    
                    logger.info(f"Encontrados {len(acordos)} acordos para processar")
                    
                    # Para cada acordo encontrado, extrai os detalhes
                    for idx, acordo in enumerate(acordos, 1):
                        logger.info(f"Processando acordo {idx} de {len(acordos)}")
                        try:
                            # Verifica e acessa o link do acordo
                            if 'link' in acordo:
                                acordo_link = acordo['link']
                                logger.info(f"Link do acordo encontrado: {acordo_link}")
                                
                                # Verifica se o link é válido
                                if not acordo_link or not acordo_link.strip():
                                    logger.warning(f"Link do acordo {idx} está vazio")
                                    continue
                                    
                                logger.info(f"Acessando link do acordo: {acordo_link}")
                                # Guarda a URL atual para voltar depois
                                current_url = self.driver.current_url
                                
                                try:
                                    # Navega para a página do acordo
                                    logger.info(f"Navegando para a página do acordo: {acordo_link}")
                                    self.driver.get(acordo_link)
                                    
                                    # Aguarda a página carregar
                                    WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.CLASS_NAME, "panel-body"))
                                    )
                                    
                                    # Aguarda a tabela principal e extrai suas linhas
                                    table = WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-striped"))
                                    )
                                    
                                    rows = table.find_elements(By.TAG_NAME, "tr")
                                    if not rows:
                                        logger.error("Tabela de detalhes do acordo está vazia")
                                        self.driver.get(current_url)
                                        continue
                                        
                                    logger.info(f"Tabela carregada com {len(rows)} linhas")
                                    
                                    # Extrai os detalhes do acordo
                                    acordo_details = {}
                                    
                                    # Mapeamento dos campos conforme HTML
                                    campos_acordo = {
                                        'id': 'ID',
                                        'processo_numero': 'Processo',
                                        'processo_id': 'ID Processo',
                                        'pa': 'PA',
                                        'tipo': 'Tipo',
                                        'origem': 'Origem',
                                        'status': 'Status',
                                        'alcada': 'Alçada',
                                        'responsavel': 'Responsável',
                                        'observacao': 'Observação',
                                        'observacao_conclusao': 'Observação Conclusão',
                                        'data_vencimento': 'Data Vencimento',
                                        'data_conclusao': 'Data Conclusão DJUR',
                                        'id_deposito': 'Id Depósito',
                                        'data_cancelamento': 'Data de Cancelamento',
                                        'tipo_liminar': 'Tipo Liminar',
                                        'tipo_lancamento': 'Tipo Lançamento',
                                        'dia_mes_gerar_liminar': 'Dia Mês Gerar Liminar',
                                        'valor': 'Valor',
                                        'valor_multa': 'Valor Multa',
                                        'justificativa_cancelamento': 'Justificativa Cancelamento',
                                        'tipo_conta': 'Tipo de Conta',
                                        'agencia': 'Agência',
                                        'conta': 'C/C',
                                        'nome_titular': 'Nome do Titular',
                                        'cpf_titular': 'CPF do Titular',
                                        'valor_acordo': 'Valor Acordo',
                                        'banco': 'Banco',
                                        'forma_pagamento': 'Forma de Pagamento',
                                        'data_pagamento': 'Data Pagamento'
                                    }
                                    
                                    # Extrai valores da tabela
                                    for row in rows:
                                        try:
                                            cells = row.find_elements(By.TAG_NAME, "td")
                                            if len(cells) >= 2:
                                                # Pega o label da primeira célula
                                                label_element = cells[0].find_element(By.TAG_NAME, "strong")
                                                if label_element:
                                                    label = label_element.text.strip().replace(":", "")
                                                    # Trata células que podem conter links
                                                    try:
                                                        link = cells[1].find_element(By.TAG_NAME, "a")
                                                        # Para campos específicos, pegamos o href do link
                                                        if label in ['Processo', 'PA']:
                                                            value = link.get_attribute('href').split('/')[-1].strip()
                                                        else:
                                                            value = link.text.strip()
                                                    except:
                                                        value = cells[1].text.strip()
                                                        
                                                    # Procura o campo correspondente ao label
                                                    for campo, campo_label in campos_acordo.items():
                                                        if campo_label == label:
                                                            acordo_details[campo] = value
                                                            break
                                        except Exception as e:
                                            logger.debug(f"Erro ao processar linha da tabela: {str(e)}")
                                            continue
                                    
                                    # Marca o lançamento como acordo e verifica suspeita de fraude
                                    acordo_details['is_acordo'] = 'Sim'
                                    nome_titular = acordo_details.get('nome_titular', '')
                                    
                                    # Verifica suspeita de fraude apenas se tivermos um nome de titular
                                    if nome_titular:
                                        suspeita_fraude = 'Sim' if self.check_name_matches(nome_titular, process_details) else 'Não'
                                        acordo_details['suspeita_fraude'] = suspeita_fraude
                                        
                                        # Atualiza o campo no grid financeiro
                                        logger.info(f"Atualizando suspeita de fraude para '{suspeita_fraude}' no acordo {acordo_link}")
                                        if not self.financial_scraper.update_acordo_suspeita_fraude(acordo_link, suspeita_fraude):
                                            logger.warning(f"Não foi possível atualizar suspeita de fraude no grid para o acordo {acordo_link}")
                                    else:
                                        logger.warning(f"Nome do titular não encontrado para o acordo {acordo_link}")
                                        acordo_details['suspeita_fraude'] = 'N/A'
                                    
                                    # Extrai documentos do acordo
                                    try:
                                        documentos = []
                                        try:
                                            # Aguarda e verifica se a tabela de documentos existe
                                            doc_table = WebDriverWait(self.driver, 5).until(
                                                EC.presence_of_element_located((By.CSS_SELECTOR, "#gridDocumentoList table"))
                                            )
                                            doc_rows = doc_table.find_elements(By.CSS_SELECTOR, "tbody tr")
                                            
                                            for doc_row in doc_rows:
                                                try:
                                                    cells = doc_row.find_elements(By.TAG_NAME, "td")
                                                    if len(cells) >= 8:
                                                        doc = {
                                                            'id': cells[2].text.strip(),
                                                            'nome': cells[3].text.strip(),
                                                            'tipo': cells[5].text.strip(),
                                                            'proprietario': cells[6].text.strip(),
                                                            'data_criacao': cells[7].text.strip()
                                                        }
                                                        documentos.append(doc)
                                                except Exception as e:
                                                    logger.debug(f"Erro ao processar linha de documento: {str(e)}")
                                                    continue
                                        except TimeoutException:
                                            logger.info(f"Nenhum documento encontrado para o acordo {acordo_link}")
                                        
                                        acordo_details['documentos'] = documentos
                                    except Exception as e:
                                        logger.warning(f"Erro ao processar seção de documentos do acordo: {str(e)}")
                                        acordo_details['documentos'] = []
                                    
                                    # Extrai histórico do acordo
                                    try:
                                        historico = []
                                        try:
                                            # Aguarda e verifica se a tabela de histórico existe
                                            hist_table = WebDriverWait(self.driver, 5).until(
                                                EC.presence_of_element_located((By.CSS_SELECTOR, "#historicoList table"))
                                            )
                                            hist_rows = hist_table.find_elements(By.CSS_SELECTOR, "tbody tr")[1:]  # Pula o cabeçalho
                                            
                                            for hist_row in hist_rows:
                                                try:
                                                    cells = hist_row.find_elements(By.TAG_NAME, "td")
                                                    if len(cells) >= 2:
                                                        hist = {
                                                            'data': cells[0].text.strip(),
                                                            'descricao': cells[1].text.strip()
                                                        }
                                                        historico.append(hist)
                                                except Exception as e:
                                                    logger.debug(f"Erro ao processar linha de histórico: {str(e)}")
                                                    continue
                                        except TimeoutException:
                                            logger.info(f"Nenhum histórico encontrado para o acordo {acordo_link}")
                                        
                                        acordo_details['historico'] = historico
                                    except Exception as e:
                                        logger.warning(f"Erro ao processar seção de histórico do acordo: {str(e)}")
                                        acordo_details['historico'] = []
                                    
                                    # Adiciona o acordo extraído à lista
                                    if acordo_details:
                                        process_details['detalhes_acordo'].append(acordo_details)
                                        logger.info(f"Acordo {idx} adicionado com sucesso")
                                    else:
                                        logger.warning(f"Acordo {idx} não contém dados")
                                        
                                except Exception as e:
                                    logger.error(f"Erro ao extrair dados do acordo: {str(e)}")
                                finally:
                                    # Volta para a página do processo
                                    logger.info("Voltando para a página do processo")
                                    self.driver.get(current_url)
                                    
                                    # Aguarda carregamento e clica na aba financeira
                                    WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.CLASS_NAME, "panel-body"))
                                    )
                                    financial_tab = WebDriverWait(self.driver, 10).until(
                                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="#box-financeiro"]'))
                                    )
                                    self.driver.execute_script("arguments[0].click();", financial_tab)
                                    WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, "#financeiroList table.table-hover"))
                                    )
                                    
                        except Exception as e:
                            logger.error(f"Erro ao processar acordo: {str(e)}")
                            # Garante que voltamos para a página do processo
                            self.driver.get(current_url)
                            continue
                            
            except Exception as e:
                logger.error(f"Erro ao extrair dados financeiros: {str(e)}")
                process_details['financeiro'] = {'lancamentos': [], 'resumo': {}}

            return process_details
            
        except Exception as e:
            logger.error(f"Erro ao extrair detalhes do processo: {str(e)}")
            return None

    def extract_parties_data(self):
        """Extrai dados das partes"""
        parties_data = {
            'parte_interessada': '',
            'parte_adversa': '',
            'cpf_cnpj_parte_adverso': '',
            'advogados_adversos': [],
            'polo_ativo': [],
            'polo_passivo': [],
            'terceiros_interessados': [],
            'advogado_interno': ''
        }
        
        try:
            # Aguarda o carregamento do accordion
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "accordion-dadosBasicos"))
            )
            
            # Extrai dados básicos
            parties_data['parte_interessada'] = self.safe_get_text("//td[strong[contains(text(), 'Parte Interessada:')]]/following-sibling::td")
            parties_data['parte_adversa'] = self.safe_get_text("//td[strong[contains(text(), 'Parte Adversa:')]]/following-sibling::td")
            parties_data['cpf_cnpj_parte_adverso'] = self.safe_get_text("//td[strong[contains(text(), 'CPF/CNPJ - Parte Adverso:')]]/following-sibling::td").split('(')[0].strip()
            parties_data['advogado_interno'] = self.safe_get_text("//td[strong[contains(text(), 'Advogado Interno:')]]/following-sibling::td")
            
            # Extrai advogados adversos
            advogados = []
            primary_adv = self.safe_get_text("//td[strong[contains(text(), 'Advogado Adverso:')]]/following-sibling::td")
            if primary_adv:
                primary_oab = self.safe_get_text("//td[strong[contains(text(), 'Nº OAB:')]]/following-sibling::td")
                advogados.append({
                    'nome': primary_adv,
                    'oab': primary_oab
                })
            
            second_adv = self.safe_get_text("//td[strong[contains(text(), 'Segundo Advogado Adverso:')]]/following-sibling::td")
            if second_adv:
                second_oab = self.safe_get_text("//td[strong[contains(text(), 'Segundo Advogado Adverso:')]]/following-sibling::td/following-sibling::td[2]")
                advogados.append({
                    'nome': second_adv,
                    'oab': second_oab
                })
            
            parties_data['advogados_adversos'] = advogados
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados das partes: {str(e)}")
        
        return parties_data

    def safe_get_text(self, xpath):
        """Extrai texto de um elemento de forma segura"""
        try:
            element = self.driver.find_element(By.XPATH, xpath)
            return element.text.strip()
        except Exception:
            return ""
