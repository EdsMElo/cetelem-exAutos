// Função para inicializar os componentes da página
document.addEventListener('DOMContentLoaded', function() {
    // Configurar Flatpickr para português
    flatpickr.localize(flatpickr.l10ns.pt);
    
    // Inicializar datepickers
    const datepickers = document.querySelectorAll('.datepicker');
    datepickers.forEach(dp => {
        flatpickr(dp, {
            dateFormat: "d/m/Y",
            locale: "pt"
        });
    });

    // Inicializar os eventos dos filtros
    initializeFilters();
    
    // Carregar dados iniciais
    searchData();
    
    // Event listeners para os botões de pesquisa e limpar
    // Botão Pesquisar
    document.getElementById('searchButton').addEventListener('click', searchData);
    
    // Botão Limpar
    document.getElementById('clearButton').addEventListener('click', clearFilters);
});

// Função para inicializar os filtros
function initializeFilters() {
    const searchButton = document.getElementById('searchButton');
    if (searchButton) {
        searchButton.addEventListener('click', searchData);
    }
    
    const clearButton = document.getElementById('clearButton');
    if (clearButton) {
        clearButton.addEventListener('click', clearFilters);
    }
}

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
document.querySelectorAll("#startDate, #endDate").forEach((input) => {
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

// Função para limpar os filtros
function clearFilters() {
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    const idFilter = document.getElementById('idFilter');
    const processoFilter = document.getElementById('processoFilter');
    const avaliacaoFilter = document.getElementById('avaliacaoFilter');
    const motivoFilter = document.getElementById('motivoFilter');
    
    if (startDate) startDate.value = '';
    if (endDate) endDate.value = '';
    if (idFilter) idFilter.value = '';
    if (processoFilter) processoFilter.value = '';
    if (avaliacaoFilter) avaliacaoFilter.value = 'Todos';
    if (motivoFilter) motivoFilter.value = 'Todos';
    
    // Realizar nova busca com filtros limpos
    searchData();
}

// Função para buscar dados
async function searchData() {
    const startTime = performance.now();
    document.getElementById('searchTimer').style.display = 'none';
    
    try {
        const startDate = document.getElementById('startDate')?.value;
        const endDate = document.getElementById('endDate')?.value;
        const idFilter = document.getElementById('idFilter')?.value;
        const processo = document.getElementById('processoFilter')?.value;
        const avaliacao = document.getElementById('avaliacaoFilter')?.value;
        const motivo = document.getElementById('motivoFilter')?.value;
        
        const filters = {
            start_date: startDate,
            end_date: endDate,
            external_id: idFilter,
            processo: processo,
            assessment_result: avaliacao === 'Todos' ? null : avaliacao,
            reason_conclusion: motivo === 'Todos' ? null : motivo
        };
        
        // Mostrar loading
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
        
        console.log('Enviando filtros:', filters);
        
        const response = await fetch('/fraudeCheck/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filters)
        });
        
        if (!response.ok) {
            throw new Error('HTTP error! status: ' + response.status);
        }
        
        const data = await response.json();
        updateTable(data);
        
        const endTime = performance.now();
        const timeTaken = Math.round(endTime - startTime);
        document.getElementById('searchTime').textContent = timeTaken;
        document.getElementById('searchTimer').style.display = 'block';
        
    } catch (error) {
        console.error('Erro ao buscar dados:', error);
        showError('Erro ao buscar dados: ' + error.message);
    } finally {
        // Esconder loading
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    }
}

// Função para atualizar a tabela com os dados
function updateTable(data) {
    const tbody = document.querySelector('#fraudeTable tbody');
    tbody.innerHTML = '';
    
    if (data.length === 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="6" class="text-center">Nenhum registro encontrado</td>';
        tbody.appendChild(tr);
        return;
    }
    
    data.forEach(item => {
        const tr = document.createElement('tr');
        
        tr.innerHTML = `
            <td>${item.external_id}</td>
            <td data-id="${item.external_id}">${item.processo}</td>
            <td>${item.assessment_date || ''}</td>
            <td>
                <select class="form-select assessment-select" data-id="${item.external_id}">
                    <option value="Pendente" ${item.assessment_result === 'Pendente' ? 'selected' : ''}>Pendente</option>
                    <option value="Positiva" ${item.assessment_result === 'Positiva' ? 'selected' : ''}>Positiva</option>
                    <option value="Negativa" ${item.assessment_result === 'Negativa' ? 'selected' : ''}>Negativa</option>
                    <option value="Falso Positivo" ${item.assessment_result === 'Falso Positivo' ? 'selected' : ''}>Falso Positivo</option>
                </select>
            </td>
            <td>
                <select class="form-select reason-select" data-id="${item.external_id}">
                    <option value="" disabled>Selecione...</option>
                    <option value="Individuo não Consta nos Autos" ${item.reason_conclusion === 'Individuo não Consta nos Autos' ? 'selected' : ''}>Individuo não Consta nos Autos</option>
                    <option value="Falha na Extração" ${item.reason_conclusion === 'Falha na Extração' ? 'selected' : ''}>Falha na Extração</option>
                    <option value="Dados Divergentes" ${item.reason_conclusion === 'Dados Divergentes' ? 'selected' : ''}>Dados Divergentes</option>
                    <option value="Individuo Consta nos Autos" ${item.reason_conclusion === 'Individuo Consta nos Autos' ? 'selected' : ''}>Individuo Consta nos Autos</option>
                </select>
            </td>
            <td>
                <button class="btn btn-primary btn-sm save-btn" data-id="${item.external_id}">
                    <i class="bi bi-check-lg"></i> Salvar
                </button>
            </td>
        `;

        // Adiciona os event listeners para os selects
        const assessmentSelect = tr.querySelector('.assessment-select');
        const reasonSelect = tr.querySelector('.reason-select');
        const saveButton = tr.querySelector('.save-btn');
        
        // Configura o estado inicial do combo de motivo
        updateReasonSelect(assessmentSelect, reasonSelect, item.assessment_date);
        
        // Adiciona o event listener para mudanças na avaliação
        assessmentSelect.addEventListener('change', () => {
            updateReasonSelect(assessmentSelect, reasonSelect);
        });

        // Adiciona o event listener para o botão salvar
        saveButton.addEventListener('click', () => {
            saveAssessment(item.external_id);
        });

        tbody.appendChild(tr);
    });
}

function updateReasonSelect(assessmentSelect, reasonSelect, assessmentDate) {
    const assessment = assessmentSelect.value;
    const options = reasonSelect.options;
    
    // Atualiza o estado do select de motivo
    if (assessment === 'Pendente') {
        reasonSelect.value = '';
        reasonSelect.disabled = true;
        options[0].disabled = false;
        for (let i = 1; i < options.length; i++) {
            options[i].disabled = true;
        }
    } else {
        reasonSelect.disabled = false;
        options[0].disabled = true;
        for (let i = 1; i < options.length; i++) {
            options[i].disabled = false;
        }
        if (reasonSelect.value === '') {
            reasonSelect.value = options[1].value;
        }
    }

    // Atualiza a data de avaliação na linha do grid
    if (assessmentDate) {
        const row = assessmentSelect.closest('tr');
        const dateCell = row.querySelector('td:nth-child(3)'); // Coluna da data
        if (dateCell) {
            dateCell.textContent = assessmentDate;
        }
    }
}

// Função para obter o usuário da estação de trabalho
async function getCurrentUser() {
    try {
        const response = await fetch('/fraudeCheck/api/current_user');
        const data = await response.json();
        return data.username;
    } catch (error) {
        console.error('Erro ao obter usuário:', error);
        return null;
    }
}

function saveAssessment(externalId) {
    const row = document.querySelector(`tr:has([data-id="${externalId}"])`);
    const process_number = row.querySelector(`td[data-id="${externalId}"]`).textContent;
    const assessmentSelect = row.querySelector('.assessment-select');
    const reasonSelect = row.querySelector('.reason-select');
    
    getCurrentUser().then(username => {
        const data = {
            process_number: process_number,
            assessment_result: assessmentSelect.value,
            reason_conclusion: assessmentSelect.value === 'Pendente' ? null : reasonSelect.value,
            username: username
        };

        fetch(`/fraudeCheck/api/assessment/${externalId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao salvar avaliação');
            }
            return response.json();
        })
        .then(data => {
            // Atualiza os valores nos selects com os dados retornados
            assessmentSelect.value = data.assessment_result;
            if (reasonSelect) {
                reasonSelect.value = data.reason_conclusion || '';
            }
            
            // Atualiza o estado do combo de motivo
            updateReasonSelect(assessmentSelect, reasonSelect, data.assessment_date);
            
            // Mostra mensagem de sucesso
            showToast('Avaliação salva com sucesso!', 'success');
        })
        .catch(error => {
            console.error('Erro:', error);
            showToast('Erro ao salvar avaliação', 'error');
        });
    });
}

// Função para mostrar erro
function showError(message) {
    // Implementar exibição de erro (pode ser um toast, alert, etc.)
    alert(message);
}

// Função para mostrar notificações toast
function showToast(message, type = 'success') {
    const toast = document.getElementById('notificationToast');
    const toastTitle = document.getElementById('toastTitle');
    const toastMessage = document.getElementById('toastMessage');
    const toastHeader = toast.querySelector('.toast-header');
    const icon = toast.querySelector('.bi');
    
    // Configura o tipo de toast
    toastHeader.className = 'toast-header';
    icon.className = 'bi me-2';
    
    if (type === 'success') {
        toastHeader.classList.add('bg-success', 'text-white');
        icon.classList.add('bi-check-circle');
        toastTitle.textContent = 'Sucesso';
    } else if (type === 'error') {
        toastHeader.classList.add('bg-danger', 'text-white');
        icon.classList.add('bi-x-circle');
        toastTitle.textContent = 'Erro';
    }
    
    // Define a mensagem
    toastMessage.textContent = message;
    
    // Cria uma nova instância do Toast do Bootstrap
    const bsToast = new bootstrap.Toast(toast, {
        animation: true,
        autohide: true,
        delay: 3000
    });
    
    // Mostra o toast
    bsToast.show();
}

// Funções de exportação
async function exportToExcel() {
    try {
        const response = await fetch('/fraudeCheck/api/export/excel');
        if (!response.ok) throw new Error('Erro ao exportar para Excel');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'fraudes.xlsx';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Erro na exportação:', error);
        showError('Erro ao exportar para Excel');
    }
}

async function exportToCSV() {
    try {
        const response = await fetch('/fraudeCheck/api/export/csv');
        if (!response.ok) throw new Error('Erro ao exportar para CSV');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'fraudes.csv';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Erro na exportação:', error);
        showError('Erro ao exportar para CSV');
    }
}

async function exportToWord() {
    try {
        const response = await fetch('/fraudeCheck/api/export/word');
        if (!response.ok) throw new Error('Erro ao exportar para Word');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'fraudes.docx';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Erro na exportação:', error);
        showError('Erro ao exportar para Word');
    }
}

// Função para visualizar detalhes
async function viewDetails(id) {
    try {
        const response = await fetch(`/fraudeCheck/api/details/${id}`);
        if (!response.ok) throw new Error('Erro ao carregar detalhes');
        
        const data = await response.json();
        showDetailsModal(data);
    } catch (error) {
        console.error('Erro ao carregar detalhes:', error);
        showError('Erro ao carregar detalhes do processo');
    }
}

// Função para mostrar modal de detalhes
function showDetailsModal(data) {
    // TODO: Implementar modal de detalhes
    console.log('Detalhes:', data);
}
