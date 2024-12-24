from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging
from .process_details_scraper import ProcessDetailsScraper

logger = logging.getLogger(__name__)

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

    def wait_for_grid_return(self, timeout=10):
        """Aguarda o retorno ao grid após extração de detalhes"""
        try:
            # Aguarda apenas a presença e visibilidade da tabela
            table = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table"))
            )
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of(table)
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao aguardar retorno ao grid: {str(e)}")
            return False

    def extract_grid_data(self, max_rows=None):
        """Extrai dados do grid de processos"""
        try:
            logger.info("Iniciando extração de dados do grid...")
            
            # Aguarda carregamento da tabela
            logger.info("Buscando tabela de processos...")
            table = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table"))
            )
            
            # Encontra todas as linhas da tabela (exceto cabeçalho)
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            logger.info(f"Encontradas {len(rows)} linhas na tabela")
            
            # Limita o número de linhas se necessário
            if max_rows and max_rows < len(rows):
                rows = rows[:max_rows]
            
            # Inicializa lista de resultados
            extracted_data = []
            raw_data = {}
            
            # Processa cada linha da tabela
            processed = 0
            for row in rows:
                try:
                    # Captura todos os dados necessários da linha antes de navegar
                    cells = row.find_elements(By.TAG_NAME, "td")
                    logger.info(f"Número de células encontradas: {len(cells)}")
                    
                    if len(cells) < 10:
                        logger.warning(f"Linha ignorada - número insuficiente de células: {len(cells)}")
                        continue
                    
                    # Captura todos os dados da linha
                    cell_data = [cell.text.strip() for cell in cells]
                    
                    # Extrai o ID do processo
                    try:
                        process_id = cells[0].find_element(By.TAG_NAME, "a").get_attribute("data-id")
                        if not process_id:
                            process_id = cell_data[1]  # Usa o ID da linha como fallback
                    except Exception as e:
                        logger.warning(f"Erro ao extrair ID do processo: {str(e)}")
                        process_id = cell_data[1]  # Usa o ID da linha como fallback
                        
                    # Extrai detalhes do processo
                    process_details = self.process_details_scraper.extract_process_details(process_id, grid_data=None)
                    
                    # Monta row_data com os dados capturados
                    row_data = [
                        process_id,              # ID do processo
                        cell_data[1],            # Numero do Processo
                        cell_data[2],            # Adverso
                        cell_data[3],            # CPF/CNPJ
                        cell_data[4],            # Comarca
                        cell_data[5],            # Estado
                        cell_data[6],            # Tipo
                        cell_data[7],            # Status
                        cell_data[8],            # Escritório
                        # Se existe qualquer lançamento do tipo ACORDO, marca como Sim
                        'Sim' if any(l.get('tipo', '').upper() == 'ACORDO' for l in (process_details or {}).get('financeiro', {}).get('lancamentos', [])) else 'Não',
                        # Para suspeita de fraude, pega o valor do primeiro acordo encontrado
                        next((l.get('suspeita_fraude', 'N/A') for l in (process_details or {}).get('financeiro', {}).get('lancamentos', []) if l.get('tipo', '').upper() == 'ACORDO'), 'N/A')
                    ]
                    
                    # Adiciona os dados à lista do grid
                    extracted_data.append(row_data)
                    
                    # Armazena os detalhes do processo usando o ID como chave
                    if process_details:
                        raw_data[process_id] = process_details
                    
                    # Retorna à página do grid após extrair os detalhes
                    self.driver.execute_script("window.history.back()")
                    
                    # Aguarda o retorno ao grid de forma otimizada
                    if not self.wait_for_grid_return():
                        logger.error("Falha ao retornar ao grid após processar detalhes")
                        continue
                    
                    # Atualiza a referência da tabela e das linhas após voltar ao grid
                    table = self.driver.find_element(By.CSS_SELECTOR, "table.table")
                    rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                    if max_rows and max_rows < len(rows):
                        rows = rows[processed:]  # Continua do ponto onde parou
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao processar linha {processed}: {str(e)}")
                    continue
            
            logger.info(f"Processamento concluído. {processed} linhas extraídas com sucesso.")
            return {
                'grid_data': extracted_data,  # Mantém o formato de lista para o grid
                'raw_data': raw_data         # Dicionário com detalhes indexados por ID
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do grid: {str(e)}")
            return {"grid_data": [], "raw_data": {}}
