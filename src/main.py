import os
from compensation import process_audio_file, load_audio

# Define paths
UPLOAD_FOLDER = "../upload"
RESULT_FOLDER = "../result"

# Ensure the result folder exists
os.makedirs(RESULT_FOLDER, exist_ok=True)

def process_all_files(upload_folder, result_folder):
    """
    Process all audio files in the upload folder and save to the result folder.
    """
    for filename in os.listdir(upload_folder):
        input_path = os.path.join(upload_folder, filename)

        # Check if the file is a valid audio file
        if os.path.isfile(input_path) and filename.endswith((".wav", ".mp3", ".flac", ".ogg")):
            output_path = os.path.join(result_folder, f"{os.path.splitext(filename)[0]}.mp3")
            print(f"Processing {filename}...")

            audio_data, sample_rate = load_audio(input_path)

            if audio_data is None or sample_rate is None:
                print(f"Failed to load {input_path}. Skipping...")
                return
            print(f"Audio length (samples): {len(audio_data)}, Sample rate: {sample_rate}")
            

            try:
                # Process the audio file
                process_audio_file(input_path, output_path)
                print(f"Processed and saved to {output_path}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")
        else:
            print(f"Skipping {filename}: Not a valid audio file.")

if __name__ == "__main__":
    process_all_files(UPLOAD_FOLDER, RESULT_FOLDER)