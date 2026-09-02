# tatu

> Encontra virtualenvs orfaos, grava o `requirements.txt` de cada projeto e remove os venvs para liberar espaco.

O tatu escava e mantem tocas organizadas, com camaras bem definidas. Esta ferramenta faz o mesmo com seus diretorios: varre em busca de venvs, congela as dependencias de cada projeto num `requirements.txt` e remove os venvs.

Nasceu de um problema real: servicos de sincronizacao (Google Drive, Dropbox, Insync) carregando gigabytes de venvs sem necessidade, muitas vezes com o interpretador quebrado depois da sync.

---

## Por que

- Venvs nao devem ir para sincronizacao nem para o controle de versao. O que importa e o `requirements.txt` (ou `pyproject.toml`).
- Ao longo do tempo eles se acumulam e ocupam muito espaco.
- Apagar na mao e arriscado: voce perde o registro exato das versoes instaladas.

O tatu resolve isso: antes de apagar, grava o snapshot das dependencias.

---

## Instalacao

Requer Python 3.10 ou superior (a propria ferramenta; ela processa venvs de qualquer versao).

```bash
pip install tatu
# ou, a partir do fonte:
git clone git@github.com:luizfpq/tatu.git
cd tatu
pip install -e .
```

Sem dependencias externas: usa apenas a biblioteca padrao.

---

## Uso

Por padrao roda em **dry-run** (nao altera nada). Sempre mostre o que sera feito antes de aplicar.

```bash
# varre o diretorio atual e mostra o que faria
tatu

# varre varios diretorios
tatu ~/Documentos ~/projetos

# aplica de fato (gera requirements.txt e remove os venvs)
tatu ~/Documentos --apply

# modo interativo: pergunta a cada venv
tatu ~/Documentos --apply --interactive

# so gera requirements, sem remover
tatu ~/Documentos --apply --no-remove

# ignora um caminho especifico
tatu ~ --ignore .venvs --ignore backups
```

### Opcoes

| Flag | Efeito |
|------|--------|
| `--apply` | Executa de fato (sem ela, dry-run) |
| `-i`, `--interactive` | Pergunta a cada venv antes de agir |
| `--no-remove` | Apenas gera o requirements, mantem o venv |
| `--no-requirements` | Apenas remove o venv, sem gerar requirements |
| `--no-backup` | Nao faz backup `.bak` de um requirements existente |
| `--include-base` | Inclui `pip`/`setuptools`/`wheel` no requirements |
| `--requirements-name NOME` | Nome do arquivo de saida (padrao `requirements.txt`) |
| `--ignore DIR` | Componente de caminho a ignorar (repetivel) |

---

## Como funciona

### Deteccao

Um venv e identificado pela presenca de `pyvenv.cfg` na raiz (PEP 405), nao pelo nome da pasta. Assim `venv`, `.venv`, `env` e qualquer outra convencao sao detectados. A ferramenta nao desce dentro de um venv ja encontrado.

### Freeze com fallback

Para congelar as dependencias, o tatu tenta duas estrategias, nessa ordem:

1. `<venv>/bin/python -m pip freeze`
2. **Fallback:** le os diretorios `*.dist-info` / `*.egg-info` do `site-packages` e extrai `nome==versao`.

O fallback e o diferencial: venvs sincronizados costumam ter o interpretador quebrado (o symlink do `python` aponta para um caminho que nao veio na sync, ou o modulo `pip` sumiu). Mesmo assim os metadados dos pacotes continuam no disco, e o tatu consegue reconstruir o `requirements.txt`.

### Versao do Python

A versao do interpretador e lida do `pyvenv.cfg` e gravada como comentario no topo do `requirements.txt`, para ajudar a recriar o venv depois:

```
# gerado por tatu (metodo: dist-info)
# python do venv original: 3.11.5
flask==3.0.0
requests==2.31.0
```

### Seguranca

- **Dry-run por padrao.** Nada e removido sem `--apply`.
- **Backup automatico.** Se ja existir um `requirements.txt`, ele e copiado para `requirements.txt.bak` antes de ser sobrescrito.
- **Nao remove sem congelar.** Se o freeze falhar (venv vazio, sem metadados), o venv e preservado.
- **`pip`/`setuptools`/`wheel`** sao omitidos por padrao (nao sao dependencias de projeto).

---

## Limitacoes conhecidas

- O freeze via `dist-info` captura **todos** os pacotes instalados, incluindo dependencias transitivas. Ele nao distingue dependencia direta de indireta. Em projetos com `pyproject.toml`, a fonte de verdade das dependencias diretas continua sendo o `pyproject.toml`.
- A ferramenta em si roda em Python 3.10+. Ela processa venvs de qualquer versao, mas para rodar o `tatu` voce precisa de um interpretador 3.10+.

---

## Desenvolvimento

```bash
pip install -e ".[dev]"
pytest
```

---

## Licenca

MIT. Veja [LICENSE](LICENSE).
