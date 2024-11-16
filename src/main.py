import os
from compensation import process_audio_file

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
        if os.path.isfile(input_path) and filename.endswith((".wav", ".mp3", ".flac")):
            output_path = os.path.join(result_folder, filename)
            print(f"Processing {filename}...")
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