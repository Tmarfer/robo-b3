import React, { useMemo, useState } from 'react';
import { DataComponent, useDataApp } from '../../data-app-public.jsx';
import './dashboard.css';

const names = {'retracao-38-50':'Fibonacci · retração 38–50%', 'fibogap':'Fibonacci · Fibogap', 'pivo-123-fibo':'Fibonacci · pivô 1-2-3', 'fibo-duas-etapas':'Fibonacci · duas etapas', 'reteste':'Rompimento e reteste · M15/M5', 'falso':'Rompimento falso · trailing (diagnóstico)', 'rompimento':'Máxima da barra anterior · versão antiga','medias-5-20':'Médias móveis 5/20','macd-12-26-9':'MACD 12/26/9','estocastico-14-3-3':'Estocástico lento'};
const periods = {'desenvolvimento':'Desenvolvimento · 31/03/2023–30/12/2025','2026-jan-set-exploratorio':'2026 · janeiro a setembro','2026-fev-set-comparavel':'2026 · 11 fevereiro a setembro · comparação M1/M5/M15'};
const money = n => n == null ? '—' : Number(n).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const number = n => n == null ? '—' : Number(n).toLocaleString('pt-BR');

function Candle({bars, trade, levels, showEma, showLevel}) {
  if (!bars.length) return <p>Sem barras disponíveis para este pregão.</p>;
  const values = bars.flatMap(b=>[b.h,b.l]);
  if(trade) values.push(trade.entrada, trade.saida);
  if(showEma) values.push(...bars.map(b=>b.ema).filter(Number.isFinite));
  if(showLevel && Number.isFinite(trade?.nivel)) values.push(trade.nivel);
  if(levels && trade) values.push(...[trade.stop,trade.alvo,trade.stop_atual].filter(Number.isFinite));
  const lo=Math.min(...values), hi=Math.max(...values), span=Math.max(1,hi-lo);
  const x=i=>65+i*845/Math.max(1,bars.length-1), y=v=>20+(hi-v)/span*300;
  const idx=t=>bars.findIndex(b=>b.t===t);
  return <svg className="precos" viewBox="0 0 1000 360" role="img" aria-label="Gráfico das barras de preço com entrada e saída">
    {[0,.25,.5,.75,1].map(f=><g key={f}><line x1="65" x2="910" y1={20+f*300} y2={20+f*300} stroke="var(--border)"/><text x="4" y={24+f*300} fill="var(--secondary)" fontSize="12">{number(Math.round(hi-f*span))}</text></g>)}
    {showLevel && trade && Number.isFinite(trade.nivel) && <g><line x1="65" x2="910" y1={y(trade.nivel)} y2={y(trade.nivel)} stroke="#b97917" strokeDasharray="5 4"/><text x="915" y={y(trade.nivel)+4} fill="#b97917" fontSize="12">Nível</text></g>}
    {showEma && <polyline points={bars.map((b,i)=>Number.isFinite(b.ema)?`${x(i)},${y(b.ema)}`:null).filter(Boolean).join(' ')} fill="none" stroke="#a96ee0" strokeWidth="2"><title>MME20 de barras M15 fechadas</title></polyline>}
    {bars.map((b,i)=><g key={b.t}><line x1={x(i)} x2={x(i)} y1={y(b.h)} y2={y(b.l)} stroke={b.c>=b.o?'#18876e':'#d25f57'}/><rect x={x(i)-1.5} y={Math.min(y(b.o),y(b.c))} width="3" height={Math.max(1,Math.abs(y(b.o)-y(b.c)))} fill={b.c>=b.o?'#18876e':'#d25f57'}><title>{b.t.slice(11,16)} · abertura {number(b.o)} · máxima {number(b.h)} · mínima {number(b.l)} · fechamento {number(b.c)}</title></rect></g>)}
    {levels && trade && [[trade.alvo,'Alvo','#18876e'],[trade.stop,'Stop inicial','#d25f57'],[trade.stop_atual,'Stop final','#bc5b13']].filter(([v])=>Number.isFinite(v)).map(([v,n,c])=><g key={n}><line x1="65" x2="910" y1={y(v)} y2={y(v)} stroke={c} strokeDasharray="5 4"/><text x="915" y={y(v)+4} fill={c} fontSize="12">{n}</text></g>)}
    {levels && trade?.movimentos_stop?.length>1 && <path d={trade.movimentos_stop.filter(e=>idx(e.t)>=0).map((e,i)=>`${i===0?`M ${x(idx(e.t))} ${y(e.preco)}`:`H ${x(idx(e.t))} V ${y(e.preco)}`}`).join(' ')} fill="none" stroke="#bc5b13" strokeWidth="2" strokeDasharray="3 2"><title>Mudanças de stop por barra; ordem intrabar suposta</title></path>}
    {trade && [['entrada_em','entrada','Entrada','#1574d4'],['saida_em','saida','Saída','#bc5b13']].map(([t,p,n,c])=>idx(trade[t])>=0 && <g key={t}><circle cx={x(idx(trade[t]))} cy={y(trade[p])} r="5" fill={c}><title>{n} {trade[t].slice(11,16)} · {number(trade[p])}</title></circle><text x={x(idx(trade[t]))+5} y={y(trade[p])-8} fill={c} fontSize="12">{n}</text></g>)}
    <text x="65" y="344" fill="var(--secondary)" fontSize="12">{bars[0].t.slice(11,16)}</text><text x="865" y="344" fill="var(--secondary)" fontSize="12">{bars.at(-1).t.slice(11,16)}</text>
  </svg>;
}

export function DashboardContent() {
  const {queries} = useDataApp();
  const metrics=queries.fichas_resultados?.rows ?? [], allTrades=queries.fichas_operacoes?.rows ?? [], allBars=queries.fichas_barras?.rows ?? [];
  const oldDev=queries.operacoes?.rows ?? [], old2026=queries.operacoes_2026?.rows ?? [];
  const [strategy,setStrategy]=useState('retracao-38-50');
  const [exitMode,setExitMode]=useState('fixo');
  const [stopTicks,setStopTicks]=useState('3');
  const [period,setPeriod]=useState('desenvolvimento');
  const [tf,setTf]=useState('M5');
  const [day,setDay]=useState('');
  const [dayOutcome,setDayOutcome]=useState('todos');
  const [tradeIdx,setTradeIdx]=useState(0);
  const [levels,setLevels]=useState(false);
  const old=strategy==='rompimento';
  const isFalso=strategy==='falso';
  const isReteste=strategy==='reteste';
  const isFibo=['retracao-38-50','fibogap','pivo-123-fibo','fibo-duas-etapas'].includes(strategy);
  const fiboMetrics=queries.fibonacci_resultados?.rows ?? [];
  const fiboTrades=queries.fibonacci_operacoes?.rows ?? [];
  const isThree=['medias-5-20','macd-12-26-9','estocastico-14-3-3'].includes(strategy);
  const isTrailing=isThree && exitMode==='trailing';
  const fiboExit=isFibo?(exitMode==='curto'?'trailing-30-15':exitMode==='trailing'?'trailing':'padrao'):'padrao';
  const trailingMetrics=queries.trailing_resultados?.rows ?? [];
  const trailingTrades=queries.trailing_operacoes?.rows ?? [];
  const retesteRows=queries.reteste_resultados?.rows ?? [];
  const retesteTrades=queries.reteste_operacoes?.rows ?? [];
  const falseRows=queries.falso_resultados?.rows ?? [];
  const falseTrades=queries.falso_operacoes?.rows ?? [];
  const selectedPeriod=old && period==='2026-fev-set-comparavel'?'2026-jan-set-exploratorio':period;
  const fixedRows=metrics.filter(r=>r.estrategia===strategy && r.periodo===selectedPeriod);
  const strategyRows=(isFibo?fiboMetrics:isReteste?retesteRows:isFalso?falseRows:isTrailing?trailingMetrics:metrics).filter(r=>(isReteste || isFalso || r.estrategia===strategy) && r.periodo===selectedPeriod);
  const timeframes=isFibo?[...new Set(strategyRows.map(r=>r.timeframe))]:(isReteste || isFalso)?[...new Set(strategyRows.map(r=>r.timeframe))]:(old?['M5']:strategyRows.map(r=>r.timeframe));
  const selectedTf=timeframes.includes(tf)?tf:timeframes[0];
  const selectedTrades=useMemo(()=>isFibo?fiboTrades.filter(r=>r.estrategia===strategy && r.periodo===selectedPeriod && r.timeframe===selectedTf && r.versao_saida===fiboExit):isReteste?retesteTrades.filter(r=>r.periodo===selectedPeriod && r.timeframe===selectedTf):isFalso?falseTrades.filter(r=>r.periodo===selectedPeriod && r.timeframe===selectedTf && r.stop_ticks===Number(stopTicks)):isTrailing?trailingTrades.filter(r=>r.estrategia===strategy && r.periodo===selectedPeriod && r.timeframe===selectedTf):(old?(selectedPeriod==='desenvolvimento'?oldDev:old2026):allTrades.filter(r=>r.estrategia===strategy && r.periodo===selectedPeriod && r.timeframe===selectedTf)),[isFibo,fiboTrades,exitMode,isReteste,retesteTrades,isFalso,falseTrades,stopTicks,isTrailing,trailingTrades,old,strategy,selectedPeriod,selectedTf,allTrades,oldDev,old2026]);
  const dailyTotals=useMemo(()=>selectedTrades.reduce((acc,o)=>{acc[o.data]=(acc[o.data]||0)+o.resultado_brl;return acc;},{}),[selectedTrades]);
  const days=useMemo(()=>Object.keys(dailyTotals).filter(d=>dayOutcome==='todos' || (dayOutcome==='lucro' && dailyTotals[d]>0) || (dayOutcome==='prejuizo' && dailyTotals[d]<0) || (dayOutcome==='zero' && dailyTotals[d]===0)),[dailyTotals,dayOutcome]);
  const selectedDay=days.includes(day)?day:days[0];
  const dayTrades=selectedTrades.filter(o=>o.data===selectedDay);
  const trade=dayTrades[Math.min(tradeIdx,dayTrades.length-1)];
  const bars=old?(selectedPeriod==='desenvolvimento'?queries.barras?.rows??[]:queries.barras_2026?.rows??[]).filter(b=>b.dia===selectedDay):allBars.filter(b=>b.periodo===selectedPeriod && b.timeframe===(selectedTf==='M15/M5 anterior'?'M5':selectedTf) && b.dia===selectedDay);
  const row=isFibo?strategyRows.find(r=>r.timeframe===selectedTf && r.versao_saida===fiboExit):isReteste?strategyRows.find(r=>r.timeframe===selectedTf):isFalso?strategyRows.find(r=>r.timeframe===selectedTf && r.stop_ticks===Number(stopTicks)):strategyRows.find(r=>r.timeframe===selectedTf);
  let running=0,peak=0,drawdown=0;
  const annual={};
  selectedTrades.forEach(o=>{running+=o.resultado_brl;peak=Math.max(peak,running);drawdown=Math.min(drawdown,running-peak);annual[o.data.slice(0,4)]=(annual[o.data.slice(0,4)]||0)+o.resultado_brl});
  const gains=selectedTrades.reduce((s,o)=>s+Math.max(0,o.resultado_brl),0), losses=-selectedTrades.reduce((s,o)=>s+Math.min(0,o.resultado_brl),0);
  const result=old?{resultado_brl:running,operacoes:selectedTrades.length,drawdown_max:drawdown,fator_lucro:losses?gains/losses:null}:row;
  const annuals=Object.entries(annual), maxAnn=Math.max(1,...annuals.map(([,v])=>Math.abs(v)));
  const primary=isFibo?'fibonacci_operacoes':isReteste?'reteste_operacoes':isFalso?'falso_operacoes':isTrailing?'trailing_operacoes':(old?(selectedPeriod==='desenvolvimento'?'operacoes':'operacoes_2026'):'fichas_operacoes');
  const barQuery=old?(selectedPeriod==='desenvolvimento'?'barras':'barras_2026'):'fichas_barras';
  const scope={[barQuery]:bars,[primary]:dayTrades};
  return <div className="pesquisa">
    <div className="selecao"><label>Estratégia<select value={strategy} onChange={e=>{setStrategy(e.target.value);setDay('');setTradeIdx(0)}}>{Object.entries(names).map(([id,name])=><option value={id} key={id}>{name}</option>)}</select></label>
      <label>Período<select value={selectedPeriod} onChange={e=>{setPeriod(e.target.value);setDay('');setTradeIdx(0)}}>{Object.entries(periods).filter(([id])=>!old || id!=='2026-fev-set-comparavel').map(([id,name])=><option value={id} key={id}>{((isReteste || isFibo) && id==='desenvolvimento') ? '03/04/2023–30/12/2025 · desenvolvimento' : name}</option>)}</select></label>
      <label>Tempo gráfico<select value={selectedTf||''} onChange={e=>{setTf(e.target.value);setDay('');setTradeIdx(0)}}>{timeframes.map(t=><option key={t}>{t}</option>)}</select></label>{(isThree || isFibo) && <label>Saída<select value={exitMode} onChange={e=>{setExitMode(e.target.value);setDay('');setTradeIdx(0)}}><option value="fixo">{isFibo?'Padrão · alvo da ficha':'Original · alvo fixo'}</option><option value="trailing">Stop móvel · 300/150</option>{isFibo && <option value="curto">Stop móvel · 30/15</option>}</select></label>}{isFalso && <label>Stop inicial<select value={stopTicks} onChange={e=>{setStopTicks(e.target.value);setDay('');setTradeIdx(0)}}><option value="3">3 ticks · 15 pontos</option><option value="5">5 ticks · 25 pontos</option></select></label>}</div>
    {isFibo && selectedPeriod==='2026-fev-set-comparavel' && <p className="aviso">Na fonte M1, 92 pregões do recorte não atenderam aos requisitos de primeira hora completa e barra das 17h. Os três tempos usaram os mesmos pregões disponíveis para esta grade.</p>}
    {isFibo && <p className="nota">Sinal e execução no tempo escolhido; a opção M15/M5 anterior mantém a rodada anterior. Uma operação por pregão. A linha pontilhada mostra o nível de referência. Para retração, ela marca o centro da zona de 38,2%–50%. As regras são adaptações objetivas das fichas.</p>}
    {isReteste && <p className="nota">Sinal confirmado no fechamento; execução na abertura seguinte no tempo selecionado. A opção M15/M5 anterior preserva a rodada original. Linha pontilhada: máxima ou mínima do pregão anterior.</p>}
    {(isTrailing || (isFibo && exitMode!=='fixo')) && <p className="aviso">{isFibo && exitMode==='curto'?'Após 30 pontos favoráveis, protege 15 pontos e acompanha o melhor preço a 15 pontos.':isFibo?'Stop inicial conforme a estrutura da ficha; após 300 pontos de ganho, acompanha a 150 pontos.':'Stop inicial de 300 pontos; após 300 pontos de ganho, acompanha o melhor preço a 150 pontos.'} Sem alvo fixo. Quando a ordem de máxima e mínima é desconhecida, o resultado usa uma hipótese adversa e não representa a sequência real.</p>}
    {isFalso && <p className="aviso">Diagnóstico aproximado: o rompimento falso é confirmado no fechamento da barra e a entrada acontece na abertura seguinte. Para barras ambíguas, usa-se uma hipótese adversa. Os dados não mostram a ordem real dos negócios; os números não reproduzem a entrada intrabar solicitada.</p>}
    <p className="nota">Simulação: 1 contrato, custos e derrapagem estimados. 2023 e 2026 são períodos parciais; outubro de 2026 não foi testado. A escolha de parâmetros usando 2026 é exploratória.</p>
    <div className="numeros" data-reviewed-rows><div><span>{isFalso ? 'Resultado sob hipótese adversa' : 'Resultado líquido'}</span><strong>{money(result?.resultado_brl)}</strong></div><div><span>Operações</span><strong>{number(result?.operacoes)}</strong></div><div><span>Fator de lucro</span><strong>{result?.fator_lucro == null?'—':result.fator_lucro.toLocaleString('pt-BR',{minimumFractionDigits:3,maximumFractionDigits:3})}</strong></div><div><span>Queda máxima</span><strong>{money(result?.drawdown_max)}</strong></div></div>
    {(isTrailing || isFibo) && <p className="nota">Operações com barras ambíguas: {number(result?.ambiguas)} de {number(result?.operacoes)} ({result?.operacoes ? (100*result.ambiguas/result.operacoes).toLocaleString('pt-BR',{maximumFractionDigits:1}) : '—'}%). O resultado depende da hipótese sobre o movimento dentro da barra.</p>}
    <DataComponent variant="card" id="anos" queryId={primary} kind="custom" title="Resultado líquido por ano" sourceRows={selectedTrades} displayRows={selectedTrades}>
      <div className="anuais" data-reviewed-rows>{annuals.map(([a,v])=><div key={a}><div>{a}{a==='2023'||a==='2026'?' · parcial':''}</div><div className="barra"><i style={{width:`${Math.abs(v)/maxAnn*100}%`,background:v<0?'#d25f57':'#18876e'}}/></div><b>{money(v)}</b></div>)}</div>
    </DataComponent>
    {isFibo && <DataComponent variant="card" id="comparacao-fibo" queryId="fibonacci_resultados" kind="custom" title="Comparação das saídas no período" sourceRows={strategyRows} displayRows={strategyRows}>
      <div className="tabela"><table><thead><tr><th>Tempo</th><th>Saída</th><th>Resultado</th><th>Operações</th><th>Fator de lucro</th><th>Ambíguas</th></tr></thead><tbody>{strategyRows.map(r=><tr key={r.timeframe+'-'+r.versao_saida}><td>{r.timeframe}</td><td>{r.versao_saida==='padrao'?'Padrão':r.versao_saida==='trailing-30-15'?'Stop móvel 30/15':'Stop móvel 300/150'}</td><td>{money(r.resultado_brl)}</td><td>{number(r.operacoes)}</td><td>{r.fator_lucro?.toLocaleString('pt-BR',{minimumFractionDigits:3,maximumFractionDigits:3})??'—'}</td><td>{number(r.ambiguas)}</td></tr>)}</tbody></table></div><p className="nota">Para cada tempo, as saídas usam as mesmas entradas e o mesmo stop inicial; entre tempos as entradas podem mudar. A versão móvel não tem alvo fixo. A ordem dentro da barra é uma hipótese.</p>
    </DataComponent>}
    {(isFalso || isReteste) && <DataComponent variant="card" id="comparacao-outros-tempos" queryId={isFalso?"falso_resultados":"reteste_resultados"} kind="custom" title="Comparação dos tempos no período selecionado" sourceRows={strategyRows} displayRows={strategyRows}>
      <div className="tabela"><table><thead><tr><th>Tempo</th>{isFalso && <th>Stop inicial</th>}<th>Resultado líquido</th><th>Operações</th><th>Fator de lucro</th></tr></thead><tbody>{strategyRows.filter(r=>!isFalso || r.stop_ticks===Number(stopTicks)).map(r=><tr key={r.timeframe}><td>{r.timeframe}</td>{isFalso && <td>{r.stop_ticks} ticks</td>}<td>{money(r.resultado_brl)}</td><td>{number(r.operacoes)}</td><td>{r.fator_lucro?.toLocaleString('pt-BR',{minimumFractionDigits:3,maximumFractionDigits:3})??'—'}</td></tr>)}</tbody></table></div><p className="nota">Os sinais mudam com o tempo gráfico. M1 está disponível apenas no recorte comum de fevereiro a setembro de 2026.</p>
    </DataComponent>}
    {!old && !isFalso && !isReteste && !isFibo && <DataComponent variant="card" id="comparacao" queryId={isTrailing?"trailing_resultados":"fichas_resultados"} queryIds={isTrailing?["trailing_resultados","fichas_resultados"]:["fichas_resultados"]} kind="custom" title="Comparação dos tempos no período selecionado" sourceRowsByQuery={isTrailing?{trailing_resultados:strategyRows,fichas_resultados:fixedRows}:{fichas_resultados:strategyRows}} displayRows={isTrailing?strategyRows.map(r=>({...r,resultado_original:fixedRows.find(f=>f.timeframe===r.timeframe)?.resultado_brl})):strategyRows}>
      <div className="tabela"><table><thead><tr><th>Tempo</th><th>Resultado da versão</th>{isTrailing && <th>Original · alvo fixo</th>}<th>Operações</th><th>Fator de lucro</th><th>Queda máxima</th></tr></thead><tbody>{strategyRows.map(r=><tr key={r.timeframe}><td>{r.timeframe}</td><td>{money(r.resultado_brl)}</td>{isTrailing && <td>{money(fixedRows.find(f=>f.timeframe===r.timeframe)?.resultado_brl)}</td>}<td>{number(r.operacoes)}</td><td>{r.fator_lucro?.toLocaleString('pt-BR',{minimumFractionDigits:3,maximumFractionDigits:3})??'—'}</td><td>{money(r.drawdown_max)}</td></tr>)}</tbody></table></div>
      <p className="nota">M1 só está disponível para fevereiro a setembro de 2026. As versões podem ter operações diferentes; a comparação usa as mesmas datas e custos. Em barras ambíguas, o resultado depende da hipótese de execução.</p>
    </DataComponent>}
    <DataComponent variant="card" id="pregao" queryId={barQuery} queryIds={[barQuery,primary]} kind="custom" title="Examinar operação" sourceRowsByQuery={scope} displayRows={bars}>
      <div className="controles"><label>Resultado do pregão<select value={dayOutcome} onChange={e=>{setDayOutcome(e.target.value);setDay('');setTradeIdx(0)}}><option value="todos">Todos</option><option value="lucro">Com lucro</option><option value="prejuizo">Com prejuízo</option><option value="zero">Sem lucro nem prejuízo</option></select></label>
      <label>Pregão<select value={selectedDay||''} disabled={!days.length} onChange={e=>{setDay(e.target.value);setTradeIdx(0)}}>{days.length?days.map(d=><option key={d} value={d}>{d.split('-').reverse().join('/')} · {money(dailyTotals[d])}</option>):<option value="">Nenhum pregão encontrado</option>}</select></label>
      <label>Operação<select value={Math.min(tradeIdx,Math.max(0,dayTrades.length-1))} disabled={!dayTrades.length} onChange={e=>setTradeIdx(Number(e.target.value))}>{dayTrades.length?dayTrades.map((o,i)=><option key={i} value={i}>{i+1} · {o.entrada_em.slice(11,16)} · {money(o.resultado_brl)}</option>):<option value="0">Nenhuma operação</option>}</select></label><label><input type="checkbox" checked={levels} onChange={e=>setLevels(e.target.checked)}/> Mostrar alvo e stop</label></div>
      <p className="nota">O filtro considera a soma líquida de todas as operações do pregão na estratégia, no período e no tempo gráfico selecionados.</p>
      <Candle bars={bars} trade={trade} levels={levels} showEma={isReteste && selectedTf==='M15/M5 anterior'} showLevel={isReteste || isFibo}/><p className="nota">As marcações identificam barras, não o instante exato. Passe o cursor sobre a barra para ver os preços.</p>
      {trade && <div className="detalhes" data-reviewed-rows>{trade.lado===-1?'Venda':'Compra'} {trade.entrada_em.slice(11,16)} · {number(trade.entrada)} pontos | Saída {trade.saida_em.slice(11,16)} · {number(trade.saida)} pontos ({trade.motivo}) | {money(trade.resultado_brl)}<br/>{trade.alvo == null?'Sem alvo fixo':`Alvo ${number(trade.alvo)}`} · Stop inicial {number(trade.stop)}{(isFalso || isTrailing || (isFibo && exitMode==='trailing')) && ` · Stop final ${number(trade.stop_atual)}`}</div>}
    </DataComponent>
    <p className="nota">{isFibo?`Fibonacci: stop estrutural; saída padrão por alvo da ficha ou trailing ${exitMode==='curto'?'30/15':'300/150'} sem alvo fixo.`:isTrailing?'Trailing sem alvo fixo: stop inicial 300 pontos; ativa com ganho de 300 e acompanha a 150 pontos.':isReteste?'Reteste com MME20 no tempo do sinal, stop de 300 e alvo de 600 pontos, com saída às 17:00.':isFalso?'Trailing ativa com 4 ticks e acompanha a 2 ticks do melhor preço; stop inicial de 3 ou 5 ticks.':(old?'Máxima anterior: alvo 3% e stop 10% do preço.':'Médias, MACD e estocástico: stop 300 e alvo 600 pontos, além da saída por sinal ou fim do pregão.')} {isFibo ? ' Saída por tempo na abertura das 17h; 2026 é exploratório e não é validação independente.' : isReteste ? ' Preços simulados não garantem execução real; o período já foi usado em outras pesquisas.' : ' Execução no fechamento final é uma hipótese; 2026 usado na escolha não é validação independente.'}</p>
  </div>;
}
