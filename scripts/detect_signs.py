from PIL import Image

image_path = "assets/png/pages/page_1.png"

image = Image.open(image_path)

print("Image loaded successfully!")

print(f"Width : {image.width} pixels")
print(f"Height: {image.height} pixels")
print(f"Mode  : {image.mode}")