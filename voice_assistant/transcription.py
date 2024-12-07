# voice_assistant/transcription.py

import os
import traceback
import json
import logging
import requests
import time

from colorama import Fore, init
from openai import OpenAI
from groq import Groq
from deepgram import DeepgramClient,PrerecordedOptions,FileSource

fast_url = "http://localhost:8000"
checked_fastwhisperapi = False

def check_fastwhisperapi():
    """Check if the FastWhisper API is running."""
    global checked_fastwhisperapi, fast_url
    if not checked_fastwhisperapi:
        infopoint = f"{fast_url}/info"
        try:
            response = requests.get(infopoint)
            if response.status_code != 200:
                raise Exception("FastWhisperAPI is not running")
        except Exception:
            raise Exception("FastWhisperAPI is not running")
        checked_fastwhisperapi = True

def transcribe_audio(model, api_key, audio_file_path, local_model_path=None):
    """
    Transcribe an audio file using the specified model.
    
    Args:
        model (str): The model to use for transcription ('openai', 'groq', 'deepgram', 'fastwhisper', 'local').
        api_key (str): The API key for the transcription service.
        audio_file_path (str): The path to the audio file to transcribe.
        local_model_path (str): The path to the local model (if applicable).

    Returns:
        str: The transcribed text.
    """
    try:
        if model == 'openai':
            return _transcribe_with_openai(api_key, audio_file_path)
        elif model == 'groq':
            return _transcribe_with_groq(api_key, audio_file_path)
        elif model == 'deepgram':
            return _transcribe_with_deepgram(api_key, audio_file_path)
        elif model == 'gemini':
            return _transcribe_with_gemini(api_key,audio_file_path)
        elif model == 'fastwhisperapi':
            return _transcribe_with_fastwhisperapi(audio_file_path)
        elif model == 'local':
            # Placeholder for local STT model transcription
            return "Transcribed text from local model"
        else:
            raise ValueError("Unsupported transcription model")
    except Exception as e:
        logging.error(f"{Fore.RED}Failed to transcribe audio: {e}{Fore.RESET}")
        traceback.print_exc()
        raise Exception("Error in transcribing audio")

def _transcribe_with_openai(api_key, audio_file_path):
    client = OpenAI(api_key=api_key)
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language='en'
        )
    return transcription.text


def _transcribe_with_groq(api_key, audio_file_path):
    client = Groq(api_key=api_key)
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_file,
            # language='en'
            language='ta'
        )
    return transcription.text


def _transcribe_with_deepgram(api_key, audio_file_path):
    deepgram = DeepgramClient(api_key)
    try:
        with open(audio_file_path, "rb") as file:
            buffer_data = file.read()

        payload = {"buffer": buffer_data}
        options = PrerecordedOptions(model="nova-2", smart_format=True)
        response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
        data = json.loads(response.to_json())

        transcript = data['results']['channels'][0]['alternatives'][0]['transcript']
        return transcript
    except Exception as e:
        logging.error(f"{Fore.RED}Deepgram transcription error: {e}{Fore.RESET}")
        raise


def _transcribe_with_fastwhisperapi(audio_file_path):
    check_fastwhisperapi()
    endpoint = f"{fast_url}/v1/transcriptions"

    files = {'file': (audio_file_path, open(audio_file_path, 'rb'))}
    data = {
        'model': "base",
        'language': "en",
        'initial_prompt': None,
        'vad_filter': True,
    }
    headers = {'Authorization': 'Bearer dummy_api_key'}

    response = requests.post(endpoint, files=files, data=data, headers=headers)
    response_json = response.json()
    return response_json.get('text', 'No text found in the response.')


from pathlib import Path
import base64
import litellm


def _transcribe_with_gemini(api_key,audio_file_path):    
    model = os.environ["GEMINI_MODEL"]
    audio_bytes = Path(audio_file_path).read_bytes()
    encoded_data = base64.b64encode(audio_bytes).decode("utf-8")

    response = litellm.completion(
        model=model,
        api_key=api_key,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Just transcribe the Tamil audio. If no audio is detected, just say '<empty>'."},
                    {
                        "type": "image_url",
                        "image_url": "data:audio/mp3;base64,{}".format(encoded_data), # 👈 SET MIME_TYPE + DATA
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    os.environ["GEMINI_MODEL"] = "gemini/gemini-1.5-flash-002"
    # print(_transcribe_with_gemini(os.environ["GEMINI_API_KEY"],"test_cropped.mp3"))
    print(_transcribe_with_groq(os.environ["GROQ_API_KEY"],"test_cropped.mp3"))
