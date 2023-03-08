""" Autor: Abeil Coelho Júnior
Data de criação: 13/02/2023
Descrição: Projeto de mestrado DataQ-cultura
Versão: 1
Data de modificação: 08/03/2023 """

import csv
import os
import json
from werkzeug.utils import secure_filename
from flask import (
    Flask,
    render_template,
    session,
    send_file,
    url_for,
    request,
    abort,
    redirect,
)
import pandas as pd
from chardet.universaldetector import UniversalDetector
from analisador import verificador


app = Flask(__name__)
if os.getenv("COLAB_RELEASE_TAG"):
	print("Sendo executado no Google Colab :D\n")
	app = Flask(__name__, template_folder='DataQ-Culture/templates')


app.secret_key = "1skrLdKMnX'dZ{0#XEuS+r"
app.config["UPLOAD_EXTENSIONS"] = [".csv", ".CSV"]
app.config["UPLOAD_PATH"] = "uploads"
PASTA_DADOS = "./data"
arquivo_crosswalks = os.path.join(PASTA_DADOS, "alinhamentos/alinhamentos.parquet")

esquema_cco = [
    "Work Type",
    "Title",
    "Creator",
    "Measurements",
    "Measurements_Altura",
    "Measurements_Largura",
    "Measurements_Profundidade",
    "Measurements_Espessura",
    "Measurements_Diametro",
    "Measurements_Peso",
    "Materials and Techniques",
    "Physical Description",
    "Date",
    "Creation Location",
    "Class",
    "Description",
    "Other Descriptive Notes",
    "Related Works",
    "Inscription",
    "Location",
]


try:
    alinhamentos = pd.read_parquet(arquivo_crosswalks)
except:
    data = [["0", "0", 0]]
    alinhamentos = pd.DataFrame(data, columns=["nome", "colunas", "id"])
    alinhamentos.to_parquet(arquivo_crosswalks)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST", "GET"])
def upload():
    if request.method == "GET":
        return render_template("upload.html")

    if request.method == "POST":
        arquivo_enviado_pelo_usuario = request.files["file"]

        # Verificar se o conteúdo que o usuário está subindo é seguro
        nome_arquivo_do_usuario = secure_filename(arquivo_enviado_pelo_usuario.filename)
        if nome_arquivo_do_usuario != "":
            extensao_arquivo = os.path.splitext(nome_arquivo_do_usuario)[1]
            if extensao_arquivo not in app.config["UPLOAD_EXTENSIONS"]:
                abort(400)

        caminho_arquivo_usuario = os.path.join(
            app.config["UPLOAD_PATH"], nome_arquivo_do_usuario
        )
        session["caminho_arquivo"] = caminho_arquivo_usuario
        session["nome_arquivo"] = nome_arquivo_do_usuario

        # Salvando arquivo do usuário
        arquivo_enviado_pelo_usuario.save(caminho_arquivo_usuario)

        # Detectar encoding e delimitador do arquivo do usuário
        try:
            detector = UniversalDetector()
            for line in open(session["caminho_arquivo"], "rb"):
                detector.feed(line)
                if detector.done: break

            detector.close()
            encoding = detector.result.get('encoding')
            session["encoding"] = encoding
            print("encoding:", encoding)

            # Verificar se o arquivo é curso demais
            num_lines = sum(1 for line in open(session["caminho_arquivo"], "rb").read())
            if num_lines < 2:
                print("O arquivo é muito curto.")
                raise

            delimitadores = [
                "\x00",
                "\x01",
                "^",
                ":",
                ",",
                "\t",
                ":",
                ";",
                "|",
                "~",
                " ",
            ]

            with open(
                session["caminho_arquivo"], encoding=encoding
            ) as verificar_delimitador:
                line = next(verificar_delimitador)
                dialect = csv.Sniffer().sniff(line, delimitadores)
                delimitador = dialect.delimiter
                print("delimitador:", delimitador)

                session["delimitador"] = delimitador

            return render_template(
                "processamento-ok.html",
                nome_arquivo=session["nome_arquivo"],
                encoding=encoding,
                delimitador=delimitador,
            )
        except:
            os.remove(session["caminho_arquivo"])
            return render_template(
                "processamento-falha.html", nome_arquivo=session["nome_arquivo"]
            )


@app.route("/alinhamento", methods=["GET", "POST"])
def alinhamento():
    if request.method == "GET":

        dados_alinhamento = pd.read_csv(
            session["caminho_arquivo"],
            sep=session["delimitador"],
            encoding=session["encoding"],
            nrows=2,
        )
        dados_alinhamento = dados_alinhamento.loc[
            :, ~dados_alinhamento.columns.str.match("Unnamed")
        ]
        cabecalho_usuario_lista = dados_alinhamento.columns.tolist()

        # Salvar o cabeçalho do arquivo na seção
        session["cabecalho_usuario_lista"] = cabecalho_usuario_lista

        cabecalho_usuario = {k: v for v, k in enumerate(cabecalho_usuario_lista)}

        # Verificar se crosswalk já existe
        key_cabecalho_usuario = "".join(cabecalho_usuario_lista)
        key_cabecalho_usuario.replace(" ", "_")

        try:
            lista_pretendentes_crosswalk = pd.read_parquet(arquivo_crosswalks)
            lista_pretendentes_crosswalk = lista_pretendentes_crosswalk.query(
                "colunas == '{}'".format(key_cabecalho_usuario)
            )
            lista_pretendentes_crosswalk = lista_pretendentes_crosswalk.set_index(
                "nome"
            ).to_dict()["id"]

        except:
            lista_pretendentes_crosswalk = []

        return render_template(
            "alinhamento.html",
            cabecalho_usuario=cabecalho_usuario,
            file_name=session["nome_arquivo"],
            esquema_cco=esquema_cco,
            lista_pretendentes_crosswalk=lista_pretendentes_crosswalk,
        )

    if request.method == "POST":
        novo_crosswalk = request.form.items()
        crosswalk = []
        crosswalk_vocabulario = []

        for indice, valor in novo_crosswalk:
            if "vocabulario_controlado" in indice:
                crosswalk_vocabulario.append(valor)
            else:
                crosswalk.append(valor)

        key_cabecalho_usuario = "".join(session["cabecalho_usuario_lista"])
        key_cabecalho_usuario.replace(" ", "_")

        nome_crosswalk = crosswalk[0]

        # Remover crosswalk com mesmo nome e colunas
        croswalks_salvos = pd.read_parquet(arquivo_crosswalks)

        croswalks_salvos = croswalks_salvos.query(
            "colunas != '{}' or nome != '{}'".format(
                key_cabecalho_usuario, nome_crosswalk
            )
        )

        novo_id = int(croswalks_salvos["id"].max()) + 1

        novo_crosswalk = pd.DataFrame(
            [[nome_crosswalk, key_cabecalho_usuario, novo_id]],
            columns=["nome", "colunas", "id"],
        )

        frames = [croswalks_salvos, novo_crosswalk]
        croswalks_salvos = pd.concat(frames)
        croswalks_salvos.to_parquet(arquivo_crosswalks)

        # Remover título do alinhamento
        crosswalk.pop(0)

        # Criar dicionário com cabeçalho antigo e novo
        crosswalk = dict(
            map(lambda i, j: (i, j), session["cabecalho_usuario_lista"], crosswalk)
        )

        print("crosswalk_vocabulario_antes:", crosswalk_vocabulario)
        crosswalk_vocabulario = list(
            map(lambda x: crosswalk.get(x, x), crosswalk_vocabulario)
        )
        print("crosswalk_vocabulario_depois:", crosswalk_vocabulario)

        # Salvar alinhamento com nome de colunas antes e depois
        caminho_crosswalk = os.path.join(PASTA_DADOS, "alinhamentos", str(novo_id))
        with open(caminho_crosswalk, "w") as arquivo_crosswalk:
            arquivo_crosswalk.write(json.dumps(crosswalk))

        # Salvar colunas com indicação de usu de vocabulário controlado
        caminho_crosswalk_vocabulario = os.path.join(
            PASTA_DADOS, "alinhamentos", str(novo_id) + "_vocabulario"
        )
        crosswalk_vocabulario = pd.DataFrame(
            crosswalk_vocabulario, columns=["Campos_Ajutados"]
        )
        crosswalk_vocabulario.to_csv(caminho_crosswalk_vocabulario)

        session["caminho_crosswalk"] = caminho_crosswalk

        return redirect(url_for("processamento"))


@app.route("/recuperar_alinhamento", methods=["POST"])
def recuperar_alinhamento():
    if request.method == "POST":
        ind_rec = request.form.get("ind_rec", None)
        recuperacao = request.form.get("recuperacao", None)
        nome_rec = request.form.get("nome_rec", None)

        if ind_rec == "2":

            caminho_crosswalk = os.path.join(PASTA_DADOS, "alinhamentos", recuperacao)
            with open(caminho_crosswalk) as crosswalk_salvo:
                crosswalk_salvo = crosswalk_salvo.read()
            print("crosswalk_salvo:", crosswalk_salvo)
            crosswalk_salvo = json.loads(crosswalk_salvo)

            recuperacao = recuperacao + "_vocabulario"
            recuperacao = os.path.join(PASTA_DADOS, "alinhamentos", recuperacao)
            caminho_crosswalk_vocabulario = pd.read_csv(recuperacao, index_col=0)
            caminho_crosswalk_vocabulario = caminho_crosswalk_vocabulario[
                "Campos_Ajutados"
            ].tolist()

            return render_template(
                "editar_alinhamento.html",
                esquema_cco=esquema_cco,
                cabecalho_usuario=crosswalk_salvo,
                nome_crosswalk=nome_rec,
                caminho_crosswalk_vocabulario=caminho_crosswalk_vocabulario,
            )

        # Remover alinhamento
        if ind_rec == "3":

            # Exluir arquivo
            caminho_crosswalk = os.path.join(PASTA_DADOS, "alinhamentos", recuperacao)
            os.remove(caminho_crosswalk)

            recuperacao = recuperacao + "_vocabulario"
            caminho_crosswalk = os.path.join(PASTA_DADOS, "alinhamentos", recuperacao)
            os.remove(caminho_crosswalk)

            # Remove registro
            croswalks_salvos = pd.read_parquet(arquivo_crosswalks)
            croswalks_salvos = croswalks_salvos.query("nome != '{}'".format(nome_rec))
            croswalks_salvos.to_parquet(arquivo_crosswalks)

            return redirect(url_for("alinhamento"))


@app.route("/processamento", methods=["GET", "POST"])
def processamento():

    try:
        # print(session["caminho_crosswalk"])
        pass
    except:
        recuperacao = request.form.get("recuperacao", None)
        caminho_crosswalk = os.path.join(PASTA_DADOS, "alinhamentos", str(recuperacao))
        session["caminho_crosswalk"] = caminho_crosswalk

    # Carregando dados para processamento
    regras_cco = pd.read_excel(os.path.join(PASTA_DADOS, "fontes\\Base_Regex.xlsx"))
    dimencoes = pd.read_excel(os.path.join(PASTA_DADOS, "fontes\\Dimencoes.xlsx"))

    # Carregando arquivo com o crosswalk
    with open(session["caminho_crosswalk"]) as crosswalk_recuperado:
        crosswalk_recuperado = crosswalk_recuperado.read()
    crosswalk_recuperado = json.loads(crosswalk_recuperado)

    acervo_id = session["caminho_crosswalk"] + "_vocabulario"

    cco_crosswalked = list(crosswalk_recuperado.values())
    cco_crosswalked = list(set(cco_crosswalked))
    cco_crosswalked.remove("Não utilizar")

    resultado_colecao = pd.DataFrame()

    # Lendo dados do usuário
    avaliacao_dados = pd.read_csv(
        session["caminho_arquivo"],
        sep=session["delimitador"],
        encoding=session["encoding"],
    )
    avaliacao_dados = avaliacao_dados.loc[
        :, ~avaliacao_dados.columns.str.match("Unnamed")
    ]
    avaliacao_dados.rename(columns=crosswalk_recuperado, inplace=True)

    # Tratando dados do usuário
    avaliacao_dados = avaliacao_dados.loc[
        :, ~avaliacao_dados.columns.str.startswith("Não utilizar")
    ]
    avaliacao_dados = avaliacao_dados.fillna("<-99>")
    tamanho_total = avaliacao_dados.shape[0]

    # Iniciando loops
    for metadado in cco_crosswalked:
        # print("\n\n", metadado)

        # Selecionar regras aplicaveis ao elemento de metadado
        regras_aplicaveis = regras_cco[regras_cco.iloc[:, 1].str.contains(metadado)]

        # Selecionar coluna correspondente ao metadado
        coluna_foco = pd.DataFrame()
        coluna_foco["foco"] = avaliacao_dados[metadado]

        for index_regras, row_regras in regras_aplicaveis.iterrows():
            nome_regra = row_regras.iloc[0]
            regex = row_regras.iloc[2]
            ind_negativo = row_regras.iloc[3]
            tipo = row_regras.iloc[4]

            avaliacoes = []

            # print("Nome da regra:",nome_regra,"\nExpressão:", regex,"\nNegação:", ind_negativo, "\nTipo:", tipo)

            # Loop para cada registro presenta na coluna do metadado
            for index_dado, row_dado in coluna_foco.iterrows():
                dado_descricional = row_dado[0]

                avaliacao = verificador(
                    regex,
                    dado_descricional,
                    ind_negativo,
                    tipo,
                    nome_regra,
                    session["nome_arquivo"],
                    metadado,
                    acervo_id,
                )
                avaliacoes.append(avaliacao)

            resultado_geral = pd.DataFrame(
                {
                    "Avaliacao": avaliacoes,
                    "Dado": coluna_foco["foco"],
                    "Colecao": session["nome_arquivo"],
                    "Campo_Metadado": metadado,
                    "Regra": nome_regra,
                    "Regex": regex,
                    "Total": tamanho_total,
                }
            )
            frames = [resultado_colecao, resultado_geral]
            resultado_colecao = pd.concat(frames)

        del coluna_foco

    resultado_colecao = resultado_colecao.reset_index()
    resultado_colecoes_data = (
        resultado_colecao.groupby(
            ["Colecao", "Regra", "Campo_Metadado", "Dado", "Avaliacao", "Regex", "Total"]
        )
        .agg(resultado=("Avaliacao", "count"))
        .reset_index()
    )

    resultado_colecoes_data = resultado_colecoes_data.pivot(
        index=["Colecao", "Campo_Metadado", "Regra", "Dado", "Total"],
        columns=["Avaliacao"],
        values="resultado",
    )
    resultado_colecoes_data = resultado_colecoes_data.reset_index()

    resultado_colecoes_data = resultado_colecoes_data.rename(
        columns={False: "0", True: "1"}
    )
    resultado_colecoes_data = resultado_colecoes_data.fillna(0)
    resultados_preliminares = pd.merge(
        resultado_colecoes_data, dimencoes, how="left", on="Campo_Metadado"
    )
    resultados_preliminares = resultados_preliminares[
        ["Colecao", "Dimensão", "Campo_Metadado", "Regra", "Dado", "0", "1", "Total"]
    ]
    resultados_preliminares = resultados_preliminares.sort_values(
        by=["Dimensão", "Campo_Metadado"]
    ).reset_index(drop=True)

    nome_arquivo = session["nome_arquivo"] + ".xlsx"
    nome_arquivo = os.path.join(PASTA_DADOS, nome_arquivo)
    session["arquivo_download"] = nome_arquivo
    # session['nome_arquivo'] = nome_arquivo

    resultados_preliminares.to_excel(nome_arquivo)

    adequacao_por_regras = (
        resultados_preliminares.groupby(
            ["Colecao", "Dimensão", "Campo_Metadado", "Regra"]
        )
        .agg(zeros=("0", "sum"), ums=("1", "sum"))
        .reset_index()
    )

    adequacao_por_regras_clean = adequacao_por_regras[
        ["Colecao", "Dimensão", "Campo_Metadado", "Regra", "ums", "zeros"]
    ]

    # Adequação total
    adequacao_total = (
        adequacao_por_regras_clean.groupby(["Colecao"])
        .agg(zeros=("zeros", "sum"), ums=("ums", "sum"))
        .reset_index()
    )

    adequacao_total["Total"] = adequacao_total["zeros"] + adequacao_total["ums"]
    adequacao_total["Adequacao"] = (
        adequacao_total["ums"] / adequacao_total["Total"]
    ) * 100
    session["adequacao_total"] = adequacao_total["Adequacao"].astype("int").to_list()[0]

    # Adequação por dimensão
    adequacao_por_dimensao = (
        adequacao_por_regras_clean.groupby(["Colecao", "Dimensão"])
        .agg(zeros=("zeros", "sum"), ums=("ums", "sum"))
        .reset_index()
    )

    adequacao_por_dimensao["Total"] = (
        adequacao_por_dimensao["zeros"] + adequacao_por_dimensao["ums"]
    )
    adequacao_por_dimensao["Adequacao"] = (
        adequacao_por_dimensao["ums"] / adequacao_por_dimensao["Total"]
    ) * 100

    adequacao_por_dimensao = adequacao_por_dimensao[["Dimensão", "Adequacao"]]
    adequacao_por_dimensao = adequacao_por_dimensao.sort_values(by=["Dimensão"])

    session["adequacao_por_dimensao_dimencoes"] = adequacao_por_dimensao[
        "Dimensão"
    ].to_list()
    session["adequacao_por_dimensao_adequacao"] = (
        adequacao_por_dimensao["Adequacao"].astype("int").to_list()
    )

    adequacao_por_dimensao = adequacao_por_dimensao.query("Adequacao != 100")

    adequacao_por_dimensao = adequacao_por_dimensao.sort_values(by=["Dimensão"])
    analise_dimensoes = adequacao_por_dimensao["Dimensão"].to_list()

    dimensoes = {"dimensao": []}

    # "Dimensão": ["Campos"]
    campos = {}

    # "Dimensão": ["valores campos"]
    valores_campos = {}

    # "Campos": ["Regras"]
    regras = {}

    for x in analise_dimensoes:
        dimensoes["dimensao"].append(x)

        avaliacao = adequacao_por_regras_clean.query("Dimensão == '{}'".format(x))
        avaliacao = (
            avaliacao.groupby(["Colecao", "Dimensão", "Campo_Metadado"])
            .agg(zeros=("zeros", "sum"), ums=("ums", "sum"))
            .reset_index()
        )

        avaliacao["Total"] = avaliacao["zeros"] + avaliacao["ums"]
        avaliacao["Adequacao"] = (avaliacao["ums"] / avaliacao["Total"]) * 100
        avaliacao = avaliacao.sort_values(by=["Adequacao"], ascending=True)

        # avaliacao = avaliacao.query("Adequacao != 100")

        campos_list = avaliacao["Campo_Metadado"].to_list()
        valores_campos_list = avaliacao["Adequacao"].astype("int").to_list()

        campos[x] = campos_list
        valores_campos[x] = valores_campos_list

        for campo in campos_list:
            # print(campo)
            avaliacao1 = adequacao_por_regras_clean.query(
                "Dimensão == '{}' and Campo_Metadado == '{}'".format(x, campo)
            )
            avaliacao1 = (
                avaliacao1.groupby(["Regra"])
                .agg(zeros=("zeros", "sum"), ums=("ums", "sum"))
                .reset_index()
            )

            avaliacao1["Total"] = avaliacao1["zeros"] + avaliacao1["ums"]
            avaliacao1["Adequacao"] = (avaliacao1["ums"] / avaliacao1["Total"]) * 100

            avaliacao1 = avaliacao1.query("Adequacao != 100")
            avaliacao1 = avaliacao1.sort_values(by=["Adequacao"], ascending=True)

            regra = avaliacao1["Regra"].to_list()
            # valores_regras = avaliacao1["Adequacao"].astype('int').to_list()

            regras[campo] = regra

    session["dimensoes"] = dimensoes
    session["campos"] = campos
    session["valores_campos"] = valores_campos
    session["regras"] = regras

    return redirect(url_for("relatorio"))
    # return render_template("report.html", imagem=nome_imagem)


@app.route("/relatorio", methods=["GET"])
def relatorio():

    # session.clear()

    return render_template(
        "report.html",
        adequacao_total=session["adequacao_total"],
        adequacao_por_dimensao_adequacao=session["adequacao_por_dimensao_adequacao"],
        adequacao_por_dimensao_dimencoes=session["adequacao_por_dimensao_dimencoes"],
        dimensoes=session["dimensoes"],
        campos=session["campos"],
        valores_campos=session["valores_campos"],
        regras=session["regras"],
    )


@app.route("/download", methods=["GET"])
def download():

    arquivo = session["arquivo_download"]
    # session.clear()
    return send_file(arquivo, as_attachment=True)


if __name__ == "__main__":
    app.run()
