interface NovosTotais {
    kcal: number;
    prot: number;
    carb: number;
    gord: number;
}

interface NutroideResponse {
    status: string;
    refeicao_titulo: string;
    refeicao_kcal: number;
    novos_totais: NovosTotais;
}

const sendBtn = document.getElementById('send-btn') as HTMLButtonElement | null;
const input = document.getElementById('chat-input') as HTMLInputElement | null;
const statusMsg = document.getElementById('status-msg') as HTMLElement | null;
const mealList = document.getElementById('meal-list') as HTMLUListElement | null;

const registrarRefeicao = async (): Promise<void> => {
    if (!input || !statusMsg || !mealList) return;

    const texto = input.value.trim();
    if (!texto) return;

    statusMsg.innerText = "Nutroide analisando...";
    input.value = "";

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texto })
        });

        const result: NutroideResponse = await response.json();

        if (result.status === 'sucesso') {
            statusMsg.innerText = "Refeição registrada!";
            updateDashboard(result.novos_totais);
            addMealToList(result.refeicao_titulo, result.refeicao_kcal);
        } else {
            statusMsg.innerText = "Erro ao processar.";
        }
    } catch (error) {
        console.error("Erro:", error);
        statusMsg.innerText = "Erro de conexão.";
    }
};

function updateDashboard(totais: NovosTotais): void {
    const kcalEl = document.getElementById('total-kcal');
    const protEl = document.getElementById('total-prot');
    const carbEl = document.getElementById('total-carb');
    const gordEl = document.getElementById('total-gord');

    if (kcalEl) kcalEl.innerText = totais.kcal.toString();
    if (protEl) protEl.innerText = `${totais.prot}g`;
    if (carbEl) carbEl.innerText = `${totais.carb}g`;
    if (gordEl) gordEl.innerText = `${totais.gord}g`;
}

function addMealToList(titulo: string, kcal: number): void {
    if (!mealList) return;
    const novoItem = document.createElement('li');
    novoItem.className = "list-group-item bg-dark text-white border-secondary d-flex justify-content-between align-items-center";
    novoItem.innerHTML = `<span>${titulo}</span><span class="text-secondary">${kcal} kcal</span>`;
    mealList.prepend(novoItem);
}

sendBtn?.addEventListener('click', registrarRefeicao);

export {};