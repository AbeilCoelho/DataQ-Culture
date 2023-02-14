import pandas as pd
import numpy as np
import re
import collections

pd.options.mode.chained_assignment = None

def verificador_multivalor(regex, valores, negativo, tipo):
    respostas = []
    if tipo == "Match":
        for valor in valores:
            match = re.match(regex, valor)
            if match is not None:
                resposta = True    
            else:
                resposta = False
            respostas.append(resposta)
            del resposta
    else:
        for valor in valores:
            match = re.fullmatch(regex, valor)
            if match is not None:
                resposta = True    
            else:
                resposta = False
            respostas.append(resposta)
            del resposta
    
    respostas=collections.Counter(respostas)
    resultado_final = respostas.most_common()[0]
    resultado_final = resultado_final[0]
    
    if negativo == 1:
        resultado_final = not resultado_final
    else:
        pass
        
    return resultado_final

def verificador(regex, valor, negativo, tipo, nome_regra, museu, metadado):
    valor = str(valor)
    
    if valor == '<-99>':
        resposta = False
        return resposta
    else:
        if nome_regra == 'Fazer uso de vocabulário controlado':
            controlados = pd.read_excel("./Campos_com_vocabularios_controlados.xlsx", index_col=0)
            controlados_check = controlados.query("Colecao == '{}' and Campos_Ajutados == '{}'".format(museu, metadado))
            if controlados_check.shape[0] == 0:
                resposta = False
            else:
                resposta = True
            return resposta
        
        if nome_regra == 'Usar o mesmo idioma do catálogo':
            resposta = True
            return resposta
        
        if "|" in valor:
            valores = valor.split("|")
            resposta = verificador_multivalor(regex, valores, negativo, tipo)
            return resposta
        
        if ">" in valor:
            valor = valor.split("> ")[-1]
        
        
            
                
    if tipo == "Match":
        match = re.match(regex, valor)
    else:
        match = re.fullmatch(regex, valor)
        
    if match is not None:
        resposta = True    
    else:
        resposta = False

    if negativo == 1:
        resposta = not resposta

    return resposta

resultado_colecao = pd.DataFrame()

for museu in museus:
    tic()
#     acervo_avaliado = acervo_ibram.query("Nome_Acervo == '{}'".format(museu))
    acervo_avaliado = sampled_data.query("Nome_Acervo == '{}'".format(museu))
    print("\n\n############################################\n")
    print(museu)
    print("A coleção possui", acervo_avaliado.shape[0],"itens.")
    print("\n############################################\n\n")
    

    acervo_avaliado = acervo_avaliado.fillna("<-99>")
    #acervo_avaliado["Creator"].replace({"Não identificado": "<-99>"}, inplace=True)
    #acervo_avaliado["Creator"].replace({"Não identificada": "<-99>"}, inplace=True)
    #acervo_avaliado["Creator"].replace({"Ignorado": "<-99>"}, inplace=True)
    #acervo_avaliado["Creator"].replace({"Sem Autor": "<-99>"}, inplace=True)


    
    tamanho_total = acervo_avaliado.shape[0]

    # Loop para cada elemento de metadado
    for metadado in elementos_de_metadados:
        print("\n\n",metadado)

        # Selecionar regras aplicaveis ao elemento de metadado
        regras_aplicaveis = regras_cco[regras_cco.iloc[:,1].str.contains(metadado)]

        # Selecionar coluna correspondente ao metadado
        coluna_foco = pd.DataFrame()
        coluna_foco["foco"] = acervo_avaliado[metadado]

        # Loop para cada regra existente
        print("Quantidade de regras:",regras_aplicaveis.shape[0], "\n")
        print("==========================================================================================")
        
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

                avaliacao = verificador(regex, dado_descricional, ind_negativo, tipo, nome_regra, museu, metadado)
                avaliacoes.append(avaliacao)

            resultados_distintos = list(dict.fromkeys(avaliacoes))


            counter=collections.Counter(avaliacoes)
            print("Os resultados obtidos foram:",dict(counter),"\n")

            resultado_geral = pd.DataFrame({'Avaliacao': avaliacoes, "Dado": coluna_foco["foco"], "Colecao": museu, "Campo_Metadado": metadado, "Regra": nome_regra, "Regex": regex, "Total": tamanho_total})
            frames = [resultado_colecao, resultado_geral]
            resultado_colecao = pd.concat(frames)

            if len(resultados_distintos) == 1:
                print("==> Amostra", resultados_distintos[0],"\n")
                temp = resultado_geral.query("Avaliacao == {}".format(resultados_distintos[0]))
                print(temp["Dado"].sample(),'\n')
                
            else:
                print("==> Amostra", resultados_distintos[0],"\n")
                temp = resultado_geral.query("Avaliacao == {}".format(resultados_distintos[0]))
                print(temp["Dado"].sample(),'\n')

                print("==> Amostra", resultados_distintos[1])                
                temp = resultado_geral.query("Avaliacao == {}".format(resultados_distintos[1]))
                print(temp["Dado"].sample(),'\n')

            del resultado_geral, temp
            print("=======================================")
        del coluna_foco
    tac("Competou a coleção", museu)
    
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
nome_arquivo = session['nome_rec'] + ".xlsx"
resultados_preliminares.to_excel(os.path.join(pasta_dados, nome_arquivo))