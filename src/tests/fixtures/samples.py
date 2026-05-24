"""
tests/fixtures/samples.py  —  Shared test fixtures and sample data.
"""
from __future__ import annotations

# ── Sample LaTeX resume (Om Dhangar's resume structure) ───────────────────────
SAMPLE_LATEX_RESUME = r"""
\documentclass[letterpaper,10pt]{article}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage{tabularx}
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\addtolength{\oddsidemargin}{-0.6in}
\addtolength{\textwidth}{1.2in}
\addtolength{\topmargin}{-.85in}
\addtolength{\textheight}{1.75in}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}
\titleformat{\section}{\vspace{-6pt}\bfseries\raggedright\large}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]
\newcommand{\resumeItem}[1]{\item\small{#1}\vspace{-1pt}}
\newcommand{\resumeSubheading}[4]{
  \item
  \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
    \textbf{#1} & \small #2 \\
    \textit{\small#3} & \textit{\small #4} \\
  \end{tabular*}\vspace{-5pt}
}
\newcommand{\resumeProjectHeading}[2]{
  \item\vspace{1pt}
  \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
    \small#1 & \small #2 \\
  \end{tabular*}\vspace{-4pt}
}
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}[leftmargin=*,itemsep=-1pt,topsep=0pt]}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-4pt}}

\begin{document}

\begin{center}
  \textbf{\Huge \scshape Om Dhangar} \textbar{} \Large Software Developer \\
  \vspace{1pt}
  \small
  \href{mailto:omdhangar51@gmail.com}{omdhangar51@gmail.com} \textbar{}
  Shirpur, Maharashtra
\end{center}

\section{Experience}
\resumeSubHeadingListStart
  \resumeSubheading{Backend Developer Intern}{Apr 2025 -- Jul 2025}{ECOEVR Mobility}{Remote}
  \resumeItemListStart
    \resumeItem{Designed REST APIs using Node.js and Express.js.}
    \resumeItem{Containerized services with Docker, reducing deployment failures by 60\%.}
  \resumeItemListEnd
\resumeSubHeadingListEnd

\section{Projects}
\resumeSubHeadingListStart
  \resumeProjectHeading{\textbf{Microservices E-Commerce Platform}}{2024}
  \resumeItemListStart
    \resumeItem{Architected 9-service event-driven platform with Kafka and RabbitMQ.}
    \resumeItem{Implemented dual-database architecture with PostgreSQL and MongoDB.}
  \resumeItemListEnd
\resumeSubHeadingListEnd

\section{Skills}
\begin{itemize}[leftmargin=0.15in, label={}]
  \resumeItem{\textbf{Languages:} Python, JavaScript, TypeScript, SQL, C++}
  \resumeItem{\textbf{Backend:} Node.js, FastAPI, REST APIs, Microservices, Kafka, RabbitMQ}
  \resumeItem{\textbf{Databases:} PostgreSQL, MongoDB, Redis}
  \resumeItem{\textbf{Tools:} Docker, AWS S3, Git}
\end{itemize}

\end{document}
"""

SAMPLE_JD_BACKEND = """
We are looking for a Backend Software Engineer to join our platform team.

Requirements:
- 2+ years backend experience (Python strongly preferred)
- Experience with REST APIs and microservices
- Proficiency with PostgreSQL and Redis
- Familiarity with message queues (Kafka or RabbitMQ)
- Docker and containerized deployments
- Strong understanding of distributed systems

Nice to have:
- Experience with FastAPI or similar Python frameworks
- AWS experience (S3, Lambda)
- System design knowledge (HLD/LLD)

You will:
- Design and maintain scalable backend services
- Collaborate with frontend and data teams
- Own deployments and reliability for core platform services
"""

SAMPLE_JD_ML = """
Machine Learning Engineer - NLP Platform

We're building the next generation of language understanding infrastructure.

Requirements:
- 3+ years ML engineering experience
- Strong Python + PyTorch or TensorFlow
- Experience deploying ML models at scale
- Familiarity with LLMs, transformers, fine-tuning
- Experience with MLOps tools (MLflow, Weights & Biases)

Responsibilities:
- Train and fine-tune LLMs for production use
- Build model serving infrastructure
- Design evaluation frameworks
"""

SAMPLE_IDENTITY_JSON = {
    "name": "Om Dhangar",
    "years_experience": 1.0,
    "core_skills": ["Node.js", "Python", "FastAPI", "PostgreSQL", "MongoDB", "Redis", "Docker", "Kafka", "RabbitMQ"],
    "companies_worked": ["ECOEVR Mobility"],
    "degrees": ["B.Tech Computer Science Engineering"],
    "project_titles": ["Microservices E-Commerce Platform", "AI Loan Approval Agent", "Gram Panchayat Citizen Platform"],
    "voice_markers": ["architected", "fault-tolerant"],
    "strongest_domain": "backend",
}