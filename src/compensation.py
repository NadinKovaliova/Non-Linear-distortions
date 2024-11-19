import numpy as np
from scipy import signal
from scipy.io import wavfile
import soundfile as sf
from scipy.interpolate import interp1d
from pydub import AudioSegment
import os
import librosa
import matplotlib.pyplot as plt




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
        Apply non-linear compression based on auditory model.
        """
        compressed = np.zeros_like(signal_db)
        for i, level in np.ndenumerate(signal_db):  # Support multi-dimensional arrays
            if level < self.threshold_db:
                compressed[i] = level * 1.2  # Mild linear amplification
            else:
                compressed[i] = self.threshold_db + (level - self.threshold_db) / 2  # Non-linear compression
        return compressed

    def compensate_audio(self, audio_data, sample_rate):
        """
        Targeted hearing compensation method with spectrogram visualization.
        """
        # Ensure result directory exists
        os.makedirs('../result', exist_ok=True)

        # Separate stereo channels or handle mono audio
        if audio_data.ndim == 2 and audio_data.shape[1] == 2:
            left_channel = audio_data[:, 0]
            right_channel = audio_data[:, 1]
        else:
            left_channel = audio_data
            right_channel = audio_data

        # Visualize input spectrogram
        plt.figure(figsize=(15, 5))
        plt.subplot(1, 2, 1)
        plt.title("Input Spectrogram")
        
        # Compute input spectrogram
        f_input, t_input, Sxx_input = signal.spectrogram(left_channel, fs=sample_rate)
        plt.pcolormesh(t_input, f_input, 10 * np.log10(Sxx_input), shading='gouraud', cmap='viridis')
        plt.ylabel('Frequency [Hz]')
        plt.xlabel('Time [sec]')
        plt.colorbar(label='Intensity [dB]')

        def apply_hearing_compensation(channel):

            # Use librosa for spectral processing
            n_fft = 2048
            hop_length = 512
            
            # Perform Short-Time Fourier Transform
            stft = librosa.stft(channel, n_fft=n_fft, hop_length=hop_length)
            
            # Define a frequency-dependent compensation curve
            frequencies = librosa.fft_frequencies(sr=sample_rate, n_fft=n_fft)
            
            # Compensation curve - boost mid and high frequencies
            compensation_curve = np.ones_like(frequencies)
            
            # Boost around 2-4 kHz (critical speech intelligibility region)
            speech_boost_mask = (frequencies >= 2000) & (frequencies <= 4000)
            compensation_curve[speech_boost_mask] *= 1.5
            
            # Additional boost for high frequencies
            high_freq_mask = frequencies > 4000
            compensation_curve[high_freq_mask] *= 1.8
            
            # Apply compensation to magnitude spectrum
            magnitude = np.abs(stft)
            compensated_magnitude = magnitude * compensation_curve[:, np.newaxis]
            
            # Reconstruct the complex spectrum
            compensated_stft = compensated_magnitude * np.exp(1j * np.angle(stft))
            
            # Inverse STFT to get time-domain signal
            compensated_channel = librosa.istft(
                compensated_stft, 
                hop_length=hop_length, 
                length=len(channel)
            )
            
            # Soft dynamic range compression
            def soft_compress(x, threshold=0.5):
                return np.sign(x) * (1 - np.exp(-np.abs(x) * threshold))
            
            compensated_channel = soft_compress(compensated_channel)
            
            return compensated_channel

        # Apply compensation to each channel
        compensated_left = apply_hearing_compensation(left_channel)
        compensated_right = apply_hearing_compensation(right_channel)

        # Visualize output spectrogram
        plt.subplot(1, 2, 2)
        plt.title("Compensated Spectrogram")
        
        # Compute output spectrogram
        f_output, t_output, Sxx_output = signal.spectrogram(compensated_left, fs=sample_rate)
        plt.pcolormesh(t_output, f_output, 10 * np.log10(Sxx_output), shading='gouraud', cmap='viridis')
        plt.ylabel('Frequency [Hz]')
        plt.xlabel('Time [sec]')
        plt.colorbar(label='Intensity [dB]')

        # Adjust layout and save
        plt.tight_layout()
        plt.savefig('../result/spectrogram_comparison.png')
        plt.close()

        # Recombine channels if stereo
        if audio_data.ndim == 2 and audio_data.shape[1] == 2:
            compensated_audio = np.column_stack((compensated_left, compensated_right))
        else:
            compensated_audio = compensated_left

        # Normalization
        max_val = np.max(np.abs(compensated_audio))
        if max_val > 0:
            compensated_audio = compensated_audio * min(1.0, 0.99 / max_val)

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
