# Processo Jurídico - Extrator Autos

## Descrição
Este projeto é um sistema avançado de Recuperação Aumentada por Geração (RAG) especializado em processar e analisar documentos jurídicos. Ele utiliza técnicas de ponta em OCR (Reconhecimento Óptico de Caracteres) e processamento de linguagem natural, integrando Ollama para modelos de linguagem e ChromaDB para armazenamento eficiente de vetores, permitindo uma análise rápida e precisa de documentos legais.

## Finalidade
O objetivo principal deste sistema é revolucionar a forma como profissionais do direito interagem com documentos jurídicos. Ao combinar o poder do Ollama para geração de linguagem natural com a eficiência do ChromaDB para busca semântica, o sistema oferece:

- Extração rápida de informações chave de documentos PDF jurídicos.
- Respostas precisas e contextualizadas a consultas sobre o conteúdo dos documentos.
- Análise semântica avançada de textos jurídicos.

## Componentes Principais

### Ollama
Ollama é utilizado como o motor de modelo de linguagem do projeto, oferecendo:
- Geração de respostas naturais e contextualmente relevantes.
- Flexibilidade para usar diferentes modelos de linguagem.
- Processamento eficiente de consultas em linguagem natural.

### ChromaDB
ChromaDB serve como o banco de dados vetorial do sistema, proporcionando:
- Armazenamento eficiente de embeddings de documentos.
- Busca semântica rápida para recuperação de informações relevantes.
- Escalabilidade para lidar com grandes volumes de dados jurídicos.

## Estrutura do Projeto
O projeto é composto por vários módulos Python, cada um com uma função específica:

- `main.py`: Ponto de entrada da aplicação.
- `config.py`: Configurações globais do projeto.
- `document_processor.py`: Responsável pelo processamento de documentos PDF, incluindo OCR.
- `document_validator.py`: Valida se o documento processado é de natureza jurídica.
- `prompt_manager.py`: Gerencia a interação com o Ollama para gerar respostas.
- `llm_interface.py`: Interface para interação com o Ollama.
- `embedding_manager.py`: Gerencia a criação de embeddings para os documentos.
- `chroma_manager.py`: Gerencia as operações do ChromaDB.
- `rag_engine.py`: Implementa a lógica de Recuperação Aumentada por Geração, integrando Ollama e ChromaDB.
- `app.py`: Interface web usando Flask.

## Principais Bibliotecas Utilizadas

- `ollama`: Interface para modelos de linguagem, central para a geração de respostas.
- `chromadb`: Banco de dados vetorial para armazenamento e busca eficiente de embeddings.
- `flask`: Para criar a interface gráfica do usuário.
- `langchain`: Framework para desenvolvimento de aplicações com LLMs, facilitando a integração com Ollama.
- `spacy`: Para processamento de linguagem natural.
- `ocrmypdf`: Para realizar OCR em documentos PDF.
- `PyPDF2`: Para manipulação de arquivos PDF.
- `scikit-learn`: Para funcionalidades adicionais de aprendizado de máquina.

## Configuração do Ambiente

### Requisitos
- Python 3.12+
- Docker (opcional, para implantação em contêiner)
- Ollama instalado e configurado (para execução local)

### Instalação
1. Clone o repositório:
   ```
   git clone [URL_DO_REPOSITORIO]
   ```
2. Crie um ambiente virtual:
   ```
   python -m venv .venv
   source .venv/bin/activate  # No Windows use: .venv\Scripts\activate
   ```
3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
4. Configure o Ollama seguindo as instruções em [https://ollama.ai/](https://ollama.ai/)

### Uso com Docker
O projeto inclui um Dockerfile para fácil implantação, que configura automaticamente o ambiente com Ollama e ChromaDB. Para construir e executar o contêiner:

1. Construa a imagem Docker:
   ```
   docker build -t processo-juridico-extrator .
   ```
2. Execute o contêiner:
   ```
   docker run -p 7863:7863 processo-juridico-extrator
   ```

## Uso
1. Execute o script principal:
   ```
   python main.py
   ```
2. Acesse a interface web através do navegador no endereço indicado (geralmente `http://localhost:7863`).
3. Faça upload de um documento PDF jurídico.
4. O sistema processará o documento usando OCR, armazenará os embeddings no ChromaDB e estará pronto para responder perguntas.
5. Faça perguntas sobre o documento e receba respostas geradas pelo Ollama, contextualizadas com informações recuperadas do ChromaDB.

## Contribuição
Contribuições são bem-vindas! Estamos especialmente interessados em melhorias relacionadas à integração do Ollama e otimizações do ChromaDB. Por favor, leia o arquivo CONTRIBUTING.md (se disponível) para detalhes sobre nosso código de conduta e o processo para enviar pull requests.
