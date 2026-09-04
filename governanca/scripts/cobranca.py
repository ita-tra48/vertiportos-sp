import argparse
import json
import os
import smtplib
import sys
from datetime import date, datetime, timedelta
from email.message import EmailMessage

import banco

SITE = "https://ita-tra48.github.io/vertiportos-sp/"
JANELA_DIAS = 7
FAIXAS = ("atrasada", "hoje", "semana", "depois", "sem prazo")
TITULOS = {"atrasada": "ATRASADA", "hoje": "PARA HOJE",
           "semana": "ESTA SEMANA", "depois": "MAIS ADIANTE",
           "sem prazo": "SEM PRAZO"}


def _prazo(valor):
    if not valor:
        return None
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if isinstance(valor, datetime):
        return valor.date()
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def faixa(prazo, hoje):
    if prazo is None:
        return "sem prazo"
    if prazo < hoje:
        return "atrasada"
    if prazo == hoje:
        return "hoje"
    if prazo <= hoje + timedelta(days=JANELA_DIAS):
        return "semana"
    return "depois"


def coleta(con, hoje):
    travas = {}
    for tid, titulo in con.execute(
            "SELECT a.destino, p.titulo FROM aresta a JOIN pendencia p "
            "ON p.id = a.origem WHERE a.relacao = 'bloqueia' "
            "AND p.status = 'aberta' ORDER BY a.destino, p.id").fetchall():
        travas.setdefault(tid, []).append(titulo)
    por_resp = {}
    for tid, titulo, resp, prazo in con.execute(
            "SELECT id, titulo, resp, prazo FROM tarefa WHERE status = 'aberta' "
            "ORDER BY prazo NULLS LAST, id").fetchall():
        nome = (resp or "").strip()
        if not nome:
            continue
        p = _prazo(prazo)
        por_resp.setdefault(nome, []).append(
            {"id": tid, "titulo": titulo, "prazo": p,
             "faixa": faixa(p, hoje), "travas": travas.get(tid, [])})
    for tarefas in por_resp.values():
        tarefas.sort(key=lambda t: (FAIXAS.index(t["faixa"]),
                                    t["prazo"] or date.max, t["id"]))
    return por_resp


def corpo(nome, tarefas):
    linhas = [f"{nome}, o banco diz que estas tarefas continuam abertas.", ""]
    atual = None
    for t in tarefas:
        if t["faixa"] != atual:
            atual = t["faixa"]
            linhas.append(TITULOS[atual])
        quando = t["prazo"].strftime("%d/%m") if t["prazo"] else "  --  "
        linhas.append(f"  {quando}  {t['titulo']}")
        linhas.append(f"          {t['id']}")
        for trava in t["travas"]:
            linhas.append(f"          travada por: {trava}")
        linhas.append("")
    linhas.append(f"Fechar: ./gov fecha ID --resolucao \"...\"")
    linhas.append(f"Grafo:  {SITE}")
    linhas.append("")
    linhas.append("O que nao estiver no banco, nao aconteceu.")
    return "\n".join(linhas)


def assunto(tarefas):
    atrasadas = sum(1 for t in tarefas if t["faixa"] == "atrasada")
    n = len(tarefas)
    plural = "tarefa sua em aberto" if n == 1 else "tarefas suas em aberto"
    if not atrasadas:
        return f"TRA-48 — {n} {plural}"
    vencidas = "1 atrasada" if atrasadas == 1 else f"{atrasadas} atrasadas"
    return f"TRA-48 — {n} {plural}, {vencidas}"


def destinos(nome, emails):
    achado = emails.get(nome)
    if achado is None:
        chave = " ".join(nome.split()).casefold()
        for bruto, valor in emails.items():
            if " ".join(str(bruto).split()).casefold() == chave:
                achado = valor
                break
    if achado is None:
        return []
    if isinstance(achado, str):
        achado = achado.split(",")
    return [e.strip() for e in achado if str(e).strip()]


def mensagens(por_resp, emails):
    saida, sem_email = [], []
    for nome in sorted(por_resp):
        para = destinos(nome, emails)
        if not para:
            sem_email.append(nome)
            continue
        saida.append({"para": ", ".join(para), "nome": nome,
                      "assunto": assunto(por_resp[nome]),
                      "corpo": corpo(nome, por_resp[nome])})
    return saida, sem_email


def envia(msgs, remetente, senha, host, porta):
    with smtplib.SMTP(host, porta) as smtp:
        smtp.starttls()
        smtp.login(remetente, senha)
        for m in msgs:
            email = EmailMessage()
            email["From"] = remetente
            email["To"] = m["para"]
            email["Subject"] = m["assunto"]
            email.set_content(m["corpo"])
            smtp.send_message(email)


def main(argv=None):
    a = argparse.ArgumentParser(prog="cobranca")
    a.add_argument("--seco", action="store_true")
    args = a.parse_args(argv)

    hoje = date.today()
    por_resp = coleta(banco.conecta(somente_leitura=True), hoje)
    if not por_resp:
        print("nenhuma tarefa aberta: nada a enviar")
        return 0

    emails = json.loads(os.environ.get("EMAILS_JSON") or "{}")
    msgs, sem_email = mensagens(por_resp, emails)
    for nome in sem_email:
        print(f"aviso: {nome} tem tarefa aberta e nao tem email em EMAILS_JSON",
              file=sys.stderr)
    if not msgs:
        print("ninguem com tarefa aberta tem email cadastrado")
        return 0

    if args.seco:
        for m in msgs:
            print(f"--- {m['para']} | {m['assunto']}\n{m['corpo']}\n")
        return 0

    remetente = os.environ.get("SMTP_USUARIO", "").strip()
    senha = os.environ.get("SMTP_SENHA", "")
    if not remetente or not senha:
        print("cobranca: faltam SMTP_USUARIO e SMTP_SENHA", file=sys.stderr)
        return 2
    envia(msgs, remetente, senha,
          os.environ.get("SMTP_HOST", "smtp.gmail.com"),
          int(os.environ.get("SMTP_PORTA", "587")))
    print(f"enviados {len(msgs)} emails: "
          + ", ".join(m["nome"] for m in msgs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
