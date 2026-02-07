#!/usr/bin/env python3
import zipfile, xml.etree.ElementTree as ET, re, json, os, sys
from collections import defaultdict

if len(sys.argv) < 2:
    print('用法: python3 update_data.py /path/to/价格表.xlsx')
    sys.exit(1)

path = sys.argv[1]
if not os.path.exists(path):
    print('找不到文件:', path)
    sys.exit(1)

out_dir = os.path.dirname(os.path.abspath(__file__))

with zipfile.ZipFile(path) as z:
    names = z.namelist()
    sst = []
    if 'xl/sharedStrings.xml' in names:
        xml = z.read('xl/sharedStrings.xml')
        root = ET.fromstring(xml)
        ns = {'a':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        for si in root.findall('a:si', ns):
            texts = []
            for t in si.findall('.//a:t', ns):
                texts.append(t.text or '')
            sst.append(''.join(texts))

    def col_to_index(col):
        idx = 0
        for c in col:
            idx = idx*26 + (ord(c)-64)
        return idx-1

    def parse_sheet(sheet_name):
        xml = z.read(sheet_name)
        root = ET.fromstring(xml)
        ns = {'a':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        rows = defaultdict(dict)
        max_col = 0
        max_row = 0
        for row in root.findall('a:sheetData/a:row', ns):
            r_idx = int(row.get('r'))
            max_row = max(max_row, r_idx)
            for c in row.findall('a:c', ns):
                cell_ref = c.get('r')
                m = re.match(r'([A-Z]+)(\d+)', cell_ref)
                if not m:
                    continue
                col = m.group(1)
                col_idx = col_to_index(col)
                max_col = max(max_col, col_idx)
                v = c.find('a:v', ns)
                t = c.get('t')
                if v is None:
                    val = ''
                else:
                    raw = v.text or ''
                    if t == 's':
                        val = sst[int(raw)] if raw.isdigit() else raw
                    else:
                        val = raw
                rows[r_idx][col_idx] = val
        dense = []
        for r in range(1, max_row+1):
            row = [rows[r].get(c, '') for c in range(max_col+1)]
            dense.append(row)
        return dense

    def clean(v):
        if v is None:
            return ''
        return str(v).strip()

    def parse_number(v):
        v = clean(v)
        if v in ('', '/', '请联系我们', '#VALUE!'):
            return None
        v = v.replace(',', '')
        try:
            if '.' in v:
                return float(v)
            return int(v)
        except:
            return v

    def parse_range(rng):
        s = clean(rng)
        if not s:
            return None
        s = s.replace(',', '')
        if '+' in s:
            num = int(re.findall(r'\d+', s)[0])
            return {'min': num, 'max': None}
        if '-' in s:
            parts = [p.strip() for p in s.split('-')]
            if len(parts) == 2:
                try:
                    return {'min': int(parts[0]), 'max': int(parts[1])}
                except:
                    return {'text': s}
        try:
            num = int(s)
            return {'min': num, 'max': num}
        except:
            return {'text': s}

    sheets = {
        'ONES Project 项目管理平台': 'xl/worksheets/sheet2.xml',
        'ONES Wiki 知识库管理平台': 'xl/worksheets/sheet3.xml',
        'ONES Copilot': 'xl/worksheets/sheet4.xml',
        'ONES Desk': 'xl/worksheets/sheet5.xml',
    }

    data = {
        'products': {},
        'notes': {
            'private_min_subscription': 50000,
            'private_min_perpetual': 80000,
        }
    }

    for product, sheet_name in sheets.items():
        dense = parse_sheet(sheet_name)
        editions = ['标准版 V6', '专业版 V6', '企业版 V6', '信创版 V6']
        records = []
        current_deploy = None
        current_license = None
        for i, row in enumerate(dense):
            if i < 2:
                continue
            deploy = clean(row[0])
            license_type = clean(row[1])
            seats = clean(row[2])
            seat_range = clean(row[3])
            months = clean(row[4])
            if deploy:
                current_deploy = deploy
            if license_type:
                current_license = license_type
            deploy = current_deploy
            license_type = current_license
            if not deploy or not license_type or not seats:
                continue
            if seats in ('授权用户数',):
                continue
            seats_norm = seats.replace(',', '')
            if seats_norm == '10,000+':
                seats_val = 10000
            else:
                try:
                    seats_val = int(seats_norm)
                except:
                    continue
            entry = {
                'deployment': deploy,
                'license': license_type,
                'seats': seats_val,
                'seat_range': parse_range(seat_range),
                'months': months,
                'editions': {}
            }
            col = 5
            for ed in editions:
                price = parse_number(row[col])
                per = parse_number(row[col+1])
                entry['editions'][ed] = {
                    'list_price': price,
                    'unit_price': per
                }
                col += 2
            records.append(entry)
        data['products'][product] = {
            'editions': editions,
            'records': records
        }

    out_path = os.path.join(out_dir, 'data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

print('已更新:', os.path.join(out_dir, 'data.json'))
