"""Transcrição em streaming e contratos dos resultados do laboratório."""

import wave
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import ClassVar, Final, override

from pydantic import BaseModel, ConfigDict, Field
from vosk import KaldiRecognizer, Model

SAMPLE_RATE: Final = 16000
SAMPLE_WIDTH: Final = 2
CHUNK_FRAMES: Final = 4000


@dataclass(frozen=True, slots=True)
class AudioFormatError(Exception):
    """Áudio fora do contrato de entrada."""

    path: Path
    reason: str

    @override
    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


class Word(BaseModel):
    """Palavra reconhecida com tempos em segundos e confiança do modelo."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    word: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    conf: float = Field(ge=0, le=1)


class Segment(BaseModel):
    """Resposta final de um segmento emitido pelo Vosk."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    text: str
    result: tuple[Word, ...] = ()


class Transcript(BaseModel):
    """Resultado de um arquivo, com metadados para futura avaliação."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    audio_path: str
    sample_rate_hz: int
    duration_seconds: float
    processing_seconds: float
    text: str
    words: tuple[Word, ...]


class Failure(BaseModel):
    """Falha de um arquivo sem impedir o restante do lote."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    audio_path: str
    error: str


class Report(BaseModel):
    """Relatório versionado de uma execução de transcrição."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    schema_version: int = 1
    engine: str = "vosk"
    engine_version: str
    model_path: str
    transcripts: tuple[Transcript, ...]
    failures: tuple[Failure, ...]


def transcribe(path: Path, model: Model) -> Transcript:
    """Transcreva WAV PCM mono 16-bit/16 kHz sem carregar todo o áudio em RAM.

    Raises:
        AudioFormatError: Se o WAV estiver vazio, truncado ou fora do formato.
        OSError: Se o arquivo não puder ser lido.
        wave.Error: Se o arquivo não for um WAV válido.
    """
    started = perf_counter()
    segments: list[Segment] = []
    with wave.open(str(path), "rb") as audio:
        if (
            audio.getnchannels() != 1
            or audio.getsampwidth() != SAMPLE_WIDTH
            or audio.getframerate() != SAMPLE_RATE
            or audio.getcomptype() != "NONE"
        ):
            raise AudioFormatError(path, "use WAV PCM mono, 16 bits, 16000 Hz")
        frame_count = audio.getnframes()
        if frame_count == 0:
            raise AudioFormatError(path, "WAV sem amostras")
        recognizer = KaldiRecognizer(model, SAMPLE_RATE)
        recognizer.SetWords(True)  # noqa: FBT003 -- API externa.
        bytes_read = 0
        while chunk := audio.readframes(CHUNK_FRAMES):
            bytes_read += len(chunk)
            if recognizer.AcceptWaveform(chunk):
                segments.append(Segment.model_validate_json(recognizer.Result()))
        if bytes_read != frame_count * SAMPLE_WIDTH:
            raise AudioFormatError(path, "WAV truncado: faltam amostras")
        segments.append(Segment.model_validate_json(recognizer.FinalResult()))
    return Transcript(
        audio_path=str(path),
        sample_rate_hz=SAMPLE_RATE,
        duration_seconds=frame_count / SAMPLE_RATE,
        processing_seconds=perf_counter() - started,
        text=" ".join(segment.text for segment in segments if segment.text),
        words=tuple(word for segment in segments for word in segment.result),
    )
