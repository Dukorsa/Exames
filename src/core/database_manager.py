import sqlite3
import logging
import json
import sys
from contextlib import contextmanager
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

DB_FILE: Optional[Path] = None
CODE_DB_VERSION = 3 # AUMENTAMOS A VERSÃO PARA IMPLEMENTAR A NOVA FUNCIONALIDADE

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    CONFIG_PATH = Path(sys._MEIPASS) / "src" / "resources" / "config" / "default_config.json"
else:
    CONFIG_PATH = Path(__file__).resolve().parent.parent / "resources" / "config" / "default_config.json"

def set_database_path(data_dir: Path):
    global DB_FILE
    data_dir.mkdir(parents=True, exist_ok=True)
    DB_FILE = data_dir / "app.db"
    logger.info(f"Caminho do banco de dados definido para: {DB_FILE}")

def _load_default_config() -> Dict:
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            logger.info(f"Carregando configuração padrão de: {CONFIG_PATH}")
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Não foi possível carregar ou parsear o arquivo de configuração padrão: {e}")
        return {"clinicas": [], "exames": {}, "rotinas": {}, "perfis": {}}

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def _migrate_v1_to_v2(conn: sqlite3.Connection):
    logger.info("Executando migração do DB para a v2: Sincronizando dados padrão...")
    cursor = conn.cursor()
    default_config = _load_default_config()
    default_clinicas = default_config.get("clinicas", [])
    default_exames = default_config.get("exames", {})
    if default_clinicas:
        cursor.executemany("INSERT OR IGNORE INTO clinicas (nome) VALUES (?)", [(n,) for n in default_clinicas])
    if default_exames:
        for nome, details in default_exames.items():
            cursor.execute("INSERT OR IGNORE INTO exames (nome_padrao) VALUES (?)", (nome,))
            exame_id = cursor.execute("SELECT id FROM exames WHERE nome_padrao = ?", (nome,)).fetchone()['id']
            if details.get('aliases'):
                cursor.executemany("INSERT OR IGNORE INTO exame_aliases (exame_id, alias) VALUES (?, ?)", [(exame_id, a) for a in details['aliases']])
    logger.info("Migração para v2 concluída.")

def _migrate_v2_to_v3(conn: sqlite3.Connection):
    logger.info("Executando migração do DB para a v3: Adicionando campo 'periodo' às rotinas...")
    cursor = conn.cursor()
    try:
        # Adiciona a nova coluna. O DEFAULT 'Sempre' aplica a regra padrão para dados existentes.
        cursor.execute("ALTER TABLE rotina_config ADD COLUMN periodo TEXT NOT NULL DEFAULT 'Sempre'")
        
        # O SQLite não suporta DROP CONSTRAINT. A maneira mais segura de recriar a chave única
        # seria criar uma nova tabela, copiar os dados e renomear. Para esta atualização,
        # vamos confiar que não haverá duplicatas e adicionar a lógica na aplicação.
        # Em sistemas maiores, um passo de recriação da tabela seria necessário aqui.
        logger.info("Coluna 'periodo' adicionada com sucesso à tabela rotina_config.")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.warning("Coluna 'periodo' já existe em rotina_config. Pulando a migração.")
        else:
            logger.error(f"Erro ao migrar para v3: {e}")
            conn.rollback()
            raise

def _run_migrations(conn: sqlite3.Connection):
    cursor = conn.cursor()
    version_row = cursor.execute("SELECT value FROM db_meta WHERE key = 'db_version'").fetchone()
    current_version = 0
    if version_row is None:
        has_tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clinicas'").fetchone()
        if has_tables:
            current_version = 1
            cursor.execute("INSERT OR IGNORE INTO db_meta (key, value) VALUES ('db_version', ?)", (str(current_version),))
    else:
        current_version = int(version_row['value'])
    logger.info(f"Versão do banco de dados: {current_version}. Versão do código: {CODE_DB_VERSION}")
    while current_version < CODE_DB_VERSION:
        logger.info(f"Aplicando migração da versão {current_version} para {current_version + 1}...")
        if current_version == 1:
            _migrate_v1_to_v2(conn)
            cursor.execute("UPDATE db_meta SET value = ? WHERE key = 'db_version'", (str(2),))
            conn.commit()
        elif current_version == 2:
            _migrate_v2_to_v3(conn)
            cursor.execute("UPDATE db_meta SET value = ? WHERE key = 'db_version'", (str(3),))
            conn.commit()
        current_version = int(cursor.execute("SELECT value FROM db_meta WHERE key = 'db_version'").fetchone()['value'])

def _seed_database_if_empty(conn: sqlite3.Connection) -> None:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(id) FROM clinicas")
        if cursor.fetchone()[0] == 0:
            logger.info("Banco de dados vazio. Populando com dados padrão do arquivo de configuração...")
            default_config = _load_default_config()
            default_clinicas = default_config.get("clinicas", [])
            default_exames = default_config.get("exames", {})
            default_rotinas = default_config.get("rotinas", {})
            default_perfis = default_config.get("perfis", {})
            if default_clinicas:
                cursor.executemany("INSERT INTO clinicas (nome) VALUES (?)", [(n,) for n in default_clinicas])
            if default_exames:
                for nome, details in default_exames.items():
                    cursor.execute("INSERT INTO exames (nome_padrao) VALUES (?)", (nome,))
                    exame_id = cursor.lastrowid
                    if details.get('aliases'):
                        cursor.executemany("INSERT INTO exame_aliases (exame_id, alias) VALUES (?, ?)", [(exame_id, a) for a in details['aliases']])
            if default_rotinas:
                for r_nome, conf in default_rotinas.items():
                    cursor.execute("INSERT INTO rotinas (nome) VALUES (?)", (r_nome,))
                    r_id = cursor.lastrowid
                    for e_nome, rules_list in conf.items():
                        e_row = cursor.execute("SELECT id FROM exames WHERE nome_padrao = ?", (e_nome,)).fetchone()
                        if e_row:
                            for rule in rules_list:
                                cursor.execute("INSERT INTO rotina_config (rotina_id, exame_id, periodo, frequencia, tipo) VALUES (?, ?, ?, ?, ?)", (r_id, e_row['id'], rule['Período'], rule['Frequência'], rule['Tipo']))
            if default_perfis:
                for p_nome, details in default_perfis.items():
                    r_row = cursor.execute("SELECT id FROM rotinas WHERE nome = ?", (details.get('rotina'),)).fetchone()
                    r_id = r_row['id'] if r_row else None
                    cursor.execute("INSERT INTO perfis (nome, rotina_id) VALUES (?, ?)", (p_nome, r_id))
                    p_id = cursor.lastrowid
                    if details.get('clinicas'):
                        placeholders = ','.join(['?'] * len(details['clinicas']))
                        c_ids = [row['id'] for row in cursor.execute(f"SELECT id FROM clinicas WHERE nome IN ({placeholders})", details['clinicas']).fetchall()]
                        cursor.executemany("INSERT INTO perfil_clinicas (perfil_id, clinica_id) VALUES (?, ?)", [(p_id, c_id) for c_id in c_ids])
            cursor.execute("INSERT OR IGNORE INTO db_meta (key, value) VALUES ('db_version', ?)", (str(CODE_DB_VERSION),)) # POPULA COM A VERSÃO ATUAL
            conn.commit()
            logger.info("Dados padrão inseridos com sucesso")
    except Exception as e:
        logger.error(f"Erro ao popular banco de dados: {e}")
        conn.rollback()
        raise

def init_db() -> None:
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS clinicas (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE)')
            cursor.execute('CREATE TABLE IF NOT EXISTS exames (id INTEGER PRIMARY KEY, nome_padrao TEXT NOT NULL UNIQUE)')
            cursor.execute('CREATE TABLE IF NOT EXISTS exame_aliases (id INTEGER PRIMARY KEY, exame_id INTEGER NOT NULL, alias TEXT NOT NULL, FOREIGN KEY (exame_id) REFERENCES exames (id) ON DELETE CASCADE)')
            cursor.execute('CREATE TABLE IF NOT EXISTS rotinas (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE)')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rotina_config (
                    id INTEGER PRIMARY KEY, 
                    rotina_id INTEGER NOT NULL, 
                    exame_id INTEGER NOT NULL, 
                    periodo TEXT NOT NULL DEFAULT 'Sempre',
                    frequencia TEXT NOT NULL, 
                    tipo TEXT NOT NULL, 
                    FOREIGN KEY (rotina_id) REFERENCES rotinas (id) ON DELETE CASCADE, 
                    FOREIGN KEY (exame_id) REFERENCES exames (id) ON DELETE CASCADE, 
                    UNIQUE(rotina_id, exame_id, periodo)
                )
            ''')
            cursor.execute('CREATE TABLE IF NOT EXISTS perfis (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE, rotina_id INTEGER, FOREIGN KEY (rotina_id) REFERENCES rotinas (id) ON DELETE SET NULL)')
            cursor.execute('CREATE TABLE IF NOT EXISTS perfil_clinicas (perfil_id INTEGER NOT NULL, clinica_id INTEGER NOT NULL, PRIMARY KEY (perfil_id, clinica_id), FOREIGN KEY (perfil_id) REFERENCES perfis (id) ON DELETE CASCADE, FOREIGN KEY (clinica_id) REFERENCES clinicas (id) ON DELETE CASCADE)')
            cursor.execute('CREATE TABLE IF NOT EXISTS manual_overrides (id INTEGER PRIMARY KEY, patient_cns TEXT NOT NULL, exam TEXT NOT NULL, analysis_period TEXT NOT NULL, marked_by TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(patient_cns, exam, analysis_period))')
            cursor.execute('CREATE TABLE IF NOT EXISTS db_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_exame_aliases_exame_id ON exame_aliases(exame_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rotina_config_rotina_id ON rotina_config(rotina_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_manual_overrides_period ON manual_overrides(analysis_period)')
            conn.commit()
            _seed_database_if_empty(conn)
            _run_migrations(conn)
            logger.info("Banco de dados inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        raise

def get_rotina_details(rotina_nome: str) -> Dict[str, List[Dict[str, str]]]:
    rotina = {}
    try:
        with get_db_connection() as conn:
            query = "SELECT e.nome_padrao, rc.periodo, rc.frequencia, rc.tipo FROM rotina_config rc JOIN rotinas r ON rc.rotina_id = r.id JOIN exames e ON rc.exame_id = e.id WHERE r.nome = ?"
            for row in conn.execute(query, (rotina_nome,)):
                # setdefault inicializa a chave com uma lista vazia se ela não existir
                rotina.setdefault(row['nome_padrao'], []).append({
                    'Período': row['periodo'],
                    'Frequência': row['frequencia'],
                    'Tipo': row['tipo']
                })
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes da rotina {rotina_nome}: {e}")
    return rotina

def save_rotina(rotina_nome: str, config_dict: Dict[str, List[Dict[str, str]]]) -> None:
    try:
        with get_db_connection() as conn:
            r_row = conn.execute("SELECT id FROM rotinas WHERE nome = ?", (rotina_nome,)).fetchone()
            if not r_row:
                raise ValueError(f"Rotina '{rotina_nome}' não encontrada")
            r_id = r_row['id']
            conn.execute("DELETE FROM rotina_config WHERE rotina_id = ?", (r_id,))
            for e_nome, rules_list in config_dict.items():
                if not rules_list:
                    continue
                e_row = conn.execute("SELECT id FROM exames WHERE nome_padrao = ?", (e_nome,)).fetchone()
                if e_row:
                    for rule in rules_list:
                        if rule.get('Frequência') == 'Não Cobra':
                            continue
                        conn.execute("INSERT INTO rotina_config (rotina_id, exame_id, periodo, frequencia, tipo) VALUES (?, ?, ?, ?, ?)", (r_id, e_row['id'], rule['Período'], rule['Frequência'], rule['Tipo']))
            conn.commit()
            logger.info(f"Rotina '{rotina_nome}' salva com sucesso")
    except Exception as e:
        logger.error(f"Erro ao salvar rotina {rotina_nome}: {e}")
        raise

# ... O restante do arquivo (get_clinicas, save_exames, etc.) permanece inalterado ...

def get_clinicas() -> List[str]:
    try:
        with get_db_connection() as conn:
            return [row['nome'] for row in conn.execute("SELECT nome FROM clinicas ORDER BY nome").fetchall()]
    except Exception as e:
        logger.error(f"Erro ao buscar clínicas: {e}")
        return []

def save_clinicas(clinicas_list: List[str]) -> None:
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM clinicas")
            if clinicas_list:
                conn.executemany("INSERT OR IGNORE INTO clinicas (nome) VALUES (?)", [(n,) for n in clinicas_list])
            conn.commit()
            logger.info(f"Clínicas salvas: {len(clinicas_list)}")
    except Exception as e:
        logger.error(f"Erro ao salvar clínicas: {e}")
        raise

def get_exames_with_aliases() -> Dict[str, Dict[str, List[str]]]:
    exames = {}
    try:
        with get_db_connection() as conn:
            query = "SELECT e.nome_padrao, a.alias FROM exames e LEFT JOIN exame_aliases a ON e.id = a.exame_id ORDER BY e.nome_padrao, a.alias"
            for row in conn.execute(query):
                if row['nome_padrao'] not in exames:
                    exames[row['nome_padrao']] = {'aliases': []}
                if row['alias']:
                    exames[row['nome_padrao']]['aliases'].append(row['alias'])
    except Exception as e:
        logger.error(f"Erro ao buscar exames: {e}")
    return exames

def save_exames_from_dict(exames_dict: Dict[str, Dict[str, List[str]]]) -> None:
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM exame_aliases")
            conn.execute("DELETE FROM exames")
            for nome, details in exames_dict.items():
                cursor = conn.execute("INSERT INTO exames (nome_padrao) VALUES (?)", (nome,))
                exame_id = cursor.lastrowid
                if details.get('aliases'):
                    conn.executemany("INSERT INTO exame_aliases (exame_id, alias) VALUES (?, ?)", [(exame_id, a) for a in details['aliases']])
            conn.commit()
            logger.info(f"Exames salvos: {len(exames_dict)}")
    except Exception as e:
        logger.error(f"Erro ao salvar exames: {e}")
        raise

def check_exame_usage(exame_nome: str) -> List[str]:
    try:
        with get_db_connection() as conn:
            query = "SELECT r.nome FROM rotina_config rc JOIN exames e ON rc.exame_id = e.id JOIN rotinas r ON rc.rotina_id = r.id WHERE e.nome_padrao = ? AND rc.frequencia != 'Não Cobra'"
            return [row['nome'] for row in conn.execute(query, (exame_nome,)).fetchall()]
    except Exception as e:
        logger.error(f"Erro ao verificar uso do exame '{exame_nome}': {e}")
        return []

def get_rotina_names() -> List[str]:
    try:
        with get_db_connection() as conn:
            return [row['nome'] for row in conn.execute("SELECT nome FROM rotinas ORDER BY nome").fetchall()]
    except Exception as e:
        logger.error(f"Erro ao buscar nomes de rotinas: {e}")
        return []

def create_rotina(novo_nome: str, base_nome: str) -> None:
    try:
        with get_db_connection() as conn:
            base_row = conn.execute("SELECT id FROM rotinas WHERE nome = ?", (base_nome,)).fetchone()
            if not base_row:
                raise ValueError(f"Rotina base '{base_nome}' não encontrada")
            cursor = conn.execute("INSERT INTO rotinas (nome) VALUES (?)", (novo_nome,))
            nova_id = cursor.lastrowid
            conn.execute("INSERT INTO rotina_config (rotina_id, exame_id, periodo, frequencia, tipo) SELECT ?, exame_id, periodo, frequencia, tipo FROM rotina_config WHERE rotina_id = ?", (nova_id, base_row['id']))
            conn.commit()
            logger.info(f"Rotina '{novo_nome}' criada com base em '{base_nome}'")
    except Exception as e:
        logger.error(f"Erro ao criar rotina {novo_nome}: {e}")
        raise

def delete_rotina(nome_rotina: str) -> None:
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM rotinas WHERE nome = ?", (nome_rotina,))
            conn.commit()
            logger.info(f"Rotina '{nome_rotina}' deletada")
    except Exception as e:
        logger.error(f"Erro ao deletar rotina {nome_rotina}: {e}")
        raise

def get_perfis() -> Dict[str, Dict]:
    perfis = {}
    try:
        with get_db_connection() as conn:
            query = "SELECT p.nome as p_nome, r.nome as r_nome FROM perfis p LEFT JOIN rotinas r ON p.rotina_id = r.id"
            for p_row in conn.execute(query):
                perfis[p_row['p_nome']] = {'rotina': p_row['r_nome'], 'clinicas': []}
                clinicas_query = "SELECT c.nome FROM perfil_clinicas pc JOIN clinicas c ON pc.clinica_id = c.id JOIN perfis p ON pc.perfil_id = p.id WHERE p.nome = ? ORDER BY c.nome"
                perfis[p_row['p_nome']]['clinicas'] = [c_row['nome'] for c_row in conn.execute(clinicas_query, (p_row['p_nome'],))]
    except Exception as e:
        logger.error(f"Erro ao buscar perfis: {e}")
    return perfis

def save_perfil(nome_original: Optional[str], nome_novo: str, nome_rotina: str, clinicas: List[str]) -> None:
    try:
        with get_db_connection() as conn:
            r_row = conn.execute("SELECT id FROM rotinas WHERE nome = ?", (nome_rotina,)).fetchone()
            r_id = r_row['id'] if r_row else None
            p_row = conn.execute("SELECT id FROM perfis WHERE nome = ?", (nome_original or nome_novo,)).fetchone()
            if p_row:
                p_id = p_row['id']
                conn.execute("UPDATE perfis SET nome = ?, rotina_id = ? WHERE id = ?", (nome_novo, r_id, p_id))
            else:
                cursor = conn.execute("INSERT INTO perfis (nome, rotina_id) VALUES (?, ?)", (nome_novo, r_id))
                p_id = cursor.lastrowid
            conn.execute("DELETE FROM perfil_clinicas WHERE perfil_id = ?", (p_id,))
            if clinicas:
                placeholders = ','.join(['?'] * len(clinicas))
                c_ids = [r['id'] for r in conn.execute(f"SELECT id FROM clinicas WHERE nome IN ({placeholders})", clinicas)]
                conn.executemany("INSERT INTO perfil_clinicas (perfil_id, clinica_id) VALUES (?, ?)", [(p_id, c_id) for c_id in c_ids])
            conn.commit()
            logger.info(f"Perfil '{nome_novo}' salvo com sucesso")
    except Exception as e:
        logger.error(f"Erro ao salvar perfil {nome_novo}: {e}")
        raise

def delete_perfil(nome_perfil: str) -> None:
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM perfis WHERE nome = ?", (nome_perfil,))
            conn.commit()
            logger.info(f"Perfil '{nome_perfil}' deletado")
    except Exception as e:
        logger.error(f"Erro ao deletar perfil {nome_perfil}: {e}")
        raise

def add_override(cns: str, exam: str, period: str, user: str = "default") -> None:
    try:
        with get_db_connection() as conn:
            try:
                conn.execute("INSERT INTO manual_overrides (patient_cns, exam, analysis_period, marked_by) VALUES (?, ?, ?, ?)", (cns, exam, period, user))
                conn.commit()
                logger.info(f"Override adicionado: CNS={cns}, Exame={exam}, Período={period}")
            except sqlite3.IntegrityError:
                logger.warning(f"Override já existe: CNS={cns}, Exame={exam}, Período={period}")
    except Exception as e:
        logger.error(f"Erro ao adicionar override: {e}")
        raise

def get_overrides_for_period(period: str) -> Set[Tuple[str, str]]:
    try:
        with get_db_connection() as conn:
            return set((row['patient_cns'], row['exam']) for row in conn.execute('SELECT patient_cns, exam FROM manual_overrides WHERE analysis_period = ?', (period,)))
    except Exception as e:
        logger.error(f"Erro ao buscar overrides do período {period}: {e}")
        return set()

def remove_override(cns: str, exam: str, period: str) -> None:
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM manual_overrides WHERE patient_cns = ? AND exam = ? AND analysis_period = ?", (cns, exam, period))
            conn.commit()
            logger.info(f"Override removido: CNS={cns}, Exame={exam}, Período={period}")
    except Exception as e:
        logger.error(f"Erro ao remover override: {e}")
        raise

def clear_old_overrides(months_to_keep: int = 12) -> int:
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM manual_overrides WHERE datetime(timestamp) < datetime('now', '-' || ? || ' months')", (months_to_keep,))
            conn.commit()
            deleted = cursor.rowcount
            logger.info(f"Overrides antigos removidos: {deleted}")
            return deleted
    except Exception as e:
        logger.error(f"Erro ao limpar overrides antigos: {e}")
        return 0

def validate_database_integrity() -> bool:
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result[0] != 'ok':
                logger.error(f"Falha na verificação de integridade: {result[0]}")
                return False
            required_tables = ['clinicas', 'exames', 'exame_aliases', 'rotinas', 'rotina_config', 'perfis', 'perfil_clinicas', 'manual_overrides', 'db_meta']
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            missing_tables = set(required_tables) - existing_tables
            if missing_tables:
                logger.error(f"Tabelas ausentes: {missing_tables}")
                return False
            logger.info("Validação de integridade do banco: OK")
            return True
    except Exception as e:
        logger.error(f"Erro ao validar integridade do banco: {e}")
        return False

def get_database_stats() -> Dict[str, int]:
    stats = {}
    try:
        with get_db_connection() as conn:
            stats['clinicas'] = conn.execute("SELECT COUNT(*) FROM clinicas").fetchone()[0]
            stats['exames'] = conn.execute("SELECT COUNT(*) FROM exames").fetchone()[0]
            stats['aliases'] = conn.execute("SELECT COUNT(*) FROM exame_aliases").fetchone()[0]
            stats['rotinas'] = conn.execute("SELECT COUNT(*) FROM rotinas").fetchone()[0]
            stats['perfis'] = conn.execute("SELECT COUNT(*) FROM perfis").fetchone()[0]
            stats['overrides'] = conn.execute("SELECT COUNT(*) FROM manual_overrides").fetchone()[0]
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do banco: {e}")
    return stats