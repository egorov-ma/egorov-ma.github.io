#!/usr/bin/env bash
# Проверка личного сайта: локальная сборка (--dist cv|projects|all) или живой сайт (<url> [--no-domain]).
# Ищет утечки (телефон, рабочая почта, возраст, инфраструктура VPN), трекеры и внешние скрипты.
# Реальные персональные данные берутся из CV в момент проверки и в вывод не печатаются.
set -uo pipefail
cd "$(dirname "$0")/.."
CV_TEX="${CV_TEX:-$HOME/projects/cv/resume/CV.tex}"
MIN_CARDS="${MIN_CARDS:-8}"
fail=0
ok()  { echo "  ok    $*"; }
bad() { echo "  FAIL  $*"; fail=1; }

# Проверки содержимого одной страницы: $1 — файл html, $2 — подпись
scan() {
  python3 - "$1" "$2" "$CV_TEX" <<'PY'
import re, sys, html, os
path, label, cv = sys.argv[1:4]
raw = open(path, encoding='utf-8', errors='replace').read()
text = html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', raw, flags=re.S)))
errs = []
if re.search(r'<script[^>]*\ssrc="https?:', raw): errs.append('внешний <script src>')
if re.search(r'googletagmanager|mc\.yandex|metrika|gtag\(', raw): errs.append('трекер')
phone_rx = r'(\+7|\b8|tel:\+?7)[ (-]*9[0-9]{2}[) -]*[0-9]{3}[ -]?[0-9]{2}[ -]?[0-9]{2}'
if re.search(phone_rx, text) or re.search(phone_rx, raw): errs.append('номер телефона по шаблону')
if re.search(r'85\.90\.208|185\.211\.170|80\.90\.191|aqstream\.ru|\b10810\b|\b2096\b|3x-ui|vless', raw, re.I): errs.append('инфраструктура VPN')
if re.search(r'@neoflex\.ru', raw, re.I): errs.append('рабочая почта')
if re.search(r'Возраст\s*:|\b\d{2}\s*(год|года|лет)\b', text): errs.append('возраст')
if os.path.exists(cv):
    src = open(cv, encoding='utf-8', errors='replace').read()
    m = re.search(r'\\phone\{([^}]*)\}', src)
    if m:
        tail = re.sub(r'\D', '', m.group(1))[-7:]
        if len(tail) == 7 and (tail in re.sub(r'\D', '', text) or tail in re.sub(r'\D', '', raw)): errs.append('хвост реального телефона из CV')
    m = re.search(r'\\email\{([^}]*)\}', src)
    if m and m.group(1).strip().lower() in raw.lower(): errs.append('личная почта из CV')
elif os.environ.get('CI'):
    print(f'  skip  {label}: сверка с CV пропущена в CI (CV не хранится в репо)')
else:
    errs.append('нет CV для сверки персональных данных')
for e in errs: print(f'  FAIL  {label}: {e}')
if not errs: print(f'  ok    {label}: утечек и трекеров нет')
sys.exit(1 if errs else 0)
PY
  [ $? -eq 0 ] || fail=1
}

check_dist() {
  local part=$1
  [ -d dist ] || { bad "нет dist — сначала npm run build"; return; }
  if [ "$part" = all ] || [ "$part" = cv ]; then
    f=dist/cv/index.html
    if [ -s "$f" ]; then
      for s in achievements experience stack; do grep -q "id=\"$s\"" "$f" && ok "cv: раздел $s" || bad "cv: нет раздела $s"; done
      scan "$f" cv
    else bad "нет $f"; fi
    n=$(git ls-files 2>/dev/null | grep -ciE '\.(tex|pdf|docx)$' || true)
    [ "${n:-0}" = 0 ] && ok "репо: исходников CV нет" || bad "репо: $n файлов .tex/.pdf/.docx"
  fi
  if [ "$part" = all ] || [ "$part" = projects ]; then
    f=dist/projects/index.html
    if [ -s "$f" ]; then
      c=$(grep -o 'class="project-card"' "$f" | wc -l | tr -d ' ')
      [ "$c" -ge "$MIN_CARDS" ] && ok "projects: карточек $c (минимум $MIN_CARDS)" || bad "projects: карточек $c < $MIN_CARDS"
      scan "$f" projects
      if grep -rqiE '85\.90\.208|185\.211\.170|80\.90\.191|aqstream\.ru|3x-ui|vless' src; then bad "src: инфраструктура VPN в исходниках"; else ok "src: инфраструктуры VPN нет"; fi
    else bad "нет $f"; fi
  fi
  if [ "$part" = all ]; then
    for f in $(find dist -name '*.html'); do scan "$f" "${f#dist/}"; done
  fi
}

check_url() {
  local base=${1%/} nodomain=${2:-}
  local tmp; tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
  for p in / /cv/ /projects/ /notes/; do
    code=$(curl -s -m 20 -o "$tmp/page.html" -w '%{http_code}' "$base$p")
    if [ "$code" = 200 ]; then ok "$p → 200 (сертификат принят)"; scan "$tmp/page.html" "$p"; else bad "$p → $code"; fi
  done
  if [ "$nodomain" != --no-domain ]; then
    host=${base#https://}
    code=$(curl -s -m 20 -o /dev/null -w '%{http_code}' "http://$host/")
    [ "$code" = 301 ] && ok "http → 301" || bad "http → $code (ждали 301)"
    loc=$(curl -s -m 20 -o /dev/null -w '%{redirect_url}' "https://www.$host/")
    case "$loc" in https://$host/*|https://$host) ok "www → apex" ;; *) bad "www не ведёт на apex ($loc)" ;; esac
  fi
  rm -rf "$tmp"
}

case "${1:-}" in
  --dist) case "${2:-all}" in cv|projects|all) check_dist "${2:-all}" ;; *) echo "Неизвестная часть: ${2} (cv|projects|all)"; exit 2 ;; esac ;;
  https://*) check_url "$1" "${2:-}" ;;
  *) echo "Использование: $0 --dist <cv|projects|all> | $0 <https://url> [--no-domain]  (для *.github.io — с --no-domain)"; exit 2 ;;
esac
[ $fail = 0 ] && echo "ИТОГ: ok" || echo "ИТОГ: FAIL"
exit $fail
