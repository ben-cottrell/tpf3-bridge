"""Call the local operator through actual stdio MCP; no model or network calls."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]

def semantic_result(data):
    """Decode tool text for stdout without changing the full protocol record."""
    if 'tools' in data:return data,False
    decoded=[];messages=[]
    for item in data.get('content',[]):
        if item.get('type')!='text':continue
        messages.append(item['text'])
        try:value=json.loads(item['text'])
        except ValueError:continue
        if isinstance(value,dict):decoded.append(value)
    protocol_error=bool(data.get('is_error',data.get('isError',False)))
    if len(decoded)==1:result=decoded[0]
    elif decoded:result={'status':'error' if protocol_error else 'results','results':decoded}
    else:result={'status':'error' if protocol_error else 'result','message':' '.join(messages)[:500]}
    if protocol_error:
        result['status']='error';result.setdefault('error','MCP tool error')
    failed=protocol_error or any(v.get('status') not in ('ok','planned','built','reviewed') for v in decoded)
    return result,failed

def compact_stdout(result,output):
    text=json.dumps(result,separators=(',',':'),ensure_ascii=False)
    if len(text.encode('utf-8'))<=4096:return text
    return json.dumps({'status':result.get('status','output_saved'),'output_saved':output is not None,
                      'evidence':str(output) if output else None,'bytes':len(text.encode('utf-8'))},separators=(',',':'))

async def call(tool,arguments,output):
    from mcp import Client, StdioServerParameters
    async with Client(StdioServerParameters(command=sys.executable,args=['-u',str(ROOT/'bridge_operator_mcp.py')],cwd=str(ROOT)),read_timeout_seconds=30) as client:
        if tool=='list':
            listing=await client.list_tools();data={'tools':[t.name for t in listing.tools]}
        else:
            reply=await client.call_tool(tool,arguments,read_timeout_seconds=600);data=reply.model_dump(mode='json',exclude_none=True)
        if output:
            output.parent.mkdir(parents=True,exist_ok=True)
            with output.open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2)
        result,failed=semantic_result(data)
        print(compact_stdout(result,output))
        return 1 if failed else 0

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('tool');parser.add_argument('--input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();payload=json.loads(args.input.read_text(encoding='utf-8-sig')) if args.input else {}
    return asyncio.run(call(args.tool,payload,args.output))

if __name__=='__main__':raise SystemExit(main())
