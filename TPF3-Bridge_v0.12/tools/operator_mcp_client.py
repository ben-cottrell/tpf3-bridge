"""Call the local operator through actual stdio MCP; no model or network calls."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

from mcp import Client, StdioServerParameters

ROOT=Path(__file__).resolve().parents[1]

async def call(tool,arguments,output):
    async with Client(StdioServerParameters(command=sys.executable,args=['-u',str(ROOT/'bridge_operator_mcp.py')],cwd=str(ROOT)),read_timeout_seconds=30) as client:
        if tool=='list':
            listing=await client.list_tools();data={'tools':[t.name for t in listing.tools]}
        else:
            reply=await client.call_tool(tool,arguments,read_timeout_seconds=600);data=reply.model_dump(mode='json',exclude_none=True)
        if output:
            output.parent.mkdir(parents=True,exist_ok=True)
            with output.open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2)
        text=json.dumps(data,separators=(',',':'))
        print(text if len(text.encode())<=4096 else json.dumps({'status':'output_saved','evidence':str(output),'bytes':len(text.encode())}))
        failed=data.get('is_error',data.get('isError',False))
        if tool!='list':
            for item in data.get('content',[]):
                if item.get('type')=='text':
                    try:status=json.loads(item['text']).get('status')
                    except (ValueError,AttributeError):continue
                    failed=failed or status not in ('ok','planned','built','reviewed')
        return 1 if failed else 0

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('tool');parser.add_argument('--input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();payload=json.loads(args.input.read_text(encoding='utf-8-sig')) if args.input else {}
    return asyncio.run(call(args.tool,payload,args.output))

if __name__=='__main__':raise SystemExit(main())
