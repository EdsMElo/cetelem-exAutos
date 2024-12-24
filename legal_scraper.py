import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import pyotp
import os
from dotenv import load_dotenv
import logging
import json
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
import traceback
from bs4 import BeautifulSoup, Comment
from scraper import GridScraper, ProcessDetailsScraper

# Configurar logging
logging.basicConfig(level=logging.INFO)

class LegalScraper:
    def __init__(self, headless=True, max_rows=None, enable_screenshots=False):
        """
        Inicializa o scraper
        Args:
            headless (bool): Se True, executa em modo headless. Se False, mostra o navegador
            max_rows (int): Número máximo de linhas a extrair do grid. Valores possíveis: [1, 5, 10, 50, 100, None (todos)]
            enable_screenshots (bool): Se True, captura screenshots durante a extração
        """
        self.driver = None
        self.base_url = "https://cetelem.djur.adv.br/"
        self.headless = headless
        self.max_rows = max_rows
        self.enable_screenshots = enable_screenshots
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        self.username = os.getenv("DJUR_USERNAME")
        self.password = os.getenv("DJUR_PASSWORD")
        self.mfa_secret = os.getenv("DJUR_MFA_SECRET")
        self.totp = pyotp.TOTP(self.mfa_secret) if self.mfa_secret else None
        
        # Cria diretório para screenshots e logs HTML apenas se necessário
        self.screenshot_dir = os.path.join(os.getcwd(), "screenshots")
        self.html_logs_dir = os.path.join(os.getcwd(), "html_logs")
        if self.enable_screenshots:
            for dir_path in [self.screenshot_dir, self.html_logs_dir]:
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
        
        # Cria diretório para screenshots se não existir
        if self.enable_screenshots:
            self.screenshot_dir = os.path.join(os.getcwd(), "screenshots")
            if not os.path.exists(self.screenshot_dir):
                os.makedirs(self.screenshot_dir)

    def initialize(self):
        """Inicializa o driver e faz login no sistema"""
        try:
            if self.driver is None:
                self._setup_driver()
                success, message = self.auto_login()
                if not success:
                    raise Exception(f"Falha no login: {message}")
                self.logger.info("Scraper inicializado com sucesso")
                return True
            return True
        except Exception as e:
            self.logger.error(f"Erro ao inicializar o scraper: {str(e)}")
            self.close()
            raise

    def _setup_driver(self):
        """Configura o driver do Selenium"""
        try:
            options = uc.ChromeOptions()
            
            # Configurações básicas
            options.add_argument('--no-sandbox')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-extensions')
            
            if self.headless:
                self.logger.info("Iniciando o Chrome em modo headless...")
                options.add_argument('--headless=new')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--start-maximized')
                options.add_argument('--disable-setuid-sandbox')
                options.add_argument('--disable-infobars')
                options.add_argument('--ignore-certificate-errors')
                options.add_argument('--allow-running-insecure-content')
                options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
            else:
                self.logger.info("Iniciando o Chrome em modo guiado...")
            
            # Inicializa o driver com as opções configuradas
            self.driver = uc.Chrome(options=options)
            self.logger.info("Chrome iniciado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao configurar o driver: {str(e)}")
            raise

    def ensure_logged_in(self):
        """Garante que o usuário está logado antes de executar operações"""
        if not self.driver:
            self.initialize()
        try:
            # Tenta acessar uma página que requer login
            self.driver.get("https://cetelem.djur.adv.br/processo/list?cache=false")
            # Se não encontrar o formulário de login, assume que está logado
            if not self._is_login_page():
                return True
            # Se encontrar o formulário de login, tenta fazer login novamente
            success, message = self.auto_login()
            if not success:
                raise Exception(f"Falha ao reconectar: {message}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao verificar login: {str(e)}")
            raise

    def _is_login_page(self):
        """Verifica se está na página de login"""
        try:
            return bool(self.driver.find_elements(By.ID, "Email"))
        except:
            return False

    def get_mfa_code(self):
        """Gera o código MFA atual"""
        if not self.totp:
            raise ValueError("MFA secret não configurado")
        return self.totp.now()
        
    def wait_and_find_element(self, by, value, timeout=10, description="elemento"):
        """Função auxiliar para esperar e encontrar elementos"""
        try:
            self.logger.info(f"Aguardando {description}...")
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            self.logger.info(f"{description} encontrado")
            return element
        except TimeoutException:
            self.logger.error(f"Timeout aguardando {description}")
            raise
        
    def take_screenshot(self, name):
        """Captura screenshot da página atual"""
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{timestamp}_{name}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            self.driver.save_screenshot(filepath)
            self.logger.info(f"Screenshot salvo: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Erro ao capturar screenshot: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
            return None

    def save_page_source(self, name):
        """Salva o código fonte da página atual de forma limpa e compacta"""
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{timestamp}_{name}.html"
            filepath = os.path.join(self.html_logs_dir, filename)
            
            # Obtém o HTML da página
            page_source = self.driver.page_source
            
            # Parse o HTML
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Remove scripts e estilos
            for script in soup(["script", "style", "link", "meta", "noscript"]):
                script.decompose()
                
            # Remove atributos desnecessários
            for tag in soup.find_all():
                # Lista de atributos a manter
                keep_attrs = ['href', 'src', 'id', 'class', 'type']
                attrs = dict(tag.attrs)
                for attr in attrs:
                    if attr not in keep_attrs:
                        del tag[attr]
            
            # Remove comentários HTML
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            # Remove espaços em branco extras
            cleaned_html = str(soup).replace('\\n', '').replace('\\t', '')
            cleaned_html = ' '.join(cleaned_html.split())
            
            # Salva o HTML limpo
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(cleaned_html)
                
            self.logger.info(f"HTML source salvo: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar HTML source: {str(e)}")
            return None

    def auto_login(self):
        """Realiza o login automaticamente usando as credenciais do .env"""
        try:
            if not all([self.username, self.password, self.mfa_secret]):
                return False, "Credenciais não configuradas no arquivo .env"
                
            if not self.driver:
                if not self.initialize_driver():
                    return False, "Falha ao inicializar o Chrome"
            
            self.logger.info(f"Acessando {self.base_url}")
            self.driver.get(self.base_url)
            if self.enable_screenshots:
                self.take_screenshot("01_pagina_inicial")
            
            # Aguarda a página carregar completamente
            time.sleep(3)
            
            # Log do título da página
            self.logger.info(f"Título da página: {self.driver.title}")
            
            # Aguarda e preenche o campo de email
            email_field = self.wait_and_find_element(
                By.ID, "Email", 
                description="campo de email"
            )
            email_field.clear()
            email_field.send_keys(self.username)
            self.logger.info("Email preenchido")
            if self.enable_screenshots:
                self.take_screenshot("02_email_preenchido")
            
            # Aguarda e preenche o campo de senha
            password_field = self.wait_and_find_element(
                By.ID, "Senha",
                description="campo de senha"
            )
            password_field.clear()
            password_field.send_keys(self.password)
            self.logger.info("Senha preenchida")
            if self.enable_screenshots:
                self.take_screenshot("03_senha_preenchida")
            
            # Clica no botão de login
            login_button = self.wait_and_find_element(
                By.CSS_SELECTOR, "button.btn.btn-bricky",
                description="botão de login"
            )
            login_button.click()
            self.logger.info("Botão de login clicado")
            if self.enable_screenshots:
                self.take_screenshot("04_login_clicado")
            
            # Aguarda redirecionamento
            time.sleep(3)
            
            # Log da URL atual
            current_url = self.driver.current_url
            self.logger.info(f"URL atual: {current_url}")
            if self.enable_screenshots:
                self.take_screenshot("05_apos_login")
            
            # Verifica se fomos redirecionados para a página do Google Auth
            if "/Autorizador/googleAuth" in current_url:
                self.logger.info("Redirecionado para página do Google Auth")
                if self.enable_screenshots:
                    self.take_screenshot("06_pagina_mfa")
                
                # Aguarda o campo de código MFA
                mfa_field = self.wait_and_find_element(
                    By.NAME, "passcode",
                    description="campo de código MFA"
                )
                
                # Gera e insere o código MFA
                mfa_code = self.get_mfa_code()
                self.logger.info(f"Código MFA gerado: {mfa_code}")
                mfa_field.clear()
                mfa_field.send_keys(mfa_code)
                if self.enable_screenshots:
                    self.take_screenshot("07_mfa_preenchido")
                
                # Submete o código MFA - usando o botão correto
                mfa_submit = self.wait_and_find_element(
                    By.CSS_SELECTOR, "input[type='submit'].btn.btn-success",
                    description="botão de submit MFA"
                )
                mfa_submit.click()
                self.logger.info("Código MFA submetido")
                if self.enable_screenshots:
                    self.take_screenshot("08_mfa_submetido")
                
                # Aguarda redirecionamento com retry
                max_retries = 3
                retry_count = 0
                dashboard_loaded = False
                
                while retry_count < max_retries and not dashboard_loaded:
                    try:
                        # Aguarda um pouco mais para o redirecionamento
                        time.sleep(5)
                        
                        current_url = self.driver.current_url
                        self.logger.info(f"URL após MFA (tentativa {retry_count + 1}): {current_url}")
                        if self.enable_screenshots:
                            self.take_screenshot(f"09_tentativa_dashboard_{retry_count + 1}")
                        
                        if "/main" in current_url or "/home/Index" in current_url:
                            # Aguarda algum elemento do dashboard carregar
                            self.wait_and_find_element(
                                By.CLASS_NAME, "main-navigation-menu",
                                timeout=10,
                                description="menu principal do dashboard"
                            )
                            dashboard_loaded = True
                            self.logger.info("Dashboard carregado com sucesso")
                            if self.enable_screenshots:
                                self.take_screenshot("10_dashboard_carregado")
                            break
                    except Exception as e:
                        self.logger.warning(f"Tentativa {retry_count + 1} falhou: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
                        retry_count += 1
                
                if dashboard_loaded:
                    self.logger.info("Login completo com sucesso")
                    return True, "Login automático realizado com sucesso"
                else:
                    self.logger.error("Erro após submissão do MFA - Dashboard não carregou")
                    return False, "Erro ao carregar o dashboard após MFA"
            else:
                self.logger.error("Não redirecionou para página do Google Auth")
                if self.enable_screenshots:
                    self.take_screenshot("erro_redirecionamento_mfa")
                return False, "Erro no redirecionamento para autenticação MFA"
            
        except TimeoutException as e:
            self.logger.error(f"Timeout ao aguardar elemento: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
            return False, f"Timeout ao aguardar elemento: {str(e)}"
        except WebDriverException as e:
            self.logger.error(f"Erro do WebDriver: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
            return False, f"Erro do WebDriver: {str(e)}"
        except Exception as e:
            self.logger.error(f"Erro inesperado: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
            return False, f"Erro durante o login automático: {str(e)}"
            
    def search_processes(self, start_date=None, end_date=None, status=None, process_number=None):
        """Realiza a busca de processos com os filtros fornecidos"""
        try:
            # Aplica os filtros e realiza a busca
            self._apply_filters(
                start_date=start_date,
                end_date=end_date,
                status=status,
                process_number=process_number
            )
            
            # Instancia os scrapers específicos
            grid_scraper = GridScraper(self.driver)
            
            # Extrai dados do grid
            result = grid_scraper.extract_grid_data(self.max_rows)
            
            # Para cada processo que tem acordo, busca os detalhes adicionais
            if result and 'raw_data' in result:
                for process_id, process_data in result['raw_data'].items():
                    # Verifica se há lançamentos financeiros
                    if ('financeiro' in process_data and 
                        'lancamentos' in process_data['financeiro']):
                        
                        # Filtra apenas lançamentos do tipo ACORDO
                        acordos = [
                            lanc for lanc in process_data['financeiro']['lancamentos'] 
                            if lanc.get('tipo_lancamento', '').upper() == 'ACORDO'
                        ]
                        
                        # Se encontrou acordos, extrai os detalhes
                        if acordos:
                            self.logger.info(f"Encontrados {len(acordos)} acordos para o processo {process_id}")
                            
                            # Extrai os detalhes do acordo
                            acordo_details = self.extract_process_details(process_id)
                            if acordo_details and 'detalhes_acordo' in acordo_details:
                                process_data['detalhes_acordo'] = acordo_details['detalhes_acordo']
                                self.logger.info(f"Detalhes do acordo extraídos com sucesso para o processo {process_id}")
                            else:
                                self.logger.warning(f"Não foi possível extrair detalhes do acordo para o processo {process_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro durante a busca de processos: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
            raise

    def _apply_filters(self, start_date=None, end_date=None, status=None, process_number=None):
        """Aplica os filtros de busca no formulário"""
        try:
            # Aplica os filtros
            self.logger.info("Navegando para a página de consulta...")
            self.driver.get("https://cetelem.djur.adv.br/processo/list?cache=false")
            
            # Wait for page load and any blockUI to disappear
            if not self.wait_page_load():
                raise Exception("Timeout ao carregar página de consulta")

            # Fill search filters if provided
            if start_date:
                try:
                    self.logger.info(f"Preenchendo data inicial: {start_date}")
                    start_date_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "Filters_DataCadastroIni"))
                    )
                    start_date_input.clear()
                    start_date_input.send_keys(start_date)
                except Exception as e:
                    self.logger.error(f"Erro ao preencher data inicial: {str(e)}")
                    if self.enable_screenshots:
                        self.take_screenshot("erro_data_inicial")
                    raise
            
            if end_date:
                try:
                    self.logger.info(f"Preenchendo data final: {end_date}")
                    end_date_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "Filters_DataCadastroFim"))
                    )
                    end_date_input.clear()
                    end_date_input.send_keys(end_date)
                except Exception as e:
                    self.logger.error(f"Erro ao preencher data final: {str(e)}")
                    if self.enable_screenshots:
                        self.take_screenshot("erro_data_final")
                    raise
            
            if status:
                try:
                    self.logger.info(f"Selecionando status: {status}")
                    status_select = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "Filters_StatusId"))
                    )
                    
                    # Map status text to value
                    status_map = {
                        "Encerrado": "0",
                        "Ativo": "1",
                        "Suspenso": "2"
                    }
                    
                    if status not in status_map:
                        self.logger.error(f"Status inválido: {status}. Valores permitidos: {list(status_map.keys())}")
                        raise ValueError(f"Status inválido: {status}")
                    
                    status_value = status_map[status]
                    
                    # Tenta diferentes abordagens para selecionar o valor
                    try:
                        Select(status_select).select_by_value(status_value)
                    except:
                        try:
                            self.driver.execute_script(
                                f"arguments[0].value = '{status_value}';", 
                                status_select
                            )
                        except:
                            option = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, f"#Filters_StatusId option[value='{status_value}']"))
                            )
                            option.click()
                    
                except Exception as e:
                    self.logger.error(f"Erro ao selecionar status: {str(e)}")
                    if self.enable_screenshots:
                        self.take_screenshot("erro_status")
                    raise
            
            if process_number:
                try:
                    self.logger.info(f"Preenchendo número do processo: {process_number}")
                    process_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "Filters_Protocolo"))
                    )
                    process_input.clear()
                    process_input.send_keys(process_number)
                except Exception as e:
                    self.logger.error(f"Erro ao preencher número do processo: {str(e)}")
                    if self.enable_screenshots:
                        self.take_screenshot("erro_processo")
                    raise
            
            # Click search button
            try:
                self.logger.info("Clicando no botão de pesquisa...")
                search_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "buttonSubmit"))
                )
                search_button.click()
                
                # Wait for results and blockUI to disappear
                time.sleep(3)
                try:
                    WebDriverWait(self.driver, 10).until_not(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.blockUI"))
                    )
                except TimeoutException:
                    self.logger.warning("BlockUI não encontrado após pesquisa")
                
            except Exception as e:
                self.logger.error(f"Erro ao realizar pesquisa: {str(e)}")
                if self.enable_screenshots:
                    self.take_screenshot("erro_pesquisa")
                raise
                
        except Exception as e:
            self.logger.error(f"Erro ao aplicar filtros: {str(e)}")
            raise

    def close(self):
        """Fecha o driver do Chrome"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Chrome fechado com sucesso")
            except Exception as e:
                self.logger.error(f"Erro ao fechar o Chrome: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
            finally:
                self.driver = None

    def wait_page_load(self, timeout=10):
        """Aguarda o carregamento completo da página"""
        try:
            self.logger.info("Aguardando carregamento da página...")
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            self.logger.info("Página carregada")
            return True
        except TimeoutException:
            self.logger.error("Timeout aguardando carregamento da página")
            return False

    def safe_get_text(self, xpath):
        """Extrai texto de um elemento de forma segura"""
        try:
            element = self.driver.find_element(By.XPATH, xpath)
            return element.text.strip() if element else "N/A"
        except:
            return "N/A"

    def extract_process_list(self):
        """Extract the list of processes from the search results"""
        try:
            self.logger.info("Iniciando extração da lista de processos...")
            
            # Wait for any loading indicators to disappear
            try:
                WebDriverWait(self.driver, 10).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.blockUI"))
                )
                self.logger.info("Loading indicator desapareceu")
            except Exception as e:
                self.logger.warning(f"Não foi possível encontrar ou esperar loading indicator: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
            
            # Try multiple selectors with increased timeout
            table_selectors = [
                (By.ID, "processoList"),
                (By.XPATH, "/html/body/div[6]/div[2]/div/div[1]/div[3]/div[3]/div"),
                (By.CSS_SELECTOR, "div.grid-view-content"),
                (By.CSS_SELECTOR, "div.grid-view")
            ]

            process_table = None
            for selector in table_selectors:
                try:
                    self.logger.info(f"Tentando encontrar tabela com selector: {selector}")
                    # Increased wait time to 20 seconds
                    process_table = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located(selector)
                    )
                    if process_table:
                        self.logger.info(f"Tabela encontrada com selector: {selector}")
                        break
                except Exception as e:
                    self.logger.warning(f"Tabela não encontrada com selector {selector}: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
                    continue

            if not process_table:
                self.logger.error("Tabela de processos não encontrada após tentar todos os selectors")
                if self.enable_screenshots:
                    self.take_screenshot("tabela_nao_encontrada")
                return [['Número', 'Parte', 'Tipo', 'Valor', 'Status', 'Data Cadastro']]

            # Additional wait for table to be visible and have content
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.visibility_of(process_table)
                )
                self.logger.info("Tabela está visível")
                
                # Log table HTML for debugging
                table_html = process_table.get_attribute('outerHTML')
                self.logger.debug(f"HTML da tabela encontrada:\n{table_html[:500]}...")  # Logging first 500 chars
                
            except Exception as e:
                self.logger.warning(f"Erro ao verificar visibilidade da tabela: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
            
            # Take a screenshot after finding the table
            if self.enable_screenshots:
                self.take_screenshot("tabela_encontrada")

            # Wait a bit more for any dynamic content to load
            time.sleep(2)

            # Try to find rows using multiple selectors
            row_selectors = [
                ".//tr[contains(@class, 'gridrow') or contains(@class, 'gridrow_alternate')]",
                ".//tbody/tr[contains(@class, 'gridrow') or contains(@class, 'gridrow_alternate')]",
                ".//tr[@class='gridrow' or @class='gridrow_alternate']"
            ]

            rows = []
            for selector in row_selectors:
                try:
                    rows = process_table.find_elements(By.XPATH, selector)
                    if rows:
                        break
                except:
                    continue
            
            if not rows:
                self.logger.warning("Nenhuma linha encontrada na tabela")
                return [['Número', 'Parte', 'Tipo', 'Valor', 'Status', 'Data Cadastro']]

            self.logger.info(f"Número de linhas encontradas: {len(rows)}")

            # Define headers for the DataFrame
            headers = ['Número', 'Parte', 'Tipo', 'Valor', 'Status', 'Data Cadastro']
            processes = [headers]  # Start with headers as first row

            # Limit the number of rows based on max_rows parameter
            if self.max_rows is not None and self.max_rows > 0:
                self.logger.info(f"Limitando a {self.max_rows} linhas conforme configurado")
                rows = rows[:self.max_rows]

            for row_index, row in enumerate(rows):
                try:
                    # Log the current row being processed
                    self.logger.debug(f"Processando linha {row_index + 1}")
                    row_html = row.get_attribute('outerHTML')
                    self.logger.debug(f"HTML da linha {row_index + 1}:\n{row_html}")
                    
                    # Tenta diferentes estratégias para encontrar as células
                    cells = None
                    try:
                        # Primeira tentativa: find_elements direto com td
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if cells:
                            self.logger.debug(f"Células encontradas via find_elements na linha {row_index + 1}")
                    except Exception as e:
                        self.logger.debug(f"Falha ao encontrar células via find_elements na linha {row_index + 1}: {str(e)}")
                        try:
                            # Segunda tentativa: XPath específico
                            cells = row.find_elements(By.XPATH, ".//td[@width]")
                            if cells:
                                self.logger.debug(f"Células encontradas via XPath específico na linha {row_index + 1}")
                        except Exception as e:
                            self.logger.debug(f"Falha ao encontrar células via XPath específico na linha {row_index + 1}: {str(e)}")

                    if not cells:
                        self.logger.warning(f"Não foi possível encontrar células na linha {row_index + 1}")
                        continue

                    self.logger.debug(f"Número de células encontradas na linha {row_index + 1}: {len(cells)}")
                    
                    if len(cells) >= 12:  # Agora sabemos que tem 12 células
                        # Mapeamento das células baseado na estrutura real
                        process_data = [
                            cells[2].text.strip() or cells[2].find_element(By.TAG_NAME, "a").text.strip() or "N/A",  # Número do processo
                            cells[3].text.strip() or "N/A",  # Nome da parte
                            cells[11].text.strip() or "N/A",  # Tipo (CONSIGNADO - PF)
                            "N/A",  # Valor (não disponível no grid)
                            cells[8].text.strip() or "N/A",  # Status (Encerrado)
                            "N/A"  # Data Cadastro (não disponível no grid)
                        ]
                        
                        processes.append(process_data)
                        self.logger.debug(f"Processo extraído da linha {row_index + 1}: {process_data}")
                    else:
                        self.logger.warning(f"Linha {row_index + 1} com número insuficiente de células: {len(cells)}")
                except Exception as e:
                    self.logger.warning(f"Erro ao extrair dados da linha {row_index + 1}: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
                    continue

            self.logger.info(f"Total de processos extraídos: {len(processes) - 1}")  # -1 for headers
            return processes

        except Exception as e:
            self.logger.error(f"Erro ao extrair lista de processos: {str(e)}\nDetalhes: {type(e).__name__}, {str(e)}\nStack: {traceback.format_exc()}")
            if self.enable_screenshots:
                self.take_screenshot("erro_extracao_lista")
            return [['Número', 'Parte', 'Tipo', 'Valor', 'Status', 'Data Cadastro']]  # Return empty table with headers

    def get_acordo_details(self, url):
        """Extrai os detalhes do acordo da página de detalhes da obrigação"""
        try:
            self.logger.info(f"Acessando detalhes do acordo: {url}")
            self.driver.get(url)
            
            # Aguarda o carregamento da página
            if not self.wait_page_load():
                raise Exception("Timeout ao carregar página de detalhes do acordo")
            
            # Extrai os detalhes necessários
            detalhes_acordo = {}
            
            # Define os campos a serem extraídos com seus respectivos XPaths
            campos = {
                "nome_titular": {
                    "xpath": [
                        "//td[strong[contains(text(), 'Nome do Titular')]]/following-sibling::td[1]",
                        "//td[contains(text(), 'Nome do Titular')]/following-sibling::td[1]",
                        "//td[strong[contains(text(), 'Nome')]]/following-sibling::td[1]"
                    ],
                    "required": True
                },
                "cpf_titular": {
                    "xpath": [
                        "//td[strong[contains(text(), 'CPF do Titular')]]/following-sibling::td[1]",
                        "//td[contains(text(), 'CPF do Titular')]/following-sibling::td[1]",
                        "//td[strong[contains(text(), 'CPF')]]/following-sibling::td[1]"
                    ],
                    "required": True
                },
                "valor_acordo": {
                    "xpath": [
                        "//td[strong[contains(text(), 'Valor Acordo')]]/following-sibling::td[1]",
                        "//td[contains(text(), 'Valor Acordo')]/following-sibling::td[1]",
                        "//td[strong[contains(text(), 'Valor')]]/following-sibling::td[1]"
                    ],
                    "required": True
                },
                "forma_pagamento": {
                    "xpath": [
                        "//td[strong[contains(text(), 'Forma de Pagamento')]]/following-sibling::td[1]",
                        "//td[contains(text(), 'Forma de Pagamento')]/following-sibling::td[1]",
                        "//td[strong[contains(text(), 'Forma')]]/following-sibling::td[1]"
                    ],
                    "required": False
                }
            }
            
            # Extrai cada campo usando múltiplas tentativas
            for campo, config in campos.items():
                valor = None
                for xpath in config['xpath']:
                    try:
                        elemento = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        valor = elemento.text.strip()
                        if valor:
                            self.logger.info(f"Campo {campo} encontrado: {valor}")
                            break
                    except Exception as e:
                        self.logger.debug(f"Tentativa falhou para {campo} usando xpath {xpath}: {str(e)}")
                        continue
                
                if valor:
                    detalhes_acordo[campo] = valor
                else:
                    if config['required']:
                        self.logger.error(f"Campo obrigatório {campo} não encontrado")
                        return None
                    else:
                        self.logger.warning(f"Campo opcional {campo} não encontrado")
                        detalhes_acordo[campo] = "N/A"
            
            # Verifica se todos os campos obrigatórios foram preenchidos
            campos_obrigatorios = [campo for campo, config in campos.items() if config['required']]
            if all(campo in detalhes_acordo for campo in campos_obrigatorios):
                self.logger.info(f"Todos os campos obrigatórios encontrados: {detalhes_acordo}")
                return detalhes_acordo
            else:
                self.logger.error("Nem todos os campos obrigatórios foram encontrados")
                return None
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair detalhes do acordo: {str(e)}")
            return None

    def extract_process_details(self, process_id):
        """Extrai os detalhes de um processo específico"""
        try:
            # Navega para a página de detalhes do processo
            url = f"https://cetelem.djur.adv.br/processo/details/{process_id}"
            self.logger.info(f"Acessando detalhes do processo: {url}")
            self.driver.get(url)
            
            # Aguarda o carregamento da página
            if not self.wait_page_load():
                raise Exception("Timeout ao carregar página de detalhes do processo")
            
            # Aguarda a aba financeira carregar
            try:
                financial_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="#box-financeiro"]'))
                )
                financial_tab.click()
                self.logger.info("Aba financeira acessada")
                time.sleep(2)  # Aguarda um pouco para a tabela carregar
            except Exception as e:
                self.logger.error(f"Erro ao acessar aba financeira: {str(e)}")
                return None
            
            # Extrai informações do processo
            processo_info = {'detalhes_acordo': []}
            
            # Procura por lançamentos do tipo ACORDO na tabela
            try:
                # Aguarda a tabela financeira carregar
                table = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.paginate tbody"))
                )
                
                # Encontra todas as linhas
                rows = table.find_elements(By.TAG_NAME, "tr")
                self.logger.info(f"Encontradas {len(rows)} linhas na tabela financeira")
                
                for row in rows:
                    try:
                        # Verifica se é um lançamento do tipo ACORDO
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 8:  # Verifica se tem células suficientes
                            tipo_lancamento = cells[7].text.strip()  # Coluna do tipo de lançamento
                            
                            if "ACORDO" in tipo_lancamento.upper():
                                self.logger.info("Encontrado lançamento do tipo ACORDO")
                                
                                # Encontra o link para os detalhes da obrigação
                                try:
                                    link_element = row.find_element(By.XPATH, ".//td/a[contains(@href, '/obrigacaoprocesso/details/')]")
                                    acordo_url = link_element.get_attribute('href')
                                    self.logger.info(f"URL do acordo encontrada: {acordo_url}")
                                    
                                    # Extrai os detalhes do acordo
                                    acordo_details = self.get_acordo_details(acordo_url)
                                    if acordo_details:
                                        self.logger.info(f"Detalhes do acordo extraídos: {acordo_details}")
                                        processo_info['detalhes_acordo'].append(acordo_details)
                                    else:
                                        self.logger.warning("Não foi possível extrair detalhes do acordo")
                                        
                                except Exception as e:
                                    self.logger.error(f"Erro ao processar URL do acordo: {str(e)}")
                                    continue
                    except Exception as e:
                        self.logger.warning(f"Erro ao processar linha da tabela: {str(e)}")
                        continue
                
            except Exception as e:
                self.logger.error(f"Erro ao processar tabela financeira: {str(e)}")
                return None
            
            # Retorna apenas se encontrou algum acordo
            if processo_info['detalhes_acordo']:
                self.logger.info(f"Total de acordos encontrados: {len(processo_info['detalhes_acordo'])}")
                return processo_info
            else:
                self.logger.warning("Nenhum acordo encontrado")
                return None
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair detalhes do processo: {str(e)}")
            return None
