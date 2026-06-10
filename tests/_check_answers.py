import json, sys, io
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

run_dir = Path(r'D:\SC2\SC2_DATA_Agen\result\deepseek-v4-flash_reasoning_english_20260609_204558')
summary = json.loads((run_dir / 'summary.json').read_text(encoding='utf-8'))

targets = ['T05_barracks_dependency_impact', 'T09_barracks_antiair', 'Z01_larva_morph_outputs', 'Z05_infestor_ability_profile']
for case_id in targets:
    row = [r for r in summary['rows'] if r['id'] == case_id][0]
    raw = json.loads((run_dir / 'raw' / (case_id + '.json')).read_text(encoding='utf-8'))
    answer = raw['result'].get('answer', '')
    status = 'PASS' if row['passed'] else 'FAIL'
    
    print('=== ' + case_id + ' [' + status + '] ===')
    print('Tools: ' + str(row['called_tools']))
    print('Answer (' + str(len(answer)) + ' chars):')
    print(answer[:1000])
    if len(answer) > 1000:
        print('... [' + str(len(answer) - 1000) + ' more chars]')
    print()
