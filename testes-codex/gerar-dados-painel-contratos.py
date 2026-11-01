import json, datetime
from pathlib import Path
root=Path(__file__).resolve().parent.parent
periodos=[('12/02 a 15/04','2025-02-12','2025-04-15'),('16/04 a 17/06','2025-04-16','2025-06-17')]
fonte=[]
for r in json.loads((root/'testes-codex/resultado-fichas.json').read_text()):
 if r['periodo']=='desenvolvimento':
  nomes={'medias-5-20':'Médias 5/20','macd-12-26-9':'MACD 12/26/9','estocastico-14-3-3':'Estocástico 14/3/3'}
  fonte.append((nomes[r['estrategia']],r['operacoes']['M5'],'Rodada anterior',r['manifesto']))
for r in json.loads((root/'testes-codex/resultado-fibonacci-tempos.json').read_text()):
 if r['periodo']=='desenvolvimento' and r['timeframe']=='M5':
  nomes={'fibogap':'Fibogap','pivo-123-fibo':'Pivô Fibonacci','fibo-duas-etapas':'Fibonacci duas etapas','retracao-38-50':'Retração 38–50%'}
  fonte.append((nomes[r['estrategia']],r['operacoes']['padrao'],'Rodada anterior',r['manifesto']))
r=json.loads((root/'testes-codex/resultado-reteste-v1.json').read_text())
fonte.append(('Rompimento e reteste',r['operacoes'],'Reteste novo',r['manifesto']))
rows=[]
for nome,ops,origem,manifesto in fonte:
 for periodo,inicio,fim in periodos:
  for op in ops:
   if inicio<=op['data']<=fim:
    rows.append({'estrategia':nome,'contrato':periodo,'data':op['data'],'entrada':op['entrada_em'],'saida':op['saida_em'],'resultado':op['resultado_brl'],'motivo':op['motivo'],'origem':origem})
snapshot={'surface':'dashboard','title':'WIN · Resultados por contrato','buildStatus':'creating','status':'ready','generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exportPreferences':{'selected':None,'destinations':[]},'filters':[],'queries':{'operacoes':{'rows':rows,'source':{'name':'Resultados locais de backtests WIN','files':['testes-codex/resultado-fichas.json','testes-codex/resultado-fibonacci-tempos.json','testes-codex/resultado-reteste-v1.json','config/rolagens.yaml'],'description':'Dados históricos de desenvolvimento WIN$N, Clear; preços de execução M5, exceto sinal M15 do reteste. Custos já incluídos. Os resultados não são novos backtests por contrato.','metricDefinitions':[{'label':'Resultado líquido','definition':'Soma do resultado_brl das operações no intervalo, por contrato WIN, após custos.'},{'label':'Operações','definition':'Contagem de operações com entrada no intervalo selecionado.'}],'evidenceFlow':[{'title':'Rodadas registradas','detail':'Operações dos JSONs de desenvolvimento e manifestos associados; nenhum dado de 2026.'},{'title':'Separação por contrato','detail':'Entrada de 12/02 a 15/04/2025 ou de 16/04 a 17/06/2025, conforme config/rolagens.yaml.'}]},'methods':[{'language':'text','code':'Filtrar operações de desenvolvimento por data de entrada; agrupar por estratégia e período; somar resultado_brl e contar operações.'}]}}}
Path('/private/tmp/robo-b3-snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False))
print('Operações selecionadas:',len(rows))
