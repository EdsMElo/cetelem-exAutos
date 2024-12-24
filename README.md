# exAutos - Sistema de Extração de Dados Jurídicos

## Descrição
O exAutos é um sistema automatizado desenvolvido para extrair e processar dados jurídicos do sistema DJUR. Ele oferece uma interface web intuitiva para monitorar e gerenciar processos jurídicos, facilitando o acesso e análise de informações processuais.

## Objetivo
O principal objetivo do exAutos é automatizar a coleta de dados jurídicos, proporcionando uma maneira eficiente de acessar, monitorar e analisar informações de processos judiciais, reduzindo o tempo gasto em tarefas manuais e minimizando erros humanos.

## Tecnologias Utilizadas
- **Python**: Linguagem principal do projeto
- **Flask**: Framework web para a interface do usuário
- **Selenium (undetected-chromedriver)**: Para automação web e scraping
- **BeautifulSoup**: Para parsing de HTML
- **Docker**: Para containerização da aplicação
- **Chrome WebDriver**: Para automação do navegador

## Componentes Principais

### 1. Interface Web (app.py)
- Gerencia a interface do usuário
- Processa requisições HTTP
- Coordena a execução do scraping
- Exibe resultados e status da extração

### 2. Scraper Legal (legal_scraper.py)
- Realiza a automação do navegador
- Gerencia autenticação e navegação
- Extrai dados do sistema DJUR
- Processa e estrutura as informações coletadas

### 3. Configurações (config.py)
- Gerencia variáveis de ambiente
- Configura parâmetros do sistema
- Define constantes globais

## Funcionalidades Principais

### Métodos do LegalScraper

#### `__init__(headless=True, max_rows=None, enable_screenshots=False)`
- Inicializa o scraper com configurações personalizáveis
- Permite execução headless ou com interface visual
- Configura captura de screenshots e limites de extração

#### `initialize()`
- Inicia o navegador Chrome
- Configura opções do WebDriver
- Estabelece conexão com o sistema DJUR

#### `login()`
- Realiza autenticação no sistema
- Processa autenticação de dois fatores
- Gerencia sessão do usuário

#### `extract_data()`
- Navega pelo sistema DJUR
- Coleta dados dos processos
- Estrutura informações extraídas

### Recursos Funcionais

1. **Extração Automatizada**
   - Coleta automática de dados processuais
   - Captura de múltiplos processos simultaneamente
   - Estruturação dos dados em formato padronizado

2. **Monitoramento em Tempo Real**
   - Interface web para acompanhamento da extração
   - Visualização do progresso em tempo real
   - Alertas e notificações de status

3. **Gestão de Screenshots**
   - Captura automática de telas importantes
   - Armazenamento organizado de evidências
   - Rastreabilidade do processo de extração

4. **Logging e Depuração**
   - Registro detalhado de operações
   - Logs HTML para análise
   - Tratamento de erros e exceções

## Modos de Operação

### Modo HEADLESS
- Execução sem interface gráfica do navegador
- Ideal para ambientes de produção e servidores
- Menor consumo de recursos do sistema
- Execução mais rápida das operações
- Configurável através do parâmetro `headless=True` no inicializador

### Modo SCREENSHOT
- Captura automatizada de screenshots durante a execução
- Útil para:
  - Debugging e análise de problemas
  - Documentação do processo
  - Evidências de execução
  - Auditoria de operações
- Screenshots são salvos no diretório `screenshots/`
- Ativado através do parâmetro `enable_screenshots=True`
- Cada screenshot é nomeado com timestamp para fácil rastreamento

### Modo TESTER
- Modo especial para testes e desenvolvimento
- Gera dados simulados para teste do sistema
- Características:
  - Cria processos fictícios com dados realistas
  - Simula diferentes estados processuais
  - Gera variações de acordos e suspeitas de fraude
  - Permite testar todas as funcionalidades sem acessar o sistema real
- Útil para:
  - Desenvolvimento de novas features
  - Testes de integração
  - Validação de regras de negócio
  - Treinamento de usuários
- Ativado através da função `generate_test_data()`

## Interface do Usuário

### Grid de Processos
- Exibição tabular dos processos jurídicos
- Colunas personalizáveis com informações principais:
  - Número do processo
  - Status
  - Escritório responsável
  - Tipo de processo
  - Data de distribuição
  - Valor da causa
- Ordenação por qualquer coluna
- Paginação para melhor performance
- Atualização em tempo real dos dados

### Sistema de Filtros
- Filtros avançados para refinamento da busca:
  - Por status do processo
  - Por escritório
  - Por tipo de processo
  - Por data (período específico)
  - Por valor da causa
  - Por existência de acordo
  - Por suspeita de fraude
- Filtros combinados para buscas complexas
- Salvamento de filtros favoritos
- Reset rápido de todos os filtros
- Indicador visual de filtros ativos

### Aba de Dados Brutos
- Visualização detalhada de todas as informações extraídas
- Dados apresentados em formato JSON para análise técnica
- Funcionalidades disponíveis:
  - Exportação dos dados em diferentes formatos (JSON, CSV)
  - Cópia direta para clipboard
  - Busca textual dentro dos dados
  - Expansão/colapso de seções
- Informações incluídas:
  - Dados completos do processo
  - Histórico de movimentações
  - Documentos anexados
  - Partes envolvidas
  - Detalhes de acordos
  - Indicadores de fraude
  - Logs de extração
- Atualização em tempo real conforme novos dados são extraídos

## Regras de Negócio

### Regra do Acordo
- O sistema identifica automaticamente processos que possuem acordo firmado
- Critérios para identificação de acordo:
  - Presença de termos específicos como "ACORDO", "TRANSAÇÃO" ou "COMPOSIÇÃO" nos movimentos processuais
  - Análise do conteúdo das petições e decisões judiciais
  - Verificação de valores acordados e condições de pagamento
- O status do processo é atualizado para refletir a existência do acordo
- Informações relevantes do acordo são extraídas e armazenadas:
  - Data do acordo
  - Valor total
  - Número de parcelas
  - Datas de vencimento
  - Condições especiais

### Regra de Suspeita de Fraude
- O sistema monitora e identifica indicadores de possível fraude nos processos
- Critérios para identificação de suspeita de fraude:
  - Padrões suspeitos de comportamento processual
  - Inconsistências em documentos apresentados
  - Histórico de fraudes anteriores relacionadas às partes
  - Múltiplos processos com características similares
  - Advogados ou escritórios com histórico de fraudes
- Alertas são gerados automaticamente quando identificados indicadores de fraude
- O sistema categoriza o nível de risco da suspeita
- Informações relevantes são registradas para análise:
  - Tipo de suspeita
  - Evidências encontradas
  - Histórico relacionado
  - Recomendações de ação

## Como Executar

1. Clone o repositório
2. Configure o arquivo `.env` com suas credenciais
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute o script de setup apropriado:
   - Windows: `setup.bat`
   - Linux/Mac: `setup.sh`
5. Inicie a aplicação:
   ```bash
   python app.py
   ```

## Segurança
- Credenciais armazenadas em variáveis de ambiente
- Suporte a autenticação de dois fatores
- Proteção contra detecção de automação

## Monitoramento e Logs
- Logs detalhados de execução
- Capturas de tela para debugging
- Registro de eventos importantes

## Contribuição
Para contribuir com o projeto:
1. Faça um fork do repositório
2. Crie uma branch para sua feature
3. Faça commit das alterações
4. Push para a branch
5. Abra um Pull Request

## Licença
Este projeto é propriedade da Cetelem e seu uso é restrito aos termos estabelecidos pela empresa.
