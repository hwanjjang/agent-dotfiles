// @exec: {"yield_time_ms": 30000, "max_output_tokens": 3000}
const value=await tools.exec_command({cmd:"cat /runtime/qualification.js",workdir:"/work/project",login:false,yield_time_ms:1000,max_output_tokens:6000});
const r=typeof value==="string"?JSON.parse(value):value;
if(!r||r.exit_code!==0||(r.session_id!==undefined&&r.session_id!==null)||typeof r.output!=="string"||r.output.length!==EXPECTED_SCRIPT_BYTES||/[^\x00-\x7f]/.test(r.output))throw Error("qualification source read failed");
await eval("(async()=>{"+r.output+"\n})()");
