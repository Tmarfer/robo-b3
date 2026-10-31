import React, { useMemo, useState } from 'react';
import { DataComponent, useDataApp } from '../../data-app-public.jsx';
import './dashboard.css';

const moeda = n => n.toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
const num = n => Number(n).toLocaleString('pt-BR');

function Candle({barras, ops, limites}) {
  if (!barras.length) return <p>Sem barras para este pregão.</p>;
  const op = ops[0];
  const vals = barras.flatMap(b => [b.h,b.l]);
  if (limites && op) vals.push(op.stop, op.alvo);
  const min = Math.min(...vals), max = Math.max(...vals), span = Math.max(1,max-min);
  const x = i => 66 + i*850/Math.max(1,barras.length-1);
  const y = v => 20 + (max-v)/span*300;
  const at = t => barras.findIndex(b=>b.t===t);
  return <svg viewBox="0 0 1000 360" role="img" aria-label="Barras de preço M5, entrada e saída da operação" className="precos">
    {[0,.25,.5,.75,1].map(f => <g key={f}><line x1="65" x2="920" y1={20+f*300} y2={20+f*300} stroke="var(--border)"/><text x="5" y={24+f*300} fill="var(--secondary)" fontSize="12">{num(Math.round(max-f*span))}</text></g>)}
    {barras.map((b,i) => <g key={b.t}><line x1={x(i)} x2={x(i)} y1={y(b.h)} y2={y(b.l)} stroke={b.c>=b.o?'#18876e':'#d25f57'} strokeWidth="1"/><rect x={x(i)-2} y={Math.min(y(b.o),y(b.c))} width="4" height={Math.max(1,Math.abs(y(b.o)-y(b.c)))} fill={b.c>=b.o?'#18876e':'#d25f57'}><title>{b.t.slice(11,16)} · abertura {num(b.o)} · máxima {num(b.h)} · mínima {num(b.l)} · fechamento {num(b.c)}</title></rect></g>)}
    {limites && op && [[op.alvo,'Alvo','#18876e'],[op.stop,'Stop','#d25f57']].map(([v,n,c])=><g key={n}><line x1="65" x2="920" y1={y(v)} y2={y(v)} stroke={c} strokeDasharray="5 4"/><text x="925" y={y(v)+4} fill={c} fontSize="12">{n}</text></g>)}
    {ops.map((o,i)=><g key={i}>{[['entrada_em','entrada','Compra','#1574d4'],['saida_em','saida','Saída','#bc5b13']].map(([t,p,n,c])=> at(o[t])>=0 && <g key={t}><circle cx={x(at(o[t]))} cy={y(o[p])} r="5" fill={c}><title>{n}: {o[t].slice(11,16)} · {num(o[p])}</title></circle><text x={x(at(o[t]))+5} y={y(o[p])-8} fill={c} fontSize="12">{n}</text></g>)}</g>)}
    <text x="65" y="345" fill="var(--secondary)" fontSize="12">{barras[0].t.slice(11,16)}</text><text x="870" y="345" fill="var(--secondary)" fontSize="12">{barras.at(-1).t.slice(11,16)}</text>
  </svg>;
}

export function DashboardContent() {
  const {queries} = useDataApp();
  const ops = queries.operacoes?.rows ?? [];
  const allBars = queries.barras?.rows ?? [];
  const dias = useMemo(()=>[...new Set(ops.map(o=>o.data))], [ops]);
  const [dia,setDia] = useState('2025-01-02');
  const [limites,setLimites] = useState(false);
  const selected = dias.includes(dia) ? dia : dias[0];
  const diario = ops.filter(o=>o.data===selected);
  const barras = allBars.filter(b=>b.dia===selected);
  const totais = ['2023','2024','2025'].map(ano=>({ano, valor:ops.filter(o=>o.data.startsWith(ano)).reduce((s,o)=>s+o.resultado_brl,0)}));
  const total = totais.reduce((s,x)=>s+x.valor,0);
  const alvo = ops.filter(o=>o.motivo==='alvo').length, stop=ops.filter(o=>o.motivo==='stop').length;
  const op = diario[0];
  return <div className="pesquisa">
    <p className="nota">Desenvolvimento: 31 mar 2023 a 30 dez 2025 · 2023 parcial · 1 contrato · custos e derrapagem incluídos</p>
    <div className="numeros" data-reviewed-rows>
      <div><span>Resultado líquido</span><strong>{moeda(total)}</strong></div><div><span>Operações</span><strong>{num(ops.length)}</strong></div><div><span>Saídas no alvo</span><strong>{alvo}</strong></div><div><span>Saídas no stop</span><strong>{stop}</strong></div>
    </div>
    <DataComponent variant="card" id="resultado-anual" queryId="operacoes" kind="custom" title="Resultado líquido por ano" sourceRows={ops} displayRows={ops}>
      <div className="anuais" data-reviewed-rows>{totais.map(a=><div key={a.ano}><div className="ano">{a.ano}{a.ano==='2023'?' · parcial':''}</div><div className="barra"><i style={{width:`${Math.abs(a.valor)/Math.max(...totais.map(t=>Math.abs(t.valor)))*100}%`,background:a.valor<0?'#d25f57':'#18876e'}}/></div><b>{moeda(a.valor)}</b></div>)}</div>
      <p className="nota">O resultado foi positivo em dois anos, mas negativo em 2024. Isso ainda não demonstra consistência.</p>
    </DataComponent>
    <DataComponent variant="card" id="pregao" queryId="barras" queryIds={['barras','operacoes']} kind="custom" title="Examinar pregão" sourceRowsByQuery={{barras,operacoes:diario}} displayRows={barras}>
      <div className="controles"><label>Dia <select value={selected || ''} onChange={e=>setDia(e.target.value)}>{dias.map(d=><option key={d} value={d}>{d.split('-').reverse().join('/')}</option>)}</select></label><label><input type="checkbox" checked={limites} onChange={e=>setLimites(e.target.checked)}/> Mostrar níveis de alvo e stop</label></div>
      <Candle barras={barras} ops={diario} limites={limites}/>
      <p className="nota">Círculos: compra e saída simuladas. Marcas mostram a barra M5, não o instante exato. Ative os níveis para ver alvo e stop na mesma escala.</p>
      {op && <div className="detalhes" data-reviewed-rows>{diario.map((o,i)=><div key={i}>Compra {o.entrada_em.slice(11,16)} · {num(o.entrada)} pts &nbsp; | &nbsp; Saída {o.saida_em.slice(11,16)} · {num(o.saida)} pts ({o.motivo}) &nbsp; | &nbsp; {moeda(o.resultado_brl)}<br/>Alvo {num(o.alvo)} pts · Stop {num(o.stop)} pts</div>)}</div>}
    </DataComponent>
    <p className="nota">Regra: rompe máxima da barra anterior + 5 pontos; alvo 3%, stop 10%, zeragem na última barra. Não é resultado fora da amostra. Custos são hipóteses.</p>
  </div>;
}
