# Estado do laboratório e retomada

Registro de parada em 6 de novembro de 2026. Implementação pausada a pedido do usuário.
Base do código neste registro: commit `b301a86`, já enviado à `main`.

## Onde paramos

O laboratório gera e transcreve áudios, mas **ainda não implementa a análise completa
WAV → operação/valor/qualidade**. O formato de retorno foi discutido e aprovado,
porém não foi convertido em código. O comando `stt-analyze` não existe.

Não há implementação parcial dessa nova CLI no repositório. Os arquivos Python
atuais são `cli.py`, `transcription.py`, `generation.py` e `__init__.py`.
Não considerar mensagens de intenção de implementação como funcionalidades entregues.

## O que já funciona

- Python 3.12/3.13, dependências fixadas em `uv.lock` e instalação com `uv`.
- `stt-lab`: transcrição offline com Vosk de um WAV ou de uma pasta, com relatório JSON.
- Entrada aceita: WAV PCM mono, 16 bits, 16.000 Hz.
- Relatório de transcrição: texto, palavras com tempos/confiança, duração,
  tempo de processamento e falhas por arquivo.
- `stt-generate`: geração local de exatamente dez comandos Pix com Piper.
- Dez WAVs, dez referências TXT e manifesto versionados em `data/generated/pix-pilot/`.
- Catálogo de geração: `src/stt_lab/pix_pilot.json`.
- Catálogo e manifesto incluem `text`, `reference_text`, `op` e `amount_cents`.
- Manifesto com `schema_version: 2`, hashes dos áudios/modelo e `human_reviewed: false`.
- `text` alimenta o sintetizador; `reference_text` alimenta os TXT de referência.
- Valores esperados são inteiros em centavos: `1020` representa R$ 10,20.
- Modelos baixados, resultados locais e outros lotes gerados continuam fora do Git.
- A checagem de modelo aceita tanto `am/final.mdl` quanto `final.mdl` na raiz,
  como no modelo português pequeno.

Última alteração funcional entregue: `f0c695b` e `b301a86`, com referências explícitas
e operação esperada. Na entrega, passaram Ruff, formatação, BasedPyright, build e
verificação de leitura/serialização dos dez exemplos e hashes dos WAVs.
Isso não constitui uma suíte automatizada persistida no repositório.

## Bloqueios e ocorrências confirmadas

### O modelo Vosk atual não contém a palavra Pix

Consulta real ao modelo local `models/vosk-model-small-pt-0.3`, usando
`Model.vosk_model_find_word()`:

| Palavra | Identificador no vocabulário |
|---|---:|
| `pix` | `-1` (ausente) |
| `PIX` | `-1` (ausente) |
| `pico` | `40979` |
| `pedido` | `46869` |
| `reais` | `53733` |
| `centavos` | `31122` |

Nos pilotos, o Vosk reconheceu "pix" como "pico", "pedido" ou omitiu a palavra.
Também houve troca de "cinquenta e seis centavos" por "cinquenta e sete centavos".
Processar os dez arquivos sem falha não significa acertar suas transcrições.

Adicionar `pix` a `SetGrammar()` não cria uma palavra ausente do vocabulário.
O Vosk ignora esses tokens. Corrigir o reconhecimento exige adaptar o léxico/grafo
ou testar um modelo/motor que contenha a palavra. Nenhuma alternativa foi instalada
ou validada para resolver isso. Não substituir `pico`/`pedido` por `PIX` automaticamente.

Referências: [fonte do reconhecedor Vosk](https://github.com/alphacep/vosk-api/blob/4ab9821510b488efb7740094714a130bd3545e90/src/recognizer.cc#L343-L354)
e [adaptação de modelos](https://alphacephei.com/vosk/adaptation).

### Ocorrências das ferramentas, diferentes de falhas da aplicação

- Houve chamadas da ferramenta de edição abortadas, sem alterações no código.
  A implementação da análise foi anunciada, mas não chegou a ser escrita.
- O daemon LSP não estava acessível. A checagem de tipos foi executada diretamente
  com BasedPyright nas alterações efetivamente entregues.
- Esses problemas não explicam a troca de Pix por pico; a ausência no vocabulário
  foi confirmada independentemente por execução real do Vosk.

## Contrato de retorno acordado, ainda não implementado

Exemplo ilustrativo, não saída de uma execução nem medições reais:

```json
{
  "val": "10.20",
  "amount_cents": 1020,
  "currency": "BRL",
  "op": "PIX",
  "status": "needs_confirmation",
  "quality": {
    "estimation_status": "uncalibrated",
    "probability_amount_correct": null,
    "warnings": []
  },
  "metrics": {
    "performance": {
      "transcription_seconds": null,
      "total_seconds": null
    }
  }
}
```

- `amount_cents` será a fonte de verdade; `val` será uma string decimal derivada.
- Não usar float intermediário para converter fala em centavos.
- Operação ou valor inconclusivos devem permitir `null`, nunca um resultado inventado.
- Resultados precisam de confirmação antes de qualquer uso financeiro.
- Sem referência, não há WER/CER/SER, Accuracy, MER, WIL/WIP ou erro de entidades
  medidos para uma nova fala. Essas métricas pertencem à avaliação offline.
- Confiança por palavra do Vosk é evidência bruta, não probabilidade calibrada de acerto.
- Captura de microfone e integração com o aparelho ainda não existem; a entrada atual é WAV.
- O laboratório não executa pagamentos e não se conecta a serviços bancários.

## Próximos passos

1. **Retomar pela extração e contrato JSON, sem depender de corrigir todo o ASR.**
   Pode-se manter o Vosk inicialmente, sinalizando que o modelo não suporta Pix
   e retornando `op: null` quando a operação não for reconhecida.
2. **Implementar extração monetária conservadora.** Suportar reais/centavos por
   extenso e definir a política para abreviações, números, negação, correção na fala
   e múltiplos valores. "Dez e vinte" e "trinta com quarenta" têm valores anotados
   no corpus, mas isso não elimina a ambiguidade em produção. Política de produção
   ainda precisa ser implementada e documentada, sem copiar rótulos do catálogo.
3. **Implementar análise sem referência.** Retornar qualidade não calibrada,
   avisos e tempos reais de carregamento, transcrição, extração e processamento total.
   Qualidade de captura, silêncio/saturação e confirmação também precisam de regras.
4. **Criar `stt-analyze`.** Aceitar WAV, modelo e saída opcional; manter JSON em
   stdout separado de mensagens de diagnóstico e tratar entradas inválidas.
5. **Validar ponta a ponta.** Usar os dez pilotos, silêncio, WAV inválido,
   operação ausente, valores ausentes/ambíguos e frases negativas/corrigidas.
   Preservar os WAVs existentes e testar o extrator também com textos controlados,
   para distinguir defeitos de interpretação dos erros do reconhecedor.
6. **Resolver reconhecimento de Pix.** Comparar um segundo modelo/motor nos mesmos
   áudios ou adaptar o Vosk. Não prometer que um modelo alternativo resolve o problema
   antes de testá-lo. CPU, RAM, sistema operacional e requisito offline do aparelho
   ainda não foram informados; são necessários para decidir a implantação embarcada,
   mas não impedem implementar a CLI local com resultados inconclusivos explícitos.
7. **Implementar avaliação offline separada.** Calcular WER, CER, SER, `1 - WER`,
   MER, WIL/WIP, WER normalizado e métricas de entidades/palavras-chave usando
   referências revisadas. Nunca usar esses rótulos para produzir a previsão.
8. **Calibrar com gravações reais do dispositivo.** Os dez sintéticos não bastam
   para estimar probabilidades de acerto em clientes. Só ampliar para 100 e 1.000
   após revisar o piloto e as regras do fluxo básico.

## Como testar o que já existe

Na raiz do repositório, com o modelo português já baixado conforme o README:

```bash
uv sync --locked
uv run stt-lab data/generated/pix-pilot/audio/pix_0001.wav \
  --model models/vosk-model-small-pt-0.3 \
  --output results/teste-pix.json
```

Para transcrever os dez arquivos, substituir o caminho do WAV pela pasta
`data/generated/pix-pilot/audio`. O comando retorna transcrição e metadados,
**não** o contrato de análise acima. Não executar `stt-analyze`: ainda não existe.

As referências estão nos TXT e no `manifest.json`; os áudios podem ser ouvidos
diretamente, sem instalar Piper. Não regenerar o piloto para retomar o desenvolvimento.

## Critérios para considerar o fluxo completo

- Um WAV novo produz o contrato JSON sem depender de referência ou manifesto.
- Valor/operação ausentes ou ambíguos não são substituídos por dados do corpus.
- Os tempos são medidos, não exemplos fixos, e a incerteza é explícita.
- A ausência de Pix no vocabulário é sinalizada, não disfarçada por substituições.
- O fluxo foi executado pela CLI com os dez pilotos e entradas inválidas.
- Verificações estáticas e testes pertinentes aprovados, com limitações documentadas.
- Alterações implementadas são revisadas, commitadas e enviadas quando autorizadas.
