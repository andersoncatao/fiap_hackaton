# 🛡️ Modelagem de Ameaças com STRIDE impulsionada por IA

Este projeto automatiza a identificação de componentes arquiteturais em diagramas e gera **Relatórios de Modelagem de Ameaças STRIDE** utilizando IA (YOLOv8, OCR da Azure e GPT-4o). Ideal para arquiteturas baseadas em nuvem (AWS, Azure, etc).

## 🚀 Visão Geral

### Objetivo
Detectar componentes em diagramas de arquitetura (ícones + textos), classificá-los por tipo/provedor (e.g. *EC2 - AWS*) e gerar um relatório técnico com ameaças e contramedidas baseado na metodologia **STRIDE**.

---

## 🧠 Fluxo da Solução

1. **Geração de Dataset Sintético** (`generate_synthetic_diagrams.py`)
   - Combina ícones de arquitetura em imagens aleatórias para treinar modelos de detecção (YOLOv8).
   - Cria labels no formato YOLO e arquivo `aws.yaml`.

2. **Detecção em Diagramas Reais** (`app.py`)
   - **YOLOv8** detecta ícones arquiteturais.
   - **Azure OCR** extrai textos (ex: nomes dos serviços).
   - **GPT-4o** combina resultados e estrutura os componentes (nome, tipo, provedor).
   - **GPT-4o** gera um **Relatório STRIDE** completo (spoofing, tampering, etc).
   - O relatório é salvo como **PDF estruturado**.

---

## 📂 Estrutura de Pastas

```
.
├── generate_synthetic_diagrams.py      # Gera imagens sintéticas com ícones
├── app.py                              # Pipeline principal
├── icons/                              # Ícones PNG (100x100) de arquitetura
├── output/
│   ├── images/train/                   # Imagens sintéticas
│   ├── labels/train/                   # Labels YOLO
│   └── relatorio_stride.pdf            # Relatório final gerado
├── aws.yaml                            # Configuração de dataset para YOLOv8
├── DiagramaTest.png                    # Imagem de diagrama real de exemplo
└── .env                                # Variáveis de ambiente
```

---

## ⚙️ Requisitos

- Python 3.10+
- Pacotes:
  - `ultralytics`, `Pillow`, `opencv-python`, `reportlab`, `dotenv`, `openai`, `azure-cognitiveservices-vision-computervision`
- Conta na **Azure Cognitive Services**
- Chave e endpoint da **API OpenAI**

---

## 📥 Como Executar

### 1. Geração de Dataset Sintético (YOLO)

```bash
python generate_synthetic_diagrams.py
```

- Gera imagens e labels sintéticas em `output/images/train` e `output/labels/train`.
- Arquivo `aws.yaml` criado automaticamente com as classes detectadas.

> Você pode treinar com:
> ```bash
> yolo detect train model=yolov8n.pt data=aws.yaml epochs=50 imgsz=640
> ```

---

### 2. Geração do Relatório STRIDE a partir de um Diagrama Real

Edite o caminho da imagem e o modelo no topo do `app.py`:

```python
model_path = 'runs/detect/train/weights/best.pt'
image_path = 'DiagramaTest.png'
```

Depois, execute:

```bash
python app.py
```

- Detecta os ícones (YOLO) e textos (Azure OCR)
- Usa GPT-4o para estruturar os componentes e gerar o relatório
- Gera um PDF chamado `relatorio_stride.pdf`

---

## 🧪 Exemplo de Componente Detectado

```json
[
  {
    "name": "EC2",
    "provider": "AWS",
    "type": "Compute"
  },
  {
    "name": "S3",
    "provider": "AWS",
    "type": "Storage"
  }
]
```

---

## 📄 Exemplo de Relatório Gerado (Resumo)

> **Componente:** EC2  
> **Spoofing:** Possível uso de chaves SSH comprometidas  
> **Tampering:** Modificação de imagens de AMI  
> **Mitigação:** Uso de IAM Roles com políticas restritas

(PDF completo estruturado com título, seções e descrições por ameaça)

---

## 🔐 Variáveis `.env`

```env
AZURE_KEY=your_azure_key
AZURE_ENDPOINT=https://your-cv-endpoint.cognitiveservices.azure.com/
OPENAI_API_KEY=your_openai_key
```

---

## 📌 Notas

- O projeto pode ser facilmente estendido para outros tipos de diagramas (GCP, On-Prem, etc).
- Também pode ser integrado com ferramentas de DevSecOps.

---

## 📚 Referências

- [STRIDE Threat Model](https://docs.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)
- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [Azure OCR](https://learn.microsoft.com/en-us/azure/cognitive-services/computer-vision/overview-ocr)
- [OpenAI API](https://platform.openai.com/docs)

---

## 👨‍💻 Autor

Desenvolvido por [Anderson Catão](https://github.com/andersoncatao)
