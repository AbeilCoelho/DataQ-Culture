""" Autor: Abeil Coelho Júnior
Data de criação: 13/02/2023
Descrição: Projeto de mestrado
Versão: 1
Data de modificação: 15/02/2023 """

import csv
import os
import json
#from fileinput import filename
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from werkzeug.utils import secure_filename
from flask import Flask, render_template, session, send_file, url_for, request, abort, redirect
import pandas as pd
import magic
from analisador import verificador

app = Flask(__name__)
app.secret_key = "1skrLdKMnX'dZ{0#XEuS+r"
app.config["UPLOAD_EXTENSIONS"] = ['.csv', '.CSV']
app.config["UPLOAD_PATH"] = "uploads"
PASTA_DADOS = "data"
arquivo_crosswalks = os.path.join(PASTA_DADOS, "alinhamentos\\alinhamentos.parquet")

esquema_cco = ['Work Type',
'Title',
'Creator',
'Measurements',
'Measurements_Altura',
'Measurements_Largura',
'Measurements_profundidade',
'Measurements_espessura',
'Measurements_diametro',
'Measurements_peso',
'Materials and Techniques',
'Physical Description',
'Date',
'Creation Location',
'Class',
'Description',
'Other Descriptive Notes',
'Related Works',
'Inscription',
'Location']

try:
    alinhamentos = pd.read_parquet(arquivo_crosswalks)
except:
    data = [["0", "0", 0]]
    alinhamentos = pd.DataFrame(data, columns = ['nome', 'colunas', 'id'])
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
        if nome_arquivo_do_usuario != '':
            extensao_arquivo = os.path.splitext(nome_arquivo_do_usuario)[1]
            if extensao_arquivo not in app.config["UPLOAD_EXTENSIONS"]:
                abort(400)

        caminho_arquivo_usuario= os.path.join(app.config["UPLOAD_PATH"], nome_arquivo_do_usuario)
        session["caminho_arquivo"] = caminho_arquivo_usuario
        session["nome_arquivo"] = nome_arquivo_do_usuario

        # Salvando arquivo do usuário
        arquivo_enviado_pelo_usuario.save(caminho_arquivo_usuario)

        # Detectar encoding e delimitador do arquivo do usuário
        try:
            blob = open(caminho_arquivo_usuario, 'rb').read()
            magic_mime = magic.Magic(mime_encoding=True)
            encoding = magic_mime.from_buffer(blob)
            session["encoding"] = encoding
            #print("encoding:", encoding)

            sniffer = csv.Sniffer()
            with open(caminho_arquivo_usuario, encoding=encoding) as verificar_delimitador:
                try:
                    delimitador = sniffer.sniff(verificar_delimitador.read(1240)).delimiter
                    session["delimitador"] = delimitador
                    #print("delimitador:", delimitador)
                except csv.Error:
                    os.remove(caminho_arquivo_usuario)
                    abort(400)
                    #return render_template("processamento-falha.html", nome_arquivo=nome_arquivo_do_usuario)

            return render_template("processamento-ok.html", nome_arquivo=nome_arquivo_do_usuario, encoding=encoding, delimitador=delimitador)
        except:
            os.remove(caminho_arquivo_usuario)
            return render_template("processamento-falha.html", nome_arquivo=nome_arquivo_do_usuario)



@app.route("/alinhamento", methods=["GET", "POST"])
def alinhamento():
    if request.method == "GET":

        dados_alinhamento = pd.read_csv(session["caminho_arquivo"], sep=session["delimitador"], encoding=session["encoding"], nrows=2)
        dados_alinhamento = dados_alinhamento.loc[:,~dados_alinhamento.columns.str.match("Unnamed")]
        cabecalho_usuario_lista = dados_alinhamento.columns.tolist()

        # Salvar o cabeçalho do arquivo na seção
        session["cabecalho_usuario_lista"] = cabecalho_usuario_lista

        cabecalho_usuario = {k: v for v, k in enumerate(cabecalho_usuario_lista)}

        # Verificar se crosswalk já existe
        key_cabecalho_usuario = ''.join(cabecalho_usuario_lista)
        key_cabecalho_usuario.replace(" ", "_")

        try:
            lista_pretendentes_crosswalk = pd.read_parquet(arquivo_crosswalks)
            lista_pretendentes_crosswalk = lista_pretendentes_crosswalk.query("colunas == '{}'".format(key_cabecalho_usuario))
            lista_pretendentes_crosswalk = lista_pretendentes_crosswalk.set_index('nome').to_dict()['id']

        except:
            lista_pretendentes_crosswalk = []


        return render_template("alinhamento.html", cabecalho_usuario=cabecalho_usuario, file_name=session['nome_arquivo'], esquema_cco=esquema_cco, lista_pretendentes_crosswalk=lista_pretendentes_crosswalk)

    if request.method == "POST":
        novo_crosswalk = request.form.items()
        crosswalk = []
        crosswalk_vocabulario = []

        for indice, valor in novo_crosswalk:
            if "vocabulario_controlado" in indice:
                crosswalk_vocabulario.append(valor)
            else:
                crosswalk.append(valor)



        key_cabecalho_usuario = ''.join(session["cabecalho_usuario_lista"])
        key_cabecalho_usuario.replace(" ", "_")

        nome_crosswalk = crosswalk[0]


        # Remover crosswalk com mesmo nome e colunas
        croswalks_salvos = pd.read_parquet(arquivo_crosswalks)

        croswalks_salvos = croswalks_salvos.query("colunas != '{}' or nome != '{}'".format(key_cabecalho_usuario, nome_crosswalk))

        novo_id = int(croswalks_salvos['id'].max()) + 1


        novo_crosswalk = pd.DataFrame([[nome_crosswalk, key_cabecalho_usuario, novo_id]], columns=['nome','colunas','id'])

        frames = [croswalks_salvos, novo_crosswalk]
        croswalks_salvos = pd.concat(frames)
        croswalks_salvos.to_parquet(arquivo_crosswalks)

        #Remover título do alinhamento
        crosswalk.pop(0)

        # Criar dicionário com cabeçalho antigo e novo
        crosswalk = dict(map(lambda i,j : (i,j) , session["cabecalho_usuario_lista"], crosswalk))


        print("crosswalk_vocabulario_antes:", crosswalk_vocabulario)
        crosswalk_vocabulario = list(map(lambda x: crosswalk.get(x, x), crosswalk_vocabulario))
        print("crosswalk_vocabulario_depois:", crosswalk_vocabulario)

        # Salvar alinhamento com nome de colunas antes e depois
        caminho_crosswalk = os.path.join(PASTA_DADOS, "alinhamentos", str(novo_id))
        with open(caminho_crosswalk, 'w') as arquivo_crosswalk:
            arquivo_crosswalk.write(json.dumps(crosswalk))

        # Salvar colunas com indicação de usu de vocabulário controlado
        caminho_crosswalk_vocabulario = os.path.join(PASTA_DADOS,"alinhamentos", str(novo_id)+"_vocabulario" )
        crosswalk_vocabulario = pd.DataFrame(crosswalk_vocabulario, columns = ['Campos_Ajutados'])
        crosswalk_vocabulario.to_csv(caminho_crosswalk_vocabulario)

        session["caminho_crosswalk"] = caminho_crosswalk

        return redirect(url_for('processamento'))

@app.route("/recuperar_alinhamento", methods=["POST"])
def recuperar_alinhamento():
    if request.method == "POST":
        ind_rec = request.form.get('ind_rec', None)
        recuperacao = request.form.get('recuperacao', None)
        nome_rec = request.form.get('nome_rec', None)

        if ind_rec == "2":


            caminho_crosswalk = os.path.join(PASTA_DADOS, "alinhamentos", recuperacao)
            with open(caminho_crosswalk) as crosswalk_salvo:
                crosswalk_salvo = crosswalk_salvo.read()
            print("crosswalk_salvo:", crosswalk_salvo)
            crosswalk_salvo = json.loads(crosswalk_salvo)

            recuperacao = recuperacao + "_vocabulario"
            recuperacao = os.path.join(PASTA_DADOS, "alinhamentos", recuperacao)
            caminho_crosswalk_vocabulario = pd.read_csv(recuperacao, index_col=0)
            caminho_crosswalk_vocabulario = caminho_crosswalk_vocabulario['Campos_Ajutados'].tolist()

            return render_template("editar_alinhamento.html", esquema_cco=esquema_cco, cabecalho_usuario=crosswalk_salvo, nome_crosswalk=nome_rec, caminho_crosswalk_vocabulario=caminho_crosswalk_vocabulario)

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

            return redirect(url_for('alinhamento'))


@app.route("/processamento", methods=["GET", "POST"])
def processamento():

    try:
        print(session["caminho_crosswalk"])
    except:
        recuperacao = request.form.get('recuperacao', None)
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
    cco_crosswalked.remove('Não utilizar')

    resultado_colecao = pd.DataFrame()

    # Lendo dados do usuário
    avaliacao_dados = pd.read_csv(session["caminho_arquivo"], sep=session["delimitador"], encoding=session["encoding"])
    avaliacao_dados = avaliacao_dados.loc[:,~avaliacao_dados.columns.str.match("Unnamed")]
    avaliacao_dados.rename(columns=crosswalk_recuperado, inplace=True)

    # Tratando dados do usuário
    avaliacao_dados = avaliacao_dados.loc[:, ~avaliacao_dados.columns.str.startswith('Não utilizar')]
    avaliacao_dados = avaliacao_dados.fillna("<-99>")
    tamanho_total = avaliacao_dados.shape[0]

    # Iniciando loops
    for metadado in cco_crosswalked:
        print("\n\n", metadado)

        # Selecionar regras aplicaveis ao elemento de metadado
        regras_aplicaveis = regras_cco[regras_cco.iloc[:,1].str.contains(metadado)]

        # Selecionar coluna correspondente ao metadado
        coluna_foco = pd.DataFrame()
        coluna_foco["foco"] = avaliacao_dados[metadado]

        for index_regras, row_regras in regras_aplicaveis.iterrows():
            nome_regra = row_regras.iloc[0]
            regex = row_regras.iloc[2]
            ind_negativo = row_regras.iloc[3]
            tipo = row_regras.iloc[4]

            avaliacoes = []

            print("Nome da regra:",nome_regra,"\nExpressão:", regex,"\nNegação:", ind_negativo, "\nTipo:", tipo)

            # Loop para cada registro presenta na coluna do metadado
            for index_dado, row_dado in coluna_foco.iterrows():
                dado_descricional = row_dado[0]

                avaliacao = verificador(regex, dado_descricional, ind_negativo, tipo, nome_regra, session["nome_arquivo"], metadado, acervo_id)
                avaliacoes.append(avaliacao)

            resultado_geral = pd.DataFrame({'Avaliacao': avaliacoes, "Dado": coluna_foco["foco"], "Colecao": session["nome_arquivo"], "Campo_Metadado": metadado, "Regra": nome_regra, "Regex": regex, "Total": tamanho_total})
            frames = [resultado_colecao, resultado_geral]
            resultado_colecao = pd.concat(frames)

        del coluna_foco

    resultado_colecao = resultado_colecao.reset_index()
    resultado_colecoes_data = (resultado_colecao.groupby(["Colecao", "Regra", "Campo_Metadado", "Avaliacao", "Regex", "Total"]).agg(
                resultado=("Avaliacao", "count")).reset_index())

    resultado_colecoes_data = resultado_colecoes_data.pivot(
                index=["Colecao", "Campo_Metadado", "Regra", "Total"], columns=["Avaliacao"], values="resultado")
    resultado_colecoes_data = resultado_colecoes_data.reset_index()

    resultado_colecoes_data = resultado_colecoes_data.rename(columns={False: "0", True: "1"})
    resultado_colecoes_data = resultado_colecoes_data.fillna(0)
    resultados_preliminares = pd.merge(resultado_colecoes_data, dimencoes, how="left", on="Campo_Metadado")
    resultados_preliminares = resultados_preliminares[["Colecao", "Dimensão", "Campo_Metadado", "Regra", "0", "1", "Total"]]
    resultados_preliminares = resultados_preliminares.sort_values(by=["Dimensão", "Campo_Metadado"]).reset_index(drop=True)

    nome_arquivo = session["nome_arquivo"] + ".xlsx"
    nome_arquivo = os.path.join(PASTA_DADOS, nome_arquivo)
    session["arquivo_download"] = nome_arquivo
    #session['nome_arquivo'] = nome_arquivo

    resultados_preliminares.to_excel(nome_arquivo)

    adequacao_por_regras = (resultados_preliminares.groupby(["Colecao", "Dimensão", "Campo_Metadado", "Regra"]).agg(
    zeros=("0", "sum"),
    ums=("1", "sum")).reset_index())

    adequacao_por_regras_clean = adequacao_por_regras[["Colecao", "Dimensão", "Campo_Metadado", "Regra", "ums", "zeros"]]

    adequacao_por_dimensao = (adequacao_por_regras_clean.groupby(["Colecao", "Dimensão"]).agg(
        zeros=("zeros", "sum"),
        ums=("ums", "sum")).reset_index())

    adequacao_por_dimensao["Total"] = adequacao_por_dimensao["zeros"] + adequacao_por_dimensao["ums"]
    adequacao_por_dimensao["Adequacao"] = (adequacao_por_dimensao["ums"]/adequacao_por_dimensao["Total"]) * 100

    adequacao_por_dimensao = adequacao_por_dimensao[["Colecao", "Dimensão", "Adequacao"]]
    adequacao_por_dimensao = adequacao_por_dimensao.round({'Adequacao': 0})
    adequacao_por_dimensao = adequacao_por_dimensao.sort_values(by=["Dimensão", "Colecao"])
    sns.set(rc={'figure.figsize':(5,1)})
    adequacao_por_dimensao = adequacao_por_dimensao.pivot(index='Colecao', columns='Dimensão', values='Adequacao')
    sns.heatmap(adequacao_por_dimensao, cmap="Blues", annot=True, fmt="g", linewidths=.2, annot_kws={"fontsize":12}).set(ylabel=None)
    plt.tick_params(axis='y', which='major', labelsize=9, direction="in")
    nome_imagem = "imagem.png"
    caminho_imagem = os.path.join("static", nome_imagem)
    plt.savefig(caminho_imagem, bbox_inches="tight", transparent=True) 


    return render_template("report.html", imagem=nome_imagem)

@app.route("/download", methods=["GET"])
def download():

    arquivo = session["arquivo_download"]

    return send_file(arquivo, as_attachment=True)

if __name__ == "__main__":
    #app.run(host="data-q-culture.vercel.app", port=8000, debug=True)
    app.run(host="10.150.109.25", port=8000, debug=True)