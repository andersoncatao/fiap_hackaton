import os
import random
from PIL import Image
import shutil

# Configurações
IMG_SIZE = 640
ICON_SIZE = 100
NUM_IMAGES = 200

# Diretórios
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ICONS_DIR = os.path.join(BASE_DIR, "icons")
IMG_OUT_DIR = os.path.join(BASE_DIR, "output/images/train")
LBL_OUT_DIR = os.path.join(BASE_DIR, "output/labels/train")
os.makedirs(IMG_OUT_DIR, exist_ok=True)
os.makedirs(LBL_OUT_DIR, exist_ok=True)

# Limpa os diretórios
shutil.rmtree(os.path.join(BASE_DIR, "output"), ignore_errors=True)
os.makedirs(IMG_OUT_DIR, exist_ok=True)
os.makedirs(LBL_OUT_DIR, exist_ok=True)

# Mapeia classes
classes = {}
for idx, fname in enumerate(sorted(os.listdir(ICONS_DIR))):
    if fname.endswith(".png"):
        cname = os.path.splitext(fname)[0].lower()
        classes[cname] = idx

icon_files = list(classes.keys())

def overlaps(box1, box2):
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    return not (x1 + w1 < x2 or x1 > x2 + w2 or y1 + h1 < y2 or y1 > y2 + h2)

for i in range(NUM_IMAGES):
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), (255, 255, 255))
    labels = []
    placed_boxes = []

    num_icons = random.randint(3, 6)
    icons_selected = random.sample(icon_files, num_icons)

    for cname in icons_selected:
        icon_path = os.path.join(ICONS_DIR, f"{cname}.png")
        icon = Image.open(icon_path).convert("RGBA")
        icon = icon.resize((ICON_SIZE, ICON_SIZE))

        tries = 0
        while True:
            x = random.randint(0, IMG_SIZE - ICON_SIZE)
            y = random.randint(0, IMG_SIZE - ICON_SIZE)
            new_box = (x, y, ICON_SIZE, ICON_SIZE)

            if all(not overlaps(new_box, b) for b in placed_boxes) or tries > 10:
                break
            tries += 1

        img.paste(icon, (x, y), mask=icon)
        placed_boxes.append(new_box)

        cx = (x + ICON_SIZE / 2) / IMG_SIZE
        cy = (y + ICON_SIZE / 2) / IMG_SIZE
        w = ICON_SIZE / IMG_SIZE
        h = ICON_SIZE / IMG_SIZE
        class_id = classes[cname]
        labels.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

    img_filename = f"synthetic_{i}.jpg"
    lbl_filename = f"synthetic_{i}.txt"
    img.save(os.path.join(IMG_OUT_DIR, img_filename))
    with open(os.path.join(LBL_OUT_DIR, lbl_filename), "w") as f:
        f.write("\n".join(labels))

# Gera aws.yaml
yaml_path = os.path.join(BASE_DIR, "aws.yaml")
with open(yaml_path, "w") as f:
    f.write("path: output\n")
    f.write("train: images/train\n")
    f.write("val: images/train\n")
    f.write(f"nc: {len(classes)}\n")
    f.write("names:\n")
    for cname, idx in sorted(classes.items(), key=lambda x: x[1]):
        f.write(f"  {idx}: {cname}\n")

print(f"[✓] {NUM_IMAGES} imagens sintéticas geradas em output/images/train")
print(f"[✓] Labels YOLOv8 geradas em output/labels/train")
print(f"[✓] Arquivo aws.yaml gerado com {len(classes)} classes")
print("Agora você pode treinar com: yolo detect train model=yolov8n.pt data=aws.yaml epochs=50 imgsz=640")
