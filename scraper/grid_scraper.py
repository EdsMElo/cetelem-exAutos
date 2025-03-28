from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging
import re
from .process_details_scraper import ProcessDetailsScraper
import traceback
from database.db_manager import DatabaseManager  # Corrigindo o import
from config import get_logger

logger = get_logger(__name__)

class GridScraper:
    def __init__(self, driver):
        self.driver = driver
        self.process_details_scraper = ProcessDetailsScraper(driver)
        
    def wait_for_grid_load(self, timeout=30):
        """Aguarda o carregamento completo do grid com retentativas"""
        start_time = time.time()
        retry_interval = 2
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Aguarda o desaparecimento do blockUI
                logger.info("Aguardando remoção do blockUI...")
                try:
                    WebDriverWait(self.driver, 5).until_not(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.blockUI"))
                    )
                except TimeoutException:
                    logger.warning("BlockUI não encontrado ou já removido")

                # Verifica se há mensagem de erro na tela
                try:
                    error_msg = self.driver.find_element(By.CSS_SELECTOR, ".alert-danger, .error-message")
                    if error_msg.is_displayed():
                        error_text = error_msg.text
                        logger.error(f"Erro encontrado na tela: {error_text}")
                        return False
                except NoSuchElementException:
                    pass  # Não há mensagem de erro, continua normalmente

                # Aguarda a presença da tabela
                logger.info("Verificando presença da tabela...")
                table = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "gridProcessos"))
                )

                # Aguarda que a tabela esteja visível
                logger.info("Aguardando visibilidade da tabela...")
                WebDriverWait(self.driver, 5).until(
                    EC.visibility_of(table)
                )

                # Verifica se há linhas na tabela
                logger.info("Verificando linhas da tabela...")
                rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.gridrow, tr.gridrow_alternate")
                
                if len(rows) > 0:
                    logger.info(f"Grid carregado com sucesso. {len(rows)} linhas encontradas.")
                    return True
                else:
                    # Se não encontrou linhas, verifica se há mensagem de "nenhum resultado"
                    try:
                        no_results = self.driver.find_element(By.CSS_SELECTOR, ".no-results, .empty-grid")
                        if no_results.is_displayed():
                            logger.info("Grid carregado, mas nenhum resultado encontrado")
                            return True
                    except NoSuchElementException:
                        pass

                    logger.warning("Tabela encontrada mas sem linhas")
                    
            except Exception as e:
                elapsed_time = time.time() - start_time
                retry_count += 1
                
                if retry_count >= max_retries:
                    logger.error(f"Falha ao aguardar carregamento do grid após {max_retries} tentativas: {str(e)}")
                    return False
                
                logger.warning(f"Tentativa {retry_count} falhou. Aguardando {retry_interval}s antes de tentar novamente...")
                time.sleep(retry_interval)
                
                # Tenta rolar a página para atualizar
                try:
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                except Exception:
                    pass

        return False

    def wait_for_grid_return(self):
        """
        Aguarda o retorno ao grid de processos e garante que estamos na página correta
        Retorna: True se voltou ao grid corretamente, False caso contrário
        """
        try:
            # Aguarda até 10 segundos pelo carregamento da página
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "processoList"))
            )
            
            # Verifica se realmente voltamos para o grid
            grid = self.driver.find_element(By.ID, "processoList")
            if not grid:
                logger.error("Grid de processos não encontrado após retorno")
                return False
                
            # Verifica se a tabela dentro do grid está presente
            table = grid.find_element(By.CSS_SELECTOR, "table.table")
            if not table:
                logger.error("Tabela do grid não encontrada após retorno")
                return False
                
            # Verifica se há linhas na tabela
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            if not rows:
                logger.error("Nenhuma linha encontrada na tabela do grid após retorno")
                return False
                
            logger.info("Retorno ao grid confirmado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao aguardar retorno ao grid: {str(e)}")
            return False

    def return_to_grid(self):
        """
        Tenta retornar ao grid de processos de forma segura
        Retorna: True se conseguiu voltar, False caso contrário
        """
        try:
            max_attempts = 3
            for attempt in range(max_attempts):
                logger.info(f"Tentativa {attempt + 1} de {max_attempts} de retornar ao grid")
                
                # Tenta voltar usando history.back()
                self.driver.execute_script("window.history.back()")
                
                # Aguarda um pouco para a navegação iniciar
                time.sleep(1)
                
                # Verifica se voltamos para o grid
                if self.wait_for_grid_return():
                    return True
                
                # Se não voltou ao grid, tenta navegar diretamente
                if attempt == max_attempts - 1:
                    logger.warning("Tentando navegar diretamente para a página do grid")
                    try:
                        current_url = self.driver.current_url
                        base_url = current_url.split('/processo/')[0]
                        self.driver.get(f"{base_url}/processo")
                        return self.wait_for_grid_return()
                    except Exception as e:
                        logger.error(f"Erro ao navegar diretamente para o grid: {str(e)}")
                
            return False
            
        except Exception as e:
            logger.error(f"Erro ao tentar retornar ao grid: {str(e)}")
            return False

    def wait_for_grid_load_after_navigation(self, timeout=10):
        """Aguarda o carregamento do grid após navegação"""
        try:
            # Aguarda o desaparecimento do indicador de carregamento
            WebDriverWait(self.driver, timeout).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.blockUI"))
            )
            
            # Aguarda a tabela ficar visível
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table"))
            )
            
            # Pequena pausa para garantir que os dados foram carregados
            time.sleep(1)
            
            return True
        except Exception as e:
            logger.error(f"Erro ao aguardar carregamento do grid: {str(e)}")
            return False

    def get_total_records(self):
        """Extrai o número total de registros do texto de paginação"""
        try:
            # Lista de seletores possíveis para encontrar o total de registros
            selectors = [
                "//*[@id='processoList']/div[3]/div/div[1]/span",  # Seletor original
                "//div[contains(@class, 'dataTables_info')]",      # Seletor alternativo comum
                "//div[contains(text(), 'Exibindo')]",             # Busca por texto
                "//span[contains(text(), 'Exibindo')]"             # Busca por texto em span
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element and element.is_displayed():
                            text = element.text
                            # Procura por padrões comuns de texto
                            # Ex: "Exibindo 1-50 de 126", "Mostrando 1 até 50 de 126 registros"
                            matches = re.findall(r'\b(\d+)\b(?=[^\d]*$)', text)  # Pega o último número
                            if matches:
                                total = int(matches[0])
                                logger.info(f"Total de registros encontrados: {total}")
                                return total
                except Exception as e:
                    logger.debug(f"Erro ao tentar seletor {selector}: {str(e)}")
                    continue
            
            # Se não encontrou pelos seletores, tenta contar as linhas da tabela
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
                if rows:
                    total = len(rows)
                    logger.info(f"Total de registros obtido contando linhas: {total}")
                    return total
            except Exception as e:
                logger.debug(f"Erro ao contar linhas da tabela: {str(e)}")
            
            logger.warning("Não foi possível determinar o total de registros")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter total de registros: {str(e)}")
            return None

    def get_total_pages(self):
        """
        Determina o número total de páginas usando duas estratégias:
        1. Total de registros dividido por 50
        2. Maior número encontrado nos links de paginação
        """
        try:
            total_pages = 1
            
            # Estratégia 1: Total de registros / 50
            total_records = self.get_total_records()
            if total_records:
                calculated_pages = (total_records + 49) // 50  # Arredonda para cima
                total_pages = max(total_pages, calculated_pages)
                logger.info(f"Total de páginas calculado pelo total de registros ({total_records}): {calculated_pages}")
            
            # Estratégia 2: Maior número nos links de paginação
            try:
                # Encontra todos os links numéricos na paginação
                page_links = self.driver.find_elements(By.CSS_SELECTOR, "ul.pagination li a")
                for link in page_links:
                    page_num = self.get_page_number(link)
                    if page_num:
                        total_pages = max(total_pages, page_num)
                
                logger.info(f"Maior número encontrado nos links de paginação: {total_pages}")
            except Exception as e:
                logger.debug(f"Erro ao buscar links de paginação: {str(e)}")
            
            return total_pages
            
        except Exception as e:
            logger.error(f"Erro ao calcular total de páginas: {str(e)}")
            return 1

    def get_pagination_info(self):
        """Obtém informações sobre a paginação do grid"""
        try:
            # Primeiro obtém o total de registros e páginas
            total_records = self.get_total_records()
            total_pages = self.get_total_pages()
            
            # Procura o container de paginação
            pagination_items = self.driver.find_elements(By.XPATH, "//*[@id='processoList']/div[3]/div/div[2]/ul/li")
            if not pagination_items:
                logger.info("Não há paginação - grid com uma única página")
                return {
                    "has_pagination": False,
                    "current_page": 1,
                    "total_pages": 1,
                    "total_records": total_records or len(self.driver.find_elements(By.CSS_SELECTOR, "tbody tr"))
                }
            
            # Encontra a página atual
            current_page = 1
            try:
                active_page = self.driver.find_element(By.CSS_SELECTOR, "ul.pagination li.active a")
                if active_page:
                    page_num = self.get_page_number(active_page)
                    if page_num:
                        current_page = page_num
            except Exception as e:
                logger.debug(f"Erro ao encontrar página atual: {str(e)}")
            
            logger.info(f"Paginação encontrada: Página {current_page} de {total_pages}")
            return {
                "has_pagination": True,
                "current_page": current_page,
                "total_pages": total_pages,
                "total_records": total_records
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter informações de paginação: {str(e)}")
            return {
                "has_pagination": False,
                "current_page": 1,
                "total_pages": 1,
                "total_records": None
            }

    def click_next_page_button(self, next_button):
        """
        Tenta clicar no botão de próxima página usando diferentes estratégias
        """
        try:
            # Primeira tentativa: scroll até o elemento e clique normal
            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            time.sleep(1)  # Pequena pausa para o scroll terminar
            
            # Primeira tentativa: clique via JavaScript
            try:
                self.driver.execute_script("arguments[0].click();", next_button)
                return True
            except Exception as e:
                logger.debug(f"Clique via JavaScript falhou: {str(e)}")
            
            # Segunda tentativa: remover elementos que possam estar interceptando
            try:
                self.driver.execute_script("""
                    var elements = document.getElementsByClassName('username');
                    for(var i=0; i<elements.length; i++) {
                        elements[i].style.pointerEvents = 'none';
                    }
                """)
                next_button.click()
                return True
            except Exception as e:
                logger.debug(f"Clique após remover interceptadores falhou: {str(e)}")
            
            # Terceira tentativa: usar o href do botão
            try:
                href = next_button.get_attribute('href')
                if href:
                    current_url = self.driver.current_url
                    base_url = current_url.split('?')[0]  # Remove qualquer query string
                    new_url = f"{base_url}?page={href}"
                    self.driver.get(new_url)
                    return True
            except Exception as e:
                logger.debug(f"Navegação via URL falhou: {str(e)}")
            
            return False
            
        except Exception as e:
            logger.error(f"Todas as tentativas de clique falharam: {str(e)}")
            return False

    def get_page_number(self, element):
        """Extrai o número da página de um elemento <a>"""
        try:
            href = element.get_attribute('href')
            if not href:
                return None
                
            # Se for uma URL completa, pega só o último componente
            if '/' in href:
                href = href.split('/')[-1]
            
            # Remove qualquer query string
            if '?' in href:
                href = href.split('?')[0]
            
            # Converte para número
            if href.isdigit():
                return int(href)
            
            return None
        except Exception as e:
            logger.debug(f"Erro ao extrair número da página: {str(e)}")
            return None

    def find_next_page_button(self):
        """
        Encontra o botão de próxima página usando atributos mais confiáveis
        Retorna: O elemento do botão se encontrado, None caso contrário
        """
        try:
            # Primeiro tenta encontrar o elemento ativo atual
            active_page = self.driver.find_element(By.CSS_SELECTOR, "ul.pagination li.active a")
            if not active_page:
                logger.error("Não foi possível encontrar a página ativa atual")
                return None
                
            current_page = self.get_page_number(active_page)
            if not current_page:
                logger.error("Não foi possível determinar a página atual")
                return None
                
            next_page = current_page + 1
            logger.info(f"Página atual: {current_page}, procurando link para página {next_page}")
            
            # Lista de seletores para encontrar o botão de próxima página
            selectors = [
                # Procura pelo botão ">" com título específico
                "ul.pagination li a[title='Ir para página seguinte']",
                # Procura pelo símbolo ">" como texto
                "ul.pagination li a:not(.active)",
                # Procura por qualquer link não ativo
                "ul.pagination li:not(.active) a"
            ]
            
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    # Verifica se é realmente o botão de próxima página
                    href_page = self.get_page_number(element)
                    title = element.get_attribute('title')
                    text = element.text.strip()
                    
                    is_next_button = (
                        (href_page and href_page == next_page) or  # Link direto para próxima página
                        (title and 'Ir para página seguinte' in title.lower()) or  # Título contém "seguinte"
                        (text == '>')  # Texto é ">"
                    )
                    
                    if is_next_button:
                        # Verifica se o elemento pai não está desabilitado
                        parent = element.find_element(By.XPATH, "./..")
                        if 'disabled' not in parent.get_attribute('class'):
                            logger.info(f"Botão 'Próxima Página' encontrado: href_page={href_page}, title={title}, text={text}")
                            return element
            
            logger.info("Botão 'Próxima Página' não encontrado ou desabilitado")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao procurar botão de próxima página: {str(e)}")
            return None

    def catalog_processes(self):
        """Cataloga todos os processos do grid e seus links"""
        try:
            logger.info("Iniciando catalogação dos processos...")
            catalog = []
            
            # Obtém informações de paginação
            pagination_info = self.get_pagination_info()
            total_pages = pagination_info["total_pages"]
            total_records = pagination_info["total_records"]
            
            if total_records:
                logger.info(f"Total de registros a catalogar: {total_records} (em {total_pages} páginas)")
            else:
                total_records = total_pages * 50
                logger.info(f"Total estimado de registros: {total_records} (em {total_pages} páginas)")
            
            current_page = 1
            processed_total = 0
            
            while current_page <= total_pages:
                logger.info(f"Catalogando página {current_page}/{total_pages} ({(current_page/total_pages)*100:.1f}%)")
                
                # Aguarda carregamento da tabela
                table = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.table"))
                )
                
                # Encontra todas as linhas da tabela
                rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                rows_in_page = len(rows)
                logger.info(f"Encontradas {rows_in_page} linhas na página atual")
                
                # Processa cada linha para extrair informações básicas
                for row_index, row in enumerate(rows, 1):
                    try:
                        processed_total += 1
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 10:
                            continue
                            
                        # Extrai dados básicos da linha
                        cell_data = [cell.text.strip() for cell in cells]
                        
                        # Extrai o ID e link do processo
                        process_link = cells[0].find_element(By.TAG_NAME, "a")
                        process_id = process_link.get_attribute("data-id") or cell_data[1]
                        details_url = process_link.get_attribute("href")

                        # Primeiro verifica se o processo existe no banco de dados
                        db = DatabaseManager()
                        existing_process = db.get_process_by_id(process_id)

                        if not existing_process:                      
                            # Monta o registro do catálogo
                            catalog_entry = {
                                'id': process_id,
                                'details_url': details_url,
                                'origem': 'scrape',
                                'grid_data': [
                                    process_id,              # ID do processo
                                    cell_data[1],            # Numero do Processo
                                    cell_data[2],            # Adverso
                                    cell_data[3],            # CPF/CNPJ
                                    cell_data[4],            # Comarca
                                    cell_data[5],            # Estado
                                    cell_data[6],            # Tipo
                                    cell_data[7],            # Status
                                    cell_data[8],            # Escritório
                                    False,                   # Tem acordo?
                                    False,                   # Suspeita de fraude
                                ]
                            }
                        else:
                            # Monta o registro do catálogo vindo da base de dados
                            catalog_entry = {
                                'id': process_id,
                                'details_url': details_url,
                                'origem': 'base',
                                'base_data': existing_process,
                                'grid_data': [
                                    process_id,                                       # ID do processo
                                    existing_process.get('numero'),                   # Numero do Processo
                                    existing_process.get('parte_adversa'),            # Adverso
                                    existing_process.get('cpf_cnpj_parte_adverso'),   # CPF/CNPJ
                                    existing_process.get('comarca'),                  # Comarca
                                    existing_process.get('estado'),                   # Estado
                                    existing_process.get('fase'),                     # Tipo
                                    existing_process.get('status'),                   # Status
                                    existing_process.get('escritorio_celula'),        # Escritório
                                    existing_process.get('tem_acordo'),               # Tem acordo?
                                    existing_process.get('suspeita_fraude'),          # Suspeita de fraude
                                ]
                            }

                        catalog.append(catalog_entry)
                        
                    except Exception as e:
                        logger.error(f"Erro ao catalogar linha {row_index} da página {current_page}: {str(e)}")
                        continue
                
                # Navega para a próxima página se não for a última
                if current_page < total_pages:
                    next_button = self.find_next_page_button()
                    if next_button and self.click_next_page_button(next_button):
                        time.sleep(2)
                        self.wait_for_grid_load_after_navigation()
                        current_page += 1
                    else:
                        break
                else:
                    break
            
            logger.info(f"Catalogação concluída. Total de {len(catalog)} processos catalogados")
            return catalog
            
        except Exception as e:
            logger.error(f"Erro ao catalogar processos: {str(e)}")
            return []

    def extract_grid_data(self):
        """Extrai dados do grid de processos usando o catálogo"""
        try:
            logger.info("Iniciando extração de dados do grid...")
            
            # Cataloga todos os processos primeiro
            catalog = self.catalog_processes()
            if not catalog:
                logger.error("Não foi possível catalogar os processos")
                return {
                    "grid_data": [],
                    "raw_data": {},
                    "total_pages": 0,
                    "total_records": 0
                }
            
            # Inicializa estruturas de dados
            extracted_data = []
            raw_data = {}
            total_records = len(catalog)
            
            # Processa cada processo do catálogo
            for index, entry in enumerate(catalog, 1):
                try:
                    logger.info(f"Processando registro {index}/{total_records}")
                    
                    if entry['origem'] == 'scrape':
                        # Navega para a página de detalhes
                        self.driver.get(entry['details_url'])

                        # Se não existe, faz o scrape
                        logger.info(f"Processo {entry['id']} não encontrado no banco, realizando scrape")
                        process_details = self.process_details_scraper.extract_process_details(entry['id'], catalog)

                        # Se o scrape foi bem sucedido, salva no banco
                        if process_details:
                            try:
                                # Armazena os detalhes do processo
                                raw_data[entry['id']] = process_details

                                process_details = {
                                    'processo': {
                                        'id': entry['id'],
                                        'numero': entry['grid_data'][2],
                                        'escritorio_celula': process_details.get('processo', {}).get('escritorio_celula', ''),
                                        'comarca': entry['grid_data'][5],
                                        'estado': entry['grid_data'][6],
                                        'status': entry['grid_data'][8],
                                        'fase': process_details.get('processo', {}).get('fase', '')
                                    },
                                    'partes': {
                                        'parte_adversa': entry['grid_data'][3],
                                        'cpf_cnpj_parte_adverso': entry['grid_data'][4],
                                        'advogados_adversos': process_details.get('partes', {}).get('advogados_adversos', [])
                                    },
                                    'detalhes_acordo': process_details.get('detalhes_acordo', {}).get('acordo', [])
                                }

                                db = DatabaseManager()
                                db.save_process_data(raw_data, entry['grid_data'], entry['id'])
                                logger.info(f"Processo {entry['id']} salvo no banco de dados após scrape")

                                # Leva o process_details com a estrutura completa com os detalhes do processo
                                raw_data[entry['id']] = process_details

                            except Exception as e:
                                logger.error(f"Erro ao salvar processo {entry['id']} no banco após scrape: {str(e)}")                                
                    else:                    
                        # Primeiro verifica se o processo existe no banco de dados
                        existing_process = entry['base_data']

                        # Se existe no banco, usa os dados existentes
                        logger.info(f"Processo {entry['id']} encontrado no banco de dados, usando dados existentes")
                        process_details = {
                            'processo': {
                                'id': existing_process['id'],
                                'numero': existing_process['numero'],
                                'escritorio_celula': existing_process['escritorio_celula'],
                                'comarca': existing_process['comarca'],
                                'estado': existing_process['estado'],
                                'status': existing_process['status'],
                                'fase': existing_process['fase'],
                                'tem_acordo': existing_process['tem_acordo'],
                                'suspeita_fraude': existing_process['suspeita_fraude']
                            },
                            'partes': existing_process['partes'],
                            'detalhes_acordo': existing_process.get('acordo', [])
                        }
                        raw_data[entry['id']] = process_details
                    
                    # Adiciona os dados à lista do grid
                    extracted_data.append(entry['grid_data'])
                    
                except Exception as e:
                    logger.error(f"Erro ao processar processo {entry['id']}: {str(e)}")
                    continue
            
            logger.info(f"Processamento concluído. Total de {len(extracted_data)} registros extraídos")
            return {
                'grid_data': extracted_data,
                'raw_data': raw_data,
                'total_pages': (total_records + 49) // 50,  # Calcula número de páginas
                'total_records': total_records
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do grid: {str(e)}")
            return {
                "grid_data": [],
                "raw_data": {},
                "total_pages": 0,
                "total_records": 0
            }
