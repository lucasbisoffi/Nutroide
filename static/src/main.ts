interface NovosTotais {
    kcal: number;
    prot: number;
    carb: number;
    gord: number;
}

interface ItemRefeicao {
    alimento: string;
    quantidade: string;
    calorias: number;
    proteina: number;
    carboidrato: number;
    gordura: number;
}

interface NutroideResponse {
    status: string;
    refeicao_id: number;
    refeicao_titulo: string;
    refeicao_kcal: number;
    novos_totais: NovosTotais;
    itens: ItemRefeicao[];
}

const sendBtn = document.getElementById('send-btn') as HTMLButtonElement | null;
const input = document.getElementById('chat-input') as HTMLInputElement | null;
const statusMsg = document.getElementById('status-msg') as HTMLElement | null;
const mealList = document.getElementById('meal-list') as HTMLDivElement | null;

const registrarRefeicao = async (): Promise<void> => {
    if (!input || !statusMsg || !mealList) return;

    const texto = input.value.trim();
    if (!texto) return;

    statusMsg.innerText = "Nutroide processando...";
    input.value = "";

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texto })
        });

        const result: NutroideResponse = await response.json();

        if (result.status === 'sucesso') {
            statusMsg.innerText = "Refeição registrada com sucesso.";
            updateDashboard(result.novos_totais);
            addMealToList(result);
            setTimeout(() => { statusMsg.innerText = ""; }, 3000);
        } else {
            statusMsg.innerText = "Erro ao processar refeição.";
        }
    } catch (error) {
        console.error("Erro:", error);
        statusMsg.innerText = "Erro de conexão com o servidor.";
    }
};

function updateDashboard(totais: NovosTotais): void {
    const kcalEl = document.getElementById('total-kcal');
    const protEl = document.getElementById('total-prot');
    const carbEl = document.getElementById('total-carb');
    const gordEl = document.getElementById('total-gord');

    if (kcalEl) kcalEl.innerText = totais.kcal.toString();
    if (protEl) protEl.innerText = totais.prot.toString();
    if (carbEl) carbEl.innerText = totais.carb.toString();
    if (gordEl) gordEl.innerText = totais.gord.toString();
}

function addMealToList(result: NutroideResponse): void {
    if (!mealList) return;

    const emptyState = document.getElementById('empty-state');
    if (emptyState) emptyState.remove();

    const novoCard = document.createElement('div');
    novoCard.className = "meal-item bg-suisse-card border border-suisse-border rounded-lg p-4 shadow-sm transition-all";
    novoCard.setAttribute('data-id', result.refeicao_id.toString());

    let itensHtml = '';
    let totalProtRef = 0;
    let totalCarbRef = 0;
    let totalGordRef = 0;

    result.itens.forEach(item => {
        totalProtRef += Number(item.proteina) || 0;
        totalCarbRef += Number(item.carboidrato) || 0;
        totalGordRef += Number(item.gordura) || 0;

        itensHtml += `
            <div class="flex justify-between items-center bg-suisse-bg/60 p-2 rounded">
                <span class="font-medium text-suisse-text">${item.quantidade} de ${item.alimento}</span>
                <div class="flex items-center gap-3 text-[11px]">
                    <span>P: ${item.proteina}g | C: ${item.carboidrato}g | G: ${item.gordura}g</span>
                    <span class="font-semibold text-suisse-text">${item.calorias} kcal</span>
                </div>
            </div>
        `;
    });

    novoCard.innerHTML = `
        <div class="flex justify-between items-center cursor-pointer">
            <div>
                <span class="font-semibold text-sm block">${result.refeicao_titulo}</span>
                <span class="text-xs text-suisse-muted block mt-0.5">
                    P: <strong class="text-suisse-text font-medium">${Math.round(totalProtRef * 10) / 10}g</strong> &bull; 
                    C: <strong class="text-suisse-text font-medium">${Math.round(totalCarbRef * 10) / 10}g</strong> &bull; 
                    G: <strong class="text-suisse-text font-medium">${Math.round(totalGordRef * 10) / 10}g</strong>
                </span>
            </div>
            <div class="flex items-center gap-3">
                <span class="text-sm font-semibold">${result.refeicao_kcal} kcal</span>
                <button onclick="deletarRefeicao(event, ${result.refeicao_id})" class="text-suisse-muted hover:text-suisse-danger p-1 transition-colors" title="Excluir refeição">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2.2 2.2 0 0115.938 21H8.062a2.2 2.2 0 01-2.195-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                </button>
            </div>
        </div>
        <div class="meal-details mt-3 pt-3 border-t border-suisse-border text-xs space-y-2 text-suisse-muted">
            ${itensHtml}
        </div>
    `;

    mealList.prepend(novoCard);
}

// Função global para exclusão acessível pelo HTML inline
(window as any).deletarRefeicao = async (event: Event, id: number) => {
    event.stopPropagation();
    if (!confirm("Deseja realmente excluir esta refeição?")) return;

    try {
        const response = await fetch(`/refeicao/${id}/deletar`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.status === 'sucesso') {
            updateDashboard(result.novos_totais);
            const card = document.querySelector(`.meal-item[data-id="${id}"]`);
            if (card) card.remove();
        } else {
            alert("Erro ao excluir refeição.");
        }
    } catch (error) {
        console.error("Erro:", error);
        alert("Erro de conexão ao excluir.");
    }
};

sendBtn?.addEventListener('click', registrarRefeicao);
input?.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'Enter') registrarRefeicao();
});

export {};