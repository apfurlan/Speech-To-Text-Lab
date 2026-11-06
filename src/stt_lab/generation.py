"""Geração local do piloto de dez comandos Pix, sem executar pagamentos."""

import hashlib
import shutil
import subprocess
import wave
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, ClassVar, Final, Literal

import typer
from pydantic import BaseModel, ConfigDict, Field

from stt_lab.transcription import SAMPLE_RATE

DEFAULT_OUTPUT: Final = Path("data/generated/pix-pilot")


class Prompt(BaseModel):
    """Texto falado e valor monetário esperado, sem arredondamento de float."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")
    id: str = Field(pattern=r"^pix_[0-9]{4}$")
    text: str = Field(min_length=1)
    reference_text: str = Field(min_length=1)
    op: Literal["PIX"]
    amount_cents: int = Field(gt=0)


class Pilot(BaseModel):
    """Catálogo limitado aos dez exemplos aprováveis nesta etapa."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")
    samples: tuple[Prompt, ...] = Field(min_length=10, max_length=10)


class GeneratedSample(Prompt):
    """Artefato sintetizado e referência candidata, ainda sem revisão humana."""

    audio_path: str
    reference_path: str
    duration_seconds: float
    audio_sha256: str


class Manifest(BaseModel):
    """Proveniência do piloto e rótulos para futura avaliação semântica."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    schema_version: int = 2
    engine: Literal["piper"] = "piper"
    engine_version: str
    voice: str
    voice_sha256: str
    voice_config_sha256: str
    language: Literal["pt-BR"] = "pt-BR"
    currency: Literal["BRL"] = "BRL"
    sample_rate_hz: int = SAMPLE_RATE
    human_reviewed: Literal[False] = False
    samples: tuple[GeneratedSample, ...]


def file_sha256(path: Path) -> str:
    """Identifique o conteúdo de modelos e áudios sem carregá-los inteiros em RAM."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(
    voice: Annotated[
        Path,
        typer.Option("--voice", exists=True, dir_okay=False, help="Modelo Piper pt-BR .onnx."),
    ],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Diretório novo para os dez exemplos.")
    ] = DEFAULT_OUTPUT,
) -> None:
    """Sintetize somente os dez comandos Pix do piloto com uma voz pt-BR local."""
    if output.exists():
        message = "o diretório já existe; escolha outro destino para preservar o piloto"
        raise typer.BadParameter(message, param_hint="--output")
    config = Path(f"{voice}.json")
    if not config.is_file():
        message = f"configuração da voz ausente: {config}"
        raise typer.BadParameter(message, param_hint="--voice")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        typer.echo("Instale FFmpeg para converter os WAVs para 16000 Hz.", err=True)
        raise typer.Exit(code=1)
    try:
        from piper import PiperVoice  # noqa: PLC0415 -- Dependência opcional de geração.
    except ModuleNotFoundError as exc:
        typer.echo(f"Dependência TTS ausente ({exc}). Execute: uv sync --extra tts", err=True)
        raise typer.Exit(code=1) from exc

    pilot = Pilot.model_validate_json(files("stt_lab").joinpath("pix_pilot.json").read_text())
    try:
        piper_voice = PiperVoice.load(str(voice))
        if piper_voice.config.espeak_voice != "pt-br":
            message = "o piloto exige uma voz Piper em português brasileiro (pt-br)"
            raise typer.BadParameter(message, param_hint="--voice")
        samples: list[GeneratedSample] = []
        output.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".pix-pilot-", dir=output.parent) as temporary:
            staging = Path(temporary) / "pilot"
            (staging / "audio").mkdir(parents=True)
            (staging / "references").mkdir()
            native = Path(temporary) / "native.wav"
            for prompt in pilot.samples:
                audio_relative = f"audio/{prompt.id}.wav"
                reference_relative = f"references/{prompt.id}.txt"
                audio_path = staging / audio_relative
                with wave.open(str(native), "wb") as wav:
                    _ = piper_voice.synthesize_wav(prompt.text, wav)
                _ = subprocess.run(  # noqa: S603 -- Binário resolvido, argumentos sem shell.
                    [
                        ffmpeg,
                        "-v",
                        "error",
                        "-nostdin",
                        "-i",
                        str(native),
                        "-ac",
                        "1",
                        "-ar",
                        str(SAMPLE_RATE),
                        "-c:a",
                        "pcm_s16le",
                        str(audio_path),
                    ],
                    check=True,
                    capture_output=True,
                )
                _ = (staging / reference_relative).write_text(
                    prompt.reference_text + "\n", encoding="utf-8"
                )
                with wave.open(str(audio_path), "rb") as audio:
                    duration = audio.getnframes() / audio.getframerate()
                samples.append(
                    GeneratedSample(
                        id=prompt.id,
                        text=prompt.text,
                        reference_text=prompt.reference_text,
                        op=prompt.op,
                        amount_cents=prompt.amount_cents,
                        audio_path=audio_relative,
                        reference_path=reference_relative,
                        duration_seconds=duration,
                        audio_sha256=file_sha256(audio_path),
                    )
                )
                typer.echo(f"{prompt.id}: {prompt.text}")
            manifest = Manifest(
                engine_version=version("piper-tts"),
                voice=voice.name,
                voice_sha256=file_sha256(voice),
                voice_config_sha256=file_sha256(config),
                samples=tuple(samples),
            )
            _ = (staging / "manifest.json").write_text(
                manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
            )
            _ = staging.rename(output)
    except (OSError, ValueError, wave.Error, subprocess.CalledProcessError) as exc:
        typer.echo(f"Falha na geração do piloto: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Gerados {len(samples)} áudios e referências em {output}.")
    typer.echo("Aguardando revisão humana antes de ampliar o corpus.")


def main() -> None:
    """Execute o gerador instalado como stt-generate."""
    typer.run(run)
