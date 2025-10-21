import sqlite3
import logging
from contextlib import contextmanager
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

DB_FILE: Optional[Path] = None

def set_database_path(data_dir: Path):
    global DB_FILE
    data_dir.mkdir(parents=True, exist_ok=True)
    DB_FILE = data_dir / "app.db"
    logger.info(f"Caminho do banco de dados definido para: {DB_FILE}")

DEFAULT_CLINICAS = [
    "Clinica do Rim",
    "Instituto do Rim"
]

DEFAULT_EXAMES = {
    "25-Hidroxivitamina D": {
        "aliases": [
            "Vit. D"
        ]
    },
    "Albumina": {
        "aliases": [
            "Alb"
        ]
    },
    "Aluminio Serico": {
        "aliases": [
            "Al"
        ]
    },
    "Anti-HBs": {
        "aliases": [
            "A HBs"
        ]
    },
    "Anti-HCV": {
        "aliases": [
            "A HCV"
        ]
    },
    "Anti-HIV": {
        "aliases": [
            "A HIV"
        ]
    },
    "Ca x P": {
        "aliases": [
            "Ca x P"
        ]
    },
    "Calcio": {
        "aliases": [
            "Ca"
        ]
    },
    "Calcio Corrigido pela Albumina": {
        "aliases": [
            "Calcio Corrigido pela Albumina"
        ]
    },
    "Capacidade Total Ligacao Ferro": {
        "aliases": [
            "CTLF"
        ]
    },
    "Clearence de Creatinina": {
        "aliases": [
            "Clearance de Creatinina"
        ]
    },
    "Colesterol HDL": {
        "aliases": [
            "HDL"
        ]
    },
    "Colesterol LDL": {
        "aliases": [
            "LDL"
        ]
    },
    "Colesterol Total": {
        "aliases": [
            "COL"
        ]
    },
    "Colesterol VLDL": {
        "aliases": [
            "VLDL"
        ]
    },
    "Creatinina": {
        "aliases": [
            "CR"
        ]
    },
    "Ferritina": {
        "aliases": [
            "Ferrit"
        ]
    },
    "Ferro Serico": {
        "aliases": [
            "Ferro"
        ]
    },
    "Fosfatase Alcalina": {
        "aliases": [
            "Fosf Alc"
        ]
    },
    "Fosforo": {
        "aliases": [
            "P"
        ]
    },
    "Glicose": {
        "aliases": [
            "Glic"
        ]
    },
    "Globulina": {
        "aliases": [
            "Glob"
        ]
    },
    "Grupo Sanguineo": {
        "aliases": [
            "ABORh"
        ]
    },
    "HbsAg": {
        "aliases": [
            "HbsAg"
        ]
    },
    "Hemacias": {
        "aliases": [
            "Hemacias"
        ]
    },
    "Hematocrito": {
        "aliases": [
            "HT"
        ]
    },
    "Hemoglobina": {
        "aliases": [
            "HB"
        ]
    },
    "Hemograma": {
        "aliases": [
            "Hemograma"
        ]
    },
    "Kt/V": {
        "aliases": [
            "Kt/V"
        ]
    },
    "Kt/V Equilibrado": {
        "aliases": [
            "eKt/V"
        ]
    },
    "Kt/V Standard": {
        "aliases": [
            "stdKt/V"
        ]
    },
    "Leucocitos": {
        "aliases": [
            "Leucocitos"
        ]
    },
    "PCRn SP": {
        "aliases": [
            "PCRn SP"
        ]
    },
    "PNA": {
        "aliases": [
            "PNA"
        ]
    },
    "PTH": {
        "aliases": [
            "PTH"
        ]
    },
    "Plaquetas": {
        "aliases": [
            "Plaquetas"
        ]
    },
    "Potassio": {
        "aliases": [
            "K"
        ]
    },
    "Proteinas Totais": {
        "aliases": [
            "Prot T"
        ]
    },
    "Saturaçao da Transferrina": {
        "aliases": [
            "Sat Transf"
        ]
    },
    "Sodio": {
        "aliases": [
            "Na"
        ]
    },
    "T4": {
        "aliases": [
            "T4"
        ]
    },
    "TAC Ureia SP": {
        "aliases": [
            "TAC Ureia SP"
        ]
    },
    "TFG": {
        "aliases": [
            "TFG"
        ]
    },
    "TGP": {
        "aliases": [
            "TGP"
        ]
    },
    "TSH": {
        "aliases": [
            "TSH"
        ]
    },
    "Triglicerideos": {
        "aliases": [
            "Trigl."
        ]
    },
    "URR": {
        "aliases": [
            "URR"
        ]
    },
    "Ureia": {
        "aliases": [
            "UR"
        ]
    },
    "Ureia Pós": {
        "aliases": [
            "UR Pós"
        ]
    }
}

DEFAULT_ROTINAS = {
    "Padrão": {
        "25-Hidroxivitamina D": {"Frequência": "Semestral", "Tipo": "Obrigatório"}, 
        "Anti-HBs": {"Frequência": "Semestral", "Tipo": "Obrigatório"},
        "Anti-HCV": {"Frequência": "Semestral", "Tipo": "Obrigatório"}, 
        "HbsAg": {"Frequência": "Semestral", "Tipo": "Obrigatório"},
        "Anti-HIV": {"Frequência": "Anual", "Tipo": "Obrigatório"}, 
        "Capacidade Total Ligacao Ferro": {"Frequência": "Trimestral", "Tipo": "Obrigatório"},
        "Ferritina": {"Frequência": "Trimestral", "Tipo": "Obrigatório"}, 
        "Ferro Serico": {"Frequência": "Trimestral", "Tipo": "Obrigatório"},
        "Fosfatase Alcalina": {"Frequência": "Trimestral", "Tipo": "Obrigatório"}, 
        "Proteinas Totais": {"Frequência": "Trimestral", "Tipo": "Obrigatório"},
        "PTH": {"Frequência": "Trimestral", "Tipo": "Obrigatório"}, 
        "Saturação da Transferrina": {"Frequência": "Trimestral", "Tipo": "Obrigatório"},
        "Hemograma": {"Frequência": "Trimestral", "Tipo": "Opcional"}, 
        "Colesterol HDL": {"Frequência": "Anual", "Tipo": "Obrigatório"},
        "Colesterol LDL": {"Frequência": "Anual", "Tipo": "Obrigatório"}, 
        "Colesterol Total": {"Frequência": "Anual", "Tipo": "Obrigatório"},
        "Colesterol VLDL": {"Frequência": "Anual", "Tipo": "Obrigatório"}, 
        "Creatinina": {"Frequência": "Anual", "Tipo": "Obrigatório"},
        "Glicose": {"Frequência": "Anual", "Tipo": "Obrigatório"}, 
        "T4": {"Frequência": "Anual", "Tipo": "Obrigatório"},
        "Triglicerideos": {"Frequência": "Anual", "Tipo": "Obrigatório"}, 
        "TSH": {"Frequência": "Anual", "Tipo": "Obrigatório"},
        "Clearence de Creatinina": {"Frequência": "Anual", "Tipo": "Opcional"}, 
        "Aluminio Serico": {"Frequência": "Anual", "Tipo": "Obrigatório"},
        "Calcio": {"Frequência": "Mensal", "Tipo": "Obrigatório"}, 
        "Fosforo": {"Frequência": "Mensal", "Tipo": "Obrigatório"},
        "Hematocrito": {"Frequência": "Mensal", "Tipo": "Obrigatório"}, 
        "Hemoglobina": {"Frequência": "Mensal", "Tipo": "Obrigatório"},
        "Potassio": {"Frequência": "Mensal", "Tipo": "Obrigatório"}, 
        "Sodio": {"Frequência": "Mensal", "Tipo": "Obrigatório"},
        "TGP": {"Frequência": "Mensal", "Tipo": "Obrigatório"}, 
        "Ureia": {"Frequência": "Mensal", "Tipo": "Obrigatório"},
        "Ureia Pós": {"Frequência": "Mensal", "Tipo": "Obrigatório"}, 
        "Albumina": {"Frequência": "Não Cobra", "Tipo": "Opcional"},
        "Ca x P": {"Frequência": "Não Cobra", "Tipo": "Opcional"}, 
        "Calcio Corrigido pela Albumina": {"Frequência": "Não Cobra", "Tipo": "Opcional"},
        "Globulina": {"Frequência": "Trimestral", "Tipo": "Obrigatório"}, 
        "Grupo Sanguineo": {"Frequência": "Não Cobra", "Tipo": "Opcional"},
        "Hemacias": {"Frequência": "Não Cobra", "Tipo": "Opcional"}, 
        "Kt/V": {"Frequência": "Não Cobra", "Tipo": "Opcional"},
        "Kt/V Equilibrado": {"Frequência": "Não Cobra", "Tipo": "Opcional"}, 
        "Kt/V Standard": {"Frequência": "Não Cobra", "Tipo": "Opcional"},
        "Leucocitos": {"Frequência": "Não Cobra", "Tipo": "Opcional"}, 
        "PCRn SP": {"Frequência": "Não Cobra", "Tipo": "Opcional"},
        "PNA": {"Frequência": "Não Cobra", "Tipo": "Opcional"}, 
        "Plaquetas": {"Frequência": "Não Cobra", "Tipo": "Opcional"},
        "TAC Ureia SP": {"Frequência": "Não Cobra", "Tipo": "Opcional"}, 
        "TFG": {"Frequência": "Não Cobra", "Tipo": "Opcional"},
        "URR": {"Frequência": "Não Cobra", "Tipo": "Opcional"}
    }
}

DEFAULT_PERFIS = {
    "Padrão": { 
        "rotina": "Padrão", 
        "clinicas": ["Clinica do Rim", "Instituto do Rim"] 
    }
}


@contextmanager
def get_db_connection():
    """Context manager para conexão com banco de dados."""
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


def _seed_database_if_empty(conn: sqlite3.Connection) -> None:
    """Popula o banco de dados com dados padrão se estiver vazio."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(id) FROM clinicas")
        
        if cursor.fetchone()[0] == 0:
            logger.info("Populando banco de dados com dados padrão...")
            
            # Inserir clínicas
            if DEFAULT_CLINICAS:
                cursor.executemany(
                    "INSERT INTO clinicas (nome) VALUES (?)", 
                    [(n,) for n in DEFAULT_CLINICAS]
                )
            
            # Inserir exames e aliases
            if DEFAULT_EXAMES:
                for nome, details in DEFAULT_EXAMES.items():
                    cursor.execute("INSERT INTO exames (nome_padrao) VALUES (?)", (nome,))
                    exame_id = cursor.lastrowid
                    if details.get('aliases'):
                        cursor.executemany(
                            "INSERT INTO exame_aliases (exame_id, alias) VALUES (?, ?)", 
                            [(exame_id, a) for a in details['aliases']]
                        )
            
            # Inserir rotinas
            if DEFAULT_ROTINAS:
                for r_nome, conf in DEFAULT_ROTINAS.items():
                    cursor.execute("INSERT INTO rotinas (nome) VALUES (?)", (r_nome,))
                    r_id = cursor.lastrowid
                    for e_nome, details in conf.items():
                        cursor.execute("SELECT id FROM exames WHERE nome_padrao = ?", (e_nome,))
                        e_row = cursor.fetchone()
                        if e_row:
                            cursor.execute(
                                "INSERT INTO rotina_config (rotina_id, exame_id, frequencia, tipo) VALUES (?, ?, ?, ?)",
                                (r_id, e_row['id'], details['Frequência'], details['Tipo'])
                            )
            
            # Inserir perfis
            if DEFAULT_PERFIS:
                for p_nome, details in DEFAULT_PERFIS.items():
                    cursor.execute("SELECT id FROM rotinas WHERE nome = ?", (details.get('rotina'),))
                    r_row = cursor.fetchone()
                    r_id = r_row['id'] if r_row else None
                    cursor.execute("INSERT INTO perfis (nome, rotina_id) VALUES (?, ?)", (p_nome, r_id))
                    p_id = cursor.lastrowid
                    if details.get('clinicas'):
                        placeholders = ','.join(['?'] * len(details['clinicas']))
                        cursor.execute(
                            f"SELECT id FROM clinicas WHERE nome IN ({placeholders})", 
                            details['clinicas']
                        )
                        c_ids = [row['id'] for row in cursor.fetchall()]
                        cursor.executemany(
                            "INSERT INTO perfil_clinicas (perfil_id, clinica_id) VALUES (?, ?)", 
                            [(p_id, c_id) for c_id in c_ids]
                        )
            
            conn.commit()
            logger.info("Dados padrão inseridos com sucesso")
    except Exception as e:
        logger.error(f"Erro ao popular banco de dados: {e}")
        conn.rollback()
        raise


def init_db() -> None:
    """Inicializa o banco de dados criando tabelas se necessário."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Criar tabelas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clinicas (
                    id INTEGER PRIMARY KEY, 
                    nome TEXT NOT NULL UNIQUE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS exames (
                    id INTEGER PRIMARY KEY, 
                    nome_padrao TEXT NOT NULL UNIQUE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS exame_aliases (
                    id INTEGER PRIMARY KEY, 
                    exame_id INTEGER NOT NULL, 
                    alias TEXT NOT NULL, 
                    FOREIGN KEY (exame_id) REFERENCES exames (id) ON DELETE CASCADE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rotinas (
                    id INTEGER PRIMARY KEY, 
                    nome TEXT NOT NULL UNIQUE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rotina_config (
                    id INTEGER PRIMARY KEY, 
                    rotina_id INTEGER NOT NULL, 
                    exame_id INTEGER NOT NULL, 
                    frequencia TEXT NOT NULL, 
                    tipo TEXT NOT NULL, 
                    FOREIGN KEY (rotina_id) REFERENCES rotinas (id) ON DELETE CASCADE, 
                    FOREIGN KEY (exame_id) REFERENCES exames (id) ON DELETE CASCADE, 
                    UNIQUE(rotina_id, exame_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS perfis (
                    id INTEGER PRIMARY KEY, 
                    nome TEXT NOT NULL UNIQUE, 
                    rotina_id INTEGER, 
                    FOREIGN KEY (rotina_id) REFERENCES rotinas (id) ON DELETE SET NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS perfil_clinicas (
                    perfil_id INTEGER NOT NULL, 
                    clinica_id INTEGER NOT NULL, 
                    PRIMARY KEY (perfil_id, clinica_id), 
                    FOREIGN KEY (perfil_id) REFERENCES perfis (id) ON DELETE CASCADE, 
                    FOREIGN KEY (clinica_id) REFERENCES clinicas (id) ON DELETE CASCADE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS manual_overrides (
                    id INTEGER PRIMARY KEY, 
                    patient_cns TEXT NOT NULL, 
                    exam TEXT NOT NULL, 
                    analysis_period TEXT NOT NULL, 
                    marked_by TEXT, 
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                    UNIQUE(patient_cns, exam, analysis_period)
                )
            ''')
            
            # Criar índices para melhor performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_exame_aliases_exame_id 
                ON exame_aliases(exame_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_rotina_config_rotina_id 
                ON rotina_config(rotina_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_manual_overrides_period 
                ON manual_overrides(analysis_period)
            ''')
            
            conn.commit()
            _seed_database_if_empty(conn)
            logger.info("Banco de dados inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        raise


def get_clinicas() -> List[str]:
    """Retorna lista de todas as clínicas cadastradas."""
    try:
        with get_db_connection() as conn:
            return [row['nome'] for row in conn.execute(
                "SELECT nome FROM clinicas ORDER BY nome"
            ).fetchall()]
    except Exception as e:
        logger.error(f"Erro ao buscar clínicas: {e}")
        return []


def save_clinicas(clinicas_list: List[str]) -> None:
    """Salva lista de clínicas, substituindo todas as existentes."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM clinicas")
            if clinicas_list:
                conn.executemany(
                    "INSERT OR IGNORE INTO clinicas (nome) VALUES (?)", 
                    [(n,) for n in clinicas_list]
                )
            conn.commit()
            logger.info(f"Clínicas salvas: {len(clinicas_list)}")
    except Exception as e:
        logger.error(f"Erro ao salvar clínicas: {e}")
        raise


def get_exames_with_aliases() -> Dict[str, Dict[str, List[str]]]:
    """Retorna dicionário de exames com seus aliases."""
    exames = {}
    try:
        with get_db_connection() as conn:
            query = """
                SELECT e.nome_padrao, a.alias 
                FROM exames e 
                LEFT JOIN exame_aliases a ON e.id = a.exame_id 
                ORDER BY e.nome_padrao, a.alias
            """
            for row in conn.execute(query):
                if row['nome_padrao'] not in exames:
                    exames[row['nome_padrao']] = {'aliases': []}
                if row['alias']:
                    exames[row['nome_padrao']]['aliases'].append(row['alias'])
    except Exception as e:
        logger.error(f"Erro ao buscar exames: {e}")
    return exames


def save_exames_from_dict(exames_dict: Dict[str, Dict[str, List[str]]]) -> None:
    """Salva exames e aliases a partir de um dicionário."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM exame_aliases")
            conn.execute("DELETE FROM exames")
            for nome, details in exames_dict.items():
                cursor = conn.execute("INSERT INTO exames (nome_padrao) VALUES (?)", (nome,))
                exame_id = cursor.lastrowid
                if details.get('aliases'):
                    conn.executemany(
                        "INSERT INTO exame_aliases (exame_id, alias) VALUES (?, ?)", 
                        [(exame_id, a) for a in details['aliases']]
                    )
            conn.commit()
            logger.info(f"Exames salvos: {len(exames_dict)}")
    except Exception as e:
        logger.error(f"Erro ao salvar exames: {e}")
        raise


def get_rotina_names() -> List[str]:
    """Retorna lista de nomes de todas as rotinas."""
    try:
        with get_db_connection() as conn:
            return [row['nome'] for row in conn.execute(
                "SELECT nome FROM rotinas ORDER BY nome"
            ).fetchall()]
    except Exception as e:
        logger.error(f"Erro ao buscar nomes de rotinas: {e}")
        return []


def get_rotina_details(rotina_nome: str) -> Dict[str, Dict[str, str]]:
    """Retorna detalhes completos de uma rotina específica."""
    rotina = {}
    try:
        with get_db_connection() as conn:
            query = """
                SELECT e.nome_padrao, rc.frequencia, rc.tipo 
                FROM rotina_config rc 
                JOIN rotinas r ON rc.rotina_id = r.id 
                JOIN exames e ON rc.exame_id = e.id 
                WHERE r.nome = ?
            """
            for row in conn.execute(query, (rotina_nome,)):
                rotina[row['nome_padrao']] = {
                    'Frequência': row['frequencia'], 
                    'Tipo': row['tipo']
                }
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes da rotina {rotina_nome}: {e}")
    return rotina


def save_rotina(rotina_nome: str, config_dict: Dict[str, Dict[str, str]]) -> None:
    """Salva configuração de uma rotina."""
    try:
        with get_db_connection() as conn:
            r_row = conn.execute("SELECT id FROM rotinas WHERE nome = ?", (rotina_nome,)).fetchone()
            if not r_row:
                raise ValueError(f"Rotina '{rotina_nome}' não encontrada")
            
            r_id = r_row['id']
            conn.execute("DELETE FROM rotina_config WHERE rotina_id = ?", (r_id,))
            
            for e_nome, details in config_dict.items():
                e_row = conn.execute("SELECT id FROM exames WHERE nome_padrao = ?", (e_nome,)).fetchone()
                if e_row:
                    conn.execute(
                        "INSERT INTO rotina_config (rotina_id, exame_id, frequencia, tipo) VALUES (?, ?, ?, ?)",
                        (r_id, e_row['id'], details['Frequência'], details['Tipo'])
                    )
            conn.commit()
            logger.info(f"Rotina '{rotina_nome}' salva com sucesso")
    except Exception as e:
        logger.error(f"Erro ao salvar rotina {rotina_nome}: {e}")
        raise


def create_rotina(novo_nome: str, base_nome: str) -> None:
    """Cria uma nova rotina baseada em uma existente."""
    try:
        with get_db_connection() as conn:
            base_row = conn.execute("SELECT id FROM rotinas WHERE nome = ?", (base_nome,)).fetchone()
            if not base_row:
                raise ValueError(f"Rotina base '{base_nome}' não encontrada")
            
            cursor = conn.execute("INSERT INTO rotinas (nome) VALUES (?)", (novo_nome,))
            nova_id = cursor.lastrowid
            conn.execute(
                """INSERT INTO rotina_config (rotina_id, exame_id, frequencia, tipo) 
                   SELECT ?, exame_id, frequencia, tipo 
                   FROM rotina_config 
                   WHERE rotina_id = ?""",
                (nova_id, base_row['id'])
            )
            conn.commit()
            logger.info(f"Rotina '{novo_nome}' criada com base em '{base_nome}'")
    except Exception as e:
        logger.error(f"Erro ao criar rotina {novo_nome}: {e}")
        raise


def delete_rotina(nome_rotina: str) -> None:
    """Deleta uma rotina e suas configurações."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM rotinas WHERE nome = ?", (nome_rotina,))
            conn.commit()
            logger.info(f"Rotina '{nome_rotina}' deletada")
    except Exception as e:
        logger.error(f"Erro ao deletar rotina {nome_rotina}: {e}")
        raise


def get_perfis() -> Dict[str, Dict]:
    """Retorna todos os perfis com suas rotinas e clínicas associadas."""
    perfis = {}
    try:
        with get_db_connection() as conn:
            query = """
                SELECT p.nome as p_nome, r.nome as r_nome 
                FROM perfis p 
                LEFT JOIN rotinas r ON p.rotina_id = r.id
            """
            for p_row in conn.execute(query):
                perfis[p_row['p_nome']] = {
                    'rotina': p_row['r_nome'], 
                    'clinicas': []
                }
                clinicas_query = """
                    SELECT c.nome 
                    FROM perfil_clinicas pc 
                    JOIN clinicas c ON pc.clinica_id = c.id 
                    JOIN perfis p ON pc.perfil_id = p.id 
                    WHERE p.nome = ? 
                    ORDER BY c.nome
                """
                perfis[p_row['p_nome']]['clinicas'] = [
                    c_row['nome'] for c_row in conn.execute(clinicas_query, (p_row['p_nome'],))
                ]
    except Exception as e:
        logger.error(f"Erro ao buscar perfis: {e}")
    return perfis


def save_perfil(nome_original: Optional[str], nome_novo: str, nome_rotina: str, clinicas: List[str]) -> None:
    """Salva ou atualiza um perfil."""
    try:
        with get_db_connection() as conn:
            # Buscar ID da rotina
            r_row = conn.execute("SELECT id FROM rotinas WHERE nome = ?", (nome_rotina,)).fetchone()
            r_id = r_row['id'] if r_row else None
            
            # Verificar se perfil já existe
            p_row = conn.execute(
                "SELECT id FROM perfis WHERE nome = ?", 
                (nome_original or nome_novo,)
            ).fetchone()
            
            if p_row:
                # Atualizar perfil existente
                p_id = p_row['id']
                conn.execute(
                    "UPDATE perfis SET nome = ?, rotina_id = ? WHERE id = ?", 
                    (nome_novo, r_id, p_id)
                )
            else:
                # Criar novo perfil
                cursor = conn.execute(
                    "INSERT INTO perfis (nome, rotina_id) VALUES (?, ?)", 
                    (nome_novo, r_id)
                )
                p_id = cursor.lastrowid
            
            # Atualizar clínicas associadas
            conn.execute("DELETE FROM perfil_clinicas WHERE perfil_id = ?", (p_id,))
            if clinicas:
                placeholders = ','.join(['?'] * len(clinicas))
                c_ids = [
                    r['id'] for r in conn.execute(
                        f"SELECT id FROM clinicas WHERE nome IN ({placeholders})", 
                        clinicas
                    )
                ]
                conn.executemany(
                    "INSERT INTO perfil_clinicas (perfil_id, clinica_id) VALUES (?, ?)", 
                    [(p_id, c_id) for c_id in c_ids]
                )
            
            conn.commit()
            logger.info(f"Perfil '{nome_novo}' salvo com sucesso")
    except Exception as e:
        logger.error(f"Erro ao salvar perfil {nome_novo}: {e}")
        raise


def delete_perfil(nome_perfil: str) -> None:
    """Deleta um perfil."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM perfis WHERE nome = ?", (nome_perfil,))
            conn.commit()
            logger.info(f"Perfil '{nome_perfil}' deletado")
    except Exception as e:
        logger.error(f"Erro ao deletar perfil {nome_perfil}: {e}")
        raise


def add_override(cns: str, exam: str, period: str, user: str = "default") -> None:
    """Adiciona um override manual para um exame de paciente."""
    try:
        with get_db_connection() as conn:
            try:
                conn.execute(
                    """INSERT INTO manual_overrides 
                       (patient_cns, exam, analysis_period, marked_by) 
                       VALUES (?, ?, ?, ?)""",
                    (cns, exam, period, user)
                )
                conn.commit()
                logger.info(f"Override adicionado: CNS={cns}, Exame={exam}, Período={period}")
            except sqlite3.IntegrityError:
                logger.warning(f"Override já existe: CNS={cns}, Exame={exam}, Período={period}")
    except Exception as e:
        logger.error(f"Erro ao adicionar override: {e}")
        raise


def get_overrides_for_period(period: str) -> Set[Tuple[str, str]]:
    """Retorna conjunto de overrides para um período específico."""
    try:
        with get_db_connection() as conn:
            return set(
                (row['patient_cns'], row['exam']) 
                for row in conn.execute(
                    'SELECT patient_cns, exam FROM manual_overrides WHERE analysis_period = ?', 
                    (period,)
                )
            )
    except Exception as e:
        logger.error(f"Erro ao buscar overrides do período {period}: {e}")
        return set()


def remove_override(cns: str, exam: str, period: str) -> None:
    """Remove um override específico."""
    try:
        with get_db_connection() as conn:
            conn.execute(
                """DELETE FROM manual_overrides 
                   WHERE patient_cns = ? AND exam = ? AND analysis_period = ?""",
                (cns, exam, period)
            )
            conn.commit()
            logger.info(f"Override removido: CNS={cns}, Exame={exam}, Período={period}")
    except Exception as e:
        logger.error(f"Erro ao remover override: {e}")
        raise


def clear_old_overrides(months_to_keep: int = 12) -> int:
    """Remove overrides antigos. Retorna número de registros removidos."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                """DELETE FROM manual_overrides 
                   WHERE datetime(timestamp) < datetime('now', '-' || ? || ' months')""",
                (months_to_keep,)
            )
            conn.commit()
            deleted = cursor.rowcount
            logger.info(f"Overrides antigos removidos: {deleted}")
            return deleted
    except Exception as e:
        logger.error(f"Erro ao limpar overrides antigos: {e}")
        return 0


def validate_database_integrity() -> bool:
    """Valida a integridade do banco de dados."""
    try:
        with get_db_connection() as conn:
            # Verificar integridade
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result[0] != 'ok':
                logger.error(f"Falha na verificação de integridade: {result[0]}")
                return False
            
            # Verificar se todas as tabelas existem
            required_tables = [
                'clinicas', 'exames', 'exame_aliases', 'rotinas', 
                'rotina_config', 'perfis', 'perfil_clinicas', 'manual_overrides'
            ]
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
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
    """Retorna estatísticas do banco de dados."""
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