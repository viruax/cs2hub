#!/usr/bin/env python3
"""
CS2 Hub Auto-Updater
Запускай раз в день — обновляет HTML-файл со свежими данными.

Использование:
    python update_cs2_hub.py

Автозапуск (Windows):
    1. Win+R → taskschd.msc
    2. Создать задачу → Триггер: Ежедневно в 9:00
    3. Действие: Запустить программу → python update_cs2_hub.py

Автозапуск (Linux/macOS cron):
    0 9 * * * cd /путь/к/папке && python3 update_cs2_hub.py
"""

import json
import urllib.request
import socket
import time
from datetime import datetime, timedelta

socket.setdefaulttimeout(30)

OUTPUT_FILE = "CS2_Hub.html"

def fetch_with_retry(url, headers=None, max_retries=3, timeout=30):
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"   ⚠️ Попытка {attempt+1} не удалась: {e}. Повтор...")
                time.sleep(2)
            else:
                raise

def get_steam_news(days=14):
    url = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid=730&count=30&maxlength=600&format=json"
    data = fetch_with_retry(url, {'User-Agent': 'Mozilla/5.0'})
    cutoff = datetime.now() - timedelta(days=days)
    items = []
    for item in data.get('appnews', {}).get('newsitems', []):
        d = datetime.fromtimestamp(item['date'])
        if d >= cutoff:
            content = item.get('contents', '').replace('\\', '').replace('\', '')[:500]
            if len(content) == 500: content += '...'
            items.append({
                'title': item['title'],
                'date': d.strftime('%d.%m.%Y'),
                'time': d.strftime('%H:%M'),
                'content': content,
                'url': item['url'],
                'author': item.get('author', 'Valve'),
                'isPatch': 'patchnotes' in item.get('tags', [])
            })
    return items

def get_matches(days=14):
    url = "https://api.csapi.de/matches/latest"
    data = fetch_with_retry(url, {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    tier1 = {'Spirit', 'Vitality', 'NAVI', 'Natus Vincere', 'MOUZ', 'FURIA',
             'G2', 'G2 Esports', 'FaZe', 'The MongolZ', 'Aurora', 'Falcons',
             '9z', 'NIP', 'Astralis', 'Liquid', 'Complexity', 'BIG', 'paiN',
             'Virtus.pro', 'VP', 'Heroic', 'MIBR', 'FUT'}
    items = []
    for m in data:
        if m.get('date', '') >= cutoff:
            t1, t2 = m['team1']['name'], m['team2']['name']
            if t1 in tier1 or t2 in tier1:
                maps = ' | '.join(f"{x['name']} {x['team1_score']}:{x['team2_score']}"
                                  for x in m.get('maps', [])) or 'N/A'
                items.append({
                    'team1': t1, 'team2': t2,
                    'score1': m['team1']['score'], 'score2': m['team2']['score'],
                    'winner': m['winner']['name'],
                    'date': datetime.strptime(m['date'], '%Y-%m-%d').strftime('%d.%m.%Y'),
                    'event': m['event'],
                    'maps': maps,
                    'url': f"https://www.hltv.org/matches/{m['id']}/match"
                })
    return items

def generate_html(news_data, matches_data, hltv_data, vrs_data, tournaments_data):
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    news_json = json.dumps(news_data, ensure_ascii=False)
    matches_json = json.dumps(matches_data, ensure_ascii=False)
    hltv_json = json.dumps(hltv_data, ensure_ascii=False)
    vrs_json = json.dumps(vrs_data, ensure_ascii=False)
    tournaments_json = json.dumps(tournaments_data, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CS2 Hub — Новости, матчи, рейтинги</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--bg:#0a0a12;--card:#141420;--card-hover:#1a1a2e;--accent:#ff4757;--accent2:#ffa502;--accent3:#2ed573;--text:#e8e8e8;--muted:#6c6c8a;--border:rgba(255,255,255,0.06)}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;line-height:1.5}}
nav{{background:rgba(10,10,18,0.95);backdrop-filter:blur(20px);padding:0 25px;display:flex;gap:3px;align-items:center;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100;height:58px;overflow-x:auto}}
nav .logo{{font-size:1.25em;font-weight:800;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-right:25px;white-space:nowrap;display:flex;align-items:center;gap:6px}}
nav a{{color:var(--muted);text-decoration:none;font-weight:500;font-size:0.9em;cursor:pointer;transition:all 0.2s;padding:8px 14px;border-radius:8px;position:relative;white-space:nowrap;flex-shrink:0}}
nav a:hover{{color:var(--text);background:rgba(255,255,255,0.03)}}
nav a.active{{color:var(--text)}}
nav a.active::after{{content:'';position:absolute;bottom:-14px;left:14px;right:14px;height:2px;background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:2px}}
.container{{max-width:1050px;margin:0 auto;padding:25px 18px}}
.hero{{text-align:center;padding:40px 20px;background:linear-gradient(135deg,rgba(255,71,87,0.08),rgba(254,202,87,0.08));border-radius:18px;margin-bottom:22px;border:1px solid var(--border);position:relative;overflow:hidden}}
.hero h1{{font-size:2.4em;margin-bottom:8px;font-weight:700}}
.hero p{{color:var(--muted);font-size:1.05em}}
.hero .update-time{{color:#555;font-size:0.8em;margin-top:12px}}
.stats-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:25px}}
.stat-card{{background:var(--card);padding:18px 10px;border-radius:12px;text-align:center;border:1px solid var(--border);transition:all 0.2s}}
.stat-card:hover{{transform:translateY(-2px);border-color:rgba(255,255,255,0.1)}}
.stat-card .num{{font-size:1.9em;font-weight:800;background:linear-gradient(135deg,var(--accent2),#ff7675);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.stat-card .lbl{{color:var(--muted);font-size:0.78em;margin-top:3px}}
.section-title{{font-size:1.2em;font-weight:600;margin:28px 0 12px;display:flex;align-items:center;gap:8px;color:#fff}}
.section-title::before{{content:'';width:4px;height:20px;background:linear-gradient(180deg,var(--accent),var(--accent2));border-radius:2px}}
.ranking-table{{background:var(--card);border-radius:14px;border:1px solid var(--border);overflow:hidden}}
.ranking-row{{display:grid;grid-template-columns:45px 1fr 80px 60px;gap:10px;align-items:center;padding:12px 18px;border-bottom:1px solid var(--border);transition:background 0.15s}}
.ranking-row:last-child{{border-bottom:none}}
.ranking-row:hover{{background:rgba(255,255,255,0.02)}}
.ranking-row.header{{background:rgba(255,255,255,0.02);font-size:0.75em;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:var(--muted);padding:10px 18px}}
.rank-num{{font-size:1.1em;font-weight:800;color:var(--accent2);text-align:center}}
.rank-team{{font-weight:600;font-size:0.95em}}
.rank-team .players{{font-size:0.75em;color:#555;margin-top:2px;font-weight:400}}
.rank-points{{text-align:right;font-weight:700;color:var(--accent);font-size:0.9em}}
.rank-change{{text-align:right;font-size:0.85em;font-weight:600}}
.rank-change.up{{color:var(--accent3)}}
.rank-change.down{{color:var(--accent)}}
.rank-change.same{{color:#555}}
.rank-region{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:0.65em;font-weight:700;margin-left:6px;text-transform:uppercase}}
.region-eu{{background:rgba(52,152,219,0.15);color:#3498db}}
.region-am{{background:rgba(46,213,115,0.15);color:#2ed573}}
.region-as{{background:rgba(241,196,15,0.15);color:#f1c40f}}
.tournament-card{{background:var(--card);border-radius:14px;padding:16px 18px;border:1px solid var(--border);margin-bottom:10px;transition:all 0.2s;display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;text-decoration:none;color:inherit}}
.tournament-card:hover{{background:var(--card-hover);border-color:rgba(255,255,255,0.12);transform:translateX(4px)}}
.tournament-card .name{{font-weight:600;font-size:1em;margin-bottom:4px}}
.tournament-card .meta{{color:var(--muted);font-size:0.82em;display:flex;gap:14px;flex-wrap:wrap}}
.tournament-card .meta span{{display:flex;align-items:center;gap:4px}}
.tournament-card .status{{font-size:0.8em;font-weight:600;padding:4px 10px;border-radius:20px;white-space:nowrap}}
.status-live{{background:rgba(231,76,60,0.15);color:#e74c3c}}
.status-soon{{background:rgba(255,165,2,0.15);color:#ffa502}}
.status-confirmed{{background:rgba(46,213,115,0.15);color:#2ed573}}
.tournament-card .prize{{font-size:0.85em;font-weight:700;color:var(--accent2);margin-top:4px}}
.news-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}
.news-card{{background:var(--card);border-radius:14px;padding:16px;border:1px solid var(--border);transition:all 0.2s;text-decoration:none;color:inherit;display:block}}
.news-card:hover{{background:var(--card-hover);border-color:rgba(255,255,255,0.12);transform:translateY(-2px);box-shadow:0 8px 30px rgba(0,0,0,0.3)}}
.news-card .badge{{display:inline-block;padding:2px 8px;border-radius:20px;font-size:0.65em;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px}}
.badge-patch{{background:linear-gradient(135deg,#e74c3c,#c0392b);color:white}}
.badge-news{{background:linear-gradient(135deg,#3498db,#2980b9);color:white}}
.news-card h3{{font-size:1em;font-weight:600;margin-bottom:6px;line-height:1.3;color:#fff}}
.news-card .meta{{color:var(--muted);font-size:0.75em;margin-bottom:8px;display:flex;gap:10px;flex-wrap:wrap}}
.news-card .desc{{color:#999;font-size:0.85em;line-height:1.5}}
.match-row{{display:grid;grid-template-columns:1fr auto 1fr;gap:12px;align-items:center;background:var(--card);padding:14px 20px;border-radius:12px;margin-bottom:8px;border:1px solid var(--border);transition:all 0.2s;text-decoration:none;color:inherit}}
.match-row:hover{{background:var(--card-hover);border-color:rgba(255,255,255,0.1)}}
.match-row .team{{font-weight:600;font-size:0.95em}}
.match-row .team.winner{{color:var(--accent2)}}
.match-row .vs{{text-align:center;font-size:1.2em;font-weight:800;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.match-row .event{{color:var(--muted);font-size:0.75em;text-align:center;margin-top:2px}}
.match-row .maps{{color:#555;font-size:0.72em;text-align:center;margin-top:3px}}
.tab-content{{display:none;animation:fadeIn 0.25s ease-out}}
.tab-content.active{{display:block}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.empty-state{{text-align:center;padding:40px;color:var(--muted)}}
.empty-state .emoji{{font-size:2.5em;margin-bottom:10px;display:block}}
footer{{text-align:center;padding:30px 20px;color:#444;font-size:0.8em;border-top:1px solid var(--border);margin-top:35px}}
@media(max-width:768px){{.hero h1{{font-size:1.7em}}.stats-grid{{grid-template-columns:repeat(2,1fr)}}.news-grid{{grid-template-columns:1fr}}.two-col{{grid-template-columns:1fr}}.match-row{{grid-template-columns:1fr;text-align:center;gap:5px;padding:12px}}.ranking-row{{grid-template-columns:35px 1fr 70px 50px;padding:10px 12px}}.tournament-card{{grid-template-columns:1fr}}nav{{padding:0 12px}}nav .logo{{margin-right:10px;font-size:1.1em}}nav a{{padding:6px 10px;font-size:0.82em}}}}
</style>
</head>
<body>
<nav><div class="logo">🎯 CS2 Hub</div><a onclick="showTab('home')" class="active" id="tab-home">Главная</a><a onclick="showTab('rankings')" id="tab-rankings">Рейтинги</a><a onclick="showTab('tournaments')" id="tab-tournaments">Турниры</a><a onclick="showTab('matches')" id="tab-matches">Матчи</a><a onclick="showTab('news')" id="tab-news">Новости</a></nav>
<div class="container">
<div id="content-home" class="tab-content active">
<div class="hero"><h1>🎯 CS2 Hub</h1><p>Новости, матчи, рейтинги и турниры — всё в одном месте</p><div class="update-time">📅 Обновлено: {now}</div></div>
<div class="stats-grid">
<div class="stat-card"><div class="num">{len(news_data)}</div><div class="lbl">Обновлений</div></div>
<div class="stat-card"><div class="num">{len(matches_data)}</div><div class="lbl">Матчей тир-1</div></div>
<div class="stat-card"><div class="num">{len(tournaments_data)}</div><div class="lbl">Турниров</div></div>
<div class="stat-card"><div class="num">{len(hltv_data)}</div><div class="lbl">Команд в топе</div></div>
</div>
<div class="two-col">
<div><div class="section-title">🏆 HLTV Top 5</div><div class="ranking-table" id="home-hltv"></div></div>
<div><div class="section-title">📊 VRS Top 5</div><div class="ranking-table" id="home-vrs"></div></div>
</div>
<div class="section-title">🔥 Последние матчи</div><div id="home-matches"></div>
<div class="section-title">📅 Ближайшие турниры</div><div id="home-tournaments"></div>
</div>
<div id="content-rankings" class="tab-content">
<div class="hero"><h1>📊 Рейтинги команд</h1><p>HLTV World Ranking и Valve Regional Standings (VRS)</p></div>
<div class="two-col">
<div><div class="section-title">🏆 HLTV World Ranking</div><div class="ranking-table" id="all-hltv"></div></div>
<div><div class="section-title">📊 VRS (Valve)</div><div class="ranking-table" id="all-vrs"></div></div>
</div>
</div>
<div id="content-tournaments" class="tab-content">
<div class="hero"><h1>📅 Предстоящие турниры</h1><p>Тир-1 и тир-2 события до конца 2026 года</p></div>
<div id="all-tournaments"></div>
</div>
<div id="content-matches" class="tab-content">
<div class="hero"><h1>🏆 Матчи тир-1</h1><p>Результаты за последние 2 недели</p></div>
<div id="all-matches"></div>
</div>
<div id="content-news" class="tab-content">
<div class="hero"><h1>📰 Новости CS2</h1><p>Обновления игры и анонсы от Valve</p></div>
<div class="news-grid" id="all-news"></div>
</div>
</div>
<footer><p>CS2 Hub v2.0 | Данные: Steam API + CSAPI + HLTV + VRS</p><p style="margin-top:4px">Обновляется ежедневно | Просто открой файл — всё работает!</p></footer>
<script>
const NEWS_DATA={news_json};
const MATCHES_DATA={matches_json};
const HLTV_DATA={hltv_json};
const VRS_DATA={vrs_json};
const TOURNAMENTS_DATA={tournaments_json};
function renderRankingRow(item,type,isHeader=false){{
if(isHeader){{return`<div class="ranking-row header"><div>#</div><div>Команда</div><div style="text-align:right">Очки</div><div style="text-align:right">Изм.</div></div>`}}
const changeIcon=item.change>0?'↑':item.change<0?'↓':'—';
const changeClass=item.change>0?'up':item.change<0?'down':'same';
const changeText=item.change!==0?Math.abs(item.change):'';
const regionClass=item.region?`region-${{item.region.toLowerCase()}}`:'';
const regionBadge=item.region?`<span class="rank-region ${{regionClass}}">${{item.region}}</span>`:'';
const players=item.players?`<div class="players">${{item.players.join(', ')}}</div>`:'';
return`<div class="ranking-row"><div class="rank-num">${{item.rank}}</div><div class="rank-team">${{item.team}}${{regionBadge}}${{players}}</div><div class="rank-points">${{item.points}}</div><div class="rank-change ${{changeClass}}">${{changeIcon}}${{changeText}}</div></div>`}}
function renderTournament(t,compact=false){{
const statusClass=t.status.includes('Идёт')?'status-live':t.status.includes('Скоро')?'status-soon':'status-confirmed';
if(compact){{return`<a href="${{t.url}}" target="_blank" class="tournament-card"><div><div class="name">${{t.name}}</div><div class="meta"><span>📅 ${{t.dates}}</span><span>📍 ${{t.location}}</span></div><div class="prize">${{t.prize}}</div></div><div class="status ${{statusClass}}">${{t.status}}</div></a>`}}
return`<a href="${{t.url}}" target="_blank" class="tournament-card"><div><div class="name">${{t.name}}</div><div class="meta"><span>📅 ${{t.dates}}</span><span>📍 ${{t.location}}</span><span>👥 ${{t.teams}} команд</span></div><div class="prize">Призовой фонд: ${{t.prize}}</div></div><div class="status ${{statusClass}}">${{t.status}}</div></a>`}}
function renderNewsCard(n){{
const badge=n.isPatch?'badge-patch':'badge-news';
const label=n.isPatch?'Патч':'Новость';
return`<a href="${{n.url}}" target="_blank" class="news-card"><span class="badge ${{badge}}">${{label}}</span><h3>${{escapeHtml(n.title)}}</h3><div class="meta"><span>📅 ${{n.date}}</span><span>🕐 ${{n.time}}</span><span>✍️ ${{escapeHtml(n.author)}}</span></div><div class="desc">${{escapeHtml(n.content)}}</div></a>`}}
function renderMatchRow(m){{
const t1Win=m.winner===m.team1?'winner':'';
const t2Win=m.winner===m.team2?'winner':'';
return`<a href="${{m.url}}" target="_blank" class="match-row"><div class="team ${{t1Win}}" style="text-align:right">${{escapeHtml(m.team1)}}<div class="maps">${{escapeHtml(m.maps)}}</div></div><div><div class="vs">${{m.score1}}:${{m.score2}}</div><div class="event">${{escapeHtml(m.event)}} • ${{m.date}}</div></div><div class="team ${{t2Win}}">${{escapeHtml(m.team2)}}</div></a>`}}
function escapeHtml(text){{const div=document.createElement('div');div.textContent=text;return div.innerHTML}}
function showTab(name){{document.querySelectorAll('.tab-content').forEach(el=>el.classList.remove('active'));document.querySelectorAll('nav a').forEach(el=>el.classList.remove('active'));document.getElementById('content-'+name).classList.add('active');document.getElementById('tab-'+name).classList.add('active');window.scrollTo({{top:0,behavior:'smooth'}})}}
function loadAll(){{
document.getElementById('home-hltv').innerHTML=renderRankingRow({{}},'hltv',true)+HLTV_DATA.slice(0,5).map(x=>renderRankingRow(x,'hltv')).join('');
document.getElementById('home-vrs').innerHTML=renderRankingRow({{}},'vrs',true)+VRS_DATA.slice(0,5).map(x=>renderRankingRow(x,'vrs')).join('');
const homeMatches=document.getElementById('home-matches');
homeMatches.innerHTML=MATCHES_DATA.slice(0,4).map(renderMatchRow).join('')||'<div class="empty-state"><span class="emoji">😴</span>Нет матчей</div>';
const homeTours=document.getElementById('home-tournaments');
homeTours.innerHTML=TOURNAMENTS_DATA.slice(0,3).map(t=>renderTournament(t,true)).join('')||'<div class="empty-state"><span class="emoji">😴</span>Нет турниров</div>';
document.getElementById('all-hltv').innerHTML=renderRankingRow({{}},'hltv',true)+HLTV_DATA.map(x=>renderRankingRow(x,'hltv')).join('');
document.getElementById('all-vrs').innerHTML=renderRankingRow({{}},'vrs',true)+VRS_DATA.map(x=>renderRankingRow(x,'vrs')).join('');
document.getElementById('all-tournaments').innerHTML=TOURNAMENTS_DATA.map(t=>renderTournament(t)).join('')||'<div class="empty-state"><span class="emoji">😴</span>Нет турниров</div>';
document.getElementById('all-matches').innerHTML=MATCHES_DATA.map(renderMatchRow).join('')||'<div class="empty-state"><span class="emoji">😴</span>Нет матчей</div>';
document.getElementById('all-news').innerHTML=`<div class="news-grid" style="grid-template-columns:1fr">${{NEWS_DATA.map(renderNewsCard).join('')}}</div>`||'<div class="empty-state"><span class="emoji">😴</span>Нет новостей</div>';
}}
loadAll();
</script>
</body>
</html>"""

# ============ ДАННЫЕ (обновлять вручную или через парсер) ============
HLTV_TOP10 = [
    {"rank": 1, "team": "Falcons", "points": 907, "players": ["karrigan", "NiKo", "TeSeS", "m0NESY", "kyousuke"], "change": 0},
    {"rank": 2, "team": "Spirit", "points": 752, "players": ["sh1ro", "magixx", "tN1R", "zont1x", "donk"], "change": 0},
    {"rank": 3, "team": "FURIA", "points": 646, "players": ["FalleN", "yuurih", "YEKINDAR", "KSCERATO", "molodoy"], "change": 0},
    {"rank": 4, "team": "Vitality", "points": 626, "players": ["apEX", "ropz", "ZywOo", "flameZ", "mezii"], "change": 0},
    {"rank": 5, "team": "MOUZ", "points": 574, "players": ["torzsi", "Spinx", "xertioN", "PR", "xelex"], "change": 0},
    {"rank": 6, "team": "Natus Vincere", "points": 459, "players": ["Aleksib", "iM", "b1t", "w0nderful", "makazze"], "change": 0},
    {"rank": 7, "team": "9z", "points": 363, "players": ["max", "dgt", "meyern", "luchov", "HUASOPEEK"], "change": 0},
    {"rank": 8, "team": "Aurora", "points": 330, "players": ["XANTARES", "woxic", "Jimpphat", "kyxsan", "Wicadia"], "change": 0},
    {"rank": 9, "team": "FaZe", "points": 328, "players": ["frozen", "Twistzz", "Neityu", "jcobbb", "JBOEN"], "change": 2},
    {"rank": 10, "team": "G2", "points": 308, "players": ["huNter-", "NertZ", "r1nkle", "HeavyGod", "MATYS"], "change": -1},
]

VRS_TOP10 = [
    {"rank": 1, "team": "Spirit", "points": 1993, "region": "EU", "change": 1},
    {"rank": 2, "team": "Falcons", "points": 1988, "region": "EU", "change": 1},
    {"rank": 3, "team": "Vitality", "points": 1908, "region": "EU", "change": -2},
    {"rank": 4, "team": "NAVI", "points": 1837, "region": "EU", "change": 0},
    {"rank": 5, "team": "FURIA", "points": 1797, "region": "AM", "change": 6},
    {"rank": 6, "team": "MOUZ", "points": 1762, "region": "EU", "change": -1},
    {"rank": 7, "team": "Legacy", "points": 1752, "region": "AM", "change": -1},
    {"rank": 8, "team": "Aurora", "points": 1723, "region": "EU", "change": 0},
    {"rank": 9, "team": "G2", "points": 1713, "region": "EU", "change": 4},
    {"rank": 10, "team": "BetBoom", "points": 1705, "region": "EU", "change": 7},
]

UPCOMING_TOURNAMENTS = [
    {"name": "Esports World Cup 2026", "dates": "12–23 августа", "location": "Париж", "prize": "$2,000,000", "teams": 32, "status": "🔴 Идёт сейчас", "url": "https://esportsworldcup.com/en/competitions/2026/cs2"},
    {"name": "BLAST Open Fall 2026", "dates": "26 августа – 6 сентября", "location": "Порту, Португалия", "prize": "$1,100,000", "teams": 16, "status": "⏳ Скоро", "url": "https://blast.tv/cs/tournaments"},
    {"name": "StarLadder StarSeries S20", "dates": "~17–20 сентября", "location": "Вааса, Финляндия", "prize": "$500,000", "teams": 8, "status": "⏳ Скоро", "url": "https://liquipedia.net/counterstrike/StarLadder/StarSeries/Season_20"},
    {"name": "ESL Pro League S24", "dates": "~3–11 октября", "location": "Катовице, Польша", "prize": "TBC", "teams": 16, "status": "⏳ Скоро", "url": "https://pro.eslgaming.com/csgo/proleague/"},
    {"name": "Thunderpick World Championship", "dates": "~14–18 октября", "location": "TBC", "prize": "$1,250,000", "teams": 8, "status": "⏳ Скоро", "url": "https://thunderpick.com"},
    {"name": "PGL Masters Bucharest 2026", "dates": "~24–31 октября", "location": "Бухарест, Румыния", "prize": "TBC", "teams": 16, "status": "⏳ Скоро", "url": "https://pgl.gg"},
    {"name": "IEM Beijing 2026", "dates": "~2–8 ноября", "location": "Пекин, Китай", "prize": "TBC", "teams": 16, "status": "⏳ Скоро", "url": "https://intel.com/iem"},
    {"name": "BLAST Rivals Fall 2026", "dates": "~9–15 ноября", "location": "Гонконг", "prize": "TBC", "teams": 16, "status": "⏳ Скоро", "url": "https://blast.tv"},
    {"name": "PGL Major Singapore 2026", "dates": "25 ноября – 13 декабря", "location": "Сингапур", "prize": "$1,250,000", "teams": 32, "status": "✅ Подтверждён", "url": "https://pgl.gg"},
]

# ============ ГЕНЕРАЦИЯ ============
if __name__ == '__main__':
    print("🔄 Загружаю данные...")
    news = get_steam_news(14)
    matches = get_matches(14)
    print(f"   ✅ Новостей: {len(news)}, Матчей: {len(matches)}")

    print("🎨 Генерирую HTML...")
    html = generate_html(news, matches, HLTV_TOP10, VRS_TOP10, UPCOMING_TOURNAMENTS)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Готово! Файл: {OUTPUT_FILE} ({len(html):,} символов)")
    print(f"
📊 Содержимое:")
    print(f"   • Новостей Steam: {len(news)}")
    print(f"   • Матчей тир-1: {len(matches)}")
    print(f"   • HLTV Top 10: {len(HLTV_TOP10)}")
    print(f"   • VRS Top 10: {len(VRS_TOP10)}")
    print(f"   • Турниров: {len(UPCOMING_TOURNAMENTS)}")
    print(f"
💡 Просто открой {OUTPUT_FILE} в браузере!")
