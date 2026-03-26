document.getElementById('send-btn').addEventListener('click', async () => {
    const input = document.getElementById('chat-input');
    const status = document.getElementById('status-msg');
    const texto = input.value;

    if (!texto) return;

    status.innerText = "Nutroide analisando...";
    input.value = "";

    const response = await fetch('/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ texto: texto })
    });

    const result = await response.json();

    if (result.status === 'sucesso') {
    status.innerText = "Refeição registrada!";

    // atualiza os cards 
    document.getElementById('total-kcal').innerText = result.novos_totais.kcal;
    document.getElementById('total-prot').innerText = result.novos_totais.prot + "g";
    document.getElementById('total-carb').innerText = result.novos_totais.carb + "g";
    document.getElementById('total-gord').innerText = result.novos_totais.gord + "g";

    // adiciona a nova refeição na lista sem F5
    const lista = document.getElementById('meal-list');
    const novoItem = document.createElement('li');

    novoItem.className = "list-group-item bg-dark text-white border-secondary d-flex justify-content-between align-items-center";
    novoItem.innerHTML = `
        <span>${result.refeicao_titulo}</span>
        <span class="text-secondary">${result.refeicao_kcal} kcal</span>
    `;
    
    // adiciona no topo da lista
    lista.prepend(novoItem);
    } else {
        status.innerText = "Erro ao processar.";
    }
});