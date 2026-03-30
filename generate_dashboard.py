"""
生成 Dcard 買房板視覺化 Dashboard（不需要安裝額外套件）
執行後開啟 index.html 即可
"""
import sqlite3
import json
import os
from collections import Counter
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'dcard_posts.sqlite')
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')

def query(conn, sql):
    cursor = conn.cursor()
    cursor.execute(sql)
    return cursor.fetchall()

def normalize_key(val, mappings):
    """將相似的值合併到同一個 key"""
    if not val:
        return None
    val = val.strip()
    for canonical, aliases in mappings.items():
        if val == canonical or val in aliases:
            return canonical
    return val

BANK_MAP = {
    '台灣銀行': ['台銀', '臺銀', '台灣銀行'],
    '土地銀行': ['土銀', '土地銀行'],
    '合作金庫': ['合庫', '合作金庫'],
    '第一銀行': ['一銀', '第一銀行'],
    '公股銀行': ['公股銀行', '公股行庫'],
    '台企銀': ['台企銀'],
    '彰化銀行': ['彰銀', '彰化銀行'],
    '中國信託': ['中信', '中國信託'],
    '農會': ['農會'],
    '富邦人壽': ['富邦人壽'],
}

LOAN_MAP = {
    '新青安': ['新青安', '新青安方案', '青安', '新青安,首購', '首購,新青安', '新青安,一般房貸'],
    '首購': ['首購'],
    '一般房貸': ['一般房貸'],
    '公教貸款': ['公教貸款', '公教房貸', '公教方案'],
    '築巢優利貸': ['築巢優利貸', '築巢方案'],
    '信貸': ['信貸'],
    '團貸': ['團貸'],
}

def parse_wan(val_str):
    """將 '1000萬' 等字串解析為整數（萬元）"""
    if not val_str:
        return None
    for part in str(val_str).replace('，', ',').split(','):
        part = part.strip().replace('元', '').replace('塊', '').replace(' ', '')
        try:
            if '萬' in part:
                num = float(part.replace('萬', ''))
                if 10 <= num <= 10000:
                    return int(num)
            elif '億' in part:
                num = float(part.replace('億', ''))
                if 0.1 <= num <= 10:
                    return int(num * 10000)
        except:
            pass
    return None

def parse_rate(rate_str):
    """解析利率字串為 float 列表"""
    results = []
    if not rate_str:
        return results
    for part in str(rate_str).replace('，', ',').split(','):
        part = part.strip().rstrip('%')
        try:
            val = float(part)
            if 0.5 <= val <= 6:
                results.append(val)
        except:
            pass
    return results

def bucket_list(values, step, lo, hi, fmt=None):
    """將數值列表分桶，回傳 (labels, counts)"""
    buckets = {}
    for v in values:
        if lo <= v <= hi:
            b = round(round(v / step) * step, 10)
            buckets[b] = buckets.get(b, 0) + 1
    sorted_b = sorted(buckets.items())
    labels = [fmt(b) if fmt else str(b) for b, _ in sorted_b]
    counts = [c for _, c in sorted_b]
    return labels, counts

def get_data(conn):
    data = {}

    # ── 1. 貸款類型分布 ──
    rows = query(conn, "SELECT loan_type, COUNT(*) as cnt FROM content_analysis WHERE loan_type IS NOT NULL AND loan_type != '' GROUP BY loan_type ORDER BY cnt DESC")
    counter = Counter()
    for loan, cnt in rows:
        key = normalize_key(loan, LOAN_MAP) or loan
        counter[key] += cnt
    top = counter.most_common(10)
    data['loan_type'] = {'labels': [t[0] for t in top], 'values': [t[1] for t in top]}

    # ── 2. 銀行分布 ──
    rows = query(conn, "SELECT bank, COUNT(*) as cnt FROM content_analysis WHERE bank IS NOT NULL AND bank != '' GROUP BY bank ORDER BY cnt DESC")
    counter = Counter()
    for bank, cnt in rows:
        for b in bank.split(','):
            b = b.strip()
            key = normalize_key(b, BANK_MAP) or b
            counter[key] += cnt
    top = counter.most_common(12)
    data['bank'] = {'labels': [t[0] for t in top], 'values': [t[1] for t in top]}

    # ── 3. 地區分布 ──
    rows = query(conn, "SELECT real_estate_area, COUNT(*) as cnt FROM content_analysis WHERE real_estate_area IS NOT NULL AND real_estate_area != '' GROUP BY real_estate_area ORDER BY cnt DESC LIMIT 15")
    data['area'] = {'labels': [r[0] for r in rows], 'values': [r[1] for r in rows]}

    # ── 4. 職業分布 ──
    rows = query(conn, "SELECT loaner_occupation, COUNT(*) as cnt FROM content_analysis WHERE loaner_occupation IS NOT NULL AND loaner_occupation != '' GROUP BY loaner_occupation ORDER BY cnt DESC LIMIT 10")
    data['occupation'] = {'labels': [r[0] for r in rows], 'values': [r[1] for r in rows]}

    # ── 5. 利率分布 ──
    rows = query(conn, "SELECT interest_rate FROM content_analysis WHERE interest_rate IS NOT NULL AND interest_rate != ''")
    rates = []
    for (rate_str,) in rows:
        rates.extend(parse_rate(rate_str))
    labels, counts = bucket_list(rates, 0.1, 1.0, 5.0, fmt=lambda x: f'{x:.1f}%')
    data['interest_rate'] = {'x': labels, 'y': counts}

    # ── 6. 性別分布 ──
    rows = query(conn, "SELECT gender, COUNT(*) as cnt FROM posts WHERE gender != '' GROUP BY gender")
    gender_map = {'M': '男性', 'F': '女性', 'D': '其他'}
    data['gender'] = {
        'labels': [gender_map.get(r[0], r[0]) for r in rows],
        'values': [r[1] for r in rows]
    }

    # ── 7. 按讚數 Top 10 貼文 ──
    rows = query(conn, "SELECT title, like_count, comment_count FROM posts ORDER BY like_count DESC LIMIT 10")
    data['top_posts'] = {
        'titles': [r[0][:25] + '...' if len(r[0]) > 25 else r[0] for r in rows],
        'likes': [r[1] for r in rows],
        'comments': [r[2] for r in rows],
        'full_titles': [r[0] for r in rows],
    }

    # ── 8. 房價分布 ──
    rows = query(conn, "SELECT house_price FROM content_analysis WHERE house_price IS NOT NULL AND house_price != ''")
    prices = [parse_wan(r[0]) for r in rows]
    prices = [p for p in prices if p]
    labels, counts = bucket_list(prices, 100, 200, 6000, fmt=lambda x: f'{int(x)}萬')
    data['house_price'] = {'x': labels, 'y': counts}

    # ── 9. 貸款金額分布 ──
    rows = query(conn, "SELECT loan_amount FROM content_analysis WHERE loan_amount IS NOT NULL AND loan_amount != ''")
    loans = [parse_wan(r[0]) for r in rows]
    loans = [l for l in loans if l]
    labels, counts = bucket_list(loans, 100, 100, 5000, fmt=lambda x: f'{int(x)}萬')
    data['loan_amount'] = {'x': labels, 'y': counts}

    # ── 10. 貸款年限分布 ──
    TERM_MAP = {'40年': 40, '30年': 30, '20年': 20, '25年': 25, '35年': 35, '15年': 15, '10年': 10}
    rows = query(conn, "SELECT loan_term, COUNT(*) as cnt FROM content_analysis WHERE loan_term IS NOT NULL AND loan_term != '' GROUP BY loan_term ORDER BY cnt DESC")
    term_counter = Counter()
    for term_str, cnt in rows:
        for part in str(term_str).replace('，', ',').split(','):
            part = part.strip()
            mapped = TERM_MAP.get(part)
            if mapped:
                term_counter[mapped] += cnt
    sorted_terms = sorted(term_counter.items())
    data['loan_term'] = {
        'x': [f'{k}年' for k, _ in sorted_terms],
        'y': [v for _, v in sorted_terms]
    }

    # ── 11. 貸款成數分布 ──
    LTV_MAP = {
        '5成': 50, '50成': 50,
        '6成': 60, '60成': 60,
        '65成': 65, '6.5成': 65,
        '7成': 70, '70成': 70,
        '75成': 75, '7.5成': 75,
        '8成': 80, '80成': 80,
        '85成': 85, '8.5成': 85,
        '9成': 90, '90成': 90,
    }
    rows = query(conn, "SELECT loan_to_value_ratio, COUNT(*) as cnt FROM content_analysis WHERE loan_to_value_ratio IS NOT NULL AND loan_to_value_ratio != '' GROUP BY loan_to_value_ratio ORDER BY cnt DESC")
    ltv_counter = Counter()
    for ltv_str, cnt in rows:
        for part in str(ltv_str).replace('，', ',').split(','):
            part = part.strip()
            mapped = LTV_MAP.get(part)
            if mapped:
                ltv_counter[mapped] += cnt
    sorted_ltv = sorted(ltv_counter.items())
    data['ltv'] = {
        'x': [f'{k}%' for k, _ in sorted_ltv],
        'y': [v for _, v in sorted_ltv]
    }

    # ── 12. 寬限期分布 ──
    GRACE_MAP = {
        '無': 0, '無寬限': 0, '無寬限期': 0, '沒有': 0,
        '1年': 1, '2年': 2, '3年': 3, '4年': 4, '5年': 5,
    }
    rows = query(conn, "SELECT grace_period, COUNT(*) as cnt FROM content_analysis WHERE grace_period IS NOT NULL AND grace_period != '' GROUP BY grace_period ORDER BY cnt DESC")
    grace_counter = Counter()
    for g_str, cnt in rows:
        for part in str(g_str).replace('，', ',').split(','):
            part = part.strip()
            mapped = GRACE_MAP.get(part)
            if mapped is not None:
                grace_counter[mapped] += cnt
    sorted_grace = sorted(grace_counter.items())
    data['grace'] = {
        'x': ['無寬限期' if k == 0 else f'{k}年' for k, _ in sorted_grace],
        'y': [v for _, v in sorted_grace]
    }

    # ── 13. 年收入分布 ──
    rows = query(conn, "SELECT loaner_income_yearly FROM content_analysis WHERE loaner_income_yearly IS NOT NULL AND loaner_income_yearly != ''")
    incomes = [parse_wan(r[0]) for r in rows]
    incomes = [i for i in incomes if i]
    labels, counts = bucket_list(incomes, 50, 50, 1500, fmt=lambda x: f'{int(x)}萬')
    data['income_yearly'] = {'x': labels, 'y': counts}

    # ── 14. 貸款類型 vs 貸款成數（交叉分析）──
    rows = query(conn, """
        SELECT loan_type, loan_to_value_ratio, COUNT(*) as cnt
        FROM content_analysis
        WHERE loan_type IS NOT NULL AND loan_type != ''
          AND loan_to_value_ratio IS NOT NULL AND loan_to_value_ratio != ''
        GROUP BY loan_type, loan_to_value_ratio
    """)
    cross = {}
    for loan, ltv_str, cnt in rows:
        loan_key = normalize_key(loan, LOAN_MAP) or loan
        for part in str(ltv_str).replace('，', ',').split(','):
            part = part.strip()
            ltv_val = LTV_MAP.get(part)
            if ltv_val and loan_key in ['新青安', '首購', '公教貸款', '一般房貸']:
                if loan_key not in cross:
                    cross[loan_key] = {}
                cross[loan_key][ltv_val] = cross[loan_key].get(ltv_val, 0) + cnt
    all_ltvs = sorted(set(v for d in cross.values() for v in d.keys()))
    cross_series = []
    for loan_key, d in cross.items():
        cross_series.append({
            'name': loan_key,
            'data': [d.get(ltv, 0) for ltv in all_ltvs]
        })
    data['cross_loan_ltv'] = {
        'x': [f'{v}%' for v in all_ltvs],
        'series': cross_series
    }

    # ── 統計卡片 ──
    total_posts = query(conn, "SELECT COUNT(*) FROM posts")[0][0]
    total_comments = query(conn, "SELECT COUNT(*) FROM post_comments")[0][0]
    analyzed = query(conn, "SELECT COUNT(*) FROM content_analysis WHERE house_price IS NOT NULL AND house_price != ''")[0][0]
    time_range = query(conn, "SELECT MIN(created_at), MAX(created_at) FROM posts")[0]
    avg_price = sum(prices) / len(prices) if prices else 0
    data['stats'] = {
        'total_posts': total_posts,
        'total_comments': total_comments,
        'analyzed': analyzed,
        'avg_price': round(avg_price),
        'date_from': time_range[0][:10] if time_range[0] else '',
        'date_to': time_range[1][:10] if time_range[1] else '',
    }

    return data

def generate_html(data):
    data_json = json.dumps(data, ensure_ascii=False)
    html = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dcard 買房板 數據視覺化</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft JhengHei", sans-serif; background: #f0f2f5; color: #333; }}
  header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px 32px; }}
  header h1 {{ font-size: 1.8rem; font-weight: 700; letter-spacing: 1px; }}
  header p {{ opacity: 0.85; margin-top: 6px; font-size: 0.95rem; }}
  .stats {{ display: flex; gap: 16px; padding: 24px 32px 8px; flex-wrap: wrap; }}
  .stat-card {{
    background: white; border-radius: 12px; padding: 20px 28px; flex: 1; min-width: 180px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07); border-left: 4px solid #667eea;
    transition: transform 0.2s;
  }}
  .stat-card:hover {{ transform: translateY(-2px); }}
  .stat-card .num {{ font-size: 2rem; font-weight: 700; color: #667eea; }}
  .stat-card .label {{ color: #888; margin-top: 4px; font-size: 0.9rem; }}
  .section-title {{ font-size: 1.1rem; font-weight: 700; color: #555; padding: 20px 32px 0; letter-spacing: 0.5px; }}
  .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; padding: 12px 32px 8px; }}
  .grid:last-of-type {{ padding-bottom: 32px; }}
  .card {{
    background: white; border-radius: 12px; padding: 16px 20px 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
  }}
  .card.full {{ grid-column: 1 / -1; }}
  .chart {{ width: 100%; height: 320px; }}
  .chart-tall {{ width: 100%; height: 400px; }}
  .chart-wide {{ width: 100%; height: 360px; }}
  @media (max-width: 1024px) {{
    .grid {{ grid-template-columns: 1fr; padding: 12px 20px 8px; }}
    .section-title {{ padding: 16px 20px 0; }}
    .stats {{ padding: 16px 20px 8px; }}
    .stat-card {{ min-width: 140px; padding: 16px 20px; }}
    .stat-card .num {{ font-size: 1.6rem; }}
  }}
  @media (max-width: 768px) {{
    header {{ padding: 16px 20px; }}
    header h1 {{ font-size: 1.4rem; }}
    .chart {{ height: 260px; }}
    .chart-tall {{ height: 320px; }}
    .chart-wide {{ height: 280px; }}
  }}
  @media (max-width: 480px) {{
    .grid {{ gap: 12px; padding: 10px 12px 8px; }}
    .section-title {{ padding: 14px 12px 0; font-size: 1rem; }}
    .stats {{ gap: 10px; padding: 12px; }}
    .stat-card {{ min-width: 100%; }}
    .chart {{ height: 220px; }}
    .chart-tall {{ height: 270px; }}
    .chart-wide {{ height: 240px; }}
    header h1 {{ font-size: 1.2rem; }}
  }}
</style>
</head>
<body>
<header>
  <h1>📊 Dcard 買房板 數據視覺化</h1>
  <p id="subtitle"></p>
</header>

<div class="stats" id="stats"></div>

<div class="section-title">📌 貸款概況</div>
<div class="grid">
  <div class="card">
    <div id="chart-bank" class="chart-tall"></div>
  </div>
  <div class="card">
    <div id="chart-loan" class="chart-tall"></div>
  </div>
  <div class="card">
    <div id="chart-rate" class="chart"></div>
  </div>
  <div class="card">
    <div id="chart-ltv" class="chart"></div>
  </div>
  <div class="card">
    <div id="chart-term" class="chart"></div>
  </div>
  <div class="card">
    <div id="chart-grace" class="chart"></div>
  </div>
  <div class="card full">
    <div id="chart-cross" class="chart"></div>
  </div>
</div>

<div class="section-title">🏠 房價與財務</div>
<div class="grid">
  <div class="card">
    <div id="chart-price" class="chart"></div>
  </div>
  <div class="card">
    <div id="chart-loanamt" class="chart"></div>
  </div>
  <div class="card">
    <div id="chart-income" class="chart"></div>
  </div>
  <div class="card">
    <div id="chart-occupation" class="chart-tall"></div>
  </div>
</div>

<div class="section-title">👥 貼文分析</div>
<div class="grid">
  <div class="card">
    <div id="chart-area" class="chart-tall"></div>
  </div>
  <div class="card">
    <div id="chart-gender" class="chart"></div>
  </div>
  <div class="card full">
    <div id="chart-topposts" class="chart-wide"></div>
  </div>
</div>

<script>
const D = {data_json};

const COLORS = ['#667eea','#764ba2','#f093fb','#4facfe','#43e97b','#fa709a','#fee140','#a18cd1','#fd746c','#c3cfe2','#96fbc4','#f5576c'];
const tooltip_style = {{ backgroundColor: 'rgba(50,50,50,0.85)', borderColor: 'transparent', textStyle: {{ color: '#fff', fontSize: 13 }} }};

document.getElementById('subtitle').textContent = `資料期間：${{D.stats.date_from}} ～ ${{D.stats.date_to}}`;
document.getElementById('stats').innerHTML = `
  <div class="stat-card"><div class="num">${{D.stats.total_posts.toLocaleString()}}</div><div class="label">📝 總貼文數</div></div>
  <div class="stat-card"><div class="num">${{D.stats.total_comments.toLocaleString()}}</div><div class="label">💬 總留言數</div></div>
  <div class="stat-card"><div class="num">${{D.stats.analyzed.toLocaleString()}}</div><div class="label">🏠 含房價分析筆數</div></div>
  <div class="stat-card"><div class="num">${{D.stats.avg_price.toLocaleString()}} 萬</div><div class="label">📊 平均房價</div></div>
`;

// ── 銀行 Bar ──
echarts.init(document.getElementById('chart-bank')).setOption({{
  title: {{ text: '🏦 貸款銀行 Top 12', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'axis', formatter: p => `${{p[0].name}}<br/>筆數：<b>${{p[0].value}}</b>` }},
  grid: {{ top: 50, bottom: 20, left: 20, right: 30, containLabel: true }},
  xAxis: {{ type: 'value' }},
  yAxis: {{ type: 'category', data: D.bank.labels, axisLabel: {{ fontSize: 12 }} }},
  series: [{{
    type: 'bar', data: D.bank.values, barMaxWidth: 28,
    itemStyle: {{ color: p => COLORS[p.dataIndex % COLORS.length], borderRadius: [0, 4, 4, 0] }},
    label: {{ show: true, position: 'right', fontSize: 11 }}
  }}]
}});

// ── 貸款類型 Pie ──
echarts.init(document.getElementById('chart-loan')).setOption({{
  title: {{ text: '📋 貸款類型分布', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'item', formatter: '{{b}}<br/>{{c}} 筆（{{d}}%）' }},
  legend: {{ bottom: 0, type: 'scroll', textStyle: {{ fontSize: 11 }} }},
  color: COLORS,
  series: [{{
    type: 'pie', radius: ['35%', '65%'], center: ['50%', '48%'],
    data: D.loan_type.labels.map((l, i) => ({{ name: l, value: D.loan_type.values[i] }})),
    label: {{ formatter: '{{b}}\\n{{d}}%', fontSize: 11 }},
    emphasis: {{ itemStyle: {{ shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.2)' }} }}
  }}]
}});

// ── 利率分布 ──
echarts.init(document.getElementById('chart-rate')).setOption({{
  title: {{ text: '📈 利率分布', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'axis', formatter: p => `利率 ${{p[0].axisValue}}<br/>筆數：<b>${{p[0].value}}</b>` }},
  grid: {{ top: 50, bottom: 60, left: 50, right: 20 }},
  xAxis: {{ type: 'category', data: D.interest_rate.x, axisLabel: {{ rotate: 45, fontSize: 11 }} }},
  yAxis: {{ type: 'value', name: '筆數' }},
  series: [{{
    type: 'bar', data: D.interest_rate.y, barMaxWidth: 36,
    itemStyle: {{ color: {{ type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{{ offset: 0, color: '#fa709a' }}, {{ offset: 1, color: '#fee140' }}] }}, borderRadius: [4, 4, 0, 0] }}
  }}]
}});

// ── 貸款成數 ──
echarts.init(document.getElementById('chart-ltv')).setOption({{
  title: {{ text: '📐 貸款成數分布', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'axis', formatter: p => `成數 ${{p[0].axisValue}}<br/>筆數：<b>${{p[0].value}}</b>` }},
  grid: {{ top: 50, bottom: 50, left: 50, right: 20 }},
  xAxis: {{ type: 'category', data: D.ltv.x, axisLabel: {{ fontSize: 12 }} }},
  yAxis: {{ type: 'value', name: '筆數' }},
  series: [{{
    type: 'bar', data: D.ltv.y, barMaxWidth: 50,
    itemStyle: {{ color: {{ type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{{ offset: 0, color: '#4facfe' }}, {{ offset: 1, color: '#a18cd1' }}] }}, borderRadius: [4, 4, 0, 0] }},
    label: {{ show: true, position: 'top', fontSize: 11 }}
  }}]
}});

// ── 貸款年限 ──
echarts.init(document.getElementById('chart-term')).setOption({{
  title: {{ text: '🗓️ 貸款年限分布', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'axis', formatter: p => `${{p[0].axisValue}}<br/>筆數：<b>${{p[0].value}}</b>` }},
  grid: {{ top: 50, bottom: 50, left: 50, right: 20 }},
  xAxis: {{ type: 'category', data: D.loan_term.x, axisLabel: {{ fontSize: 13 }} }},
  yAxis: {{ type: 'value', name: '筆數' }},
  series: [{{
    type: 'bar', data: D.loan_term.y, barMaxWidth: 60,
    itemStyle: {{ color: {{ type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{{ offset: 0, color: '#43e97b' }}, {{ offset: 1, color: '#38f9d7' }}] }}, borderRadius: [4, 4, 0, 0] }},
    label: {{ show: true, position: 'top', fontSize: 12 }}
  }}]
}});

// ── 寬限期 ──
echarts.init(document.getElementById('chart-grace')).setOption({{
  title: {{ text: '⏳ 寬限期分布', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'axis', formatter: p => `${{p[0].axisValue}}<br/>筆數：<b>${{p[0].value}}</b>` }},
  grid: {{ top: 50, bottom: 50, left: 50, right: 20 }},
  xAxis: {{ type: 'category', data: D.grace.x, axisLabel: {{ fontSize: 12 }} }},
  yAxis: {{ type: 'value', name: '筆數' }},
  series: [{{
    type: 'bar', data: D.grace.y, barMaxWidth: 60,
    itemStyle: {{ color: p => p.dataIndex === 0 ? '#fd746c' : '#667eea', borderRadius: [4, 4, 0, 0] }},
    label: {{ show: true, position: 'top', fontSize: 12 }}
  }}]
}});

// ── 貸款類型 × 貸款成數 交叉分析 ──
echarts.init(document.getElementById('chart-cross')).setOption({{
  title: {{ text: '🔀 貸款類型 × 貸款成數 交叉分析', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
  legend: {{ top: 36, textStyle: {{ fontSize: 12 }} }},
  grid: {{ top: 80, bottom: 40, left: 20, right: 20, containLabel: true }},
  xAxis: {{ type: 'category', data: D.cross_loan_ltv.x }},
  yAxis: {{ type: 'value', name: '筆數' }},
  color: COLORS,
  series: D.cross_loan_ltv.series.map(s => ({{
    name: s.name, type: 'bar', data: s.data, barMaxWidth: 40,
    itemStyle: {{ borderRadius: [4, 4, 0, 0] }}
  }}))
}});

// ── 房價分布 ──
echarts.init(document.getElementById('chart-price')).setOption({{
  title: {{ text: '🏠 房價分布（萬元）', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'axis', formatter: p => `${{p[0].axisValue}}<br/>筆數：<b>${{p[0].value}}</b>` }},
  grid: {{ top: 50, bottom: 60, left: 50, right: 20 }},
  xAxis: {{ type: 'category', data: D.house_price.x, axisLabel: {{ rotate: 45, fontSize: 10 }} }},
  yAxis: {{ type: 'value', name: '筆數' }},
  series: [{{
    type: 'bar', data: D.house_price.y, barMaxWidth: 30,
    itemStyle: {{ color: {{ type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{{ offset: 0, color: '#f093fb' }}, {{ offset: 1, color: '#f5576c' }}] }}, borderRadius: [3, 3, 0, 0] }}
  }}]
}});

// ── 貸款金額分布 ──
echarts.init(document.getElementById('chart-loanamt')).setOption({{
  title: {{ text: '💰 貸款金額分布（萬元）', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'axis', formatter: p => `${{p[0].axisValue}}<br/>筆數：<b>${{p[0].value}}</b>` }},
  grid: {{ top: 50, bottom: 60, left: 50, right: 20 }},
  xAxis: {{ type: 'category', data: D.loan_amount.x, axisLabel: {{ rotate: 45, fontSize: 10 }} }},
  yAxis: {{ type: 'value', name: '筆數' }},
  series: [{{
    type: 'bar', data: D.loan_amount.y, barMaxWidth: 30,
    itemStyle: {{ color: {{ type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{{ offset: 0, color: '#667eea' }}, {{ offset: 1, color: '#764ba2' }}] }}, borderRadius: [3, 3, 0, 0] }}
  }}]
}});

// ── 年收入分布 ──
echarts.init(document.getElementById('chart-income')).setOption({{
  title: {{ text: '💼 貸款人年收入分布（萬元）', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'axis', formatter: p => `${{p[0].axisValue}}<br/>筆數：<b>${{p[0].value}}</b>` }},
  grid: {{ top: 50, bottom: 60, left: 50, right: 20 }},
  xAxis: {{ type: 'category', data: D.income_yearly.x, axisLabel: {{ rotate: 45, fontSize: 11 }} }},
  yAxis: {{ type: 'value', name: '筆數' }},
  series: [{{
    type: 'bar', data: D.income_yearly.y, barMaxWidth: 36,
    itemStyle: {{ color: {{ type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{{ offset: 0, color: '#43e97b' }}, {{ offset: 1, color: '#fee140' }}] }}, borderRadius: [4, 4, 0, 0] }}
  }}]
}});

// ── 職業 Bar ──
echarts.init(document.getElementById('chart-occupation')).setOption({{
  title: {{ text: '🧑‍💼 職業分布', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'axis', formatter: p => `${{p[0].name}}<br/>筆數：<b>${{p[0].value}}</b>` }},
  grid: {{ top: 50, bottom: 20, left: 20, right: 30, containLabel: true }},
  xAxis: {{ type: 'value' }},
  yAxis: {{ type: 'category', data: D.occupation.labels, axisLabel: {{ fontSize: 12 }} }},
  series: [{{
    type: 'bar', data: D.occupation.values, barMaxWidth: 28,
    itemStyle: {{ color: '#43e97b', borderRadius: [0, 4, 4, 0] }},
    label: {{ show: true, position: 'right', fontSize: 11 }}
  }}]
}});

// ── 地區 Bar ──
echarts.init(document.getElementById('chart-area')).setOption({{
  title: {{ text: '📍 地區分布 Top 15', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'axis', formatter: p => `${{p[0].name}}<br/>筆數：<b>${{p[0].value}}</b>` }},
  grid: {{ top: 50, bottom: 20, left: 20, right: 30, containLabel: true }},
  xAxis: {{ type: 'value' }},
  yAxis: {{ type: 'category', data: D.area.labels, axisLabel: {{ fontSize: 11 }} }},
  series: [{{
    type: 'bar', data: D.area.values, barMaxWidth: 28,
    itemStyle: {{ color: '#4facfe', borderRadius: [0, 4, 4, 0] }},
    label: {{ show: true, position: 'right', fontSize: 11 }}
  }}]
}});

// ── 性別 Pie ──
echarts.init(document.getElementById('chart-gender')).setOption({{
  title: {{ text: '👤 發文性別比例', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{ ...tooltip_style, trigger: 'item', formatter: '{{b}}<br/>{{c}} 筆（{{d}}%）' }},
  legend: {{ bottom: 0, textStyle: {{ fontSize: 12 }} }},
  color: ['#4facfe', '#fa709a', '#fee140'],
  series: [{{
    type: 'pie', radius: ['40%', '68%'], center: ['50%', '48%'],
    data: D.gender.labels.map((l, i) => ({{ name: l, value: D.gender.values[i] }})),
    label: {{ formatter: '{{b}}\\n{{d}}%', fontSize: 13, fontWeight: 'bold' }},
    emphasis: {{ itemStyle: {{ shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.2)' }} }}
  }}]
}});

// ── Top 10 貼文 ──
echarts.init(document.getElementById('chart-topposts')).setOption({{
  title: {{ text: '🔥 最高按讚 Top 10 貼文', left: 8, top: 4, textStyle: {{ fontSize: 14, fontWeight: 600, color: '#444' }} }},
  tooltip: {{
    ...tooltip_style, trigger: 'axis', axisPointer: {{ type: 'shadow' }},
    formatter: params => {{
      const idx = D.top_posts.titles.indexOf(params[0].axisValue);
      const title = D.top_posts.full_titles[idx] || params[0].axisValue;
      return `${{title}}<br/>${{params.map(p => `${{p.marker}} ${{p.seriesName}}：<b>${{p.value}}</b>`).join('<br/>')}}`;
    }}
  }},
  legend: {{ top: 40, textStyle: {{ fontSize: 12 }} }},
  grid: {{ top: 80, bottom: 20, left: 20, right: 20, containLabel: true }},
  xAxis: {{ type: 'category', data: D.top_posts.titles, axisLabel: {{ rotate: 20, fontSize: 10, interval: 0 }} }},
  yAxis: {{ type: 'value', name: '數量' }},
  color: ['#667eea', '#f093fb'],
  series: [
    {{ name: '按讚數', type: 'bar', data: D.top_posts.likes, barMaxWidth: 36, itemStyle: {{ borderRadius: [4, 4, 0, 0] }} }},
    {{ name: '留言數', type: 'bar', data: D.top_posts.comments, barMaxWidth: 36, itemStyle: {{ borderRadius: [4, 4, 0, 0] }} }}
  ]
}});

// RWD resize（debounce 防抖）
let _resizeTimer;
window.addEventListener('resize', () => {{
  clearTimeout(_resizeTimer);
  _resizeTimer = setTimeout(() => {{
    document.querySelectorAll('[id^="chart-"]').forEach(el => {{
      const instance = echarts.getInstanceByDom(el);
      if (instance) instance.resize();
    }});
  }}, 150);
}});
</script>
</body>
</html>'''
    return html

if __name__ == '__main__':
    print('連接資料庫...')
    conn = sqlite3.connect(DB_PATH)
    print('讀取資料...')
    data = get_data(conn)
    conn.close()
    print('生成 HTML...')
    html = generate_html(data)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✅ 完成！請開啟：{OUTPUT_PATH}')
