# Non-Linear-distortions
Final Project for CS50x

# Hearing Compensation Audio Processing Tool

## Overview
This program applies advanced audio compensation techniques to mitigate non-linear distortions of human hearing, enhancing audio perception and intelligibility.

## Non-Linear Distortions of Human Hearing

### What are Non-Linear Ear Distortions?
The human auditory system introduces several non-linear distortions when perceiving sound:

1. **Subjective Harmonics**
   - When exposed to loud sounds, ears generate additional frequency components
   - These "phantom" frequencies are not present in the original sound
   - Typically occur at integer multiples of the original frequency
   - Most prominent above 80 dB sound pressure levels

2. **Combination Tones**
   - Generated when two or more frequencies interact in the inner ear
   - Two main types:
     a) Difference Tones: New frequencies created by subtracting input frequencies
     b) Cubic Difference Tones: More complex interactions creating additional frequencies

3. **Compression and Masking**
   - Ear's dynamic range is limited compared to external sound
   - Loud sounds can "mask" or suppress quieter sounds
   - Non-linear compression occurs in the cochlea

### Compensation Strategies
Our program addresses these distortions by:
- Frequency-specific equalization
- Soft dynamic range compression
- Boosting critical frequency ranges (2-4 kHz)
- Preserving phase and temporal information

## Installation

### Prerequisites
- Python 3.8+
- FFmpeg installed system-wide

### Setup
1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Directory Structure
```
project_root/
│
├── upload/     # Place input audio files here
├── result/     # Processed files and spectrograms will be saved here
└── src/
    ├── main.py
    └── compensation.py
```

### Running the Program
```bash
python src/main.py
```

### Supported Audio Formats
- WAV
- MP3
- FLAC
- OGG

### Output
- Compensated audio files in the `result/` directory
- Spectrogram comparison image: `result/spectrogram_comparison.png`

## Visualization
The program generates a spectrogram comparison showing:
- Input audio frequency characteristics
- Compensated audio frequency characteristics
- Changes in spectral intensity

## Customization
Modify `compensation.py` to adjust:
- Frequency boost levels
- Compensation intensity
- Specific hearing impairment models

## Scientific References
- Aldoshina, I.A. - Research on Subjective Hearing Perception
- Bekesy, G. von - Experiments in Hearing
- Moore, B.C.J. - Perceptual Consequences of Cochlear Damage

## Limitations
- Not a medical device
- Individual hearing variations not fully accounted for
- Recommended for general audio enhancement

## Contributing
Contributions are welcome! Please submit pull requests or open issues.

## License
[Insert your license here]