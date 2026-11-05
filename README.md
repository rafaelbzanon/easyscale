# EasyScale
# Sistema Open-Source para Automação de Pesagem Rodoviária

## Objetivo

Desenvolver uma solução open-source para automatizar o processo de pesagem rodoviária, reduzindo erros operacionais e aumentando a eficiência do controle logístico.

## Tecnologias

### Backend
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571.svg?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-000?style=for-the-badge&logo=postgresql)

### Frontend
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![Tailwind](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white)

### OCR
![OpenCV](https://img.shields.io/badge/opencv-%23white.svg?style=for-the-badge&logo=opencv&logoColor=white)
- EasyOCR

### Infraestrutura
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)

## Estado do projeto

Protótipo em desenvolvimento (TCC — IFRS, Veranópolis). **Ainda não há aplicação para executar.**

- **Pronto:** regras de domínio, camada de dispositivos com simuladores e pipeline de LPR, em `backend/`, com testes automatizados.
- **Em definição:** contratos da API, em `specs/features/`.
- **A fazer:** banco de dados, orquestração, API, frontend e Docker.

Nada foi validado com balança, cancela ou câmera reais. O andamento fica em [`specs/tarefas-iniciais.md`](specs/tarefas-iniciais.md).

## Funcionalidades previstas

- Cadastro de veículos
- Controle de pesagens
- Controle  de agendamentos
- Automação de cancelas e pesagem com LPR e visão computacional
- Dashboard operacional

## Licença
 [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
