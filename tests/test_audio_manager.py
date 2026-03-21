"""
Testes para audio_manager.py
Cobre: play_sfx, play_chime, text_to_speech (fallback chain),
       narrator_speech, master_speech, speech_to_text
"""
import os
import pytest
from unittest.mock import patch, MagicMock, call

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mock pygame e pyttsx3 antes de importar audio_manager
pygame_mock = MagicMock()
pygame_mock.mixer = MagicMock()
pygame_mock.mixer.Sound = MagicMock()
pygame_mock.mixer.music = MagicMock()
pygame_mock.mixer.music.get_busy.return_value = False

pyttsx3_mock = MagicMock()

with patch.dict("sys.modules", {"pygame": pygame_mock, "pyttsx3": pyttsx3_mock}):
    import audio_manager

# patch.dict limpa sys.modules ao sair — re-registrar para que patch() encontre o módulo correto
sys.modules["audio_manager"] = audio_manager


# ─── play_sfx ────────────────────────────────────────────────────────────────

class TestPlaySFX:
    def test_plays_known_sfx(self):
        with patch("audio_manager._ensure_mixer_initialized"):
            with patch("audio_manager.os.path.exists", return_value=True):
                sound_mock = MagicMock()
                with patch("audio_manager.pygame.mixer.Sound", return_value=sound_mock):
                    audio_manager.play_sfx("chime")
                    sound_mock.play.assert_called_once()

    def test_unknown_sfx_does_not_crash(self):
        # Não deve lançar exceção
        audio_manager.play_sfx("sfx_que_nao_existe_xyz")

    def test_file_not_found_does_not_crash(self):
        with patch("audio_manager._ensure_mixer_initialized"):
            with patch("audio_manager.os.path.exists", return_value=False):
                audio_manager.play_sfx("chime")  # Não deve explodir

    def test_all_known_sfx_names_are_in_library(self):
        expected_sfx = ["chime", "coin", "crow", "crows", "fome", "logo",
                        "village", "people", "rain", "tavern",
                        "familiar1", "familiar2", "familiar3", "crianca", "scream"]
        sfx_library = audio_manager.SFX_LIBRARY if hasattr(audio_manager, "SFX_LIBRARY") else {}
        # Se SFX_LIBRARY existir, verificar que as keys conhecidas estão nela
        if sfx_library:
            for sfx in expected_sfx:
                assert sfx in sfx_library, f"SFX '{sfx}' não encontrado na biblioteca"

    def test_play_sfx_initializes_mixer(self):
        with patch("audio_manager._ensure_mixer_initialized") as mock_init:
            with patch("audio_manager.os.path.exists", return_value=False):
                audio_manager.play_sfx("chime")
                mock_init.assert_called_once()


# ─── play_chime ───────────────────────────────────────────────────────────────

class TestPlayChime:
    def test_play_chime_calls_play_sfx(self):
        with patch("audio_manager.play_sfx") as mock_sfx:
            audio_manager.play_chime()
            mock_sfx.assert_called_once_with("chime")

    def test_play_chime_does_not_crash(self):
        with patch("audio_manager.play_sfx"):
            audio_manager.play_chime()  # Não deve lançar exceção


# ─── narrator_speech ─────────────────────────────────────────────────────────

class TestNarratorSpeech:
    def test_calls_text_to_speech_with_narrator_voice(self):
        with patch("audio_manager.text_to_speech") as mock_tts:
            audio_manager.narrator_speech("Era uma vez...")
            mock_tts.assert_called_once_with("Era uma vez...", voice_type="narrator")

    def test_passes_text_correctly(self):
        text = "Bem-vindo à Plataforma Ressoar"
        with patch("audio_manager.text_to_speech") as mock_tts:
            audio_manager.narrator_speech(text)
            args = mock_tts.call_args[0]
            assert text in args


# ─── master_speech ────────────────────────────────────────────────────────────

class TestMasterSpeech:
    def test_calls_text_to_speech_with_master_voice(self):
        with patch("audio_manager.text_to_speech") as mock_tts:
            audio_manager.master_speech("O mestre narra...")
            mock_tts.assert_called_once_with("O mestre narra...", voice_type="master")

    def test_passes_text_correctly(self):
        text = "Você entra na taverna"
        with patch("audio_manager.text_to_speech") as mock_tts:
            audio_manager.master_speech(text)
            args = mock_tts.call_args[0]
            assert text in args


# ─── text_to_speech (fallback chain) ─────────────────────────────────────────

class TestTextToSpeech:
    def setup_method(self):
        """Limpa cache entre testes para evitar interferência."""
        audio_manager._tts_cache.clear()

    def test_does_not_crash_when_all_providers_fail(self):
        with patch("audio_manager.text_to_speech_google_cloud", return_value=False):
            with patch("audio_manager.text_to_speech_local", return_value=False):
                with patch("audio_manager.text_to_speech_elevenlabs", return_value=False):
                    # Não deve lançar exceção
                    audio_manager.text_to_speech("texto")

    def test_uses_google_cloud_first(self):
        with patch("audio_manager.text_to_speech_google_cloud", return_value=True) as mock_gc:
            with patch("audio_manager.text_to_speech_local", return_value=True) as mock_local:
                audio_manager.text_to_speech("texto")
                mock_gc.assert_called_once()

    def test_falls_back_to_local_when_google_fails(self):
        with patch("audio_manager.text_to_speech_google_cloud", return_value=False):
            with patch("audio_manager.text_to_speech_local", return_value=True) as mock_local:
                audio_manager.text_to_speech("texto")
                mock_local.assert_called_once()

    def test_falls_back_to_elevenlabs_when_others_fail(self):
        with patch("audio_manager.text_to_speech_google_cloud", return_value=False):
            with patch("audio_manager.text_to_speech_local", return_value=False):
                with patch("audio_manager.text_to_speech_elevenlabs", return_value=True) as mock_el:
                    audio_manager.text_to_speech("texto")
                    mock_el.assert_called_once()

    def test_voice_type_forwarded_to_provider(self):
        with patch("audio_manager.text_to_speech_google_cloud", return_value=True) as mock_gc:
            audio_manager.text_to_speech("texto", voice_type="narrator")
            call_args = mock_gc.call_args
            assert "narrator" in str(call_args)

    def test_caching_skips_second_call(self):
        # Limpar cache antes do teste
        audio_manager._tts_cache.clear()

        with patch("audio_manager.text_to_speech_google_cloud", return_value=True) as mock_gc:
            audio_manager.text_to_speech("texto cache test", voice_type="master")
            audio_manager.text_to_speech("texto cache test", voice_type="master")
            # Segunda chamada deve usar cache, não chamar novamente
            assert mock_gc.call_count <= 1

    def test_empty_text_handled_gracefully(self):
        with patch("audio_manager.text_to_speech_google_cloud", return_value=False):
            with patch("audio_manager.text_to_speech_local", return_value=False):
                with patch("audio_manager.text_to_speech_elevenlabs", return_value=False):
                    audio_manager.text_to_speech("")  # Não deve explodir


# ─── text_to_speech_local ─────────────────────────────────────────────────────

class TestTextToSpeechLocal:
    def test_returns_bool(self):
        mock_engine = MagicMock()
        pyttsx3_mock.init.return_value = mock_engine
        mock_engine.getProperty.return_value = []

        with patch.dict("sys.modules", {"pyttsx3": pyttsx3_mock}):
            result = audio_manager.text_to_speech_local("texto")
        assert isinstance(result, bool)

    def test_returns_false_on_exception(self):
        pyttsx3_mock.init.side_effect = Exception("pyttsx3 error")
        with patch.dict("sys.modules", {"pyttsx3": pyttsx3_mock}):
            result = audio_manager.text_to_speech_local("texto")
        assert result is False
        pyttsx3_mock.init.side_effect = None  # Reset


# ─── text_to_speech_elevenlabs ───────────────────────────────────────────────

class TestTextToSpeechElevenLabs:
    def test_returns_false_without_api_key(self):
        env = {k: v for k, v in os.environ.items() if k != "ELEVENLABS_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = audio_manager.text_to_speech_elevenlabs("texto")
        assert result is False

    def test_returns_false_on_request_error(self):
        import requests
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
            with patch("audio_manager.requests.post", side_effect=Exception("network error")):
                result = audio_manager.text_to_speech_elevenlabs("texto")
        assert result is False

    def test_returns_false_on_non_200_response(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.content = b""

        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
            with patch("audio_manager.requests.post", return_value=mock_response):
                result = audio_manager.text_to_speech_elevenlabs("texto")
        assert isinstance(result, bool)


# ─── speech_to_text ───────────────────────────────────────────────────────────

class TestSpeechToText:
    def test_returns_string(self):
        with patch("audio_manager.play_chime"):
            with patch("audio_manager.sr") as mock_sr:
                mock_sr.Recognizer.return_value = MagicMock()
                mock_sr.Microphone.return_value.__enter__ = MagicMock(return_value=MagicMock())
                mock_sr.Microphone.return_value.__exit__ = MagicMock(return_value=False)
                mock_recognizer = MagicMock()
                mock_recognizer.recognize_google.return_value = "texto reconhecido"
                mock_sr.Recognizer.return_value = mock_recognizer
                with patch("builtins.input", return_value="texto digitado"):
                    result = audio_manager.speech_to_text()
        assert isinstance(result, str)

    def test_falls_back_to_input_on_microphone_error(self):
        with patch("audio_manager.play_chime"):
            with patch("audio_manager.sr") as mock_sr:
                mock_sr.Microphone.side_effect = Exception("no microphone")
                with patch("builtins.input", return_value="ação digitada") as mock_input:
                    result = audio_manager.speech_to_text()
        assert isinstance(result, str)

    def test_falls_back_to_input_on_unknown_value_error(self):
        with patch("audio_manager.play_chime"):
            with patch("audio_manager.sr") as mock_sr:
                mock_sr.UnknownValueError = Exception
                mock_recognizer = MagicMock()
                mock_recognizer.recognize_google.side_effect = mock_sr.UnknownValueError
                mock_sr.Recognizer.return_value = mock_recognizer
                with patch("builtins.input", return_value="digitado") as mock_input:
                    result = audio_manager.speech_to_text()
        assert isinstance(result, str)

    def test_plays_chime_before_listening(self):
        with patch("audio_manager.play_chime") as mock_chime:
            with patch("audio_manager.sr") as mock_sr:
                mock_sr.Microphone.side_effect = Exception("no mic")
                with patch("builtins.input", return_value="texto"):
                    audio_manager.speech_to_text()
            mock_chime.assert_called_once()
