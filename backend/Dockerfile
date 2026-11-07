# Imagem do backend — spec specs/features/025-docker-backend/spec.md (BE-801).
# Contexto de build: esta pasta (`docker build -t pesagem-backend backend/`).
FROM python:3.12.15-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY pyproject.toml ./

# O pyproject.toml é a única fonte das versões (spec 001 §8). O pip da imagem
# não lê `--group`, então a lista sai do próprio arquivo. torch/torchvision só
# para CPU vêm do índice do PyTorch antes do resto (D-09, AMBIENTE.md §6.1).
RUN python -c "import tomllib; p = tomllib.load(open('pyproject.toml', 'rb')); print(*p['project']['dependencies'], sep='\n')" > /tmp/execucao.txt \
 && python -c "import tomllib; p = tomllib.load(open('pyproject.toml', 'rb')); print(*p['dependency-groups']['lpr'], sep='\n')" > /tmp/lpr.txt \
 && grep '^torch' /tmp/lpr.txt > /tmp/torch.txt \
 && pip install --index-url https://download.pytorch.org/whl/cpu -r /tmp/torch.txt \
 && pip install -r /tmp/execucao.txt -r /tmp/lpr.txt \
 && rm /tmp/execucao.txt /tmp/lpr.txt /tmp/torch.txt

COPY src ./src

# Sem privilégios. /modelos-ocr é o ponto do volume pesagem-modelos-ocr (P-9, D-08);
# criado aqui com o dono certo para o volume novo herdar a permissão.
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin pesagem \
 && mkdir /modelos-ocr \
 && chown pesagem /modelos-ocr
USER pesagem

EXPOSE 8000
# Um processo só, sem --workers: a posse das portas seriais é de um único processo (ADR-0002).
CMD ["uvicorn", "--factory", "pesagem.main:criar_aplicacao", "--host", "0.0.0.0", "--port", "8000"]
