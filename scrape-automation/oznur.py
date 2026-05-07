import kagglehub

# Download latest version
path = kagglehub.dataset_download("mexwell/iba-cocktails")

print("Path to dataset files:", path)