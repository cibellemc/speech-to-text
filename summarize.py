from transformers import pipeline


def suimmarize(text_content):
    # summarizer = pipeline("summarization", model="google/pegasus-cnn_dailymail")
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    # summarizer = pipeline("summarization", model="google/pegasus-xsum")

    summary = summarizer(
        text_content,
        do_sample=False,
    )

    # print(summary)

    print(summary[0]["summary_text"])


suimmarize(
    """
           SPEAKER 2:  Era uma tarde nublada quando me sentei no banco da praça, esperando que a chuva começasse a cair.
SPEAKER 2:  Ao meu lado, havia dois homens, ambos parecendo absortos em seus próprios pensamentos.
SPEAKER 2:  Por algum motivo, a presença deles me deixou inquieto, como se algo não dito pairasse no ar.
SPEAKER 3:  Você acredita em coincidências? Perguntou-se em desviar os olhos do horizonte.
SPEAKER 2:  Pensei um pouco antes de responder. Não sei.
SPEAKER 2:  Às vezes, parece que o acaso nos empurra a lugares e situações que nunca imaginamos.
SPEAKER 2:  Mas sempre fica a dúvida. E você, acredita?
SPEAKER 3:  Ele sorriu como quem guardava um segredo.
SPEAKER 3:  Coincidências? Destino? Acaso?
SPEAKER 3:  Eu sempre achei que as coisas encaixavam do jeito que preciso.
SPEAKER 3:  Eu estava viajando bem longe daqui quando recebi uma carta de um amigo que não via antes.
SPEAKER 3:  No dia seguinte, voltei para a cidade desta vez, sentado exatamente onde estamos agora.
SPEAKER 2:  Antes que eu pudesse responder, o outro homem, que parecia mais jovem e mais impaciente, interrompeu, balançando a cabeça.
SPEAKER 1:  Não existe nada disso.
SPEAKER 1:  A vida é o que a gente faz dela. Pura e simples.
SPEAKER 1:  Não tem coincidências. Tem escolha.
SPEAKER 1:  Eu estava no mesmo lugar de sempre quando decidi largar o povo.
SPEAKER 1:  Não foi o acaso que me fez vender a empresa e viajar pelo mundo. Eu quis e pronto.
SPEAKER 2:  Olhei para os dois, tentando absorver o contraste das suas histórias.
SPEAKER 2:  O homem mais velho parecia acreditar que tudo seguia um plano,
SPEAKER 2:  enquanto o mais jovem parecia insistir que ele era o único arquiteto de seu próprio destino.
SPEAKER 2:  Me senti no meio de duas forças opostas.
SPEAKER 1:  E você? Perguntou uma jovem, agora me encarando. O que acha tudo isso?
SPEAKER 2:  Respirei fundo, sentindo o peso da questão.
SPEAKER 2:  Olhei para o céu, onde as nuvens começavam a escurecer, ameaçando a tarde pacífica.
SPEAKER 2:  Acho que a verdade está em algum lugar entre vocês dois.
SPEAKER 2:  Respondi, finalmente.
"""
)

