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
        self.threshold_db = 40
        self.max_compression_db = 120
        self.compression_ratio = 1000

    def iso_compensation(self, frequencies):
        """
        Applies ISO 226 compensation to balance perceived loudness across frequencies.
        """
        # ISO 226 data for perceived loudness
        iso_frequencies = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
        iso_sensitivity = [75, 60, 50, 40, 30, 25, 20, 30, 50, 70]  # Example sensitivity curve
        
        # Interpolate to match spectrogram frequencies
        iso_curve = interp1d(iso_frequencies, iso_sensitivity, kind="linear", fill_value="extrapolate")
        return iso_curve(frequencies)

    def apply_dynamic_compression(self, signal_db):
        """
        Compresses the dynamic range of the signal.
        """
        compressed = np.zeros_like(signal_db)
        for i, level in enumerate(signal_db):
            if level < self.threshold_db:
                compressed[i] = level * 1.2
            else:
                compressed[i] = self.threshold_db + (level - self.threshold_db) / 2
        return compressed

    def spectral_masking(self, frequencies, spectrogram):
        """
        Applies spectral masking to simulate the effect of one frequency masking another.
        """
        masked_spec = np.copy(spectrogram)
        for i in range(1, len(frequencies)):
            masked_spec[i] -= masked_spec[i - 1] * 0.5  # Example masking effect
        return np.maximum(masked_spec, 0)  # Avoid negative values

    def apply_phase_distortion(self, spectrogram):
        """
        Introduces phase shifts to simulate real-world distortions.
        """
        phase_shifts = np.random.uniform(-np.pi / 4, np.pi / 4, spectrogram.shape)
        return spectrogram * np.exp(1j * phase_shifts)  # Apply phase shift as a complex multiplier

    def harmonic_reduction(self, frequencies, spectrogram):
        """
        Reduces the volume of harmonics to prevent harshness.
        """
        reduced_spec = np.copy(spectrogram)
        for i, freq in enumerate(frequencies):
            harmonics = [freq * n for n in range(2, 5)]
            for harmonic in harmonics:
                harm_idx = np.argmin(np.abs(frequencies - harmonic))
                if harm_idx < len(frequencies):
                    reduced_spec[harm_idx] *= 0.7  # Reduce harmonic level by 30%
        return reduced_spec

    def compensate_audio(self, audio_data, sample_rate):
        """
        Processes the audio data to compensate for non-linear distortions.
        """
        audio_length = len(audio_data)
        # Dynamically set nperseg and noverlap based on audio length
        if audio_length < 2048:
            nperseg = audio_length  # If audio is shorter than 2048, use the audio length
        else:
            nperseg = 2048  # Otherwise, use the default segment length

        # Ensure noverlap is less than nperseg
        #noverlap = min(nperseg // 2, audio_length // 2)



        # If the calculated overlap is not less than nperseg, adjust it
        #if noverlap >= nperseg:
           # noverlap = nperseg - 1

        print(f"Using nperseg={nperseg}, noverlap={noverlap}, audio_length={audio_length}")


        # Transform audio to frequency domain (works for stereo)
        frequencies, times, spec = signal.spectrogram(audio_data, fs=sample_rate, nperseg=nperseg, noverlap=noverlap)
        spec_db = 10 * np.log10(spec + 1e-10)

        # Apply ISO compensation
        iso_curve = self.iso_compensation(frequencies)
        spec_db += iso_curve[:, np.newaxis]

        # Apply dynamic compression
        spec_db = self.apply_dynamic_compression(spec_db)

        # Apply spectral masking
        spec_db = self.spectral_masking(frequencies, spec_db)

        # Apply harmonic reduction
        spec_db = self.harmonic_reduction(frequencies, spec_db)

        # Convert back to time domain (preserve stereo)
        spec_linear = 10 ** (spec_db / 10)
        _, compensated_audio = signal.istft(spec_linear, fs=sample_rate, nperseg=nperseg, noverlap=noverlap)

        return compensated_audio



def process_audio_file(input_file, output_file):
    """
    Processes an audio file with the compensator.
    """
    audio_data, sample_rate = sf.read(input_file)
    compensator = HearingCompensator()
    compensated_audio = compensator.compensate_audio(audio_data, sample_rate)
    sf.write(output_file, compensated_audio, sample_rate)