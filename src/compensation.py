import numpy as np
from scipy import signal
from scipy.io import wavfile
import soundfile as sf
from scipy.interpolate import interp1d
from pydub import AudioSegment
import os
import logging
import librosa


# Configure logging
#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def load_audio(file_path):
    """
    Load audio data and return a NumPy array and the sample rate.
    Supports WAV and other formats via pydub.
    """
    try:
        # Use pydub for flexible format handling
        audio = AudioSegment.from_file(file_path)
        audio = audio.set_frame_rate(44100).set_sample_width(2)  # Set sample rate and bit depth without changing channels
        sample_rate = audio.frame_rate
        audio_data = np.array(audio.get_array_of_samples(), dtype=np.float32) / np.iinfo(np.int16).max
        
        # If the audio is stereo, reshape it to have two channels
        if audio.channels == 2:
            audio_data = audio_data.reshape(-1, 2)  # Reshape to (samples, 2) for stereo
        
        print(f"Loaded {file_path} - Sample rate: {sample_rate}, Shape: {audio_data.shape}")
        return audio_data, sample_rate
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None, None

class HearingCompensator:
    def __init__(self):
        # Константы из исследований Алдошиной
        self.threshold_db = 40  # Порог появления субъективных гармоник
        self.max_compression_db = 120  # Максимальный уровень компрессии
        self.compression_ratio = 1000  # Динамический диапазон слухового нерва
        
    def calculate_subjective_harmonics(self, frequency, level_db):
        """
        Расчет уровней субъективных гармоник для заданной частоты
        На основе данных из статьи: при 80 дБ на 1000 Гц вторая гармоника = 63 дБ
        """
        if level_db < self.threshold_db:
            return []
        
        harmonics = []
        for n in range(2, 5):  # Расчет до 4-й гармоники
            # Формула получена из соотношения 80:63 для первой гармоники
            harmonic_level = level_db - (17 * (n-1))
            if harmonic_level > 0:
                harmonics.append({
                    'frequency': frequency * n,
                    'level': harmonic_level
                })
        return harmonics

    def calculate_combination_tones(self, f1, f2, level_db):
        """
        Расчет комбинационных тонов для двух частот
        """
        if level_db < 50:  # Порог для простых разностных тонов
            return []
        
        combination_tones = []
        # Простой разностный тон
        diff_tone = abs(f2 - f1)
        diff_level = level_db - 20  # Примерно на 20 дБ ниже основного
        
        # Кубичный разностный тон
        cubic_tone = 2 * f1 - f2
        cubic_level = level_db - 25  # Примерно на 25 дБ ниже основного
        
        if diff_level > 0:
            combination_tones.append({
                'frequency': diff_tone,
                'level': diff_level,
                'type': 'difference'
            })
        
        if cubic_level > 0:
            combination_tones.append({
                'frequency': cubic_tone,
                'level': cubic_level,
                'type': 'cubic'
            })
            
        return combination_tones

    def apply_compression(self, signal_db):
        """
        Применение нелинейной компрессии по модели слухового аппарата
        """
        # Нормализация к диапазону слухового нерва
        compressed = np.zeros_like(signal_db)
        for i, level in enumerate(signal_db):
            if level < self.threshold_db:
                # Линейное усиление для слабых сигналов
                compressed[i] = level * 1.2
            else:
                # Нелинейная компрессия для сильных сигналов
                compressed[i] = self.threshold_db + (level - self.threshold_db) / 2
                
        return np.clip(compressed, -120, 0)  # Keep within a reasonable dB range

    def compensate_audio(self, audio_data, sample_rate):
            

        if audio_data.ndim == 2 and audio_data.shape[1] == 2:
            left_channel = audio_data[:, 0]
            right_channel = audio_data[:, 1]
        else:
            left_channel = audio_data
            right_channel = audio_data

        # Compute spectrograms
        frequencies, times, spec_left = signal.spectrogram(left_channel, fs=sample_rate, nperseg=2048, noverlap=1024)
        _, _, spec_right = signal.spectrogram(right_channel, fs=sample_rate, nperseg=2048, noverlap=1024)

        # Convert to dB
        spec_left_db = 10 * np.log10(spec_left + 1e-10)
        spec_right_db = 10 * np.log10(spec_right + 1e-10)

        # Apply compensation (simplified for clarity)
        compensated_spec_left_db = self.apply_compression(spec_left_db.flatten()).reshape(spec_left_db.shape)
        compensated_spec_right_db = self.apply_compression(spec_right_db.flatten()).reshape(spec_right_db.shape)

        # Avoid unnecessary conversions; directly perform ISTFT
        _, compensated_audio_left = signal.istft(
            10 ** (compensated_spec_left_db / 10), fs=sample_rate, nperseg=2048, noverlap=1024
        )
        _, compensated_audio_right = signal.istft(
            10 ** (compensated_spec_right_db / 10), fs=sample_rate, nperseg=2048, noverlap=1024
        )

        # Normalize
        compensated_audio = np.vstack((compensated_audio_left, compensated_audio_right)).T
        max_val = np.max(np.abs(compensated_audio))
        if max_val > 0:
            compensated_audio /= max_val

        return compensated_audio



def process_audio_file(input_file, output_file):
    """
    Process an audio file and apply compensation.
    """
    # Load the audio data
    audio_data, sample_rate = load_audio(input_file)
    print("Audio Loaded - Min:", np.min(audio_data), "Max:", np.max(audio_data), "Shape:", audio_data.shape)


    if audio_data is None or sample_rate is None:
        print(f"Failed to load {input_file}. Skipping...")
        return

    # Create the compensator and apply compensation
    compensator = HearingCompensator()
    compensated_audio = compensator.compensate_audio(audio_data, sample_rate)

    sf.write(output_file, compensated_audio, sample_rate)
