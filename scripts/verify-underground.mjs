// Underground atlas v0.3: dependency-free, Node.js 20+.
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
export function validate(world,dm,previous=null,mergeBase=null,head=null){
  const kinds={areas:"AREA",nodes:"NODE",segments:"SEGMENT",routes:"ROUTE",facilities:"FACILITY",reports:"REPORT"};
  const errors=[],warnings=[],err=(m)=>errors.push(m),warn=(m)=>warnings.push(m);
  const obj=x=>x!==null&&typeof x==="object"&&!Array.isArray(x);
  const str=x=>typeof x==="string"&&x.trim().length>0;
  const arr=x=>Array.isArray(x)?x:[];
  const num=x=>typeof x==="number"&&Number.isFinite(x);
  const stable=x=>Array.isArray(x)?x.map(stable):obj(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,stable(x[k])])):x;
  const same=(a,b)=>JSON.stringify(stable(a))===JSON.stringify(stable(b));
  function collect(w,d,check=false){
    const map=new Map();
    for(const [atlas,scope] of [[w,"world"],[d,"dm"]]){
      if(!obj(atlas)||!["0.2","0.3"].includes(atlas.version)){if(check)err(`${scope}: invalid atlas version`);continue}
      for(const [group,kind] of Object.entries(kinds)){
        if(group==="areas"&&atlas.version==="0.2"&&atlas[group]===undefined)continue;
        if(!Array.isArray(atlas[group])){if(check)err(`${scope}.${group}: expected array`);continue}
        for(const r of atlas[group]){
          if(!obj(r)||!str(r.id)){if(check)err(`${scope}.${group}: missing id`);continue}
          if(map.has(r.id)){if(check)err(`duplicate id ${r.id}`);continue}
          map.set(r.id,{r,scope,group,kind});
        }
      }
    }return map;
  }
  const map=collect(world,dm,true);
  function ref(owner,id,group,active=true){
    if(!str(id)||!map.has(id)){err(`${owner.r.id}: unknown reference ${id}`);return null}
    const x=map.get(id);
    if(group&&x.group!==group){err(`${owner.r.id}: wrong reference type ${id}`);return null}
    if(owner.scope==="world"&&x.scope==="dm"){err(`${owner.r.id}: world -> dm reference ${id}`);return null}
    if(active&&x.r.lifecycle!=="active"){err(`${owner.r.id}: inactive reference ${id}`);return null}
    return x;
  }
  function chain(owner,steps,active=true){
    if(!Array.isArray(steps)||!steps.length){err(`${owner.r.id}: empty segment chain`);return null}
    let first,last;
    for(let i=0;i<steps.length;i++){
      const step=steps[i];
      if(!obj(step)||!["forward","reverse"].includes(step.direction)){err(`${owner.r.id}: invalid step direction`);return null}
      const x=ref(owner,step.segment,"segments",active);if(!x)return null;
      const a=step.direction==="forward"?x.r.from:x.r.to,b=step.direction==="forward"?x.r.to:x.r.from;
      if(a===null){err(`${owner.r.id}: unknown start in chain`);return null}
      if(i&& (last===null||last!==a)){err(`${owner.r.id}: disconnected segment chain`);return null}
      if(!i)first=a;last=b;
    }return [first,last];
  }
  const numbers=new Set();
  for(const x of map.values()){
    const {r,scope,group,kind}=x;
    const prefix=kind+":";
    if(r.registration==="pending"){if(!/^tmp:[a-z0-9_-]+:[a-z0-9_-]+$/i.test(r.id))err(`${r.id}: invalid temporary key`)}
    else if(r.registration==="named"){if(!r.id.startsWith(prefix)||r.id!==prefix+r.name||!str(r.name)||/^\d+$/.test(r.name))err(`${r.id}: named id must match registered name`)}
    else if(r.registration==="numbered"){if(!r.id.startsWith(prefix)||!/^[1-9]\d*$/.test(r.id.slice(prefix.length)))err(`${r.id}: invalid numbered key`)}
    else err(`${r.id}: invalid registration`);
    if(!["accepted","provisional"].includes(r.approval))err(`${r.id}: unapproved record`);
    if(!["active","retired"].includes(r.lifecycle))err(`${r.id}: invalid lifecycle`);
    if(!str(r.source))err(`${r.id}: missing source`);
    if(!Array.isArray(r.history))err(`${r.id}: missing history`);
    for(const h of arr(r.history))if(!obj(h)||!str(h.at)||!str(h.reason)||!str(h.source)||!["world_change","correction","registration","survey","reorganization","knowledge","approval"].includes(h.kind))err(`${r.id}: invalid history entry`);
    if(r.lifecycle==="retired"){
      if(!obj(r.retirement)||!str(r.retirement.at)||!str(r.retirement.reason)||!Array.isArray(r.retirement.successors))err(`${r.id}: missing retirement history`);
      else {
        for(const s of r.retirement.successors){const id=typeof s==="string"?s:s?.segment;ref(x,id,group,false);if(id===r.id)err(`${r.id}: self successor`)}
        if(group==="segments"&&r.retirement.successors.length){
          const endpoints=chain(x,r.retirement.successors,false);
          if(endpoints&&r.retirement.reason==="split"&&(endpoints[0]!==r.from||endpoints[1]!==r.to))err(`${r.id}: split endpoints changed`);
        }
      }
    }else if(r.retirement)err(`${r.id}: active record has retirement`);
    const active=r.lifecycle==="active";
    if(group==="areas"){
      if(!["approximate","surveyed","unknown"].includes(r.geometry))err(`${r.id}: invalid area geometry`);
      if(r.datum!==null&&!str(r.datum))err(`${r.id}: invalid area datum`);
      if(r.outline_xy_m!==null&&(!Array.isArray(r.outline_xy_m)||r.outline_xy_m.length<3||!r.outline_xy_m.every(p=>Array.isArray(p)&&p.length===2&&p.every(num))))err(`${r.id}: invalid area outline`);
      if(!Array.isArray(r.terrain))err(`${r.id}: invalid terrain collection`);
      const keys=new Set();for(const t of arr(r.terrain)){if(!str(t.key)||keys.has(t.key)||!["line","polygon"].includes(t.geometry)||!Array.isArray(t.xy_m)||t.xy_m.length<(t.geometry==="polygon"?3:2)||!t.xy_m.every(p=>Array.isArray(p)&&p.length===2&&p.every(num)))err(`${r.id}: invalid terrain feature`);keys.add(t.key)}
    }
    if(r.area!=null){const a=ref(x,r.area,"areas",active);if(group==="nodes"&&r.position&&a&&r.position.datum!==a.r.datum)err(`${r.id}: area datum mismatch`)}
    if(group==="nodes"){
      if(!str(r.kind))err(`${r.id}: missing node kind`);
      if(r.position!==null&&r.position!==undefined&&(!obj(r.position)||!str(r.position.datum)||!["x","y","z"].every(k=>num(r.position[k]))))err(`${r.id}: invalid position`);
    }
    if(group==="segments"){
      const origin=ref(x,r.from,"nodes",active);
      if(r.destination_area!=null)ref(x,r.destination_area,"areas",active);
      if(r.origin_area!=null)ref(x,r.origin_area,"areas",active);
      if(r.origin_area&&origin?.r.area!==r.origin_area)err(`${r.id}: origin area mismatch`);
      if(r.terminal_kind==="known_area_connection"&&r.destination_area==null)err(`${r.id}: missing destination area`);
      if(r.terminal_kind==="observed_opening"&&r.destination_area!=null)err(`${r.id}: opening claims known destination`);
      if(r.area&&origin?.r.area!==r.area)err(`${r.id}: local segment origin area mismatch`);
      if(r.area&&r.to!==null&&map.get(r.to)?.r.area!==r.area)err(`${r.id}: local segment endpoint area mismatch`);
      if(r.to!==null)ref(x,r.to,"nodes",active);
      if(!["schematic","surveyed","approximate","unknown"].includes(r.geometry))err(`${r.id}: invalid geometry`);
      if(r.length_m!==null&&(!num(r.length_m)||r.length_m<0))err(`${r.id}: invalid length`);
      if(r.elevation_change_m!==null&&!num(r.elevation_change_m))err(`${r.id}: invalid elevation`);
      if(num(r.length_m)&&num(r.elevation_change_m)&&Math.abs(r.elevation_change_m)>r.length_m+1e-6)err(`${r.id}: elevation exceeds length`);
      if(!Array.isArray(r.methods))err(`${r.id}: missing methods`);
      for(const m of arr(r.methods)){
        if(!obj(m)||!str(m.mode)||!["both","forward","reverse"].includes(m.direction)||!["passable","restricted","blocked","unknown"].includes(m.state)){err(`${r.id}: invalid method`);continue}
        if(m.facility!==null&&m.facility!==undefined){
          const f=ref(x,m.facility,"facilities",active);
          if(f&&active&&!arr(f.r.segments).includes(r.id))err(`${r.id}: facility backlink missing`);
        }
      }
      if(r.refines!==undefined){
        const p=ref(x,r.refines,"segments",true);
        if(scope!=="dm"||!p||p.scope!=="world"||p.r.to!==null||p.r.from!==r.from||r.to===null)err(`${r.id}: invalid DM refinement`);
      }
    }
    if(group==="routes"){
      if(active)chain(x,r.steps,true);else chain(x,r.steps,false);
      if(r.registration==="numbered"){const n=r.id.slice(prefix.length);if(numbers.has(n))err(`${r.id}: duplicate route number`);numbers.add(n)}
    }
    if(group==="facilities"){
      if(!str(r.kind)||!["operational","failed","closed","unknown","building"].includes(r.state))err(`${r.id}: invalid facility`);
      if(!Array.isArray(r.nodes)||!Array.isArray(r.segments)||(!arr(r.nodes).length&&!arr(r.segments).length))err(`${r.id}: missing facility placement`);
      for(const n of arr(r.nodes))ref(x,n,"nodes",active);
      for(const s of arr(r.segments))ref(x,s,"segments",active);
    }
    if(group==="reports"){
      if(!str(r.observer)||!str(r.observed_at)||!(r.reported_at===null||str(r.reported_at))||!Array.isArray(r.knowledge_holders)||!r.knowledge_holders.every(str)||!["observed","surveyed","reported","inferred"].includes(r.certainty)||!str(r.claim)||!Array.isArray(r.subjects)||!r.subjects.length)err(`${r.id}: invalid report`);
      for(const subject of arr(r.subjects))ref(x,subject,null,false);
    }
  }
  // Successor graph must remain acyclic, including temporary -> formal mappings.
  const visiting=new Set(),done=new Set();
  function visit(id){if(done.has(id))return;if(visiting.has(id)){err(`successor cycle ${id}`);return}visiting.add(id);const r=map.get(id)?.r;for(const s of arr(r?.retirement?.successors)){const n=typeof s==="string"?s:s?.segment;if(map.has(n))visit(n)}visiting.delete(id);done.add(id)}
  for(const id of map.keys())visit(id);
  const refined=new Set();for(const {r} of map.values())if(r.lifecycle==="active"&&r.refines){if(refined.has(r.refines))err(`duplicate DM refinement ${r.refines}`);refined.add(r.refines)}
  // Only exact, same-datum signed elevation differences participate.
  const adjacency=new Map();
  function edge(a,b,d){if(!adjacency.has(a))adjacency.set(a,[]);adjacency.get(a).push([b,d])}
  for(const {r,group} of map.values())if(group==="segments"&&r.lifecycle==="active"&&r.to!==null&&r.elevation_precision==="exact"&&str(r.elevation_datum)&&num(r.elevation_change_m)){const a=r.elevation_datum+"|"+r.from,b=r.elevation_datum+"|"+r.to;edge(a,b,r.elevation_change_m);edge(b,a,-r.elevation_change_m)}
  const z=new Map();for(const a of adjacency.keys()){if(z.has(a))continue;z.set(a,0);const q=[a];for(let i=0;i<q.length;i++)for(const [b,d] of adjacency.get(q[i])){const value=z.get(q[i])+d;if(z.has(b)){if(Math.abs(z.get(b)-value)>1e-6)err(`inconsistent exact elevation loop ${a} -> ${b}`)}else{z.set(b,value);q.push(b)}}}
  if(previous){
    const old=collect(previous.world,previous.dm);
    for(const [id,x] of old){
      const y=map.get(id);if(!y){err(`deleted historical id ${id}`);continue}
      if(x.group!==y.group)err(`changed entity type ${id}`);
      if(x.r.lifecycle==="retired"&&!same(x.r,y.r))err(`modified retired record ${id}`);
      if(x.group==="reports"&&!same(x.r,y.r))err(`modified original report ${id}; append a correction report`);
      if(x.scope==="world"&&y.scope==="dm")warn(`world -> dm move ${id}; previous public exposure remains`);
      if(!same(x.r,y.r)||x.scope!==y.scope){
        const prior=arr(x.r.history),next=arr(y.r.history);
        if(next.length<=prior.length||!same(next.slice(0,prior.length),prior))err(`missing append-only change history ${id}`);
      }
    }
  }
  if(previous&&mergeBase&&head){
    const base=collect(mergeBase.world,mergeBase.dm),target=collect(previous.world,previous.dm),incoming=collect(head.world,head.dm);
    for(const [id,b] of incoming){
      const a=target.get(id),old=base.get(id);
      if(a&&!old)err(`parallel allocation collision ${id}`);
      else if(a&&old&&(!same(a.r,old.r)||a.scope!==old.scope)&&(!same(b.r,old.r)||b.scope!==old.scope)&&(!same(a.r,b.r)||a.scope!==b.scope))err(`parallel edit conflict ${id}`);
    }
  }
  return {errors:[...new Set(errors)],warnings:[...new Set(warnings)]};
}
export function usable(segment,mode,direction,facilities){
  if(segment.lifecycle!=="active"||segment.geometry==="schematic")return false;
  return (segment.methods??[]).some(m=>m.mode===mode&&(m.direction==="both"||m.direction===direction)&&m.state==="passable"&&(!m.facility||facilities.some(f=>f.id===m.facility&&f.lifecycle==="active"&&f.state==="operational")));
}
const paths={world:"world/underground/atlas.json",dm:"dm/underground/atlas.json"};
const empty=()=>({version:"0.2",nodes:[],segments:[],routes:[],facilities:[],reports:[]});
function snapshot(ref=null){
  return Object.fromEntries(Object.entries(paths).map(([k,p])=>{
    if(!ref)return [k,JSON.parse(readFileSync(p,"utf8"))];
    const found=execFileSync("git",["ls-tree","--name-only",ref,"--",p],{encoding:"utf8"}).trim();
    return [k,found?JSON.parse(execFileSync("git",["show",ref+":"+p],{encoding:"utf8"})):empty()];
  }));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  const args=process.argv.slice(2),get=name=>{const i=args.indexOf(name);return i<0?null:args[i+1]};
  const current=snapshot(),base=get("--target"),head=get("--head"),ancestor=get("--merge-base");
  if([base,head,ancestor].some(Boolean)&&![base,head,ancestor].every(Boolean))throw Error("Provide --target, --head and --merge-base together");
  const result=validate(current.world,current.dm,base?snapshot(base):null,ancestor?snapshot(ancestor):null,head?snapshot(head):null);
  for(const e of result.errors)console.error("ERROR:",e);
  for(const w of result.warnings)console.warn("WARN:",w);
  console.log("Atlas:",result.errors.length,"errors,",result.warnings.length,"warnings");
  if(result.errors.length)process.exitCode=1;
}
