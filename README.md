# Speech-To-Text-Lab

Laboratório de **Speech-To-Text offline com Vosk**, executado em CPU, sem API paga
ou GPU. Transcreve um arquivo ou vários áudios e produz um relatório JSON para
inspeção e, posteriormente, comparação com transcrições de referência.

## Requisitos e instalação

- Python 3.12 ou 3.13 e [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Modelo Vosk extraído no computador.
- FFmpeg para converter áudios e gerar o piloto; `curl` e `unzip` nos downloads abaixo.

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
deve apontar para a pasta extraída, não para o ZIP. São aceitos modelos com
`am/final.mdl` e modelos com `final.mdl` diretamente na raiz, como o pequeno português.
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
padrão, com uma exceção: os dez WAVs do piloto Pix, seus TXT e manifesto estão
versionados em `data/generated/pix-pilot/`. Nenhuma gravação humana é distribuída.
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

## Piloto: dez áudios de comandos Pix

O catálogo versionado em `src/stt_lab/pix_pilot.json` contém **exatamente dez frases**.
Não há geração automática de 100 ou 1.000 nesta etapa. Primeiro, ouça os dez arquivos
e confira a pronúncia de "pix", dos valores e das expressões abreviadas.
O laboratório não faz transferências nem se conecta a serviços bancários.

Os dez áudios já estão incluídos no repositório: basta abrir os WAVs em um player.
Não é necessário instalar Piper ou baixar a voz para ouvi-los. Modelos, resultados
de transcrição e outros lotes gerados continuam ignorados pelo Git.

Os três primeiros exemplos são:

| Arquivo | Texto falado | Valor esperado |
|---|---|---|
| `pix_0001.wav` | Faça um pix no valor de dez reais e vinte centavos. | R$ 10,20 |
| `pix_0002.wav` | Pix no valor de dez e vinte. | R$ 10,20 |
| `pix_0003.wav` | Fazer um pix no valor de trinta com quarenta. | R$ 30,40 |

Os demais incluem R$ 1,00, R$ 1,01, R$ 10,05, R$ 50,00, R$ 100,99, R$ 0,99 e
R$ 1.234,56. Valores são escritos por extenso na entrada TTS. O rótulo `amount_cents`
usa inteiros: `1020` representa R$ 10,20, sem problemas de ponto flutuante.
Nos dois exemplos abreviados, a interpretação é uma convenção do corpus, não uma
garantia de que um comando real seja inequívoco. A extração de valores ainda não existe.

### Instalar sintetizador e voz

O gerador usa [Piper](https://github.com/OHF-Voice/piper1-gpl) local, em CPU,
com a voz brasileira `pt_BR-cadu-medium`. Instale a dependência opcional e baixe
o ONNX com a configuração correspondente:

```bash
uv sync --locked --extra tts
uv run --extra tts python -m piper.download_voices pt_BR-cadu-medium --data-dir models
```

Instale FFmpeg pelo gerenciador do sistema, caso necessário. A voz gera nativamente
22.050 Hz; o gerador converte para WAV PCM mono, 16 bits, 16.000 Hz, aceito pelo Vosk.
Depois dos downloads, a síntese e a transcrição funcionam offline.

O motor Piper atual é GPL-3.0. O [model card da voz](https://huggingface.co/rhasspy/piper-voices/blob/main/pt/pt_BR/cadu/medium/MODEL_CARD)
informa CC0 para o dataset de treinamento, mas não especifica uma licença separada
para os pesos. Confira os termos da voz antes de redistribuir modelo ou corpus;
a licença do motor não deve ser confundida com a do modelo ou dos áudios produzidos.

### Gerar novamente e inspecionar

Para produzir uma nova síntese sem sobrescrever o piloto versionado:

```bash
uv run --extra tts stt-generate --voice models/pt_BR-cadu-medium.onnx \
  --output data/generated/pix-pilot-v2
```

Piloto incluído no Git (a nova síntese acima fica em `pix-pilot-v2/`, ignorada):

```text
data/generated/pix-pilot/
  audio/pix_0001.wav ... pix_0010.wav
  references/pix_0001.txt ... pix_0010.txt
  manifest.json
```

Cada TXT contém o texto enviado ao sintetizador, ainda sujeito a revisão auditiva.
O manifesto inclui valores esperados, versão do motor, hashes SHA-256 da voz,
configuração e WAVs, duração e caminhos relativos à raiz do piloto.
`human_reviewed: false` registra que a síntese não é uma referência humana validada.

O comando recusa um destino existente. Para preservar o primeiro lote ao gerar outro,
use `--output data/generated/pix-pilot-v2`. A saída final só é publicada depois de
todos os exemplos serem gerados; arquivos temporários são removidos se houver falha.
O conteúdo do catálogo é fixo, mas a síntese do Piper pode variar entre execuções:
não há promessa de WAVs idênticos bit a bit. Preserve o lote e seus hashes para avaliação.

Transcreva o piloto com o modelo português baixado anteriormente:

```bash
uv run stt-lab data/generated/pix-pilot/audio \
  --model models/vosk-model-small-pt-0.3 \
  --output results/pix-pilot.json
```

Compare o resultado com os TXT e com `amount_cents`, sem substituir as referências
pelo texto do Vosk. Os dez exemplos usam uma única voz limpa: não representam a
diversidade de usuários reais nem estabelecem uma meta de precisão.
Só após a revisão deste piloto serão preparados os lotes de 100 e, depois, 1.000.

## Verificações de desenvolvimento

```bash
uv run ruff check .
uv run ruff format --check .
uv run --extra tts basedpyright
uv build
```

O código fica em `src/stt_lab/`. `transcription.py` contém o reconhecimento e os
contratos de resultado; `cli.py`, a execução em lote. `typings/vosk/` descreve
apenas os métodos da API Vosk utilizados, pois o pacote não fornece esses tipos.
