// Configuração do menu de configurações
document.addEventListener("DOMContentLoaded", function () {
  const settingsIcon = document.getElementById("settingsIcon");
  const settingsMenu = document.getElementById("settingsMenu");

  settingsIcon.addEventListener("click", function (e) {
    e.stopPropagation();
    settingsMenu.classList.toggle("active");
  });

  // Fechar o menu ao clicar fora
  document.addEventListener("click", function (e) {
    if (!settingsMenu.contains(e.target) && e.target !== settingsIcon) {
      settingsMenu.classList.remove("active");
    }
  });

  // Prevenir que cliques dentro do menu o fechem
  settingsMenu.addEventListener("click", function (e) {
    e.stopPropagation();
  });

  // Adiciona a opção de debug no menu de configurações
  const debugOption = document.createElement("div");
  debugOption.className = "settings-item";
  debugOption.innerHTML = `
    <label class="switch">
      <input type="checkbox" id="debugToggle" checked>
      <span class="slider round"></span>
    </label>
    <span>Modo Debug</span>
  `;
  settingsMenu.appendChild(debugOption);

  // Gerencia o estado do debug
  const debugToggle = document.getElementById("debugToggle");
  
  // Função para log condicional baseado no estado do debug
  window.debugLog = function(message) {
    if (debugToggle.checked) {
      console.log(message);
    }
  };

  // Função para log de erro (sempre exibido)
  window.errorLog = function(message) {
    console.error(message);
  };

  debugToggle.addEventListener("change", async function() {
    try {
      const response = await fetch("/api/config/debug", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ enabled: this.checked }),
      });

      if (!response.ok) {
        throw new Error("Falha ao atualizar configuração de debug");
      }

      showToast(`Modo debug ${this.checked ? "ativado" : "desativado"}`, "success");
    } catch (error) {
      console.error("Erro ao atualizar configuração de debug:", error);
      showToast("Erro ao atualizar configuração de debug", "error");
      this.checked = !this.checked; // Reverte a mudança em caso de erro
    }
  });

  // Adiciona evento de clique ao botão de recertificação de fraude
  const recertifyFraudBtn = document.getElementById("recertifyFraudBtn");
  if (recertifyFraudBtn) {
    recertifyFraudBtn.addEventListener("click", function() {
      // Cria o modal de confirmação
      const modalHtml = `
        <div class="modal fade" id="recertifyModal" tabindex="-1" aria-labelledby="recertifyModalLabel" aria-hidden="true">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header bg-warning text-dark">
                <h5 class="modal-title" id="recertifyModalLabel">Confirmar Recertificação de Fraude</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
              </div>
              <div class="modal-body">
                <div class="alert alert-warning">
                  <i class="bi bi-exclamation-triangle-fill me-2"></i>
                  <strong>Atenção!</strong> Esta ação irá:
                </div>
                <ul class="list-group mb-3">
                  <li class="list-group-item">
                    <i class="bi bi-check-circle text-success me-2"></i>
                    Reavaliar <strong>todos os processos</strong> na base de dados
                  </li>
                  <li class="list-group-item">
                    <i class="bi bi-trash text-danger me-2"></i>
                    Remover registros de fraude que não atendem mais aos critérios
                  </li>
                  <li class="list-group-item">
                    <i class="bi bi-plus-circle text-primary me-2"></i>
                    Adicionar novos registros de fraude para processos que atendem aos critérios
                  </li>
                </ul>
                <p>Esta operação pode levar alguns minutos, dependendo do tamanho da base de dados.</p>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-warning" id="confirmRecertify">
                  <i class="bi bi-shield-check me-1"></i> Confirmar Recertificação
                </button>
              </div>
            </div>
          </div>
        </div>
      `;

      // Adiciona o modal ao DOM
      const modalContainer = document.createElement('div');
      modalContainer.innerHTML = modalHtml;
      document.body.appendChild(modalContainer);

      // Inicializa o modal do Bootstrap
      const recertifyModal = new bootstrap.Modal(document.getElementById('recertifyModal'));
      recertifyModal.show();

      // Adiciona evento ao botão de confirmação
      document.getElementById('confirmRecertify').addEventListener('click', async function() {
        try {
          // Fecha o modal
          recertifyModal.hide();
          
          // Mostra loading
          document.querySelector(".loading-overlay").style.display = "flex";
          document.querySelector(".stop-extraction").style.display = "none";
          
          // Faz a requisição para a API
          const response = await fetch("/fraudeCheck/api/recertify", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            }
          });

          if (!response.ok) {
            throw new Error("Falha ao recertificar fraudes");
          }

          const result = await response.json();
          
          // Esconde loading
          document.querySelector(".loading-overlay").style.display = "none";
          
          // Mostra resultado
          const resultHtml = `
            <div class="alert alert-success">
              <h5>Recertificação concluída com sucesso!</h5>
              <p>Total de processos analisados: <strong>${result.stats.total_processos}</strong></p>
              <p>Total de fraudes identificadas: <strong>${result.stats.total_fraudes}</strong></p>
              ${result.stats.erros > 0 ? `<p>Erros durante o processamento: <strong>${result.stats.erros}</strong></p>` : ''}
            </div>
          `;
          
          // Cria modal de resultado
          const resultModalHtml = `
            <div class="modal fade" id="resultModal" tabindex="-1" aria-labelledby="resultModalLabel" aria-hidden="true">
              <div class="modal-dialog">
                <div class="modal-content">
                  <div class="modal-header bg-success text-white">
                    <h5 class="modal-title" id="resultModalLabel">Resultado da Recertificação</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                  </div>
                  <div class="modal-body">
                    ${resultHtml}
                  </div>
                  <div class="modal-footer">
                    <button type="button" class="btn btn-primary" data-bs-dismiss="modal">Fechar</button>
                  </div>
                </div>
              </div>
            </div>
          `;
          
          // Adiciona o modal de resultado ao DOM
          const resultContainer = document.createElement('div');
          resultContainer.innerHTML = resultModalHtml;
          document.body.appendChild(resultContainer);
          
          // Mostra o modal de resultado
          const resultModal = new bootstrap.Modal(document.getElementById('resultModal'));
          resultModal.show();
          
          // Limpa os modais quando fechados
          document.getElementById('recertifyModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
          });
          
          document.getElementById('resultModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
          });
          
        } catch (error) {
          console.error("Erro ao recertificar fraudes:", error);
          document.querySelector(".loading-overlay").style.display = "none";
          
          // Usa a função de toast diretamente em vez de chamar showToast
          const toastContainer = document.querySelector(".toast-container");
          const toastId = "toast-" + Date.now();
          const toastHtml = `
            <div id="${toastId}" class="toast align-items-center border-0 bg-danger text-white" role="alert" aria-live="assertive" aria-atomic="true">
              <div class="d-flex">
                <div class="toast-body">
                  <i class="bi bi-exclamation-circle-fill me-2"></i>
                  Erro ao recertificar fraudes: ${error.message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
              </div>
            </div>
          `;
          
          toastContainer.insertAdjacentHTML("beforeend", toastHtml);
          const toastElement = document.getElementById(toastId);
          const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
          toast.show();
          
          // Remove o modal quando fechado
          document.getElementById('recertifyModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
          });
        }
      });
    });
  }
});

// Inicialização do sistema
document.addEventListener("DOMContentLoaded", async () => {
  const updateInitStep = (stepId, status) => {
    const step = document.querySelector(`#step-${stepId}`);
    if (!step) return;

    step.classList.remove("active", "completed", "error");
    const progress = step.querySelector(".progress");

    if (status === "active") {
      step.classList.add("active");
      progress.style.width = "50%";
    } else if (status === "completed") {
      step.classList.add("completed");
      progress.style.width = "100%";
    } else if (status === "error") {
      step.classList.add("error");
      progress.style.width = "100%";
    } else {
      progress.style.width = "0%";
    }
  };

  try {
    // Atualiza o status inicial
    updateInitStep("setup", "active");

    // Inicializa o scraper
    const response = await fetch("/api/initialize", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const result = await response.json();
    console.log("Resultado da inicialização:", result);

    if (response.ok && result.status === "success") {
      // Configurando Extrator
      updateInitStep("setup", "completed");
      
      // Realizando Login
      updateInitStep("login", "active");
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simula o tempo do login
      updateInitStep("login", "completed");
      
      // Sistema Pronto
      updateInitStep("ready", "active");
      await new Promise(resolve => setTimeout(resolve, 500));
      updateInitStep("ready", "completed");
      
      // Pequeno delay para mostrar a conclusão
      setTimeout(hideInitOverlay, 1000);
    } else {
      updateInitStep("setup", "error");
      throw new Error(result.message || "Falha na inicialização");
    }
  } catch (error) {
    console.error("Erro durante a inicialização:", error);
    updateInitStep("setup", "error");
    showToast(error.message || "Erro durante a inicialização", "error");
  }
});

// Função para esconder o overlay de inicialização
function hideInitOverlay() {
  document.querySelector(".init-overlay").style.display = "none";
}

// Variáveis globais
let columnFilters = {};
let lastData = null; // Armazena os últimos dados carregados
let currentSort = { column: null, direction: "asc" };
let isExtracting = false;

document.addEventListener("DOMContentLoaded", function () {
  // Configuração do Flatpickr nos botões de calendário
  const flatpickrConfig = {
    dateFormat: "d/m/Y",
    allowInput: true,
    locale: {
      firstDayOfWeek: 0,
      weekdays: {
        shorthand: ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"],
        longhand: [
          "Domingo",
          "Segunda",
          "Terça",
          "Quarta",
          "Quinta",
          "Sexta",
          "Sábado",
        ],
      },
      months: {
        shorthand: [
          "Jan",
          "Fev",
          "Mar",
          "Abr",
          "Mai",
          "Jun",
          "Jul",
          "Ago",
          "Set",
          "Out",
          "Nov",
          "Dez",
        ],
        longhand: [
          "Janeiro",
          "Fevereiro",
          "Março",
          "Abril",
          "Maio",
          "Junho",
          "Julho",
          "Agosto",
          "Setembro",
          "Outubro",
          "Novembro",
          "Dezembro",
        ],
      },
    },
  };

  // Inicializa o Flatpickr em cada input de data
  document.querySelectorAll("#start_date, #end_date").forEach((input) => {
    flatpickr(input, {
      ...flatpickrConfig,
      clickOpens: false, // Previne que o input abra o calendário ao ser clicado
    });
  });

  // Adiciona evento de click nos botões de calendário
  document.querySelectorAll(".calendar-btn").forEach((btn) => {
    const input = btn.parentElement.querySelector("input");
    btn.addEventListener("click", () => {
      if (input._flatpickr) {
        input._flatpickr.toggle(); // Alterna a visibilidade do calendário
      }
    });
  });

  // Permitir entrada manual de data
  document.querySelectorAll("#start_date, #end_date").forEach((input) => {
    input.addEventListener("input", function (e) {
      let value = e.target.value;
      value = value.replace(/[^\d/]/g, "");
      if (value.length === 2 || value.length === 5) {
        if (value[value.length - 1] !== "/") {
          value = value + "/";
        }
      }
      if (value.length > 10) {
        value = value.slice(0, 10);
      }
      e.target.value = value;
    });
  });

  // Mostrar/esconder botões de exportação baseado na aba ativa
  const exportButtons = document.querySelector(".export-buttons-container");
  document.querySelectorAll("#resultsTabs .nav-link").forEach((tab) => {
    tab.addEventListener("click", function () {
      exportButtons.style.display =
        this.id === "processes-tab" ? "block" : "none";
    });
  });

  // Botão Limpar
  document.getElementById("clear").addEventListener("click", () => {
    // Limpa a tabela de processos
    const tableBody = document.querySelector("#processTable tbody");
    if (tableBody) tableBody.innerHTML = "";

    // Limpa o accordion de dados brutos
    const rawDataAccordion = document.getElementById("rawDataAccordion");
    if (rawDataAccordion) rawDataAccordion.innerHTML = "";

    // Limpa o container de detalhes
    const detailsContainer = document.getElementById("details-container");
    if (detailsContainer) detailsContainer.innerHTML = "";

    // Reseta os campos de filtro
    document.getElementById("start_date").value = "";
    document.getElementById("end_date").value = "";
    document.getElementById("status_filter").value = "Todos";
    document.getElementById("process_number").value = "";
    document.getElementById("acordo").value = "Todos";

    // Reseta os checkboxes
    document.getElementById("headlessMode").checked = true;
    document.getElementById("screenshotMode").checked = false;
    document.getElementById("testerMode").checked = false;

    // Limpa a galeria de screenshots
    const screenshotsGallery = document.getElementById("screenshotsGallery");
    if (screenshotsGallery) {
      screenshotsGallery.innerHTML = "";
    }
  });

  // Função para obter os números dos processos do textarea
  const getProcessNumbers = () => {
    const processInput = document.getElementById("process_number");
    if (!processInput) return [];

    const value = processInput.value.trim();
    if (!value) return [];

    // Split por qualquer caractere não numérico e filtra valores vazios
    return value.split(/[^0-9.-]+/).filter((num) => num.trim());
  };

  // Função para extrair processos
  async function extractProcesses() {
    const startTime = performance.now();
    document.getElementById('searchTimer').style.display = 'none';

    if (isExtracting) {
      showToast("Uma extração já está em andamento", "warning");
      return;
    }

    try {
      isExtracting = true;
      document.querySelector(".loading-overlay").style.display = "flex";
      document.querySelector(".stop-extraction").style.display = "block";

      // Limpa a tabela e os detalhes antes de iniciar nova extração
      const tableBody = document.querySelector("#processTable tbody");
      if (tableBody) tableBody.innerHTML = "";
      const detailsContainer = document.getElementById("details-container");
      if (detailsContainer) detailsContainer.innerHTML = "";

      // Reseta os filtros e ordenação
      columnFilters = {};
      currentSort = { column: null, direction: "asc" };

      // Limpa as informações de filtro e ordenação
      const sortInfo = document.getElementById("sortInfo");
      if (sortInfo) sortInfo.textContent = "";
      const filterInfo = document.getElementById("filterInfo");
      if (filterInfo) filterInfo.textContent = "";

      const processNumbers = getProcessNumbers();
      const dataInicial = document.getElementById("start_date").value;
      const dataFinal = document.getElementById("end_date").value;
      const status = document.getElementById("status_filter").value;
      const acordo = document.getElementById("acordo").value;
      const suspeitaFraude = document.getElementById(
        "suspeita_fraude_filter"
      ).value;

      // Validação: se não houver número de processo, as datas são obrigatórias
      if (!processNumbers.length) {
        if (!dataInicial || !dataFinal) {
          showToast(
            "Quando não houver número de processo, é obrigatório informar data inicial e final",
            "warning"
          );
          return;
        }
      }

      // Monta o objeto de dados
      const data = {
        process_numbers: processNumbers,
        data_inicial: dataInicial,
        data_final: dataFinal,
        status: status,
        acordo: acordo,
        suspeita_fraude: suspeitaFraude,
      };
      debugLog("Dados da requisição:", data);

      // Mostra o loading
      document.querySelector(".loading-overlay").style.display = "flex";

      console.log("Fazendo requisição para /api/extract...");
      const response = await fetch("/api/extract", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      console.log("Status da resposta:", response.status);
      const result = await response.json();
      console.log("Resultado completo:", result);

      if (result.status === "success") {
        console.log("Dados recebidos com sucesso");
        console.log("Dados para atualizar tabela:", result.data);
        
        // Se não houver dados, mostra apenas a mensagem de "nenhum processo encontrado"
        if (!result.data || result.data.length === 0) {
          showToast("Nenhum processo encontrado", "warning");
        } else {
          // Passar o objeto result diretamente para updateProcessTable
          // A função updateProcessTable restaurada espera o objeto completo, não apenas tableData
          console.log("Passando dados completos para updateProcessTable:", result);
          updateProcessTable(result);
          showToast("Extração concluída com sucesso!", "success");
        }
        
        const endTime = performance.now();
        const timeTaken = Math.round(endTime - startTime);
        document.getElementById('searchTime').textContent = timeTaken;
        document.getElementById('searchTimer').style.display = 'block';
      } else {
        console.error("Erro na resposta:", result.message);
        showToast(result.message || "Erro ao extrair processos", "error");
      }
    } catch (error) {
      console.error("Erro durante extração:", error);
      showToast("Erro ao extrair processos: " + error.message, "error");
    } finally {
      document.querySelector(".loading-overlay").style.display = "none";
      document.querySelector(".stop-extraction").style.display = "none";
      isExtracting = false;
    }
  }

  // Event Listeners
  document
    .getElementById("extract")
    .addEventListener("click", extractProcesses);

  // Inicializa as variáveis de ordenação e filtro
  currentSort.column = null;
  currentSort.direction = "asc";
  columnFilters = {};

  const updateSortInfo = () => {
    const sortInfo = document.getElementById("sortInfo");
    if (!sortInfo) return; // Retorna se o elemento não existir

    if (currentSort.column) {
      const th = document.querySelector(
        `th[data-sort="${currentSort.column}"]`
      );
      if (!th) return; // Retorna se o elemento não existir
      const columnName = th.textContent.trim().split(" ")[0];
      sortInfo.textContent = `Ordenado por: ${columnName} (${
        currentSort.direction === "asc" ? "Crescente" : "Decrescente"
      })`;
    } else {
      sortInfo.textContent = "";
    }
  };

  const updateFilterInfo = () => {
    const filterInfo = document.getElementById("filterInfo");
    if (!filterInfo) return; // Retorna se o elemento não existir

    const activeFilterCount = Object.keys(columnFilters).length;

    if (activeFilterCount > 0) {
      const filterText = Object.entries(columnFilters)
        .map(([column, value]) => {
          const th = document.querySelector(`th[data-sort="${column}"]`);
          if (!th) return ""; // Retorna string vazia se o elemento não existir
          const columnName = th.textContent.trim().split(" ")[0];
          return `${columnName}: ${value.length} selecionado(s)`;
        })
        .filter((text) => text !== "") // Remove entradas vazias
        .join(", ");
      filterInfo.textContent = filterText ? ` | Filtros: ${filterText}` : "";
    } else {
      filterInfo.textContent = "";
    }
  };

  const sortTable = (column) => {
    if (currentSort.column === column) {
      currentSort.direction = currentSort.direction === "asc" ? "desc" : "asc";
    } else {
      currentSort.column = column;
      currentSort.direction = "asc";
    }

    // Update sort icons
    document.querySelectorAll(".sort-icon").forEach((icon) => {
      icon.classList.remove("active", "asc", "desc");
    });

    const icon = document.querySelector(`th[data-sort="${column}"] .sort-icon`);
    icon.classList.add("active", currentSort.direction);

    // Sort the data
    const tbody = document.querySelector("#processTable tbody");
    const rows = Array.from(tbody.querySelectorAll("tr"));

    rows.sort((a, b) => {
      const colIndex = getColumnIndex(column);
      if (colIndex === -1) return 0;

      const aCell = a.children[colIndex];
      const bCell = b.children[colIndex];

      if (!aCell || !bCell) return 0;

      const aValue = aCell.textContent.trim();
      const bValue = bCell.textContent.trim();

      if (column === "valor") {
        return compareValues(
          parseFloat(aValue.replace(/[^\d,-]/g, "").replace(",", ".")),
          parseFloat(bValue.replace(/[^\d,-]/g, "").replace(",", "."))
        );
      } else if (column === "data") {
        return compareValues(new Date(aValue), new Date(bValue));
      } else {
        return compareValues(aValue, bValue);
      }
    });

    if (currentSort.direction === "desc") {
      rows.reverse();
    }

    tbody.innerHTML = "";
    rows.forEach((row) => tbody.appendChild(row));

    updateSortInfo();
  };

  const compareValues = (a, b) => {
    if (a < b) return -1;
    if (a > b) return 1;
    return 0;
  };

  const getColumnIndex = (column) => {
    const headers = document.querySelectorAll("#processTable thead th");
    for (let i = 0; i < headers.length; i++) {
      if (headers[i].getAttribute("data-sort") === column) {
        return i;
      }
    }
    return -1;
  };

  // Add click event listeners for sorting
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const column = th.getAttribute("data-sort");
      sortTable(column);
    });
  });

  // Filtering functionality
  const createFilterDropdown = (column) => {
    const dropdown = document.createElement("div");
    dropdown.className = "filter-dropdown";
    dropdown.innerHTML = `
            <input type="text" class="filter-search" placeholder="Buscar...">
            <div class="filter-options"></div>
            <div class="filter-actions">
                <button class="filter-clear">Limpar</button>
                <button class="filter-apply">Aplicar</button>
            </div>
        `;

    // Event listeners for filter actions
    const searchInput = dropdown.querySelector(".filter-search");
    const clearButton = dropdown.querySelector(".filter-clear");
    const applyButton = dropdown.querySelector(".filter-apply");

    searchInput.addEventListener("input", (e) => {
      updateFilterOptions(dropdown, column, e.target.value);
    });

    clearButton.addEventListener("click", () => {
      columnFilters[column] = [];
      applyFilters();
      dropdown.remove();
    });

    applyButton.addEventListener("click", () => {
      const selectedValues = Array.from(
        dropdown.querySelectorAll('input[type="checkbox"]:checked')
      ).map((cb) => cb.value);

      console.log("Applying filter for column:", column);
      console.log("Selected values:", selectedValues);

      columnFilters[column] = selectedValues;
      applyFilters();
      dropdown.remove();
    });

    return dropdown;
  };

  const getUniqueColumnValues = (column) => {
    const values = new Set();
    const tbody = document.querySelector("#processTable tbody");
    const columnIndex = getColumnIndex(column);

    if (columnIndex === -1) return [];

    Array.from(tbody.querySelectorAll("tr")).forEach((row) => {
      let value;

      if (column === "acordo") {
        const processId = row.children[0]?.textContent?.trim();
        if (!processId) return;

        const processDetails = lastData?.raw_data?.[processId];
        let hasAcordo = false;

        if (processDetails?.detalhes_acordo?.length > 0) {
          hasAcordo = processDetails.detalhes_acordo[0]?.is_acordo === "Sim";
        }

        if (!hasAcordo && processDetails?.financeiro?.lancamentos?.length > 0) {
          hasAcordo = processDetails.financeiro.lancamentos.some(
            (reg) =>
              reg &&
              (reg.is_acordo === "Sim" ||
                (reg.tipo && reg.tipo.toUpperCase().includes("ACORDO")))
          );
        }

        value = hasAcordo ? "Sim" : "Não";
      } else {
        const cell = row.children[columnIndex];
        value = cell ? cell.textContent.trim() : "";
      }

      if (value) values.add(value);
    });

    const sortedValues = Array.from(values).sort();
    console.log("Unique values for column", column, ":", sortedValues);
    return sortedValues;
  };

  const updateFilterOptions = (dropdown, column, searchTerm = "") => {
    const optionsContainer = dropdown.querySelector(".filter-options");
    const values = getUniqueColumnValues(column);

    optionsContainer.innerHTML = values
      .filter((value) => value.toLowerCase().includes(searchTerm.toLowerCase()))
      .map(
        (value) => `
                <label class="filter-option">
                    <input type="checkbox" value="${value}" 
                        ${
                          !columnFilters[column] ||
                          columnFilters[column].includes(value)
                            ? "checked"
                            : ""
                        }>
                    ${value}
                </label>
            `
      )
      .join("");
  };

  const applyFilters = () => {
    const tbody = document.querySelector("#processTable tbody");
    const rows = Array.from(tbody.querySelectorAll("tr"));

    console.log("Current filters:", columnFilters);

    rows.forEach((row) => {
      let showRow = true;

      // Aplicar filtro de Suspeita de Fraude
      const suspeitaFraudeFilter = document.getElementById(
        "suspeita_fraude_filter"
      ).value;
      if (suspeitaFraudeFilter !== "Todos") {
        const cellValue =
          row.children[getColumnIndex("suspeita_fraude")].textContent.trim();
        if (cellValue !== suspeitaFraudeFilter) {
          showRow = false;
        }
      }

      Object.entries(columnFilters).forEach(([column, allowedValues]) => {
        if (!allowedValues || allowedValues.length === 0) return;

        if (column === "acordo") {
          const processId = row.children[0]?.textContent?.trim();
          if (!processId) return;

          const processDetails = lastData?.raw_data?.[processId];
          let hasAcordo = false;

          if (processDetails?.detalhes_acordo?.length > 0) {
            hasAcordo = processDetails.detalhes_acordo[0]?.is_acordo === "Sim";
          }

          if (
            !hasAcordo &&
            processDetails?.financeiro?.lancamentos?.length > 0
          ) {
            hasAcordo = processDetails.financeiro.lancamentos.some(
              (reg) =>
                reg &&
                (reg.is_acordo === "Sim" ||
                  (reg.tipo && reg.tipo.toUpperCase().includes("ACORDO")))
            );
          }

          const acordoValue = hasAcordo ? "Sim" : "Não";
          console.log(
            "Checking acordo for process:",
            processId,
            "Value:",
            acordoValue,
            "Allowed:",
            allowedValues
          );
          if (!allowedValues.includes(acordoValue)) {
            showRow = false;
          }
        } else {
          const cellValue =
            row.children[getColumnIndex(column)].textContent.trim();
          if (!allowedValues.includes(cellValue)) {
            showRow = false;
          }
        }
      });

      row.style.display = showRow ? "" : "none";
    });

    updateFilterInfo();

    // Update filter icons
    document.querySelectorAll(".filter-icon").forEach((icon) => {
      const column = icon.closest("th").getAttribute("data-sort");
      icon.classList.toggle("active", columnFilters[column]?.length > 0);
    });
  };

  // Adiciona evento de click nos botões de filtro
  document.querySelectorAll(".filter-icon").forEach((icon) => {
    const th = icon.closest("th");
    const column = th.getAttribute("data-sort");
    const dropdown = createFilterDropdown(column);
    document.body.appendChild(dropdown);

    // Toggle dropdown
    icon.addEventListener("click", (e) => {
      e.stopPropagation();
      const isVisible = dropdown.classList.contains("show");

      // Hide all other dropdowns
      document.querySelectorAll(".filter-dropdown.show").forEach((d) => {
        if (d !== dropdown) d.classList.remove("show");
      });

      if (!isVisible) {
        // Position dropdown at mouse click
        const rect = icon.getBoundingClientRect();
        dropdown.style.top = `${e.clientY}px`;
        dropdown.style.left = `${e.clientX}px`;

        updateFilterOptions(dropdown, column);
      }

      dropdown.classList.toggle("show");
    });
  });

  // Close dropdowns when clicking outside
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".filter-dropdown")) {
      document.querySelectorAll(".filter-dropdown").forEach((dropdown) => {
        dropdown.classList.remove("show");
      });
    }
  });

  // Função para atualizar tabela de processos
  function updateProcessTable(data) {
    console.log("Atualizando tabela com dados:", data);
    lastData = data;

    const tbody = document.querySelector("#processTable tbody");
    if (!tbody) {
      console.error("Elemento tbody não encontrado!");
      return;
    }
    tbody.innerHTML = "";

    if (!data?.data?.length) {
      console.log("Nenhum dado para exibir na tabela. Data:", data);
      console.log("Data?.data:", data?.data);
      showToast("Nenhum processo encontrado", "warning");
      return;
    }

    console.log("Processando", data.data.length, "registros");
    console.log("Grid data disponível:", data.grid_data);

    data.data.forEach((processDetails, index) => {
      const processId = processDetails.processo.id;

      // Verifica se tem acordo e se é fraude
      let suspeitaFraude = "Não";
      let hasAcordo = false;

      // Verifica acordos
      if (processDetails.acordo?.length > 0) {
        hasAcordo = true;
        if (
          processDetails.acordo.some(
            (acordo) => acordo.suspeita_fraude === true || acordo.suspeita_fraude === "Sim"
          )
        ) {
          suspeitaFraude = "Sim";
        }
      }

      // Verifica lançamentos financeiros
      if (!hasAcordo && processDetails.financeiro?.lancamentos?.length > 0) {
        hasAcordo = processDetails.financeiro.lancamentos.some(
          (reg) =>
            reg &&
            (reg.is_acordo === "Sim" ||
              (reg.tipo && reg.tipo.toUpperCase().includes("ACORDO")))
        );
      }

      // Busca dados do grid_data se disponível
      const gridData = data.grid_data?.[index];
      console.log("Grid Data para processo:", processId, gridData);

      console.log("Criando linha da tabela com dados:", {
        id: processId,
        numero: processDetails.processo.numero,
        parteAdversa: processDetails.partes?.parte_adversa,
        cpf: processDetails.partes?.cpf_cnpj_parte_adverso,
        comarca: processDetails.processo.comarca,
        estado: processDetails.processo.estado,
        escritorio: processDetails.processo.escritorio,
        status: processDetails.processo.status,
        fase: processDetails.processo.fase,
        hasAcordo,
        suspeitaFraude,
      });

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${processId}</td>
        <td>${processDetails.processo.numero || "N/A"}</td>
        <td>${processDetails.partes?.parte_adversa || "N/A"}</td>
        <td>${processDetails.partes?.cpf_cnpj_parte_adverso || "N/A"}</td>
        <td>${processDetails.processo.comarca || "N/A"}</td>
        <td>${processDetails.processo.estado || "N/A"}</td>
        <td>${processDetails.processo.escritorio || "N/A"}</td>
        <td>${processDetails.processo.status || "N/A"}</td>
        <td>${processDetails.processo.fase || "N/A"}</td>
        <td>${hasAcordo ? "Sim" : "Não"}</td>
        <td>${suspeitaFraude}</td>
        <td>
          <button class="btn btn-details" data-process-id="${processId}">
            Detalhes
          </button>
        </td>
      `;

      tbody.appendChild(tr);

      // Cria a linha para os detalhes (inicialmente oculta)
      const detailsRow = document.createElement("tr");
      detailsRow.className = "details-row d-none";
      detailsRow.innerHTML = `
        <td colspan="12">
          <div class="accordion" id="accordion-${processId}">
            <div class="accordion-item">
              <div class="accordion-header">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-${processId}">
                  Detalhes do Processo
                </button>
              </div>
              <div id="collapse-${processId}" class="accordion-collapse collapse" data-bs-parent="#accordion-${processId}">
                <div class="accordion-body">
                  <div id="details-content-${processId}">Carregando...</div>
                </div>
              </div>
            </div>
          </div>
        </td>
      `;
      tbody.appendChild(detailsRow);

      // Adiciona o evento de click no botão de detalhes
      const detailsBtn = tr.querySelector(".btn-details");
      detailsBtn.addEventListener("click", function () {
        const currentDetailsRow = this.closest("tr").nextElementSibling;
        const accordionButton = currentDetailsRow.querySelector(".accordion-button");
        const accordionCollapse = currentDetailsRow.querySelector(".accordion-collapse");

        // Fecha todos os outros detalhes abertos e reseta os botões
        document.querySelectorAll(".details-row").forEach((row) => {
          if (row !== currentDetailsRow) {
            row.classList.add("d-none");
            const accordion = row.querySelector(".accordion-collapse");
            if (accordion) {
              accordion.classList.remove("show");
            }
            const button = row.querySelector(".accordion-button");
            if (button) {
              button.classList.add("collapsed");
            }
            // Remove a classe active do botão
            const prevBtn = row.previousElementSibling.querySelector(".btn-details");
            if (prevBtn) {
              prevBtn.classList.remove("active");
            }
          }
        });

        // Alterna a visibilidade da linha de detalhes atual
        const isHidden = currentDetailsRow.classList.contains("d-none");
        currentDetailsRow.classList.toggle("d-none");

        // Alterna a classe active do botão
        this.classList.toggle("active");

        // Se estiver mostrando os detalhes
        if (isHidden) {
          // Remove a classe collapsed do botão e adiciona show ao collapse
          accordionButton.classList.remove("collapsed");
          accordionCollapse.classList.add("show");
          renderFormattedDetails(
            processId,
            document.getElementById(`details-content-${processId}`),
            gridData
          );
        } else {
          // Adiciona a classe collapsed ao botão e remove show do collapse
          accordionButton.classList.add("collapsed");
          accordionCollapse.classList.remove("show");
        }
      });
    });

    console.log("Tabela atualizada com sucesso");
  }

  // Função para renderizar detalhes formatados
  function renderFormattedDetails(processId, container, gridData) {
    console.log("Renderizando detalhes formatados para processo:", processId);

    if (!container) {
      console.error("Container não fornecido");
      return;
    }

    if (!lastData) {
      console.error("Nenhum dado disponível em lastData");
      return;
    }

    const process = lastData.data.find((p) => p.processo?.id === processId);
    if (!process) {
      console.error("Processo não encontrado:", processId);
      return;
    }

    let html = "";

    // Informações das Partes
    if (process.partes) {
      html += `
        <div class="detail-section">
          <h6>Partes do Processo</h6>
          <div class="detail-grid">
            <div class="detail-item">
              <div class="detail-label">Parte Adversa</div>
              <div class="detail-value">${process.partes.parte_adversa || "N/A"}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">CPF/CNPJ Parte Adversa</div>
              <div class="detail-value">${process.partes.cpf_cnpj_parte_adverso || "N/A"}</div>
            </div>
            ${
              process.partes.advogados_adversos?.length > 0
                ? `
              <div class="detail-item">
                <div class="detail-label">Advogados Adversos</div>
                <div class="detail-value">
                  ${process.partes.advogados_adversos
                    .map((adv) => adv.nome || "N/A")
                    .join(", ")}
                </div>
              </div>
            `
                : ""
            }
          </div>
        </div>
      `;
    }

    // Detalhes do Acordo
    if (process.acordo?.length > 0) {
      const acordo = process.acordo[0];
      html += `
        <div class="detail-section">
          <h6>Detalhes do Pagamento do Acordo</h6>
          <div class="detail-grid">
            <div class="detail-item">
              <div class="detail-label">Nome do Titular</div>
              <div class="detail-value">${acordo.nome_titular || "N/A"}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">CPF/CNPJ Titular</div>
              <div class="detail-value">${acordo.cpf_titular || acordo.cpf_cnpj_titular || "N/A"}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Valor do Acordo</div>
              <div class="detail-value">${acordo.valor || "N/A"}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Data de Pagamento</div>
              <div class="detail-value">${acordo.data_pagamento || "N/A"}</div>
            </div>
          </div>
        </div>
      `;
    }

    container.innerHTML = html;
    console.log("Detalhes renderizados com sucesso");
  }

  // Função para mostrar dados brutos
  window.showRawData = function (processId) {
    console.log("Mostrando dados brutos para processo:", processId);

    if (!lastData) {
      console.error("Nenhum dado disponível em lastData");
      return;
    }

    const details = lastData.raw_data[processId];
    if (!details) {
      console.error("Nenhum detalhe encontrado para o processo:", processId);
      return;
    }

    // Encontra o número do processo correto
    const processNumber =
      lastData.data.find((p) => p.processo.id === processId)?.processo.numero ||
      "N/A";
    console.log("Número do processo:", processNumber);

    // Cria o elemento de accordion se não existir
    let accordion = document.getElementById("rawDataAccordion");
    if (!accordion) {
      console.error("Accordion não encontrado!");
      return;
    }

    // Cria o item do accordion
    const accordionItem = document.createElement("div");
    accordionItem.className = "accordion-item";
    accordionItem.id = `accordion-${processId}`;

    const headerId = `heading-${processId}`;
    const collapseId = `collapse-${processId}`;

    accordionItem.innerHTML = `
      <h2 class="accordion-header" id="${headerId}">
        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}" aria-expanded="true" aria-controls="${collapseId}">
          Processo ${processNumber} (ID: ${processId})
        </button>
      </h2>
      <div id="${collapseId}" class="accordion-collapse collapse show" aria-labelledby="${headerId}">
        <div class="accordion-body">
          <div class="d-flex justify-content-between mb-2">
            <h5>Detalhes do Processo</h5>
            <button class="btn btn-sm btn-outline-primary copy-json" data-id="${processId}">
              <i class="bi bi-clipboard"></i> Copiar
            </button>
          </div>
          <pre><code>${JSON.stringify(details, null, 2)}</code></pre>
        </div>
      </div>
    `;

    // Adiciona evento de cópia
    const copyButton = accordionItem.querySelector(".copy-json");
    copyButton.addEventListener("click", () => {
      console.log("Copiando JSON para processo:", processId);
      const codeContent = accordionItem.querySelector("pre code").textContent;
      navigator.clipboard
        .writeText(codeContent)
        .then(() => {
          console.log("JSON copiado com sucesso");
          showToast("Conteúdo copiado com sucesso!");
        })
        .catch((error) => {
          console.error("Erro ao copiar:", error);
          showToast("Erro ao copiar conteúdo", "error");
        });
    });

    // Adiciona o novo item no início do accordion
    if (accordion.firstChild) {
      accordion.insertBefore(accordionItem, accordion.firstChild);
    } else {
      accordion.appendChild(accordionItem);
    }

    // Limita o número de itens no accordion para 5
    while (accordion.children.length > 5) {
      accordion.removeChild(accordion.lastChild);
    }

    // Muda para a aba de dados brutos
    const rawDataTab = document.querySelector("#raw-data-tab");
    if (!rawDataTab) {
      console.error("Aba de dados brutos não encontrada!");
      return;
    }

    console.log("Mudando para aba de dados brutos");
    const tab = new bootstrap.Tab(rawDataTab);
    tab.show();
  };

  // Função para mostrar/esconder o loading e o botão de parar
  function showLoading(show = true) {
    console.log("showLoading:", show);
    const overlay = document.querySelector(".loading-overlay");
    if (!overlay) {
      console.error("Elemento loading-overlay não encontrado!");
      return;
    }

    const stopButton = document.querySelector(".stop-extraction");
    if (!stopButton) {
      console.error("Botão stop-extraction não encontrado!");
      return;
    }

    if (show) {
      overlay.style.display = "flex";
      stopButton.style.display = "block";
    } else {
      overlay.style.display = "none";
      stopButton.style.display = "none";
    }
  }

  // Função para mostrar mensagens toast
  function showToast(message, type = "success") {
    console.log("showToast:", message, type);
    const toastContainer = document.querySelector(".toast-container");
    if (!toastContainer) {
      console.error("Container de toast não encontrado!");
      return;
    }

    // Ajusta o tipo para 'error' quando for 'danger'
    if (type === 'danger') type = 'error';

    const toast = document.createElement("div");
    toast.className = `toast align-items-center border-0`;
    toast.classList.add(`bg-${type}`);
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "assertive");
    toast.setAttribute("aria-atomic", "true");
    
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          <i class="bi ${type === "success" ? "bi-check-circle" : type === "warning" ? "bi-exclamation-triangle" : "bi-x-circle"} me-2"></i>
          ${message}
        </div>
        <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    `;

    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, {
      animation: true,
      autohide: true,
      delay: 5000
    });
    bsToast.show();

    // Remove o toast após ele ser escondido
    toast.addEventListener('hidden.bs.toast', () => {
      toastContainer.removeChild(toast);
    });
  }
});

// Funções de exportação
function exportToExcel() {
  if (!lastData?.data || lastData.data.length === 0) {
    showToast("Não há dados para exportar", "error");
    return;
  }

  // Criar uma tabela temporária para a exportação
  let table = document.createElement("table");

  // Adicionar cabeçalho
  let header = table.createTHead();
  let headerRow = header.insertRow();
  [
    "ID",
    "Processo",
    "Parte Adversa",
    "CPF/CNPJ",
    "Comarca",
    "Estado",
    "Escritório",
    "Status",
    "Fase",
    "Acordo",
    "Suspeita Fraude",
  ].forEach((text) => {
    let th = document.createElement("th");
    th.textContent = text;
    headerRow.appendChild(th);
  });

  // Adicionar dados
  let tbody = table.createTBody();
  lastData.data.forEach((processDetails) => {
    const hasAcordo =
      processDetails.acordo?.length > 0 ||
      processDetails.financeiro?.lancamentos?.some(
        (reg) =>
          reg &&
          (reg.is_acordo === "Sim" ||
            (reg.tipo && reg.tipo.toUpperCase().includes("ACORDO")))
      ) ||
      false;

    let suspeitaFraude = "Não";
    console.log("Acordos 1:", processDetails.acordo);
    if (processDetails.acordo?.length > 0) {
      console.log("Acordos:", processDetails.acordo);
      if (
        processDetails.acordo.some(
          (acordo) => acordo.suspeita_fraude === true || acordo.suspeita_fraude === "Sim"
        )
      ) {
        suspeitaFraude = "Sim";
      }
    }

    let row = tbody.insertRow();
    [
      processDetails.processo.id,
      processDetails.processo.numero,
      processDetails.partes?.parte_adversa || "N/A",
      processDetails.partes?.cpf_cnpj_parte_adverso || "N/A",
      processDetails.processo.comarca,
      processDetails.processo.estado,
      processDetails.processo.escritorio,
      processDetails.processo.status,
      processDetails.processo.fase,
      hasAcordo ? "Sim" : "Não",
      suspeitaFraude,
    ].forEach((text) => {
      let cell = row.insertCell();
      cell.textContent = text || "N/A";
    });
  });

  // Converter para o formato que pode ser aberto no Excel
  let html = table.outerHTML;
  let url = "data:application/vnd.ms-excel," + encodeURIComponent(html);

  // Criar link temporário e clicar nele
  let downloadLink = document.createElement("a");
  document.body.appendChild(downloadLink);
  downloadLink.href = url;
  downloadLink.download =
    "processos_" + new Date().toISOString().split("T")[0] + ".xls";
  downloadLink.click();
  document.body.removeChild(downloadLink);

  showToast("Arquivo Excel exportado com sucesso!");
}

function exportToCSV() {
  if (!lastData?.data || lastData.data.length === 0) {
    showToast("Não há dados para exportar", "error");
    return;
  }

  // Definir cabeçalhos
  const headers = [
    "ID",
    "Processo",
    "Parte Adversa",
    "CPF/CNPJ",
    "Comarca",
    "Estado",
    "Escritório",
    "Status",
    "Fase",
    "Acordo",
    "Suspeita Fraude",
  ];

  // Converter dados para formato CSV
  let csvContent = headers.join(",") + "\n";

  lastData.data.forEach((processDetails) => {
    const hasAcordo =
      processDetails.acordo?.length > 0 ||
      processDetails.financeiro?.lancamentos?.some(
        (reg) =>
          reg &&
          (reg.is_acordo === "Sim" ||
            (reg.tipo && reg.tipo.toUpperCase().includes("ACORDO")))
      ) ||
      false;

    let suspeitaFraude = "Não";
    console.log("Acordos 1:", processDetails.acordo);
    if (processDetails.acordo?.length > 0) {
      console.log("Acordos:", processDetails.acordo);
      if (
        processDetails.acordo.some(
          (acordo) => acordo.suspeita_fraude === true || acordo.suspeita_fraude === "Sim"
        )
      ) {
        suspeitaFraude = "Sim";
      }
    }

    let row = [
      processDetails.processo.id,
      `"${processDetails.processo.numero || ""}"`,
      `"${(processDetails.partes?.parte_adversa || "N/A").replace(
        /"/g,
        '""'
      )}"`,
      `"${(processDetails.partes?.cpf_cnpj_parte_adverso || "N/A").replace(
        /"/g,
        '""'
      )}"`,
      `"${(processDetails.processo.comarca || "N/A").replace(/"/g, '""')}"`,
      `"${(processDetails.processo.estado || "N/A").replace(/"/g, '""')}"`,
      `"${(processDetails.processo.escritorio || "N/A").replace(/"/g, '""')}"`,
      `"${(processDetails.processo.status || "N/A").replace(/"/g, '""')}"`,
      `"${(processDetails.processo.fase || "N/A").replace(/"/g, '""')}"`,
      `"${hasAcordo ? "Sim" : "Não"}"`,
      `"${suspeitaFraude}"`,
    ];
    csvContent += row.join(",") + "\n";
  });

  // Criar blob e link para download
  let blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  let link = document.createElement("a");
  let url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute(
    "download",
    "processos_" + new Date().toISOString().split("T")[0] + ".csv"
  );
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  showToast("Arquivo CSV exportado com sucesso!");
}

function exportToWord() {
  if (!lastData?.data || lastData.data.length === 0) {
    showToast("Não há dados para exportar", "error");
    return;
  }

  // Criar conteúdo HTML formatado para Word
  let content = `
        <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word'>
        <head>
            <meta charset="utf-8">
            <title>Relatório de Processos</title>
            <style>
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid black; padding: 8px; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h1>Relatório de Processos</h1>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Processo</th>
                    <th>Parte Adversa</th>
                    <th>CPF/CNPJ</th>
                    <th>Comarca</th>
                    <th>Estado</th>
                    <th>Escritório</th>
                    <th>Status</th>
                    <th>Fase</th>
                    <th>Acordo</th>
                    <th>Suspeita Fraude</th>
                </tr>`;

  lastData.data.forEach((processDetails) => {
    const hasAcordo =
      processDetails.acordo?.length > 0 ||
      processDetails.financeiro?.lancamentos?.some(
        (reg) =>
          reg &&
          (reg.is_acordo === "Sim" ||
            (reg.tipo && reg.tipo.toUpperCase().includes("ACORDO")))
      ) ||
      false;

    let suspeitaFraude = "Não";
    console.log("Acordos 1:", processDetails.acordo);
    if (processDetails.acordo?.length > 0) {
      console.log("Acordos:", processDetails.acordo);
      if (
        processDetails.acordo.some(
          (acordo) => acordo.suspeita_fraude === true || acordo.suspeita_fraude === "Sim"
        )
      ) {
        suspeitaFraude = "Sim";
      }
    }

    content += `
            <tr>
                <td>${processDetails.processo.id || "N/A"}</td>
                <td>${processDetails.processo.numero || "N/A"}</td>
                <td>${processDetails.partes?.parte_adversa || "N/A"}</td>
                <td>${
                  processDetails.partes?.cpf_cnpj_parte_adverso || "N/A"
                }</td>
                <td>${processDetails.processo.comarca || "N/A"}</td>
                <td>${processDetails.processo.estado || "N/A"}</td>
                <td>${processDetails.processo.escritorio || "N/A"}</td>
                <td>${processDetails.processo.status || "N/A"}</td>
                <td>${processDetails.processo.fase || "N/A"}</td>
                <td>${hasAcordo ? "Sim" : "Não"}</td>
                <td>${suspeitaFraude}</td>
            </tr>`;
  });

  content += `
            </table>
        </body>
        </html>`;

  // Criar blob e link para download
  let blob = new Blob([content], { type: "application/msword" });
  let link = document.createElement("a");
  let url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute(
    "download",
    "processos_" + new Date().toISOString().split("T")[0] + ".doc"
  );
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  showToast("Arquivo Word exportado com sucesso!");
}

// Função para verificar o status da sessão periodicamente
async function checkSession() {
  try {
    const response = await fetch('/api/healthcheck', {
      method: 'GET',
      credentials: 'include'
    });
    
    const data = await response.json();
    if (data.status === 'invalid') {
      console.log('Sessão inválida:', data.message);
      // Se a sessão estiver inválida, mostra o overlay e reinicializa
      document.getElementById('initOverlay').style.display = 'flex';
      initializeScraper();
    }
  } catch (error) {
    console.error('Erro ao verificar sessão:', error);
  }
}

// Função para inicializar o scraper
async function initializeScraper() {
  try {
    // Atualiza o status inicial
    updateInitStep("setup", "active");

    // Inicializa o scraper
    const response = await fetch("/api/initialize", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: 'include'
    });

    const result = await response.json();
    console.log("Resultado da inicialização:", result);

    if (response.ok && result.status === "success") {
      // Configurando Extrator
      updateInitStep("setup", "completed");
      
      // Realizando Login
      updateInitStep("login", "active");
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simula o tempo do login
      updateInitStep("login", "completed");
      
      // Sistema Pronto
      updateInitStep("ready", "active");
      await new Promise(resolve => setTimeout(resolve, 500));
      updateInitStep("ready", "completed");
      
      // Pequeno delay para mostrar a conclusão
      setTimeout(hideInitOverlay, 1000);
    } else {
      updateInitStep("setup", "error");
      throw new Error(result.message || "Falha na inicialização");
    }
  } catch (error) {
    console.error("Erro durante a inicialização:", error);
    updateInitStep("setup", "error");
    showToast(error.message || "Erro durante a inicialização", "error");
  }
}

// Inicia a verificação de sessão a cada 5 minutos e na carga inicial da página
document.addEventListener("DOMContentLoaded", async () => {
  // Verifica a sessão imediatamente ao carregar a página
  await checkSession();
  
  // Configura a verificação periódica
  setInterval(checkSession, 5 * 60 * 1000);
});

// Função para mostrar mensagens toast
function showToast(message, type = "success") {
  console.log("showToast:", message, type);
  const toastContainer = document.querySelector(".toast-container");
  if (!toastContainer) {
    console.error("Container de toast não encontrado!");
    return;
  }

  // Ajusta o tipo para 'error' quando for 'danger'
  if (type === 'danger') type = 'error';

  const toast = document.createElement("div");
  toast.className = `toast align-items-center border-0`;
  toast.classList.add(`bg-${type}`);
  toast.setAttribute("role", "alert");
  toast.setAttribute("aria-live", "assertive");
  toast.setAttribute("aria-atomic", "true");
  
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        <i class="bi ${type === "success" ? "bi-check-circle" : type === "warning" ? "bi-exclamation-triangle" : "bi-x-circle"} me-2"></i>
        ${message}
      </div>
      <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  toastContainer.appendChild(toast);
  const bsToast = new bootstrap.Toast(toast, {
    animation: true,
    autohide: true,
    delay: 5000
  });
  bsToast.show();

  // Remove o toast após ele ser escondido
  toast.addEventListener('hidden.bs.toast', () => {
    toastContainer.removeChild(toast);
  });
}