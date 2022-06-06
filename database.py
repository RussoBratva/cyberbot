import sqlite3

db = sqlite3.connect("main.db")

cur = db.cursor()

# Ativando modo WAL (Write-Ahead Logging) para melhorar o desempenho do SQLite.
cur.execute("PRAGMA journal_mode=WAL")


cur.executescript(
    """
-- Configurações gerais do bot --
CREATE TABLE IF NOT EXISTS bot_config(
    lara_name TEXT DEFAULT 'Nome da sua lara',                                  -- Nome da lara
    lara_key TEXT DEFAULT 'pix@example.com',                                    -- Chave pix da lara
    main_img TEXT DEFAULT 'https://telegra.ph/file/f0ac7b4baf2ed34c51747.png',  -- Link da imagem do /start
    support_user TEXT DEFAULT '@decoder_py',                                    -- Username de atendimento
    channel_user TEXT DEFAULT '@cyberspace_bots',                               -- Canal de notícias
    is_on INTEGER DEFAULT 1,                                                    -- Se o bot está on ou em manutenção
    gate_chk TEXT DEFAULT 'w4rlock',                                            -- Gate para chk
    gate_exchange TEXT DEFAULT 'w4rlock',                                       -- Gate para troca
    pay_auto TEXT DEFAULT 'mercado pago',                                       -- Seleção de pix auto
    random_pix TEXT,                                                            -- PIX pro AUTO PAY gerencia net
    random_pix_pb TEXT,                                                         -- Pix pro AUTO PAY PagBank
    time_exchange INTEGER DEFAULT 5,                                            -- Tempo de troca
    exchange_is INTEGER DEFAULT 1,                                              -- Ativa e desativa troca
    db_version INTEGER DEFAULT 9                                                -- Versão da database, veja abaixo
);

-- Inicializa a configuração com os valores padrão acima --
-- As configurações podem ser alteradas via painel posteriormente --
INSERT OR IGNORE INTO bot_config(ROWID) values(0);

CREATE TABLE IF NOT EXISTS prices(
    price_name TEXT,                           -- Nome do preço, ex.: Gold, 550209. Em caso de MIX é a quantidade
    price_type TEXT,                           -- Tipo do preço, ex.: UNIT, BIN, MIX, etc
    price NUMERIC                              -- Preço do item, ex.: 10
);

-- Db principal de cartões --
CREATE TABLE IF NOT EXISTS cards(
    number TEXT PRIMARY KEY NOT NULL,
    bin TEXT NOT NULL,                                                      -- bin do cartão
    month TEXT NOT NULL,                                                    -- Mês do vencimento
    year TEXT NOT NULL,                                                     -- Ano do vencimento
    cvv TEXT NOT NULL,                                                      -- Dígito verificador
    cpf TEXT,                                                               -- CPF do dono da cc
    name TEXT,                                                              -- Name do dono da cc
    added_date TEXT DEFAULT (datetime('now','localtime')),                  -- Data de adição na db
    vendor TEXT,                                                            -- Bandeira, ex.: Mastercard
    level TEXT,                                                             -- Nível, ex.: Gold
    card_type TEXT,                                                         -- Credito ou debito
    bank TEXT,                                                              -- Banco, ex.: Nubank
    country TEXT,                                                           -- País, ex.: BR
    pending INTEGER DEFAULT 0                                               -- Se a cc está pendente
);

-- Db de cartões vendidos --
CREATE TABLE IF NOT EXISTS cards_sold(
    number TEXT PRIMARY KEY NOT NULL,
    month TEXT NOT NULL,                                                  -- Mês do vencimento
    year TEXT NOT NULL,                                                   -- Ano do vencimento
    cvv TEXT NOT NULL,                                                    -- Dígito verificador
    cpf TEXT,                                                             -- CPF do dono da cc
    name TEXT,                                                            -- Name do dono da cc
    added_date TEXT NOT NULL,                                             -- Data de adição na db
    vendor TEXT,                                                          -- Bandeira, ex.: Mastercard
    level TEXT,                                                           -- Nível, ex.: Gold
    bank TEXT,                                                            -- Banco, ex.: Nubank
    country TEXT,                                                         -- País, ex.: BR
    owner INTEGER NOT NULL,                                               -- ID de quem comprou
    plan TEXT,                                                            -- Plano, ex.: UNIT, MIX, BIN, etc
    is_checked INTEGER NOT NULL DEFAULT 1,                                -- checada ou foi vendida sem checar
    bought_date TEXT DEFAULT (datetime('now','localtime'))                -- Data de compra
);

-- Db de cartões die e trocas --
CREATE TABLE IF NOT EXISTS cards_dies(
    number TEXT PRIMARY KEY NOT NULL,
    month TEXT NOT NULL,                                                 -- Mês do vencimento
    year TEXT NOT NULL,                                                  -- Ano do vencimento
    cvv TEXT NOT NULL,                                                   -- Dígito verificador
    cpf TEXT,                                                            -- CPF do dono da cc
    name TEXT,                                                           -- Name do dono da cc
    added_date TEXT NOT NULL,                                            -- Data de adição na db
    vendor TEXT,                                                         -- Bandeira, ex.: Mastercard
    level TEXT,                                                          -- Nível, ex.: Gold
    bank TEXT,                                                           -- Banco, ex.: Nubank
    country TEXT,                                                        -- País, ex.: BR
    owner INTEGER,                                                       -- ID de quem comprou
    plan TEXT,                                                           -- Plano, ex.: UNIT, MIX, BIN, etc
    bought_date TEXT,                                                    -- Data de compra
    die_date TEXT DEFAULT (datetime('now','localtime'))                  -- Data que ficou die
);

CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY NOT NULL,                                     -- ID do usuário
    username TEXT,                                                       -- Username do usuário
    name_user TEXT,                                                      -- frist name
    balance NUMERIC NOT NULL DEFAULT 0,                                  -- Saldo do usuário
    balance_diamonds NUMERIC NOT NULL DEFAULT 0,                         -- Saldo do usuário em diamantes
    agreed_tos INTEGER NOT NULL DEFAULT 0,                               -- Se o usuário aceitou os termos
    last_bought TEXT,                                                    -- Data da última compra
    is_action_pending INTEGER DEFAULT 0,                                 -- Se o usuário tem uma ação pendente
    is_blacklisted INTEGER NOT NULL DEFAULT 0,                           -- Se o usuário está bloqueado/banido
    refer INTEGER,                                                       -- de quem o usuário é refenciado
    cpf TEXT,                                                            -- cpf valido (para pix auto)
    name TEXT,                                                           -- name atrelado ao cpf (para pix auto)
    email TEXT                                                           -- email (para pix auto)
);

CREATE TABLE IF NOT EXISTS gifts(
    token TEXT PRIMARY KEY NOT NULL,                                    -- codigo do gift gerado pelo adm
    value INTEGER NOT NULL                                              -- valor do gift em saldo
);

CREATE TABLE IF NOT EXISTS tokens(
    type_token TEXT PRIMARY KEY NOT NULL,                              -- para especie de token (MercadoPago)
    client_id TEXT,                                                    -- id ou Client_id
    client_secret TEXT,                                                -- App_user ou Client_scret
    name_cert_pem TEXT,                                                -- Nome do arquivo .pem
    name_cert_key TEXT,                                                -- Nome do arquivo .key
    bearer_tk TEXT                                                     -- bearer token
);

-- Table para fazer o relatorio de vendas de entrada de saldo diario. --
CREATE TABLE IF NOT EXISTS sold_balance(
    type TEXT NOT NULL,                                               -- Tipo de transação: manual, auto ou cards (compra)
    value INTEGER NOT NULL,                                           -- Valor adicionado
    owner INTEGER NOT NULL,                                           -- ID de quem abasteceu
    quantity INTEGER NOT NULL DEFAULT 1,                              -- Quantidade de itens adicionados, por padrão 1
    add_balance_date TEXT DEFAULT (datetime('now','localtime'))       -- Data da compra. Por padrão o tempo atual, então não é necessário inserir
);

-- tabela para configurar bonus e preços e etc. --
CREATE TABLE IF NOT EXISTS values_config(
    transaction_type TEXT NOT NULL,                                   -- Tipo de transação (manual, auto, points, refer ou buy)
    min_value INTEGER NOT NULL,                                       -- Valor mínimo para esse tipo de transação
    bonus_value INTEGER NOT NULL                                      -- Valor do bônus em +valor ou valor%
);
"""
)


# Aqui o bot obtém a versão atual da database, e caso ela seja antiga,
# migra os dados dela automaticamente (Ex.: Quando uma coluna nova foi adicionada).
# A versão sempre deve ser aumentada no DEFAULT do bot_config caso uma mudança seja feita.
database_version = cur.execute("SELECT db_version FROM bot_config").fetchone()[0]


# Aqui ele compara a versão da database e executa as mudanças necessárias,
# ex.: Para adicionar uma nova coluna em uma table na db, use:
# ALTER TABLE cards ADD COLUMN something TEXT;

# Você deve criar um if para cada versão, em ordem crescente,
# assim eles executarão em ordem, atualizando a db para a última versão.
# O último if sempre deve ter um número menor que a versão atual,
# assim a versão da database não ficará mais alta que a versão atual.

if database_version == 0:
    cur.executescript(
        """
    ALTER TABLE bot_config ADD COLUMN gate_chk TEXT DEFAULT w4rlock;
    ALTER TABLE bot_config ADD COLUMN gate_exchange TEXT DEFAULT w4rlock;
        """
    )

    database_version += 1

if database_version == 1:
    cur.executescript(
        """
    ALTER TABLE bot_config ADD COLUMN time_exchange INTEGER DEFAULT 5;
        """
    )
    database_version += 1

if database_version == 2:
    cur.executescript(
        """
    ALTER TABLE bot_config ADD COLUMN exchange_is INTEGER DEFAULT 1;
        """
    )
    database_version += 1

if database_version == 3:
    cur.executescript(
        """
    ALTER TABLE users ADD COLUMN is_action_pending INTEGER DEFAULT 0;
        """
    )
    database_version += 1


if database_version == 4:
    cur.executescript(
        """
    ALTER TABLE bot_config ADD COLUMN pay_auto TEXT DEFAULT 'mercado pago';
    ALTER TABLE bot_config ADD COLUMN random_pix TEXT;
        """
    )
    database_version += 1

if database_version == 5:
    cur.executescript(
        """
    ALTER TABLE tokens ADD COLUMN name_cert_pem TEXT NOT NULL;
    ALTER TABLE tokens ADD COLUMN name_cert_key TEXT NOT NULL;
        """
    )
    database_version += 1

if database_version == 6:
    cur.executescript(
        """
    ALTER TABLE tokens ADD COLUMN bearer_tk TEXT DEFAULT 'None';
    ALTER TABLE bot_config ADD COLUMN random_pix_pb TEXT;
        """
    )
    database_version += 1

if database_version == 7:
    cur.executescript(
        """
    ALTER TABLE cards_sold ADD COLUMN cpf TEXT;
    ALTER TABLE cards_sold ADD COLUMN name TEXT;

    ALTER TABLE cards_dies ADD COLUMN cpf TEXT;
    ALTER TABLE cards_dies ADD COLUMN name TEXT;
        """
    )
    database_version += 1

if database_version == 8:
    cur.executescript(
        """
    ALTER TABLE sold_balance ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1
        """
    )
    database_version += 1


cur.execute("UPDATE bot_config SET db_version = ?", (database_version,))

cur.execute("UPDATE users SET is_action_pending = 0")

cur.execute("UPDATE cards SET pending = 0")

save = lambda: db.commit()
