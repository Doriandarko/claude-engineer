import pyaudio
import wave
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def record_audio(duration=5, sample_rate=44100, chunk=1024, channels=1):
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk,
    )

    print("Recording...")
    frames = []

    for _ in range(0, int(sample_rate / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)

    print("Recording finished.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    return b"".join(frames)


def save_audio(audio_data, filename="input.wav", sample_rate=44100, channels=1):
    wf = wave.open(filename, "wb")
    wf.setnchannels(channels)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(audio_data)
    wf.close()


def transcribe_audio(audio_file):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    client = OpenAI(api_key=api_key)

    try:
        with open(audio_file, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
        return transcript.text
    except Exception as e:
        raise Exception(f"Transcription failed: {str(e)}")


def get_voice_input():
    audio_data = record_audio()
    save_audio(audio_data)
    transcription = transcribe_audio("input.wav")
    return transcription


if __name__ == "__main__":
    # Test the voice input functionality
    user_input = get_voice_input()
    print(f"Transcribed text: {user_input}")
