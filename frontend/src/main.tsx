import React from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';

type Action={strategy_mode:string;title:string;weakness_target:string|null;pkg:any};
const mock=import.meta.env.VITE_USE_MOCK==='true';
const actions:Action[]=[{strategy_mode:'safe_bet',title:'검증된 생산성 팁 확장',weakness_target:null,pkg:{}},{strategy_mode:'growth_experiment',title:'후킹 개선 실험',weakness_target:'초반 3초 이탈',pkg:{}} ,{strategy_mode:'safe_bet',title:'튜토리얼 시리즈화',weakness_target:null,pkg:{}}];
function App(){return <main><header><h1>TrendPilot</h1>{mock&&<b className="mock">MOCK</b>}</header><section><h2>입력</h2><input placeholder="niche"/><input placeholder="audience"/><input placeholder="goal"/><input placeholder="content format"/><input placeholder="weekly production time"/><input placeholder="trend query"/><button>Run</button></section><section><h2>분석 결과</h2><p>관측 근거: 미확인</p><p>팔로워 변화: raw missing / relationship absent / rename / outside window / unresolved 구분</p></section><section><h2>콘텐츠 전략</h2>{actions.map(a=><article><strong>{a.strategy_mode==='safe_bet'?'SAFE BET':'GROWTH EXPERIMENT'}</strong><h3>{a.title}</h3>{a.weakness_target&&<p>weakness_target: {a.weakness_target}</p>}<Package/></article>)}</section></main>}
function Package(){return <div><h4>SCRIPT</h4><p>Hook Intro Body Ending CTA</p><h4>SHOT LIST</h4><p>장면·시간·화면·나레이션·자막</p><h4>EDITING GUIDE</h4><p>속도·자막·컷·음악 방향·B-roll</p><h4>THUMBNAIL PLAN</h4><p>콘셉트·문구·구성·프롬프트</p><h4>PUBLISHING PACKAGE</h4><p>제목·설명·해시태그·CTA·목표 지표</p><button>복사</button></div>}
createRoot(document.getElementById('root')!).render(<App/>);