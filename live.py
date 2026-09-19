# -*- coding: utf-8 -*-
"""
さじかげんLP の確認用サーバー

  起動:        python live.py
  ページを見る: http://127.0.0.1:8210/
  編集する:    http://127.0.0.1:8210/__edit   ← 左でHTMLを編集、右に即プレビュー

・編集画面では、右のプレビューで文字をクリックすると、左のエディタのその行に飛ぶ
・Ctrl+S で index.html に保存（直前の版は index.html.bak に1つだけ残る）
・ふつうのページ（/）は、index.html を保存すると1秒以内に自動で再読み込みされる
・キャッシュは使わない。自動更新のしかけは配信するときだけ差し込み、index.html には書き足さない
"""
import http.server, os, sys, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "index.html")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8210
WATCH = (".html", ".css", ".js", ".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif")

# ---- ふつうのページ用：保存を検知して再読み込み ----
INJECT = b"""
<script>
(function(){
  var last = null;
  setInterval(function(){
    fetch('/__mtime?' + Date.now(), {cache:'no-store'})
      .then(function(r){ return r.text(); })
      .then(function(t){ if(last && t !== last){ location.reload(); } last = t; })
      .catch(function(){});
  }, 700);
})();
</script>
"""

# ---- 編集画面 ----
EDITOR = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>さじかげん 編集</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/theme/material-darker.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/dialog/dialog.min.css">
<style>
  html,body{margin:0;height:100%;background:#1b1b1b;color:#ddd;font-family:"Yu Gothic UI","Meiryo",system-ui,sans-serif}
  .bar{height:44px;display:flex;align-items:center;gap:14px;padding:0 14px;background:#111;border-bottom:1px solid #2c2c2c;font-size:13px}
  .bar b{color:#fff;font-size:14px}
  .bar .tip{color:#9a9a9a}
  .bar .st{margin-left:auto;white-space:nowrap}
  .bar button{background:#2F6B4F;color:#fff;border:0;border-radius:6px;padding:7px 14px;font-size:13px;cursor:pointer;font-family:inherit}
  .bar button:hover{background:#3a8462}
  .bar a{color:#9BC3AC;text-decoration:none}
  .main{display:flex;height:calc(100% - 45px)}
  .left{width:48%;min-width:240px;height:100%}
  .gutter{width:7px;cursor:col-resize;background:#222;flex:none}
  .gutter:hover{background:#2F6B4F}
  .right{flex:1;min-width:240px;height:100%;background:#fff}
  .right iframe{width:100%;height:100%;border:0;display:block}
  .CodeMirror{height:100%;font-size:13.5px;font-family:Consolas,"BIZ UDGothic","MS Gothic",monospace}
  #src{width:100%;height:100%;box-sizing:border-box;background:#1e1e1e;color:#ddd;border:0;padding:10px;
       font:13.5px Consolas,"BIZ UDGothic",monospace;resize:none}
  .dragging iframe{pointer-events:none}
  .warn{display:none;align-items:center;gap:12px;padding:8px 14px;background:#5a2336;color:#fff;font-size:13px}
  .warn.on{display:flex}
  .warn button{background:#fff;color:#5a2336;border:0;border-radius:5px;padding:5px 12px;font:inherit;cursor:pointer}
  .main.warned{height:calc(100% - 45px - 38px)}
</style>
</head>
<body>
<div class="bar">
  <b>さじかげん 編集</b>
  <span class="tip">右の文字をクリック → 左のその行へ ／ Ctrl+F で検索 ／ Ctrl+S で保存</span>
  <span class="st" id="st">読み込み中…</span>
  <a href="/" target="_blank">ページだけ開く</a>
  <button id="save">保存 (Ctrl+S)</button>
</div>
<div class="warn" id="warn"><span>ほかの場所で index.html が変更されました。このまま保存すると、その変更は消えます。</span>
  <button id="reloadSrc">最新を読み込む</button><button id="keepMine">自分の内容で上書きする</button></div>
<div class="main" id="main">
  <div class="left" id="left"><textarea id="src" spellcheck="false"></textarea></div>
  <div class="gutter" id="gutter" title="ドラッグで幅を変える"></div>
  <div class="right"><iframe id="pv" title="プレビュー"></iframe></div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/xml/xml.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/javascript/javascript.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/css/css.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/htmlmixed/htmlmixed.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/search/searchcursor.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/search/search.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/dialog/dialog.min.js"></script>
<script>
(function(){
  var ta = document.getElementById('src'), pv = document.getElementById('pv'), st = document.getElementById('st');
  var cm = null, dirty = false, timer = null, known = null, saving = false;
  function stamp(){ return fetch('/__imtime?' + Date.now(), {cache:'no-store'}).then(function(r){ return r.text(); }); }
  function setWarn(on){ document.getElementById('warn').classList.toggle('on', on);
    document.getElementById('main').classList.toggle('warned', on); if (cm) cm.refresh(); }
  function loadSource(){
    return fetch('/__source', {cache:'no-store'}).then(function(r){ return r.text(); }).then(function(txt){
      if (cm){ var c = cm.getCursor(), sc = cm.getScrollInfo(); cm.setValue(txt); cm.setCursor(c); cm.scrollTo(sc.left, sc.top); }
      else { ta.value = txt; }
      dirty = false; return stamp().then(function(t){ known = t; setWarn(false); render(); say('最新を読み込みました'); });
    });
  }
  setInterval(function(){
    if (saving || known === null) return;
    stamp().then(function(t){
      if (t === known) return;
      if (!dirty){ loadSource(); }      // 手を付けていなければ、黙って最新に入れ替える
      else { setWarn(true); say('外で変更あり', '#f88'); }
    }).catch(function(){});
  }, 1500);

  function say(msg, color){ st.textContent = msg; st.style.color = color || '#9BC3AC'; }
  function getVal(){ return cm ? cm.getValue() : ta.value; }

  fetch('/__source', {cache:'no-store'}).then(function(r){ return r.text(); }).then(function(txt){
    ta.value = txt;
    if (window.CodeMirror){
      cm = CodeMirror.fromTextArea(ta, {mode:'htmlmixed', theme:'material-darker', lineNumbers:true,
        lineWrapping:true, indentUnit:2, tabSize:2});
      cm.on('change', onChange);
    } else {
      ta.addEventListener('input', onChange);
    }
    stamp().then(function(t){ known = t; });
    render(); say('読み込みました');
  }).catch(function(){ say('index.html を読めませんでした', '#f88'); });

  function onChange(){
    dirty = true; say('未保存', '#fc6');
    clearTimeout(timer); timer = setTimeout(render, 350);
  }

  // プレビュー：画像のパスが通るように <base>、見やすいように演出を止める、クリックで左へ飛ぶ
  var PREP = '<base href="/"><style>.rv{opacity:1!important;transform:none!important;transition:none!important}'
           + '.hero-inner>*{opacity:1!important;transform:none!important;animation:none!important}</style>';
  var PICK = '<scr' + 'ipt>document.addEventListener("click",function(e){e.preventDefault();e.stopPropagation();'
           + 'var el=e.target;while(el&&!(el.innerText||"").trim())el=el.parentElement;if(!el)return;'
           + 'var t=(el.innerText||"").trim().split("\\n")[0];parent.postMessage({pick:t},"*");},true);</scr' + 'ipt>';

  function render(){
    var y = 0;
    try { y = pv.contentWindow.scrollY || 0; } catch(e){}
    var html = getVal();
    if (/<head[^>]*>/i.test(html)) html = html.replace(/<head([^>]*)>/i, '<head$1>' + PREP);
    else html = PREP + html;
    if (/<\/body>/i.test(html)) html = html.replace(/<\/body>/i, PICK + '</body>');
    else html = html + PICK;
    pv.onload = function(){ try { pv.contentWindow.scrollTo(0, y); } catch(e){} };
    pv.srcdoc = html;
  }

  // 右でクリックした文字を、左の <body> より後ろから探して選択する
  window.addEventListener('message', function(e){
    if (!e.data || !e.data.pick) return;
    var t = e.data.pick.replace(/\s+/g, ' ').trim();
    if (!cm){ say('クリック移動はエディタ読み込み後に使えます', '#fc6'); return; }
    var start = 0;
    cm.eachLine(function(l){ if (!start && /<body[\s>]/i.test(l.text)) start = cm.getLineNumber(l); });
    var tries = [t.slice(0, 30), t.slice(0, 14), t.slice(0, 7), t.slice(0, 4)];
    for (var i = 0; i < tries.length; i++){
      var q = tries[i]; if (!q) continue;
      var cur = cm.getSearchCursor(q, CodeMirror.Pos(start, 0));
      if (cur.findNext()){
        cm.setSelection(cur.from(), cur.to());
        cm.scrollIntoView({from: cur.from(), to: cur.to()}, 160);
        cm.focus();
        say((cur.from().line + 1) + '行目：' + q);
        return;
      }
    }
    say('左で見つかりませんでした：' + t.slice(0, 20), '#f88');
  });

  function save(force){
    if (!force && document.getElementById('warn').classList.contains('on')){
      say('先に上の赤い帯でどちらか選んでください', '#f88'); return;
    }
    saving = true; say('保存中…', '#fc6');
    fetch('/__save', {method:'POST', headers:{'Content-Type':'text/plain; charset=utf-8'}, body:getVal()})
      .then(function(r){ if (!r.ok) throw 0; return r.text(); })
      .then(function(t){ known = t; dirty = false; setWarn(false); say('保存しました ' + new Date().toLocaleTimeString()); })
      .catch(function(){ say('保存できませんでした（サーバーが止まっていないか確認）', '#f88'); })
      .then(function(){ saving = false; });
  }
  document.getElementById('reloadSrc').onclick = function(){ loadSource(); };
  document.getElementById('keepMine').onclick = function(){ save(true); };
  document.getElementById('save').onclick = function(){ save(false); };
  document.addEventListener('keydown', function(e){
    if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')){ e.preventDefault(); save(false); }
  });
  window.addEventListener('beforeunload', function(e){ if (dirty){ e.preventDefault(); e.returnValue = ''; } });

  // 真ん中の線をドラッグして幅を変える
  var g = document.getElementById('gutter'), left = document.getElementById('left'), main = document.getElementById('main');
  g.addEventListener('mousedown', function(e){
    e.preventDefault(); main.classList.add('dragging');
    function mv(ev){ var w = Math.max(240, Math.min(ev.clientX, main.clientWidth - 240)); left.style.width = w + 'px'; if (cm) cm.refresh(); }
    function up(){ main.classList.remove('dragging'); document.removeEventListener('mousemove', mv); document.removeEventListener('mouseup', up); }
    document.addEventListener('mousemove', mv); document.addEventListener('mouseup', up);
  });
})();
</script>
</body>
</html>
"""

def latest_mtime():
    m = 0.0
    for dp, _, files in os.walk(ROOT):
        for f in files:
            if f.lower().endswith(WATCH):
                try:
                    m = max(m, os.path.getmtime(os.path.join(dp, f)))
                except OSError:
                    pass
    return repr(m)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def _send(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path_only = self.path.split("?")[0].split("#")[0]
        if path_only == "/__mtime":
            return self._send(latest_mtime().encode(), "text/plain")
        if path_only == "/__imtime":
            return self._send(repr(os.path.getmtime(INDEX)).encode(), "text/plain")
        if path_only in ("/__edit", "/__edit/"):
            return self._send(EDITOR.encode("utf-8"), "text/html; charset=utf-8")
        if path_only == "/__source":
            with open(INDEX, "rb") as f:
                return self._send(f.read(), "text/plain; charset=utf-8")

        path = self.translate_path(path_only)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        if path.lower().endswith(".html") and os.path.isfile(path):
            with open(path, "rb") as f:
                data = f.read()
            data = data.replace(b"</body>", INJECT + b"</body>", 1) if b"</body>" in data else data + INJECT
            return self._send(data, "text/html; charset=utf-8")
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/__save":
            self.send_error(404); return
        n = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(n)
        if not body.strip():
            self.send_error(400, "empty"); return   # 空で上書きしない
        try:
            if os.path.isfile(INDEX):
                shutil.copy2(INDEX, INDEX + ".bak")  # 直前の版を1つだけ残す
            with open(INDEX, "wb") as f:
                f.write(body)
        except OSError as e:
            self.send_error(500, str(e)); return
        self._send(repr(os.path.getmtime(INDEX)).encode(), "text/plain")

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    print("さじかげん 確認用サーバー")
    print("  ページ:   http://127.0.0.1:%d/" % PORT)
    print("  編集画面: http://127.0.0.1:%d/__edit" % PORT)
    print("  止めるときは Ctrl+C")
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
