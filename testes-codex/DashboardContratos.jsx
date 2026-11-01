import React, { useMemo, useState } from 'react';
import { useDataApp, EvidenceChart, DataComponent, Dropdown, Section, SortableRegion, SortableItem } from '../../data-app-public.jsx';
import './dashboard.css';

const contracts = ['12/02 a 15/04', '16/04 a 17/06'];
const names = ['Médias 5/20','MACD 12/26/9','Estocástico 14/3/3','Fibogap','Pivô Fibonacci','Fibonacci duas etapas','Retração 38–50%','Rompimento e reteste'];
const brl = n => new Intl.NumberFormat('pt-BR', {style:'currency',currency:'BRL'}).format(n);
const shortDate = d => d.slice(8,10)+'/'+d.slice(5,7);

export function DashboardContent() {
  const { queries } = useDataApp();
  const rows = queries.operacoes?.rows ?? [];
  const [strategy,setStrategy] = useState(names[0]);
  const [contract,setContract] = useState(contracts[0]);
  const summary = useMemo(() => names.map(name => {
    const one = contracts.map(c => rows.filter(r => r.estrategia===name && r.contrato===c));
    return { estrategia:name, primeiro:one[0].reduce((s,r)=>s+r.resultado,0), segundo:one[1].reduce((s,r)=>s+r.resultado,0), n1:one[0].length, n2:one[1].length, origem:one[0][0]?.origem ?? '—' };
  }),[rows]);
  const selected = useMemo(() => rows.filter(r => r.estrategia===strategy && r.contrato===contract).sort((a,b)=>a.entrada.localeCompare(b.entrada)),[rows,strategy,contract]);
  const result = selected.reduce((s,r)=>s+r.resultado,0);
  const gains = selected.filter(r=>r.resultado>0).length;
  const curve = useMemo(() => { let total=0; const days = new Map(); selected.forEach(r=>days.set(r.data,(days.get(r.data)||0)+r.resultado)); return [...days].map(([data,valor])=>({data, resultado: total+=valor})); },[selected]);
  const last = [...selected].reverse().slice(0,15);
  return <div className="contratos-dashboard">
    <div className="contexto"><strong>Desenvolvimento · WIN · 2025</strong><span>Dois períodos de contrato da série contínua da Clear. Resultados líquidos para 1 contrato, com custos.</span></div>
    <p className="nota">O reteste foi executado novamente; as demais estratégias mostram operações das rodadas anteriores agrupadas por contrato. Não foram feitos novos backtests isolados.</p>
    <SortableRegion id="contratos:visao" variant="canvas" columns={12} spacing="standard" label="Painel de resultados" rows={[{id:'comparacao',items:['comparativo']},{id:'tabela',items:['tabela']},{id:'detalhes',items:['curva','operacoes']}]}>
      <SortableItem id="comparativo" label="Resultado por estratégia" kind="chart" span={12}>
        <EvidenceChart id="comparativo" queryId="operacoes" variant="card" title="Resultado por estratégia e contrato" description="Os dois resultados são comparados em reais; as estratégias representam simulações independentes." rows={summary} sourceRows={rows} height={360} spec={{type:'bar',x:'estrategia',y:'primeiro',fields:['primeiro','segundo'],stackable:false, currency:'BRL',legend:{labels:{primeiro:'12/02 a 15/04',segundo:'16/04 a 17/06'}},showXAxisLabel:false,showYAxisLabel:false}} />
      </SortableItem>
      <SortableItem id="tabela" label="Comparação detalhada" kind="table" span={12}>
        <DataComponent id="tabela" queryId="operacoes" title="Comparação detalhada" variant="card" kind="table" sourceRows={rows} displayRows={summary}>
          <div className="table-scroll"><table data-reviewed-rows><thead><tr><th>Estratégia</th><th>Operações<br/>12/02–15/04</th><th>Resultado<br/>12/02–15/04</th><th>Operações<br/>16/04–17/06</th><th>Resultado<br/>16/04–17/06</th><th>Origem</th></tr></thead><tbody>{summary.map(r=><tr key={r.estrategia}><td>{r.estrategia}</td><td>{r.n1}</td><td className={r.primeiro<0?'loss':'gain'}>{brl(r.primeiro)}</td><td>{r.n2}</td><td className={r.segundo<0?'loss':'gain'}>{brl(r.segundo)}</td><td>{r.origem}</td></tr>)}</tbody></table></div>
        </DataComponent>
      </SortableItem>
      <SortableItem id="curva" label="Resultado acumulado" kind="chart" span={7}>
        <EvidenceChart id="curva" queryId="operacoes" variant="card" title="Resultado acumulado" description="Soma das operações encerradas, agrupadas pela data de entrada; começa em zero em cada contrato." rows={curve} sourceRows={selected} height={290} spec={{type:'line',x:'data',y:'resultado',currency:'BRL',showXAxisLabel:false,showYAxisLabel:false}} headerControls={<><Dropdown label="Estratégia" showLabel value={strategy} choices={names} onChange={setStrategy}/><Dropdown label="Contrato" showLabel value={contract} choices={contracts} onChange={setContract}/></>} />
      </SortableItem>
      <SortableItem id="operacoes" label="Operações selecionadas" kind="table" span={5}>
        <DataComponent id="operacoes" queryId="operacoes" title="Operações selecionadas" variant="card" kind="table" sourceRows={selected} displayRows={last}>
          <div className="metricas"><div><span>Resultado líquido</span><strong className={result<0?'loss':'gain'}>{brl(result)}</strong></div><div><span>Operações</span><strong>{selected.length}</strong></div><div><span>Positivas</span><strong>{selected.length ? (100*gains/selected.length).toFixed(1).replace('.',',')+'%' : '—'}</strong></div></div>
          <p className="subtle">{strategy} · {contract} · Últimas 15 operações</p>
          <div className="table-scroll recent"><table data-reviewed-rows><thead><tr><th>Data</th><th>Saída</th><th>Resultado</th></tr></thead><tbody>{last.map((r,i)=><tr key={r.entrada+'-'+i}><td>{shortDate(r.data)}</td><td>{r.motivo}</td><td className={r.resultado<0?'loss':'gain'}>{brl(r.resultado)}</td></tr>)}</tbody></table></div>
        </DataComponent>
      </SortableItem>
    </SortableRegion>
    <div className="rodape"><strong>Como ler:</strong> as estratégias são simulações independentes; não some os resultados como se fossem uma carteira. A série contínua não representa toda a vida de cada contrato. Poucas operações, custos e hipóteses de execução limitam as conclusões.</div>
  </div>;
}
