#!/usr/bin/env python3
"""Submit and collect ChatGPT website jobs through Google's Chrome DevTools CLI.

Start writes a run directory before sending; collect never sends or retries a job.
Requires chrome-devtools (chrome-devtools-mcp package) and signed-in Chrome on Linux or macOS.
"""
import argparse
import base64
import fcntl
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit


class BrowserError(RuntimeError):
    pass


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


def composer(page):
    return evaluate(page, '''const e=document.querySelector('[role=textbox][contenteditable=true]');
      const f=e?.closest('form');
      return {text:e?.innerText?.trim(),
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
        pattern = re.escape(Path(name).stem) + r'(?:\(\d+\))?' + re.escape(Path(name).suffix)
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
        raise BrowserError('Composer attachments do not match the intended files')


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


def request_model(page, request_id):
    data = json.loads(cli('get_network_request', page, '--reqid', request_id,
                          '--output-format=json'))['networkRequest']['requestBody']
    body = json.loads(data) if isinstance(data, str) else data
    return body.get('model')


def validate_request_model(mode, model):
    if not isinstance(model, str) or not model:
        raise BrowserError('No model identifier in captured browser submission')
    valid = (mode == 'research' or
             (model == 'gpt-6-pro' if mode == 'analysis' else 'pro' not in model.lower()))
    if not valid:
        raise BrowserError(f'Unexpected submitted model for {mode}: {model}')


def network_evidence(page, mode):
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
            if match[2] == 'POST' and url.path in ('/backend-api/f/conversation', '/backend-api/conversation') and match[4] == '200':
                model = request_model(page, match[1])
                validate_request_model(mode, model)
                models.append(model)
    if any(e['path'].startswith('/backend-api/codex') for e in entries):
        raise BrowserError('Unexpected Codex endpoint in browser traffic; inspect the run')
    sent = any(e['method'] == 'POST' and e['path'] in
               ('/backend-api/f/conversation', '/backend-api/conversation')
               and e['status'] == '200' for e in entries)
    return {'chatgpt_conversation_request': sent, 'codex_requests': 0,
            'submitted_models': models, 'requests': entries}


def observe(page):
    return evaluate(page, r'''const visible=e=>!!e && e.getClientRects().length>0 &&
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
      return {url:location.href, users:[...main.querySelectorAll('[data-user-message-bubble]')]
        .filter(visible).map(e=>{
          const content=e.querySelector('[data-search-result-target]') || e.querySelector('[dir="auto"]') || e;
          return content.innerText.trim();
        }),
        text:last?.innerText.replace(/^ChatGPT said:\s*/, '').trim() || '',
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
        observation['research_complete'] = research['complete']
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
        wait_until(lambda: composer(page)['send'] and not composer(page)['busy'], 60)
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
        save(run, state)  # A timeout after this point must never trigger a resend.
        click(page, 'button[aria-label="Send"]')
        wait_until(lambda: prompt_visible(state, observe(page)), 30)
        state.update(phase='submitted', url=conversation_url(observe(page)['url']))
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
        return bool(observation.get('research_complete') and observation.get('text'))
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


def close_completed_tab(state, observation):
    try:
        current = observe_run(state['page'], state['mode'])
        draft = composer(state['page'])
        if (current != observation or draft['text'] or draft['files'] or draft['busy']):
            return 'kept: tab changed after collection'
        cli('close_page', state['page'])
        return 'closed'
    except (BrowserError, OSError, ValueError, subprocess.SubprocessError) as error:
        return 'close failed: ' + str(error)


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
        verify_conversation(state, observation)
        if not conversation_url(observation['url']) or not is_finished(state['mode'], observation):
            result = {'phase': 'pending', 'run': str(run), 'url': observation['url']}
            if state['mode'] == 'research':
                research = observation['research']
                result['research_phase'] = research['phase']
                result['progress'] = research.get('status') or research['text'] or observation['text']
            print(json.dumps(result))
            return
        evidence = network_evidence(page, state['mode'])
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
        state.update(phase='complete', url=observation['url'], artifacts=artifacts)
        state.pop('error', None)
        save(run, state)
        state['tab'] = close_completed_tab(state, observation)
        save(run, state)
        print(json.dumps({'phase': 'complete', 'run': str(run), 'url': state['url'],
                          'artifacts': artifacts, 'tab': state['tab']}))


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
    args = parser.parse_args()
    try:
        require_browser_daemon()
        (start if args.command == 'start' else collect)(args)
    except (BrowserError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
