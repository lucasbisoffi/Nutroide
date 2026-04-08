"use strict";
const sendBtn = document.getElementById('send-btn');
const input = document.getElementById('chat-input');
const statusMsg = document.getElementById('status-msg');
const mealList = document.getElementById('meal-list');
const registrarRefeicao = async () => {
    const texto = input.value.trim();
    if (!texto)
        return;
    statusMsg.innerText = "Nutroide analisando...";
    input.value = "";
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texto })
        });
        if (!response.ok)
            throw new Error("Erro na rede");
        const result = await response.json();
        if (result.status === 'sucesso') {
            statusMsg.innerText = "Refeição registrada!";
            updateDashboard(result.novos_totais);
            addMealToList(result.refeicao_titulo, result.refeicao_kcal);
        }
        else {
            statusMsg.innerText = "Erro ao processar.";
        }
    }
    catch (error) {
        console.error("Falha na requisição:", error);
        statusMsg.innerText = "Erro de conexão com o servidor.";
    }
};
// 4. Funções Auxiliares (Modularização)
function updateDashboard(totais) {
    const kcalEl = document.getElementById('total-kcal');
    const protEl = document.getElementById('total-prot');
    const carbEl = document.getElementById('total-carb');
    const gordEl = document.getElementById('total-gord');
    if (kcalEl)
        kcalEl.innerText = totais.kcal.toString();
    if (protEl)
        protEl.innerText = `${totais.prot}g`;
    if (carbEl)
        carbEl.innerText = `${totais.carb}g`;
    if (gordEl)
        gordEl.innerText = `${totais.gord}g`;
}
function addMealToList(titulo, kcal) {
    const novoItem = document.createElement('li');
    novoItem.className = "list-group-item bg-dark text-white border-secondary d-flex justify-content-between align-items-center";
    novoItem.innerHTML = `
        <span>${titulo}</span>
        <span class="text-secondary">${kcal} kcal</span>
    `;
    mealList.prepend(novoItem);
}
sendBtn?.addEventListener('click', registrarRefeicao);
