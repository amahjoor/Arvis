"""
Arvis Audio Utilities

Audio recording and processing utilities for voice capture.
Includes silence detection and WAV encoding for Whisper API.
"""

import asyncio
import io
import wave
from typing import Optional
import numpy as np
from loguru import logger

from src.config import (
    SAMPLE_RATE,
    CHANNELS,
    CHUNK_SIZE,
    MAX_RECORDING_SECONDS,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    MOCK_HARDWARE,
)


async def record_until_silence(
    max_duration: float = MAX_RECORDING_SECONDS,
    silence_threshold: float = SILENCE_THRESHOLD,
    silence_duration: float = SILENCE_DURATION,
    sample_rate: int = SAMPLE_RATE,
    mock_mode: bool = MOCK_HARDWARE,
) -> tuple[bytes, float]:
    """
    Record audio until silence is detected or max duration reached.
    
    Args:
        max_duration: Maximum recording duration in seconds
        silence_threshold: Energy threshold below which is considered silence
        silence_duration: Seconds of continuous silence before stopping
        sample_rate: Audio sample rate (default 16kHz for Whisper)
        mock_mode: If True, return mock audio data
        
    Returns:
        Tuple of (wav_bytes, duration_seconds)
    """
    if mock_mode:
        return await _mock_record()
    
    return await _real_record(
        max_duration=max_duration,
        silence_threshold=silence_threshold,
        silence_duration=silence_duration,
        sample_rate=sample_rate,
    )


async def _real_record(
    max_duration: float,
    silence_threshold: float,
    silence_duration: float,
    sample_rate: int,
) -> tuple[bytes, float]:
    """Real audio recording using sounddevice."""
    import sounddevice as sd
    
    logger.info("🎙️ Recording... (speak now)")
    
    # Calculate parameters
    chunk_duration = CHUNK_SIZE / sample_rate
    max_chunks = int(max_duration / chunk_duration)
    silence_chunks_needed = int(silence_duration / chunk_duration)
    
    recorded_chunks: list[np.ndarray] = []
    silence_chunk_count = 0
    
    # Create input stream
    stream = sd.InputStream(
        samplerate=sample_rate,
        channels=CHANNELS,
        dtype=np.int16,
        blocksize=CHUNK_SIZE,
    )
    
    try:
        stream.start()
        
        for _ in range(max_chunks):
            # Read audio chunk
            audio_chunk, overflowed = stream.read(CHUNK_SIZE)
            
            if overflowed:
                logger.warning("Audio buffer overflow during recording")
            
            recorded_chunks.append(audio_chunk.copy())
            
            # Check for silence
            if is_silence(audio_chunk, silence_threshold):
                silence_chunk_count += 1
                if silence_chunk_count >= silence_chunks_needed:
                    logger.info("Silence detected, stopping recording")
                    break
            else:
                silence_chunk_count = 0
            
            # Yield to event loop
            await asyncio.sleep(0.001)
        
        else:
            logger.info(f"Max duration ({max_duration}s) reached")
        
    finally:
        stream.stop()
        stream.close()
    
    # Combine chunks and convert to WAV
    if not recorded_chunks:
        logger.warning("No audio recorded")
        return b"", 0.0
    
    audio_data = np.concatenate(recorded_chunks)
    duration = len(audio_data) / sample_rate
    
    wav_bytes = audio_to_wav(audio_data, sample_rate)
    
    logger.info(f"Recording complete: {duration:.2f}s, {len(wav_bytes)} bytes")
    
    return wav_bytes, duration


async def _mock_record() -> tuple[bytes, float]:
    """Return mock audio data for testing."""
    logger.info("🎙️ Mock recording (simulated)")
    
    # Simulate recording delay
    await asyncio.sleep(0.5)
    
    # Generate silent audio (1 second of silence)
    duration = 1.0
    samples = int(SAMPLE_RATE * duration)
    audio_data = np.zeros(samples, dtype=np.int16)
    
    wav_bytes = audio_to_wav(audio_data, SAMPLE_RATE)
    
    logger.info(f"Mock recording complete: {duration:.2f}s")
    
    return wav_bytes, duration


def is_silence(audio_chunk: np.ndarray, threshold: float = SILENCE_THRESHOLD) -> bool:
    """
    Check if an audio chunk is silence.
    
    Uses simple energy-based detection.
    
    Args:
        audio_chunk: Audio samples as numpy array
        threshold: Energy threshold (default from config)
        
    Returns:
        True if chunk is considered silence
    """
    energy = np.abs(audio_chunk).mean()
    return energy < threshold


def audio_to_wav(audio_data: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    """
    Convert numpy audio array to WAV bytes.
    
    Args:
        audio_data: Audio samples as numpy array (int16)
        sample_rate: Sample rate in Hz
        
    Returns:
        WAV file as bytes
    """
    # Ensure correct dtype
    if audio_data.dtype != np.int16:
        audio_data = audio_data.astype(np.int16)
    
    # Flatten if needed
    if len(audio_data.shape) > 1:
        audio_data = audio_data.flatten()
    
    # Write to WAV
    buffer = io.BytesIO()
    
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)  # 16-bit = 2 bytes
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    return buffer.getvalue()


def wav_to_audio(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    """
    Convert WAV bytes to numpy array.
    
    Args:
        wav_bytes: WAV file as bytes
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    buffer = io.BytesIO(wav_bytes)
    
    with wave.open(buffer, "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        audio_data = np.frombuffer(
            wav_file.readframes(wav_file.getnframes()),
            dtype=np.int16
        )
    
    return audio_data, sample_rate

