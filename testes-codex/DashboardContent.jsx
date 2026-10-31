import React, { useMemo, useState } from 'react';
import { DataComponent, useDataApp } from '../../data-app-public.jsx';
import './dashboard.css';

const names = {'rompimento':'Máxima da barra anterior','medias-5-20':'Médias móveis 5/20','macd-12-26-9':'MACD 12/26/9','estocastico-14-3-3':'Estocástico lento'};
const periods = {'desenvolvimento':'Desenvolvimento · 31/03/2023–30/12/2025','2026-jan-set-exploratorio':'2026 · janeiro a setembro','2026-fev-set-comparavel':'2026 · 11 fevereiro a setembro · comparação M1/M5/M15'};
const money = n => n == null ? '—' : Number(n).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const number = n => n == null ? '—' : Number(n).toLocaleString('pt-BR');

function Candle({bars, trade, levels}) {
  if (!bars.length) return <p>Sem barras disponíveis para este pregão.</p>;
  const values = bars.flatMap(b=>[b.h,b.l]);
  if(trade) values.push(trade.entrada, trade.saida);
  if(levels && trade) values.push(trade.stop,trade.alvo);
  const lo=Math.min(...values), hi=Math.max(...values), span=Math.max(1,hi-lo);
  const x=i=>65+i*845/Math.max(1,bars.length-1), y=v=>20+(hi-v)/span*300;
  const idx=t=>bars.findIndex(b=>b.t===t);
  return <svg className="precos" viewBox="0 0 1000 360" role="img" aria-label="Gráfico das barras de preço com entrada e saída">
    {[0,.25,.5,.75,1].map(f=><g key={f}><line x1="65" x2="910" y1={20+f*300} y2={20+f*300} stroke="var(--border)"/><text x="4" y={24+f*300} fill="var(--secondary)" fontSize="12">{number(Math.round(hi-f*span))}</text></g>)}
    {bars.map((b,i)=><g key={b.t}><line x1={x(i)} x2={x(i)} y1={y(b.h)} y2={y(b.l)} stroke={b.c>=b.o?'#18876e':'#d25f57'}/><rect x={x(i)-1.5} y={Math.min(y(b.o),y(b.c))} width="3" height={Math.max(1,Math.abs(y(b.o)-y(b.c)))} fill={b.c>=b.o?'#18876e':'#d25f57'}><title>{b.t.slice(11,16)} · abertura {number(b.o)} · máxima {number(b.h)} · mínima {number(b.l)} · fechamento {number(b.c)}</title></rect></g>)}
    {levels && trade && [[trade.alvo,'Alvo','#18876e'],[trade.stop,'Stop','#d25f57']].map(([v,n,c])=><g key={n}><line x1="65" x2="910" y1={y(v)} y2={y(v)} stroke={c} strokeDasharray="5 4"/><text x="915" y={y(v)+4} fill={c} fontSize="12">{n}</text></g>)}
    {trade && [['entrada_em','entrada','Entrada','#1574d4'],['saida_em','saida','Saída','#bc5b13']].map(([t,p,n,c])=>idx(trade[t])>=0 && <g key={t}><circle cx={x(idx(trade[t]))} cy={y(trade[p])} r="5" fill={c}><title>{n} {trade[t].slice(11,16)} · {number(trade[p])}</title></circle><text x={x(idx(trade[t]))+5} y={y(trade[p])-8} fill={c} fontSize="12">{n}</text></g>)}
    <text x="65" y="344" fill="var(--secondary)" fontSize="12">{bars[0].t.slice(11,16)}</text><text x="865" y="344" fill="var(--secondary)" fontSize="12">{bars.at(-1).t.slice(11,16)}</text>
  </svg>;
}

export function DashboardContent() {
  const {queries} = useDataApp();
  const metrics=queries.fichas_resultados?.rows ?? [], allTrades=queries.fichas_operacoes?.rows ?? [], allBars=queries.fichas_barras?.rows ?? [];
  const oldDev=queries.operacoes?.rows ?? [], old2026=queries.operacoes_2026?.rows ?? [];
  const [strategy,setStrategy]=useState('medias-5-20');
  const [period,setPeriod]=useState('desenvolvimento');
  const [tf,setTf]=useState('M5');
  const [day,setDay]=useState('');
  const [tradeIdx,setTradeIdx]=useState(0);
  const [levels,setLevels]=useState(false);
  const old=strategy==='rompimento';
  const selectedPeriod=old && period==='2026-fev-set-comparavel'?'2026-jan-set-exploratorio':period;
  const strategyRows=metrics.filter(r=>r.estrategia===strategy && r.periodo===selectedPeriod);
  const timeframes=old?['M5']:strategyRows.map(r=>r.timeframe);
  const selectedTf=timeframes.includes(tf)?tf:timeframes[0];
  const selectedTrades=useMemo(()=>old?(selectedPeriod==='desenvolvimento'?oldDev:old2026):allTrades.filter(r=>r.estrategia===strategy && r.periodo===selectedPeriod && r.timeframe===selectedTf),[old,strategy,selectedPeriod,selectedTf,allTrades,oldDev,old2026]);
  const days=useMemo(()=>[...new Set(selectedTrades.map(o=>o.data))],[selectedTrades]);
  const selectedDay=days.includes(day)?day:days[0];
  const dayTrades=selectedTrades.filter(o=>o.data===selectedDay);
  const trade=dayTrades[Math.min(tradeIdx,dayTrades.length-1)];
  const bars=old?(selectedPeriod==='desenvolvimento'?queries.barras?.rows??[]:queries.barras_2026?.rows??[]).filter(b=>b.dia===selectedDay):allBars.filter(b=>b.periodo===selectedPeriod && b.timeframe===selectedTf && b.dia===selectedDay);
  const row=strategyRows.find(r=>r.timeframe===selectedTf);
  let running=0,peak=0,drawdown=0;
  const annual={};
  selectedTrades.forEach(o=>{running+=o.resultado_brl;peak=Math.max(peak,running);drawdown=Math.min(drawdown,running-peak);annual[o.data.slice(0,4)]=(annual[o.data.slice(0,4)]||0)+o.resultado_brl});
  const gains=selectedTrades.reduce((s,o)=>s+Math.max(0,o.resultado_brl),0), losses=-selectedTrades.reduce((s,o)=>s+Math.min(0,o.resultado_brl),0);
  const result=old?{resultado_brl:running,operacoes:selectedTrades.length,drawdown_max:drawdown,fator_lucro:losses?gains/losses:null}:row;
  const annuals=Object.entries(annual), maxAnn=Math.max(1,...annuals.map(([,v])=>Math.abs(v)));
  const primary=old?(selectedPeriod==='desenvolvimento'?'operacoes':'operacoes_2026'):'fichas_operacoes';
  const barQuery=old?(selectedPeriod==='desenvolvimento'?'barras':'barras_2026'):'fichas_barras';
  const scope={[barQuery]:bars,[primary]:dayTrades};
  return <div className="pesquisa">
    <div className="selecao"><label>Estratégia<select value={strategy} onChange={e=>{setStrategy(e.target.value);setDay('');setTradeIdx(0)}}>{Object.entries(names).map(([id,name])=><option value={id} key={id}>{name}</option>)}</select></label>
      <label>Período<select value={selectedPeriod} onChange={e=>{setPeriod(e.target.value);setDay('');setTradeIdx(0)}}>{Object.entries(periods).filter(([id])=>!old || id!=='2026-fev-set-comparavel').map(([id,name])=><option value={id} key={id}>{name}</option>)}</select></label>
      <label>Tempo gráfico<select value={selectedTf||''} onChange={e=>{setTf(e.target.value);setDay('');setTradeIdx(0)}}>{timeframes.map(t=><option key={t}>{t}</option>)}</select></label></div>
    <p className="nota">Simulação: 1 contrato, custos e derrapagem estimados. 2023 e 2026 são períodos parciais; outubro de 2026 não foi testado. A escolha de parâmetros usando 2026 é exploratória.</p>
    <div className="numeros" data-reviewed-rows><div><span>Resultado líquido</span><strong>{money(result?.resultado_brl)}</strong></div><div><span>Operações</span><strong>{number(result?.operacoes)}</strong></div><div><span>Fator de lucro</span><strong>{result?.fator_lucro == null?'—':result.fator_lucro.toLocaleString('pt-BR',{minimumFractionDigits:3,maximumFractionDigits:3})}</strong></div><div><span>Queda máxima</span><strong>{money(result?.drawdown_max)}</strong></div></div>
    <DataComponent variant="card" id="anos" queryId={primary} kind="custom" title="Resultado líquido por ano" sourceRows={selectedTrades} displayRows={selectedTrades}>
      <div className="anuais" data-reviewed-rows>{annuals.map(([a,v])=><div key={a}><div>{a}{a==='2023'||a==='2026'?' · parcial':''}</div><div className="barra"><i style={{width:`${Math.abs(v)/maxAnn*100}%`,background:v<0?'#d25f57':'#18876e'}}/></div><b>{money(v)}</b></div>)}</div>
    </DataComponent>
    {!old && <DataComponent variant="card" id="comparacao" queryId="fichas_resultados" kind="custom" title="Comparação dos tempos no período selecionado" sourceRows={strategyRows} displayRows={strategyRows}>
      <div className="tabela"><table><thead><tr><th>Tempo</th><th>Resultado</th><th>Operações</th><th>Fator de lucro</th><th>Queda máxima</th></tr></thead><tbody>{strategyRows.map(r=><tr key={r.timeframe}><td>{r.timeframe}</td><td>{money(r.resultado_brl)}</td><td>{number(r.operacoes)}</td><td>{r.fator_lucro?.toLocaleString('pt-BR',{minimumFractionDigits:3,maximumFractionDigits:3})??'—'}</td><td>{money(r.drawdown_max)}</td></tr>)}</tbody></table></div>
      <p className="nota">M1 só está disponível para o recorte comparável de fevereiro a setembro de 2026. Barra ambígua: saída pelo stop. Resultados por tempo são simulações diferentes.</p>
    </DataComponent>}
    <DataComponent variant="card" id="pregao" queryId={barQuery} queryIds={[barQuery,primary]} kind="custom" title="Examinar operação" sourceRowsByQuery={scope} displayRows={bars}>
      <div className="controles"><label>Pregão<select value={selectedDay||''} onChange={e=>{setDay(e.target.value);setTradeIdx(0)}}>{days.map(d=><option key={d} value={d}>{d.split('-').reverse().join('/')}</option>)}</select></label>
      <label>Operação<select value={Math.min(tradeIdx,Math.max(0,dayTrades.length-1))} onChange={e=>setTradeIdx(Number(e.target.value))}>{dayTrades.map((o,i)=><option key={i} value={i}>{i+1} · {o.entrada_em.slice(11,16)} · {money(o.resultado_brl)}</option>)}</select></label><label><input type="checkbox" checked={levels} onChange={e=>setLevels(e.target.checked)}/> Mostrar alvo e stop</label></div>
      <Candle bars={bars} trade={trade} levels={levels}/><p className="nota">As marcações identificam barras, não o instante exato. Passe o cursor sobre a barra para ver os preços.</p>
      {trade && <div className="detalhes" data-reviewed-rows>{trade.lado===-1?'Venda':'Compra'} {trade.entrada_em.slice(11,16)} · {number(trade.entrada)} pontos | Saída {trade.saida_em.slice(11,16)} · {number(trade.saida)} pontos ({trade.motivo}) | {money(trade.resultado_brl)}<br/>Alvo {number(trade.alvo)} · Stop {number(trade.stop)}</div>}
    </DataComponent>
    <p className="nota">{old?'Máxima anterior: alvo 3% e stop 10% do preço.':'Médias, MACD e estocástico: stop 300 e alvo 600 pontos, além da saída por sinal ou fim do pregão.'} Execução no fechamento final é uma hipótese; 2026 usado na escolha não é validação independente.</p>
  </div>;
}
