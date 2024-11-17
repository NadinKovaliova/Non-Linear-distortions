import numpy as np
from scipy import signal
from scipy.io import wavfile
import soundfile as sf
from scipy.interpolate import interp1d
from pydub import AudioSegment

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
                
        return compressed

    def compensate_audio(self, audio_data, sample_rate):
        """
        Основная функция компенсации искажений для аудиофайла
        """
        # Преобразование в частотную область
        frequencies, times, spec = signal.spectrogram(
            audio_data, 
            fs=sample_rate,
            nperseg=2048,
            noverlap=1024
        )
        
        # Преобразование в дБ
        spec_db = 10 * np.log10(spec + 1e-10)
        
        # Компенсация для каждого частотно-временного блока
        compensated_spec = np.zeros_like(spec_db)
        
        for i, freq in enumerate(frequencies):
            for j, time in enumerate(times):
                level = spec_db[i, j]
                
                # Применение компрессии
                compressed_level = self.apply_compression(np.array([level]))[0]
                
                # Расчет и компенсация гармоник
                harmonics = self.calculate_subjective_harmonics(freq, level)
                for harmonic in harmonics:
                    harm_idx = np.argmin(np.abs(frequencies - harmonic['frequency']))
                    if harm_idx < len(frequencies):
                        compensated_spec[harm_idx, j] -= harmonic['level']
                
                compensated_spec[i, j] = compressed_level
        
        # Обратное преобразование в линейный масштаб
        compensated_spec = 10 ** (compensated_spec / 10)
        
        # Обратное преобразование во временную область
        _, compensated_audio = signal.istft(
            compensated_spec,
            fs=sample_rate,
            nperseg=2048,
            noverlap=1024
        )
        
        return compensated_audio

def process_audio_file(input_file, output_file):
    """
    Обработка аудиофайла с компенсацией нелинейных искажений
    """
    # Загрузка аудио
    audio_data, sample_rate = sf.read(input_file)
    
    # Создание компенсатора
    compensator = HearingCompensator()
    
    # Применение компенсации
    compensated_audio = compensator.compensate_audio(audio_data, sample_rate)
    
    # Сохранение результата
    sf.write(output_file, compensated_audio, sample_rate)