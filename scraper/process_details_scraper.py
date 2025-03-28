from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from unidecode import unidecode
import re
import time
import logging
from .financial_scraper import FinancialScraper
from difflib import SequenceMatcher
from collections import Counter
import numpy as np
from Levenshtein import ratio as levenshtein_ratio
from textdistance import jaccard, jaro_winkler
import math
from config import get_logger

logger = get_logger(__name__)

def calculate_name_similarity(nome1, nome2):
    """
    Calcula a similaridade entre dois nomes usando múltiplas métricas.
    
    Métricas utilizadas:
    1. Distância de Levenshtein
    2. Coeficiente de Jaccard
    3. Similaridade de Cosseno (usando n-gramas)
    4. Jaro-Winkler
    
    Returns:
        float: Score de similaridade entre 0 e 1
    """
    if not nome1 or not nome2:
        return 0.0
        
    # Normalização dos nomes
    nome1_norm = ProcessDetailsScraper._normalize_name(None, nome1)
    nome2_norm = ProcessDetailsScraper._normalize_name(None, nome2)
    
    if not nome1_norm or not nome2_norm:
        return 0.0
    
    # 1. Levenshtein Ratio (peso: 0.3)
    levenshtein_score = levenshtein_ratio(nome1_norm, nome2_norm)
    
    # 2. Coeficiente de Jaccard (peso: 0.2)
    jaccard_score = jaccard.normalized_similarity(nome1_norm.split(), nome2_norm.split())
    
    # 3. Similaridade de Cosseno usando n-gramas (peso: 0.2)
    def get_ngrams(text, n=3):
        return [text[i:i+n] for i in range(len(text)-n+1)]
    
    def cosine_similarity(vec1, vec2):
        intersection = set(vec1.keys()) & set(vec2.keys())
        numerator = sum([vec1[x] * vec2[x] for x in intersection])
        
        sum1 = sum([vec1[x]**2 for x in vec1.keys()])
        sum2 = sum([vec2[x]**2 for x in vec2.keys()])
        denominator = math.sqrt(sum1) * math.sqrt(sum2)
        
        if not denominator:
            return 0.0
        return float(numerator) / denominator
    
    # Cria vetores de n-gramas
    ngrams1 = Counter(get_ngrams(nome1_norm))
    ngrams2 = Counter(get_ngrams(nome2_norm))
    
    cosine_score = cosine_similarity(ngrams1, ngrams2)
    
    # 4. Jaro-Winkler (peso: 0.3)
    jaro_score = jaro_winkler.normalized_similarity(nome1_norm, nome2_norm)
    
    # Cálculo do score final ponderado
    final_score = (
        0.3 * levenshtein_score +  # Levenshtein tem peso maior por ser mais preciso para nomes
        0.2 * jaccard_score +      # Jaccard é bom para comparar conjuntos de palavras
        0.2 * cosine_score +       # Cosseno captura similaridades em nível de caractere
        0.3 * jaro_score          # Jaro-Winkler é especialmente bom para strings curtas como nomes
    )
    
    logger.debug(f"""
    Scores de similaridade para '{nome1}' e '{nome2}':
    - Nomes normalizados: '{nome1_norm}' e '{nome2_norm}'
    - Levenshtein: {levenshtein_score:.3f}
    - Jaccard: {jaccard_score:.3f}
    - Cosseno: {cosine_score:.3f}
    - Jaro-Winkler: {jaro_score:.3f}
    - Score Final: {final_score:.3f}
    """)
    
    return final_score

class ProcessDetailsScraper:
    def __init__(self, driver):
        self.driver = driver
        self.financial_scraper = FinancialScraper(driver)

    def _log_time(self, start_time, step_name):
        """Calcula e loga o tempo gasto em uma etapa"""
        elapsed = time.time() - start_time
        logger.info(f"[TEMPO] {step_name}: {elapsed:.2f} segundos")
        return elapsed

    def check_name_matches(self, nome_titular, process_details, grid_data):
        """
        Verifica se o nome do titular tem correspondência com outras partes do processo.
        Retorna True se não houver match.
        
        Ordem de verificação:
        1. Verifica se o nome do titular está contido em alguma das outras partes
        2. Verifica similaridade entre os nomes (>50%)
        """
        if not nome_titular:
            return False
        
        # Lista de nomes para comparar
        nomes_para_comparar = []
        
        # Adiciona partes do processo
        if 'partes' in process_details:
            partes = process_details['partes']
            
            # Adiciona parte adversa ou usa o campo adverso do grid_data apenas para validação de fraude
            parte_adversa = None
            if 'parte_adversa' in partes and partes['parte_adversa'] and partes['parte_adversa'].strip() not in ['', 'N/A']:
                parte_adversa = partes['parte_adversa'].replace('AUTOR - ', '').strip()
                logger.info(f"Usando parte adversa do processo: {parte_adversa}")
            elif grid_data[0]['grid_data'][3]:
                # O campo adverso está na posição 3 do grid_data
                grid_adverso = grid_data[0]['grid_data'][3].strip()
                if grid_adverso and grid_adverso not in ['', 'N/A']:
                    parte_adversa = grid_adverso
                    logger.info(f"Usando parte adversa do grid_data para validação de fraude: {parte_adversa}")
            else:
                logger.warning("Parte adversa não encontrada em nenhuma fonte")
                
            if parte_adversa:
                nomes_para_comparar.append({
                    'nome': parte_adversa,
                    'tipo': 'parte_adversa'
                })
                
            # Adiciona advogado interno
            if 'advogado_interno' in partes and partes['advogado_interno']:
                nome = partes['advogado_interno'].strip()
                if nome:
                    nomes_para_comparar.append({
                        'nome': nome,
                        'tipo': 'advogado_interno'
                    })
                
            # Adiciona todos os advogados adversos
            if 'advogados_adversos' in partes:
                for adv in partes['advogados_adversos']:
                    if 'nome' in adv and adv['nome']:
                        nome = adv['nome'].strip()
                        if nome:
                            nomes_para_comparar.append({
                                'nome': nome,
                                'tipo': 'advogado_adverso'
                            })
        
        # Normaliza o nome do titular para comparação
        nome_titular_norm = self._normalize_name(nome_titular)
        
        # 1. Verifica se o nome do titular está contido em algum dos outros nomes
        for info in nomes_para_comparar:
            nome_norm = self._normalize_name(info['nome'])
            
            # Se houver correspondência entre os nomes (usando versões normalizadas sem acentos)
            if nome_titular_norm in nome_norm or nome_norm in nome_titular_norm:
                logger.warning(
                    f"Match direto encontrado entre '{nome_titular}' (normalizado: '{nome_titular_norm}') e '{info['nome']}' (normalizado: '{nome_norm}')"
                )
                return False
        
        # 2. Verifica similaridade entre os nomes
        for info in nomes_para_comparar:
            similarity = calculate_name_similarity(nome_titular, info['nome'])
            logger.info(f"Comparando '{nome_titular}' com '{info['nome']}' - Similaridade: {similarity:.2f}")
            
            if similarity > 0.5:  # 50% de similaridade
                logger.warning(
                    f"Match por similaridade encontrado entre '{nome_titular}' e '{info['nome']}' "
                    f"com {similarity:.2f} de similaridade"
                )
                return False
            
        return True

    def _normalize_name(self, name):
        """
        Normaliza um nome para comparação, aplicando as seguintes transformações:
        1. Remove acentos e caracteres especiais
        2. Converte para minúsculo
        3. Remove títulos honoríficos e sufixos empresariais
        4. Remove caracteres não alfanuméricos
        5. Padroniza espaços e pontuação
        6. Remove palavras comuns e stopwords
        """
        if not name:
            return ""
        
        # Converte para minúsculo e remove espaços extras nas extremidades
        normalized = name.lower().strip()
        
        # Remove acentos e caracteres especiais usando unidecode
        normalized = unidecode(normalized)
        
        # Lista expandida de palavras para remover
        palavras_para_remover = [
            # Stopwords em português
            'a', 'ao', 'aos', 'aquela', 'aquelas', 'aquele', 'aqueles', 'aquilo',
            'as', 'ate', 'com', 'como', 'da', 'das', 'de', 'dela', 'delas',
            'dele', 'deles', 'depois', 'do', 'dos', 'e', 'ela', 'elas', 'ele',
            'eles', 'em', 'entre', 'era', 'eram', 'essa', 'essas', 'esse',
            'esses', 'esta', 'estas', 'este', 'estes', 'eu', 'isso', 'isto',
            'ja', 'la', 'lhe', 'lhes', 'lo', 'mas', 'me', 'mesmo', 'meu',
            'meus', 'minha', 'minhas', 'muito', 'na', 'nas', 'nem', 'no', 'nos',
            'nossa', 'nossas', 'nosso', 'nossos', 'num', 'numa', 'o', 'os',
            'ou', 'para', 'pela', 'pelas', 'pelo', 'pelos', 'por', 'qual',
            'quando', 'que', 'quem', 'sao', 'se', 'seja', 'sejam', 'sem',
            'seu', 'seus', 'so', 'sua', 'suas', 'tambem', 'te', 'tem', 'tinha',
            'um', 'uma', 'voce', 'voces', 'vos', 'vosso', 'vossa', 'vossos',
            'vossas',
            
            # Títulos honoríficos e profissionais
            'dr', 'dra', 'doutor', 'doutora', 'adv', 'advogado', 'advogada',
            'professor', 'professora', 'prof', 'profa', 'mestre', 'mestra',
            'especialista', 'bacharel', 'excelentissimo', 'excelentissima',
            'ilustrissimo', 'ilustrissima', 'senhor', 'senhora', 'sr', 'sra',
            'vossa', 'excelencia', 'meritissimo', 'meritissima',
            'senhor', 'senhora', 'sr', 'sra', 'vossa', 'excelencia',
            'meritissimo', 'meritissima',
            
            # Sufixos empresariais e termos jurídicos
            'me', 'mei', 'ltda', 'sa', 's/a', 'ss', 'epp', 'eireli',
            'sociedade', 'individual', 'empresaria', 'limitada', 'simples',
            'microempresa', 'microempreendedor', 'empresa', 'comercio',
            'industria', 'servicos', 'representacoes', 'distribuicao',
            'importacao', 'exportacao', 'assessoria', 'consultoria',
            'consultor', 'consultora', 'engenheiro', 'engenharia',
            'arquiteto', 'arquitetura', 'arquiteto', 'arquitetura',
            'advogado', 'advogada', 'advogados', 'advogada', 'advogados',
            
            # Conectores e preposições compostas
            'junto', 'perante', 'mediante', 'durante', 'apos', 'sobre',
            'sob', 'ate', 'desde', 'entre', 'contra', 'por', 'para',
            'com', 'sem',
            
            # Sufixos e designações familiares
            'junior', 'jr', 'senior', 'sr', 'filho', 'filha', 'neto',
            'neta', 'sobrinho', 'sobrinha', 'primo', 'prima', 'tio', 'tia',
            'avo', 'avoa',

            # Outros termos comuns em nomes empresariais
            'grupo', 'holding', 'participacoes', 'empreendimentos',
            'administracao', 'gestao', 'negocios', 'comercial',
            'industrial', 'brasil', 'brasileiro', 'brasileira', 'nacional',
            'internacional', 'global', 'local', 'regional',
            'fundacao', 'fundacao', 'fundacao', 'fundacao',        ]
        
        # Remove caracteres especiais mantendo apenas letras, números e espaços
        # Substitui múltiplos espaços por um único espaço
        normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Divide o texto em palavras
        palavras = normalized.split()
        
        # Remove palavras comuns e garante tamanho mínimo
        palavras_filtradas = [
            palavra for palavra in palavras 
            if palavra not in palavras_para_remover 
            and len(palavra) > 1  # Remove palavras com apenas 1 caractere
        ]
        
        # Se após a filtragem não sobrar nenhuma palavra, retorna a string vazia
        if not palavras_filtradas:
            return ""
        
        # Junta as palavras novamente
        resultado = ' '.join(palavras_filtradas)
        
        # Remove espaços extras que possam ter sido criados
        resultado = resultado.strip()
        
        # Log para debug
        if resultado != name.lower():
            logger.debug(f"Nome normalizado: '{name}' -> '{resultado}'")
        
        return resultado

    def extract_process_details(self, process_id, grid_data):
        """Extrai detalhes completos de um processo específico"""
        process_start = time.time()
        total_time = 0

        try:
            if not process_id:
                logger.warning(f"ID do processo não fornecido")
                return None
                
            # Navega para a página de detalhes do processo
            nav_start = time.time()
            details_url = f"https://cetelem.djur.adv.br/processo/details/{process_id}"
            logger.info(f"Acessando detalhes do processo: {details_url}")
            self.driver.get(details_url)
            total_time += self._log_time(nav_start, "Navegação para página de detalhes")
            
            # Aguarda carregamento inicial
            try:
                load_start = time.time()
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "panel-body"))
                )
                total_time += self._log_time(load_start, "Carregamento inicial da página")
            except TimeoutException:
                logger.warning(f"Timeout aguardando carregamento da página de detalhes do processo {process_id}")
                return None
            
            process_details = {
                'processo': {},
                'partes': {},
                'financeiro': {},
                'detalhes_acordo': {}
            }

            # Extrai os dados do processo da página
            status_pagina = self.safe_get_text("//td[strong[text()='Status:']]/following-sibling::td")
            escritorio_pagina = self.safe_get_text("//td[strong[text()='Escritório / Célula:']]/following-sibling::td")
            data_cadastro = self.safe_get_text("//td[strong[text()='Data de Cadastro:']]/following-sibling::td")
            
            # Se os dados da página estiverem vazios, usa os dados do grid
            status_final = status_pagina
            escritorio_final = escritorio_pagina
            
            if grid_data and len(grid_data) > 8:
                if not status_pagina or status_pagina.strip() in ['', 'N/A']:
                    status_final = grid_data[8]  # Status está na posição 8
                    logger.info(f"Usando status do grid_data: {status_final}")
                
                if not escritorio_pagina or escritorio_pagina.strip() in ['', 'N/A']:
                    escritorio_final = grid_data[7]  # Escritório está na posição 7
                    logger.info(f"Usando escritório do grid_data: {escritorio_final}")

            numero_processo = grid_data[0].get('grid_data')[2]
            if numero_processo == '':
                numero_processo = self.safe_get_text("//td[strong[text()='Número do Processo:']]/following-sibling::td")
                    
            process_details['processo'] = {
                'numero': numero_processo,
                'escritorio_celula': escritorio_final,
                'comarca': self.safe_get_text("//td[strong[text()='Comarca:']]/following-sibling::td"),
                'fase': self.safe_get_text("//td[strong[text()='Fase']]/following-sibling::td"),
                'status': status_final,
                'data_cadastro': data_cadastro
            }

            # Extrai dados das partes primeiro para ter os nomes para comparação
            try:
                parties_start = time.time()
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
                total_time += self._log_time(parties_start, "Extração dos dados das partes")
                
                # Armazena grid_data apenas para validação de suspeita de fraude
                if grid_data:
                    process_details['grid_data'] = grid_data
                
                # Popula polo ativo
                if 'parte_adversa' in process_details['partes'] and process_details['partes']['parte_adversa']:
                    process_details['partes']['polo_ativo'] = [{
                        'nome': process_details['partes']['parte_adversa'].replace('AUTOR - ', ''),
                        'cpf_cnpj': process_details['partes'].get('cpf_cnpj_parte_adverso', ''),
                        'tipo': 'AUTOR'
                    }]
            
            except Exception as e:
                logger.error(f"Erro ao extrair dados das partes: {str(e)}")
                process_details['partes'] = {}

            # Extrai dados financeiros
            try:
                financial_start = time.time()
                # Aguarda e clica na aba financeira
                financial_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="#box-financeiro"]'))
                )
                self.driver.execute_script("arguments[0].click();", financial_tab)
                
                # Aguarda o carregamento da tabela financeira
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#financeiroList table.table-hover"))
                )
                
                # Extrai os dados financeiros (apenas lançamentos)
                process_details['financeiro'] = self.financial_scraper.extract_financial_data(process_id)
                total_time += self._log_time(financial_start, "Extração dos dados financeiros")
                
                # Verifica se há acordos nos lancamentos financeiros
                if process_details['financeiro'] and 'lancamentos' in process_details['financeiro']:
                    acordos = process_details['financeiro']['lancamentos']  # Todos os lançamentos já são acordos
                    
                    logger.info(f"Encontrados {len(acordos)} acordos para processar")
                    
                    # Para cada acordo encontrado, extrai os detalhes
                    for idx, acordo in enumerate(acordos, 1):
                        acordo_start = time.time()
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
                                    
                                    # Aguarda o carregamento da tabela principal e extrai suas linhas
                                    table = WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-striped"))
                                    )
                                    
                                    # Aguarda a tabela estar realmente carregada
                                    WebDriverWait(self.driver, 5).until(
                                        lambda d: len(d.find_elements(By.CSS_SELECTOR, "table.table-striped tr")) > 0
                                    )
                                    
                                    rows = table.find_elements(By.TAG_NAME, "tr")
                                    if not rows:
                                        logger.error("Tabela de detalhes do acordo está vazia")
                                        self.driver.get(current_url)
                                        continue
                                    
                                    logger.info(f"Tabela carregada com {len(rows)} linhas")
                                    
                                    # Extrai os detalhes do acordo
                                    acordo_details = {}
                                    
                                    # Mapeamento de campos
                                    field_mapping = {
                                        'numero': 'Número',
                                        'parte_adversa': 'Parte Adversa',
                                        'valor': 'Valor',
                                        'status': 'Status',
                                        'escritorio_celula': 'Escritório/Célula',
                                        'comarca': 'Comarca',
                                        'estado': 'Estado',
                                        'fase': 'Fase',
                                        'advogado_adverso': 'Advogado Adverso',
                                        'cpf_cnpj_parte_adverso': 'CPF/CNPJ Parte Adversa',
                                        'nome_titular': 'Nome do Titular',
                                        'cpf_titular': 'CPF do Titular',
                                        'data_pagamento': 'Data Pagamento'  # Ajustado para corresponder ao campo na tabela
                                    }
                                    
                                    # Extrai valores da tabela
                                    for row in rows:
                                        try:
                                            cells = row.find_elements(By.TAG_NAME, "td")
                                            if len(cells) >= 3:
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
                                                    for campo, campo_label in field_mapping.items():
                                                        if campo_label == label:
                                                            acordo_details[campo] = value
                                                        
                                                # Pega o label da segunda célula
                                                if len(cells) >= 2:
                                                    if cells[2].text != '': 
                                                        label_element = cells[2].find_element(By.TAG_NAME, "strong")   
                                                        if label_element:
                                                            label = label_element.text.strip().replace(":", "")
                                                            value = cells[3].text.strip()
                                                                
                                                            # Procura o campo correspondente ao label
                                                            for campo, campo_label in field_mapping.items():
                                                                if campo == 'nome_titular':
                                                                    if acordo_details.get(label) == '':
                                                                        acordo_details[campo] = value
                                                                        break
                                                                else:
                                                                    if campo_label == label:
                                                                        acordo_details[campo] = value
                                                                        break
                                                                                                                                                    
                                        except Exception as e:
                                            logger.debug(f"Erro ao processar linha da tabela: {str(e)}")
                                            continue
                                    
                                    # Marca o lancamento como acordo e verifica suspeita de fraude
                                    acordo_details['is_acordo'] = 'Sim'
                                    nome_titular = acordo_details.get('nome_titular', '')
                                    cpf_titular = acordo_details.get('cpf_titular', '')
                                    
                                    # Verifica suspeita de fraude apenas se tivermos um nome de titular
                                    if nome_titular:
                                        suspeita_fraude = 'Não'
                                        if self.check_name_matches(nome_titular, process_details, grid_data):
                                            suspeita_fraude = 'Sim'
                                            
                                        acordo_details['suspeita_fraude'] = suspeita_fraude
                                        
                                        # Atualiza o campo no grid financeiro
                                        logger.info(f"Atualizando suspeita de fraude para '{suspeita_fraude}' no acordo {acordo_link}")
                                        if not self.financial_scraper.update_acordo_suspeita_fraude(acordo_link, suspeita_fraude):
                                            logger.warning(f"Não foi possível atualizar suspeita de fraude no grid para o acordo {acordo_link}")
                                    else:
                                        logger.warning(f"Nome do titular não encontrado para o acordo {acordo_link}")
                                        acordo_details['suspeita_fraude'] = 'Não'
                                    
                                    # Adiciona o acordo extraído à lista
                                    if acordo_details:
                                        process_details['detalhes_acordo'] = {'acordo': acordo_details}
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

            # Log do tempo total no final
            self._log_time(process_start, f"TEMPO TOTAL do processo {process_id}")
            logger.info(f"[RESUMO] Processo {process_id} - Tempo total: {total_time:.2f} segundos")
            
            return process_details
            
        except Exception as e:
            logger.error(f"Erro ao extrair detalhes do processo: {str(e)}")
            return None

    def extract_parties_data(self):
        """Extrai dados das partes"""
        parties_data = {}
        max_retries = 3
        base_delay = 0.5
        
        def is_element_ready(element):
            """Verifica se o elemento está realmente pronto para interação"""
            try:
                return (element.is_displayed() and 
                       element.is_enabled() and 
                       element.get_attribute('innerHTML').strip() != '')
            except:
                return False

        def wait_for_element_state(locator, timeout=10):
            """Espera elemento estar pronto para interação com verificação de estado"""
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located(locator)
                )
                # Aguarda até que o elemento esteja realmente pronto
                WebDriverWait(self.driver, timeout).until(
                    lambda d: is_element_ready(element)
                )
                return element
            except:
                return None

        for attempt in range(max_retries):
            try:
                # Tenta localizar e verificar o accordion
                accordion = wait_for_element_state((By.ID, "accordion-dadosBasicos"))
                if not accordion:
                    delay = base_delay * (2 ** attempt)  # Backoff exponencial
                    logger.debug(f"Tentativa {attempt + 1}: Accordion não encontrado. Aguardando {delay}s")
                    time.sleep(delay)
                    continue

                # Verifica se precisamos expandir o accordion
                if not accordion.is_displayed():
                    toggle = accordion.find_element(By.CSS_SELECTOR, ".accordion-toggle")
                    if toggle and toggle.is_displayed():
                        toggle.click()
                        # Aguarda a expansão do accordion
                        WebDriverWait(self.driver, 2).until(
                            lambda d: accordion.is_displayed()
                        )

                # Extrai parte adversa
                for parte_label in ["Parte Adversa:", "Autor:", "Requerente:"]:
                    xpath_parte = f"//td[strong[normalize-space()='{parte_label}']]/following-sibling::td"
                    parte_element = wait_for_element_state((By.XPATH, xpath_parte), timeout=2)
                    if parte_element:
                        parte_name = parte_element.text.strip()
                        if parte_name:
                            parties_data['parte_adversa'] = parte_name
                            logger.info(f"Parte adversa encontrada: {parte_name}")
                            break
            
                # Extrai CPF/CNPJ da parte adversa
                for cpf_label in ["CPF/CNPJ Parte Adversa:", "CPF/CNPJ Autor:", "CPF/CNPJ Requerente:"]:
                    xpath_cpf = f"//td[strong[normalize-space()='{cpf_label}']]/following-sibling::td"
                    cpf_element = wait_for_element_state((By.XPATH, xpath_cpf), timeout=2)
                    if cpf_element:
                        cpf_value = cpf_element.text.strip()
                        if cpf_value:
                            parties_data['cpf_cnpj_parte_adverso'] = cpf_value
                            logger.info(f"CPF/CNPJ da parte adversa encontrado: {cpf_value}")
                            break

                # Extrai advogado interno
                xpath_adv_interno = "//td[strong[normalize-space()='Advogado Interno:']]/following-sibling::td"
                adv_interno_element = wait_for_element_state((By.XPATH, xpath_adv_interno), timeout=2)
                if adv_interno_element:
                    adv_interno = adv_interno_element.text.strip()
                    if adv_interno:
                        parties_data['advogado_interno'] = adv_interno
                        logger.info(f"Advogado interno encontrado: {adv_interno}")

                # Extrai advogados adversos
                advogados = []
                i = 1
                max_advogados = 10

                while i <= max_advogados:
                    prefix = ""
                    if i == 1:
                        prefix = "Advogado Adverso:"
                    elif i == 2:
                        prefix = "Segundo Advogado Adverso:"
                    elif i == 3:
                        prefix = "Terceiro Advogado Adverso:"
                    else:
                        prefix = f"{i}º Advogado Adverso:"

                    # Tenta diferentes estratégias de localização
                    for xpath in [
                        f"//td[strong[normalize-space()='{prefix}']]/following-sibling::td",
                        f"//td[contains(normalize-space(.), '{prefix}')]/following-sibling::td"
                    ]:
                        element = wait_for_element_state((By.XPATH, xpath), timeout=2)
                        if element:
                            adv_name = element.text.strip()
                            if adv_name:
                                advogados.append({'nome': adv_name})
                                logger.info(f"Advogado adverso encontrado: {adv_name}")
                                break
                    else:
                        # Se nenhuma estratégia funcionou, provavelmente não há mais advogados
                        break

                    i += 1

                if advogados:
                    parties_data['advogados_adversos'] = advogados
            
                # Retorna todos os dados coletados
                return parties_data
        
            except Exception as e:
                delay = base_delay * (2 ** attempt)
                logger.debug(f"Tentativa {attempt + 1} falhou: {str(e)}. Aguardando {delay}s")
                time.sleep(delay)
                continue

        logger.error("Todas as tentativas de extrair dados das partes falharam")
        return parties_data

    def safe_get_text(self, xpath):
        """
        Extrai texto de um elemento de forma segura, garantindo que o elemento
        esteja presente e visível antes de tentar extrair seu texto.
        """
        try:
            # Espera o elemento estar presente e visível
            element = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            
            # Verifica se o elemento está realmente visível e tem texto
            if element.is_displayed():
                text = element.text.strip()
                # Algumas vezes o texto pode estar em um atributo value ou innerText
                if not text:
                    text = element.get_attribute("value") or element.get_attribute("innerText")
                return text.strip() if text else ""
            
            return ""
            
        except Exception:
            return ""
