"""Interface de linha de comando para transcrição individual ou em lote."""

import wave
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Final

import typer
from pydantic import ValidationError
from vosk import Model

from stt_lab.transcription import (
    AudioFormatError,
    Failure,
    Report,
    Transcript,
    transcribe,
)

DEFAULT_OUTPUT: Final = Path("results/transcriptions.json")


def run(
    source: Annotated[
        Path,
        typer.Argument(exists=True, readable=True, help="Arquivo WAV ou pasta de WAVs."),
    ],
    model: Annotated[
        Path,
        typer.Option(
            "--model", exists=True, file_okay=False, help="Pasta do modelo Vosk extraído."
        ),
    ],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Relatório JSON (substitui se existir).")
    ] = DEFAULT_OUTPUT,
) -> None:
    """Transcreva um WAV ou todos os WAVs de uma pasta, recursivamente, offline."""
    if output.suffix.lower() != ".json":
        message = "a saída deve ter extensão .json"
        raise typer.BadParameter(message, param_hint="--output")
    if not any(path.is_file() for path in (model / "am" / "final.mdl", model / "final.mdl")):
        message = "selecione a pasta extraída que contém am/final.mdl ou final.mdl"
        raise typer.BadParameter(message, param_hint="--model")
    if source.is_file():
        files = [source] if source.suffix.lower() == ".wav" else []
    else:
        files = sorted(
            path for path in source.rglob("*") if path.is_file() and path.suffix.lower() == ".wav"
        )
    if not files:
        message = "nenhum arquivo WAV encontrado"
        raise typer.BadParameter(message, param_hint="SOURCE")

    # Um modelo por execução; um reconhecedor novo por arquivo.
    vosk_model = Model(str(model.resolve()))
    transcripts: list[Transcript] = []
    failures: list[Failure] = []
    for path in files:
        try:
            transcript = transcribe(path, vosk_model)
        except (AudioFormatError, OSError, wave.Error, EOFError, ValidationError) as exc:
            failures.append(Failure(audio_path=str(path), error=str(exc)))
            typer.echo(f"ERRO {path}: {exc}", err=True)
        else:
            transcripts.append(transcript)
            typer.echo(f"OK {path}: {transcript.text}")

    report = Report(
        engine_version=version("vosk"),
        model_path=str(model.resolve()),
        transcripts=tuple(transcripts),
        failures=tuple(failures),
    )
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        _ = output.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        typer.echo(f"Erro ao salvar {output}: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"{len(transcripts)} sucesso(s), {len(failures)} falha(s). Relatório: {output}")
    if failures:
        raise typer.Exit(code=1)


def main() -> None:
    """Execute a CLI instalada como stt-lab."""
    typer.run(run)
