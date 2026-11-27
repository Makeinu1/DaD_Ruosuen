// Reference helper for an agent host exposing Files read and GitHub create_blob.
// Pass only an actual exported packet file ID and locally computed manifest.
// This does not run in ordinary Node without adapters; no credential extraction.
// Returns a verified blob SHA; the caller must separately commit and verify the tree.
async function uploadPacket(tools, repository, fileId, manifest) {
  const {rows, row_width: width, base64_length: total, bytes, git_blob_sha1: expected} = manifest;
  if (!Number.isSafeInteger(bytes) || bytes <= 0 || bytes > 10*1024*1024 ||
      width !== 8192 || total !== 4*Math.ceil(bytes/3) ||
      rows !== Math.ceil(total/width) || !/^[0-9a-f]{40}$/.test(expected))
    throw Error("invalid manifest");
  const chunks = new Map();
  const requests = Array.from({length:Math.ceil((rows+1)/30)}, (_,i)=>({
    ref_id:fileId,mode:"full",start_line:1+i*30,max_lines:30,include_images:false
  }));
  for(let i=0;i<requests.length;i+=5) {
    const batch=requests.slice(i,i+5);
    const result=await tools.files__read({read:batch});
    if(result.results.length!==batch.length) throw Error("missing read result");
    for(const a of result.results) {
      for(const line of a.content.filter(x=>typeof x==="string").join("\n").split("\n")) {
        if(!/^\d+,/.test(line)) continue;
        const [idx,v,...extra]=line.split(",");
        const j=Number(idx);
        const length=j===rows-1?total-width*j:width;
        if(extra.length||chunks.has(j)||j<0||j>=rows||
           !/^[A-Za-z0-9+/]+={0,2}$/.test(v)||v.length!==length||
           (j!==rows-1&&v.includes("="))) throw Error("invalid packet row "+j);
        chunks.set(j,v);
      }
    }
  }
  if(chunks.size!==rows) throw Error("missing packet rows");
  const encoded=Array.from({length:rows},(_,i)=>chunks.get(i)).join("");
  if(encoded.length!==total) throw Error("packet length mismatch");
  const result=await tools.mcp__GitHub__create_blob({
    repository_full_name:repository,content:encoded,encoding:"base64"
  });
  if(result.result.sha!==expected) throw Error("Git blob SHA mismatch");
  return result.result.sha;
}
