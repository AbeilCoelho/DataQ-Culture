""" Autor: Abeil Coelho Júnior
Data de criação: 13/02/2023
Descrição: Projeto de mestrado
Versão: 1
Data de modificação: 14/02/2023 """

import collections
import os
import re
import pandas as pd


pasta_dados = "data"


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

    respostas = collections.Counter(respostas)
    resultado_final = respostas.most_common()[0]
    resultado_final = resultado_final[0]

    if negativo == 1:
        resultado_final = not resultado_final
    else:
        pass

    return resultado_final


def verificador(regex, valor, negativo, tipo, nome_regra, museu, metadado, id):
    valor = str(valor)

    if valor == "<-99>":
        resposta = False
        return resposta
    else:
        if nome_regra == "Fazer uso de vocabulário controlado":
            controlados = pd.read_csv(os.path.join(id), index_col=0)
            controlados_check = controlados.query(
                "Campos_Ajutados == '{}'".format(metadado)
            )
            if controlados_check.shape[0] == 0:
                resposta = False
            else:
                resposta = True
            return resposta

        if nome_regra == "Usar o mesmo idioma do catálogo":
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
