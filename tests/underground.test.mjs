import { readFileSync } from 'node:fs';
import { validate, usable } from '../scripts/verify-underground.mjs';
function runCases(validate,usable,world,dm){
  const copy=x=>JSON.parse(JSON.stringify(x)), cases=[];
  const test=(name,fn)=>{if(!fn())throw new Error("FAILED "+name);cases.push(name)};
  const w=()=>copy(world),d=()=>copy(dm),good=(a,b=d())=>validate(a,b).errors.length===0;
  const bad=(a,b=d(),p=null,mb=null,h=null,part="")=>validate(a,b,p,mb,h).errors.some(e=>e.includes(part));
  const base={approval:"accepted",lifecycle:"active",registration:"numbered",source:"synthetic fixture",history:[]};
  const node=(id)=>({...base,id,kind:"junction",position:null,name:null});
  const seg=(id,from,to,elevation=null)=>({...base,id,from,to,geometry:"surveyed",length_m:100,elevation_change_m:elevation,elevation_precision:"exact",elevation_datum:"fixture",methods:[]});
  const route=(id,steps)=>({...base,id,steps});
  const step=(segment,direction="forward")=>({segment,direction});
  const hist={kind:"reorganization",at:"test:2",reason:"fixture",source:"fixture"};
  const network=()=>{const a=w();a.nodes.push(node("NODE:1"),node("NODE:2"),node("NODE:3"));a.segments.push(seg("SEGMENT:1","NODE:1","NODE:2",-30),seg("SEGMENT:2","NODE:2","NODE:3",-10));a.routes.push(route("ROUTE:1",[step("SEGMENT:1"),step("SEGMENT:2")]));return a};
  test("initial canonical seed",()=>good(w()));
  test("unknown terminus",()=>{const a=network();a.segments.push(seg("SEGMENT:3","NODE:3",null));a.routes[0].steps.push(step("SEGMENT:3"));return good(a)});
  test("unknown middle rejected",()=>{const a=network();a.segments[3].to=null;return bad(a,d(),null,null,null,"disconnected")});
  test("missing reference",()=>{const a=network();a.segments[3].from="NODE:99";return bad(a,d(),null,null,null,"unknown reference")});
  test("duplicate id",()=>{const a=network();a.nodes.push(node("NODE:1"));return bad(a,d(),null,null,null,"duplicate id")});
  test("reverse order rejected",()=>{const a=network();a.routes[0].steps=[step("SEGMENT:1","reverse"),step("SEGMENT:2","reverse")];return bad(a,d(),null,null,null,"disconnected")});
  test("valid reverse",()=>{const a=network();a.routes[0].steps=[step("SEGMENT:2","reverse"),step("SEGMENT:1","reverse")];return good(a)});
  test("exact elevation contradiction",()=>{const a=network();a.segments.push(seg("SEGMENT:3","NODE:3","NODE:1",20));return bad(a,d(),null,null,null,"elevation loop")});
  test("exact elevation closure",()=>{const a=network();a.segments.push(seg("SEGMENT:3","NODE:3","NODE:1",40));return good(a)});
  test("unknown elevation",()=>{const a=network();a.segments.push(seg("SEGMENT:3","NODE:3","NODE:1",null));return good(a)});
  test("negative length",()=>{const a=network();a.segments[3].length_m=-1;return bad(a,d(),null,null,null,"invalid length")});
  test("missing source",()=>{const a=network();a.nodes[4].source="";return bad(a,d(),null,null,null,"missing source")});
  test("world dm boundary",()=>{const a=network(),b=d();b.nodes.push(node("NODE:99"));a.segments[3].to="NODE:99";return bad(a,b,null,null,null,"world -> dm")});
  test("dm can reference world",()=>{const a=network(),b=d();b.nodes.push(node("NODE:99"));b.segments.push(seg("SEGMENT:99","NODE:3","NODE:99"));return good(a,b)});
  test("DM refinement",()=>{const a=network(),b=d();a.segments.push(seg("SEGMENT:3","NODE:3",null));b.nodes.push(node("NODE:99"));b.segments.push({...seg("SEGMENT:99","NODE:3","NODE:99"),refines:"SEGMENT:3"});return good(a,b)});
  test("temporary promotion and old id retained",()=>{const a=network(),b=d();b.nodes.push({...node("tmp:test:opening"),registration:"pending"});const old={world:copy(a),dm:copy(b)};b.nodes[0].lifecycle="retired";b.nodes[0].retirement={at:"test:2",reason:"registration",successors:["NODE:99"]};b.nodes[0].history.push(hist);b.nodes.push(node("NODE:99"));return validate(a,b,old).errors.length===0});
  test("split updates shared reverse route",()=>{const a=network();a.routes.push(route("ROUTE:2",[step("SEGMENT:1","reverse")]));const old={world:copy(a),dm:d()};a.nodes.push(node("NODE:4"));const s=a.segments[3];s.lifecycle="retired";s.retirement={at:"test:2",reason:"split",successors:[step("SEGMENT:3"),step("SEGMENT:4")]};s.history.push(hist);a.segments.push(seg("SEGMENT:3","NODE:1","NODE:4",-10),seg("SEGMENT:4","NODE:4","NODE:2",-20));a.routes[0].steps=[step("SEGMENT:3"),step("SEGMENT:4"),step("SEGMENT:2")];a.routes[1].steps=[step("SEGMENT:4","reverse"),step("SEGMENT:3","reverse")];a.routes.forEach(r=>r.history.push(hist));return validate(a,d(),old).errors.length===0});
  test("history protects existing id",()=>{const a=network(),old={world:copy(a),dm:d()};a.nodes[4].name="changed";return bad(a,d(),old,null,null,"missing append-only")});
  test("old id cannot vanish",()=>{const a=network(),old={world:copy(a),dm:d()};a.nodes.push(node("NODE:4"));old.world.nodes.push(node("NODE:99"));return bad(a,d(),old,null,null,"deleted historical")});
  test("retired id cannot be revived",()=>{const a=network();a.nodes.push({...node("NODE:99"),lifecycle:"retired",retirement:{at:"test:1",reason:"obsolete",successors:[]}});const old={world:copy(a),dm:d()};a.nodes.at(-1).lifecycle="active";delete a.nodes.at(-1).retirement;a.nodes.at(-1).history.push(hist);return bad(a,d(),old,null,null,"modified retired")});
  test("parallel collision",()=>{const a=network(),b=network(),c=network();b.nodes.push(node("NODE:99"));c.nodes.push({...node("NODE:99"),name:"other"});return bad(c,d(),{world:b,dm:d()},{world:a,dm:d()},{world:c,dm:d()},"parallel allocation")});
  test("conflicting reports coexist",()=>{const a=network();for(let i=1;i<=2;i++)a.reports.push({...base,id:"REPORT:"+i,observer:"party"+i,observed_at:"test:1",reported_at:null,knowledge_holders:["party"+i],certainty:"reported",claim:i===1?"40m":"90m",subjects:["SEGMENT:1"]});return good(a)});
  test("report remains immutable",()=>{const a=network();a.reports.push({...base,id:"REPORT:1",observer:"party",observed_at:"test:1",reported_at:null,knowledge_holders:["party"],certainty:"observed",claim:"40m",subjects:["SEGMENT:1"]});const old={world:copy(a),dm:d()};a.reports[0].claim="90m";return bad(a,d(),old,null,null,"modified original report")});
  test("facility failure leaves rope",()=>{const s=seg("SEGMENT:5","NODE:1","NODE:2");s.methods=[{mode:"rope",direction:"both",state:"passable"},{mode:"lift",direction:"both",state:"passable",facility:"FACILITY:8"}];const f={...base,id:"FACILITY:8",state:"failed"};return usable(s,"rope","forward",[f])&&!usable(s,"lift","forward",[f])});
  test("schematic link not navigable",()=>!usable(world.segments[0],"lift","forward",world.facilities));
  return cases;
}
const world=JSON.parse(readFileSync('world/underground/atlas.json','utf8'));
const dm=JSON.parse(readFileSync('dm/underground/atlas.json','utf8'));
// Seed fixtures are isolated from real atlas evolution.
const fixtureWorld={
  "version": "0.2",
  "nodes": [
    {
      "id": "tmp:seed:surface",
      "name": "ルオスエン（地上側）",
      "registration": "pending",
      "approval": "accepted",
      "lifecycle": "active",
      "source": "world/02_マナ・魔石・迷宮と社会.md#採用地下交通拠点ターミナルの構造名称開拓用語2026-11-24作者決定改訂",
      "history": [],
      "kind": "surface_access",
      "position": null
    },
    {
      "id": "NODE:TERMINAL",
      "name": "TERMINAL",
      "registration": "named",
      "approval": "accepted",
      "lifecycle": "active",
      "source": "world/02_マナ・魔石・迷宮と社会.md#採用地下交通拠点ターミナルの構造名称開拓用語2026-11-24作者決定改訂",
      "history": [],
      "kind": "transport_hub",
      "position": null
    },
    {
      "id": "NODE:PORT",
      "name": "PORT",
      "registration": "named",
      "approval": "accepted",
      "lifecycle": "active",
      "source": "world/02_マナ・魔石・迷宮と社会.md#採用地下交通拠点ターミナルの構造名称開拓用語2026-11-24作者決定改訂",
      "history": [],
      "kind": "port",
      "position": null
    },
    {
      "id": "NODE:GATE",
      "name": "GATE",
      "registration": "named",
      "approval": "accepted",
      "lifecycle": "active",
      "source": "world/02_マナ・魔石・迷宮と社会.md#採用地下交通拠点ターミナルの構造名称開拓用語2026-11-24作者決定改訂",
      "history": [],
      "kind": "gate",
      "position": null
    }
  ],
  "segments": [
    {
      "id": "tmp:seed:home-link",
      "name": null,
      "registration": "pending",
      "approval": "accepted",
      "lifecycle": "active",
      "source": "world/02_マナ・魔石・迷宮と社会.md#採用地下交通拠点ターミナルの構造名称開拓用語2026-11-24作者決定改訂",
      "history": [],
      "from": "tmp:seed:surface",
      "to": "NODE:TERMINAL",
      "geometry": "schematic",
      "length_m": null,
      "elevation_change_m": null,
      "methods": [
        {
          "mode": "lift",
          "direction": "both",
          "state": "unknown",
          "facility": "FACILITY:HOME",
          "condition": null
        }
      ],
      "note": "地上とターミナルの接続を表す概念区間。乗降場の正確な位置は未決。"
    },
    {
      "id": "tmp:seed:port-access",
      "name": null,
      "registration": "pending",
      "approval": "accepted",
      "lifecycle": "active",
      "source": "world/02_マナ・魔石・迷宮と社会.md#採用地下交通拠点ターミナルの構造名称開拓用語2026-11-24作者決定改訂",
      "history": [],
      "from": "NODE:TERMINAL",
      "to": "NODE:PORT",
      "geometry": "schematic",
      "length_m": null,
      "elevation_change_m": null,
      "methods": [],
      "note": "ターミナルにおける港への機能的接続。具体的な動線は未決。"
    },
    {
      "id": "tmp:seed:gate-access",
      "name": null,
      "registration": "pending",
      "approval": "accepted",
      "lifecycle": "active",
      "source": "world/02_マナ・魔石・迷宮と社会.md#採用地下交通拠点ターミナルの構造名称開拓用語2026-11-24作者決定改訂",
      "history": [],
      "from": "NODE:TERMINAL",
      "to": "NODE:GATE",
      "geometry": "schematic",
      "length_m": null,
      "elevation_change_m": null,
      "methods": [],
      "note": "徒歩探索への機能的接続。具体的な動線は未決。"
    }
  ],
  "routes": [],
  "facilities": [
    {
      "id": "FACILITY:HOME",
      "name": "HOME",
      "registration": "named",
      "approval": "accepted",
      "lifecycle": "active",
      "source": "world/02_マナ・魔石・迷宮と社会.md#採用地下交通拠点ターミナルの構造名称開拓用語2026-11-24作者決定改訂",
      "history": [],
      "kind": "lift",
      "nodes": [],
      "segments": [
        "tmp:seed:home-link"
      ],
      "state": "unknown",
      "note": "既存設定上の大昇降機そのもの。運行状況・乗降場詳細は未決。"
    }
  ],
  "reports": []
};
const fixtureDm={
  "version": "0.2",
  "nodes": [],
  "segments": [],
  "routes": [],
  "facilities": [],
  "reports": []
};
const cases=runCases(validate,usable,fixtureWorld,fixtureDm);
const actual=validate(world,dm);
if(actual.errors.length)throw Error(actual.errors.join('\n'));
for(const name of cases)console.log("PASS",name);
console.log(cases.length+" synthetic cases passed; current atlas validated");
