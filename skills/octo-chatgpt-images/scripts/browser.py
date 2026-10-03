#!/usr/bin/env python3
"""Submit and collect ChatGPT website jobs through Google's Chrome DevTools CLI.

Start writes a run directory before sending; collect never sends or retries a job.
Requires chrome-devtools (chrome-devtools-mcp package) and signed-in Chrome on Linux or macOS.
"""
import argparse
import base64
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit


class BrowserError(RuntimeError):
    pass


MAX_CITATIONS = 256
MAX_CITATION_BYTES = 512 * 1024
MAX_CLEANUP_BYTES = 4096
CONVERSATION_PATHS = ('/backend-api/f/conversation', '/backend-api/conversation')


def cli(*args):
    result = subprocess.run(['chrome-devtools', *map(str, args)],
                            capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise BrowserError(result.stderr.strip() or 'Chrome DevTools command failed')
    if re.match(r'(Error:|Could not |Protocol error)', result.stdout):
        raise BrowserError(result.stdout.strip())
    return result.stdout


def evaluate(page, body, *, uid=None):
    args = ('--args', uid) if uid else ()
    message = cli('evaluate_script', 'async (root) => {' + body + '}', '--pageId', page,
                  '--waitForStableDom', 'false', *args)
    match = re.search(r'```json\n(.*?)\n```', message, re.S)
    if not match:
        raise BrowserError(message)
    return json.loads(match[1])


def require_browser_daemon():
    status = cli('status')
    match = re.search(r'^args=(.*)$', status, re.M)
    if not match or '--auto-connect' not in json.loads(match[1]):
        raise BrowserError('Start the browser CLI with: chrome-devtools start --autoConnect '
                           '--no-usage-statistics --no-performance-crux. '
                           'Do not restart it while a run is pending.')


def save(run, state):
    temporary = run / 'run.json.tmp'
    temporary.write_text(json.dumps(state, indent=2) + '\n')
    temporary.replace(run / 'run.json')


def wait_until(check, seconds=30, description='Browser readiness'):
    deadline = time.monotonic() + seconds
    while True:
        value = check()
        if value:
            return value
        if time.monotonic() >= deadline:
            raise BrowserError(description + ' timed out; inspect the preserved tab')
        time.sleep(2)


def click(page, selector):
    wait_until(lambda: evaluate(page, 'return !!document.querySelector(' + json.dumps(selector) + ');'),
               description='Waiting for ' + selector)
    evaluate(page, 'const e=document.querySelector(' + json.dumps(selector) + ');'
             'if(!e) throw new Error(' + json.dumps('Required control missing: ' + selector) + ');'
             'e.click(); return true;')


def model_proof(page, mode):
    click(page, 'button[aria-label="Select ChatGPT model"]')
    wait_until(lambda: evaluate(page, "return !!document.querySelector('[role=menu] [role=slider]');"))
    proof = evaluate(page, '''const m=document.querySelector('[role="menu"]');
        return {text:m?.innerText,
          value:m?.querySelector('[role="slider"]')?.getAttribute('aria-valuenow')};''')
    cli('press_key', page, 'Escape')
    validate_model(mode, proof)
    return proof


def validate_model(mode, proof):
    text = proof.get('text') or ''
    if mode == 'images':
        valid = proof.get('value') == '0' and bool(re.search(r'\bInstant\b', text))
    else:
        valid = proof.get('value') == '4' and bool(re.search(r'(?:^|\n)(?:GPT-)?6\s*\nPro(?:\n|$)', text))
    if not valid:
        raise BrowserError(f'Model mismatch for {mode}: {text!r}. Nothing will be sent.')


def select_model(page, mode):
    click(page, 'button[aria-label="Select ChatGPT model"]')
    click(page, '[role="menuitem"][aria-label="Select model"]')
    wait_until(lambda: evaluate(page, "return !!document.querySelector('[role=menuitemradio]');"))
    evaluate(page, '''const e=[...document.querySelectorAll('[role="menuitemradio"]')]
      .find(e=>e.innerText.trim()==='Latest');
      if(!e) throw new Error('Latest model option missing'); e.click(); return true;''')
    cli('press_key', page, 'Escape')
    click(page, 'button[aria-label="Select ChatGPT model"]')
    wait_until(lambda: evaluate(page, "return !!document.querySelector('[role=menuitem][aria-label=Power]');"))
    evaluate(page, '''const e=document.querySelector('[role="menuitem"][aria-label="Power"]');
      if(!e) throw new Error('Power control missing'); e.focus(); return true;''')
    for _ in range(4):
        cli('press_key', page, 'ArrowLeft' if mode == 'images' else 'ArrowRight')
    cli('press_key', page, 'Escape')
    return model_proof(page, mode)


def snapshot_uid(page, role, label, *, allow_description=False):
    snapshot = cli('take_snapshot', page)
    pattern = r'uid=(\S+) ' + re.escape(role) + r' ("(?:[^"\\\n]|\\.)*")'
    matches = []
    for uid, name in re.findall(pattern, snapshot):
        name = json.loads(name)
        if name == label or (allow_description and name.startswith(label + ' ')):
            matches.append(uid)
    if len(matches) != 1:
        raise BrowserError(f'Expected one {label!r} control, found {len(matches)}')
    return matches[0]


PROMPT_TEXT_SCRIPT = r'''const promptText=(e,restoreCode=false)=>{
      if(!e) return undefined;
      const icon='[data-rich-text-generated-autolink] [data-inline-url-icon][aria-hidden="true"][contenteditable="false"], '
        + 'a[data-inline-mention-interactive][href] > [data-layout="inline-flow"] > [data-markdown-copy="exclude"]:has(img[alt=""])';
      const inlineCode=node=>restoreCode && node.tagName==='CODE' && !node.closest('pre');
      if(!e.querySelector(icon) && ![...e.querySelectorAll('code')].some(inlineCode)) return e.innerText.trim();
      // innerText adds layout breaks around URL icons; retain actual DOM text and breaks.
      let text='', boundary=0;
      const append=value=>{
        if(!value) return;
        if(boundary && text) {
          const trailing=text.match(/\n*$/)[0].length;
          text+='\n'.repeat(Math.max(0,boundary-trailing));
        }
        boundary=0;
        text+=value;
      };
      const read=node=>{
        if(node.nodeType===Node.TEXT_NODE) { append(node.data); return; }
        if(node.nodeType!==Node.ELEMENT_NODE || node.matches(icon)) return;
        // Sent user bubbles render inline code without its source delimiters.
        // Composer text remains literal; only restore the observed single-backtick form.
        if(inlineCode(node)) { append('`'+node.innerText+'`'); return; }
        if(node.tagName==='BR') { append('\n'); return; }
        const separator=node.tagName==='P' ? 2 :
          /^(DIV|PRE|BLOCKQUOTE|LI|UL|OL)$/.test(node.tagName) ? 1 : 0;
        boundary=Math.max(boundary,separator);
        node.childNodes.forEach(read);
        boundary=Math.max(boundary,separator);
      };
      e.childNodes.forEach(read);
      return text.trim();
    };'''


RESPONSE_TEXT_SCRIPT = r'''const responseText=root=>{
      if(!root) return '';
      if(!root.matches('.katex') && !root.querySelector('.katex')) return root.innerText || '';
      // Read original rendered nodes: detached clones lose innerText layout and
      // SVG radicals have no text. Serialize each complete math expression once.
      let text='', boundary=0;
      const append=(value,collapse=false)=>{
        if(!value) return;
        if(collapse) {
          value=value.replace(collapse==='pre-line' ? /[\t\r\f ]+/g : /[\t\n\r\f ]+/g,' ');
          if(collapse==='pre-line') value=value.replace(/ *\n */g,'\n');
          if(boundary || !text || text.endsWith(' ')) value=value.replace(/^ +/,'');
          if(!value) return;
        }
        if(boundary && text) {
          text=text.replace(/[\t ]+$/,'');
          const trailing=text.match(/\n*$/)[0].length;
          text+='\n'.repeat(Math.max(0,boundary-trailing));
        }
        boundary=0;
        text+=value;
      };
      const read=node=>{
        if(node.nodeType===Node.TEXT_NODE) {
          const style=getComputedStyle(node.parentElement);
          if(/^(hidden|collapse)$/.test(style.visibility)) return;
          append(node.data,style.whiteSpace==='pre-line' ? 'pre-line' :
            !/^(pre|pre-wrap|break-spaces)$/.test(style.whiteSpace));
          return;
        }
        if(node.nodeType!==Node.ELEMENT_NODE) return;
        const style=getComputedStyle(node);
        if(style.display==='none' || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(node.tagName)) return;
        if(node.matches('.katex')) {
          if(/^(hidden|collapse)$/.test(style.visibility)) return;
          const tex=node.querySelector('annotation[encoding="application/x-tex"]')?.textContent;
          if(!tex?.trim()) throw new Error('Math expression has no TeX annotation');
          const delimiter=node.closest('.katex-display') ? '$$' : '$';
          append(delimiter+tex+delimiter);
          return;
        }
        if(node.tagName==='BR') {
          if(!/^(hidden|collapse)$/.test(style.visibility)) append('\n');
          return;
        }
        const separator=node.tagName==='P' || node.matches('.katex-display') ? 2 :
          /^(block|flow-root|flex|grid|list-item|table|table-row|table-caption)$/.test(style.display) ? 1 : 0;
        boundary=Math.max(boundary,separator);
        if(style.display==='table-row' && node.querySelector('.katex')) {
          const cells=[...node.children].filter(c=>getComputedStyle(c).display==='table-cell');
          cells.forEach((cell,index)=>{
            if(index) append('\t');
            append(responseText(cell));
          });
        } else if(style.display!=='contents' && !node.querySelector('.katex') &&
                  typeof node.innerText==='string') {
          append(node.innerText);
        } else {
          node.childNodes.forEach(read);
        }
        boundary=Math.max(boundary,separator);
      };
      read(root);
      return text.trim();
    };'''


def composer(page):
    return evaluate(page, PROMPT_TEXT_SCRIPT + '''
      const editors=[...document.querySelectorAll('form [role=textbox][contenteditable=true]')]
        .filter(e=>e.getClientRects().length &&
          !/^(hidden|collapse)$/.test(getComputedStyle(e).visibility));
      if(editors.length!==1) throw new Error('Expected one visible form-backed composer; found '+editors.length);
      const e=editors[0], f=e.closest('form');
      return {text:promptText(e),
        files:[...f.querySelectorAll('[data-composer-attachments] button[aria-label^="Remove "]')]
          .map(b=>b.getAttribute('aria-label').slice(7)),
        busy:!!f?.querySelector('[role="progressbar"], [aria-busy="true"]'),
        send:!!f?.querySelector('button[aria-label="Send"]:not(:disabled)')};''')


def upload(page, files):
    if not files:
        return
    click(page, 'button[aria-label="Add files and more"]')
    uid = snapshot_uid(page, 'button', 'Add photos & files', allow_description=True)
    cli('upload_file', page, uid, *files)
    wait_until(lambda: attachments_match(files, composer(page)['files']), 60)


def attachments_match(expected, actual):
    remaining = list(actual)
    for path in expected:
        name = Path(path).name
        # Chat may rename a completed upload after its initial chip appears.
        pattern = (re.escape(Path(name).stem) + r'(?:\((?:\d+|\d{8}-\d{6})\))?'
                   + re.escape(Path(name).suffix))
        match = next((item for item in remaining if re.fullmatch(pattern, item)), None)
        if match is None:
            return False
        remaining.remove(match)
    return not remaining


def verify_draft(draft, prompt, files):
    if draft.get('text') != prompt.strip():
        raise BrowserError('Composer does not match the requested prompt')
    if draft.get('busy') or not draft.get('send'):
        raise BrowserError('Uploads or send control are not ready')
    if not attachments_match(files, draft.get('files', [])):
        raise BrowserError(f'Composer attachments do not match: expected '
                           f'{[Path(p).name for p in files]!r}, found {draft.get("files", [])!r}')


def research_proof(page):
    return evaluate(page, '''const e=document.querySelector('[role=textbox][contenteditable=true]');
      return [...e.querySelectorAll('[app-mention-path]')].map(m=>({
        name:m.getAttribute('app-mention-name'), path:m.getAttribute('app-mention-path'),
        label:m.getAttribute('app-mention-display-name')}));''')


def validate_research(proof):
    if proof != [{'name': 'deep-research', 'path': 'app://connector_openai_deep_research',
                  'label': 'Deep research'}]:
        raise BrowserError('Deep Research plugin is not selected; nothing will be sent')


def select_research(page):
    click(page, 'button[aria-label="Add files and more"]')
    uid = snapshot_uid(page, 'button', 'Deep research', allow_description=True)
    cli('click', page, uid)
    proof = wait_until(lambda: research_proof(page))
    validate_research(proof)
    return proof


def verify_research_draft(draft, prompt, files):
    # The UI inserts its chip at the current caret, at either end of our filled prompt.
    expected = (prompt.strip() + '\nDeep research', 'Deep research ' + prompt.strip())
    if draft.get('text') not in expected:
        raise BrowserError('Research composer does not match the requested prompt')
    verify_draft(draft, draft['text'], files)


def request_model(page, request_id, *, run=None):
    # Inline network bodies are truncated by the CLI. Read its complete export
    # inside our owned workspace, then remove the raw submission on every exit.
    with tempfile.TemporaryDirectory(prefix='.browser-request-', dir=run or Path.cwd()) as scratch:
        path = Path(scratch) / 'submission.network-request'
        cli('get_network_request', page, '--reqid', request_id, '--requestFilePath', path)
        body = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(body, dict):
        raise BrowserError('Captured submission body is not a JSON object')
    return body.get('model')


def validate_request_model(mode, model):
    if not isinstance(model, str) or not model:
        raise BrowserError('No model identifier in captured browser submission')
    valid = (mode == 'research' or
             (model == 'gpt-6-pro' if mode == 'analysis' else 'pro' not in model.lower()))
    if not valid:
        raise BrowserError(f'Unexpected submitted model for {mode}: {model}')


def network_evidence(page, mode, *, run=None):
    message = cli('list_network_requests', page, '--includePreservedRequests')
    entries = []
    models = []
    for line in message.splitlines():
        match = re.search(r'reqid=(\d+) (GET|POST) (https://\S+) \[([^]]+)\]', line)
        if not match:
            continue
        url = urlsplit(match[3])
        if url.hostname == 'chatgpt.com' and url.path.startswith('/backend-api/'):
            entries.append({'method': match[2], 'path': url.path, 'status': match[4]})
            if match[2] == 'POST' and url.path in CONVERSATION_PATHS and match[4] == '200':
                model = request_model(page, match[1], run=run)
                validate_request_model(mode, model)
                models.append(model)
    if any(e['path'].startswith('/backend-api/codex') for e in entries):
        raise BrowserError('Unexpected Codex endpoint in browser traffic; inspect the run')
    return {'chatgpt_conversation_request': bool(models), 'codex_requests': 0,
            'submitted_models': models, 'requests': entries}


def observe(page, *, legacy=False):
    reader = 'e?.innerText || ""' if legacy else 'responseText(e)'
    return evaluate(page, PROMPT_TEXT_SCRIPT + RESPONSE_TEXT_SCRIPT +
      'const assistantText=e=>' + reader + ';' + r'''const visible=e=>!!e && e.getClientRects().length>0 &&
      getComputedStyle(e).visibility!=='hidden' && getComputedStyle(e).display!=='none';
      const main=[...document.querySelectorAll('main')].find(visible);
      if(!main) throw new Error('Visible conversation missing');
      // Current Chat uses accessible turn headings instead of role attributes.
      let turns=[...main.querySelectorAll('h4')]
        .filter(e=>/^(You said:|ChatGPT said:)$/.test(e.textContent.trim()) && visible(e.parentElement));
      if(!turns.length) turns=[...main.querySelectorAll('[data-message-author-role], [data-conversation-role]')]
        .filter(visible);
      const marker=turns.at(-1);
      const role=marker?.getAttribute('data-message-author-role') || marker?.getAttribute('data-conversation-role');
      const assistant=role==='assistant' || marker?.textContent.trim()==='ChatGPT said:';
      const last=assistant ? (marker.tagName==='H4' ? marker.parentElement : marker) : null;
      const citations=[];
      for(const anchor of last?.querySelectorAll('a[href]') || []) {
        if(!visible(anchor) || !/^https?:/.test(anchor.href)) continue;
        const context=anchor.closest('p,li,td,th,blockquote') || anchor.parentElement;
        const quote=(assistantText(anchor).trim() || assistantText(context).trim()).slice(0,2048);
        if(citations.some(c=>c.url===anchor.href && c.context_quote===quote)) continue;
        citations.push({url:anchor.href,context_quote:quote});
        if(citations.length>256) throw new Error('Assistant has more than 256 citation links');
      }
      return {url:location.href, users:[...main.querySelectorAll('[data-user-message-bubble]')]
        .filter(visible).map(e=>{
          const content=e.querySelector('[data-search-result-target]') || e.querySelector('[dir="auto"]') || e;
          return promptText(content,true);
        }),
        text:assistantText(last).replace(/^ChatGPT said:\s*/, '').trim(), citations,
        streaming:[...document.querySelectorAll('button[data-testid="stop-button"],button[aria-label="Stop streaming"],button[aria-label="Stop"]')].some(visible),
        complete:!!last && ([...document.querySelectorAll('[role="status"]')]
          .some(e=>visible(e)&&e.innerText==='Response complete') ||
          [...main.querySelectorAll('button')].some(e=>visible(e)&&
            (marker.compareDocumentPosition(e)&Node.DOCUMENT_POSITION_FOLLOWING)&&
            /^(Copy|Copy image|Good response|Bad response)$/.test(e.getAttribute('aria-label')||''))),
        images:[...(last?.querySelectorAll('img') || [])]
          .filter(i=>visible(i)&&/^Generated image/.test(i.alt)&&i.complete&&i.naturalWidth>0)
          .map(i=>({alt:i.alt,src:i.currentSrc||i.src,width:i.naturalWidth,height:i.naturalHeight}))};''')


def research_root_uid(snapshot):
    frames = list(re.finditer(r'(?m)^( *)uid=\S+ Iframe "Deep research"\s*$', snapshot))
    if len(frames) > 1:
        raise BrowserError('Multiple research widgets; cannot identify the original task')
    if not frames:
        return None
    frame = frames[0]
    for line in snapshot[frame.end():].splitlines():
        match = re.match(r'( *)uid=(\S+) (\S+)', line)
        if not match:
            continue
        if len(match[1]) <= len(frame[1]):
            break
        if match[3] == 'main':
            return match[2]
    return None


def observe_research(page):
    uid = research_root_uid(cli('take_snapshot', page))
    if not uid:
        return {'phase': 'waiting', 'text': '', 'complete': False}
    data = evaluate(page, r'''const buttons=[...root.querySelectorAll('button')]
      .map(b=>b.getAttribute('aria-label')||b.innerText.trim());
      const pages=[...root.querySelectorAll('[class*="_reportPage_"]')];
      return {status:root.innerText, text:pages.map(p=>p.innerText).join('\n\n'), buttons,
        links:pages.flatMap(p=>[...p.querySelectorAll('a[href]')])
          .filter(a=>/^https?:/.test(a.href)).map(a=>({title:a.innerText.trim(),url:a.href}))};''', uid=uid)
    data['complete'] = research_finished(data)
    data['phase'] = ('complete' if data['complete'] else
                     'researching' if 'Stop research' in data['buttons'] else
                     'awaiting_plan' if any(b.startswith('Start') for b in data['buttons']) else 'needs_input')
    return data


def research_finished(data):
    return bool(re.match(r'^Research completed in\b', data['status']) and data['text'] and
                'Export' in data['buttons'] and 'Stop research' not in data['buttons'])


def observe_run(page, mode):
    observation = observe(page)
    if mode == 'research':
        research = observation['research'] = observe_research(page)
        if (research['phase'] == 'waiting' and observation['complete'] and
                not observation['streaming'] and observation['text']):
            research['phase'] = 'needs_input'
        if research['complete']:
            observation['text'] = research['text']
    return observation


def conversation_url(url):
    return url if re.fullmatch(r'https://chatgpt\.com/c/[0-9a-f-]{36}', url) else None


def prompt_visible(state, observation):
    expected = state.get('submitted_prompt', state['prompt'])
    users = observation['users']
    if state.get('mode') == 'research':
        # The rendered plugin chip adds a line break absent from the composer.
        expected = ' '.join(expected.split())
        users = [' '.join(text.split()) for text in users]
    return expected in users


def verify_conversation(state, observation):
    if not prompt_visible(state, observation):
        raise BrowserError('Cannot confirm original prompt in this tab; never resend automatically')
    previous = conversation_url(state.get('url') or '')
    if previous and previous != observation['url']:
        raise BrowserError('Browser tab no longer matches the original conversation')


def start(args):
    run = args.run.resolve()
    run.mkdir(parents=True, exist_ok=False)
    with (run / 'collect.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        submit(args, run)


def submit(args, run):
    prompt = args.prompt.read_text().strip()
    if not prompt:
        raise BrowserError('Prompt is empty')
    files = [str(p.resolve(strict=True)) for p in args.attach]
    if len({Path(p).name for p in files}) != len(files):
        raise BrowserError('Attachment filenames must be unique')
    state = {'mode': args.mode, 'phase': 'preparing', 'prompt': prompt, 'attachments': files}
    (run / 'prompt.txt').write_text(prompt + '\n')
    save(run, state)
    try:
        pages = cli('new_page', 'https://chatgpt.com/')
        match = re.search(r'^(\d+): .*https://chatgpt.com/.*\[selected\]', pages, re.M)
        if not match:
            raise BrowserError(pages)
        page = state['page'] = int(match[1])
        save(run, state)
        wait_until(lambda: evaluate(page, "return !!document.querySelector('[role=textbox][contenteditable=true]');"))
        chat = evaluate(page, '''const b=[...document.querySelectorAll('button')].find(e=>e.textContent==='Chat');
          if(b?.getAttribute('aria-pressed')==='true') return true; return false;''')
        if not chat:
            raise BrowserError('New page must have Chat selected, not Work')
        state['chat_mode'] = 'Chat'
        draft = composer(page)
        if draft['text'] or draft['files']:
            raise BrowserError('Existing browser draft preserved; clear it before starting a new run')
        if args.mode != 'research':
            state['model'] = select_model(page, args.mode)
        upload(page, files)
        uid = snapshot_uid(page, 'textbox', 'Ask ChatGPT')
        cli('fill', page, uid, prompt)
        if args.mode == 'research':
            state['research'] = select_research(page)
        wait_until(lambda: (draft := composer(page))['send'] and not draft['busy'], 60)
        if args.mode == 'research':
            state['research'] = research_proof(page)
            validate_research(state['research'])
            draft = composer(page)
            verify_research_draft(draft, prompt, files)
            state['submitted_prompt'] = draft['text']
        else:
            state['model'] = model_proof(page, args.mode)
            verify_draft(composer(page), prompt, files)
        state['phase'] = 'sending'
        state['send_attempt_ms'] = time.time_ns() // 1_000_000
        save(run, state)  # A timeout after this point must never trigger a resend.
        click(page, 'button[aria-label="Send"]')
        wait_until(lambda: prompt_visible(state, observe(page)), 30)
        state.update(phase='submitted', url=conversation_url(observe(page)['url']))
        state['submission_confirmed_ms'] = time.time_ns() // 1_000_000
        save(run, state)
        result = {'phase': state['phase'], 'run': str(run), 'url': state['url']}
        key = 'research' if args.mode == 'research' else 'model'
        result[key] = state[key]
        print(json.dumps(result))
    except Exception as error:
        state['error'] = str(error)
        save(run, state)
        raise


def is_finished(mode, observation):
    if observation.get('streaming'):
        return False
    if mode == 'research':
        return bool(observation.get('research', {}).get('complete') and observation.get('text'))
    if not observation.get('complete'):
        return False
    return bool(observation.get('images') if mode == 'images' else observation.get('text'))


def download(page, src):
    value = evaluate(page, '''const r=await fetch(''' + json.dumps(src) + ''');
      if(!r.ok) throw new Error('Image download failed: '+r.status);
      const b=await r.blob(); return await new Promise((resolve,reject)=>{
        const f=new FileReader(); f.onerror=reject; f.onload=()=>resolve({type:b.type,data:f.result});f.readAsDataURL(b)});''')
    data = base64.b64decode(value['data'].split(',', 1)[1], validate=True)
    extensions = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp'}
    if value['type'] not in extensions or not data:
        raise BrowserError('Downloaded result is not a supported image')
    return data, extensions[value['type']]


def close_completed_tab(state, observation, *, legacy=False):
    try:
        current = (observe(state['page'], legacy=True) if legacy else
                   observe_run(state['page'], state['mode']))
        draft = composer(state['page'])
        if (current != observation or draft['text'] or draft['files'] or draft['busy']):
            return 'kept: tab changed after collection'
        cli('close_page', state['page'])
        return 'closed'
    except (BrowserError, OSError, ValueError, subprocess.SubprocessError) as error:
        return 'close failed: ' + str(error)


def hydration_equivalent(original, current):
    # Preserve words, numbers, punctuation, currency and math boundaries. Only
    # paired TeX delimiters and whitespace between unchanged tokens may differ.
    math = re.compile(r'\\\[(.*?)\\\]|\\\((.*?)\\\)|'
                      r'(?<![\\$])\$\$(.*?)(?<!\\)\$\$(?!\$)|'
                      r'(?<![\\$])\$(?!\$)(.*?)(?<!\\)\$(?!\$)', re.S)

    def tokens(text):
        return re.findall(r'\w+|[^\w\s]', text)

    def parts(text):
        result = []
        end = 0
        for match in math.finditer(text):
            index = next(i for i, value in enumerate(match.groups()) if value is not None)
            # A pair of prices such as "$10 and $20" is not inline math. Refuse
            # ambiguous numeric dollar spans even if the other rendering uses TeX.
            if index == 3 and re.match(r'\s*[-+]?(?:\d|[.,]\d|[A-Z]{3}\s+\d)', match[4]):
                continue
            result.append(('text', tokens(text[end:match.start()])))
            result.append(('display' if index in (0, 2) else 'inline', tokens(match[index + 1])))
            end = match.end()
        result.append(('text', tokens(text[end:])))
        return result

    return parts(original) == parts(current)


def validate_cleanup_network(evidence):
    if (not isinstance(evidence, dict) or
            evidence.get('chatgpt_conversation_request') is not True or
            type(evidence.get('codex_requests')) is not int or evidence['codex_requests'] != 0 or
            evidence.get('submitted_models') != ['gpt-6-pro']):
        raise BrowserError('Cleanup requires exactly one verified GPT-6 Pro submission and zero Codex requests')
    requests = evidence.get('requests')
    if not isinstance(requests, list) or not all(isinstance(row, dict) and
            all(isinstance(row.get(key), str) for key in ('method', 'path', 'status')) for row in requests):
        raise BrowserError('Cleanup requires the original browser request evidence')
    if any(row['path'].startswith('/backend-api/codex') for row in requests):
        raise BrowserError('Cleanup refuses Codex request evidence')
    submissions = [row for row in requests if row['method'] == 'POST' and row['path'] in
                   CONVERSATION_PATHS]
    if len(submissions) != 1 or submissions[0]['status'] != '200':
        raise BrowserError('Cleanup requires exactly one successful original conversation POST')
    return submissions[0]


def cleanup_receipt(run, expected):
    path = run / 'tab_cleanup.json'
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CLEANUP_BYTES:
        raise BrowserError('Tab cleanup receipt must be a regular file of at most 4 KiB')
    data = path.read_bytes()
    payload = json.loads(data)
    if (not isinstance(payload, dict) or payload != expected or
            type(payload.get('version')) is not int or type(payload.get('page')) is not int):
        raise BrowserError('Tab cleanup receipt conflicts with the immutable completed run')
    return {'file': path.name, 'sha256': hashlib.sha256(data).hexdigest()}


def cleanup_completed(args):
    run = args.run.resolve(strict=True)
    lock_path = run / 'collect.lock'
    if lock_path.is_symlink() or not lock_path.is_file():
        raise BrowserError('Cleanup requires the regular owned collection lock')
    with lock_path.open('r') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        archive = {}
        for name in ('run.json', 'response.md', 'network.json', 'source_citations.json'):
            path = run / name
            if name == 'source_citations.json' and not path.exists() and not path.is_symlink():
                continue
            if path.is_symlink() or not path.is_file():
                raise BrowserError('Cleanup requires regular owned ' + name)
            archive[name] = path.read_bytes()
        state = json.loads(archive['run.json'])
        if (not isinstance(state, dict) or state.get('phase') != 'complete' or
                state.get('mode') != 'analysis' or state.get('chat_mode') != 'Chat' or
                not isinstance(state.get('prompt'), str) or not state['prompt'].strip() or
                state.get('submitted_prompt', state['prompt']) != state['prompt'] or
                type(state.get('page')) is not int or state['page'] < 0 or
                not isinstance(state.get('url'), str) or not isinstance(state.get('model'), dict) or
                not conversation_url(state.get('url') or '')):
            raise BrowserError('Cleanup requires the original completed analysis, prompt and owned page')
        validate_model('analysis', state.get('model') or {})
        original_submission = validate_cleanup_network(json.loads(archive['network.json']))
        expected = dict(version=1, run_sha256=hashlib.sha256(archive['run.json']).hexdigest(),
                        response_sha256=hashlib.sha256(archive['response.md']).hexdigest(),
                        conversation_url=state['url'], page=state['page'], tab='closed')
        receipt = cleanup_receipt(run, expected)
        if receipt is None:
            if state.get('tab') == 'closed':
                raise BrowserError('Original completed tab is already closed; no cleanup receipt can be inferred')
            require_browser_daemon()
            pages = cli('list_pages')
            if not re.search(r'^' + str(state['page']) + r': .*' + re.escape(state['url']) +
                             r'(?:\)|\s|$)', pages, re.M):
                raise BrowserError('Cannot verify the original owned page and conversation')
            current_submission = validate_cleanup_network(network_evidence(state['page'], 'analysis', run=run))
            if current_submission != original_submission:
                raise BrowserError('Current browser submission differs from the original request evidence')
            observation = observe_run(state['page'], 'analysis')
            verify_conversation(state, observation)
            if observation['users'] != [state['prompt']] or not is_finished('analysis', observation):
                raise BrowserError('Cleanup requires only the original prompt and finished assistant reply')
            if not hydration_equivalent(archive['response.md'].decode('utf-8'), observation['text']):
                raise BrowserError('Current assistant reply differs substantively from the banked response')
            draft = composer(state['page'])
            if draft['text'] or draft['files'] or draft['busy']:
                raise BrowserError('Cleanup preserves the current composer draft or upload')
            if any((run / name).is_symlink() or (run / name).read_bytes() != data
                   for name, data in archive.items()):
                raise BrowserError('Completed archive changed during cleanup verification')
            status = close_completed_tab(state, observation)
            if status != 'closed':
                raise BrowserError('Completed cleanup ' + status + '; no receipt written')
            if any((run / name).is_symlink() or (run / name).read_bytes() != data
                   for name, data in archive.items()):
                raise BrowserError('Completed archive changed during tab closure; no receipt written')
            data = (json.dumps(expected, indent=2) + '\n').encode('utf-8')
            with tempfile.TemporaryDirectory(prefix='.browser-cleanup-', dir=run) as scratch:
                temporary = Path(scratch) / 'tab_cleanup.json'
                temporary.write_bytes(data)
                (run / temporary.name).hardlink_to(temporary)
            receipt = cleanup_receipt(run, expected)
        print(json.dumps({'phase': 'complete', 'run': str(run), 'url': state['url'],
                          'artifact': receipt, 'tab': 'closed'}))


def citation_archive(run):
    for name in ('run.json', 'response.md'):
        path = run / name
        if path.is_symlink() or not path.is_file():
            raise BrowserError('Citation capture requires regular owned ' + name)
    metadata = (run / 'run.json').read_bytes()
    state = json.loads(metadata)
    if (state.get('phase') != 'complete' or state.get('mode') != 'analysis' or
            not conversation_url(state.get('url') or '')):
        raise BrowserError('Citation capture requires a completed analysis conversation')
    response = (run / 'response.md').read_bytes()
    return state, response, hashlib.sha256(metadata).hexdigest()


def validate_citations(payload, state, response, run_hash):
    fields = {'version', 'conversation_url', 'run_sha256', 'response_sha256',
              'observed_response_sha256', 'observed_at_utc', 'citations'}
    response_hash = hashlib.sha256(response).hexdigest()
    if (not isinstance(payload, dict) or set(payload) != fields or
            type(payload['version']) is not int or payload['version'] != 1 or
            payload['conversation_url'] != state['url'] or payload['run_sha256'] != run_hash or
            payload['response_sha256'] != response_hash or
            payload['observed_response_sha256'] != response_hash):
        raise BrowserError('Citation sidecar does not match the immutable run and response')
    timestamp = payload['observed_at_utc']
    if not isinstance(timestamp, str) or not timestamp.endswith('Z'):
        raise BrowserError('Citation observation timestamp must be UTC')
    datetime.fromisoformat(timestamp[:-1] + '+00:00')
    rows = payload['citations']
    if not isinstance(rows, list) or not 0 < len(rows) <= MAX_CITATIONS:
        raise BrowserError('Citation sidecar requires 1 to 256 observed links')
    text = response.decode('utf-8')
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'url', 'context_quote'}:
            raise BrowserError('Invalid observed citation row')
        url, quote = row['url'], row['context_quote']
        if (not isinstance(url, str) or urlsplit(url).scheme not in ('http', 'https') or
                not urlsplit(url).netloc or not isinstance(quote, str) or
                not quote.strip() or len(quote) > 2048 or quote not in text):
            raise BrowserError('Citation href or exact response context is invalid')


def existing_citations(run, state, response, run_hash):
    path = run / 'source_citations.json'
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CITATION_BYTES:
        raise BrowserError('Citation sidecar must be a regular file of at most 512 KiB')
    data = path.read_bytes()
    validate_citations(json.loads(data), state, response, run_hash)
    return {'file': path.name, 'sha256': hashlib.sha256(data).hexdigest()}


def save_citations(run, observation, observed_at):
    state, response, run_hash = citation_archive(run)
    observed = (observation['text'] + '\n').encode('utf-8')
    if observation['url'] != state['url'] or observed != response:
        raise BrowserError('Observed assistant bytes do not match the banked response')
    payload = dict(version=1, conversation_url=state['url'], run_sha256=run_hash,
                   response_sha256=hashlib.sha256(response).hexdigest(),
                   observed_response_sha256=hashlib.sha256(observed).hexdigest(),
                   observed_at_utc=observed_at, citations=observation.get('citations', []))
    validate_citations(payload, state, response, run_hash)
    data = (json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if len(data) > MAX_CITATION_BYTES:
        raise BrowserError('Observed citation evidence exceeds 512 KiB')
    path = run / 'source_citations.json'
    if path.exists() or path.is_symlink():
        receipt = existing_citations(run, state, response, run_hash)
        if json.loads(path.read_bytes())['citations'] != payload['citations']:
            raise BrowserError('Immutable citation sidecar contains different observed links')
        return receipt
    with tempfile.TemporaryDirectory(prefix='.browser-citations-', dir=run) as scratch:
        temporary = Path(scratch) / path.name
        temporary.write_bytes(data)
        path.hardlink_to(temporary)  # Publish atomically without replacing existing evidence.
    return {'file': path.name, 'sha256': hashlib.sha256(data).hexdigest()}


def capture_citations(args):
    run = args.run.resolve(strict=True)
    with (run / 'collect.lock').open('r') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state, response, run_hash = citation_archive(run)
        sidecar = run / 'source_citations.json'
        if sidecar.exists() or sidecar.is_symlink():
            receipt = existing_citations(run, state, response, run_hash)
            print(json.dumps({'phase': 'complete', 'run': str(run), 'url': state['url'],
                              'artifact': receipt, 'tab': 'not opened: immutable replay'}))
            return
        evidence = json.loads((run / 'network.json').read_bytes())
        if (evidence.get('chatgpt_conversation_request') is not True or
                evidence.get('codex_requests') != 0 or evidence.get('submitted_models') != ['gpt-6-pro']):
            raise BrowserError('Completed analysis lacks its verified GPT-6 Pro submission receipt')
        metadata = (run / 'run.json').read_bytes()
        pages = cli('new_page', state['url'])
        match = re.search(r'^(\d+): .*' + re.escape(state['url']) + r'.*\[selected\]', pages, re.M)
        if not match:
            raise BrowserError('Cannot identify the owned citation-capture tab')
        page = int(match[1])
        verified = None
        legacy = False
        try:
            wait_until(lambda: evaluate(page, '''return !!document.querySelector('main [data-user-message-bubble]') &&
                [...document.querySelectorAll('main h4,main [data-message-author-role],main [data-conversation-role]')]
                  .some(e=>e.textContent.trim()==='ChatGPT said:' ||
                    e.getAttribute('data-message-author-role')==='assistant' ||
                    e.getAttribute('data-conversation-role')==='assistant');'''),
                description='Completed citation conversation readiness')
            observation = observe(page)
            verify_conversation(state, observation)
            if not is_finished('analysis', observation):
                raise BrowserError('Original assistant response is not complete')
            if (observation['text'] + '\n').encode('utf-8') != response:
                legacy = True
                observation = observe(page, legacy=True)
                verify_conversation(state, observation)
                if not is_finished('analysis', observation):
                    raise BrowserError('Original assistant response is not complete')
            if (observation['text'] + '\n').encode('utf-8') != response:
                raise BrowserError('Current and legacy assistant bytes differ from the banked response')
            verified = observation
            observed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            if not observation.get('citations'):
                raise BrowserError('No actual source hrefs found in the completed assistant')
        except Exception as error:
            if verified is None:
                raise BrowserError(str(error) + '; owned citation-capture tab preserved for inspection') from error
            raise
        finally:
            if verified is not None:
                cleanup = close_completed_tab(dict(state, page=page), verified, legacy=legacy)
                if cleanup != 'closed':
                    raise BrowserError('Citation capture ' + cleanup + '; no sidecar written')
        if (run / 'run.json').read_bytes() != metadata or (run / 'response.md').read_bytes() != response:
            raise BrowserError('Completed archive changed during citation capture')
        receipt = save_citations(run, observation, observed_at)
        print(json.dumps({'phase': 'complete', 'run': str(run), 'url': state['url'],
                          'artifact': receipt, 'tab': 'closed'}))


def collect(args):
    run = args.run.resolve(strict=True)
    with (run / 'collect.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads((run / 'run.json').read_text())
        if state['phase'] == 'complete':
            print(json.dumps({'phase': 'complete', 'run': str(run), 'url': state['url']}))
            return
        if state['phase'] not in ('sending', 'submitted'):
            raise BrowserError('Run was not submitted; inspect the preserved browser tab')
        page = state['page']
        observation = observe_run(page, state['mode'])
        observed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        verify_conversation(state, observation)
        if not conversation_url(observation['url']) or not is_finished(state['mode'], observation):
            result = {'phase': 'pending', 'run': str(run), 'url': observation['url']}
            if state['mode'] == 'research':
                research = observation['research']
                result['research_phase'] = research['phase']
                result['progress'] = research.get('status') or research['text'] or observation['text']
            print(json.dumps(result))
            return
        evidence = network_evidence(page, state['mode'], run=run)
        if not evidence['chatgpt_conversation_request']:
            raise BrowserError('Missing browser submission evidence; do not claim a verified run')
        (run / 'network.json').write_text(json.dumps(evidence, indent=2) + '\n')
        artifacts = []
        if state['mode'] == 'images':
            for index, item in enumerate(observation['images'], 1):
                data, extension = download(page, item['src'])
                path = run / f'image-{index}.{extension}'
                path.write_bytes(data)
                artifacts.append({'file': path.name, 'sha256': hashlib.sha256(data).hexdigest(),
                                  'width': item['width'], 'height': item['height']})
        else:
            response = observation['text']
            if state['mode'] == 'research':
                sources = observation['research']['links']
                (run / 'sources.json').write_text(json.dumps(sources, indent=2) + '\n')
                artifacts.append({'file': 'sources.json'})
                if sources:
                    response += '\n\nSource links\n\n' + '\n'.join(
                        f'- [{s["title"] or s["url"]}]({s["url"]})' for s in sources)
                response += '\n\nConversation: ' + observation['url']
            (run / 'response.md').write_text(response + '\n')
            artifacts.append({'file': 'response.md'})
        capture = state['mode'] == 'analysis' and bool(observation.get('citations'))
        if capture:
            artifacts.append({'file': 'source_citations.json'})
        state.update(phase='complete', url=observation['url'], artifacts=artifacts)
        state.pop('error', None)
        save(run, state)
        state['tab'] = close_completed_tab(state, observation)
        save(run, state)
        receipts = [dict(artifact) for artifact in artifacts]
        if capture:
            receipts[-1] = save_citations(run, observation, observed_at)
        print(json.dumps({'phase': 'complete', 'run': str(run), 'url': state['url'],
                          'artifacts': receipts, 'tab': state['tab']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    send = sub.add_parser('start')
    send.add_argument('mode', choices=['images', 'analysis', 'research'])
    send.add_argument('--prompt', type=Path, required=True)
    send.add_argument('--attach', type=Path, action='append', default=[])
    send.add_argument('--run', type=Path, required=True)
    get = sub.add_parser('collect')
    get.add_argument('--run', type=Path, required=True)
    citations = sub.add_parser('capture-citations', help='Capture exact assistant hrefs for an unchanged completed analysis')
    citations.add_argument('--run', type=Path, required=True)
    cleanup = sub.add_parser('cleanup-completed', help='Close the unchanged owned tab of a completed analysis')
    cleanup.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command != 'cleanup-completed':
            require_browser_daemon()
        {'start': start, 'collect': collect, 'capture-citations': capture_citations,
         'cleanup-completed': cleanup_completed}[args.command](args)
    except (BrowserError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
