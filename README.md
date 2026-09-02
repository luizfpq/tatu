<p align="center">
  <img src="https://img.icons8.com/pulsar-color/96/pangolin.png" width="96" height="96" alt="tatu">
</p>

# tatu

> Acha ambientes virtuais Python espalhados pelo computador, salva a lista de dependencias de cada projeto e apaga os ambientes para liberar espaco em disco.

O tatu e um bicho que cava tocas organizadas, com espaco separado para cada coisa. A ferramenta faz isso com suas pastas: procura os ambientes virtuais (os venvs), anota o que cada projeto precisa num `requirements.txt` e remove os venvs, que sao facilmente recriaveis depois.

---

## O problema que ele resolve

Todo projeto Python costuma ter um ambiente virtual: uma pasta (`venv`, `.venv`, `env`) que guarda as bibliotecas daquele projeto. Essa pasta e grande, cheia de arquivos, e nao precisa ser guardada nem versionada. O que importa mesmo e a lista de dependencias, porque com ela voce recria o ambiente em segundos.

Na pratica esses venvs vao se acumulando pelo disco. E as coisas pioram quando um projeto acaba dentro de uma pasta sincronizada. Guardar codigo em pasta de sincronizacao ja e uma pratica ruim por si so, mas quando isso acontece o estrago aumenta: o venv inteiro sobe para a nuvem sem necessidade, ocupa gigabytes e costuma chegar quebrado do outro lado.

Apagar na mao funciona, mas e arriscado: se voce nao anotou as versoes exatas do que estava instalado, perde essa informacao. O tatu resolve os dois lados. Antes de apagar qualquer venv, ele grava o `requirements.txt` daquele projeto. Se um dia precisar do ambiente de volta, basta um `pip install -r requirements.txt`.

---

## Instalacao

Precisa de Python 3.10 ou mais novo para rodar a ferramenta. Ela consegue processar venvs de qualquer versao do Python, essa exigencia e so para o proprio tatu.

Instale direto do repositorio:

```bash
pip install "git+https://github.com/luizfpq/tatu.git"
```

Ou clonando o codigo primeiro:

```bash
git clone https://github.com/luizfpq/tatu.git
cd tatu
pip install .
```

Nao instala nada alem de si mesmo: usa somente a biblioteca padrao do Python.

> Observacao: ainda nao esta publicado no PyPI, entao `pip install tatu` (sem o endereco do repositorio) nao funciona. Use uma das formas acima.

---

## Como usar

Uma regra de ouro: por padrao o tatu nao apaga nada. Ele so mostra o que faria. Isso se chama dry-run. Voce olha o resultado, confere se esta tudo certo, e so entao roda de novo com `--apply` para valer.

```bash
# olha a pasta atual e mostra o que faria (nao apaga nada)
tatu

# olha varias pastas
tatu ~/Documentos ~/projetos

# manda ver: gera os requirements.txt e apaga os venvs
tatu ~/Documentos --apply

# pergunta antes de cada venv, um por um
tatu ~/Documentos --apply --interactive

# so gera os requirements, sem apagar os venvs
tatu ~/Documentos --apply --no-remove

# ignora alguma pasta que voce nao quer tocar
tatu ~ --ignore .venvs --ignore backups

# usa um atalho de busca mais rapido, se disponivel
tatu ~ --locate
```

Um fluxo tranquilo para a primeira vez:

1. Rode `tatu ~/seus-projetos` e leia a lista.
2. Confira o total de espaco que seria liberado.
3. Se estiver de acordo, rode `tatu ~/seus-projetos --apply`.
4. Na duvida sobre algum venv, use `--interactive` para decidir caso a caso.

### Todas as opcoes

| Opcao | O que faz |
|-------|-----------|
| `--apply` | Executa de verdade. Sem ela, so simula (dry-run) |
| `-i`, `--interactive` | Pergunta antes de mexer em cada venv |
| `--no-remove` | So gera o requirements, mantem o venv |
| `--no-requirements` | So apaga o venv, sem gerar requirements |
| `--no-backup` | Nao guarda copia `.bak` de um requirements que ja exista |
| `--include-base` | Inclui `pip`, `setuptools` e `wheel` na lista |
| `--requirements-name NOME` | Muda o nome do arquivo de saida (padrao `requirements.txt`) |
| `--ignore DIR` | Ignora uma pasta pelo nome (pode repetir a opcao) |
| `--locate` | Usa o indice do `locate` para achar os venvs mais rapido |

---

## O que o tatu faz por baixo dos panos

Se voce so quer usar, o de cima ja basta. Esta secao e para quem gosta de saber como as coisas funcionam.

### Como ele reconhece um venv

Todo venv tem um arquivo chamado `pyvenv.cfg` na raiz. O tatu procura por esse arquivo, nao pelo nome da pasta. Por isso encontra `venv`, `.venv`, `env` ou qualquer outro nome que voce tenha usado. Ele tambem nao entra dentro de um venv ja encontrado, para nao se confundir com bibliotecas que trazem venvs de exemplo.

### Como ele anota as dependencias

Para montar o `requirements.txt`, o tatu tenta dois caminhos, nessa ordem:

1. Roda o `pip freeze` de dentro do proprio venv, que e a forma tradicional.
2. Se isso falhar, ele le os metadados das bibliotecas direto do disco (as pastas `*.dist-info` e `*.egg-info`) e reconstroi a lista.

O segundo caminho e o que faz diferenca de verdade. Venvs que passaram por sincronizacao costumam chegar quebrados: o atalho para o Python aponta para um lugar que nao existe naquela maquina, ou o proprio `pip` sumiu. Mesmo assim, os registros das bibliotecas continuam no disco. O tatu aproveita isso e consegue gerar o `requirements.txt` de um venv que nem liga mais.

### Achar os venvs: busca normal ou atalho

Por padrao o tatu percorre as pastas uma a uma. E confiavel e sempre reflete o estado atual do disco.

Com `--locate`, ele tenta usar o `locate`, uma ferramenta do sistema que mantem um indice pronto de arquivos e responde quase na hora. Como esse indice pode estar velho, o tatu toma alguns cuidados:

- confere se cada `pyvenv.cfg` ainda existe de fato, para nao tentar apagar venvs que ja sairam;
- considera apenas os que estao dentro das pastas que voce pediu;
- volta sozinho para a busca normal quando o indice nao cobre as pastas de interesse (comum quando o indice nao inclui a sua pasta pessoal);
- avisa a idade do indice e, se o `locate` nem estiver instalado, explica como instalar e segue com a busca normal sem instalar nada por conta propria.

### O registro da versao do Python

O tatu le no `pyvenv.cfg` qual versao do Python o venv usava e anota isso como comentario no topo do `requirements.txt`. Assim, no dia de recriar o ambiente, voce sabe com qual versao ele foi feito:

```
# gerado por tatu (metodo: dist-info)
# python do venv original: 3.11.5
flask==3.0.0
requests==2.31.0
```

### Por que da para confiar

O tatu foi feito para nao te dar sustos:

- Nao apaga nada sem `--apply`. O padrao e so mostrar.
- Se ja houver um `requirements.txt`, ele salva uma copia em `requirements.txt.bak` antes de sobrescrever. Voce nao perde um arquivo que tenha ajustado a mao.
- Nunca apaga um venv sem antes conseguir anotar as dependencias. Se o freeze falhar (venv vazio, por exemplo), o venv fica onde esta.
- Deixa `pip`, `setuptools` e `wheel` de fora da lista por padrao, porque nao sao dependencias do seu projeto.

---

## Limitacoes que vale conhecer

- Quando o tatu precisa ler os metadados do disco (o segundo caminho de freeze), ele lista todas as bibliotecas instaladas, inclusive as que vieram de brinde junto com outras. Ele nao separa o que voce pediu do que foi arrastado como dependencia. Em projetos que usam `pyproject.toml`, a lista oficial do que o projeto precisa continua sendo o `pyproject.toml`.
- A ferramenta roda em Python 3.10 ou mais novo. Ela cuida de venvs de qualquer versao, mas para executar o `tatu` voce precisa de um Python 3.10+.

---

## Para desenvolver

```bash
pip install -e ".[dev]"
pytest
```

---

## Licenca

MIT. Veja o arquivo [LICENSE](LICENSE).
