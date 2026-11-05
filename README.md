# Speech-To-Text-Lab

Laboratório de **Speech-To-Text offline com Vosk**, executado em CPU, sem API paga
ou GPU. Transcreve um arquivo ou vários áudios e produz um relatório JSON para
inspeção e, posteriormente, comparação com transcrições de referência.

## Requisitos e instalação

- Python 3.12 ou 3.13 e [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Modelo Vosk extraído no computador.
- FFmpeg somente para converter áudios; `curl` e `unzip` nos comandos de download abaixo.

Na raiz do repositório:

```bash
uv sync --locked
uv run stt-lab --help
```

O `uv.lock` fixa as versões das dependências. A transcrição não acessa a rede:
somente a instalação e o download inicial do modelo precisam de internet.

## Modelo inicial: português

Sugestão: `vosk-model-small-pt-0.3`, modelo leve para português/português brasileiro,
com download de aproximadamente 31 MB e licença Apache 2.0.

Em Linux/macOS, a partir da raiz:

```bash
mkdir -p models
curl -fL https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip \
  -o models/vosk-model-small-pt-0.3.zip
unzip models/vosk-model-small-pt-0.3.zip -d models
```

Também é possível baixar e extrair manualmente pelo
[catálogo oficial](https://alphacephei.com/vosk/models). O caminho de `--model`
deve apontar para a pasta que contém `am/`, `conf/` e `graph/`, não para o ZIP.
Para outro idioma, utilize um modelo correspondente. Não há detecção automática.

O modelo pequeno é um baseline, não uma garantia de precisão. Ruído, sotaque,
microfone e vocabulário afetam bastante os resultados.

## Organizar e preparar os áudios

```text
data/
  audio/
    limpo/frase_001.wav
    ruido/frase_002.wav
  references/
    limpo/frase_001.txt
    ruido/frase_002.txt
models/
  vosk-model-small-pt-0.3/
results/
```

Adicione suas gravações em `data/audio/`. Esta versão aceita **WAV PCM mono,
16 bits, 16.000 Hz**. MP3, M4A, OGG, WAV estéreo ou outra taxa devem ser convertidos
antes, por exemplo:

```bash
ffmpeg -i gravacao.mp3 -ac 1 -ar 16000 -c:a pcm_s16le data/audio/frase_001.wav
```

Guarde os originais separadamente e não use o mesmo caminho na entrada e saída
da conversão. Não há captura de microfone nesta versão.

Modelos, áudios, referências e resultados locais são ignorados pelo Git por
padrão. Os diretórios estão preparados, mas **nenhum corpus é distribuído**.
Versione apenas exemplos pequenos e autorizados, com licença e consentimento
adequados. Não inclua gravações pessoais ou sensíveis indiscriminadamente.

## Executar Speech-To-Text

Um arquivo:

```bash
uv run stt-lab data/audio/frase_001.wav \
  --model models/vosk-model-small-pt-0.3 \
  --output results/frase_001.json
```

Todos os WAVs, incluindo subpastas, em ordem de caminho:

```bash
uv run stt-lab data/audio \
  --model models/vosk-model-small-pt-0.3 \
  --output results/lote.json
```

O modelo é carregado uma vez por execução. Cada áudio usa um reconhecedor
independente e é lido em blocos, sem carregar a gravação inteira na memória.
A saída padrão mostra o texto; o JSON contém:

- `schema_version`, motor, versão do Vosk e caminho do modelo;
- `transcripts`: caminho do áudio, texto completo, taxa de amostragem, duração
  e tempo de processamento (não inclui carregamento do modelo);
- `words`: palavra, início/fim em segundos e `conf` entre 0 e 1;
- `failures`: arquivos que falharam e respectivas mensagens.

O diretório de saída é criado automaticamente. **Um relatório já existente no
mesmo caminho será substituído**; use nomes diferentes para comparar execuções.
O relatório mantém todos os resultados em memória até a gravação final, portanto
lotes enormes devem ser divididos.

Código de saída: `0` para sucesso completo, `1` para falha em áudio ou na escrita,
`2` para argumentos inválidos, ausência de WAVs ou caminho de modelo inadequado.
Uma falha de áudio não interrompe o restante do lote. WAV vazio ou truncado é
rejeitado; silêncio válido pode produzir texto vazio e isso não significa falha
de execução. A confiança do Vosk **não equivale à precisão da transcrição**.

## Preparação da futura suíte de validação

A suíte de avaliação de qualidade ainda não está implementada. O próximo passo
é montar um corpus de referência com os mesmos caminhos relativos e nomes dos
áudios: `audio/limpo/frase_001.wav` corresponde a
`references/limpo/frase_001.txt` (UTF-8, transcrição humana revisada).

Evolução sugerida:

1. Reunir gravações com frases curtas/longas, silêncio, ruído, sotaques e vocabulário variado.
2. Definir normalização de maiúsculas, pontuação, números e acentos antes de comparar.
3. Calcular WER (erros por palavra) e CER (erros por caractere), por áudio e no corpus.
4. Definir limites de aprovação e casos separados para erros de formato e processamento.
5. Fixar corpus e versão/checksum do modelo para comparar mudanças e executar em CI.

Não trate texto reconhecido pelo próprio modelo como referência humana. O relatório
atual fornece os dados de transcrição, mas não calcula WER/CER nem decide aprovação.

## Verificações de desenvolvimento

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
uv build
```

O código fica em `src/stt_lab/`. `transcription.py` contém o reconhecimento e os
contratos de resultado; `cli.py`, a execução em lote. `typings/vosk/` descreve
apenas os métodos da API Vosk utilizados, pois o pacote não fornece esses tipos.
