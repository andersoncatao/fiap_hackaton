import os, time, base64, json, logging, re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from ultralytics import YOLO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import mm
import cv2

# ─────────── Configurações Globais ───────────
model_path = 'runs/detect/train/weights/best.pt'
image_path = 'DiagramaTest.png'

# ─────────── Logging ───────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ─────────── Credenciais ───────────
load_dotenv()
client_oai = OpenAI()
client_cv = ComputerVisionClient(
    os.getenv("AZURE_ENDPOINT"),
    CognitiveServicesCredentials(os.getenv("AZURE_KEY"))
)

# ─────────── GPT Tool Schema ───────────
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "set_components",
        "parameters": {
            "type": "object",
            "properties": {
                "components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "provider": {"type": "string"},
                            "type": {"type": "string"}
                        },
                        "required": ["name", "provider", "type"]
                    }
                }
            },
            "required": ["components"]
        }
    }
}
FENCE_RX = re.compile(r"^```(?:json)?\s*|\s*```$", re.I | re.M)

# ─────────── Função: Detectar Componentes ───────────
def list_components(image_path: str, model_path: str) -> list[dict]:
    # 1. YOLO - Detecção de ícones
    log.info("Detectando ícones com YOLO...")
    model = YOLO(model_path)
    results = model(image_path, conf=0.6)

    yolo_classes = []
    for r in results:
        annotated = r.plot()
        output_path = "output_diagrama_detected.jpg"
        cv2.imwrite(output_path, annotated)
        log.info(f"Imagem com bounding boxes salva em {output_path}")

    log.info("Classes detectadas (YOLO):")
    for box in results[0].boxes:
        class_id = int(box.cls[0])
        class_name = model.names[class_id]
        yolo_classes.append(class_name)
        log.info(f"- {class_name}")

    # 2. OCR - Azure
    log.info("Executando OCR via Azure...")
    with open(image_path, "rb") as f:
        op = client_cv.read_in_stream(f, raw=True)
    op_id = op.headers["Operation-Location"].split("/")[-1]

    while True:
        result = client_cv.get_read_result(op_id)
        if result.status not in ("notStarted", "running"):
            break
        time.sleep(0.4)

    ocr_lines = [ln.text for pg in result.analyze_result.read_results for ln in pg.lines]
    log.info("OCR detectou %d linhas:", len(ocr_lines))
    for i, line in enumerate(ocr_lines, 1):
        print(f"{i:02d}: {line}")

    # 3. GPT-4o - Envio combinado (OCR + YOLO)
    log.info("Enviando dados para GPT-4o...")
    combined_prompt = "Texto detectado via OCR:\n"
    combined_prompt += "\n".join(ocr_lines) if ocr_lines else "(nenhum texto)\n"
    combined_prompt += "\n\nÍcones detectados via YOLO (classes):\n"
    combined_prompt += "\n".join(f"- {cls}" for cls in yolo_classes) if yolo_classes else "(nenhum ícone detectado)"

    data_uri = "data:image/png;base64," + base64.b64encode(Path(image_path).read_bytes()).decode()

    response = client_oai.chat.completions.create(
        model="gpt-4o",
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "function", "function": {"name": "set_components"}},
        messages=[
            {"role": "system", "content": "Você deve identificar os componentes da arquitetura em nuvem (AWS/Azure) e chamar a função set_components com os dados estruturados."},
            {"role": "user", "content": [
                {"type": "text", "text": combined_prompt},
                {"type": "image_url", "image_url": {"url": data_uri}}
            ]}
        ],
        temperature=0,
        max_tokens=800
    )

    msg = response.choices[0].message

    if msg.tool_calls:
        return json.loads(msg.tool_calls[0].function.arguments)["components"]

    if isinstance(msg.content, str):
        cleaned = FENCE_RX.sub("", msg.content).strip()
        return json.loads(cleaned)

    return []

# ─────────── Função: Gerar Relatório STRIDE via GPT ───────────
def gerar_relatorio_stride(components: list[dict]) -> str:
    prompt = (
        "Com base na lista de componentes abaixo, gere um relatório de modelagem de ameaças "
        "utilizando a metodologia STRIDE. Para cada componente, identifique ameaças potenciais "
        "relacionadas a: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, "
        "e Elevation of Privilege. Sugira também contramedidas para cada ameaça.\n\n"
        "Responda com um texto estruturado, claro, técnico, e em português.\n\n"
        f"Lista de componentes:\n{json.dumps(components, indent=2, ensure_ascii=False)}"
    )

    resp = client_oai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Você é um especialista em segurança da informação."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=2000
    )

    return resp.choices[0].message.content.strip()

# ─────────── Função: Gerar PDF Estruturado do Relatório ───────────
def gerar_pdf_relatorio(texto: str, output_file: str = "relatorio_stride.pdf"):
    doc = SimpleDocTemplate(output_file, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    doc.title = "Relatório STRIDE"
    styles = getSampleStyleSheet()

    # Estilos customizados
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, spaceAfter=14)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=13, spaceAfter=10)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontName='Helvetica-Bold', leftIndent=10, spaceAfter=2)
    text_style = ParagraphStyle('Text', parent=styles['Normal'], leftIndent=20, spaceAfter=6)

    flowables = []
    lines = texto.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("# "):
            title = line[2:].strip()
            flowables.append(Paragraph(title, title_style))
            flowables.append(Spacer(1, 12))

        elif line.startswith("## "):
            component = line[3:].strip()
            flowables.append(Paragraph(component, section_style))

        elif line.startswith("### "):
            threat_type = line[4:].strip()
            flowables.append(Paragraph(f"<b>{threat_type}</b>", label_style))

        elif line.startswith("- **"):
            match = re.match(r"- \*\*(.+?)\*\*: (.+)", line)
            if match:
                label, content = match.groups()
                flowables.append(Paragraph(f"<b>{label}:</b>", label_style))
                flowables.append(Paragraph(content.strip(), text_style))
            else:
                flowables.append(Paragraph(line, text_style))
        else:
            flowables.append(Paragraph(line, text_style))

    doc.build(flowables)
    log.info(f"Relatório STRIDE salvo em: {output_file}")

# ─────────── Execução Principal ───────────
if __name__ == "__main__":
    components = list_components(image_path, model_path)

    if not components:
        log.warning("Nenhum componente retornado pelo GPT-4o.")
    else:
        print("\n Componentes estruturados detectados:")
        print(json.dumps(components, indent=2, ensure_ascii=False))

        log.info("Gerando relatório STRIDE com GPT-4o...")
        relatorio_texto = gerar_relatorio_stride(components)

        print("\n Relatório STRIDE:\n")
        print(relatorio_texto)

        gerar_pdf_relatorio(relatorio_texto)
