CREATE TABLE humanos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    senha_hash TEXT NOT NULL,
    --considerar possiveis problemas com fuso horario 
    data_registro DATETIME DEFAULT CURRENT_TIMESTAMP 
);

CREATE TABLE biopedancia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    humano_id INTEGER,
    peso REAL,
    massa_magra REAL,
    percentual_gordura REAL,
    taxa_metabolica_basal REAL,
    data_registro DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (humano_id) REFERENCES humanos(id)
);

CREATE TABLE metas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    humano_id INTEGER,
    kcal_objetivo REAL,
    prot_objetivo REAL,
    carb_objetivo REAL,
    gord_objetivo REAL,
    agua_objetivo REAL, 
    FOREIGN KEY (humano_id) REFERENCES humanos(id)
);

CREATE TABLE refeicoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    humano_id INTEGER,
    titulo TEXT,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (humano_id) REFERENCES humanos(id)
);

CREATE TABLE itens_refeicao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    refeicao_id INTEGER,
    alimento TEXT, 
    quantidade TEXT, 
    calorias REAL,
    proteina REAL,
    carboidrato REAL,
    gordura REAL,
    FOREIGN KEY (refeicao_id) REFERENCES refeicoes(id) ON DELETE CASCADE
);

CREATE TABLE desafios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    descricao TEXT,
    data_inicio DATE,
    data_fim DATE,
    meta_kcal_diaria REAL
);

CREATE TABLE participacoes_desafio (
    humano_id INTEGER,
    desafio_id INTEGER,
    PRIMARY KEY (humano_id, desafio_id),
    FOREIGN KEY (humano_id) REFERENCES humanos(id),
    FOREIGN KEY (desafio_id) REFERENCES desafios(id)
);