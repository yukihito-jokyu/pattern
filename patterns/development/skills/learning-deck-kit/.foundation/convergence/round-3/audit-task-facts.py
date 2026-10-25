"""作業コピーの要求事実を確認する。引数は測定のround-3ディレクトリ。"""
import json
import sys
from pathlib import Path
r=Path(sys.argv[1]).resolve()
results=[]
for task in ('T1-add','T2-change','T3-cross','H1-holdout'):
 base=r/task/'base'/'courses/go'
 for n in range(1,4):
  c=r/task/f'agent-{n}'/'courses/go'
  profile=json.loads((c/'profile.json').read_text())
  load=lambda name:json.loads((c/f'lessons/{name}/lesson.json').read_text())
  if task=='T1-add':
   item=profile['curriculum'][-1]; lesson=load('zero-values')
   assert item['id']=='zero-values' and item['goal']=='intのゼロ値が0であると説明できる' and item['dependsOn']==['variables']
   assert len(lesson['slides'])==2 and {'variables','short-declarations'} <= set(lesson['sources'])
   examples=[x for x in lesson['explanation'] if x['code']]
   assert any('var count int' in x['code'] and 'count =' not in x['code'] and x['output']=='Go: 0 lessons' for x in examples)
   assert '5' in lesson['exercise']['prompt'] and '5' in lesson['exercise']['answer']
   for name in ('variables','control-flow','functions'):
    assert (c/f'lessons/{name}/lesson.json').read_bytes()==(base/f'lessons/{name}/lesson.json').read_bytes()
  elif task=='T2-change':
   lesson=load('variables'); assert any(x['output']=='Go: 4 lessons' and 'count = 4' in x['code'] for x in lesson['explanation'])
   for name in ('control-flow','functions'):
    assert (c/f'lessons/{name}/lesson.json').read_bytes()==(base/f'lessons/{name}/lesson.json').read_bytes()
   assert (c/'profile.json').read_bytes()==(base/'profile.json').read_bytes()
  elif task=='T3-cross':
   assert (c/'profile.json').read_bytes()==(base/'profile.json').read_bytes()
   for name in ('variables','control-flow','functions'):
    lesson=load(name); assert 'release-history' in lesson['sources']
    assert lesson['explanation'][-1]=={'title':'版を確かめる','body':'この教材の対象はGo1.27です。利用中の版はgo versionで確認し、異なる版では公式リリース履歴も確認してください。','code':'','output':''}
  else:
   lesson=load('functions')
   assert any('remaining(5, 2)' in x['code'] and x['output']=='remaining 3' for x in lesson['explanation'])
   for name in ('variables','control-flow'):
    assert (c/f'lessons/{name}/lesson.json').read_bytes()==(base/f'lessons/{name}/lesson.json').read_bytes()
   old=json.loads((base/'profile.json').read_text())
   current=json.loads((c/'profile.json').read_text())
   for source in current['sources']:
    prior=next(x for x in old['sources'] if x['id']==source['id'])
    if source['id']=='function-declarations':
     assert source['checkedAt'] in (prior['checkedAt'],'2026-10-25')
     source['checkedAt']=prior['checkedAt']
   assert current==old
  results.append({'task':task,'agent':n,'facts':'passed'})
print(json.dumps({'status':'passed','runs':results},ensure_ascii=False,indent=2))
