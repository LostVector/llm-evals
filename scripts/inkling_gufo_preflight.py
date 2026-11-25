#!/usr/bin/env python3
"""Qualify the serving configuration before starting the Inkling evals."""

import argparse
from concurrent.futures import ThreadPoolExecutor, wait
import json
from pathlib import Path
from threading import Barrier
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4


SERVER_SLOTS = 4
MAX_ACTIVE_TASKS = 3
CONTEXT_PER_SLOT = 262_144
CHECKPOINT = 'Inkling-2-Mini-Q8_0.gguf'


def read_json(base, route, body=None):
    request = Request(
        f'{base.rstrip("/")}{route}',
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
    )
    with build_opener(ProxyHandler({})).open(request, timeout=900) as response:
        return json.load(response)


def validate_server(props, model, build_info):
    if not build_info or props.get('build_info') != build_info:
        raise ValueError('Wrong Gufo candidate build')
    if props.get('model_alias') != model or Path(props.get('model_path', '')).name != CHECKPOINT:
        raise ValueError('Wrong model or checkpoint')
    if props.get('total_slots') != SERVER_SLOTS:
        raise ValueError('Expected four inference slots')
    if props.get('default_generation_settings', {}).get('n_ctx') != CONTEXT_PER_SLOT:
        raise ValueError('Expected 262,144 tokens per slot')


def interleaved_completions(base, model, conversations, *, observe_slots=False):
    if len(conversations) != MAX_ACTIVE_TASKS:
        raise ValueError('Expected exactly three conversations')
    barrier = Barrier(MAX_ACTIVE_TASKS, timeout=10)

    def complete(messages):
        barrier.wait()
        return read_json(base, '/v1/chat/completions', {
            'model': model,
            'messages': messages,
            'temperature': 0,
            'reasoning_effort': 'medium',
            'reasoning_budget_tokens': 16,
            'max_tokens': 128,
        })

    with ThreadPoolExecutor(max_workers=MAX_ACTIVE_TASKS) as workers:
        futures = [workers.submit(complete, conversation) for conversation in conversations]
        pending = set(futures)
        observed = False
        while observe_slots and pending:
            active_tasks = sum(slot['is_processing'] for slot in read_json(base, '/slots'))
            if active_tasks > MAX_ACTIVE_TASKS:
                raise ValueError('More than three tasks are active')
            if active_tasks == MAX_ACTIVE_TASKS:
                observed = True
                break
            _, pending = wait(pending, timeout=0.25)
        results = [future.result() for future in futures]
        if observe_slots and not observed:
            raise ValueError('The server did not process three tasks simultaneously')
        return results


def check_reuse(cold, warm):
    prior_prompt = cold['usage']['prompt_tokens']
    usage = warm['usage']
    reused = usage['prompt_tokens_details']['cached_tokens']
    if prior_prompt < 2_048 or not prior_prompt * 0.8 <= reused <= usage['prompt_tokens']:
        raise ValueError(f'Expected the conversation prefix to survive. Reused {reused} of {prior_prompt} prior tokens.')
    return dict(prior_prompt_tokens=prior_prompt, warm_prompt_tokens=usage['prompt_tokens'], reused_tokens=reused)


def qualify_chat(base, model):
    def chat(messages, cap, **options):
        result = read_json(base, '/v1/chat/completions', {
            'model': model, 'messages': messages, 'max_tokens': cap,
            'temperature': 0, **options,
        })
        usage = result['usage']
        if not 0 < usage['completion_tokens'] <= cap:
            raise ValueError('Unexpected completion-token usage')
        if usage['total_tokens'] != usage['prompt_tokens'] + usage['completion_tokens']:
            raise ValueError('Total token usage is inconsistent')
        return result['choices'][0], usage

    tool = {'type': 'function', 'function': {
        'name': 'stock_count', 'description': 'Look up stock counts',
        'parameters': {
            'type': 'object', 'properties': {'item': {'type': 'string'}},
            'required': ['item'], 'additionalProperties': False,
        },
    }}
    initial = [{'role': 'user', 'content':
                'Use stock_count with item apple. Report the returned stock count.'}]
    choice, _ = chat(initial, 384, reasoning_effort='none', tools=[tool],
                     tool_choice={'type': 'function', 'function': {'name': 'stock_count'}})
    message = choice['message']
    if choice['finish_reason'] != 'tool_calls' or len(message.get('tool_calls') or []) != 1:
        raise ValueError('Expected exactly one native tool call')
    call = message['tool_calls'][0]
    if not call.get('id') or call['function']['name'] != 'stock_count':
        raise ValueError('Wrong native tool call')
    if json.loads(call['function']['arguments'])['item'].lower() not in ('apple', 'apples'):
        raise ValueError('Wrong native tool argument')
    answer, _ = chat(initial + [message, {
        'role': 'tool', 'tool_call_id': call['id'], 'content': '37 apples are in stock.',
    }], 128, reasoning_effort='none', tools=[tool], tool_choice='none')
    if '37' not in (answer['message'].get('content') or ''):
        raise ValueError('The model did not answer from the tool result')

    prompt = [{'role': 'user', 'content':
               'Reason carefully before answering. How many integer partitions of 42 into distinct parts are there?'}]
    cap = 24
    reasoning, usage = chat(prompt, cap, reasoning_effort='xhigh')
    reasoning_tokens = usage['completion_tokens_details']['reasoning_tokens']
    if (reasoning['finish_reason'] != 'length' or usage['completion_tokens'] != cap
            or not 0 < reasoning_tokens <= cap
            or not reasoning['message'].get('reasoning_content')
            or reasoning['message'].get('content')):
        raise ValueError('The capped response did not report reasoning usage correctly')
    budget = 4
    forced, forced_usage = chat(prompt, 128, reasoning_effort='xhigh',
                                reasoning_budget_tokens=budget)
    forced_tokens = forced_usage['completion_tokens_details']['reasoning_tokens']
    forced_answer = forced['message'].get('content') or ''
    if (not budget <= forced_tokens <= budget + 3 or forced_tokens >= reasoning_tokens
            or not forced_answer or '<|content_thinking|>' in forced_answer):
        raise ValueError('The reasoning budget did not close thinking and leave room to answer')
    return {'native_tool_round_trip': True, 'completion_token_cap': cap,
            'capped_reasoning_tokens': reasoning_tokens,
            'reasoning_budget_tokens': budget, 'forced_reasoning_tokens': forced_tokens}


def qualify(base, model, build_info):
    props = read_json(base, '/props')
    validate_server(props, model, build_info)
    slots = read_json(base, '/slots')
    if len(slots) != SERVER_SLOTS or any(slot.get('n_ctx') != CONTEXT_PER_SLOT for slot in slots):
        raise ValueError('Server did not report four 262,144-token slots')
    if any(slot.get('is_processing') for slot in slots):
        raise ValueError('Run the concurrency check before starting benchmark workers')
    chat = qualify_chat(base, model)
    texts = ('amber meadow', 'granite harbor', 'violet lantern')
    nonce = uuid4().hex
    prompts = []
    for i, phrase in enumerate(texts):
        records = '\n'.join(
            f'Record {j}: Collection {i} has {12 + j * 3} catalog entries. '
            f'The archive shelf number is {j + 35}. Maintenance review is scheduled for April.'
            for j in range(74)
        )
        prompts.append([{'role': 'user', 'content':
                         f'Inventory report {nonce}-{i}. The report is background material.\n'
                         f'{records}\n\nThe access phrase is "{phrase}". '
                         'What is the two-word access phrase? Reply with the phrase only.'}])
    cold = interleaved_completions(base, model, prompts, observe_slots=True)
    for prompt, result, text in zip(prompts, cold, texts, strict=True):
        reply = result['choices'][0]['message']
        if text not in (reply.get('content') or '').lower():
            raise ValueError(f'Expected {text!r} in cold response, received {reply.get("content")!r}')
        prompt.extend((reply, {'role': 'user', 'content': 'Repeat the same two words.'}))
    warm = interleaved_completions(base, model, prompts)
    for result, text in zip(warm, texts, strict=True):
        if text not in (result['choices'][0]['message'].get('content') or '').lower():
            raise ValueError('A warm response did not match its conversation')
    return dict(server_slots=SERVER_SLOTS, max_active_tasks=MAX_ACTIVE_TASKS,
                context_per_slot=CONTEXT_PER_SLOT, build=props.get('build_info'),
                chat=chat,
                conversations=[check_reuse(a, b) for a, b in zip(cold, warm, strict=True)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True, help='Gufo base address without /v1')
    parser.add_argument('--model', required=True, help='Served model ID')
    parser.add_argument('--build-info', required=True, help='Expected Gufo version and revision')
    args = parser.parse_args()
    print(json.dumps(qualify(args.base_url, args.model, args.build_info), indent=2))


if __name__ == '__main__':
    main()
